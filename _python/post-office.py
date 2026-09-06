"""
Find UK Post Office locations using the Overpass API (OpenStreetMap data).
No API key required.

Edit the CONFIG constants below, then just run:
    python uk_post_offices.py

Requires: requests
    pip install requests
"""

import json
import os
import sys
import requests

# ---------------------------------------------------------------------------
# CONFIG — edit these to change behaviour
# ---------------------------------------------------------------------------

LOCATION = "Cheltenham"        # UK postcode or place name to search around
RADIUS_M = 5000                 # search radius in metres
# Set BBOX to (south, west, north, east) to search a bounding box instead of
# LOCATION + RADIUS_M. Leave as None to use LOCATION/RADIUS_M.
BBOX = None                     # e.g. (51.49, -0.15, 51.52, -0.10)
OUT_DIR = "_data"         # folder to save JSON results into (relative to cwd)
OUT_FILENAME = "post-offices.json"
SAVE_TO_FILE = True             # set False to just print, not save

# ---------------------------------------------------------------------------

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def geocode_postcode(postcode: str):
    """Convert a UK postcode/place to lat/lon using Nominatim (free, no key)."""
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": postcode, "countrycodes": "gb", "format": "json", "limit": 1},
        headers={"User-Agent": "uk-post-office-finder/1.0"},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        raise ValueError(f"Could not geocode location: {postcode}")
    return float(results[0]["lat"]), float(results[0]["lon"])


def query_post_offices_radius(lat: float, lon: float, radius_m: int):
    """Query Overpass for post offices within radius_m metres of a point."""
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="post_office"](around:{radius_m},{lat},{lon});
      way["amenity"="post_office"](around:{radius_m},{lat},{lon});
    );
    out center tags;
    """
    return _run_query(query)


def query_post_offices_bbox(south: float, west: float, north: float, east: float):
    """Query Overpass for post offices within a bounding box."""
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="post_office"]({south},{west},{north},{east});
      way["amenity"="post_office"]({south},{west},{north},{east});
    );
    out center tags;
    """
    return _run_query(query)


def _run_query(query: str):
    last_error = None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    for url in OVERPASS_URLS:
        try:
            resp = requests.post(url, data={"data": query}, headers=headers, timeout=30)
            if resp.status_code != 200:
                last_error = f"{url} -> HTTP {resp.status_code}: {resp.text[:300]}"
                print(f"Warning: {last_error}", file=sys.stderr)
                continue
            return resp.json().get("elements", [])
        except requests.RequestException as e:
            last_error = f"{url} -> {e}"
            print(f"Warning: {last_error}", file=sys.stderr)
            continue
    raise RuntimeError(f"All Overpass mirrors failed. Last error: {last_error}")


def format_results(elements):
    if not elements:
        print("No post offices found.")
        return

    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name", "Post Office")
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")

        addr_parts = [
            tags.get("addr:housenumber"),
            tags.get("addr:street"),
            tags.get("addr:city"),
            tags.get("addr:postcode"),
        ]
        address = ", ".join(p for p in addr_parts if p)

        print(f"- {name}")
        if address:
            print(f"    Address: {address}")
        print(f"    Coords:  {lat}, {lon}")
        print(f"    OSM:     https://www.openstreetmap.org/{el['type']}/{el['id']}")
        print()


def save_results(elements, out_dir: str, filename: str):
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)

    records = []
    for el in elements:
        tags = el.get("tags", {})
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        addr_parts = [
            tags.get("addr:housenumber"),
            tags.get("addr:street"),
            tags.get("addr:city"),
            tags.get("addr:postcode"),
        ]
        records.append({
            "name": tags.get("name", "Post Office"),
            "address": ", ".join(p for p in addr_parts if p),
            "lat": lat,
            "lon": lon,
            "osm_type": el["type"],
            "osm_id": el["id"],
        })

    with open(out_path, "w") as f:
        json.dump(records, f, indent=2)

    print(f"Saved {len(records)} result(s) to {out_path}")


def main():
    if BBOX:
        elements = query_post_offices_bbox(*BBOX)
    else:
        lat, lon = geocode_postcode(LOCATION)
        print(f"Resolved '{LOCATION}' to {lat}, {lon}\n")
        elements = query_post_offices_radius(lat, lon, RADIUS_M)

    format_results(elements)

    if SAVE_TO_FILE:
        save_results(elements, OUT_DIR, OUT_FILENAME)


if __name__ == "__main__":
    main()