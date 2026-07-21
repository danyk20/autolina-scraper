"""Paginated search-result collection.

Fetches ``/{make}/{model}`` and its ``/page/{n}`` continuations and parses each
listing card (``.car-row``) directly out of the rendered HTML — see
:mod:`autolina_scraper.htmlparse` for the shared parsing primitives and
:mod:`autolina_scraper.detail` for why DOM parsing (not the site's UA-gated
internal JSON cache) is this project's primary data source.

Confirmed against the live site:

* Range filters are a single ``min-max`` string per field, either side optional
  (``price=30000-``, ``price=-20000``, ``price=10000-20000``): ``price``,
  ``mileage``, and ``date`` (first-registration year — matches the app's own
  ``FirstRegDate -> "date"`` route-key mapping, found in its JS bundle).
* Pagination is ``/{make}/{model}/page/{n}`` (page 1 has no suffix).

Listings are de-duplicated by ``carId`` across pages as a safety net, and the
loop stops as soon as a page yields zero new ids — the same "boosted listing
can shift pagination" risk the AutoScout24 reference solved for its API
applies here too, since result order isn't guaranteed stable between requests.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import requests
from selectolax.parser import HTMLParser, Node

from autolina_scraper import htmlparse, http
from autolina_scraper.catalog import BASE_URL

logger = logging.getLogger("autolina_scraper")

_RESULT_COUNT_RE = re.compile(r"([\d']+)\s*Autos")
_LISTING_HREF_RE = re.compile(r"/auto/([a-z0-9-]+)/(\d+)$")
_DIGITS_RE = re.compile(r"\d+")
_YEAR_RE = re.compile(r"^(19|20)\d{2}$")

_FUEL_TYPES = {"Benzin", "Diesel", "Elektro", "Hybrid", "Erdgas", "Wasserstoff"}
_TRANSMISSIONS = {"Automatik", "Handschaltung"}
_CONDITIONS = {"Neuwagen", "Gebraucht", "Occasion", "Vorführwagen", "Jahreswagen", "Youngtimer"}


def _range_param(low: int | None, high: int | None) -> str | None:
    if low is None and high is None:
        return None
    return f"{low if low is not None else ''}-{high if high is not None else ''}"


def build_query(
    *,
    price_from: int | None = None,
    price_to: int | None = None,
    mileage_from: int | None = None,
    mileage_to: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict[str, str]:
    """Build the confirmed range-filter query params, omitting unset filters."""
    params: dict[str, str] = {}
    for key, value in (
        ("price", _range_param(price_from, price_to)),
        ("mileage", _range_param(mileage_from, mileage_to)),
        ("date", _range_param(year_from, year_to)),
    ):
        if value is not None:
            params[key] = value
    return params


def fetch_listings(
    session: requests.Session,
    make_key: str,
    model_key: str,
    *,
    query: dict[str, str] | None = None,
    delay: float = 1.0,
    verbose: bool = True,
    max_results: int | None = None,
) -> tuple[int, list[dict[str, Any]]]:
    """Return ``(reported_total, deduplicated_listings)`` for a make/model search.

    *reported_total* is always the site's true full count, even when
    *max_results* caps how many listings are actually collected — pagination
    stops as soon as enough unique listings are in hand, so a narrow
    ``max_results`` also saves search-phase requests, not just the caller's
    own downstream (typically detail-fetch) work.
    """
    query = query or {}
    listings_by_id: dict[int, dict[str, Any]] = {}
    reported_total = 0
    page = 1
    capped = False

    while True:
        url = f"{BASE_URL}/{make_key}/{model_key}" + (f"/page/{page}" if page > 1 else "")
        response = http.get(session, url, params=query, delay=delay)
        tree = htmlparse.parse(response.text)
        cards = tree.css(".car-row")
        if not cards:
            break

        if page == 1:
            reported_total = _parse_result_count(tree)

        new_count = 0
        for card in cards:
            listing = _parse_card(card)
            if listing is None or listing["carId"] in listings_by_id:
                continue
            listings_by_id[listing["carId"]] = listing
            new_count += 1

        if verbose:
            logger.info(
                "page %d: %d listings (%d/%d unique so far)",
                page,
                len(cards),
                len(listings_by_id),
                reported_total,
            )

        if max_results is not None and len(listings_by_id) >= max_results:
            capped = True
            break
        if new_count == 0 or len(listings_by_id) >= reported_total:
            break
        page += 1

    if not capped and len(listings_by_id) != reported_total:
        logger.warning(
            "collected %d unique listings but the site reported %d — "
            "pagination likely shifted while scraping (promoted listings can "
            "reshuffle between requests)",
            len(listings_by_id),
            reported_total,
        )

    listings = list(listings_by_id.values())
    if max_results is not None:
        listings = listings[:max_results]
    return reported_total, listings


def _parse_result_count(tree: HTMLParser) -> int:
    h1_text = htmlparse.clean_text(tree.css_first("h1"))
    match = _RESULT_COUNT_RE.search(h1_text)
    if match is None:
        return 0
    return int(match.group(1).replace("'", ""))


def _parse_card(card: Node) -> dict[str, Any] | None:
    link = card.css_first("a.url-wrapper")
    href = (link.attributes.get("href") or "") if link else ""
    match = _LISTING_HREF_RE.search(href)
    if match is None:
        return None
    slug, car_id = match.group(1), int(match.group(2))

    make_model_titles = [
        span.attributes.get("title") for span in card.css(".make-model span[title]")
    ]
    make = make_model_titles[0] if len(make_model_titles) > 0 else None
    model_type = make_model_titles[1] if len(make_model_titles) > 1 else None

    price = _parse_int(htmlparse.clean_text(card.css_first(".price-container .price")))
    previous_price = _parse_int(
        htmlparse.clean_text(card.css_first(".price-before-discount"))
    )

    year: int | None = None
    mileage: int | None = None
    power: int | None = None
    transmission: str | None = None
    fuel: str | None = None
    condition: str | None = None
    color: str | None = None
    for child in card.css(".vehicle-data > div"):
        text = htmlparse.clean_text(child)
        if not text:
            continue
        if _YEAR_RE.fullmatch(text):
            year = int(text)
        elif "km" in text:
            mileage = _parse_int(text)
        elif "PS" in text:
            power = _parse_int(text)
        elif text in _TRANSMISSIONS:
            transmission = text
        elif text in _FUEL_TYPES:
            fuel = text
        elif text in _CONDITIONS:
            condition = text
        else:
            color = text

    image_node = card.css_first("img.first-img")
    image_url = image_node.attributes.get("src") if image_node else None
    if image_url:
        image_url = image_url.split("?")[0]

    return {
        "carId": car_id,
        "slug": slug,
        "url": f"{BASE_URL}/auto/{slug}/{car_id}",
        "make": make,
        "modelType": model_type,
        "price": price,
        "previousPrice": previous_price,
        "constructionYear": year,
        "mileage": mileage,
        "powerOutput": power,
        # Named to match the equivalent detail-page label columns
        # (autolina_scraper.htmlparse.slugify_label), so detail mode refines
        # these in place instead of creating parallel columns.
        "getriebeart": transmission,
        "treibstoff": fuel,
        "fahrzeugzustand": condition,
        "farbe_aussen_innen": color,
        "isNew": card.css_first(".new") is not None,
        "isPremium": card.css_first(".premium") is not None,
        "location": htmlparse.clean_text(card.css_first(".region-or-title")),
        "imageUrl": image_url,
    }


def _parse_int(text: str) -> int | None:
    digits = "".join(_DIGITS_RE.findall(text))
    return int(digits) if digits else None
