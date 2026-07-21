from __future__ import annotations

import pytest
import requests
import responses

from autolina_scraper import http


def test_new_session_sets_identifying_user_agent() -> None:
    session = http.new_session()
    assert session.headers["User-Agent"].startswith("autolina-scraper/")
    assert "github.com/danyk20/autolina-scraper" in session.headers["User-Agent"]


@responses.activate
def test_get_returns_response_on_first_success() -> None:
    responses.add(responses.GET, "https://example.test/ok", body="hello", status=200)
    session = http.new_session()
    response = http.get(session, "https://example.test/ok", delay=0)
    assert response.text == "hello"


@responses.activate
def test_get_retries_on_429_then_succeeds() -> None:
    responses.add(responses.GET, "https://example.test/flaky", status=429)
    responses.add(responses.GET, "https://example.test/flaky", body="ok", status=200)
    session = http.new_session()
    response = http.get(session, "https://example.test/flaky", delay=0, max_retries=3)
    assert response.text == "ok"


@responses.activate
def test_get_raises_after_exhausting_retries() -> None:
    for _ in range(4):
        responses.add(responses.GET, "https://example.test/dead", status=503)
    session = http.new_session()
    with pytest.raises(requests.exceptions.HTTPError):
        http.get(session, "https://example.test/dead", delay=0, max_retries=3)


@responses.activate
def test_get_raises_immediately_on_non_retryable_4xx() -> None:
    responses.add(responses.GET, "https://example.test/gone", status=404)
    session = http.new_session()
    with pytest.raises(requests.exceptions.HTTPError):
        http.get(session, "https://example.test/gone", delay=0, max_retries=5)
    assert len(responses.calls) == 1


@responses.activate
def test_get_raises_challenge_detected_on_cloudflare_interstitial() -> None:
    responses.add(
        responses.GET,
        "https://example.test/carList",
        body="<html>Just a moment...</html>",
        status=403,
    )
    session = http.new_session()
    with pytest.raises(http.ChallengeDetectedError):
        http.get(session, "https://example.test/carList", delay=0)


@responses.activate
def test_get_raises_challenge_detected_on_cf_mitigated_header() -> None:
    responses.add(
        responses.GET,
        "https://example.test/mitigated",
        body="ok",
        status=200,
        headers={"cf-mitigated": "challenge"},
    )
    session = http.new_session()
    with pytest.raises(http.ChallengeDetectedError):
        http.get(session, "https://example.test/mitigated", delay=0)


@responses.activate
def test_get_sleeps_for_positive_delay_before_requesting() -> None:
    responses.add(responses.GET, "https://example.test/paced", body="ok", status=200)
    session = http.new_session()
    response = http.get(session, "https://example.test/paced", delay=0.01)
    assert response.text == "ok"


@responses.activate
def test_get_raises_after_exhausting_connection_error_retries() -> None:
    for _ in range(4):
        responses.add(
            responses.GET,
            "https://example.test/always-down",
            body=requests.exceptions.ConnectionError("boom"),
        )
    session = http.new_session()
    with pytest.raises(requests.exceptions.ConnectionError):
        http.get(session, "https://example.test/always-down", delay=0, max_retries=3)


@responses.activate
def test_get_retries_on_connection_error_then_succeeds() -> None:
    responses.add(
        responses.GET,
        "https://example.test/conn-flaky",
        body=requests.exceptions.ConnectionError("boom"),
    )
    responses.add(responses.GET, "https://example.test/conn-flaky", body="ok", status=200)
    session = http.new_session()
    response = http.get(session, "https://example.test/conn-flaky", delay=0, max_retries=3)
    assert response.text == "ok"
