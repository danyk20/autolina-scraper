from __future__ import annotations

import gzip

import pytest
import responses

from autolina_scraper import catalog
from autolina_scraper.orchestrate import scrape

_SITEMAP_NS = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'


def _sitemap_gz(paths: list[str]) -> bytes:
    locs = "".join(f"<url><loc>https://www.autolina.ch{p}</loc></url>" for p in paths)
    xml = f'<?xml version="1.0"?><urlset {_SITEMAP_NS}>{locs}</urlset>'
    return gzip.compress(xml.encode("utf-8"))


def _register_catalog(makes: list[str], models_by_make: dict[str, list[str]]) -> None:
    responses.add(
        responses.GET, catalog._SITEMAP_MAKES, body=_sitemap_gz([f"/{m}" for m in makes])
    )
    model_paths = [
        f"/{make}/{model}" for make, models in models_by_make.items() for model in models
    ]
    responses.add(responses.GET, catalog._SITEMAP_MODELS, body=_sitemap_gz(model_paths))


def _card_html(car_id: int, price: int) -> str:
    return f"""
    <app-car-row class="car-row">
      <a class="url-wrapper" href="/auto/vw-tiguan/{car_id}">
        <div class="make-model">
          <span title="VW">VW</span>
          <span title="Tiguan">Tiguan</span>
        </div>
        <div class="price-container"><div class="price">CHF {price}</div></div>
        <div class="vehicle-data">
          <div><span>2021</span></div>
          <div><span>50'000</span> <span class="small">km</span></div>
        </div>
        <div class="region-or-title"><span>8000 Zürich / ZH</span></div>
      </a>
    </app-car-row>
    """


def _search_page_html(count: int, cars: list[tuple[int, int]]) -> str:
    cards = "".join(_card_html(car_id, price) for car_id, price in cars)
    return f"<html><body><h1>{count} Autos in der Schweiz</h1>{cards}</body></html>"


def _detail_page_html(car_id: int, chassis_no: str) -> str:
    return f"""
    <html><body>
    <div class="details-row">
      <div><label>Fahrgestell-Nr.</label><span>{chassis_no}</span></div>
    </div>
    </body></html>
    """


# What autolina.ch actually serves for a made-up make/model slug: a 200,
# unscoped catalog page — not a 404 — confirmed live. probe_make/probe_model
# must reject this rather than treat any 200 as valid.
_GENERIC_FALLBACK_PAGE = (
    "<html><body><h1>Occasion oder Neuwagen kaufen - 97'370 Autos</h1></body></html>"
)


@responses.activate
def test_scrape_end_to_end_with_detail() -> None:
    _register_catalog(["vw"], {"vw": ["tiguan"]})
    responses.add(
        responses.GET,
        "https://www.autolina.ch/vw/tiguan",
        body=_search_page_html(1, [(42, 10000)]),
    )
    responses.add(
        responses.GET,
        "https://www.autolina.ch/auto/vw-tiguan/42",
        body=_detail_page_html(42, "ABC123"),
    )

    result = scrape("vw", "tiguan", delay=0)

    assert result.make_key == "vw"
    assert result.model_key == "tiguan"
    assert result.total_elements == 1
    assert len(result.listings) == len(result.rows) == 1
    assert result.listings[0]["fahrgestell_nr"] == "ABC123"
    assert result.listings[0]["url"] == "https://www.autolina.ch/auto/vw-tiguan/42"
    assert result.rows[0]["carId"] == "42"


@responses.activate
def test_scrape_no_detail_skips_detail_fetch() -> None:
    _register_catalog(["vw"], {"vw": ["tiguan"]})
    responses.add(
        responses.GET,
        "https://www.autolina.ch/vw/tiguan",
        body=_search_page_html(1, [(42, 10000)]),
    )

    result = scrape("vw", "tiguan", detail=False, delay=0)

    assert len(result.listings) == 1
    assert "fahrgestell_nr" not in result.listings[0]
    assert len(responses.calls) == 3  # 2 sitemaps + 1 search page, no detail visit


def test_scrape_rejects_inverted_price_range() -> None:
    with pytest.raises(ValueError, match="price_from"):
        scrape("vw", "tiguan", price_from=20_000, price_to=10_000)


def test_scrape_rejects_inverted_mileage_range() -> None:
    with pytest.raises(ValueError, match="mileage_from"):
        scrape("vw", "tiguan", mileage_from=50_000, mileage_to=10_000)


def test_scrape_rejects_inverted_year_range() -> None:
    with pytest.raises(ValueError, match="year_from"):
        scrape("vw", "tiguan", year_from=2022, year_to=2018)


def test_scrape_rejects_non_positive_max_results() -> None:
    with pytest.raises(ValueError, match="max_results"):
        scrape("vw", "tiguan", max_results=0)


