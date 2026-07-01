from __future__ import annotations

from datetime import UTC, datetime

import requests

from gdacs_events_scraper.models import CycloneSummary
from gdacs_events_scraper.storage import ExcelFlowRepository


def test_excel_flow_repository_posts_event_payload(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

    def fake_post(url: str, json: dict, timeout: int) -> _FakeResponse:
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _FakeResponse()

    monkeypatch.setattr("gdacs_events_scraper.storage.requests.post", fake_post)

    repo = ExcelFlowRepository("https://example.com/flow", timeout_seconds=12)
    event = CycloneSummary(
        event_id="tc-200",
        name="TC SAMPLE",
        start_time=datetime(2026, 6, 16, 4, 0, tzinfo=UTC),
        end_time=None,
        countries=["PHL"],
        alert_level="Orange",
        source_url="https://example.com/tc-200",
    )

    repo.append_events([(event, True)])

    assert len(calls) == 1
    assert calls[0]["url"] == "https://example.com/flow"
    assert calls[0]["timeout"] == 12

    payload = calls[0]["json"]
    assert isinstance(payload, dict)
    assert payload["source"] == "gdacs-events-scraper"
    assert len(payload["events"]) == 1
    assert payload["events"][0]["event_id"] == "tc-200"
    assert payload["events"][0]["is_new"] is True


def test_excel_flow_repository_syncs_against_existing_ids(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class _FakeResponse:
        def __init__(self, payload: dict | None = None) -> None:
            self._payload = payload or {}

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    def fake_post(url: str, json: dict, timeout: int) -> _FakeResponse:
        calls.append({"url": url, "json": json, "timeout": timeout})
        if json["action"] == "list_event_ids":
            return _FakeResponse({"event_ids": ["tc-100"]})
        return _FakeResponse()

    monkeypatch.setattr("gdacs_events_scraper.storage.requests.post", fake_post)

    repo = ExcelFlowRepository("https://example.com/flow", timeout_seconds=12)
    existing = CycloneSummary(
        event_id="tc-100",
        name="TC EXISTING",
        start_time=datetime(2026, 6, 16, 4, 0, tzinfo=UTC),
        end_time=None,
        countries=["PHL"],
        alert_level="Orange",
        source_url="https://example.com/tc-100",
    )
    new_event = CycloneSummary(
        event_id="tc-200",
        name="TC NEW",
        start_time=datetime(2026, 6, 16, 5, 0, tzinfo=UTC),
        end_time=None,
        countries=["PHL"],
        alert_level="Red",
        source_url="https://example.com/tc-200",
    )

    marked = repo.sync_events([existing, new_event])

    assert marked == [(existing, False), (new_event, True)]
    assert len(calls) == 2
    assert calls[0]["json"]["action"] == "list_event_ids"
    assert calls[1]["json"]["action"] == "append_events"
    assert calls[1]["json"]["events"][0]["event_id"] == "tc-200"


def test_excel_flow_repository_retries_transient_http_error(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class _FakeResponse:
        def __init__(self, status_code: int, payload: dict | None = None) -> None:
            self.status_code = status_code
            self._payload = payload or {}

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise requests.HTTPError(f"status={self.status_code}", response=self)

        def json(self) -> dict:
            return self._payload

    responses = iter(
        [
            _FakeResponse(502),
            _FakeResponse(200, {"event_ids": ["tc-100"]}),
            _FakeResponse(200),
        ]
    )

    def fake_post(url: str, json: dict, timeout: int) -> _FakeResponse:
        calls.append({"url": url, "json": json, "timeout": timeout})
        return next(responses)

    monkeypatch.setattr("gdacs_events_scraper.storage.requests.post", fake_post)

    repo = ExcelFlowRepository("https://example.com/flow", timeout_seconds=12, max_attempts=3)
    existing = CycloneSummary(
        event_id="tc-100",
        name="TC EXISTING",
        start_time=datetime(2026, 6, 16, 4, 0, tzinfo=UTC),
        end_time=None,
        countries=["PHL"],
        alert_level="Orange",
        source_url="https://example.com/tc-100",
    )
    new_event = CycloneSummary(
        event_id="tc-200",
        name="TC NEW",
        start_time=datetime(2026, 6, 16, 5, 0, tzinfo=UTC),
        end_time=None,
        countries=["PHL"],
        alert_level="Red",
        source_url="https://example.com/tc-200",
    )

    marked = repo.sync_events([existing, new_event])

    assert marked == [(existing, False), (new_event, True)]
    assert len(calls) == 3
    assert calls[0]["json"]["action"] == "list_event_ids"
    assert calls[1]["json"]["action"] == "list_event_ids"
    assert calls[2]["json"]["action"] == "append_events"
