# Reference

Full API surface, return types, and data schema for anyone integrating with
this project as a library — a human developer or an AI agent — without
reading the source. See [README.md](../README.md) for the pitch, install, and
CLI usage.

## How the data is obtained

autolina.ch is a single server-rendered Angular Universal app. Unlike
AutoScout24 (whose HTML site sits behind Cloudflare, but whose frontend calls
a separate, unprotected JSON API — the entire premise the reference project
is built on), autolina.ch has **no separate JSON API**: every page — search
results and individual listings alike — is plain server-rendered HTML.

There is one wrinkle worth documenting explicitly, because it shaped this
project's design: **some** requests get an additional `window.SS_Requests[...]`
`<script>` block embedding the exact internal JSON payload used to render the
page — a very AutoScout24-shaped shortcut. Empirically confirmed during
development: **that block only appears for requests whose User-Agent looks
like a real browser.** A plain `curl`/`requests`-style client — or this
project's own honestly-identified User-Agent (see
[Compliance](#compliance-robotstxt-and-cloudflare)) — never receives it, even
though the surrounding rendered HTML (listing cards, spec tables, equipment
lists, dealer info) is **byte-for-byte identical either way** (verified: same
`.car-row` count, same fields, regardless of User-Agent).

This project does not spoof a browser User-Agent to obtain that shortcut —
doing so would contradict the honest self-identification this project commits
to. Instead, it parses the same rendered HTML any client receives, using
generic, resilient primitives (`autolina_scraper.htmlparse`) rather than a
long list of brittle per-field CSS positions:

- **List pages** (`/{make}/{model}`, `/{make}/{model}/page/{n}`): each listing
  card (`.car-row`) is parsed for its link (id + slug), make/model (from
  `title` attributes), price, and the loosely-ordered `.vehicle-data` fields
  (year/mileage/power/transmission/fuel/condition/colour), classified by
  pattern rather than position, since not every field is always present.
- **Detail pages** (`/auto/{slug}/{id}`): every `<label>...</label><span>
  ...</span>` pair under `.details-row`/`.sub-details-grid`/`.energy-data-row`
  is extracted generically and keyed by the label text itself (transliterated
  to a safe column name) — so a new row autolina.ch adds later becomes a new
  column automatically instead of being silently dropped. Equipment lists,
  the dealer/seller card, the image gallery, and the posted-date/view-count
  line are parsed the same way.
- **Make/model catalog**: sourced from autolina.ch's own published sitemap
  (`sitemap/general1.xml.gz` for makes, `sitemap/model1.xml.gz` for make/model
  pairs) — the compliant, publisher-endorsed equivalent of AutoScout24's
  `/v1/makes` API. **The sitemap can lag behind the live site** — confirmed:
  Tesla's Model Y has real listings but was missing from `model1.xml.gz`. So
  make/model resolution is two-tier: the sitemap lookup (`resolve_make`/
  `resolve_model`) is the fast, offline-testable default, and only when it
  fails does `scrape()` fall back to a live request
  (`catalog.probe_make`/`probe_model`) — fetching `/{candidate}` or
  `/{make}/{candidate}` directly and accepting it only if the page's `<h1>`
  is genuinely scoped to that make (autolina.ch's router falls back to its
  generic, unscoped catalog page for a made-up slug rather than 404ing, so a
  bare "did it return 200" check isn't enough — this also means a real model
  with zero current listings, like a rare classic, resolves correctly instead
  of being reported as unknown).

One quirk had to be worked around, same as the AutoScout24 reference: without
an explicit sort order, a "boosted"/`TOP` listing can rotate into view between
requests, shifting pagination and risking skipped or duplicated listings. This
scraper de-duplicates by listing id across pages as a safety net and logs a
warning if the final unique count doesn't match the site's reported total.

## Compliance (robots.txt and Cloudflare)

- autolina.ch's internal route `/carList` sits behind an interactive
  Cloudflare Turnstile challenge (confirmed: direct requests get a `403` +
  "Verify you are human"). **This project never requests that route and never
  attempts to solve or bypass that challenge.** If a Cloudflare challenge is
  ever received from a route this library does use, `autolina_scraper.http`
  raises `ChallengeDetectedError` immediately rather than retrying — a changed
  WAF rule should fail loudly, not loop.
- Every route this library *does* use — `/{make}/{model}`, its `/page/{n}`
  continuations, `/auto/{slug}/{id}`, and the `sitemap/*.xml.gz` files — is
  open and not Cloudflare-challenged, confirmed live and repeatedly.
- `robots.txt` explicitly `Disallow: /` for generic scraper-library User-Agents
  (`python-requests`, `curl`, `Scrapy`, `Go-http-client`) and known aggressive
  crawlers, but the general `User-agent: *` group only disallows
  account/favorites/legal/compare pages — **listing and search pages are not
  blocked** for a normally, honestly identified crawler. This project's
  User-Agent (`autolina-scraper/<version> (+https://github.com/danyk20/autolina-scraper)`)
  never matches a disallowed pattern and never claims to be a named bot
  (Googlebot, ClaudeBot, etc.) it isn't.
- The default request delay (`delay=1.0`) exists for the same reason the
  AutoScout24 reference's does: this project works because it behaves like a
  reasonable, identifiable visitor. There is no concurrency knob and none is
  planned — see the README's Contributing section.

## `scrape()` signature

```python
def scrape(
    make: str,                       # e.g. "VW" or "vw" — name or slug, case-insensitive
    model: str,                      # e.g. "Tiguan" or "tiguan" — name or slug, case-insensitive
    *,
    domain: str = "ch",              # kept for signature parity with the reference; only "ch" exists
    category: str = "car",           # only "car" — autolina.ch has no motorcycles
    detail: bool = True,             # visit every listing individually for full fields (slower)
    price_from: int | None = None,   # CHF, inclusive
    price_to: int | None = None,     # CHF, inclusive
    mileage_from: int | None = None, # km, inclusive
    mileage_to: int | None = None,   # km, inclusive
    year_from: int | None = None,    # first-registration year, inclusive
    year_to: int | None = None,      # first-registration year, inclusive
    delay: float = 1.0,              # seconds between HTTP requests
    verbose: bool = True,            # emit progress via the "autolina_scraper" logger at INFO level
    session: requests.Session | None = None,  # reuse a session across calls if given
) -> ScrapeResult:
    ...
```

Raises `ValueError` immediately (before any network call) if any `_from` is
greater than its `_to`, or if `domain`/`category` isn't the one supported
value. Raises `ValueError` if `make`/`model` can't be resolved (the message
lists valid models for an unknown-model error). Raises `requests`
exceptions on unrecoverable network errors, and
`autolina_scraper.http.ChallengeDetectedError` if a Cloudflare challenge is
unexpectedly encountered.