@responses.activate
def test_scrape_max_results_caps_listings_and_only_detail_visits_those() -> None:
    _register_catalog(["vw"], {"vw": ["tiguan"]})
    responses.add(
        responses.GET,
        "https://www.autolina.ch/vw/tiguan",
        body=_search_page_html(5, [(1, 10000), (2, 20000), (3, 30000), (4, 40000), (5, 50000)]),
    )
    # max_results keeps the *newest* (highest carId) listings — 5 and 4, not 1 and 2.
    responses.add(
        responses.GET,
        "https://www.autolina.ch/auto/vw-tiguan/5",
        body=_detail_page_html(5, "ABC005"),
    )
    responses.add(
        responses.GET,
        "https://www.autolina.ch/auto/vw-tiguan/4",
        body=_detail_page_html(4, "ABC004"),
    )

    result = scrape("vw", "tiguan", max_results=2, delay=0)

    assert result.total_elements == 5  # true site total, unaffected by the cap
    assert len(result.listings) == len(result.rows) == 2
    assert [listing["carId"] for listing in result.listings] == [5, 4]  # newest first
    # only 2 detail requests fired, not 5 — the whole point of the cap
    detail_calls = [c for c in responses.calls if "/auto/" in c.request.url]
    assert len(detail_calls) == 2


def test_scrape_rejects_unsupported_domain() -> None:
    with pytest.raises(ValueError, match="domain"):
        scrape("vw", "tiguan", domain="de")


def test_scrape_rejects_unsupported_category() -> None:
    with pytest.raises(ValueError, match="category"):
        scrape("vw", "tiguan", category="motorcycle")


@responses.activate
def test_scrape_unknown_make_raises_after_live_probe_also_fails() -> None:
    _register_catalog(["vw"], {"vw": ["tiguan"]})
    responses.add(
        responses.GET,
        "https://www.autolina.ch/totallyfake",
        body=_GENERIC_FALLBACK_PAGE,
    )
    with pytest.raises(ValueError, match="unknown make"):
        scrape("totallyfake", "tiguan", delay=0)


@responses.activate
def test_scrape_make_with_no_known_models_raises_after_live_probe_also_fails() -> None:
    _register_catalog(["vw", "obscure-make"], {"vw": ["tiguan"]})
    responses.add(
        responses.GET,
        "https://www.autolina.ch/obscure-make/anything",
        body=_GENERIC_FALLBACK_PAGE,
    )
    with pytest.raises(ValueError, match="no known models"):
        scrape("obscure-make", "anything", delay=0)


@responses.activate
def test_scrape_unknown_model_lists_valid_models_after_live_probe_also_fails() -> None:
    _register_catalog(["vw"], {"vw": ["tiguan", "golf"]})
    responses.add(
        responses.GET,
        "https://www.autolina.ch/vw/not-a-model",
        body=_GENERIC_FALLBACK_PAGE,
    )
    with pytest.raises(ValueError, match="valid models"):
        scrape("vw", "not-a-model", delay=0)


@responses.activate
def test_scrape_falls_back_to_live_probe_for_a_model_missing_from_the_sitemap() -> None:
    # The real bug this guards against: Tesla Model Y has live listings but
    # was missing from autolina.ch's model1.xml.gz sitemap.
    _register_catalog(["tesla"], {"tesla": ["model-s", "model-x", "model-3"]})
    responses.add(
        responses.GET,
        "https://www.autolina.ch/tesla/model-y",
        body="<html><body><h1>TESLA MODEL Y Occasion - 44 Autos in der Schweiz</h1></body></html>",
    )
    responses.add(
        responses.GET,
        "https://www.autolina.ch/tesla/model-y",
        body=_search_page_html(1, [(1, 50000)]),
    )

    result = scrape("Tesla", "model-y", detail=False, delay=0)

    assert result.model_key == "model-y"
    assert len(result.listings) == 1


@responses.activate
def test_scrape_falls_back_to_live_probe_for_a_make_missing_from_the_sitemap() -> None:
    _register_catalog(["vw"], {"vw": ["tiguan"]})
    responses.add(
        responses.GET,
        "https://www.autolina.ch/polestar",
        body="<html><body><h1>POLESTAR Occasion - 3 Autos in der Schweiz</h1></body></html>",
    )
    responses.add(
        responses.GET,
        "https://www.autolina.ch/polestar/2",
        body="<html><body><h1>POLESTAR 2 Occasion - 3 Autos in der Schweiz</h1></body></html>",
    )
    responses.add(
        responses.GET,
        "https://www.autolina.ch/polestar/2",
        body=_search_page_html(1, [(1, 40000)]),
    )

    result = scrape("polestar", "2", detail=False, delay=0)

    assert result.make_key == "polestar"
    assert result.model_key == "2"


@responses.activate
def test_scrape_sorts_rows_and_listings_newest_first_by_car_id() -> None:
    # Deliberately uncorrelated with price/insertion order, so this can't
    # pass by coincidence: id 5 (newest) has the *lowest* price here.
    _register_catalog(["vw"], {"vw": ["tiguan"]})
    responses.add(
        responses.GET,
        "https://www.autolina.ch/vw/tiguan",
        body=_search_page_html(3, [(2, 30000), (5, 10000), (3, 20000)]),
    )

    result = scrape("vw", "tiguan", detail=False, delay=0)

    assert [listing["carId"] for listing in result.listings] == [5, 3, 2]
    assert [row["carId"] for row in result.rows] == ["5", "3", "2"]
