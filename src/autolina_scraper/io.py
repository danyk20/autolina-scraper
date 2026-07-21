"""Writers for the two output formats: CSV (flattened rows) and JSON (raw listings)."""

from __future__ import annotations

import csv
import json
from typing import Any

from autolina_scraper.flatten import order_fieldnames


def save_csv(rows: list[dict[str, str]], path: str) -> None:
    """Write *rows* (already flattened, e.g. via :func:`~autolina_scraper.flatten.flatten_listing`)
    to *path*. The column union across all rows is used, pinned columns first;
    missing values in any given row become an empty cell.
    """
    if not rows:
        open(path, "w", encoding="utf-8").close()
        return
    fieldnames = order_fieldnames({key for row in rows for key in row})
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(rows)


def save_json(listings: list[dict[str, Any]], path: str) -> None:
    """Write the raw (unflattened) listing dicts to *path* as a JSON array."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(listings, handle, ensure_ascii=False, indent=2)
