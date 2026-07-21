"""Free, keyless scraper & library for autolina.ch vehicle listings."""

from autolina_scraper.models import ScrapeResult
from autolina_scraper.orchestrate import scrape

__version__ = "0.1.0"

__all__ = ["scrape", "ScrapeResult", "__version__"]
