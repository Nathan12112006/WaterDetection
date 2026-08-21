#!/usr/bin/env python3
"""Download and normalize preview images for discovered public-domain DVIDS media.

This is an initial relevance-screening pass. It keeps source metadata outside the
final dataset and rejects obviously irrelevant themes before any video extraction.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from PIL import Image, ImageOps

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"

# Rejection-only terms keep the candidate pool focused on technical water events.
BAD = (
    "firefighting", "fire fighter", "firefighter", "fire hose", "hydrant", "washdown",
    "decontamination shower", "rainstorm", "hurricane", "typhoon", "tornado", "monsoon",
    "river flood", "street flood", "road flood", "bridge flood", "beach", "swimming",
    "water park", "fountain", "waterfall", "garden hose", "irrigation sprinkler",
    "illustration", "graphic", "poster", "animation", "render", "video game",
    "rifle", "pistol", "machine gun", "ammunition", "grenade", "missile", "torpedo",
    "live fire", "combat shooting",
)
POS = {
    "pipe_burst": (
        "pipe patch", "pipe rupture", "pipe burst", "broken pipe", "water line break",
        "water main rupture", "pipe leak", "plugging leaks", "flooding casualty",
        "wet trainer", "damage control",
    ),
    "water_drop": (
        "drip", "dripping", "small leak", "slow leak", "leaking valve", "leak detection",
        "leak test", "pressure test", "pump seal", "valve maintenance", "pipe repair",
        "water system maintenance", "wet trainer", "pipe patch",
    ),
    "water_accumulation": (
        "wet trainer", "flooding drill", "flooding casualty", "shipboard flooding",
        "flooded space", "damage control", "engine room flooding", "pump room flooding",
        "mechanical room flooding", "facility flooding", "indoor flooding",
    ),
}


def incident_id(row: dict) -> str:
    title = str(row.get("title") or row.get("search_title") or "").lower()
    title = re.sub(r"\s*\[image\s*\d+\s*of\s*\d+\]\s*", " ", title, flags=re.I)
    title = re.sub(r"\s*\(\d+\)\s*$", "", title)
    title = re.sub(r"[^a-z0-9]+", "_", title).strip("_")[:80]
    date = re.sub(r"[^0-9]", "", str(row.get("date_taken") or ""))[:8]
    return f"{date}_{title}" if title else f"{row.get('kind')}_{row.get('media_id')}"


def allowed(row: dict, group: str) -> bool:
    text = " ".join(
        str(row.get(key) or "")
        for key in ("title", "description", "search_title", "search_body", "queries", "groups")
    ).lower()
    if any(term in text for term in BAD):
        return False
    return any(term in text for term in POS[group])


def normalize(raw: bytes):
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image = ImageOps.exif_transpose(image)
            if getattr(image, "is_animated", False):
                image.seek(0)
            image = image.convert("RGB")
            width, height = image.size
            if min(width, height) < 360 or max(width, height) < 600:
                return None
            if max(width, height) > 1600:
                scale = 1600 / max(width, height)
                image = image.resize(
                    (round(width * scale), round(height * scale)), Image.Resampling.LANCZOS
                )
                width, height = image.size
            buffer = io.BytesIO()
            image.save(buffer, "JPEG", quality=90, optimize=True, progressive=True)
            data = buffer.getvalue()
            return data, width, height, hashlib.sha256(data).hexdigest()
    except Exception:
        return None


def fetch(row: dict):
    url = str(row.get("preview_url") or "").strip()
    if not url:
        return row, None, "no_preview"
    try:
        response = requests.get(
            url,
            headers={"User-Agent": UA, "Referer": row.get("url") or "https://www.dvidshub.net/"},
            timeout=(10, 30),
        )
        response.raise_for_status()
        normalized = normalize(response.content)
        return row, normalized, "" if normalized else "quality"
    except Exception as exc:
        return row, None, str(exc)[:120]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("media_json")
    parser.add_argument("output")
    args = parser.parse_args()

    rows = json.load(open(args.media_json, encoding="utf-8"))
    output = Path(args.output)
    image_dir = output / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    memberships: list[dict] = []
    for row in rows:
        groups = [g for g in str(row.get("groups") or row.get("group") or "").split(";") if g]
        for group in groups:
            if group in POS and allowed(row, group):
                membership = dict(row)
                membership["target_group"] = group
                membership["incident_id"] = incident_id(row)
                memberships.append(membership)

    unique = {(row.get("kind"), str(row.get("media_id"))): row for row in memberships}
    print(
        f"eligible memberships={len(memberships)} unique media={len(unique)}",
        flush=True,
    )

    fetched = {}
    with ThreadPoolExecutor(max_workers=20) as executor:
        for index, (row, normalized, error) in enumerate(executor.map(fetch, unique.values()), 1):
            key = (row.get("kind"), str(row.get("media_id")))
            fetched[key] = (normalized, error)
            if index % 100 == 0:
                print(f"downloaded {index}/{len(unique)}", flush=True)

    seen_sha: set[str] = set()
    file_by_key = {}
    for key in unique:
        normalized, _ = fetched.get(key, (None, "missing"))
        if not normalized:
            continue
        data, width, height, sha = normalized
        if sha in seen_sha:
            continue
        seen_sha.add(sha)
        filename = f"dvids_{key[0]}_{key[1]}.jpg"
        (image_dir / filename).write_bytes(data)
        file_by_key[key] = (filename, width, height, sha)

    manifest = []
    for row in memberships:
        key = (row.get("kind"), str(row.get("media_id")))
        if key not in file_by_key:
            continue
        filename, width, height, sha = file_by_key[key]
        manifest.append({**row, "filename": filename, "width": width, "height": height, "sha256": sha})

    fields = sorted({key for row in manifest for key in row})
    with (output / "manifest.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(manifest)
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    stats = {
        "input_rows": len(rows),
        "eligible_memberships": len(memberships),
        "downloaded_unique_images": len(file_by_key),
        "memberships": len(manifest),
        "by_group": dict(Counter(row["target_group"] for row in manifest)),
        "by_kind": dict(Counter(row.get("kind") for row in manifest)),
        "unique_incidents": len({row["incident_id"] for row in manifest}),
    }
    (output / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
