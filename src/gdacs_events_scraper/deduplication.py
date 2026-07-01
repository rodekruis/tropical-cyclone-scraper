"""Local event deduplication tracker to prevent duplicate exports."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class DeduplicationTracker:
    """Tracks exported event IDs locally to prevent duplicates across runs."""

    def __init__(self, tracker_file: str | Path | None = None) -> None:
        if tracker_file is None:
            tracker_file = Path.home() / ".gdacs_events_scraper" / "exported_event_ids.json"
        else:
            tracker_file = Path(tracker_file)

        self._tracker_file = tracker_file
        self._exported_ids = self._load_exported_ids()

    def _load_exported_ids(self) -> dict[str, str]:
        """Load previously exported event IDs from disk."""
        if not self._tracker_file.exists():
            return {}

        try:
            with open(self._tracker_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load deduplication tracker: {e}")

        return {}

    def save(self) -> None:
        """Persist exported event IDs to disk."""
        self._tracker_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._tracker_file, "w", encoding="utf-8") as f:
                json.dump(self._exported_ids, f, indent=2)
        except IOError as e:
            logger.warning(f"Failed to save deduplication tracker: {e}")

    def mark_exported(self, event_ids: list[str]) -> None:
        """Mark events as exported."""
        timestamp = datetime.now(UTC).isoformat()
        for event_id in event_ids:
            self._exported_ids[event_id] = timestamp
        self.save()

    def get_exported_ids(self) -> set[str]:
        """Get all previously exported event IDs."""
        return set(self._exported_ids.keys())

    def is_already_exported(self, event_id: str) -> bool:
        """Check if an event has been exported before."""
        return event_id in self._exported_ids

    def clear(self) -> None:
        """Clear all tracked event IDs (useful for testing or cleanup)."""
        self._exported_ids.clear()
        if self._tracker_file.exists():
            self._tracker_file.unlink()
        logger.info("Deduplication tracker cleared")
