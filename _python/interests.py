#!/usr/bin/env python3
"""Fetch OSM points of interest (incl. plaques) near Cheltenham via Overpass,
write _data/points_of_interest.json as a distance-sorted array."""
import re
import json
import os
import math
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, "..", "_data", "points_of_interest.json")

LAT, LNG = 51.894, -2.083          # Cheltenham centre (from postcode-info)
RADIUS_M = 26000                   # ~16 miles
OVERPASS = "https://overpass-api.de/api/interpreter"
HEADERS  = {"User-Agent": "cheltenham-od/1.1 (https://uk.cheltenham-od; contact@cheltenham-od.uk)"}

# Each entry: (Overpass selector, human label).
CATEGORIES = [
    ('["tourism"="museum"]',                          "Museum"),
    ('["leisure"="stadium"]',                         "Stadium"),
    ('["historic"="castle"]',                         "Castle"),
    ('["historic"="monastery"]',                      "Historic site"),
    ('["historic"="ruins"]',                          "Historic site"),
    ('["historic"="monument"]',                       "Historic site"),
    ('["historic"="archaeological_site"]',            "Historic site"),
    ('["natural"="peak"]',                            "Hill"),
    ('["tourism"="attraction"]',                      "Attraction"),
    ('["historic"="memorial"]["memorial"="plaque"]',  "Plaque"),
]


def haversine_miles(lat1, lon1, lat2, lon2):
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(r * 2 * math.asin(math.sqrt(a)), 1)


def classify(tags):
    if tags.get("historic") == "memorial" and tags.get("memorial") == "plaque":
        return "Plaque"
    if tags.get("tourism") == "museum":
        return "Museum"
    if tags.get("leisure") == "stadium":
        return "Stadium"
    if tags.get("historic") == "castle":
        return "Castle"
    if tags.get("historic") in ("monastery", "ruins", "monument", "archaeological_site"):
        return "Historic site"
    if tags.get("natural") == "peak":
        return "Hill"
    if tags.get("tourism") == "attraction":
        return "Attraction"
    return "Other"


def wiki_url(tags):
    w = tags.get("wikipedia", "")
    if ":" in w:                                   # e.g. "en:Cheltenham Town Hall"
        lang, title = w.split(":", 1)
        return f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"
    return ""


def build_query():
    clauses = []
    for selector, _ in CATEGORIES:
        for kind in ("node", "way"):
            clauses.append(f"{kind}(around:{RADIUS_M},{LAT},{LNG}){selector};")
    return f"[out:json][timeout:90];({''.join(clauses)});out center tags;"

def normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if not re.match(r'^https?://', url, re.IGNORECASE):
        url = "https://" + url
    return url

def main():
    resp = requests.post(OVERPASS, data={"data": build_query()},
                         headers=HEADERS, timeout=120)
    resp.raise_for_status()
    elements = resp.json()["elements"]

    seen, pois = set(), []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name or name in seen:
            continue
        seen.add(name)
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None:
            continue
        pois.append({
            "name":        name,
            "category":    classify(tags),
            "distance":    haversine_miles(LAT, LNG, lat, lon),
            "postcode":    tags.get("addr:postcode", ""),
            "website": normalize_url(tags.get("website") or tags.get("contact:website", "")),
            "wikipedia":   wiki_url(tags),
            "gmaps":       f"https://www.google.com/maps/search/?api=1&query={lat},{lon}",
            "inscription": tags.get("inscription", ""),
            "lat":         lat,
            "lng":         lon,
        })

    pois.sort(key=lambda p: p["distance"])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(pois, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(pois)} points of interest to {OUT}")


if __name__ == "__main__":
    main()
