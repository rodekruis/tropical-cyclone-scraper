from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .models import EventSummary


class EventsFileExporter:
    def __init__(self, output_dir: str, output_formats: list[str]) -> None:
        self._output_dir = Path(output_dir)
        self._output_formats = output_formats

    def export(self, events: list[EventSummary]) -> list[Path]:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

        created_files: list[Path] = []
        for output_format in self._output_formats:
            if output_format == "csv":
                output_path = self._output_dir / f"events-{timestamp}.csv"
                self._write_csv(output_path, events)
                created_files.append(output_path)

        return created_files

    def _write_csv(self, output_path: Path, events: list[EventSummary]) -> None:
        fieldnames = [
            "event_id",
            "name",
            "start_time",
            "end_time",
            "countries",
            "alert_level",
            "source_url",
        ]
        with output_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            for event in events:
                record = self._to_record(event)
                writer.writerow(
                    {
                        "event_id": record["event_id"],
                        "name": record["name"],
                        "start_time": record["start_time"],
                        "end_time": record["end_time"],
                        "countries": ";".join(record["countries"]),
                        "alert_level": record["alert_level"],
                        "source_url": record["source_url"],
                    }
                )

    def _to_record(self, event: EventSummary) -> dict[str, object]:
        record = asdict(event)
        for key in ("start_time", "end_time"):
            dt = record[key]
            record[key] = dt.isoformat() if dt else None
        return record
