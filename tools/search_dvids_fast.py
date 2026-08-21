#!/usr/bin/env python3
"""Fast DVIDS discovery pass using the strongest water-event queries.

The longer discovery job uses many multilingual queries and backends. This pass is
independent and deliberately compact so candidate extraction can begin sooner.
"""
from __future__ import annotations

import concurrent.futures as futures
import csv
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from ddgs import DDGS

from search_dvids_water_media import GROUPS, canonical, fetch_page

OUT = Path("dvids_fast")
OUT.mkdir(exist_ok=True)

# Keep only high-precision, water-event-specific queries. All target controlled
# flooding, pipe failures, leak repair, wet trainers, and active dripping.
LIMITS = {
    "pipe_burst": 20,
    "water_accumulation": 20,
    "water_drop": 20,
}


def search(group: str, query: str) -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for backend in ("bing", "duckduckgo"):
        try:
            results = DDGS(timeout=18).text(
                query=query,
                region="us-en",
                safesearch="moderate",
                max_results=100,
                backend=backend,
            )
        except Exception as exc:
            print(f"{backend} failed {query!r}: {exc}", flush=True)
            continue
        added = 0
        for item in results or []:
            parsed = canonical(str(item.get("href") or item.get("url") or ""))
            if not parsed:
                continue
            kind, media_id, url = parsed
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
                "url": url,
                "search_title": str(item.get("title") or "").strip(),
                "search_body": str(item.get("body") or "").strip(),
            })
            added += 1
        print(f"{group} {backend}: {added} for {query!r}", flush=True)
        time.sleep(0.15)
    return rows


def main() -> int:
    discovered: dict[tuple[str, str], dict] = {}
    memberships: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    queries_for: defaultdict[tuple[str, str], set[str]] = defaultdict(set)

    for group in ("pipe_burst", "water_drop", "water_accumulation"):
        for query in GROUPS[group][: LIMITS[group]]:
            for row in search(group, query):
                key = (row["kind"], row["media_id"])
                memberships[key].add(group)
                queries_for[key].add(query)
                discovered.setdefault(key, row)

    print(f"fast pass discovered {len(discovered)} unique media", flush=True)
    fetched: list[dict] = []
    with futures.ThreadPoolExecutor(max_workers=20) as pool:
        for index, row in enumerate(pool.map(fetch_page, discovered.values()), 1):
            key = (row["kind"], row["media_id"])
            row["groups"] = ";".join(sorted(memberships[key]))
            row["queries"] = ";".join(sorted(queries_for[key]))
            fetched.append(row)
            if index % 100 == 0:
                print(f"fetched {index}/{len(discovered)}", flush=True)

    accepted: list[dict] = []
    seen_identity: set[str] = set()
    for row in sorted(fetched, key=lambda x: (x.get("kind", ""), int(x.get("media_id", 0)))):
        if not row.get("public_domain"):
            continue
        identity = (row.get("virin") or row.get("filename") or f"{row.get('kind')}:{row.get('media_id')}").strip()
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
