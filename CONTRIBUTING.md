# Contributing

## Dev setup

```bash
git clone https://github.com/danyk20/autolina-scraper.git
cd autolina-scraper
pipenv install --dev
```

## Pre-PR checks

```bash
pipenv run ruff check .
pipenv run mypy src
pipenv run pytest                    # unit tests, coverage gate enforced
pipenv run pytest -m e2e --no-cov    # optional, hits the real live site
```

All four should pass before opening a PR. CI runs the first three on every
push/PR; the e2e suite runs on a schedule (see
[.github/workflows/e2e.yml](.github/workflows/e2e.yml)) since it depends on
the live site being reachable and isn't something a PR should be blocked on.

## If autolina.ch changes its markup and a test starts failing

This project parses server-rendered HTML (see
[docs/REFERENCE.md](docs/REFERENCE.md#how-the-data-is-obtained) for why), so
it's more exposed to markup drift than an API client would be. When a test
fails against a *real* fixture (not a synthetic one built inline in the test),
that's the expected failure mode when the site changes something — here's the
loop:

1. Fetch a fresh copy of the affected page with a plain HTTP client and this
   project's own User-Agent (see `autolina_scraper.http.USER_AGENT`) — not a
   browser UA. Save it under `tests/fixtures/`.
2. Diff it against the old fixture to see what actually changed (class name,
   structure, wording).
3. Update the relevant selector in `autolina_scraper.htmlparse`/`search.py`/
   `detail.py` and re-run the unit suite against the new fixture.
4. If the change affects a *filter query parameter* (`price`/`mileage`/`date`),
   re-confirm it live by diffing result counts for a couple of query strings
   before trusting it — don't guess.

## Extending the filter set

`price`, `mileage`, and `date` (year) are the only server-side filters this
project ships, because they're the only ones empirically confirmed to work as
real query parameters (see
[docs/REFERENCE.md](docs/REFERENCE.md#differences-from-autoscout24-scraper)).
autolina.ch's search UI clearly supports more (body type, fuel type,
transmission, colour, warranty) — reverse-engineering the correct query
parameter names/encodings for any of these (the same way `price=min-max` was
confirmed: build a URL, diff the resulting listing count and fields against a
known-narrower query) and wiring it into `search.build_query()` +
`orchestrate.scrape()` + the CLI is a welcome contribution. Please include the
live-diffing evidence in the PR description, not just the code — a guessed
parameter that silently does nothing is worse than not having the filter.

## Be a reasonable citizen

- Don't remove the default request delay or add a concurrency knob — this
  project works because it behaves like a single, identifiable, patient
  visitor. See the README's Contributing section for why.
- Never point this project at `/carList` or attempt to solve/bypass the
  Cloudflare challenge on it. See
  [docs/REFERENCE.md](docs/REFERENCE.md#compliance-robotstxt-and-cloudflare).
- Keep the User-Agent honest — no browser spoofing, no impersonating a named
  bot (Googlebot, ClaudeBot, ...) this project isn't.

## Releasing

Releases are tag-triggered and fully automated via
[.github/workflows/release.yml](.github/workflows/release.yml) — maintainers
only, not something a contributing PR needs to touch:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

That runs, in order: `build` (sdist + wheel, uploaded once as an artifact and
reused by every later job) → `test` (full unit suite, coverage gate) →
`publish-testpypi` → `smoke-test-testpypi` (installs the just-published
version from TestPyPI into a clean environment and runs
`autolina-scraper --version`) → `publish-pypi`. Publishing to both indexes
uses [PyPI trusted publishing](https://docs.pypi.org/trusted-publishers/)
(OIDC) — no API tokens stored anywhere. If the TestPyPI smoke test fails, the
real PyPI publish never runs.

One-time setup for a maintainer's own fork/release (already done for this
repo): a pending publisher registered on both
[test.pypi.org](https://test.pypi.org/manage/account/publishing/) and
[pypi.org](https://pypi.org/manage/account/publishing/) (project name
`autolina-scraper`, owner `danyk20`, repository `autolina-scraper`, workflow
`release.yml`, environment `testpypi` / `pypi` respectively), plus matching
`testpypi` and `pypi` environments under the repo's **Settings → Environments**
(the environment name is what PyPI's OIDC check matches against — it has to
be exact).

Bump the version in **both** `pyproject.toml` (`[project].version`) and
`src/autolina_scraper/__init__.py` (`__version__`) before tagging — they're
not derived from the tag automatically. Update `CHANGELOG.md`, moving
`Unreleased` entries under a new `[X.Y.Z] - YYYY-MM-DD` heading.

## Commit / PR conventions

- Keep unit tests offline (mock HTTP via `responses`) — no test should require
  network access except the ones explicitly marked `e2e`.
- New fields/columns: prefer extending the generic extractors
  (`htmlparse.label_value_pairs`, `equipment_sections`) over hardcoding a new
  per-field selector, unless the data genuinely doesn't fit that shape.
- Update [CHANGELOG.md](CHANGELOG.md) under `Unreleased` for any
  user-visible change.
