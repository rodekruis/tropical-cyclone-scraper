from __future__ import annotations

import csv
from datetime import UTC, datetime

from gdacs_events_scraper.exporter import EventsFileExporter
from gdacs_events_scraper.models import CycloneSummary, EarthquakeSummary


def test_exporter_writes_csv_only(tmp_path) -> None:
    exporter = EventsFileExporter(str(tmp_path), ["json", "csv"])
    events = [
        CycloneSummary(
            event_id="tc-100",
            name="TC SAMPLE",
            start_time=datetime(2026, 6, 16, 0, 0, tzinfo=UTC),
            end_time=datetime(2026, 6, 17, 0, 0, tzinfo=UTC),
            countries=["Philippines", "Japan"],
            alert_level="Orange",
            source_url="https://example.com/tc-100",
        )
    ]

    output_files = exporter.export(events)

    assert len(output_files) == 1
    csv_files = [path for path in output_files if path.suffix == ".csv"]
    assert len(csv_files) == 1

    with csv_files[0].open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    assert rows[0]["event_id"] == "tc-100"
    assert rows[0]["countries"] == "Philippines;Japan"


def test_exporter_accepts_earthquake_summary(tmp_path) -> None:
    exporter = EventsFileExporter(str(tmp_path), ["csv"])
    events = [
        EarthquakeSummary(
            event_id="eq-100",
            name="EQ SAMPLE",
            start_time=datetime(2026, 6, 16, 3, 30, tzinfo=UTC),
            end_time=None,
            countries=["Japan", "Philippines", "Japan"],
            alert_level="Green",
            source_url="https://example.com/eq-100",
        )
    ]

    output_files = exporter.export(events)

    assert len(output_files) == 1
    with output_files[0].open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["event_id"] == "eq-100"
    assert rows[0]["countries"] == "Japan;Philippines;Japan"
    assert events[0].countries_csv == "Japan, Philippines"
