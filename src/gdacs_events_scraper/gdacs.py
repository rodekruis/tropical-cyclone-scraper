from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)


class GdacsClient:
    def __init__(self, base_url: str, timeout_seconds: int = 30) -> None:
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds

    def fetch_events(
        self,
        lookback_days: int,
        lookahead_days: int,
        event_types: list[str],
        sleep_seconds: float = 1.0,
        min_alert_level: str = "Green",
    ) -> list[dict[str, Any]]:
        now = datetime.now(UTC)
        from_date = now - timedelta(days=lookback_days)
        to_date = now + timedelta(days=lookahead_days)
        normalized_types = [event_type.strip().upper() for event_type in event_types if event_type.strip()]
        event_type_list = normalized_types or ["TC"]

        all_events: list[dict[str, Any]] = []

        for i, event_type in enumerate(event_type_list):
            if i > 0:
                LOGGER.debug("Sleeping %.1f seconds before fetching next event type", sleep_seconds)
                time.sleep(sleep_seconds)

            params = {
                "eventtype": event_type,
                "fromdate": from_date.strftime("%Y-%m-%d"),
                "todate": to_date.strftime("%Y-%m-%d"),
            }

            LOGGER.debug("Fetching GDACS events for type: %s", event_type)
            response = requests.get(self._base_url, params=params, timeout=self._timeout_seconds)
            response.raise_for_status()

            payload = response.json()
            LOGGER.debug("GDACS payload: %s", payload)
            events = self._extract_events(payload)
            LOGGER.debug("Extracted events: %s", events)
            all_events.extend(events)

        return all_events

    def _extract_events(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict):
            if "features" in payload and isinstance(payload["features"], list):
                events: list[dict[str, Any]] = []
                for feature in payload["features"]:
                    if not isinstance(feature, dict):
                        continue
                    properties = feature.get("properties", {}) if isinstance(feature.get("properties"), dict) else {}
                    merged = dict(properties)
                    merged["geometry"] = feature.get("geometry")
                    events.append(merged)
                return events

            if "events" in payload and isinstance(payload["events"], list):
                return [item for item in payload["events"] if isinstance(item, dict)]

        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]

        LOGGER.warning("Unexpected GDACS payload structure")
        return []
