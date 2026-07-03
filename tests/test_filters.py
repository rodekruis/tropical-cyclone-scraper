from __future__ import annotations

from datetime import UTC, datetime, timedelta

from gdacs_events_scraper.models import CycloneSummary, EarthquakeSummary
from gdacs_events_scraper.service import (
    alert_level_meets_minimum,
    filter_cyclones,
    filter_events,
    is_active,
    is_active_in_next_days,
    is_active_in_window,
    is_country_event_monitored,
    to_summary,
)



def test_is_country_event_monitored_with_iso3_match() -> None:
    monitored = {"PHL": {"TC", "EQ"}, "IDN": {"TC"}}

    assert is_country_event_monitored(["PHL"], "TC", monitored) is True



def test_is_country_event_monitored_rejects_name_only_country() -> None:
    monitored = {"PHL": {"TC"}}

    assert is_country_event_monitored(["Philippines"], "TC", monitored) is False


def test_is_country_event_monitored_rejects_unconfigured_event() -> None:
    monitored = {"PHL": {"TC"}}

    assert is_country_event_monitored(["PHL"], "EQ", monitored) is False



def test_is_active_true_with_range() -> None:
    now = datetime.now(UTC)
    cyclone = CycloneSummary(
        event_id="tc-1",
        name="TC ONE",
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=1),
        countries=["Philippines"],
    )
    assert is_active(cyclone, now) is True



def test_is_active_in_next_days_true() -> None:
    now = datetime.now(UTC)
    cyclone = CycloneSummary(
        event_id="tc-2",
        name="TC TWO",
        start_time=now + timedelta(days=2),
        end_time=now + timedelta(days=4),
        countries=["Philippines"],
    )
    assert is_active_in_next_days(cyclone, now, lookahead_days=7) is True


def test_is_active_in_window_true_for_recent_past_event() -> None:
    now = datetime.now(UTC)
    cyclone = CycloneSummary(
        event_id="tc-2b",
        name="TC TWO B",
        start_time=now - timedelta(hours=18),
        end_time=now - timedelta(hours=6),
        countries=["Philippines"],
    )

    assert is_active_in_window(cyclone, now, lookback_days=1, lookahead_days=7) is True


def test_is_active_in_window_false_when_outside_lookback() -> None:
    now = datetime.now(UTC)
    cyclone = CycloneSummary(
        event_id="tc-2c",
        name="TC TWO C",
        start_time=now - timedelta(days=3),
        end_time=now - timedelta(days=2),
        countries=["Philippines"],
    )

    assert is_active_in_window(cyclone, now, lookback_days=1, lookahead_days=7) is False


def test_to_summary_handles_alert_and_url_dict_data() -> None:
    raw_event = {
        "eventid": "tc-3",
        "name": "TC THREE",
        "fromdate": "2026-06-15T00:00:00Z",
        "todate": "2026-06-20T00:00:00Z",
        "countries": ["Philippines"],
        "alertlevel": {"name": "Orange"},
        "url": {"href": "https://example.com/tc-3"},
    }

    summary = to_summary(raw_event)

    assert summary is not None
    assert summary.alert_level == "Orange"
    assert summary.source_url == "https://example.com/tc-3"


def test_to_summary_returns_earthquake_summary_for_eq_event() -> None:
    raw_event = {
        "eventid": "eq-1",
        "eventtype": "EQ",
        "name": "EQ ONE",
        "fromdate": "2026-06-16T00:00:00Z",
        "countries": ["Philippines"],
    }

    summary = to_summary(raw_event)

    assert isinstance(summary, EarthquakeSummary)
    assert summary.event_id == "eq-1"


