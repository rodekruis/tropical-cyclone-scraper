from __future__ import annotations

from gdacs_events_scraper.gdacs import GdacsClient


class _DummyResponse:
	def raise_for_status(self) -> None:
		return None

	def json(self) -> list[dict[str, str]]:
		return []


def test_fetch_events_does_not_send_exact_alert_level_filter(monkeypatch) -> None:
	captured_params: dict[str, str] = {}

	def fake_get(url: str, params: dict[str, str], timeout: int) -> _DummyResponse:
		captured_params.update(params)
		return _DummyResponse()

	monkeypatch.setattr("gdacs_events_scraper.gdacs.requests.get", fake_get)

	client = GdacsClient("https://example.com")
	client.fetch_events(
		lookback_days=1,
		lookahead_days=7,
		event_types=["TC"],
		min_alert_level="Orange",
	)

	assert "alertlevel" not in captured_params
