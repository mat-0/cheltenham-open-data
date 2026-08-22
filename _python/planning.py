"""
planning.py

Fetches recent planning applications from Cheltenham Borough Council's
PublicAccess (Idox) portal, merges them into a running JSON store, and
writes fixed-template SEO prose into the markdown page between the
"planning_body" markers.

Run: hourly via GitHub Actions.

Data source:
    https://publicaccess.cheltenham.gov.uk/online-applications/
    (Idox PublicAccess system - standard across most UK councils)

Output:
    /assets/data/planning-applications.json   <- human/JS-readable table data
    /_pages/cheltenham-planning-applications.md  <- prose updated in place

NOTE ON SELECTORS:
    Idox PublicAccess sites are template-driven but selector/markup details
    can vary slightly council-to-council and can change on portal upgrades.
    The parsing constants are isolated in CONFIG below. If the council
    changes their portal, run with DEBUG=True and inspect
    debug_last_response.html to re-check selectors.
"""

import re
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import helper

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("planning")

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

BASE_URL = "https://publicaccess.cheltenham.gov.uk/online-applications"
MONTHLY_LIST_URL = f"{BASE_URL}/search.do?action=weeklyList&searchType=Application"

# How many days back to query each run. Hourly job + overlap window means
# a missed/failed run still gets caught next time. Dedup happens on ref.
LOOKBACK_DAYS = 7

# Drop records older than this from the JSON store each run.
RETENTION_DAYS = 183  # ~6 months

DATA_DIR = Path("assets/data")
DATA_FILE = DATA_DIR / "planning-applications.json"

PAGES_DIR = Path("_pages")
MARKDOWN_FILE = PAGES_DIR / "planning.md"
MARKER = "planning_body"

REQUEST_HEADERS = {
    "User-Agent": "REPLACE_ME/1.0",
}

REQUEST_DELAY_SECONDS = 1.5  # be polite between page requests
MAX_PAGES = 10  # safety cap on pagination

DEBUG = False


# ---------------------------------------------------------------------------
# FETCHING
# ---------------------------------------------------------------------------