### Differences from `autoscout24-scraper`

This project mirrors the reference's public API as closely as autolina.ch's
own site allows, but there are real, deliberate differences:

| | AutoScout24 reference | This project |
|---|---|---|
| Data source | Separate, unprotected JSON API | Server-rendered HTML, parsed generically |
| `category="motorcycle"` | Supported | **Not supported** — autolina.ch is cars-only; raises `ValueError` |
| `domain` other than the default | Accepted as a parameter (untested) | **Not supported** — autolina.ch only exists for `ch`; raises `ValueError` |
| Extra filters beyond price/mileage/year | None | None shipped in v1 — see below |
| Default `delay` | `0.4`s | `1.0`s — full HTML pages, more conservative |

**On extra filters:** autolina.ch's search page visibly offers more filter
dimensions than price/mileage/year (body type, fuel type, transmission,
colour, "with warranty", ...). Only `price`, `mileage`, and `date` (year) were
empirically confirmed to work as real server-side query parameters (by diffing
result counts against known query strings). Reverse-engineering the rest
without guessing was out of scope for v1 — a good first contribution for
anyone who wants to take it on (see [CONTRIBUTING.md](../CONTRIBUTING.md)).

**Logging.** Same philosophy as the reference: library code never configures
logging itself (no `basicConfig`, no handlers) — it only emits through
`logging.getLogger("autolina_scraper")`. To see progress when calling
`scrape()` directly:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

The CLI is the one place that configures real handlers automatically
(`--verbose`/`--quiet`).

## `ScrapeResult` — the return value

```python
@dataclass
class ScrapeResult:
    make_key: str          # resolved make slug, e.g. "vw"
    make_name: str          # resolved make display name, e.g. "VW"
    model_key: str          # resolved model slug, e.g. "tiguan"
    model_name: str         # resolved model display name, e.g. "TIGUAN"
    category: str           # "car" — the only supported value
    total_elements: int     # number of unique listings found by the search phase
    listings: list[dict]    # parsed listing records — see "Data structure" below
    rows: list[dict]        # flattened dicts, one per listing, CSV-ready, sorted by price ascending
    domain: str              # "ch" — the only supported value

    def to_csv(self, path: str) -> None: ...   # writes self.rows
    def to_json(self, path: str) -> None: ...  # writes self.listings
```

`len(result.rows) == len(result.listings) == result.total_elements` always
holds in the common case; if autolina.ch's pagination shifts mid-scrape (the
boosted-listing quirk described above), the actual unique count may fall
slightly short of the reported total — a warning is logged when that happens,
and `total_elements` always reflects what the site itself reported.

## Data structure

### JSON (`result.listings` / the `.json` file)

A **JSON array of listing objects**, one per vehicle found. Every listing
always includes:

