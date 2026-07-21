# Autolina Scraper

[![CI](https://github.com/danyk20/autolina-scraper/actions/workflows/ci.yml/badge.svg)](https://github.com/danyk20/autolina-scraper/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/autolina-scraper)](https://pypi.org/project/autolina-scraper/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)

> Unofficial, independently developed project — not affiliated with, endorsed by,
> or sponsored by autolina.ch ag. "autolina" is a trademark of its respective owner.

Fetches every listing for a given make/model from [autolina.ch](https://www.autolina.ch) —
for free, no API key, no paid scraping service. It's designed as a drop-in,
API-compatible sibling to
[`autoscout24-scraper`](https://github.com/danyk20/autoscout24-scraper): same
`scrape()` signature, same `ScrapeResult` shape, same CLI flags — swap the import
and point it at a different Swiss car marketplace.

autolina.ch has no public JSON API the way AutoScout24 does — it's a single
server-rendered Angular app — so this scraper parses the same server-rendered
HTML, using a small set of generic, resilient selectors rather than brittle
hardcoded field positions (see
["How the data is obtained"](docs/REFERENCE.md#how-the-data-is-obtained)). By
default it does a two-phase scrape: search to collect every matching listing
id, then visit each one individually for the full record (VIN, energy data,
standard/optional equipment, dealer contact info, images, ...). Every spec row
and equipment item the site renders is kept — nested objects are flattened
into `parent_child` CSV columns, lists are joined into semicolon-separated
cells — nothing is silently dropped.

**🤖 Robot-friendly.** This project is explicitly intended to be run, read,
imported, or adapted by AI agents and bots, same as a human developer — see
[License](#license). It only ever requests autolina.ch's open, robots.txt-permitted
routes and identifies itself honestly; see
[Compliance](docs/REFERENCE.md#compliance-robotstxt-and-cloudflare) for exactly
which routes and why.

## Setup

Requires [pipenv](https://pipenv.pypa.io/) (`brew install pipenv`).

```bash
git clone https://github.com/danyk20/autolina-scraper.git
cd autolina-scraper
pipenv install --dev
```

Contributing, linting, and testing commands: see [CONTRIBUTING.md](CONTRIBUTING.md).

## Usage

### CLI

```bash
pipenv run python -m autolina_scraper.cli --make VW --model Tiguan
```

Prints progress, then writes `vw_tiguan.csv` and `vw_tiguan.json` in the current
directory. Installed via `pip install` instead? The same command is
`autolina-scraper --make VW --model Tiguan`.

| Flag | Description |
|---|---|
| `--version` | Print the installed version and exit |
| `--make` | Make name or slug, e.g. `VW` or `vw` (required) |
| `--model` | Model name or slug, e.g. `Tiguan` or `tiguan` (required) |
| `--domain` | Country domain (default `ch`) — autolina.ch only exists for `ch` |
| `--category` | Vehicle category — only `car` is supported (no motorcycles) |
| `--out` | Output file base name, without extension. Defaults to `<make>_<model>` |
| `--no-detail` | Skip per-listing detail visits; keep only summary fields (faster, fewer fields) |
| `--delay` | Seconds between requests (default `1.0`) — raise this if you get rate-limited |
| `--price-from` / `--price-to` | Filter by price in CHF (inclusive, either end optional) |
| `--mileage-from` / `--mileage-to` | Filter by mileage in km (inclusive, either end optional) |
| `--year-from` / `--year-to` | Filter by first-registration year (inclusive, either end optional) |
| `-v` / `--verbose` | Also show debug-level detail (mutually exclusive with `-q`) |
| `-q` / `--quiet` | Suppress progress output; only warnings/errors (mutually exclusive with `-v`) |

Filters combine with AND and are applied server-side (confirmed against the live
site), so they also cut down how many listings get visited in the detail phase. A
mistyped make/model prints a clean error (plus, for an unknown model, the list of
valid models) instead of crashing.

```bash
# Fast mode: search results only, skip per-listing detail
pipenv run autolina-scraper --make VW --model Tiguan --no-detail

# 2018 or newer, under CHF 30'000, under 60'000 km
pipenv run autolina-scraper --make VW --model Tiguan --price-to 30000 --year-from 2018 --mileage-to 60000
```

### As a library

```bash
pip install autolina-scraper
```

```python
from autolina_scraper import scrape

result = scrape("VW", "Tiguan", price_to=30000, year_from=2018)

for row in result.rows:          # list[dict], CSV-ready
    print(row["price"], row["mileage"], row["url"])

result.to_csv("vw_tiguan.csv")   # optional — no files are written unless you ask
```

Full `scrape()` signature, the `ScrapeResult` return type, the complete field
schema, and how this differs from the AutoScout24 reference:
**[docs/REFERENCE.md](docs/REFERENCE.md)**.

## Testing

```bash
pipenv run pytest                    # unit tests (fast, no network), coverage gate enforced
pipenv run pytest -m e2e --no-cov    # end-to-end tests against the real live site
```

Unit tests mock all HTTP (via [`responses`](https://github.com/getsentry/responses))
against real saved HTML fixtures — no network access, no live-site dependency. E2E
tests target a small-inventory make/model to confirm the scraper still works
against the live site.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup, pre-PR checks, and what to do
if autolina.ch changes its markup and a test starts failing.

Be a reasonable citizen: the default request delay is intentional — this project
only works because it sticks to autolina.ch's own open, robots.txt-permitted
routes. Don't remove the delay, don't crank up concurrency, and never point this
at the site's Cloudflare-protected internal routes.

## License

Released under the [MIT License](LICENSE) — you can use, copy, modify, merge,
publish, distribute, and sell copies of this code, for free, for any purpose,
commercial or not, as long as the license text stays attached. No warranty.

**AI agents, LLM-based coding assistants, and other bots are explicitly welcome to
use this project** — to run the scraper, read and parse its output, import
`scrape()` into another project, or read and adapt its source — under exactly the
same terms as a human, with no additional restriction and no need to ask
permission. That's why [docs/REFERENCE.md](docs/REFERENCE.md) documents the full
function signature, return type, and data schema: so a bot can integrate correctly
without a human in the loop.

This license does not grant any rights to autolina.ch's own data or terms of
service — this project only automates requests to routes autolina.ch's own
robots.txt permits a normally-identified crawler to fetch; what you do with the
results is between you and them.
