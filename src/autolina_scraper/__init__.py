"""Free, keyless scraper & library for autolina.ch vehicle listings."""

from autolina_scraper.detail import fetch_detail, visit_all_listings
from autolina_scraper.models import ScrapeResult
from autolina_scraper.orchestrate import scrape
from autolina_scraper.search import fetch_listings as search_listings

__version__ = "0.2.0"

__all__ = [
    "scrape",
    "search_listings",
    "fetch_detail",
    "visit_all_listings",
    "ScrapeResult",
    "__version__",
]
