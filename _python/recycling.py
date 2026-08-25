#!/usr/bin/env python3
"""
Scrapes the Cheltenham Borough Council recycling banks page and rewrites
the content between the recycling_banks placeholder markers in
_pages/recycling.md.

Run from the repo root:
    python _python/recycling.py

Requires: requests, beautifulsoup4
"""
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

import helper

URL = "https://www.cheltenham.gov.uk/recyclingbanks"
OUTPUT_PATH = Path("_pages/recycling.md")
MARKER = "recycling_banks"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; recycling-bank-scraper/1.0; "
        "+https://github.com/)"
    )
}


def fetch_page(url: str) -> str:
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def parse_banks(html: str) -> list[dict]:
    """
    Parse the recycling bank locations section into a list of
    {"name": str, "materials": [str, ...]} dicts.

    The site renders each bank as a GOV.UK accordion section:

        <div class="govuk-accordion__section">
          <div class="govuk-accordion__section-header">
            <h2 class="govuk-accordion__section-heading">
              <span class="govuk-accordion__section-button">Site name, POSTCODE</span>
            </h2>
          </div>
          <div class="govuk-accordion__section-content">
            <p class="govuk-body"><ul><li>Material</li>...</ul></p>
          </div>
        </div>

    We parse every ".govuk-accordion__section" within the accordion
    container. This is more robust than relying on the surrounding
    prose/headings, which have changed between site revisions.
    """
    soup = BeautifulSoup(html, "html.parser")

    accordion = soup.find("div", class_="govuk-accordion")
    if accordion is None:
        raise RuntimeError("Could not find the recycling banks accordion")

    banks = []

    for section in accordion.find_all("div", class_="govuk-accordion__section"):
        button = section.find(class_="govuk-accordion__section-button")
        if button is None:
            continue
        name = button.get_text(strip=True)
        if not name:
            continue

        content = section.find(class_="govuk-accordion__section-content")
        if content is None:
            continue

        materials = [
            li.get_text(strip=True)
            for li in content.find_all("li")
            if li.get_text(strip=True)
        ]
        if materials:
            banks.append({"name": name, "materials": materials})

    if not banks:
        raise RuntimeError("No recycling banks were parsed from the page")

    return banks


def to_markdown(banks: list[dict]) -> str:
    lines = []
    for bank in banks:
        lines.append(f"### {bank['name']}")
        lines.append("")
        for material in bank["materials"]:
            lines.append(f"- {material}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    try:
        html = fetch_page(URL)
        banks = parse_banks(html)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to fetch or parse recycling banks: {exc}", file=sys.stderr)
        return 1

    markdown = to_markdown(banks)

    if not OUTPUT_PATH.exists():
        print(f"Output file not found: {OUTPUT_PATH}", file=sys.stderr)
        return 1

    content = OUTPUT_PATH.read_text(encoding="utf-8")
    updated = helper.replace_chunk(content, MARKER, markdown)
    OUTPUT_PATH.write_text(updated, encoding="utf-8")

    print(f"Updated {OUTPUT_PATH} with {len(banks)} recycling bank locations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())