def discover_form(html, base_url):
    """
    Parse the monthly list search form: CSRF token, action URL, the select
    field listing months, and the radio group choosing received/validated/
    decided. Done dynamically rather than hardcoding field names, since
    Idox portals vary and we've already been burned guessing them.
    """
    soup = BeautifulSoup(html, "html.parser")
    forms = soup.find_all("form")

    form = None
    for f in forms:
        select_names = " ".join((s.get("name") or "") for s in f.find_all("select"))
        option_text = " ".join(
            o.get_text(strip=True) for s in f.find_all("select") for o in s.find_all("option")
        ).lower()
        if any(m in option_text for m in ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")):
            form = f
            break

    if form is None:
        form = forms[0] if forms else None

    if not form:
        raise RuntimeError("Could not find monthly list search form on page")

    action = form.get("action")
    action_url = urljoin(base_url + "/", action)

    fields = {}
    all_selects_debug = []

    for inp in form.find_all("input"):
        itype = (inp.get("type") or "text").lower()
        name = inp.get("name")
        if not name:
            continue
        if itype == "hidden":
            fields[name] = inp.get("value", "")
        elif itype == "radio":
            if inp.has_attr("checked"):
                fields[name] = inp.get("value")

    month_select = None
    for select in form.find_all("select"):
        options = select.find_all("option")
        option_texts = " ".join(o.get_text(strip=True) for o in options).lower()
        all_selects_debug.append((select.get("name"), [o.get_text(strip=True) for o in options][:5]))
        if any(m in option_texts for m in ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")):
            month_select = select

    log.info("All <select> fields found on form: %s", all_selects_debug)

    # For every select field, submit whichever option is marked selected,
    # falling back to the first option. Covers parish/ward filters as well
    # as the month field, without hardcoding field names.
    for select in form.find_all("select"):
        name = select.get("name")
        if not name:
            continue
        options = select.find_all("option")
        if not options:
            continue
        chosen = next((o for o in options if o.has_attr("selected")), None)
        if chosen is None and select is month_select:
            chosen = options[0]  # most recent month, since options are newest-first
        elif chosen is None:
            chosen = options[0]
        fields[name] = chosen.get("value", "")

    if month_select is None:
        log.warning("No month <select> field detected - search may fail or return wrong period")

    return action_url, fields


def fetch_monthly_list_page(session, action_url, fields, page_number):
    fields = dict(fields)
    if page_number > 1:
        fields["searchCriteria.page"] = page_number

    resp = session.post(action_url, data=fields, timeout=30)
    log.info("POST %s -> status %s, %s bytes", resp.url, resp.status_code, len(resp.text))
    resp.raise_for_status()

    if DEBUG:
        Path(f"debug_monthly_response_page{page_number}.html").write_text(resp.text, encoding="utf-8")
        log.info("Wrote debug_monthly_response_page%s.html (%s bytes)", page_number, len(resp.text))

    return resp.text


def parse_results_page(html):
    """
    Parse one page of PublicAccess search results.

    Idox results pages list applications as <li class="searchresult"> blocks,
    each containing a reference, address, description and status. Exact
    class names have shifted between Idox versions - selectors below try the
    common current pattern first and fall back to a looser search if needed.
    """
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("li.searchresult")

    if not items:
        # Fallback for older/alternate Idox templates
        items = soup.select("ul#searchresults li")

    if DEBUG and items:
        log.info("--- RAW TEXT OF FIRST RESULT ITEM ---")
        log.info(" ".join(items[0].get_text(separator=" ").split()))
        log.info("--- RAW HTML OF FIRST RESULT ITEM ---")
        log.info(str(items[0])[:2000])
        log.info("--- END DEBUG ---")

    records = []
    for item in items:
        record = parse_result_item(item)
        if record:
            records.append(record)

    has_next = bool(soup.select_one("a.next, a[title='Next']"))
    log.info("has_next detected: %s (found selector match: %s)", has_next, soup.select_one("a.next, a[title='Next']"))
    return records, has_next


def parse_result_item(item):
    link = item.select_one("a")
    if not link:
        return None

    detail_url = link.get("href", "")
    if detail_url and not detail_url.startswith("http"):
        detail_url = urljoin(BASE_URL + "/", detail_url)

    full_text = " ".join(item.get_text(separator=" ").split())

    ref_match = re.search(r"Ref\.?\s*No:?\s*([A-Z0-9/]+)", full_text, re.IGNORECASE)
    ref = ref_match.group(1) if ref_match else None

    received_match = re.search(
        r"Received:\s*(?:\w{3}\s+)?(\d{1,2}\s+\w{3,9}\s+\d{4})", full_text, re.IGNORECASE
    )
    received_date = parse_date(received_match.group(1)) if received_match else None

    status_el = item.select_one(".badge-status .value")
    status = status_el.get_text(strip=True) if status_el else "Unknown"

    description = link.get_text(strip=True)

    address = None
    addr_el = item.select_one(".address, .location")
    if addr_el:
        address = addr_el.get_text(strip=True)
    else:
        # crude fallback: text after description, before "Ref"
        after = full_text.split(description, 1)[-1]
        address = after.split("Ref")[0].strip(" -\u2013")

    postcode = extract_postcode(address or "")
    units = extract_units(description)

    if not ref:
        return None

    return {
        "ref": ref,
        "description": description,
        "address": address,
        "postcode": postcode,
        "units": units,
        "status": status,
        "received_date": received_date,
        "url": detail_url,
    }


def parse_date(text):
    text = text.replace(".", "/")
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def extract_postcode(text):
    match = re.search(r"[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}", text.upper())
    return match.group(0) if match else None


def extract_units(description):
    """
    Best-effort unit count from free-text description, e.g.
    '2no. dwellings' -> 2, 'erection of 60 dwellings' -> 60.
    Returns None when no confident count is found.
    """
    match = re.search(r"(\d+)\s*(?:no\.?|x)?\s*(?:dwellings?|flats?|units?|apartments?)", description, re.IGNORECASE)
    if match:
        return int(match.group(1))
    if re.search(r"\bdwelling\b", description, re.IGNORECASE) and "dwellings" not in description.lower():
        return 1
    return None


def fetch_recent_applications():
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)

    log.info("Loading monthly list search form: %s", MONTHLY_LIST_URL)
    form_resp = session.get(MONTHLY_LIST_URL, timeout=30)
    log.info("Form page -> status %s, %s bytes", form_resp.status_code, len(form_resp.text))
    if DEBUG:
        Path("debug_form_page.html").write_text(form_resp.text, encoding="utf-8")

    action_url, fields = discover_form(form_resp.text, BASE_URL)
    log.info("Discovered form action: %s", action_url)
    log.info("Discovered fields: %s", fields)

    all_records = []
    seen_refs = set()
    page = 1
    while page <= MAX_PAGES:
        log.info("Fetching monthly list results page %s", page)
        try:
            html = fetch_monthly_list_page(session, action_url, fields, page)
        except requests.RequestException as exc:
            log.error("Request failed on page %s: %s", page, exc)
            break

        records, has_next = parse_results_page(html)
        new_records = [r for r in records if r["ref"] not in seen_refs]
        log.info("Parsed %s records on page %s (%s new)", len(records), page, len(new_records))

        if not new_records:
            log.info("No new records on page %s - stopping pagination", page)
            break

        for r in new_records:
            seen_refs.add(r["ref"])
        all_records.extend(new_records)

        if not has_next:
            break

        page += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    return all_records


# ---------------------------------------------------------------------------
# STORE (merge / dedupe / retention)
# ---------------------------------------------------------------------------

def load_existing():
    if not DATA_FILE.exists():
        return {}
    try:
        records = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return {r["ref"]: r for r in records}
    except (json.JSONDecodeError, KeyError) as exc:
        log.warning("Could not parse existing JSON store (%s); starting fresh", exc)
        return {}


def merge_records(existing, new_records):
    for record in new_records:
        ref = record["ref"]
        if ref in existing:
            existing[ref].update(record)
        else:
            existing[ref] = record
    return existing


def apply_retention(records_by_ref):
    cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).strftime("%Y-%m-%d")
    kept = {
        ref: r for ref, r in records_by_ref.items()
        if not r.get("received_date") or r["received_date"] >= cutoff
    }
    dropped = len(records_by_ref) - len(kept)
    if dropped:
        log.info("Dropped %s records older than %s days", dropped, RETENTION_DAYS)
    return kept


