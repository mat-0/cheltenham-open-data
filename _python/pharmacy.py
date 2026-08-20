#!/usr/bin/env python3
"""
fetch_gp_pharmacy.py

Pulls GP practice and pharmacy listings for Cheltenham from NHS England's
ODS ORD API (open-access, no API key) and updates a Jekyll page in place
using the project's helper.replace_chunk() function.

Base URL: https://directory.spineservices.nhs.uk/ORD/2-0-0
GP practices: NonPrimaryRoleId=RO76 (confirmed)
Pharmacies: role ID looked up dynamically via /roles (not hardcoded —
see find_pharmacy_role_ids())

Usage:
    python3 fetch_gp_pharmacy.py [--debug]
"""

import sys
import argparse
import datetime
import requests

BASE_URL = "https://directory.spineservices.nhs.uk/ORD/2-0-0"
TIMEOUT = 20

# Cheltenham postcode districts. GL54 covers some outlying villages
# (e.g. Bourton area) so is left out deliberately — add it if you want
# a wider catchment.
CHELTENHAM_POSTCODES = ["GL50", "GL51", "GL52", "GL53"]

GP_NON_PRIMARY_ROLE_ID = "RO76"  # confirmed: "GP Practice Prescribing Cost Centre"

OUTPUT_FILE = "_pages/gp-pharmacy.md"
MARKER_NAME = "gp_pharmacy_finder"  # CHECK: matches your template's marker name?

DEBUG = False


def debug_print(*args):
    if DEBUG:
        print("[debug]", *args, file=sys.stderr)


def find_pharmacy_role_ids():
    """Query the /roles endpoint and return all role IDs whose display
    name contains 'PHARMACY', rather than assuming a fixed code."""
    debug_print(f"GET {BASE_URL}/roles")
    resp = requests.get(f"{BASE_URL}/roles", timeout=TIMEOUT)
    debug_print("status:", resp.status_code, "body length:", len(resp.text))
    if resp.status_code != 200:
        debug_print("body snippet:", resp.text[:500])
    resp.raise_for_status()
    data = resp.json()

    roles = data.get("Roles", [])
    debug_print(f"{len(roles)} total roles returned by /roles endpoint")

    pharmacy_roles = [
        r for r in roles
        if "PHARMACY" in r.get("displayName", "").upper()
    ]
    debug_print(f"roles matching 'PHARMACY': {pharmacy_roles}")

    return [r["id"] for r in pharmacy_roles]


def search_organisations(params):
    """Query /organisations with given params, paginating via Offset/Limit
    if the total count exceeds one page."""
    all_orgs = []
    offset = None
    limit = 200

    while True:
        request_params = dict(params)
        request_params["Limit"] = limit
        if offset is not None:
            request_params["Offset"] = offset

        debug_print(f"GET {BASE_URL}/organisations params={request_params}")
        resp = requests.get(f"{BASE_URL}/organisations", params=request_params, timeout=TIMEOUT)
        debug_print("status:", resp.status_code, "body length:", len(resp.text))
        if resp.status_code != 200:
            debug_print("body snippet:", resp.text[:500])
        resp.raise_for_status()
        data = resp.json()

        orgs = data.get("Organisations", [])
        debug_print(f"page at offset {offset}: {len(orgs)} organisations")
        all_orgs.extend(orgs)

        if len(orgs) < limit:
            break

        offset = (offset or 0) + limit
        if offset > 5000:
            debug_print("hit pagination sanity cap, stopping")
            break

    return all_orgs


def fetch_orgs_for_postcodes(extra_params):
    """Run the same search across each Cheltenham postcode district and
    merge, deduplicating by OrgId."""
    seen_ids = set()
    merged = []
    for postcode in CHELTENHAM_POSTCODES:
        params = dict(extra_params)
        params["PostCode"] = postcode
        params["Status"] = "Active"
        orgs = search_organisations(params)
        for org in orgs:
            org_id = org.get("OrgId")
            if org_id and org_id not in seen_ids:
                seen_ids.add(org_id)
                merged.append(org)
    return merged


