"""End-to-end tests against the real, live autolina.ch — excluded by default.

Run explicitly with ``pytest -m e2e --no-cov``. Targets a small-inventory make/model
(same spirit as the AutoScout24 reference's Tesla Roadster pick) to keep these fast
and light on the real site, and respects the same default delay as any other use of
this library — no special-casing for tests.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from autolina_scraper import scrape
from autolina_scraper.catalog import fetch_make_slugs
from autolina_scraper.http import new_session

pytestmark = pytest.mark.e2e


def test_real_sitemap_resolves_known_makes() -> None:
    slugs = fetch_make_slugs(new_session(), delay=0.5)
    assert "vw" in slugs
    assert "porsche" in slugs


def test_real_scrape_of_a_small_inventory_model() -> None:
    result = scrape("aston-martin", "db7", delay=0.5)

    assert result.make_key == "aston-martin"
    assert result.model_key == "db7"
    assert len(result.listings) == len(result.rows) == result.total_elements
    for row in result.rows:
        assert row["url"].startswith("https://www.autolina.ch/auto/")


def test_real_scrape_without_detail_has_fewer_fields_than_with_detail() -> None:
    summary = scrape("aston-martin", "db7", detail=False, delay=0.5)
    full = scrape("aston-martin", "db7", detail=True, delay=0.5)

    if summary.listings:
        summary_fields = set(summary.listings[0])
        full_fields = set(full.listings[0])
        assert summary_fields <= full_fields


def test_real_scrape_orders_listings_newest_first() -> None:
    result = scrape("aston-martin", "db7", detail=False, delay=0.5)

    ids = [listing["carId"] for listing in result.listings]
    assert ids == sorted(ids, reverse=True)


def test_real_scrape_max_results_returns_the_newest_n() -> None:
    # Small-inventory model (same one used elsewhere in this file) so this
    # comparison doesn't mean scraping a large search twice against the
    # live site.
    capped = scrape("aston-martin", "db7", detail=False, max_results=3, delay=0.5)
    uncapped = scrape("aston-martin", "db7", detail=False, delay=0.5)

    assert len(capped.listings) == 3
    assert capped.total_elements == uncapped.total_elements
    newest_three_overall = [listing["carId"] for listing in uncapped.listings[:3]]
    assert [listing["carId"] for listing in capped.listings] == newest_three_overall


def test_real_scrape_raises_for_unknown_make() -> None:
    with pytest.raises(ValueError, match="unknown make"):
        scrape("this-make-does-not-exist", "tiguan", delay=0.5)


def test_cli_subprocess_writes_output_files(tmp_path) -> None:  # noqa: ANN001
    out_base = tmp_path / "db7"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "autolina_scraper.cli",
            "--make",
            "aston-martin",
            "--model",
            "db7",
            "--delay",
            "0.5",
            "--out",
            str(out_base),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    assert out_base.with_suffix(".csv").exists()
    assert out_base.with_suffix(".json").exists()


def test_cli_subprocess_exits_2_on_unknown_make() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "autolina_scraper.cli",
            "--make",
            "this-make-does-not-exist",
            "--model",
            "tiguan",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 2
