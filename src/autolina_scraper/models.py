"""The public return type of :func:`autolina_scraper.orchestrate.scrape`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autolina_scraper.io import save_csv, save_json


@dataclass
class ScrapeResult:
    """Everything a scrape produced, plus the identifiers it was resolved from.

    Kept API-compatible with the AutoScout24 reference's ``ScrapeResult``:
    ``len(rows) == len(listings) == total_elements`` always holds (barring
    ``detail=False``, where they still match — detail mode only adds fields, it
    never drops or adds listings).
    """

    make_key: str
    make_name: str
    model_key: str
    model_name: str
    category: str
    total_elements: int
    listings: list[dict[str, Any]]
    rows: list[dict[str, str]]
    domain: str

    def to_csv(self, path: str) -> None:
        save_csv(self.rows, path)

    def to_json(self, path: str) -> None:
        save_json(self.listings, path)
