# GDACS Events Scraper

Python tool frame that:
- pulls tropical cyclones from GDACS
- supports configurable country and GDACS event type monitoring (for example: PHL+TC, PHL+EQ, IDN+TC)
- filters by:
  - active in the configured time window (`lookback_days` to `lookahead_days` in YAML)
  - country `iso3` + event type combinations configured in YAML
- saves extracted events to local CSV files before Excel write
- stores filtered cyclones in a Microsoft 365 Excel table via a Power Automate flow
- treats the workbook table as the source of truth for duplicate detection

Code development assisted by: [Copilot]

## Project layout

- `src/gdacs_events_scraper/gdacs.py`: GDACS API client
- `src/gdacs_events_scraper/service.py`: parsing and filter criteria logic
- `src/gdacs_events_scraper/storage.py`: Excel flow sink
- `src/gdacs_events_scraper/__main__.py`: orchestration entrypoint

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- A Microsoft 365 workbook table that the Power Automate flow can read and append to

## Configure

Copy `.env.example` to `.env` and fill values:

```powershell
Copy-Item .env.example .env
```

Required fields:
- `EXCEL_FLOW_URL`

GDACS country and event monitoring is configured in YAML (default path: `config/config.yaml`):

```yaml
gdacs_api_url: https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH
lookback_days: 1
lookahead_days: 7
min_alert_level: Green

country_configs:
  - iso3: PHL
    event_types:
      - TC
```

Each `country_configs` entry declares an `iso3` country code and the GDACS `event_types` to monitor for that country.
The fetch event type list is derived from the union of configured country event lists.
Multiple countries and multiple event types are also supported. 
``` yaml
country_configs:
  - iso3: PHL
    event_types:
      - TC
      - EQ
  - iso3: IDN
    event_types:
      - TC
      - EQ
```

Top-level ISO3 mappings are not supported; use `country_configs` entries with `iso3` and `event_types`.
`storage_targets` is optional and defaults to `excel` for the current runtime.
Power Automate controls which workbook/table is used.

### Output file types

Exported files are produced after filtering and before Excel persistence.

- `CSV`: best for quick review in Excel/BI tools and ad hoc sharing.

### Microsoft 365 Excel sink

Set `EXCEL_FLOW_URL` in `.env`. The flow should support two actions: return existing `event_id` values from the workbook table, then append only the missing rows.
The workbook table columns should be: `event_id`, `name`, `start_time`, `end_time`, `countries`, `alert_level`, `is_new`, `source_url`.
See [EXCEL_POWER_AUTOMATE_SETUP.md](EXCEL_POWER_AUTOMATE_SETUP.md) for the exact flow steps and request schema.

## Run locally

```powershell
uv sync
uv run python -m gdacs_events_scraper
```

## Docker run

```powershell
docker build -t gdacs-events-scraper:latest .
docker run --rm --env-file .env gdacs-events-scraper:latest
```

## CI/CD baseline

Workflow in `.github/workflows/ci.yml`:
- lint + tests
- build Docker image
- optional push to ACR if secrets are configured

### Suggested secrets

- `ACR_ENDPOINT`
- `ACR_USERNAME`
- `ACR_PASSWORD`
