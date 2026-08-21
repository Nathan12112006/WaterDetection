#!/usr/bin/env python3
"""Discover public-domain industrial water-event media through DVIDS search pages.

The site search returns 30 results per page and is substantially faster and more
complete than general web search. This script records media metadata and provenance
only; a separate preview step performs visual screening before any video extraction.
"""
from __future__ import annotations

import concurrent.futures as futures
import csv
import json
import random
import re
import time
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OUT = Path("dvids_direct")
OUT.mkdir(exist_ok=True)

QUERIES: dict[str, list[str]] = {
    "pipe_burst": [
        "pipe patching", "ruptured pipe", "pipe rupture", "broken pipe water",
        "pipe burst water", "water line break", "water main break", "water leak pipe",
        "leaking pipe water", "damage control pipe leak", "flooding casualty pipe",
        "surface damage control trainer", "damage control wet trainer", "wet trainer leak",
        "pipe leak training", "plugging pipe leaks", "patching pipe leak", "valve leak water",
        "water leak repair pipe", "leak detection pipe", "water system leak", "water leak maintenance",
        "chilled water pipe leak", "HVAC water leak", "cooling water leak", "pump leak water",
        "utility pipe leak", "engine room pipe leak", "mechanical room pipe leak",
        "water treatment pipe leak", "water plant pipe leak", "pipe failure water",
    ],
    "water_drop": [
        "dripping water pipe", "dripping valve water", "water drip leak", "small pipe leak",
        "slow water leak", "leaking valve water", "pump seal leak water", "pipe joint leak water",
        "HVAC leak water", "condensate leak", "leak detection water pipe", "pipe inspection leak",
        "water system maintenance leak", "valve maintenance water", "water treatment leak",
        "filter housing leak water", "pump maintenance water leak", "pipe fitting leak water",
        "water line leak inspection", "water leak identification", "active water leak",
        "plumbing leak facility", "dripping HVAC", "dripping pipe facility",
    ],
    "water_accumulation": [
        "damage control wet trainer", "wet trainer flooding", "flooding drill", "indoor flooding",
        "flooded facility", "flooded mechanical room", "flooded pump room", "flooded engine room",
        "flooding casualty", "water damage facility", "water leak facility", "HVAC leak floor",
        "boiler room flood", "utility room flood", "water on floor equipment", "standing water equipment",
        "flooded warehouse", "flood damage equipment", "pump room flooding", "shipboard flooding",
        "flooded compartment", "water leak building", "water main break facility", "flooded machinery",
        "flooding trainer", "damage control flooding", "water accumulation floor", "facility water damage",
        "equipment room flooding", "industrial flooding", "mechanical space flooding",
    ],
}

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
MEDIA_RE = re.compile(r"https?://(?:www\.)?dvidshub\.net/(video|image)/(\d+)(?:/[^?#\s]*)?")


def canonical(url: str):
    match = MEDIA_RE.search(url)
    if not match:
        return None
    kind, media_id = match.group(1), match.group(2)
    return kind, media_id, f"https://www.dvidshub.net/{kind}/{media_id}"


def search_query(group: str, query: str, max_pages: int) -> list[dict]:
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    previous_page_ids: set[tuple[str, str]] | None = None
    for page in range(1, max_pages + 1):
        try:
            response = session.get(
                "https://www.dvidshub.net/search/",
                params={"q": query, "page": page, "view": "grid"},
                timeout=30,
            )
            response.raise_for_status()
        except Exception as exc:
            print(f"search failed {group} {query!r} page={page}: {exc}", flush=True)
            break
        soup = BeautifulSoup(response.text, "html.parser")
        page_ids: set[tuple[str, str]] = set()
        for node in soup.find_all("a", href=True):
            parsed = canonical(urllib.parse.urljoin(response.url, node["href"]))
            if not parsed:
                continue
            kind, media_id, url = parsed
            key = (kind, media_id)
            page_ids.add(key)
            if key in seen:
                continue
            seen.add(key)
            card = node
            for _ in range(5):
                if card.parent is None:
                    break
                card = card.parent
            card_text = " ".join(card.get_text(" ", strip=True).split())[:1200]
            rows.append({
                "group": group,
                "query": query,
                "page": page,
                "kind": kind,
                "media_id": media_id,
                "url": url,
                "search_card_text": card_text,
            })
        print(f"{group} {query!r} page={page}: {len(page_ids)} media", flush=True)
        if not page_ids or page_ids == previous_page_ids or len(page_ids) < 8:
            break
        previous_page_ids = page_ids
        time.sleep(0.08 + random.random() * 0.08)
    return rows


