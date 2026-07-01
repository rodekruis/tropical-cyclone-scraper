from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class CycloneSummary:
    event_id: str
    name: str
    start_time: datetime | None
    end_time: datetime | None
    countries: list[str] = field(default_factory=list)
    alert_level: str | None = None
    source_url: str | None = None

    @property
    def disaster_type(self) -> str:
        return "TC"

    @property
    def countries_csv(self) -> str:
        return ", ".join(sorted(set(self.countries)))


@dataclass(slots=True)
class EarthquakeSummary:
    event_id: str
    name: str
    start_time: datetime | None
    end_time: datetime | None
    countries: list[str] = field(default_factory=list)
    alert_level: str | None = None
    source_url: str | None = None

    @property
    def disaster_type(self) -> str:
        return "EQ"

    @property
    def countries_csv(self) -> str:
        return ", ".join(sorted(set(self.countries)))


EventSummary = CycloneSummary | EarthquakeSummary
