#!/usr/bin/env python3
"""
fetch_air_quality.py

Pulls live air-quality readings from DEFRA's UK-AIR Sensor Observation Service
(52°North Timeseries REST API) for stations around Cheltenham, and writes a
Jekyll-ready markdown page (air-quality.md).

API docs: https://uk-air.defra.gov.uk/sos-ukair/static/doc/api-doc/
Base URL: https://uk-air.defra.gov.uk/sos-ukair/api/v1

NOTE: This script could not be executed against the live API from the
sandbox this was written in (uk-air.defra.gov.uk is not on the allowed
network list here), so it has NOT been run end-to-end. Please run it
yourself and report back any errors / unexpected JSON shapes so it can
be corrected — the DEFRA JSON API is not consistently documented and
field names/behaviour have been known to drift.

Usage:
    python3 fetch_air_quality.py

Requires:
    pip install requests
"""

import sys
import datetime
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "https://uk-air.defra.gov.uk/sos-ukair/api/v1"

# Cheltenham town centre, used as the search origin
CENTRE_LAT = 51.8994
CENTRE_LON = -2.0783

# Covers Cheltenham + immediate surrounding area (Cheltenham, Bishop's
# Cleeve, Charlton Kings, etc). Increase if you want Gloucester included.
RADIUS_KM = 12

OUTPUT_FILE = "air-quality.md"

# Pollutants we care about for a public-facing summary. UK-AIR labels vary
# by station/procedure so this is a best-effort keyword match against the
# phenomenon label returned by the API.
POLLUTANTS_OF_INTEREST = {
    "pm2.5": "PM2.5 (fine particulates)",
    "pm10": "PM10 (particulates)",
    "no2": "Nitrogen dioxide (NO2)",
    "o3": "Ozone (O3)",
    "so2": "Sulphur dioxide (SO2)",
}

# Rough UK Daily Air Quality Index (DAQI) band 1 thresholds, used only to
# flag "Low / Moderate / High / Very High" per reading. These are
# simplified single-hour bands, not the official rolling-mean DAQI
# calculation — treat as indicative only. Values are in µg/m3.
# Source basis: DEFRA DAQI banding tables (uk-air.defra.gov.uk/air-pollution/daqi)
DAQI_BANDS = {
    "pm2.5": [(11, "Low"), (23, "Moderate"), (35, "High"), (999, "Very High")],
    "pm10":  [(16, "Low"), (33, "Moderate"), (50, "High"), (999, "Very High")],
    "no2":   [(67, "Low"), (134, "Moderate"), (200, "High"), (999, "Very High")],
    "o3":    [(50, "Low"), (100, "Moderate"), (240, "High"), (999, "Very High")],
    "so2":   [(88, "Low"), (177, "Moderate"), (266, "High"), (999, "Very High")],
}

TIMEOUT = 20  # seconds per request


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def match_pollutant_key(phenomenon_label: str):
    """Return our internal pollutant key if the label looks like one we track."""
    label = phenomenon_label.lower().replace(" ", "").replace(".", "")
    checks = {
        "pm2.5": ["pm2.5", "pm25"],
        "pm10": ["pm10"],
        "no2": ["no2", "nitrogendioxide"],
        "o3": ["o3", "ozone"],
        "so2": ["so2", "sulphurdioxide", "sulfurdioxide"],
    }
    for key, needles in checks.items():
        for n in needles:
            if n in label:
                return key
    return None


def daqi_band(pollutant_key: str, value: float):
    bands = DAQI_BANDS.get(pollutant_key)
    if bands is None or value is None:
        return "n/a"
    for threshold, name in bands:
        if value <= threshold:
            return name
    return "Very High"


