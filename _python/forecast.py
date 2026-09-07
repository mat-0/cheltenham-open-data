#!/usr/bin/env python3
"""Fetch a 10-day daily forecast from OpenWeather One Call 4.0 (1-day timeline),
write normalized JSON to _data/weather.json."""
import json
import os
import sys
from datetime import datetime, time, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, "..", "_data", "weather.json")

# Constants — no CLI args.
LOCATION = "Cheltenham"
LAT, LON = 51.90, -2.08
DAYS     = 10
BASE     = "https://api.openweathermap.org/data/4.0/onecall/timeline/1day"
API_KEY  = os.environ.get("OPEN_WEATHER_KEY", "817afffd47f4dc4a0e51cdb11285e3e6")


def to_c(t):
    # units=metric should return °C; guard in case the timeline endpoint ignores it.
    return round(t - 273.15, 1) if t > 100 else round(t, 1)


def start_of_today_utc():
    midnight = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
    return int(midnight.timestamp())


def local_time(unix, offset):
    """Return ('HH:MM', minutes-from-local-midnight) for a UTC unix time + offset."""
    dt = datetime.fromtimestamp(unix + offset, tz=timezone.utc)
    return dt.strftime("%H:%M"), dt.hour * 60 + dt.minute


def fetch_timeline(target):
    """Start the timeline at today, follow `next`; also return the location's UTC offset."""
    url = (f"{BASE}?lat={LAT}&lon={LON}&units=metric"
           f"&start={start_of_today_utc()}&appid={API_KEY}")
    records, offset = [], 0
    while url and len(records) < target:
        resp = requests.get(url, timeout=60)
        if resp.status_code == 401:
            sys.exit("401 from OpenWeather — activate the 'One Call API 4.0' "
                     "subscription for this key, then re-run.")
        resp.raise_for_status()
        payload = resp.json()
        offset = payload.get("timezone_offset", 0)
        records.extend(payload.get("data", []))
        url = payload.get("next")
    return records[:target], offset


def normalize(records, offset):
    days = []
    for d in records:
        w = (d.get("weather") or [{}])[0]
        sr_str, sr_min = local_time(d["sunrise"], offset)
        ss_str, ss_min = local_time(d["sunset"], offset)
        daylight = ss_min - sr_min
        days.append({
            "date":          datetime.fromtimestamp(d["dt"] + offset, tz=timezone.utc).strftime("%Y-%m-%d"),
            "min":           to_c(d["temp"]["min"]),
            "max":           to_c(d["temp"]["max"]),
            "icon":          w.get("icon", ""),
            "desc":          w.get("description", ""),
            "pop":           d.get("pop", 0),
            "wind":          round(d.get("wind_speed", 0), 1),   # m/s
            "humidity":      d.get("humidity", 0),
            "uvi":           d.get("uvi", 0),
            "sunrise":       sr_str,
            "sunset":        ss_str,
            "sun_start":     sr_min,
            "sun_end":       ss_min,
            "daylight":      daylight,                            # minutes
            "daylight_str":  f"{daylight // 60}h {daylight % 60:02d}m",
        })
    return {
        "location": LOCATION,
        "units":    "metric",
        "updated":  datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "days":     days,
    }


def main():
    if not API_KEY:
        sys.exit("OPEN_WEATHER_KEY is not set in the environment.")
    records, offset = fetch_timeline(DAYS)
    data = normalize(records, offset)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(data['days'])} days to {OUT}")


if __name__ == "__main__":
    main()
