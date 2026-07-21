"""The public ``scrape()`` entry point: wires catalog -> search -> detail -> flatten."""

from __future__ import annotations

import logging
from typing import Any

import requests

from autolina_scraper import catalog, flatten, http, search
from autolina_scraper import detail as detail_mod
from autolina_scraper.models import ScrapeResult

logger = logging.getLogger("autolina_scraper")

_SUPPORTED_DOMAIN = "ch"
_SUPPORTED_CATEGORY = "car"


def scrape(
    make: str,
    model: str,
    *,
    domain: str = "ch",
    category: str = "car",
    detail: bool = True,
    price_from: int | None = None,
    price_to: int | None = None,
    mileage_from: int | None = None,
    mileage_to: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    delay: float = 1.0,
    verbose: bool = True,
    session: requests.Session | None = None,
) -> ScrapeResult:
    """Fetch every autolina.ch listing for *make*/*model*, optionally filtered.

    Kept signature-compatible with the AutoScout24 reference's ``scrape()`` — see
    ``docs/REFERENCE.md`` for the full contract and the differences section for
    what's deliberately not the same (no ``category="motorcycle"``, no ``domain``
    other than ``"ch"`` — autolina.ch doesn't have either).

    Raises ``ValueError`` immediately, before any network call, for an inverted
    range or an unsupported ``domain``/``category``; raises ``ValueError`` if
    ``make``/``model`` can't be resolved (listing valid models for an unknown
    model); raises ``requests`` exceptions on unrecoverable network errors.
    """
    if domain != _SUPPORTED_DOMAIN:
        raise ValueError(f"unsupported domain {domain!r} — autolina.ch only has 'ch'")
    if category != _SUPPORTED_CATEGORY:
        raise ValueError(
            f"unsupported category {category!r} — autolina.ch has no motorcycles, "
            "only 'car' is supported"
        )
    _validate_range(price_from, price_to, "price")
    _validate_range(mileage_from, mileage_to, "mileage")
    _validate_range(year_from, year_to, "year")

    session = session or http.new_session()

    make_slugs = catalog.fetch_make_slugs(session, delay=delay)
    try:
        resolved_make = catalog.resolve_make(make, make_slugs)
    except ValueError:
        # autolina.ch's sitemap can lag behind the live site (confirmed: newly
        # added makes/models can be missing from it) — fall back to a live
        # probe before concluding the make genuinely doesn't exist.
        probed_make = catalog.probe_make(session, make, delay=delay)
        if probed_make is None:
            raise
        if verbose:
            logger.info(
                "make %r not in the sitemap catalog, but resolved live", probed_make.key
            )
        resolved_make = probed_make

    model_slugs_by_make = catalog.fetch_make_model_slugs(session, delay=delay)
    model_slugs = model_slugs_by_make.get(resolved_make.key, [])
    try:
        if not model_slugs:
            raise ValueError(f"make {resolved_make.key!r} has no known models in the sitemap")
        resolved_model = catalog.resolve_model(model, resolved_make.key, model_slugs)
    except ValueError:
        probed_model = catalog.probe_model(
            session, model, resolved_make.key, resolved_make.name, delay=delay
        )
        if probed_model is None:
            raise
        if verbose:
            logger.info(
                "model %r not in the sitemap catalog, but resolved live", probed_model.key
            )
        resolved_model = probed_model

    query = search.build_query(
        price_from=price_from,
        price_to=price_to,
        mileage_from=mileage_from,
        mileage_to=mileage_to,
        year_from=year_from,
        year_to=year_to,
    )
    total, listings = search.fetch_listings(
        session,
        resolved_make.key,
        resolved_model.key,
        query=query,
        delay=delay,
        verbose=verbose,
    )

    # "make" comes straight from the listing's own title attribute (e.g.
    # "MERCEDES-BENZ") and is more authoritative than the slug-derived
    # heuristic for names that don't round-trip cleanly through slugify.
    # There's no equivalent plain "model" field to prefer over
    # resolved_model.name — search cards only carry the per-listing trim
    # name (modelType, e.g. "Tiguan R-Line"), not the stable base model.
    make_name = resolved_make.name
    if listings:
        make_name = listings[0].get("make") or make_name
    model_name = resolved_model.name

    default_slug = f"{resolved_make.key}-{resolved_model.key}"
    for listing in listings:
        listing["url"] = detail_mod.listing_url(listing.get("slug", default_slug), listing["carId"])

    if detail:
        listings = [
            _fetch_one_detail(session, listing, index, len(listings), delay=delay, verbose=verbose)
            for index, listing in enumerate(listings, start=1)
        ]

    listings.sort(key=_price_sort_key)
    rows = [flatten.flatten_listing(listing) for listing in listings]

    return ScrapeResult(
        make_key=resolved_make.key,
        make_name=make_name,
        model_key=resolved_model.key,
        model_name=model_name,
        category=category,
        total_elements=total,
        listings=listings,
        rows=rows,
        domain=domain,
    )


def _fetch_one_detail(
    session: requests.Session,
    listing: dict[str, Any],
    index: int,
    total: int,
    *,
    delay: float,
    verbose: bool,
) -> dict[str, Any]:
    if verbose:
        logger.info("detail %d/%d: %s", index, total, listing["url"])
    slug = listing.get("slug", listing["url"].rsplit("/", 2)[-2])
    record = detail_mod.fetch_detail(session, slug, listing["carId"], delay=delay)
    return {**listing, **record, "url": listing["url"]}


def _price_sort_key(listing: dict[str, Any]) -> tuple[int, float]:
    price = listing.get("price")
    return (0, float(price)) if isinstance(price, (int, float)) else (1, 0.0)


def _validate_range(low: int | None, high: int | None, name: str) -> None:
    if low is not None and high is not None and low > high:
        raise ValueError(f"{name}_from ({low}) must be <= {name}_to ({high})")