def save_store(records_by_ref):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    records = sorted(
        records_by_ref.values(),
        key=lambda r: r.get("received_date") or "",
        reverse=True,
    )
    DATA_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")
    log.info("Saved %s records to %s", len(records), DATA_FILE)
    return records


# ---------------------------------------------------------------------------
# PROSE (fixed templates, stats plugged in)
# ---------------------------------------------------------------------------

def build_prose(records):
    total = len(records)
    statuses = {}
    for r in records:
        status = (r.get("status") or "Unknown").strip()
        statuses[status] = statuses.get(status, 0) + 1

    pending = sum(v for k, v in statuses.items() if "pending" in k.lower())
    decided = sum(
        v for k, v in statuses.items()
        if any(term in k.lower() for term in ("allow", "approv", "grant", "refus", "object", "permit", "withdraw"))
    )
    other = total - pending - decided

    major_schemes = [r for r in records if (r.get("units") or 0) >= 10]

    dates = [r["received_date"] for r in records if r.get("received_date")]
    date_range = ""
    if dates:
        date_range = f"between {min(dates)} and {max(dates)}"

    updated = datetime.now().strftime("%d %B %Y")

    paragraphs = []

    paragraphs.append(
        f"As of {updated}, this page tracks {total} planning application"
        f"{'s' if total != 1 else ''} submitted to Cheltenham Borough Council"
        f"{' ' + date_range if date_range else ''}, covering new housing "
        f"developments, conversions to flats, and larger commercial schemes."
    )

    paragraphs.append(
        f"Of these, {pending} are pending consideration and {decided} have "
        f"reached a decision (approved, refused, or otherwise determined). "
        f"Status is updated automatically as applications progress through "
        f"the council's PublicAccess planning portal."
    )

    if major_schemes:
        paragraphs.append(
            f"{len(major_schemes)} of the tracked applications involve 10 or "
            f"more dwellings, representing the larger housing schemes "
            f"currently working through the planning process in Cheltenham."
        )

    paragraphs.append(
        "An application reference beginning with a two-digit year (for "
        "example 26/00415/FUL) indicates the year it was submitted. FUL "
        "denotes a full planning application; OUT denotes an outline "
        "application, where only the principle of development is agreed at "
        "this stage and detailed matters are reserved for later approval."
    )

    paragraphs.append(
        "This data is sourced directly from Cheltenham Borough Council's "
        "PublicAccess planning portal and refreshed regularly. It is "
        "provided for general information; for the definitive and most "
        "current record on any application, consult the council's planning "
        "portal directly."
    )

    return "\n\n".join(paragraphs)


def update_markdown(prose):
    if not MARKDOWN_FILE.exists():
        log.warning("%s not found; skipping prose update", MARKDOWN_FILE)
        return

    content = MARKDOWN_FILE.read_text(encoding="utf-8")
    updated = helper.replace_chunk(content, MARKER, prose)
    MARKDOWN_FILE.write_text(updated, encoding="utf-8")
    log.info("Updated prose in %s", MARKDOWN_FILE)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    new_records = fetch_recent_applications()

    if not new_records:
        log.warning("No records fetched this run; leaving existing store untouched")
    else:
        existing = load_existing()
        merged = merge_records(existing, new_records)
        merged = apply_retention(merged)
        saved = save_store(merged)
        prose = build_prose(saved)
        update_markdown(prose)


if __name__ == "__main__":
    main()