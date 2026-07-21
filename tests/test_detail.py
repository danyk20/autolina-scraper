from __future__ import annotations

import responses

from autolina_scraper import detail, http


def test_listing_url_builds_expected_path() -> None:
    assert (
        detail.listing_url("vw-tiguan", 5033764) == "https://www.autolina.ch/auto/vw-tiguan/5033764"
    )


@responses.activate
def test_fetch_detail_parses_specs_energy_and_meta(detail_new_car: str) -> None:
    responses.add(
        responses.GET,
        "https://www.autolina.ch/auto/vw-tiguan/5033764",
        body=detail_new_car,
        status=200,
    )

    record = detail.fetch_detail(http.new_session(), "vw-tiguan", 5033764, delay=0)

    assert record["carId"] == 5033764
    assert record["url"] == "https://www.autolina.ch/auto/vw-tiguan/5033764"
    assert record["fahrgestell_nr"] == "WVGZZZCT3TW555786"
    assert record["treibstoff"] == "Benzin"
    assert record["getriebeart"] == "Automatik, 7 Gänge"
    assert record["antrieb"] == "Vorderradantrieb"
    assert record["aufbau"] == "SUV"
    assert record["fahrzeugzustand"] == "Neuwagen"
    assert record["farbe_aussen_innen"] == "Schwarz"
    assert record["energieeffizienz"] == "E"
    assert "hitCount" in record
    assert "lastUpdatedDateLabel" in record


@responses.activate
def test_fetch_detail_parses_used_car_condition(detail_used_car: str) -> None:
    responses.add(
        responses.GET,
        "https://www.autolina.ch/auto/vw-tiguan/4525368",
        body=detail_used_car,
        status=200,
    )

    record = detail.fetch_detail(http.new_session(), "vw-tiguan", 4525368, delay=0)

    assert record["antrieb"] == "Allradantrieb"


@responses.activate
def test_fetch_detail_extracts_equipment_lists(detail_new_car: str) -> None:
    responses.add(
        responses.GET,
        "https://www.autolina.ch/auto/vw-tiguan/5033764",
        body=detail_new_car,
        status=200,
    )

    record = detail.fetch_detail(http.new_session(), "vw-tiguan", 5033764, delay=0)

    assert len(record["optionale_ausstattung"]) > 0
    assert len(record["serienmaessige_ausstattung"]) > 0
    assert all(isinstance(item, str) for item in record["optionale_ausstattung"])


@responses.activate
def test_fetch_detail_extracts_dealer_and_images(detail_new_car: str) -> None:
    responses.add(
        responses.GET,
        "https://www.autolina.ch/auto/vw-tiguan/5033764",
        body=detail_new_car,
        status=200,
    )

    record = detail.fetch_detail(http.new_session(), "vw-tiguan", 5033764, delay=0)

    assert record["dealer"]["name"] == "Christen Automobile AG"
    assert record["dealer"]["phone"]
    assert record["images"]
    assert all(url.startswith("https://") for url in record["images"])


@responses.activate
def test_fetch_detail_extracts_description_and_ad_title(
    detail_private_seller_with_description: str,
) -> None:
    responses.add(
        responses.GET,
        "https://www.autolina.ch/auto/alfa-romeo-giulietta/4735627",
        body=detail_private_seller_with_description,
        status=200,
    )

    record = detail.fetch_detail(
        http.new_session(), "alfa-romeo-giulietta", 4735627, delay=0
    )

    expected_title = "Livraison Suisse, Matching Numbers, Matching Colors, Véhicule Vétéran"
    assert record["adTitle"] == expected_title
    assert "beschreibung" in record
    assert "Alfa Romeo Giulietta" in record["beschreibung"]
    assert record["beschreibung"].count("\n") == 0  # flattened to one CSV-friendly line


@responses.activate
def test_fetch_detail_omits_description_when_the_listing_has_none(detail_new_car: str) -> None:
    # Dealer-posted listings (like this one) commonly skip the free-text
    # description entirely — no `.description-row` at all, not an empty one.
    responses.add(
        responses.GET,
        "https://www.autolina.ch/auto/vw-tiguan/5033764",
        body=detail_new_car,
        status=200,
    )

    record = detail.fetch_detail(http.new_session(), "vw-tiguan", 5033764, delay=0)

    assert "beschreibung" not in record
    assert record["adTitle"] == "CH Fahrzeug mit 4 Jahre Werksgarantie"


@responses.activate
def test_visit_all_listings_merges_detail_onto_each_summary(
    detail_new_car: str, detail_used_car: str
) -> None:
    responses.add(
        responses.GET,
        "https://www.autolina.ch/auto/vw-tiguan/5033764",
        body=detail_new_car,
    )
    responses.add(
        responses.GET,
        "https://www.autolina.ch/auto/vw-tiguan/4525368",
        body=detail_used_car,
    )
    summaries = [
        {
            "carId": 5033764,
            "slug": "vw-tiguan",
            "url": "https://www.autolina.ch/auto/vw-tiguan/5033764",
            "price": 45300,
        },
        {
            "carId": 4525368,
            "slug": "vw-tiguan",
            "url": "https://www.autolina.ch/auto/vw-tiguan/4525368",
            "price": 34900,
        },
    ]

    enriched = detail.visit_all_listings(http.new_session(), summaries, delay=0)

    assert len(enriched) == 2
    assert enriched[0]["carId"] == 5033764
    assert enriched[0]["fahrgestell_nr"] == "WVGZZZCT3TW555786"
    assert enriched[0]["price"] == 45300  # summary field preserved, not clobbered
    assert enriched[1]["carId"] == 4525368


@responses.activate
def test_visit_all_listings_falls_back_to_slug_derived_from_url_when_absent() -> None:
    responses.add(
        responses.GET,
        "https://www.autolina.ch/auto/vw-tiguan/1",
        body="<html><body></body></html>",
    )
    summaries = [{"carId": 1, "url": "https://www.autolina.ch/auto/vw-tiguan/1"}]

    enriched = detail.visit_all_listings(http.new_session(), summaries, delay=0)

    assert enriched[0]["carId"] == 1


def test_extract_posting_meta_parses_id_date_and_hits() -> None:
    html = (
        "<p><span>Dieses Inserat 123 wurde am 01.02.2024 aufgegeben oder "
        "aktualisiert und wurde 42 mal besucht.</span></p>"
    )
    meta = detail._extract_posting_meta(html)
    assert meta == {"lastUpdatedDateLabel": "01.02.2024", "hitCount": "42"}


def test_extract_posting_meta_returns_empty_when_absent() -> None:
    assert detail._extract_posting_meta("<p>nothing here</p>") == {}
