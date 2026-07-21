"""Per-listing detail fetch.

Fetches ``/auto/{slug}/{id}`` and parses the rendered page into a flat dict:
every ``.details-row``/``.sub-details-grid``/``.energy-data-row`` label-value
pair (specs, energy data, fuel/transmission/drivetrain/condition/colour — see
:mod:`autolina_scraper.htmlparse` for how these are extracted generically),
both equipment lists, the dealer/seller card, the image gallery, and the
posted-date/view-count line.
"""

from __future__ import annotations

import re
from typing import Any

import requests
from selectolax.parser import HTMLParser

from autolina_scraper import htmlparse, http
from autolina_scraper.catalog import BASE_URL

_ROW_SELECTOR = ".details-row, .sub-details-grid, .energy-data-row .row-container"
_IMAGE_NUMBER_RE = re.compile(r"_(\d+)\.jpg$")
_META_LINE_RE = re.compile(
    r"Dieses Inserat (?P<id>\d+) wurde am (?P<date>[\d.]+) aufgegeben oder "
    r"aktualisiert und wurde (?P<hits>\d+) mal besucht"
)


def listing_url(slug: str, car_id: int) -> str:
    """The public URL of a listing, e.g. ``https://www.autolina.ch/auto/vw-tiguan/123``."""
    return f"{BASE_URL}/auto/{slug}/{car_id}"


def fetch_detail(
    session: requests.Session,
    slug: str,
    car_id: int,
    *,
    delay: float = 1.0,
) -> dict[str, Any]:
    """Fetch and parse the full detail record for one listing."""
    url = listing_url(slug, car_id)
    response = http.get(session, url, delay=delay)
    html = response.text
    tree = htmlparse.parse(html)

    data: dict[str, Any] = {"carId": car_id, "url": url}

    for row in tree.css(_ROW_SELECTOR):
        for label, value in htmlparse.label_value_pairs(row).items():
            data[htmlparse.slugify_label(label)] = value

    for title, items in htmlparse.equipment_sections(tree).items():
        data[htmlparse.slugify_label(title)] = items

    dealer = _extract_dealer(tree)
    if dealer:
        data["dealer"] = dealer

    images = _extract_images(tree)
    if images:
        data["images"] = images

    data.update(_extract_posting_meta(html))
    return data


def _extract_dealer(tree: HTMLParser) -> dict[str, str]:
    card = tree.css_first("app-dealer-card.dealer-card-with-map") or tree.css_first(
        "app-dealer-card"
    )
    if card is None:
        return {}

    phone = ""
    for link in card.css("a"):
        href = link.attributes.get("href") or ""
        if href.startswith("tel:"):
            phone = href.removeprefix("tel:").strip()
            break

    location_link = card.css_first("a.location")
    infopage_link = card.css_first("a.all-cars")

    return {
        "name": htmlparse.clean_text(card.css_first(".name")),
        "address": htmlparse.clean_text(location_link),
        "mapsUrl": (location_link.attributes.get("href") or "") if location_link else "",
        "phone": phone,
        "infopageUrl": (infopage_link.attributes.get("href") or "") if infopage_link else "",
    }


def _extract_images(tree: HTMLParser) -> list[str]:
    by_number: dict[int, str] = {}
    for img in tree.css('img[src*="auto-bild"]'):
        src = (img.attributes.get("src") or "").split("?")[0]
        match = _IMAGE_NUMBER_RE.search(src)
        if match:
            by_number[int(match.group(1))] = src
    return [by_number[number] for number in sorted(by_number)]


def _extract_posting_meta(html: str) -> dict[str, str]:
    match = _META_LINE_RE.search(html)
    if match is None:
        return {}
    return {
        "lastUpdatedDateLabel": match.group("date"),
        "hitCount": match.group("hits"),
    }
