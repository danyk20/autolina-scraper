from __future__ import annotations

from autolina_scraper.flatten import flatten_listing, order_fieldnames


def test_flattens_nested_dict_into_parent_child_columns() -> None:
    listing = {"carId": 1, "dealer": {"name": "Acme AG", "city": "Zug"}}
    flat = flatten_listing(listing)
    assert flat == {"carId": "1", "dealer_name": "Acme AG", "dealer_city": "Zug"}


def test_flattens_deeply_nested_dicts() -> None:
    listing = {"warranty": {"details": {"months": 12}}}
    assert flatten_listing(listing) == {"warranty_details_months": "12"}


def test_scalarizes_list_of_plain_strings() -> None:
    listing = {"pics": ["a.jpg", "b.jpg"]}
    assert flatten_listing(listing) == {"pics": "a.jpg; b.jpg"}


def test_scalarizes_list_of_dicts_using_title_field() -> None:
    listing = {
        "equipment": [
            {"equipmentTitle": "Alu Felgen", "equipmentSubList": []},
            {"equipmentTitle": "Klimaanlage", "equipmentSubList": []},
        ]
    }
    assert flatten_listing(listing) == {"equipment": "Alu Felgen; Klimaanlage"}


def test_scalarizes_list_of_dicts_without_title_field_as_json() -> None:
    listing = {"misc": [{"a": 1, "b": 2}]}
    flat = flatten_listing(listing)
    assert flat["misc"] == '{"a": 1, "b": 2}'


def test_scalarizes_nested_list_of_lists() -> None:
    listing = {"grid": [["a", "b"], ["c"]]}
    assert flatten_listing(listing) == {"grid": "a; b; c"}


def test_none_becomes_empty_string() -> None:
    assert flatten_listing({"vin": None}) == {"vin": ""}


def test_empty_list_becomes_empty_string() -> None:
    assert flatten_listing({"pics": []}) == {"pics": ""}


def test_order_fieldnames_pins_known_columns_first_then_alphabetical() -> None:
    fieldnames = {"zebra", "carId", "aardvark", "price", "url"}
    ordered = order_fieldnames(fieldnames)
    assert ordered == ["carId", "url", "price", "aardvark", "zebra"]


def test_order_fieldnames_only_pins_columns_actually_present() -> None:
    ordered = order_fieldnames({"custom_field", "price"})
    assert ordered == ["price", "custom_field"]
