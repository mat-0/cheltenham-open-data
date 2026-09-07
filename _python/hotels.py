#!/usr/bin/env python3
"""Fetch hotels and guest houses near Cheltenham from OpenStreetMap via Overpass,
write _data/hotels.json."""
import json
import os
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, "..", "_data", "hotels.json")

LAT, LNG = 51.894, -2.083          # Cheltenham centre
RADIUS_M = 6000                    # ~3.7 miles — keeps it to the town
OVERPASS = "https://overpass-api.de/api/interpreter"
HEADERS  = {"User-Agent": "cheltenham-od/1.2 (https://cheltenham-od.uk; contact@cheltenham-od.uk)"}

TYPES = {"hotel": "Hotel", "guest_house": "Guest house"}


def address(tags):
    line = " ".join(p for p in (tags.get("addr:housenumber", "").strip(),
                                 tags.get("addr:street", "").strip()) if p)
    suburb = tags.get("addr:suburb", "").strip()
    return ", ".join(p for p in (line, suburb) if p)


def parse_stars(tags):
    digits = "".join(c for c in tags.get("stars", "").strip() if c.isdigit())
    return int(digits) if digits else None


def build_query():
    clauses = []
    for value in TYPES:
        for kind in ("node", "way"):
            clauses.append(f'{kind}(around:{RADIUS_M},{LAT},{LNG})["tourism"="{value}"]["name"];')
    return f"[out:json][timeout:90];({''.join(clauses)});out center tags;"


def main():
    resp = requests.post(OVERPASS, data={"data": build_query()},
                         headers=HEADERS, timeout=120)
    resp.raise_for_status()
    elements = resp.json()["elements"]

    seen, hotels = set(), []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        hotels.append({
            "name":     name,
            "type":     TYPES.get(tags.get("tourism"), "Hotel"),
            "stars":    parse_stars(tags),
            "address":  address(tags),
            "postcode": tags.get("addr:postcode", ""),
            "lat":      el.get("lat") or el.get("center", {}).get("lat"),
            "lng":      el.get("lon") or el.get("center", {}).get("lon")

        })

    hotels.sort(key=lambda h: h["name"])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(hotels, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(hotels)} hotels and guest houses to {OUT}")


if __name__ == "__main__":
    main()
