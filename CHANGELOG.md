# Changelog

All notable changes to this project are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.0] - 2026-07-21

### Changed

- `listings`/`rows` are now always ordered **newest-first**, by `carId`
  descending, instead of the previous price-ascending order. `carId` is an
  auto-incrementing primary key, so higher id reliably means posted more
  recently; autolina.ch's search summary has no separate "date posted" field
  to sort by instead, and its own default result order isn't date-sorted (it
  mixes in "TOP"/boosted-listing placement).
- As a consequence, `max_results` now guarantees "the newest N" correctly:
  since that requires seeing every listing's `carId` before deciding which
  are newest, the search phase always pages through the full result set
  first — the early-pagination-stop optimization added in 0.2.0 traded
  correctness for search-phase request savings and has been reverted. The
  detail-visit phase (the dominant cost in the original reported case: up to
  772 requests) is still fully capped, unaffected by this change.

## [0.2.0] - 2026-07-21

### Added

- `max_results` on `scrape()`: caps how many listings are collected and
  detail-visited, without affecting `total_elements` (the site's true full
  count). Pagination itself stops early once enough candidates are in hand,
  saving search-phase requests too, not just detail-phase ones.
- `search_listings()`/`fetch_detail()`/`visit_all_listings()` now importable
  directly from the top-level `autolina_scraper` package — the search and
  detail phases `scrape()` composes internally, exposed standalone so callers
  can sort/filter/slice the candidate list themselves (e.g. cheapest first)
  before choosing which listings are worth a detail visit. Mirrors the
  AutoScout24 reference's own `search_listings()`/`visit_all_listings()` split.
- `--max-results` CLI flag.

### Fixed

- Detail parsing was silently missing the seller's free-text description
  (`beschreibung`) and the ad's own headline (`adTitle`) — both are now
  extracted from `.description-row`/`.title-row h2`. The description in
  particular is common on private-seller listings (rarer on dealer-posted
  ones, which is why earlier spot-checks during development missed it).

## [0.1.0] - 2026-07-21

### Added

- Initial release: `scrape()` library function and `autolina-scraper` CLI,
  API-compatible with the `autoscout24-scraper` reference project.
- Make/model catalog resolution from autolina.ch's published sitemap.
- Paginated search with `price`/`mileage`/`date` (year) range filters,
  confirmed live against autolina.ch's own query parameters.
- Full per-listing detail parsing: specs, energy data, standard/optional
  equipment, dealer/seller contact info, image gallery, posted-date/view-count.
- CSV/JSON export via `ScrapeResult.to_csv()`/`.to_json()`.
- Retry with exponential backoff + jitter; explicit detection of (and refusal
  to bypass) Cloudflare bot-detection challenges.
- 100% unit test coverage against real saved HTML fixtures; e2e suite against
  the live site.
- Live-probe fallback (`catalog.probe_make`/`probe_model`) for when a make or
  model is missing from autolina.ch's sitemap (confirmed real: Tesla's Model Y
  has live listings but isn't in the site's own `model1.xml.gz`) — the sitemap
  lookup stays the fast/offline default, but an unresolved make/model is now
  double-checked live before being reported as unknown.

[Unreleased]: https://github.com/danyk20/autolina-scraper/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/danyk20/autolina-scraper/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/danyk20/autolina-scraper/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/danyk20/autolina-scraper/releases/tag/v0.1.0