def text_after_label(text: str, label: str) -> str:
    pattern = re.compile(re.escape(label) + r"\s*[:|]\s*([^\n\r]+)", re.I)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def fetch_page(row: dict) -> dict:
    result = dict(row)
    try:
        response = requests.get(row["url"], headers={"User-Agent": UA}, timeout=30)
        result["http_status"] = response.status_code
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        title_node = soup.find("meta", property="og:title")
        description_node = soup.find("meta", property="og:description")
        image_node = soup.find("meta", property="og:image")
        result["title"] = (title_node.get("content", "") if title_node else "").strip()
        result["description"] = (description_node.get("content", "") if description_node else "").strip()
        result["preview_url"] = (image_node.get("content", "") if image_node else "").strip()
        page_text = soup.get_text("\n", strip=True)
        result["public_domain"] = "PUBLIC DOMAIN" in page_text.upper()
        result["virin"] = text_after_label(page_text, "VIRIN")
        result["filename"] = text_after_label(page_text, "Filename")
        result["date_taken"] = text_after_label(page_text, "Date Taken")
        result["length"] = text_after_label(page_text, "Length")
        result["resolution"] = text_after_label(page_text, "Resolution")
        result["page_text_excerpt"] = page_text[:7000]
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pages", type=int, default=12)
    parser.add_argument("--search-workers", type=int, default=12)
    parser.add_argument("--page-workers", type=int, default=24)
    args = parser.parse_args()

    jobs = [(group, query, args.max_pages) for group, queries in QUERIES.items() for query in queries]
    raw_rows: list[dict] = []
    with futures.ThreadPoolExecutor(max_workers=args.search_workers) as executor:
        for rows in executor.map(lambda x: search_query(*x), jobs):
            raw_rows.extend(rows)

    discovered: dict[tuple[str, str], dict] = {}
    memberships: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    queries_for: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    for row in raw_rows:
        key = (row["kind"], row["media_id"])
        memberships[key].add(row["group"])
        queries_for[key].add(row["query"])
        discovered.setdefault(key, row)
    print(f"raw rows={len(raw_rows)} unique media={len(discovered)}", flush=True)

    fetched: list[dict] = []
    with futures.ThreadPoolExecutor(max_workers=args.page_workers) as executor:
        for index, row in enumerate(executor.map(fetch_page, discovered.values()), 1):
            key = (row["kind"], row["media_id"])
            row["groups"] = ";".join(sorted(memberships[key]))
            row["queries"] = ";".join(sorted(queries_for[key]))
            fetched.append(row)
            if index % 200 == 0:
                print(f"metadata {index}/{len(discovered)}", flush=True)

    # Remove duplicate encodes of the same DOD/VIRIN item, but preserve distinct gallery images.
    accepted: list[dict] = []
    seen_identity: set[str] = set()
    for row in sorted(fetched, key=lambda x: (x.get("kind", ""), int(x.get("media_id", 0)))):
        if not row.get("public_domain"):
            continue
        identity = str(row.get("virin") or row.get("filename") or f"{row.get('kind')}:{row.get('media_id')}").strip()
        if identity in seen_identity:
            continue
        seen_identity.add(identity)
        accepted.append(row)

    fields = sorted({key for row in accepted for key in row})
    with (OUT / "media.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(accepted)
    (OUT / "media.json").write_text(json.dumps(accepted, indent=2, ensure_ascii=False), encoding="utf-8")
    stats = {
        "queries": len(jobs),
        "raw_search_rows": len(raw_rows),
        "raw_unique_media": len(discovered),
        "public_domain_unique_identity": len(accepted),
        "by_kind": dict(Counter(row.get("kind") for row in accepted)),
        "by_group_membership": dict(Counter(g for row in accepted for g in row.get("groups", "").split(";") if g)),
        "with_preview_url": sum(bool(row.get("preview_url")) for row in accepted),
        "errors": sum(bool(row.get("error")) for row in fetched),
    }
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
