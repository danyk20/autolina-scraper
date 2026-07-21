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


def test_extract_posting_meta_parses_id_date_and_hits() -> None:
    html = (
        "<p><span>Dieses Inserat 123 wurde am 01.02.2024 aufgegeben oder "
        "aktualisiert und wurde 42 mal besucht.</span></p>"
    )
    meta = detail._extract_posting_meta(html)
    assert meta == {"lastUpdatedDateLabel": "01.02.2024", "hitCount": "42"}


def test_extract_posting_meta_returns_empty_when_absent() -> None:
    assert detail._extract_posting_meta("<p>nothing here</p>") == {}
