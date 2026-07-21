from __future__ import annotations

import responses

from autolina_scraper import htmlparse, http, search


def _card_html(car_id: int, *, premium: bool = False) -> str:
    premium_div = '<div class="premium">TOP</div>' if premium else ""
    return f"""
    <app-car-row class="car-row">
      <a class="url-wrapper" href="/auto/vw-tiguan/{car_id}">
        {premium_div}
        <div class="make-model">
          <span title="VW">VW</span>
          <span title="Tiguan R-Line">Tiguan R-Line</span>
        </div>
        <div class="price-container"><div class="price">CHF {10000 + car_id}</div></div>
        <div class="vehicle-data">
          <div><span>2021</span></div>
          <div><span>50'000</span> <span class="small">km</span></div>
          <div><span>190</span> <span class="small">PS</span></div>
          <div><span>Automatik</span></div>
          <div><span>Benzin</span></div>
          <div><span>Grau</span></div>
        </div>
        <div class="region-or-title"><span>8000 Zürich / ZH</span></div>
        <img class="first-img" src="https://www.autolina.ch/auto-bild/vw-tiguan/{car_id}_1.jpg?w=1">
      </a>
    </app-car-row>
    """


def _page_html(count: int, car_ids: list[int]) -> str:
    cards = "".join(_card_html(car_id) for car_id in car_ids)
    return f"<html><body><h1>VW TIGUAN - {count} Autos in der Schweiz</h1>{cards}</body></html>"


def test_build_query_omits_unset_filters() -> None:
    assert search.build_query() == {}


def test_build_query_builds_min_max_range_strings() -> None:
    query = search.build_query(price_from=10_000, price_to=20_000, year_from=2018)
    assert query == {"price": "10000-20000", "date": "2018-"}


def test_build_query_supports_open_ended_ranges() -> None:
    assert search.build_query(price_to=20_000) == {"price": "-20000"}
    assert search.build_query(mileage_from=5_000) == {"mileage": "5000-"}


@responses.activate
def test_fetch_listings_stops_when_total_reached_on_first_page() -> None:
    html = _page_html(2, [1, 2])
    responses.add(responses.GET, "https://www.autolina.ch/vw/tiguan", body=html, status=200)

    total, listings = search.fetch_listings(http.new_session(), "vw", "tiguan", delay=0)

    assert total == 2
    assert {listing["carId"] for listing in listings} == {1, 2}
    assert len(responses.calls) == 1


@responses.activate
def test_fetch_listings_paginates_until_a_page_yields_nothing_new() -> None:
    page1 = _page_html(3, [1, 2])
    page2 = _page_html(3, [3])
    responses.add(responses.GET, "https://www.autolina.ch/vw/tiguan", body=page1, status=200)
    responses.add(
        responses.GET, "https://www.autolina.ch/vw/tiguan/page/2", body=page2, status=200
    )

    total, listings = search.fetch_listings(http.new_session(), "vw", "tiguan", delay=0)

    assert total == 3
    assert {listing["carId"] for listing in listings} == {1, 2, 3}
    assert len(responses.calls) == 2


@responses.activate
def test_fetch_listings_dedupes_repeated_car_ids_across_pages() -> None:
    page1 = _page_html(3, [1, 2])
    page2 = _page_html(3, [2])  # a "TOP" listing reshuffled into page 2 too
    responses.add(responses.GET, "https://www.autolina.ch/vw/tiguan", body=page1, status=200)
    responses.add(
        responses.GET, "https://www.autolina.ch/vw/tiguan/page/2", body=page2, status=200
    )

    total, listings = search.fetch_listings(http.new_session(), "vw", "tiguan", delay=0)

    assert total == 3
    assert len(listings) == 2
    assert len(responses.calls) == 2


@responses.activate
def test_fetch_listings_stops_on_page_with_no_cards() -> None:
    html = "<html><body><h1>0 Autos in der Schweiz</h1></body></html>"
    responses.add(responses.GET, "https://www.autolina.ch/vw/tiguan", body=html, status=200)

    total, listings = search.fetch_listings(http.new_session(), "vw", "tiguan", delay=0)

    assert total == 0
    assert listings == []
    assert len(responses.calls) == 1


@responses.activate
def test_fetch_listings_passes_query_params_through() -> None:
    html = _page_html(1, [1])
    responses.add(responses.GET, "https://www.autolina.ch/vw/tiguan", body=html, status=200)

    search.fetch_listings(
        http.new_session(), "vw", "tiguan", query={"price": "10000-20000"}, delay=0
    )

    assert responses.calls[0].request.url is not None
    assert "price=10000-20000" in responses.calls[0].request.url


@responses.activate
def test_fetch_listings_marks_premium_listings() -> None:
    html = _page_html(1, [1]).replace(
        '<a class="url-wrapper" href="/auto/vw-tiguan/1">',
        '<a class="url-wrapper" href="/auto/vw-tiguan/1">'
        '<div class="premium">TOP</div>',
    )
    responses.add(responses.GET, "https://www.autolina.ch/vw/tiguan", body=html, status=200)

    _, listings = search.fetch_listings(http.new_session(), "vw", "tiguan", delay=0)

    assert listings[0]["isPremium"] is True


def test_parse_card_against_real_fixture_extracts_expected_fields(search_page1: str) -> None:
    tree = htmlparse.parse(search_page1)
    cards = tree.css(".car-row")
    assert len(cards) > 0

    parsed = [search._parse_card(card) for card in cards]
    first = next(listing for listing in parsed if listing and listing["carId"] == 5033764)

    assert first["make"] == "VW"
    assert first["modelType"] == "Tiguan UNITED"
    assert first["price"] == 45300
    assert first["treibstoff"] == "Benzin"
    assert first["getriebeart"] == "Automatik"
    assert first["url"] == "https://www.autolina.ch/auto/vw-tiguan/5033764"


def test_parse_result_count_against_real_fixture(search_page1: str) -> None:
    tree = htmlparse.parse(search_page1)
    assert search._parse_result_count(tree) > 1000


def test_parse_result_count_returns_zero_when_h1_unrecognized() -> None:
    tree = htmlparse.parse("<html><body><h1>nothing useful here</h1></body></html>")
    assert search._parse_result_count(tree) == 0


def test_parse_card_returns_none_for_a_non_listing_link() -> None:
    html = '<div class="car-row"><a class="url-wrapper" href="/favoriten"></a></div>'
    tree = htmlparse.parse(html)
    card = tree.css_first(".car-row")
    assert search._parse_card(card) is None


def test_parse_card_ignores_blank_vehicle_data_entries() -> None:
    html = """
    <div class="car-row">
      <a class="url-wrapper" href="/auto/vw-tiguan/1">
        <div class="vehicle-data"><div><span>   </span></div></div>
      </a>
    </div>
    """
    tree = htmlparse.parse(html)
    card = tree.css_first(".car-row")
    listing = search._parse_card(card)
    assert listing is not None
    assert listing["farbe_aussen_innen"] is None
