from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def read_fixture_bytes(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


@pytest.fixture
def search_page1() -> str:
    return read_fixture("search_page1.html")


@pytest.fixture
def search_page2() -> str:
    return read_fixture("search_page2.html")


@pytest.fixture
def detail_new_car() -> str:
    return read_fixture("detail_new_car.html")


@pytest.fixture
def detail_used_car() -> str:
    return read_fixture("detail_used_car.html")


@pytest.fixture
def detail_private_seller_with_description() -> str:
    return read_fixture("detail_private_seller_with_description.html")


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit tests never actually wait — they exercise the retry/pacing *logic*, not real time."""
    monkeypatch.setattr("time.sleep", lambda _seconds: None)
