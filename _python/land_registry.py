#!/usr/bin/env python3
"""
build_house_prices.py

Re-runnable data build. Does NOT author HTML or markdown structure - those
are static, hand-edited files (cheltenham-house-prices.md, house-pricing.html,
house-price-charts.js). This script only:

  1. Queries SPARQL for Cheltenham transactions (postcode district GL50-GL54
     AND town = CHELTENHAM, cross-checked).
  2. Computes summary stats.
  3. Injects one prose sentence into the markdown page's "land_registry"
     marker (via helper.replace_chunk - never touches anything outside
     the marker, so surrounding hand-written prose is untouched).
  4. Writes JSON to _data/ for Liquid tables and chart data. Full overwrite
      is fine here - it is a generated data file, never hand-edited.

Configuration is via the constants below (MONTHS, DRY_RUN, PAGE_PATH) rather
than CLI args, so behaviour is identical whether run locally (VS Code "Run")
or via GitHub Actions.
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from statistics import median, mean

import requests
import helper

# ---------------------------------------------------------------------------
# Configuration - edit these directly, no CLI args
# ---------------------------------------------------------------------------
MONTHS = 24  # fetch 24 months so we can compare last 12 vs the prior 12
DRY_RUN = False
PAGE_PATH = Path("_pages/cheltenham-house-prices.md")
# ---------------------------------------------------------------------------

ENDPOINT = "https://landregistry.data.gov.uk/landregistry/query"
TIMEOUT_SECONDS = 30

CHELTENHAM_POSTCODE_DISTRICTS = ["GL50", "GL51", "GL52", "GL53", "GL54"]

JSON_DATA_PATH = Path("_data/cheltenham-house-prices.json")

MARKER = "land_registry"

# lrppi:propertyType now returns a human-readable rdfs:label directly
# (e.g. "Detached", "Flat/Maisonette") - no code-to-label mapping needed.


SPARQL_LIMIT = 2000
PAGE_SIZE = 2000


def _common_where(months: int) -> tuple[str, str]:
    """Returns (postcode_filters, threshold_date) shared by both queries."""
    postcode_filters = " || ".join(f'STRSTARTS(?postcode, "{d}")' for d in CHELTENHAM_POSTCODE_DISTRICTS)
    threshold_date = (datetime.now(timezone.utc) - timedelta(days=months * 30)).strftime("%Y-%m-%d")
    return postcode_filters, threshold_date


def build_count_query(months: int) -> str:
    postcode_filters, threshold_date = _common_where(months)
    return f"""
PREFIX lrppi: <http://landregistry.data.gov.uk/def/ppi/>
PREFIX lrcommon: <http://landregistry.data.gov.uk/def/common/>

SELECT (COUNT(*) AS ?n)
WHERE {{
  ?transx lrppi:pricePaid ?amount ;
          lrppi:transactionDate ?date ;
          lrppi:propertyAddress ?addr .
  ?addr lrcommon:town ?town ;
        lrcommon:postcode ?postcode .
  FILTER (?town = "CHELTENHAM")
  FILTER ({postcode_filters})
  FILTER (?date >= "{threshold_date}"^^<http://www.w3.org/2001/XMLSchema#date>)
}}
"""


def build_query(months: int, limit: int = SPARQL_LIMIT, offset: int = 0) -> str:
    postcode_filters, threshold_date = _common_where(months)

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
LIMIT {limit}
OFFSET {offset}
"""


def _run_query(query: str) -> dict:
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
    return resp.json()


def get_true_count(months: int) -> int:
    """Runs a COUNT(*) query (no LIMIT) so we know the real row count,
    independent of SPARQL_LIMIT/pagination below."""
    data = _run_query(build_count_query(months))
    bindings = data.get("results", {}).get("bindings", [])
    n = int(bindings[0]["n"]["value"]) if bindings else 0
    print(f"COUNT check: {n} true matching rows for the last {months} months.")
    return n


def _rows_to_transactions(bindings: list[dict]) -> list[dict]:
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
            "display_amount": f"£{int(float(val('amount'))):,}" if val("amount") else "",
            "date": val("date"),
            "property_type": val("propertyTypeLabel"),
            "new_build": val("newBuild") == "true",
        })
    return transactions


