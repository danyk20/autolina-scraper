from __future__ import annotations

import csv
import json
from pathlib import Path

from autolina_scraper.io import save_csv, save_json


def test_save_csv_writes_union_of_columns_pinned_first(tmp_path: Path) -> None:
    rows = [{"carId": "1", "price": "100"}, {"carId": "2", "extra": "x"}]
    path = tmp_path / "out.csv"
    save_csv(rows, str(path))

    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["carId", "price", "extra"]
        written = list(reader)

    assert written[0] == {"carId": "1", "price": "100", "extra": ""}
    assert written[1] == {"carId": "2", "price": "", "extra": "x"}


def test_save_csv_handles_empty_rows(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    save_csv([], str(path))
    assert path.read_text(encoding="utf-8") == ""


def test_save_csv_handles_unicode(tmp_path: Path) -> None:
    path = tmp_path / "unicode.csv"
    save_csv([{"model": "Škoda Octavia"}], str(path))
    assert "Škoda Octavia" in path.read_text(encoding="utf-8")


def test_save_json_round_trips(tmp_path: Path) -> None:
    listings = [{"carId": 1, "nested": {"a": 1}}, {"carId": 2}]
    path = tmp_path / "out.json"
    save_json(listings, str(path))

    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == listings
