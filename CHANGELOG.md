# Changelog

All notable changes to this project are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

[Unreleased]: https://github.com/danyk20/autolina-scraper/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/danyk20/autolina-scraper/releases/tag/v0.1.0