def fetch_transactions(months: int, expected_count: int | None = None) -> list[dict]:
    """Paginates through results in PAGE_SIZE chunks using OFFSET, so results
    are never silently truncated by the endpoint's per-request LIMIT."""
    all_transactions: list[dict] = []
    offset = 0

    while True:
        query = build_query(months, limit=PAGE_SIZE, offset=offset)
        data = _run_query(query)
        bindings = data.get("results", {}).get("bindings", [])

        if not bindings:
            break

        all_transactions.extend(_rows_to_transactions(bindings))
        print(f"Fetched page at offset {offset}: {len(bindings)} rows (running total {len(all_transactions)}).")

        if len(bindings) < PAGE_SIZE:
            break

        offset += PAGE_SIZE

    if not all_transactions:
        print("WARNING: query returned zero rows. Check filters/date range.", file=sys.stderr)

    if expected_count is not None and len(all_transactions) != expected_count:
        print(
            f"WARNING: fetched {len(all_transactions)} rows but COUNT query reported "
            f"{expected_count}. Results may be inconsistent (data changed mid-fetch, "
            f"or endpoint pagination behaving unexpectedly).",
            file=sys.stderr,
        )

    return all_transactions


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


def split_current_vs_prior_year(transactions: list[dict]) -> tuple[list[dict], list[dict]]:
    """Splits a (assumed ~24 month) transaction list into:
      - current: last 12 months
      - prior:   the 12 months before that
    Uses calendar-day cutoffs (365/730 days back from now), not calendar years.
    """
    now = datetime.now(timezone.utc)
    cutoff_12 = now - timedelta(days=365)
    cutoff_24 = now - timedelta(days=730)

    current, prior = [], []
    for t in transactions:
        if not t["date"]:
            continue
        d = datetime.fromisoformat(t["date"]).replace(tzinfo=timezone.utc)
        if d >= cutoff_12:
            current.append(t)
        elif d >= cutoff_24:
            prior.append(t)

    return current, prior


def pct_change(new: float, old: float) -> float | None:
    if not old:
        return None
    return ((new - old) / old) * 100


def prior_year_label() -> int:
    """Label used for the comparison period, financial-report style.
    Note: the comparison window is a rolling 12 months, not a calendar year,
    so this label is an approximation (e.g. 'the year to Sept 2026' vs
    'the year before'), shown as calendar_year - 1 for readability."""
    return datetime.now(timezone.utc).year - 1


def format_change(current: float, prior: float, currency: bool = False) -> str:
    """Financial-accounts style: 'up 12% (2025: 1,900)' / 'down 4% (2025: £320,000)'."""
    change = pct_change(current, prior)
    if change is None:
        return "no comparable data for the prior year"
    direction = "up" if change >= 0 else "down"
    prior_str = f"£{prior:,.0f}" if currency else f"{prior:,.0f}"
    return f"{direction} {abs(change):.0f}% ({prior_year_label()}: {prior_str})"