def get_stations_near_cheltenham():
    """Query the stations collection, expanded, filtered to a radius around
    Cheltenham. Returns the raw list of station features."""
    params = {
        "near": (
            '{"center":{"type":"Point","coordinates":'
            f'[{CENTRE_LON},{CENTRE_LAT}]}},"radius":{RADIUS_KM}}}'
        ),
        "expanded": "true",
    }
    resp = requests.get(f"{BASE_URL}/stations", params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_timeseries_last_value(ts_id: str):
    """Fetch metadata + lastValue for a single timeseries id."""
    resp = requests.get(f"{BASE_URL}/timeseries/{ts_id}", timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def collect_readings():
    """Walk stations -> timeseries -> last value, filtered to pollutants
    of interest. Returns a list of dicts ready for rendering."""
    readings = []

    try:
        stations = get_stations_near_cheltenham()
    except requests.RequestException as exc:
        print(f"ERROR: could not fetch stations list: {exc}", file=sys.stderr)
        return readings

    if not isinstance(stations, list):
        print("ERROR: unexpected response shape for stations list", file=sys.stderr)
        return readings

    for station in stations:
        props = station.get("properties", {})
        station_label = props.get("label", "Unknown station")
        timeseries_map = props.get("timeseries", {})

        for ts_id, ts_meta in timeseries_map.items():
            phenomenon_label = ts_meta.get("phenomenon", {}).get("label", "")
            pollutant_key = match_pollutant_key(phenomenon_label)
            if pollutant_key is None:
                continue  # not one of the pollutants we're displaying

            try:
                ts_detail = get_timeseries_last_value(ts_id)
            except requests.RequestException as exc:
                print(f"WARNING: failed to fetch {ts_id} ({station_label}): {exc}",
                      file=sys.stderr)
                continue

            last_value = ts_detail.get("lastValue")
            if not last_value:
                continue

            value = last_value.get("value")
            timestamp_ms = last_value.get("timestamp")
            uom = ts_detail.get("uom", "")

            when = None
            if timestamp_ms:
                when = datetime.datetime.fromtimestamp(
                    timestamp_ms / 1000, tz=datetime.timezone.utc
                )

            readings.append({
                "station": station_label,
                "pollutant_key": pollutant_key,
                "pollutant_label": POLLUTANTS_OF_INTEREST[pollutant_key],
                "value": value,
                "uom": uom,
                "timestamp": when,
                "band": daqi_band(pollutant_key, value),
            })

    return readings


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_markdown(readings):
    generated = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    front_matter = (
        "---\n"
        "layout: default\n"
        "title: Cheltenham Air Quality\n"
        "permalink: /cheltenham-air-quality\n"
        f"date: {generated}\n"
        "---\n\n"
    )

    lines = [front_matter]
    lines.append("# Cheltenham Air Quality\n")
    lines.append(
        f"Live readings from DEFRA UK-AIR monitoring stations within "
        f"{RADIUS_KM}km of Cheltenham town centre. Last updated: {generated}.\n"
    )
    lines.append(
        "\n*Bands shown are an indicative single-reading guide based on DEFRA's "
        "Daily Air Quality Index thresholds, not the official rolling-average "
        "DAQI figure. Data source: "
        "[DEFRA UK-AIR](https://uk-air.defra.gov.uk/).*\n"
    )

    if not readings:
        lines.append(
            "\n> No data was returned from the DEFRA API at generation time. "
            "This page will update on the next scheduled run.\n"
        )
        return "".join(lines)

    # Group by station
    stations = {}
    for r in readings:
        stations.setdefault(r["station"], []).append(r)

    for station_name, station_readings in sorted(stations.items()):
        lines.append(f"\n## {station_name}\n")
        lines.append("\n| Pollutant | Reading | Band | Measured (UTC) |\n")
        lines.append("|---|---|---|---|\n")
        for r in sorted(station_readings, key=lambda x: x["pollutant_label"]):
            value_str = f"{r['value']} {r['uom']}".strip() if r["value"] is not None else "n/a"
            when_str = r["timestamp"].strftime("%Y-%m-%d %H:%M") if r["timestamp"] else "n/a"
            lines.append(
                f"| {r['pollutant_label']} | {value_str} | {r['band']} | {when_str} |\n"
            )

    return "".join(lines)


def main():
    readings = collect_readings()
    markdown = render_markdown(readings)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"Wrote {len(readings)} readings to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()