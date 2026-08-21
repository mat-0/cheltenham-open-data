#!/usr/bin/env python3
"""
build_house_prices.py

Re-runnable data build. Does NOT author HTML or markdown structure - those
are static, hand-edited files (cheltenham-house-prices.md, house-pricing.html,
land-registry-table.js). This script only:

  1. Queries SPARQL for Cheltenham transactions (postcode district GL50-GL54
     AND town = CHELTENHAM, cross-checked).
  2. Computes summary stats.
  3. Injects one prose sentence into the markdown page's "land_registry"
     marker (via helper.replace_chunk - never touches anything outside
     the marker, so surrounding hand-written prose is untouched).
  4. Writes JSON to _data/ (Liquid build-time access) and assets/data/
     (client-side fetch by land-registry-table.js). Full overwrite is fine
     here - it's a generated data file, never hand-edited.

Usage:
    python build_house_prices.py --dry-run
    python build_house_prices.py --months 12
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from statistics import median, mean

import requests
import helper

ENDPOINT = "https://landregistry.data.gov.uk/landregistry/query"
TIMEOUT_SECONDS = 30

CHELTENHAM_POSTCODE_DISTRICTS = ["GL50", "GL51", "GL52", "GL53", "GL54"]

PAGE_PATH = Path("_pages/cheltenham-house-prices.md")
JSON_ASSETS_PATH = Path("assets/data/cheltenham-house-prices.json")

MARKER = "land_registry"

# lrppi:propertyType now returns a human-readable rdfs:label directly
# (e.g. "Detached", "Flat/Maisonette") - no code-to-label mapping needed.


def build_query(months: int) -> str:
    postcode_filters = " || ".join(f'STRSTARTS(?postcode, "{d}")' for d in CHELTENHAM_POSTCODE_DISTRICTS)
    threshold_date = (datetime.now(timezone.utc) - timedelta(days=months * 30)).strftime("%Y-%m-%d")

    return f"""
PREFIX lrppi: <http://landregistry.data.gov.uk/def/ppi/>
PREFIX lrcommon: <http://landregistry.data.gov.uk/def/common/>

SELECT ?paon ?saon ?street ?town ?postcode ?amount ?date ?propertyTypeLabel ?newBuild
WHERE {{
  ?transx lrppi:pricePaid ?amount ;
          lrppi:transactionDate ?date ;
          lrppi:propertyAddress ?addr .
  ?addr lrcommon:town ?town ;
        lrcommon:postcode ?postcode .
  OPTIONAL {{ ?addr lrcommon:paon ?paon }}
  OPTIONAL {{ ?addr lrcommon:saon ?saon }}
  OPTIONAL {{ ?addr lrcommon:street ?street }}
  OPTIONAL {{ ?transx lrppi:propertyType ?propertyTypeUri .
             ?propertyTypeUri <http://www.w3.org/2000/01/rdf-schema#label> ?propertyTypeLabel }}
  OPTIONAL {{ ?transx lrppi:newBuild ?newBuild }}
  FILTER (?town = "CHELTENHAM")
  FILTER ({postcode_filters})
  FILTER (?date >= "{threshold_date}"^^<http://www.w3.org/2001/XMLSchema#date>)
}}
ORDER BY DESC(?date)
LIMIT 2000
"""


def fetch_transactions(months: int) -> list[dict]:
    query = build_query(months)
    try:
        resp = requests.get(
            ENDPOINT,
            params={"query": query, "output": "json"},
            headers={"Accept": "application/sparql-results+json"},
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        print(f"ERROR: SPARQL request failed: {exc}", file=sys.stderr)
        sys.exit(1)

    bindings = resp.json().get("results", {}).get("bindings", [])
    if not bindings:
        print("WARNING: query returned zero rows. Check filters/date range.", file=sys.stderr)

    transactions = []
    for row in bindings:
        def val(key):
            return row.get(key, {}).get("value")

        transactions.append({
            "paon": val("paon"),
            "saon": val("saon"),
            "street": val("street"),
            "town": val("town"),
            "postcode": val("postcode"),
            "amount": int(float(val("amount"))) if val("amount") else None,
            "date": val("date"),
            "property_type": val("propertyTypeLabel"),
            "new_build": val("newBuild") == "true",
        })

    return transactions


def compute_stats(transactions: list[dict]) -> dict:
    prices = [t["amount"] for t in transactions if t["amount"]]
    if not prices:
        return {"count": 0}

    by_type = {}
    for t in transactions:
        pt = t["property_type"] or "Other"
        by_type.setdefault(pt, []).append(t["amount"])

    return {
        "count": len(prices),
        "median": int(median(prices)),
        "mean": int(mean(prices)),
        "min": min(prices),
        "max": max(prices),
        "by_type": {
            pt: {"count": len(vals), "median": int(median(vals))}
            for pt, vals in sorted(by_type.items())
        },
    }


def render_prose(stats: dict, months: int) -> str:
    """
    One structured, SEO/GEO-friendly sentence, written for humans first -
    natural phrasing over data-dump structure, minimal emphasis (one bolded
    figure at most).
    """
    if stats["count"] == 0:
        return f"No Cheltenham property sales were found in HM Land Registry data for the last {months} months. Data may be delayed."

    period = "year" if months == 12 else f"{months} months"

    return (
        f"Cheltenham has seen {stats['count']} homes change hands over the past {period}, "
        f"with the typical sale going for **£{stats['median']:,}**. "
        f"Prices have ranged from £{stats['min']:,} up to £{stats['max']:,}, "
        f"averaging out at £{stats['mean']:,}. "
        f"Figures last updated {datetime.now(timezone.utc).strftime('%d %B %Y')}."
    )


def inject_markdown(page_path: Path, prose: str, dry_run: bool) -> None:
    if not page_path.exists():
        print(f"ERROR: {page_path} does not exist.", file=sys.stderr)
        sys.exit(1)

    content = page_path.read_text(encoding="utf-8")
    new_content = helper.replace_chunk(content, MARKER, prose)

    if dry_run:
        print(f"--- DRY RUN: would inject into {page_path} (marker: {MARKER}) ---\n{prose}\n")
        return

    page_path.write_text(new_content, encoding="utf-8")
    print(f"Injected prose into {page_path} (marker: {MARKER})")


def write_json(transactions: list[dict], stats: dict, dry_run: bool) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "transactions": transactions,
    }

    if dry_run:
        print(f"--- DRY RUN: would write JSON to {JSON_ASSETS_PATH} ({len(transactions)} records) ---")
        return

    JSON_ASSETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_ASSETS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {JSON_ASSETS_PATH} ({len(transactions)} records)")


def main():
    parser = argparse.ArgumentParser(description="Build Cheltenham house prices data")
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--page-path", type=Path, default=PAGE_PATH)
    args = parser.parse_args()

    print(f"Fetching Cheltenham transactions from last {args.months} months...")
    transactions = fetch_transactions(args.months)
    print(f"Retrieved {len(transactions)} transactions.")

    stats = compute_stats(transactions)
    prose = render_prose(stats, args.months)

    inject_markdown(args.page_path, prose, args.dry_run)
    write_json(transactions, stats, args.dry_run)

if __name__ == "__main__":
    main()