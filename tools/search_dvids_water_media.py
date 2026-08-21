#!/usr/bin/env python3
"""Discover public-domain DVIDS water-event videos and photographs.

Searches multiple engines through DDGS, normalizes DVIDS URLs, fetches each DVIDS
page, and records public-domain metadata, media IDs, VIRIN/DOD identifiers, titles,
descriptions, and preview image URLs. No media is downloaded in this discovery pass.
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
from ddgs import DDGS

OUT = Path("dvids_search")
OUT.mkdir(exist_ok=True)

GROUPS: dict[str, list[str]] = {
    "pipe_burst": [
        'site:dvidshub.net/video "pipe patching"',
        'site:dvidshub.net/video "pipe patch" damage control',
        'site:dvidshub.net/video "ruptured pipe" water',
        'site:dvidshub.net/video "pipe rupture" water',
        'site:dvidshub.net/video "pipe burst" water',
        'site:dvidshub.net/video "broken pipe" water',
        'site:dvidshub.net/video "flooding casualty" pipe',
        'site:dvidshub.net/video "damage control" pipe leak',
        'site:dvidshub.net/video "water main rupture"',
        'site:dvidshub.net/video "water line break"',
        'site:dvidshub.net/video "leak repair" pipe',
        'site:dvidshub.net/video "plugging leaks" ship',
        'site:dvidshub.net/video "pipe leak" training',
        'site:dvidshub.net/video "water leak" maintenance pipe',
        'site:dvidshub.net/video "damage control rodeo" pipe',
        'site:dvidshub.net/video "wet trainer" pipe',
        'site:dvidshub.net/video "industrial pipe" leak',
        'site:dvidshub.net/video "valve leak" water',
        'site:dvidshub.net/video "pump leak" water',
        'site:dvidshub.net/video "engine room" pipe leak',
        'site:dvidshub.net/image "pipe burst" water',
        'site:dvidshub.net/image "pipe rupture" water',
        'site:dvidshub.net/image "pipe patching"',
        'site:dvidshub.net/image "water main rupture"',
        'site:dvidshub.net/image "broken pipe" water',
        'site:dvidshub.net/image "water leak" pipe repair',
    ],
    "water_accumulation": [
        'site:dvidshub.net/video "damage control wet trainer"',
        'site:dvidshub.net/video "wet trainer" flooding',
        'site:dvidshub.net/video "flooding drill" ship',
        'site:dvidshub.net/video "flooding casualty"',
        'site:dvidshub.net/video "shipboard flooding"',
        'site:dvidshub.net/video "USS Buttercup"',
        'site:dvidshub.net/video "submarine wet trainer"',
        'site:dvidshub.net/video "flooded space" ship',
        'site:dvidshub.net/video "damage control" flooding',
        'site:dvidshub.net/video "flooding trainer"',
        'site:dvidshub.net/video "engine room flooding"',
        'site:dvidshub.net/video "machinery room flooding"',
        'site:dvidshub.net/video "pump room flooding"',
        'site:dvidshub.net/video "mechanical room flooding"',
        'site:dvidshub.net/video "facility flooding" equipment',
        'site:dvidshub.net/video "water damage" facility',
        'site:dvidshub.net/video "indoor flooding" equipment',
        'site:dvidshub.net/video "industrial flooding"',
        'site:dvidshub.net/video "dry dock flooding"',
        'site:dvidshub.net/video "flood control" pumps',
        'site:dvidshub.net/image "wet trainer" flooding',
        'site:dvidshub.net/image "flooding drill" ship',
        'site:dvidshub.net/image "flooded space" equipment',
        'site:dvidshub.net/image "engine room flooding"',
        'site:dvidshub.net/image "facility flooding" equipment',
        'site:dvidshub.net/image "water damage" machinery',
    ],
    "water_drop": [
        'site:dvidshub.net/video "dripping water" pipe',
        'site:dvidshub.net/video "water dripping" valve',
        'site:dvidshub.net/video "leaking valve" water',
        'site:dvidshub.net/video "small leak" pipe water',
        'site:dvidshub.net/video "slow leak" pipe',
        'site:dvidshub.net/video "water leak detection" pipe',
        'site:dvidshub.net/video "water leak repair" valve',
        'site:dvidshub.net/video "leak test" pipe water',
        'site:dvidshub.net/video "pressure test" water leak',
        'site:dvidshub.net/video "pump seal" leak water',
        'site:dvidshub.net/video "valve maintenance" water leak',
        'site:dvidshub.net/video "water treatment plant" valve',
        'site:dvidshub.net/video "water purification" equipment',
        'site:dvidshub.net/video "water system maintenance" pipe',
        'site:dvidshub.net/video "plumbing repair" facility',
        'site:dvidshub.net/video "pipe repair" water leak',
        'site:dvidshub.net/video "leak check" water system',
        'site:dvidshub.net/video "pump maintenance" water system',
        'site:dvidshub.net/video "water sampling" valve facility',
        'site:dvidshub.net/video "water testing" valve pipe',
        'site:dvidshub.net/image "dripping water" pipe',
        'site:dvidshub.net/image "leaking valve" water',
        'site:dvidshub.net/image "small leak" pipe water',
        'site:dvidshub.net/image "water leak detection" pipe',
        'site:dvidshub.net/image "water treatment plant" valve',
        'site:dvidshub.net/image "pipe repair" water leak',
    ],
}

MEDIA_RE = re.compile(r"https?://(?:www\.)?dvidshub\.net/(video|image)/(\d+)(?:/[^?#\s]*)?")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"


def canonical(url: str) -> tuple[str, str, str] | None:
    match = MEDIA_RE.search(url)
    if not match:
        return None
    kind, media_id = match.group(1), match.group(2)
    return kind, media_id, f"https://www.dvidshub.net/{kind}/{media_id}"


def search_query(group: str, query: str) -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for backend in ("bing", "duckduckgo", "brave"):
        try:
            results = DDGS(timeout=25).text(
                query=query,
                region="us-en",
                safesearch="moderate",
                max_results=100,
                backend=backend,
            )
        except Exception as exc:
            print(f"search failed {backend} {query!r}: {exc}", flush=True)
            continue
        added = 0
        for item in results or []:
            url = str(item.get("href") or item.get("url") or "").strip()
            parsed = canonical(url)
            if not parsed:
                continue
            kind, media_id, canon = parsed
            key = (kind, media_id)
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "group": group,
                "query": query,
                "backend": backend,
                "kind": kind,
                "media_id": media_id,
                "url": canon,
                "search_title": str(item.get("title") or "").strip(),
                "search_body": str(item.get("body") or "").strip(),
            })
            added += 1
        print(f"{group} {backend} {query!r}: {added}", flush=True)
        time.sleep(0.3 + random.random() * 0.3)
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
        desc_node = soup.find("meta", property="og:description")
        image_node = soup.find("meta", property="og:image")
        result["title"] = (title_node.get("content", "") if title_node else "").strip()
        result["description"] = (desc_node.get("content", "") if desc_node else "").strip()
        result["preview_url"] = (image_node.get("content", "") if image_node else "").strip()
        page_text = soup.get_text("\n", strip=True)
        result["public_domain"] = "PUBLIC DOMAIN" in page_text.upper()
        result["virin"] = text_after_label(page_text, "VIRIN")
        result["filename"] = text_after_label(page_text, "Filename")
        result["date_taken"] = text_after_label(page_text, "Date Taken")
        result["length"] = text_after_label(page_text, "Length")
        result["page_text_excerpt"] = page_text[:5000]
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def main() -> int:
    discovered: dict[tuple[str, str], dict] = {}
    memberships: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    queries_for: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    for group, queries in GROUPS.items():
        for query in queries:
            for row in search_query(group, query):
                key = (row["kind"], row["media_id"])
                memberships[key].add(group)
                queries_for[key].add(query)
                if key not in discovered:
                    discovered[key] = row
    print(f"unique media before page fetch: {len(discovered)}", flush=True)

    fetched: list[dict] = []
    with futures.ThreadPoolExecutor(max_workers=16) as pool:
        for index, row in enumerate(pool.map(fetch_page, discovered.values()), 1):
            key = (row["kind"], row["media_id"])
            row["groups"] = ";".join(sorted(memberships[key]))
            row["queries"] = ";".join(sorted(queries_for[key]))
            fetched.append(row)
            if index % 100 == 0:
                print(f"fetched {index}/{len(discovered)}", flush=True)

    # Prefer one media object per VIRIN/DOD filename when duplicate encodes exist.
    deduped: list[dict] = []
    seen_identity: set[str] = set()
    for row in sorted(fetched, key=lambda x: (x.get("kind", ""), int(x.get("media_id", 0)))):
        identity = row.get("virin") or row.get("filename") or f"{row.get('kind')}:{row.get('media_id')}"
        identity = identity.strip()
        if identity in seen_identity:
            continue
        seen_identity.add(identity)
        if row.get("public_domain"):
            deduped.append(row)

    fields = sorted({key for row in deduped for key in row.keys()})
    with (OUT / "media.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(deduped)
    (OUT / "media.json").write_text(json.dumps(deduped, indent=2, ensure_ascii=False), encoding="utf-8")
    stats = {
        "raw_unique_media": len(discovered),
        "public_domain_unique_identity": len(deduped),
        "by_kind": dict(Counter(row.get("kind") for row in deduped)),
        "by_group_membership": dict(Counter(group for row in deduped for group in row.get("groups", "").split(";") if group)),
        "with_preview_url": sum(bool(row.get("preview_url")) for row in deduped),
        "with_virin": sum(bool(row.get("virin")) for row in deduped),
        "errors": sum(bool(row.get("error")) for row in fetched),
    }
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
