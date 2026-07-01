from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from .models import CycloneSummary, EarthquakeSummary, EventSummary

LOGGER = logging.getLogger(__name__)

ALERT_LEVEL_RANKS = {
    "GREEN": 0,
    "ORANGE": 1,
    "RED": 2,
}
DEFAULT_COUNTRY_EVENT_TYPES = {"PHL": {"TC"}}


def coerce_text(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None

    if isinstance(value, (int, float, bool)):
        cleaned = str(value).strip()
        return cleaned or None

    if isinstance(value, dict):
        for key in (
            "value",
            "name",
            "label",
            "text",
            "level",
            "alertlevel",
            "url",
            "link",
            "href",
            "description",
        ):
            candidate = coerce_text(value.get(key))
            if candidate:
                return candidate
        return None

    if isinstance(value, list):
        for item in value:
            candidate = coerce_text(item)
            if candidate:
                return candidate
        return None

    return None


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None

    cleaned = value.replace("Z", "+00:00")
    for fmt in (None, "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.fromisoformat(cleaned) if fmt is None else datetime.strptime(cleaned, fmt)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except ValueError:
            continue

    return None


def normalize_countries(raw: Any) -> list[str]:
    countries: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                countries.append(item.strip())
            elif isinstance(item, dict):
                candidate = item.get("iso3") or item.get("name") or item.get("country")
                if isinstance(candidate, str):
                    countries.append(candidate.strip())
    elif isinstance(raw, str):
        countries = [part.strip() for part in raw.replace(";", ",").split(",") if part.strip()]

    return [country for country in countries if country]


def normalize_iso3(value: str) -> str | None:
    cleaned = value.strip().upper()
    if len(cleaned) == 3 and cleaned.isalpha():
        return cleaned
    return None


def is_country_event_monitored(
    countries: list[str],
    disaster_type: str,
    monitored_country_event_types: dict[str, set[str]] | None,
) -> bool:
    if monitored_country_event_types is None:
        monitored_country_event_types = DEFAULT_COUNTRY_EVENT_TYPES

    event_type = disaster_type.strip().upper()
    iso3_codes = {iso3 for country in countries if (iso3 := normalize_iso3(country))}
    if not iso3_codes:
        return False

    for iso3 in iso3_codes:
        allowed_events = monitored_country_event_types.get(iso3)
        if allowed_events and event_type in allowed_events:
            return True

    return False


def normalize_event_type(raw_event: dict[str, Any]) -> str | None:
    event_type = coerce_text(
        raw_event.get("eventtype")
        or raw_event.get("eventType")
        or raw_event.get("type")
        or raw_event.get("typecode")
    )
    if not event_type:
        return None
    return event_type.strip().upper()


def is_active(event: EventSummary, now: datetime) -> bool:
    if event.start_time and event.end_time:
        return event.start_time <= now <= event.end_time
    if event.start_time and not event.end_time:
        return event.start_time <= now
    return False


def is_active_in_next_days(event: EventSummary, now: datetime, lookahead_days: int) -> bool:
    window_start = now
    window_end = now + timedelta(days=lookahead_days)
    start = event.start_time
    end = event.end_time or start

    if not start:
        return False
    return start <= window_end and end >= window_start


def is_active_in_window(
    event: EventSummary,
    now: datetime,
    lookback_days: int,
    lookahead_days: int,
) -> bool:
    window_start = now - timedelta(days=lookback_days)
    window_end = now + timedelta(days=lookahead_days)
    start = event.start_time
    end = event.end_time or start

    if not start:
        return False
    return start <= window_end and end >= window_start


def to_summary(raw_event: dict[str, Any]) -> EventSummary | None:
    event_name = coerce_text(
        raw_event.get("name")
        or raw_event.get("eventname")
        or raw_event.get("eventName")
        or raw_event.get("episodealert")
        or raw_event.get("description")
    )
    event_id = coerce_text(raw_event.get("eventid") or raw_event.get("eventId") or raw_event.get("id"))

    if not event_id or not event_name:
        return None

    countries = normalize_countries(
        raw_event.get("countries")
        or raw_event.get("exposedcountries")
        or raw_event.get("affectedcountries")
        or raw_event.get("country")
    )

    start_time = parse_dt(
        raw_event.get("fromdate")
        or raw_event.get("startdate")
        or raw_event.get("startDate")
        or raw_event.get("begindate")
    )
    end_time = parse_dt(
        raw_event.get("todate")
        or raw_event.get("enddate")
        or raw_event.get("endDate")
        or raw_event.get("expiredate")
    )

    summary_class = EarthquakeSummary if normalize_event_type(raw_event) == "EQ" else CycloneSummary
    return summary_class(
        event_id=event_id,
        name=event_name,
        start_time=start_time,
        end_time=end_time,
        countries=countries,
        alert_level=coerce_text(raw_event.get("alertlevel") or raw_event.get("alertLevel")),
        source_url=coerce_text(raw_event.get("url") or raw_event.get("link")),
    )


def alert_level_meets_minimum(alert_level: str | None, min_alert_level: str) -> bool:
    event_rank = ALERT_LEVEL_RANKS.get((alert_level or "").strip().upper(), ALERT_LEVEL_RANKS["GREEN"])
    minimum_rank = ALERT_LEVEL_RANKS.get((min_alert_level or "").strip().upper(), ALERT_LEVEL_RANKS["GREEN"])

    return event_rank >= minimum_rank


def filter_events(
    raw_events: list[dict[str, Any]],
    lookback_days: int,
    lookahead_days: int,
    min_alert_level: str = "Green",
    monitored_country_event_types: dict[str, list[str]] | None = None,
) -> list[EventSummary]:
    now = datetime.now(UTC)
    output: list[EventSummary] = []
    normalized_country_event_types = {
        iso3.strip().upper(): {event_type.strip().upper() for event_type in event_types if event_type.strip()}
        for iso3, event_types in (monitored_country_event_types or {}).items()
        if iso3.strip()
    } or DEFAULT_COUNTRY_EVENT_TYPES

    seen_ids: set[str] = set()
    for raw_event in raw_events:
        summary = to_summary(raw_event)
        if summary is None:
            continue
        if summary.event_id in seen_ids:
            continue
        if not is_active_in_window(summary, now, lookback_days, lookahead_days):
            continue
        if not alert_level_meets_minimum(summary.alert_level, min_alert_level):
            continue
        if not is_country_event_monitored(
            summary.countries,
            summary.disaster_type,
            normalized_country_event_types,
        ):
            continue

        seen_ids.add(summary.event_id)
        output.append(summary)

    LOGGER.info("Filtered %s GDACS events", len(output))
    return output


def filter_cyclones(
    raw_events: list[dict[str, Any]],
    lookback_days: int,
    lookahead_days: int,
    min_alert_level: str = "Green",
    monitored_country_event_types: dict[str, list[str]] | None = None,
) -> list[CycloneSummary]:
    output = filter_events(
        raw_events,
        lookback_days,
        lookahead_days,
        min_alert_level=min_alert_level,
        monitored_country_event_types=monitored_country_event_types,
    )
    cyclones = [event for event in output if isinstance(event, CycloneSummary)]
    LOGGER.info("Filtered %s tropical cyclones", len(cyclones))
    return cyclones
