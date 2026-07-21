"""Make/model catalog, sourced from autolina.ch's own published sitemap.

autolina.ch has no ``/v1/makes``-style API to enumerate makes and models (unlike
AutoScout24). Instead, it publishes its full make and make/model landing-page
catalog as an SEO sitemap (``robots.txt`` points at it directly), which is exactly
the set of clean, crawlable URLs the rest of this library fetches anyway:

* ``sitemap/general1.xml.gz`` — one ``<loc>`` per make, e.g. ``/vw``
* ``sitemap/model1.xml.gz`` — one ``<loc>`` per make/model pair, e.g. ``/vw/tiguan``

Display names (``VW``, `"TIGUAN"``, ...) aren't in the sitemap — those come back
authoritatively in every search result (``makeName``/``modelName`` fields), so
this module only needs to resolve a user-supplied make/model into the URL slug
pair used to build every subsequent request.

**The sitemap can lag behind the live site** — confirmed: Tesla's Model Y has
real listings live but isn't in ``model1.xml.gz``. So `resolve_make`/
`resolve_model` are pure, offline, sitemap-only lookups (fast, and unit
testable without a network); `probe_make`/`probe_model` are a live fallback
callers should try when the pure lookup fails, before concluding the make/model
genuinely doesn't exist — see `autolina_scraper.orchestrate.scrape`.
"""

from __future__ import annotations

import gzip
import re
from dataclasses import dataclass
from xml.etree import ElementTree

import requests

from autolina_scraper import htmlparse, http

BASE_URL = "https://www.autolina.ch"
_SITEMAP_MAKES = f"{BASE_URL}/sitemap/general1.xml.gz"
_SITEMAP_MODELS = f"{BASE_URL}/sitemap/model1.xml.gz"
_LOC_TAG = "{http://www.sitemaps.org/schemas/sitemap/0.9}loc"


@dataclass(frozen=True, slots=True)
class ResolvedMake:
    key: str
    name: str


@dataclass(frozen=True, slots=True)
class ResolvedModel:
    key: str
    name: str


def slug_to_display_name(slug: str) -> str:
    """Best-effort display name for a slug, e.g. ``"alfa-romeo"`` -> ``"ALFA ROMEO"``.

    Used only as a fallback label; real scrapes overwrite it with the authoritative
    ``makeName``/``modelName`` from the first matching listing.
    """
    return slug.replace("-", " ").upper()


def _fetch_sitemap_slugs(session: requests.Session, url: str, *, delay: float) -> list[str]:
    response = http.get(session, url, delay=delay)
    xml_bytes = gzip.decompress(response.content)
    root = ElementTree.fromstring(xml_bytes)
    slugs = []
    for loc in root.iter(_LOC_TAG):
        if not loc.text:
            continue
        path = loc.text.removeprefix(BASE_URL).strip("/")
        slugs.append(path)
    return slugs


def fetch_make_slugs(session: requests.Session, *, delay: float = 1.0) -> list[str]:
    """All make slugs, e.g. ``["vw", "audi", ...]``, from ``general1.xml.gz``."""
    slugs = _fetch_sitemap_slugs(session, _SITEMAP_MAKES, delay=delay)
    return sorted({slug for slug in slugs if slug and "/" not in slug})


def fetch_make_model_slugs(
    session: requests.Session, *, delay: float = 1.0
) -> dict[str, list[str]]:
    """``{make_slug: [model_slug, ...]}`` for every make, from ``model1.xml.gz``."""
    slugs = _fetch_sitemap_slugs(session, _SITEMAP_MODELS, delay=delay)
    by_make: dict[str, list[str]] = {}
    for path in slugs:
        if "/" not in path:
            continue
        make_slug, _, model_slug = path.partition("/")
        by_make.setdefault(make_slug, []).append(model_slug)
    return by_make


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def resolve_make(make: str, make_slugs: list[str]) -> ResolvedMake:
    """Resolve a user-supplied make (name or slug, case-insensitive) to its slug.

    Tries an exact slug match first, then substring fallback, matching the
    reference project's forgiving ``resolve_make_key`` UX.
    """
    normalized = _normalize(make)
    if normalized in make_slugs:
        return ResolvedMake(key=normalized, name=slug_to_display_name(normalized))

    matches = [slug for slug in make_slugs if normalized in slug or slug in normalized]
    if len(matches) == 1:
        return ResolvedMake(key=matches[0], name=slug_to_display_name(matches[0]))

    raise ValueError(
        f"unknown make {make!r}"
        + (f" — did you mean one of: {', '.join(sorted(matches))}?" if matches else "")
    )


def resolve_model(model: str, make_key: str, model_slugs: list[str]) -> ResolvedModel:
    """Resolve a user-supplied model (name or slug) to its slug within *make_key*."""
    normalized = _normalize(model)
    if normalized in model_slugs:
        return ResolvedModel(key=normalized, name=slug_to_display_name(normalized))

    matches = [slug for slug in model_slugs if normalized in slug or slug in normalized]
    if len(matches) == 1:
        return ResolvedModel(key=matches[0], name=slug_to_display_name(matches[0]))

    valid = ", ".join(sorted(model_slugs))
    hint = f" — did you mean one of: {', '.join(sorted(matches))}?" if matches else ""
    raise ValueError(
        f"unknown model {model!r} for make {make_key!r}{hint}\nvalid models: {valid}"
    )


def probe_make(session: requests.Session, make: str, *, delay: float = 1.0) -> ResolvedMake | None:
    """Live fallback for when *make* isn't in the (possibly stale) sitemap.

    Requests ``/{candidate-slug}`` directly and accepts it only if the
    rendered page is genuinely scoped to that make — autolina.ch's router
    falls back to its generic, unscoped catalog page for a made-up slug
    rather than 404ing, so a naive "did it return 200" check isn't enough.
    """
    candidate_slug = _normalize(make)
    display_name = slug_to_display_name(candidate_slug)
    response = http.get(session, f"{BASE_URL}/{candidate_slug}", delay=delay)
    if _renders_as(response.text, display_name):
        return ResolvedMake(key=candidate_slug, name=display_name)
    return None


def probe_model(
    session: requests.Session,
    model: str,
    make_key: str,
    make_display_name: str,
    *,
    delay: float = 1.0,
) -> ResolvedModel | None:
    """Live fallback for when *model* isn't in the (possibly stale) sitemap.

    Same idea as `probe_make`: request ``/{make_key}/{candidate-slug}``
    directly and only accept it if the page is genuinely scoped to that
    make/model — this correctly accepts a real model with zero current
    listings (e.g. a rare model) while rejecting a typo, since an invalid
    combination falls back to a generic, unscoped page rather than 404ing.
    """
    candidate_slug = _normalize(model)
    response = http.get(session, f"{BASE_URL}/{make_key}/{candidate_slug}", delay=delay)
    if _renders_as(response.text, make_display_name):
        return ResolvedModel(key=candidate_slug, name=slug_to_display_name(candidate_slug))
    return None


def _renders_as(html: str, expected_prefix: str) -> bool:
    tree = htmlparse.parse(html)
    h1_text = htmlparse.clean_text(tree.css_first("h1"))
    return h1_text.upper().startswith(expected_prefix.upper())
