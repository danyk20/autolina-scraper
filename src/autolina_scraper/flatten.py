"""Flatten a nested listing dict into CSV-ready columns.

Rules (mirrors the flattening conventions documented for the AutoScout24
reference, adapted to this project's field names):

* Nested objects become ``parent_child`` columns, e.g. ``dealer.email`` ->
  ``dealer_email``, ``warranty.warrantyText`` -> ``warranty_warrantyText``.
* Lists of scalars are joined into one semicolon-separated cell.
* Lists of dicts are scalarized one item at a time — using a recognisable
  "title" field if the dict has one (``equipmentTitle``, ``name``, ...), falling
  back to a compact JSON representation otherwise — then joined the same way.
* ``None`` becomes an empty string; everything else becomes ``str(value)``.
"""

from __future__ import annotations

import json
from typing import Any, Final

_TITLE_CANDIDATES: Final = ("equipmentTitle", "name", "feature", "key", "url", "title")

# Columns pinned first, in this order; everything else is sorted alphabetically after.
PINNED_COLUMNS: Final = (
    "carId",
    "url",
    "make",
    "modelType",
    "adTitle",
    "price",
    "previousPrice",
    "neupreis",
    "constructionYear",
    "erstzulassung",
    "mileage",
    "fahrzeugzustand",
    "treibstoff",
    "getriebeart",
    "antrieb",
    "powerOutput",
    "farbe_aussen_innen",
    "dealer_name",
    "dealer_address",
    "dealer_phone",
)


def flatten_listing(listing: dict[str, Any], _parent_key: str = "") -> dict[str, str]:
    """Flatten one listing dict into a single-level ``{column: value}`` mapping."""
    flat: dict[str, str] = {}
    for key, value in listing.items():
        full_key = f"{_parent_key}_{key}" if _parent_key else key
        if isinstance(value, dict):
            flat.update(flatten_listing(value, full_key))
        elif isinstance(value, list):
            flat[full_key] = _scalarize_list(value)
        elif value is None:
            flat[full_key] = ""
        else:
            flat[full_key] = str(value)
    return flat


def _scalarize_list(items: list[Any]) -> str:
    parts: list[str] = []
    for item in items:
        if isinstance(item, dict):
            parts.append(_scalarize_dict(item))
        elif isinstance(item, list):
            parts.append(_scalarize_list(item))
        elif item is not None:
            parts.append(str(item))
    return "; ".join(parts)


def _scalarize_dict(item: dict[str, Any]) -> str:
    for candidate in _TITLE_CANDIDATES:
        if candidate in item and item[candidate]:
            return str(item[candidate])
    return json.dumps(item, ensure_ascii=False, sort_keys=True)


def order_fieldnames(fieldnames: set[str]) -> list[str]:
    """Pinned columns first (only the ones actually present), then the rest,
    alphabetically.
    """
    pinned = [name for name in PINNED_COLUMNS if name in fieldnames]
    rest = sorted(fieldnames - set(pinned))
    return pinned + rest