def render_prose(
    current_stats: dict,
    prior_stats: dict,
    current_new_build_stats: dict,
    prior_new_build_stats: dict,
    full_dataset_stats: dict,
    full_dataset_months: int,
    current_domestic_stats: dict,
    prior_domestic_stats: dict,
    current_other_count: int = 0,
    prior_other_count: int = 0,
) -> str:
    """
    Four paragraphs:
      1. This year vs last year, all sales (median/mean explicitly labelled, range).
      2. New build sales, this year vs last year, on its own.
      3. Summary of the full dataset (the whole fetched window, not just 12mo).
      4. Domestic-only (excludes Land Registry "Other" property type), with a
         caveat that this is a Land Registry classification, not a guarantee.
    No "figures last updated" line - handled elsewhere.
    """
    if current_stats["count"] == 0:
        return "No Cheltenham property sales were found in HM Land Registry data for the last 12 months. Data may be delayed."

    py = prior_year_label()

    # --- Paragraph 1: this year vs last year, all sales ---
    p1 = f"Cheltenham has seen {current_stats['count']} properties change hands over the past year"
    if prior_stats.get("count"):
        p1 += f", {format_change(current_stats['count'], prior_stats['count'])}"
    p1 += ". "
    p1 += f"The typical sale (median) went for **£{current_stats['median']:,}**"
    if prior_stats.get("median"):
        p1 += f", {format_change(current_stats['median'], prior_stats['median'], currency=True)}"
    p1 += f", with an average (mean) of £{current_stats['mean']:,}"
    if prior_stats.get("mean"):
        p1 += f", {format_change(current_stats['mean'], prior_stats['mean'], currency=True)}"
    p1 += ". "
    p1 += f"Prices ranged from £{current_stats['min']:,} up to £{current_stats['max']:,}"
    if prior_stats.get("min") and prior_stats.get("max"):
        p1 += f" ({py}: £{prior_stats['min']:,}–£{prior_stats['max']:,})"
    p1 += "."

    # --- Paragraph 2: new build, on its own ---
    if current_new_build_stats.get("count"):
        p2 = f"Of these, **{current_new_build_stats['count']}** were new build sales"
        if prior_new_build_stats.get("count"):
            p2 += f", {format_change(current_new_build_stats['count'], prior_new_build_stats['count'])}"
        p2 += f", with a median price of £{current_new_build_stats['median']:,}"
        if prior_new_build_stats.get("median"):
            p2 += f", {format_change(current_new_build_stats['median'], prior_new_build_stats['median'], currency=True)}"
        p2 += "."
    else:
        p2 = "No new build sales were recorded in Cheltenham over the past year."

    # --- Paragraph 3: full dataset summary ---
    p3 = (
        f"Across the full {full_dataset_months}-month dataset, {full_dataset_stats['count']} Cheltenham "
        f"property sales were recorded, with a median price of £{full_dataset_stats['median']:,} "
        f"(mean £{full_dataset_stats['mean']:,}), ranging from £{full_dataset_stats['min']:,} "
        f"to £{full_dataset_stats['max']:,}."
    )

    # --- Paragraph 4: domestic only (excludes "Other" property type) ---
    if current_domestic_stats.get("count"):
        p4 = f"Excluding properties classed as \"Other\" in Land Registry data, {current_domestic_stats['count']} domestic sales were recorded over the past year"
        if prior_domestic_stats.get("count"):
            p4 += f", {format_change(current_domestic_stats['count'], prior_domestic_stats['count'])}"
        p4 += f", with an average (mean) price of £{current_domestic_stats['mean']:,}"
        if prior_domestic_stats.get("mean"):
            p4 += f", {format_change(current_domestic_stats['mean'], prior_domestic_stats['mean'], currency=True)}"
        p4 += ". "
        total_other = current_other_count + prior_other_count
        if total_other:
            p4 += (
                f"({current_other_count} sale{'s' if current_other_count != 1 else ''} this year and "
                f"{prior_other_count} the year before {'were' if total_other != 1 else 'was'} classed as "
                f"\"Other\" - typically non-residential premises such as banks and business units, "
                f"though this can also include land-only transactions and garages. "
            )
        p4 += (
            f"\n\nNotes: This exclusion is based on Land Registry's own property type classification which seems to indicate non-domestic buildings "
            "and should be treated as a indicative and not a guaranteed commercial/residential split."
        )
    else:
        p4 = ""

    paragraphs = [p1, p2, p3]
    if p4:
        paragraphs.append(p4)

    return "\n\n".join(paragraphs)


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
        print(f"--- DRY RUN: would write JSON to {JSON_DATA_PATH} ({len(transactions)} records) ---")
        return

    JSON_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_DATA_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {JSON_DATA_PATH} ({len(transactions)} records)")


def main():
    print(f"Checking true row count for last {MONTHS} months...")
    true_count = get_true_count(MONTHS)

    print(f"Fetching Cheltenham transactions from last {MONTHS} months...")
    transactions = fetch_transactions(MONTHS, expected_count=true_count)
    print(f"Retrieved {len(transactions)} transactions (COUNT query reported {true_count}).")

    stats = compute_stats(transactions)  # full window, written to JSON as-is

    current_txns, prior_txns = split_current_vs_prior_year(transactions)
    current_stats = compute_stats(current_txns)
    prior_stats = compute_stats(prior_txns)

    # New build, current vs prior year
    current_new_build_txns = [t for t in current_txns if t["new_build"]]
    prior_new_build_txns = [t for t in prior_txns if t["new_build"]]
    current_new_build_stats = compute_stats(current_new_build_txns)
    prior_new_build_stats = compute_stats(prior_new_build_txns)

    # Domestic only = excludes Land Registry "Other" property type (new builds stay in)
    current_domestic_txns = [t for t in current_txns if t["property_type"] != "Other"]
    prior_domestic_txns = [t for t in prior_txns if t["property_type"] != "Other"]
    current_other_txns = [t for t in current_txns if t["property_type"] == "Other"]
    prior_other_txns = [t for t in prior_txns if t["property_type"] == "Other"]
    current_domestic_stats = compute_stats(current_domestic_txns)
    prior_domestic_stats = compute_stats(prior_domestic_txns)

    print(f"Current 12mo: {current_stats.get('count', 0)} sales. Prior 12mo: {prior_stats.get('count', 0)} sales.")
    print(f"New build: {current_new_build_stats.get('count', 0)} current, {prior_new_build_stats.get('count', 0)} prior.")
    print(f"'Other' property_type: {len(current_other_txns)} current, {len(prior_other_txns)} prior (excluded from domestic figures).")

    prose = render_prose(
        current_stats,
        prior_stats,
        current_new_build_stats,
        prior_new_build_stats,
        stats,
        MONTHS,
        current_domestic_stats,
        prior_domestic_stats,
        len(current_other_txns),
        len(prior_other_txns),
    )

    inject_markdown(PAGE_PATH, prose, DRY_RUN)
    write_json(transactions, stats, DRY_RUN)  # JSON export always contains the full, unfiltered dataset


if __name__ == "__main__":
    main()