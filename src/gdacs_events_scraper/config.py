from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from dotenv import find_dotenv, load_dotenv


DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_EVENTS_OUTPUT_DIR = "output/events"
DEFAULT_EVENTS_OUTPUT_FORMATS = "csv"


@dataclass(slots=True)
class GlobalConfig:
    lookback_days: int
    lookahead_days: int
    min_alert_level: str = "Green"


@dataclass(slots=True)
class CountryConfig:
    iso3: str
    event_types: list[str]


@dataclass(slots=True)
class Settings:
    gdacs_api_url: str
    gdacs_timeout_seconds: int
    gdacs_event_types_file: str
    global_config: GlobalConfig
    country_configs: list[CountryConfig]
    storage_targets: list[str]
    events_output_dir: str
    events_output_formats: list[str]
    excel_flow_url: str
    excel_flow_timeout_seconds: int
    log_level: str



def load_settings() -> Settings:
    load_dotenv(find_dotenv(usecwd=True))
    event_types_file = os.getenv("GDACS_EVENT_TYPES_FILE", "config/config.yaml")
    event_config = _load_event_config(event_types_file)
    storage_targets_env = os.getenv("STORAGE_TARGETS")
    storage_targets = (
        _load_storage_targets(storage_targets_env)
        if storage_targets_env is not None
        else event_config["storage_targets"]
    )

    global_config = GlobalConfig(
        lookback_days=event_config["global_config"].lookback_days,
        lookahead_days=event_config["global_config"].lookahead_days,
        min_alert_level=event_config["global_config"].min_alert_level,
    )

    return Settings(
        gdacs_api_url=str(event_config["gdacs_api_url"]),
        gdacs_timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
        gdacs_event_types_file=event_types_file,
        global_config=global_config,
        country_configs=event_config["country_configs"],
        storage_targets=storage_targets,
        events_output_dir=DEFAULT_EVENTS_OUTPUT_DIR,
        events_output_formats=_load_output_formats(DEFAULT_EVENTS_OUTPUT_FORMATS),
        excel_flow_url=os.getenv("EXCEL_FLOW_URL", ""),
        excel_flow_timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )


def _coerce_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        try:
            return int(cleaned)
        except ValueError:
            return None
    return None


def _load_event_config(file_path: str) -> dict[str, object]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid configuration format in {file_path}: expected YAML dict")

    # Extract global parameters
    lookback_days = _coerce_int(data.get("lookback_days"))
    if lookback_days is None:
        raise ValueError("Missing required 'lookback_days' in configuration")
    
    lookahead_days = _coerce_int(data.get("lookahead_days"))
    if lookahead_days is None:
        raise ValueError("Missing required 'lookahead_days' in configuration")

    raw_alert_level = data.get("min_alert_level")
    min_alert_level = str(raw_alert_level).strip() if raw_alert_level is not None else "Green"

    global_config = GlobalConfig(lookback_days=lookback_days, lookahead_days=lookahead_days, min_alert_level=min_alert_level)

    raw_gdacs_api_url = data.get("gdacs_api_url")
    gdacs_api_url = str(raw_gdacs_api_url).strip() if raw_gdacs_api_url is not None else ""
    if not gdacs_api_url:
        raise ValueError("Missing required 'gdacs_api_url' in configuration")

    # Extract country configurations
    country_configs = _load_country_configs(data)
    if not country_configs:
        raise ValueError("No country configurations found in configuration file")

    return {
        "gdacs_api_url": gdacs_api_url,
        "global_config": global_config,
        "country_configs": country_configs,
        "storage_targets": _load_storage_targets(data.get("storage_targets"), default="excel"),
    }


def _normalize_event_types(raw: object) -> list[str]:
    if isinstance(raw, str):
        cleaned = raw.strip().upper()
        return [cleaned] if cleaned else []

    if isinstance(raw, list):
        normalized: list[str] = []
        for item in raw:
            if not isinstance(item, str):
                continue
            cleaned = item.strip().upper()
            if not cleaned:
                continue
            if cleaned not in normalized:
                normalized.append(cleaned)
        return normalized

    return []


def _load_country_configs(data: dict[str, object]) -> list[CountryConfig]:
    return _load_explicit_country_configs(data.get("country_configs"))


def _load_explicit_country_configs(raw: object) -> list[CountryConfig]:
    if not isinstance(raw, list):
        return []

    country_configs: list[CountryConfig] = []
    for item in raw:
        if not isinstance(item, dict):
            continue

        raw_iso3 = item.get("iso3")
        if not isinstance(raw_iso3, str):
            continue

        iso3 = raw_iso3.strip().upper()
        if len(iso3) != 3 or not iso3.isalpha():
            continue

        event_types = _normalize_event_types(item.get("event_types"))
        if not event_types:
            continue

        country_configs.append(CountryConfig(iso3=iso3, event_types=event_types))

    return country_configs


def _load_output_formats(raw_formats: str) -> list[str]:
    supported = {"csv"}
    cleaned: list[str] = []

    for value in raw_formats.split(","):
        format_name = value.strip().lower()
        if not format_name or format_name not in supported:
            continue
        if format_name not in cleaned:
            cleaned.append(format_name)

    return cleaned or ["csv"]


def _load_storage_targets(raw: object | None, default: str | None = None) -> list[str]:
    supported = {"cosmos", "excel"}
    values: list[str] = []

    if raw is None:
        raw_values: list[str] = [default] if default else []
    elif isinstance(raw, str):
        raw_values = [part.strip() for part in raw.split(",")]
    elif isinstance(raw, list):
        raw_values = [part.strip() for part in raw if isinstance(part, str)]
    else:
        raw_values = [default] if default else []

    for value in raw_values:
        cleaned = value.lower()
        if not cleaned:
            continue
        if cleaned == "both":
            for target in ("cosmos", "excel"):
                if target not in values:
                    values.append(target)
            continue
        if cleaned not in supported:
            continue
        if cleaned not in values:
            values.append(cleaned)

    return values or ([default] if default else ["excel"])