def test_filter_events_ignores_top_level_iso3_when_affectedcountries_missing() -> None:
    now = datetime.now(UTC)
    in_window_start = (now - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    in_window_end = (now + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")

    raw_events = [
        {
            "eventid": "1001279",
            "eventtype": "TC",
            "name": "Tropical Cyclone BAVI-26",
            "fromdate": in_window_start,
            "todate": in_window_end,
            "country": "Northern Mariana Islands",
            "affectedcountries": [],
            "iso3": "MNP",
            "alertlevel": "Red",
        }
    ]

    result = filter_events(
        raw_events,
        lookback_days=1,
        lookahead_days=7,
        monitored_country_event_types={"MNP": ["TC"]},
    )

    assert result == []


def test_filter_events_uses_affectedcountries_iso3() -> None:
    now = datetime.now(UTC)
    in_window_start = (now - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    in_window_end = (now + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")

    raw_events = [
        {
            "eventid": "1001279",
            "eventtype": "TC",
            "name": "Tropical Cyclone BAVI-26",
            "fromdate": in_window_start,
            "todate": in_window_end,
            "country": "Northern Mariana Islands",
            "affectedcountries": [{"iso3": "MNP"}],
            "iso3": "PHL",
            "alertlevel": "Red",
        }
    ]

    result = filter_events(
        raw_events,
        lookback_days=1,
        lookahead_days=7,
        monitored_country_event_types={"MNP": ["TC"]},
    )

    assert [event.event_id for event in result] == ["1001279"]
    assert result[0].countries == ["MNP"]


def test_alert_level_meets_minimum_treats_threshold_as_inclusive() -> None:
    assert alert_level_meets_minimum("Green", "Green") is True
    assert alert_level_meets_minimum("Orange", "Green") is True
    assert alert_level_meets_minimum("Red", "Orange") is True
    assert alert_level_meets_minimum("Yellow", "Orange") is False
    assert alert_level_meets_minimum(None, "Green") is True
    assert alert_level_meets_minimum(None, "Orange") is False


def test_filter_cyclones_applies_lookback_and_lookahead_window() -> None:
    now = datetime.now(UTC)
    in_lookback_start = (now - timedelta(hours=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    in_lookback_end = (now - timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
    in_lookahead_start = (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    in_lookahead_end = (now + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_of_window_start = (now - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_of_window_end = (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

    raw_events = [
        {
            "eventid": "tc-a",
            "name": "TC A",
            "fromdate": in_lookback_start,
            "todate": in_lookback_end,
            "affectedcountries": [{"iso3": "PHL"}],
        },
        {
            "eventid": "tc-b",
            "name": "TC B",
            "fromdate": in_lookahead_start,
            "todate": in_lookahead_end,
            "affectedcountries": [{"iso3": "PHL"}],
        },
        {
            "eventid": "tc-c",
            "name": "TC C",
            "fromdate": out_of_window_start,
            "todate": out_of_window_end,
            "affectedcountries": [{"iso3": "PHL"}],
        },
    ]

    result = filter_cyclones(raw_events, lookback_days=1, lookahead_days=7)

    assert [cyclone.event_id for cyclone in result] == ["tc-a", "tc-b"]


def test_filter_events_includes_earthquake_and_cyclone_matches() -> None:
    now = datetime.now(UTC)
    in_window_start = (now - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    in_window_end = (now + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")

    raw_events = [
        {
            "eventid": "eq-a",
            "eventtype": "EQ",
            "name": "EQ A",
            "fromdate": in_window_start,
            "todate": in_window_end,
            "affectedcountries": [{"iso3": "PHL"}],
        },
        {
            "eventid": "tc-a",
            "eventtype": "TC",
            "name": "TC A",
            "fromdate": in_window_start,
            "todate": in_window_end,
            "affectedcountries": [{"iso3": "PHL"}],
        },
    ]

    result = filter_events(
        raw_events,
        lookback_days=1,
        lookahead_days=7,
        monitored_country_event_types={"PHL": ["EQ", "TC"]},
    )

    assert len(result) == 2
    assert isinstance(result[0], EarthquakeSummary)
    assert isinstance(result[1], CycloneSummary)


def test_filter_events_applies_minimum_alert_level_threshold() -> None:
    now = datetime.now(UTC)
    in_window_start = (now - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    in_window_end = (now + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")

    raw_events = [
        {
            "eventid": "tc-green",
            "eventtype": "TC",
            "name": "TC GREEN",
            "fromdate": in_window_start,
            "todate": in_window_end,
            "affectedcountries": [{"iso3": "PHL"}],
            "alertlevel": "Green",
        },
        {
            "eventid": "tc-orange",
            "eventtype": "TC",
            "name": "TC ORANGE",
            "fromdate": in_window_start,
            "todate": in_window_end,
            "affectedcountries": [{"iso3": "PHL"}],
            "alertlevel": "Orange",
        },
        {
            "eventid": "tc-red",
            "eventtype": "TC",
            "name": "TC RED",
            "fromdate": in_window_start,
            "todate": in_window_end,
            "affectedcountries": [{"iso3": "PHL"}],
            "alertlevel": "Red",
        },
    ]

    result = filter_events(
        raw_events,
        lookback_days=1,
        lookahead_days=7,
        min_alert_level="Orange",
        monitored_country_event_types={"PHL": ["TC"]},
    )

    assert [event.event_id for event in result] == ["tc-orange", "tc-red"]


def test_filter_events_applies_country_event_mapping() -> None:
    now = datetime.now(UTC)
    in_window_start = (now - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    in_window_end = (now + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")

    raw_events = [
        {
            "eventid": "eq-phl",
            "eventtype": "EQ",
            "name": "EQ PHL",
            "fromdate": in_window_start,
            "todate": in_window_end,
            "affectedcountries": [{"iso3": "PHL"}],
        },
        {
            "eventid": "tc-idn",
            "eventtype": "TC",
            "name": "TC IDN",
            "fromdate": in_window_start,
            "todate": in_window_end,
            "affectedcountries": [{"iso3": "IDN"}],
        },
        {
            "eventid": "eq-idn",
            "eventtype": "EQ",
            "name": "EQ IDN",
            "fromdate": in_window_start,
            "todate": in_window_end,
            "affectedcountries": [{"iso3": "IDN"}],
        },
    ]

    result = filter_events(
        raw_events,
        lookback_days=1,
        lookahead_days=7,
        monitored_country_event_types={
            "PHL": ["TC", "EQ"],
            "IDN": ["TC"],
        },
    )

    assert [event.event_id for event in result] == ["eq-phl", "tc-idn"]
