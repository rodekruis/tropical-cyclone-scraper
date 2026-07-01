from __future__ import annotations

from pathlib import Path

import pytest

from gdacs_events_scraper.config import _load_output_formats, load_settings


def test_load_output_formats_filters_and_deduplicates() -> None:
    result = _load_output_formats("json,csv,json,xml")

    assert result == ["csv"]


def test_load_output_formats_defaults_when_empty() -> None:
    result = _load_output_formats(" , ")

    assert result == ["csv"]


def test_load_settings_reads_lookback_and_lookahead_from_yaml(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "event-types.yaml"
    config_file.write_text(
        "gdacs_api_url: https://yaml.example/gdacs\n"
        "lookback_days: 2\n"
        "lookahead_days: 9\n"
        "country_configs:\n"
        "  - iso3: PHL\n"
        "    event_types:\n"
        "      - TC\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GDACS_EVENT_TYPES_FILE", str(config_file))
    monkeypatch.delenv("LOOKBACK_DAYS", raising=False)
    monkeypatch.delenv("LOOKAHEAD_DAYS", raising=False)

    settings = load_settings()

    assert settings.global_config.lookback_days == 2
    assert settings.global_config.lookahead_days == 9


def test_load_settings_ignores_window_env_overrides(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "event-types.yaml"
    config_file.write_text(
        "gdacs_api_url: https://yaml.example/gdacs\n"
        "lookback_days: 2\n"
        "lookahead_days: 9\n"
        "country_configs:\n"
        "  - iso3: PHL\n"
        "    event_types:\n"
        "      - TC\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GDACS_EVENT_TYPES_FILE", str(config_file))
    monkeypatch.setenv("LOOKBACK_DAYS", "1")
    monkeypatch.setenv("LOOKAHEAD_DAYS", "7")

    settings = load_settings()

    assert settings.global_config.lookback_days == 2
    assert settings.global_config.lookahead_days == 9


def test_load_settings_reads_country_event_mapping(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "event-types.yaml"
    config_file.write_text(
        "gdacs_api_url: https://yaml.example/gdacs\n"
        "lookback_days: 2\n"
        "lookahead_days: 9\n"
        "country_configs:\n"
        "  - iso3: PHL\n"
        "    event_types:\n"
        "      - TC\n"
        "      - EQ\n"
        "  - iso3: IDN\n"
        "    event_types:\n"
        "      - TC\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GDACS_EVENT_TYPES_FILE", str(config_file))

    settings = load_settings()

    country_configs = {cc.iso3: cc.event_types for cc in settings.country_configs}
    assert country_configs == {
        "PHL": ["TC", "EQ"],
        "IDN": ["TC"],
    }


def test_load_settings_rejects_legacy_country_mapping(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "event-types.yaml"
    config_file.write_text(
        "gdacs_api_url: https://yaml.example/gdacs\n"
        "PHL:\n"
        "  - TC\n"
        "  - EQ\n"
        "lookback_days: 1\n"
        "lookahead_days: 7\n"
        "country_configs: []\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GDACS_EVENT_TYPES_FILE", str(config_file))

    with pytest.raises(ValueError, match="No country configurations found"):
        load_settings()


def test_load_settings_preserves_min_alert_level(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "event-types.yaml"
    config_file.write_text(
        "gdacs_api_url: https://yaml.example/gdacs\n"
        "lookback_days: 1\n"
        "lookahead_days: 7\n"
        "min_alert_level: Orange\n"
        "country_configs:\n"
        "  - iso3: PHL\n"
        "    event_types:\n"
        "      - TC\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GDACS_EVENT_TYPES_FILE", str(config_file))

    settings = load_settings()

    assert settings.global_config.min_alert_level == "Orange"


def test_load_settings_reads_storage_targets(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "event-types.yaml"
    config_file.write_text(
        "gdacs_api_url: https://yaml.example/gdacs\n"
        "lookback_days: 1\n"
        "lookahead_days: 7\n"
        "storage_targets:\n"
        "  - cosmos\n"
        "  - excel\n"
        "country_configs:\n"
        "  - iso3: PHL\n"
        "    event_types:\n"
        "      - TC\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GDACS_EVENT_TYPES_FILE", str(config_file))

    settings = load_settings()

    assert settings.storage_targets == ["cosmos", "excel"]


def test_load_settings_defaults_storage_targets_to_excel(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "event-types.yaml"
    config_file.write_text(
        "gdacs_api_url: https://yaml.example/gdacs\n"
        "lookback_days: 1\n"
        "lookahead_days: 7\n"
        "country_configs:\n"
        "  - iso3: PHL\n"
        "    event_types:\n"
        "      - TC\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GDACS_EVENT_TYPES_FILE", str(config_file))

    settings = load_settings()

    assert settings.storage_targets == ["excel"]


def test_load_settings_does_not_require_excel_table_name(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "event-types.yaml"
    config_file.write_text(
        "gdacs_api_url: https://yaml.example/gdacs\n"
        "lookback_days: 1\n"
        "lookahead_days: 7\n"
        "country_configs:\n"
        "  - iso3: PHL\n"
        "    event_types:\n"
        "      - TC\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GDACS_EVENT_TYPES_FILE", str(config_file))

    settings = load_settings()

    assert settings.global_config.lookback_days == 1


def test_load_settings_reads_gdacs_api_url_from_yaml(monkeypatch, tmp_path: Path) -> None:
    config_file = tmp_path / "event-types.yaml"
    config_file.write_text(
        "gdacs_api_url: https://yaml.example/custom\n"
        "lookback_days: 1\n"
        "lookahead_days: 7\n"
        "country_configs:\n"
        "  - iso3: PHL\n"
        "    event_types:\n"
        "      - TC\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GDACS_EVENT_TYPES_FILE", str(config_file))
    monkeypatch.setenv("GDACS_API_URL", "https://env.example/ignored")

    settings = load_settings()

    assert settings.gdacs_api_url == "https://yaml.example/custom"
