"""The top-level public API surface — what `from autolina_scraper import ...` exposes.

Kept as its own test module so a change to `__init__.py`'s exports (adding,
renaming, or accidentally dropping one) shows up as a single, obvious failure
here rather than being buried inside another module's tests.
"""

from __future__ import annotations

import autolina_scraper
from autolina_scraper import ScrapeResult, fetch_detail, scrape, search_listings, visit_all_listings
from autolina_scraper.detail import fetch_detail as detail_fetch_detail
from autolina_scraper.detail import visit_all_listings as detail_visit_all_listings
from autolina_scraper.orchestrate import scrape as orchestrate_scrape
from autolina_scraper.search import fetch_listings as search_fetch_listings


def test_top_level_scrape_is_the_orchestrate_function() -> None:
    assert scrape is orchestrate_scrape


def test_top_level_search_listings_is_search_fetch_listings() -> None:
    assert search_listings is search_fetch_listings


def test_top_level_fetch_detail_is_detail_fetch_detail() -> None:
    assert fetch_detail is detail_fetch_detail


def test_top_level_visit_all_listings_is_detail_visit_all_listings() -> None:
    assert visit_all_listings is detail_visit_all_listings


def test_scrape_result_is_exported() -> None:
    assert ScrapeResult.__name__ == "ScrapeResult"


def test_all_matches_the_documented_public_surface() -> None:
    assert set(autolina_scraper.__all__) == {
        "scrape",
        "search_listings",
        "fetch_detail",
        "visit_all_listings",
        "ScrapeResult",
        "__version__",
    }
