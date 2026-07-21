from __future__ import annotations

from pathlib import Path

import pytest
import requests

from autolina_scraper import cli
from autolina_scraper.models import ScrapeResult


def test_version_flag_exits_cleanly() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.build_parser().parse_args(["--version"])
    assert exc_info.value.code == 0


def test_missing_required_flags_exits_2() -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.build_parser().parse_args([])
    assert exc_info.value.code == 2


def test_verbose_and_quiet_are_mutually_exclusive() -> None:
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["--make", "vw", "--model", "tiguan", "-v", "-q"])


def test_no_detail_flag_maps_to_detail_false(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_scrape(make, model, **kwargs):
        captured.update(kwargs)
        return ScrapeResult("vw", "VW", "tiguan", "TIGUAN", "car", 0, [], [], "ch")

    monkeypatch.setattr(cli, "scrape", fake_scrape)
    cli.run_cli(["--make", "vw", "--model", "tiguan", "--no-detail"])
    assert captured["detail"] is False


def test_run_cli_writes_csv_and_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_scrape(make, model, **kwargs):
        return ScrapeResult(
            make_key="vw",
            make_name="VW",
            model_key="tiguan",
            model_name="TIGUAN",
            category="car",
            total_elements=1,
            listings=[{"carId": 1}],
            rows=[{"carId": "1"}],
            domain="ch",
        )

    monkeypatch.setattr(cli, "scrape", fake_scrape)
    out_base = str(tmp_path / "result")
    exit_code = cli.run_cli(["--make", "vw", "--model", "tiguan", "--out", out_base])

    assert exit_code == 0
    assert Path(f"{out_base}.csv").exists()
    assert Path(f"{out_base}.json").exists()


def test_run_cli_value_error_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_value_error(make, model, **kwargs):
        raise ValueError("unknown make 'nope'")

    monkeypatch.setattr(cli, "scrape", raise_value_error)
    exit_code = cli.run_cli(["--make", "nope", "--model", "tiguan"])
    assert exit_code == 2


def test_run_cli_network_error_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_network_error(make, model, **kwargs):
        raise requests.exceptions.ConnectionError("boom")

    monkeypatch.setattr(cli, "scrape", raise_network_error)
    exit_code = cli.run_cli(["--make", "vw", "--model", "tiguan"])
    assert exit_code == 1


def _empty_result() -> ScrapeResult:
    return ScrapeResult("vw", "VW", "t", "T", "car", 0, [], [], "ch")


def test_verbose_flag_sets_debug_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}
    monkeypatch.setattr(cli.logging, "basicConfig", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setattr(cli, "scrape", lambda make, model, **kwargs: _empty_result())
    cli.run_cli(["--make", "vw", "--model", "tiguan", "-v"])
    assert captured["level"] == cli.logging.DEBUG


def test_quiet_flag_sets_warning_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}
    monkeypatch.setattr(cli.logging, "basicConfig", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setattr(cli, "scrape", lambda make, model, **kwargs: _empty_result())
    cli.run_cli(["--make", "vw", "--model", "tiguan", "-q"])
    assert captured["level"] == cli.logging.WARNING


def test_main_exits_with_run_cli_return_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "run_cli", lambda: 0)
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    assert exc_info.value.code == 0


def test_default_out_base_is_make_underscore_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    def fake_scrape(make, model, **kwargs):
        return ScrapeResult("vw", "VW", "tiguan", "TIGUAN", "car", 0, [], [], "ch")

    monkeypatch.setattr(cli, "scrape", fake_scrape)
    cli.run_cli(["--make", "vw", "--model", "tiguan"])

    assert (tmp_path / "vw_tiguan.csv").exists()
    assert (tmp_path / "vw_tiguan.json").exists()