def get_org_detail(org_id: str):
    """Fetch full detail for a single org (address lines, phone) —
    the summary/search endpoint only returns a postcode, not full
    address or contact details."""
    debug_print(f"GET {BASE_URL}/organisations/{org_id}")
    resp = requests.get(f"{BASE_URL}/organisations/{org_id}", timeout=TIMEOUT)
    if resp.status_code != 200:
        debug_print(f"  failed to fetch detail for {org_id}: {resp.status_code}")
        return None
    return resp.json()


def to_title_case(text: str):
    """Title-case a name/address, with fixes for two known problems:
    - str.title()-style logic capitalises the letter after an apostrophe
      (ST. CATHERINE'S -> St. Catherine'S) — this keeps it lowercase.
    - UK postcodes (e.g. GL52 3EY) must stay upper case, not become
      Gl52 3ey."""
    import re

    if not text:
        return text

    def cap_piece(p):
        return p[:1].upper() + p[1:].lower() if p else p

    def fix_word(w):
        # Preserve UK postcode formatting untouched
        if re.fullmatch(r"[A-Za-z]{1,2}\d[A-Za-z\d]?", w) or re.fullmatch(r"\d[A-Za-z]{2}", w):
            return w.upper()
        parts = w.split("-")
        return "-".join(cap_piece(p) for p in parts)

    words = text.split(" ")
    return " ".join(fix_word(w) for w in words)


def maps_link(address: str):
    from urllib.parse import quote_plus
    return f"https://www.google.com/maps/search/?api=1&query={quote_plus(address)}"


def extract_detail_fields(detail_json):
    """Pull address lines and phone out of a full organisation detail
    response. Structure per ORD API docs is nested under
    Organisation -> GeoLoc -> Location, and Organisation -> Contacts."""
    org = detail_json.get("Organisation", {})

    location = org.get("GeoLoc", {}).get("Location", {})
    address_parts = [
        location.get("AddrLn1", ""),
        location.get("AddrLn2", ""),
        location.get("Town", ""),
        location.get("PostCode", ""),
    ]
    address = ", ".join(p for p in address_parts if p)

    phone = ""
    contacts = org.get("Contacts", {}).get("Contact", [])
    if isinstance(contacts, dict):
        contacts = [contacts]
    for c in contacts:
        if c.get("type") == "tel":
            phone = c.get("value", "")
            break

    return address, phone
    """Pull address lines and phone out of a full organisation detail
    response. Structure per ORD API docs is nested under
    Organisation -> GeoLoc -> Location, and Organisation -> Contacts."""
    org = detail_json.get("Organisation", {})

    location = org.get("GeoLoc", {}).get("Location", {})
    address_parts = [
        location.get("AddrLn1", ""),
        location.get("AddrLn2", ""),
        location.get("Town", ""),
        location.get("PostCode", ""),
    ]
    address = ", ".join(p for p in address_parts if p)

    phone = ""
    contacts = org.get("Contacts", {}).get("Contact", [])
    if isinstance(contacts, dict):
        contacts = [contacts]
    for c in contacts:
        if c.get("type") == "tel":
            phone = c.get("value", "")
            break

    return address, phone


def fetch_gp_practices():
    summaries = fetch_orgs_for_postcodes({"NonPrimaryRoleId": GP_NON_PRIMARY_ROLE_ID})
    results = []
    for s in summaries:
        detail = get_org_detail(s["OrgId"])
        address, phone = extract_detail_fields(detail) if detail else (s.get("PostCode", ""), "")
        results.append({
            "name": to_title_case(s.get("Name", "Unknown")),
            "address": to_title_case(address),
            "phone": phone,
        })
    return results


def fetch_pharmacies():
    pharmacy_role_ids = find_pharmacy_role_ids()
    if not pharmacy_role_ids:
        print("WARNING: no roles matching 'PHARMACY' found via /roles endpoint. "
              "Check --debug output for the full role list and adjust the "
              "matching logic if the naming differs.", file=sys.stderr)
        return []

    debug_print(f"using pharmacy role IDs: {pharmacy_role_ids}")

    all_summaries = []
    seen_ids = set()
    for role_id in pharmacy_role_ids:
        summaries = fetch_orgs_for_postcodes({"PrimaryRoleId": role_id})
        for s in summaries:
            if s.get("OrgId") not in seen_ids:
                seen_ids.add(s.get("OrgId"))
                all_summaries.append(s)

    results = []
    for s in all_summaries:
        detail = get_org_detail(s["OrgId"])
        address, phone = extract_detail_fields(detail) if detail else (s.get("PostCode", ""), "")
        results.append({
            "name": to_title_case(s.get("Name", "Unknown")),
            "address": to_title_case(address),
            "phone": phone,
        })
    return results


