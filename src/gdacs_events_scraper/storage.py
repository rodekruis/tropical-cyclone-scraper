from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import requests

from .models import EventSummary


logger = logging.getLogger(__name__)


class ExcelFlowRepository:
    def __init__(
        self,
        flow_url: str,
        timeout_seconds: int = 30,
        max_attempts: int = 3,
    ) -> None:
        if not flow_url:
            raise ValueError("EXCEL_FLOW_URL is required when excel storage is enabled")

        self._flow_url = flow_url
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max(1, max_attempts)

    def fetch_existing_event_ids(self) -> set[str]:
        payload = {
            "action": "list_event_ids",
            "source": "gdacs-events-scraper",
        }
        response = self._post(payload)

        data = response.json()
        raw_event_ids = data.get("event_ids", []) if isinstance(data, dict) else []
        if not isinstance(raw_event_ids, list):
            return set()

        event_ids: set[str] = set()
        for value in raw_event_ids:
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    event_ids.add(cleaned)
            elif isinstance(value, dict):
                raw = value.get("event_id", "")
                if isinstance(raw, str):
                    cleaned = raw.strip()
                    if cleaned:
                        event_ids.add(cleaned)
        return event_ids

    def append_events(self, events: list[tuple[EventSummary, bool]]) -> None:
        if not events:
            return

        payload = {
            "action": "append_events",
            "source": "gdacs-events-scraper",
            "recorded_at": datetime.now(UTC).isoformat(),
            "events": [self._to_record(event, is_new) for event, is_new in events],
        }
        self._post(payload)

    def sync_events(self, events: list[EventSummary]) -> list[tuple[EventSummary, bool]]:
        existing_event_ids = self.fetch_existing_event_ids()
        marked = [(event, event.event_id not in existing_event_ids) for event in events]
        new_events = [(event, is_new) for event, is_new in marked if is_new]
        self.append_events(new_events)
        return marked

    def _to_record(self, event: EventSummary, is_new: bool) -> dict[str, Any]:
        return {
            "event_id": event.event_id,
            "name": event.name,
            "disaster_type": event.disaster_type,
            "start_time": event.start_time.isoformat() if event.start_time else None,
            "end_time": event.end_time.isoformat() if event.end_time else None,
            "countries": event.countries,
            "alert_level": event.alert_level,
            "source_url": event.source_url,
            "is_new": is_new,
        }

    def _post(self, payload: dict[str, Any]) -> requests.Response:
        last_error: requests.RequestException | None = None

        for attempt in range(1, self._max_attempts + 1):
            try:
                response = requests.post(self._flow_url, json=payload, timeout=self._timeout_seconds)
                response.raise_for_status()
                return response
            except requests.HTTPError as error:
                status_code = error.response.status_code if error.response is not None else None
                if status_code not in {502, 503, 504} or attempt == self._max_attempts:
                    raise
                last_error = error
                logger.warning(
                    "Excel flow request failed with status %s on attempt %s/%s for action %s; retrying",
                    status_code,
                    attempt,
                    self._max_attempts,
                    payload.get("action"),
                )
            except (requests.ConnectionError, requests.Timeout) as error:
                if attempt == self._max_attempts:
                    raise
                last_error = error
                logger.warning(
                    "Excel flow request failed on attempt %s/%s for action %s; retrying: %s",
                    attempt,
                    self._max_attempts,
                    payload.get("action"),
                    error,
                )

        if last_error is not None:
            raise last_error
        raise RuntimeError("Excel flow request failed without raising a requests error")