| Field | Type | Description |
|---|---|---|
| `carId` | `int` | autolina.ch's internal listing id |
| `url` | `string` | Full URL of the original ad, e.g. `https://www.autolina.ch/auto/vw-tiguan/5033764` |
| `slug` | `string` | The make-model URL slug, e.g. `"vw-tiguan"` |
| `make` | `string` | e.g. `"VW"` |
| `price` | `int \| null` | Asking price in CHF |
| `mileage` | `int \| null` | Kilometers |
| `constructionYear` | `int \| null` | Model year, from the search summary |

There are two possible **shapes** for the rest of the object, depending on
whether detail mode ran:

- **Summary shape** (`detail=False` / `--no-detail`): ~18 fields — adds
  `modelType` (trim name), `previousPrice`, `powerOutput`, `isNew`,
  `isPremium` (the "TOP"/boosted-listing flag), `location`, `imageUrl`, and
  the human-readable `treibstoff`/`getriebeart`/`fahrzeugzustand`/
  `farbe_aussen_innen` (fuel/transmission/condition/exterior colour).
- **Detail shape** (`detail=True`, the default): ~40-50+ fields, varying by
  listing — every `<label>/<span>` spec row and both equipment lists autolina.ch
  renders for that specific vehicle, transliterated to safe column names (see
  [How the data is obtained](#how-the-data-is-obtained)). Typically includes
  `fahrgestell_nr` (VIN/chassis number), `wagen_nr`, `erstzulassung` (exact
  first-registration date), `leistung_hubraum` (power + engine size),
  `energieeffizienz`/`co2_emission` (energy data), `optionale_ausstattung`/
  `serienmaessige_ausstattung` (equipment lists), `dealer` (nested: `name`,
  `address`, `phone`, `mapsUrl`, `infopageUrl`), `images` (list of full-size
  photo URLs), `hitCount`, and `lastUpdatedDateLabel`. In this shape, the
  `getriebeart`/`treibstoff`/`fahrzeugzustand`/`farbe_aussen_innen` columns
  set by the summary phase are refined in place with the detail page's own
  (equally human-readable) values rather than duplicated under new names.

There is no fixed/versioned schema published by autolina.ch for these objects
— the tables above reflect the fields observed in practice as of this
writing, and the exact detail-page field set varies per listing (a listing
missing a spec row simply won't have that column). Treat unknown/missing
fields defensively (`.get(...)`, not `[...]`).

### CSV (`result.rows` / the `.csv` file)

The CSV is a **flattened** version of the same data — one row per listing,
same rows/listings correspondence and order. Flattening rules (also available
programmatically as `flatten_listing()`):

- Nested objects become `parent_child` columns, e.g. `dealer.name` ->
  `dealer_name`.
- Lists of strings (equipment, images) are joined into one
  semicolon-separated cell.
- Columns are the union of every field seen across all rows (heterogeneous
  listings don't crash the writer — missing values are an empty string),
  with `carId, url, make, modelType, price, previousPrice, neupreis,
  constructionYear, erstzulassung, mileage, fahrzeugzustand, treibstoff,
  getriebeart, antrieb, powerOutput, farbe_aussen_innen, dealer_name,
  dealer_address, dealer_phone` pinned first and everything else sorted
  alphabetically after them.

In full detail mode this is typically 40-55 columns, varying by listing; with
`--no-detail`/`detail=False` it's around 18.

## Test coverage by area

| Area | Unit tests | E2E tests |
|---|---|---|
| `htmlparse` (`label_value_pairs`, `slugify_label`, `equipment_sections`, `clean_text`) | Every branch: single/multi-value rows, missing labels/values, umlaut transliteration | Implicitly, via real fixtures |
| `catalog` (`resolve_make`/`resolve_model`, sitemap parsing) | Exact slug, case-insensitivity, substring fallback, ambiguous-match and not-found errors, malformed sitemap entries | Real make/model resolution |
| `search` (`fetch_listings`, `_parse_card`, `build_query`) | Pagination + de-dup, stable stopping conditions, every filter combination, real-fixture field extraction | Real result counts, real filter narrowing |
| `detail` (`fetch_detail`, dealer/image/posting-meta extraction) | Every extractor, both a new-car and a used-car real fixture | Real detail fetch |
| `http` (`get`, retry/backoff, challenge detection) | Retry-then-succeed and exhausted-retries paths for 429/5xx/connection errors, no retry on 4xx, Cloudflare-challenge detection | — |
| `flatten`/`io` (`flatten_listing`, `order_fieldnames`, `save_csv`/`save_json`) | Every branch (nested dicts, lists, missing/heterogeneous fields), unicode, empty input | Implicitly, via real data |
| `orchestrate` (`scrape()`) | Range validation, domain/category validation, catalog-to-search-to-detail wiring, price sort, unknown make/model errors | Full real pipeline, with and without `--detail` |
| `cli` (`run_cli`/`main`) | Every flag, default vs. custom output filenames, all exit-code paths | Real subprocess run, real error exit code |

The unit suite covers 100% of `src/autolina_scraper/`.