def render_markdown(gps, pharmacies):
    generated = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = []
    lines.append(
        "Finding a GP practice or pharmacy in Cheltenham shouldn't mean "
        "digging through the NHS website. The listings below are pulled "
        "directly from [NHS England's Organisation Data Service]"
        "(https://digital.nhs.uk/services/organisation-data-service), the "
        "official register of NHS organisations, so names, addresses and "
        f"phone numbers stay current automatically (last updated {generated}).\n"
    )
    lines.append(
        "\nIf you need to register with a new GP, you can do this "
        "directly with any practice that covers your address — you don't "
        "need a referral or your old practice's permission. For repeat "
        "prescriptions, most pharmacies listed below offer a free "
        "collection or delivery service; ask in branch or check the "
        "[NHS App](https://www.nhs.uk/nhs-app/) to nominate a regular "
        "pharmacy.\n"
    )

    lines.append("\n## GP Practices\n")
    if gps:
        for gp in sorted(gps, key=lambda x: x["name"]):
            lines.append(f"\n### {gp['name']}\n")
            lines.append(f"\n- Address: [{gp['address']}]({maps_link(gp['address'])})")
            if gp["phone"]:
                lines.append(f"\n- Phone: [{gp['phone']}](tel:{gp['phone'].replace(' ', '')})")
            lines.append("\n")
    else:
        lines.append("\n> No GP practices were returned at generation time.\n")

    lines.append("\n## Pharmacies\n")
    if pharmacies:
        for ph in sorted(pharmacies, key=lambda x: x["name"]):
            lines.append(f"\n### {ph['name']}\n")
            lines.append(f"\n- Address: [{ph['address']}]({maps_link(ph['address'])})")
            if ph["phone"]:
                lines.append(f"\n- Phone: [{ph['phone']}](tel:{ph['phone'].replace(' ', '')})")
            lines.append("\n")
    else:
        lines.append("\n> No pharmacies were returned at generation time.\n")

    lines.append(
        f"\n*Source: [NHS Organisation Data Service](https://digital.nhs.uk/services/organisation-data-service). "
        f"Data last refreshed {generated}.*\n"
    )

    return "".join(lines)


def update_target_file(body_markdown: str):
    """Uses the project's existing helper.replace_chunk(content, marker,
    chunk) function. ADAPT: fix the import path for your `helper` module."""
    import helper  # adjust import path to match your project structure

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = f.read()
    except FileNotFoundError:
        print(f"ERROR: {OUTPUT_FILE} does not exist. Create it first with "
              f"front matter and the {MARKER_NAME} starts/ends markers in "
              f"place, then re-run this script.", file=sys.stderr)
        sys.exit(1)

    new_content = helper.replace_chunk(existing, MARKER_NAME, body_markdown)

    if new_content == existing:
        print(f"WARNING: file content unchanged — the '{MARKER_NAME} starts'/"
              f"'{MARKER_NAME} ends' markers may not be present in "
              f"{OUTPUT_FILE}.", file=sys.stderr)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)


def main():
    global DEBUG
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    DEBUG = args.debug

    try:
        gps = fetch_gp_practices()
    except requests.RequestException as exc:
        print(f"ERROR: could not fetch GP practices: {exc}", file=sys.stderr)
        gps = []

    try:
        pharmacies = fetch_pharmacies()
    except requests.RequestException as exc:
        print(f"ERROR: could not fetch pharmacies: {exc}", file=sys.stderr)
        pharmacies = []

    markdown = render_markdown(gps, pharmacies)
    update_target_file(markdown)

    print(f"Updated {OUTPUT_FILE} with {len(gps)} GP practices and {len(pharmacies)} pharmacies")
    if not gps or not pharmacies:
        print("One or both lists came back empty — re-run with --debug "
              "to see raw API responses.", file=sys.stderr)


if __name__ == "__main__":
    main()