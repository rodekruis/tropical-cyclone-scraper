from __future__ import annotations

import logging
import sys

import requests

from .config import load_settings
from .deduplication import DeduplicationTracker
from .exporter import EventsFileExporter
from .gdacs import GdacsClient
from .models import EventSummary
from .service import filter_events
from .storage import ExcelFlowRepository



def main() -> int:
    settings = load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Initialize deduplication tracker
    dedup_tracker = DeduplicationTracker()
    already_exported = dedup_tracker.get_exported_ids()
    logger.info("Loaded %d previously exported event IDs from tracker", len(already_exported))

    gdacs = GdacsClient(settings.gdacs_api_url, settings.gdacs_timeout_seconds)
    
    # Fetch and filter events for each country
    all_events: list[EventSummary] = []
    
    for country_config in settings.country_configs:
        logger.info("Fetching events for country: %s with types: %s", country_config.iso3, ", ".join(country_config.event_types))
        raw_events = gdacs.fetch_events(
            settings.global_config.lookback_days,
            settings.global_config.lookahead_days,
            country_config.event_types,
            min_alert_level=settings.global_config.min_alert_level,
        )
        
        # Filter events for this country
        filtered = filter_events(
            raw_events,
            settings.global_config.lookback_days,
            settings.global_config.lookahead_days,
            min_alert_level=settings.global_config.min_alert_level,
            monitored_country_event_types={country_config.iso3: country_config.event_types},
        )
        all_events.extend(filtered)
    
    # Remove duplicates while preserving order
    seen_ids: set[str] = set()
    deduped_events: list[EventSummary] = []
    for event in all_events:
        if event.event_id not in seen_ids:
            seen_ids.add(event.event_id)
            deduped_events.append(event)

    if not deduped_events:
        logger.info("No events matched current filters")
        return 0
    tracked_duplicates = [event for event in deduped_events if event.event_id in already_exported]
    for event in tracked_duplicates:
        logger.info("Event seen in local tracker: %s", event.event_id)

    # Keep a CSV audit trail of currently matched events on every run.
    events_for_file_export = deduped_events
    logger.info(
        "Exporting %d filtered events to local files (%d also present in local tracker)",
        len(events_for_file_export),
        len(tracked_duplicates),
    )

    exporter = EventsFileExporter(settings.events_output_dir, settings.events_output_formats)
    created_files = exporter.export(events_for_file_export)
    for path in created_files:
        logger.info("Saved extracted events file: %s", path)

    if "excel" in settings.storage_targets:
        excel_repo = ExcelFlowRepository(
            flow_url=settings.excel_flow_url,
            timeout_seconds=settings.excel_flow_timeout_seconds,
        )
        try:
            marked = excel_repo.sync_events(deduped_events)
        except requests.RequestException as error:
            logger.warning(
                "Excel flow sync failed after retries; exported files were still written locally: %s",
                error,
            )
        else:
            new_event_ids = [event.event_id for event, is_new in marked if is_new]
            if new_event_ids:
                dedup_tracker.mark_exported(new_event_ids)

            logger.info("Saved %s new events to Microsoft 365 Excel flow", len(new_event_ids))

            for event, is_new in marked:
                logger.info("Event=%s new=%s countries=%s", event.name, is_new, event.countries_csv)
    else:
        # No Excel sink configured: keep local tracker behavior for non-Excel runs.
        exported_ids = [event.event_id for event in deduped_events]
        dedup_tracker.mark_exported(exported_ids)

    return 0


if __name__ == "__main__":
    sys.exit(main())
