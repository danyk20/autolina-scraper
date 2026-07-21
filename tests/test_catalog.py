from __future__ import annotations

import gzip

import pytest
import responses

from autolina_scraper import catalog, http
from tests.conftest import read_fixture_bytes


def test_slug_to_display_name() -> None:
    assert catalog.slug_to_display_name("alfa-romeo") == "ALFA ROMEO"
    assert catalog.slug_to_display_name("vw") == "VW"


@responses.activate
def test_fetch_make_slugs_parses_gzipped_sitemap() -> None:
    responses.add(
        responses.GET,
        catalog._SITEMAP_MAKES,
        body=read_fixture_bytes("sitemap_general1.xml.gz"),
        status=200,
    )
    session = http.new_session()
    slugs = catalog.fetch_make_slugs(session, delay=0)
    assert "vw" in slugs
    assert "porsche" in slugs
    assert all("/" not in slug for slug in slugs)


@responses.activate
def test_fetch_make_model_slugs_groups_by_make() -> None:
    responses.add(
        responses.GET,
        catalog._SITEMAP_MODELS,
        body=read_fixture_bytes("sitemap_model1.xml.gz"),
        status=200,
    )
    session = http.new_session()
    by_make = catalog.fetch_make_model_slugs(session, delay=0)
    assert "tiguan" in by_make["vw"]
    assert "model-s" in by_make["tesla"]


def test_resolve_make_exact_slug_match() -> None:
    resolved = catalog.resolve_make("vw", ["vw", "audi", "bmw"])
    assert resolved.key == "vw"
    assert resolved.name == "VW"


def test_resolve_make_is_case_insensitive() -> None:
    resolved = catalog.resolve_make("VW", ["vw", "audi"])
    assert resolved.key == "vw"


def test_resolve_make_substring_fallback() -> None:
    resolved = catalog.resolve_make("alfa", ["alfa-romeo", "audi"])
    assert resolved.key == "alfa-romeo"


def test_resolve_make_unknown_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unknown make"):
        catalog.resolve_make("totallyfake", ["vw", "audi"])


def test_resolve_model_exact_match() -> None:
    resolved = catalog.resolve_model("tiguan", "vw", ["tiguan", "golf", "polo"])
    assert resolved.key == "tiguan"


def test_resolve_model_unknown_lists_valid_models() -> None:
    with pytest.raises(ValueError, match="valid models: golf, polo, tiguan"):
        catalog.resolve_model("fake-model", "vw", ["tiguan", "golf", "polo"])


def test_resolve_model_substring_fallback() -> None:
    resolved = catalog.resolve_model("Golf 8", "vw", ["golf", "golf-plus", "polo"])
    assert resolved.key == "golf"


def test_resolve_make_unknown_with_no_matches_omits_suggestion_hint() -> None:
    with pytest.raises(ValueError) as exc_info:
        catalog.resolve_make("zzz-nothing-like-it", ["vw", "audi"])
    assert "did you mean" not in str(exc_info.value)


def test_resolve_make_ambiguous_substring_matches_raises() -> None:
    with pytest.raises(ValueError, match="unknown make"):
        catalog.resolve_make("a", ["audi", "alfa-romeo"])


def test_resolve_model_ambiguous_substring_matches_raises() -> None:
    with pytest.raises(ValueError, match="valid models"):
        catalog.resolve_model("golf", "vw", ["golf-plus", "golf-sportsvan"])


@responses.activate
def test_fetch_make_slugs_skips_locs_with_no_text() -> None:
    xml = (
        '<?xml version="1.0"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<url><loc></loc></url>"
        "<url><loc>https://www.autolina.ch/vw</loc></url>"
        "</urlset>"
    )
    responses.add(
        responses.GET, catalog._SITEMAP_MAKES, body=gzip.compress(xml.encode())
    )
    slugs = catalog.fetch_make_slugs(http.new_session(), delay=0)
    assert slugs == ["vw"]


@responses.activate
def test_fetch_make_model_slugs_skips_make_only_paths() -> None:
    xml = (
        '<?xml version="1.0"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<url><loc>https://www.autolina.ch/vw</loc></url>"
        "<url><loc>https://www.autolina.ch/vw/tiguan</loc></url>"
        "</urlset>"
    )
    responses.add(
        responses.GET, catalog._SITEMAP_MODELS, body=gzip.compress(xml.encode())
    )
    by_make = catalog.fetch_make_model_slugs(http.new_session(), delay=0)
    assert by_make == {"vw": ["tiguan"]}


# --- live-probe fallback, for when the sitemap lags behind the live site ---
# (confirmed real: Tesla's Model Y has live listings but was missing from
# model1.xml.gz)

_SCOPED_PAGE = "<html><body><h1>TESLA MODEL Y Occasion - 44 Autos</h1></body></html>"
_UNSCOPED_PAGE = "<html><body><h1>Occasion oder Neuwagen kaufen - 97'370 Autos</h1></body></html>"


@responses.activate
def test_probe_make_accepts_a_page_genuinely_scoped_to_that_make() -> None:
    responses.add(
        responses.GET,
        "https://www.autolina.ch/tesla",
        body="<html><body><h1>TESLA Occasion - 174 Autos</h1></body></html>",
    )
    resolved = catalog.probe_make(http.new_session(), "tesla", delay=0)
    assert resolved is not None
    assert resolved.key == "tesla"
    assert resolved.name == "TESLA"


@responses.activate
def test_probe_make_rejects_the_generic_unscoped_fallback_page() -> None:
    responses.add(
        responses.GET, "https://www.autolina.ch/totallyfake", body=_UNSCOPED_PAGE
    )
    assert catalog.probe_make(http.new_session(), "totallyfake", delay=0) is None


@responses.activate
def test_probe_model_accepts_a_page_genuinely_scoped_to_that_make_and_model() -> None:
    responses.add(
        responses.GET, "https://www.autolina.ch/tesla/model-y", body=_SCOPED_PAGE
    )
    resolved = catalog.probe_model(
        http.new_session(), "Model Y", "tesla", "TESLA", delay=0
    )
    assert resolved is not None
    assert resolved.key == "model-y"
    assert resolved.name == "MODEL Y"


@responses.activate
def test_probe_model_accepts_a_real_model_with_zero_current_listings() -> None:
    responses.add(
        responses.GET,
        "https://www.autolina.ch/tesla/roadster",
        body="<html><body><h1>TESLA ROADSTER Occasion - 0 Autos</h1></body></html>",
    )
    resolved = catalog.probe_model(
        http.new_session(), "roadster", "tesla", "TESLA", delay=0
    )
    assert resolved is not None
    assert resolved.key == "roadster"


@responses.activate
def test_probe_model_rejects_a_typo_that_falls_back_to_the_generic_page() -> None:
    responses.add(
        responses.GET, "https://www.autolina.ch/tesla/not-a-real-model", body=_UNSCOPED_PAGE
    )
    resolved = catalog.probe_model(
        http.new_session(), "not-a-real-model", "tesla", "TESLA", delay=0
    )
    assert resolved is None


@responses.activate
def test_probe_model_rejects_a_body_type_filter_page_misidentified_as_a_model() -> None:
    # /tesla/kombi is a real, 200-returning route (a body-type filter link),
    # but it's not a model — and it renders the same generic unscoped page as
    # a typo, not a "TESLA KOMBI" page, so it's correctly rejected too.
    responses.add(
        responses.GET, "https://www.autolina.ch/tesla/kombi", body=_UNSCOPED_PAGE
    )
    resolved = catalog.probe_model(http.new_session(), "kombi", "tesla", "TESLA", delay=0)
    assert resolved is None
