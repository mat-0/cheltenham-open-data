#!/usr/bin/env python3
"""
sparql_probe.py

Standalone reliability probe for the HM Land Registry SPARQL endpoint.
Run this a handful of times over a day or two (locally, or as a manual/scratch
GitHub Action) BEFORE relying on the endpoint in a scheduled build.

Does not write any output files. Just prints timing/success/failure so you
can decide: SPARQL live (Option C) vs CSV backfill + cache (Option A/B).

Usage:
    python sparql_probe.py
    python sparql_probe.py --runs 5 --delay 2
"""

import argparse
import sys
import time
from datetime import datetime, timezone

import requests

ENDPOINT = "https://landregistry.data.gov.uk/landregistry/query"

# Small, cheap, date-bounded, town-bounded query. Deliberately narrow so a
# slow/failed response tells us about endpoint health, not query cost.
PROBE_QUERY = """
PREFIX lrppi: <http://landregistry.data.gov.uk/def/ppi/>
PREFIX lrcommon: <http://landregistry.data.gov.uk/def/common/>

SELECT ?paon ?street ?town ?postcode ?amount ?date
WHERE {
  ?transx lrppi:pricePaid ?amount ;
          lrppi:transactionDate ?date ;
          lrppi:propertyAddress ?addr .
  ?addr lrcommon:town ?town ;
        lrcommon:postcode ?postcode .
  OPTIONAL { ?addr lrcommon:paon ?paon }
  OPTIONAL { ?addr lrcommon:street ?street }
  FILTER (?town = "CHELTENHAM")
  FILTER (?date >= "2025-01-01"^^<http://www.w3.org/2001/XMLSchema#date>)
}
LIMIT 5
"""

TIMEOUT_SECONDS = 25


def run_probe(run_number: int) -> dict:
    started = time.monotonic()
    ts = datetime.now(timezone.utc).isoformat()
    result = {
        "run": run_number,
        "timestamp_utc": ts,
        "success": False,
        "http_status": None,
        "elapsed_seconds": None,
        "row_count": None,
        "error": None,
    }
    try:
        resp = requests.get(
            ENDPOINT,
            params={"query": PROBE_QUERY, "output": "json"},
            headers={"Accept": "application/sparql-results+json"},
            timeout=TIMEOUT_SECONDS,
        )
        result["http_status"] = resp.status_code
        result["elapsed_seconds"] = round(time.monotonic() - started, 2)

        if resp.status_code == 200:
            data = resp.json()
            rows = data.get("results", {}).get("bindings", [])
            result["row_count"] = len(rows)
            result["success"] = True
        else:
            result["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"

    except requests.exceptions.Timeout:
        result["elapsed_seconds"] = round(time.monotonic() - started, 2)
        result["error"] = f"Timed out after {TIMEOUT_SECONDS}s"
    except requests.exceptions.RequestException as exc:
        result["elapsed_seconds"] = round(time.monotonic() - started, 2)
        result["error"] = str(exc)

    return result


def main():
    parser = argparse.ArgumentParser(description="Probe HMLR SPARQL endpoint reliability")
    parser.add_argument("--runs", type=int, default=3, help="Number of probe requests (default 3)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests (default 1.0)")
    args = parser.parse_args()

    print(f"Probing {ENDPOINT}")
    print(f"Runs: {args.runs}, delay: {args.delay}s, timeout: {TIMEOUT_SECONDS}s\n")

    results = []
    for i in range(1, args.runs + 1):
        r = run_probe(i)
        results.append(r)

        status_label = "OK" if r["success"] else "FAIL"
        print(
            f"[run {r['run']}] {status_label} "
            f"| status={r['http_status']} "
            f"| elapsed={r['elapsed_seconds']}s "
            f"| rows={r['row_count']} "
            f"| error={r['error']}"
        )

        if i < args.runs:
            time.sleep(args.delay)

    successes = sum(1 for r in results if r["success"])
    print(f"\n{successes}/{args.runs} succeeded.")

    if successes == args.runs:
        print("Endpoint looks reliable across this run. Still test at different times of day before trusting it in scheduled CI.")
    elif successes == 0:
        print("Endpoint failed every attempt. Do not build CI dependency on this yet - fall back to CSV.")
    else:
        print("Mixed results. Treat as unreliable for scheduled CI - build a CSV fallback regardless.")

    sys.exit(0 if successes > 0 else 1)


if __name__ == "__main__":
    main()