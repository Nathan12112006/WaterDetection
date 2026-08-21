#!/usr/bin/env python3
"""Collect DVIDS public-media search thumbnails for industrial water-event review.

The script only uses DVIDS search-result pages. It records provenance, keeps source
incidents diverse, rejects obvious out-of-scope subjects, downloads review-size
thumbnails, and removes exact/perceptual duplicates. A later human-review stage
chooses the final images and verifies each selected DVIDS media page individually.
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import csv
import hashlib
import io
import json
import random
import re
import shutil
import time
import urllib.parse
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path

import cv2
import numpy as np
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps, UnidentifiedImageError

BASE = "https://www.dvidshub.net/search/"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
MEDIA_RE = re.compile(r"/(image|video)/(\d+)(?:/([^?#]+))?")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

QUERIES: dict[str, list[str]] = {
    "pipe_burst": [
        "damage control wet trainer",
        "pipe patching water",
        "flooding casualty pipe",
        "ruptured pipe water",
        "pipe rupture water",
        "broken pipe water",
        "pipe leak training",
        "damage control pipe leak",
        "plugging pipe leaks",
        "patching pipe leak",
        "water line break facility",
        "water main break facility",
        "valve leak water facility",
        "pump leak water facility",
        "cooling water pipe leak",
        "HVAC water pipe leak",
        "mechanical room pipe leak",
        "engine room pipe leak",
        "water treatment pipe leak",
        "industrial water pipe leak",
        "pipe failure water spray",
        "water system pipe rupture",
        "high pressure water leak pipe",
        "damage control flooding trainer",
    ],
    "water_drop": [
        "dripping water pipe",
        "dripping valve water",
        "water drip leak pipe",
        "small pipe leak water",
        "slow water leak pipe",
        "leaking valve water",
        "pump seal leak water",
        "pipe joint leak water",
        "pipe fitting leak water",
        "flange leak water",
        "HVAC leak water",
        "condensate leak facility",
        "leak detection water pipe",
        "water line leak inspection",
        "water system maintenance leak",
        "valve maintenance water leak",
        "water treatment leak pipe",
        "filter housing leak water",
        "pump maintenance water leak",
        "active water leak facility",
        "plumbing leak facility",
        "dripping HVAC pipe",
        "water leak identification pipe",
        "water leak repair valve",
        "water purification equipment leak",
        "utility pipe drip leak",
        "boiler valve water leak",
        "chiller pipe leak water",
        "mechanical room dripping pipe",
        "facility pipe leak inspection",
    ],
    "water_accumulation": [
        "damage control wet trainer flooding",
        "wet trainer flooding",
        "flooding casualty",
        "flooded compartment equipment",
        "shipboard flooding trainer",
        "flooding drill water",
        "damage control flooding",
        "indoor flooding equipment",
        "flooded facility equipment",
        "flooded mechanical room",
        "flooded pump room",
        "flooded engine room",
        "water damage facility equipment",
        "water on floor equipment",
        "standing water equipment room",
        "utility room flooding",
        "boiler room flooding",
        "HVAC room flooding",
        "mechanical space flooding",
        "pump room flooding",
        "equipment room flooding",
        "facility water damage machinery",
        "water main break building",
        "industrial flooding equipment",
        "warehouse flooding machinery",
        "water leak floor facility",
        "flooded maintenance facility",
        "flooded workshop equipment",
        "flooded utility building",
        "water accumulation floor machinery",
    ],
}

POSITIVE: dict[str, tuple[str, ...]] = {
    "pipe_burst": (
        "pipe", "rupture", "burst", "broken", "leak", "patch", "flooding casualty",
        "wet trainer", "damage control", "water line", "water main", "valve", "pump",
    ),
    "water_drop": (
        "drip", "dripping", "leak", "valve", "pipe", "pump", "seal", "flange",
        "fitting", "hvac", "condensate", "inspection", "maintenance", "filter",
    ),
    "water_accumulation": (
        "flood", "flooding", "flooded", "water damage", "standing water", "water on floor",
        "wet trainer", "damage control", "casualty", "compartment", "facility", "equipment",
    ),
}

# Search-result rejection terms. These are intentionally conservative: anything
# questionable is left for human review, while clearly non-industrial themes go.
BAD = (
    "firefighting", "fire fighter", "firefighter", "fire hose", "hydrant", "wildfire",
    "live fire", "rifle", "pistol", "weapon", "ammunition", "missile", "torpedo",
    "rain", "hurricane", "typhoon", "tornado", "monsoon", "river", "street flooding",
    "road flooding", "bridge", "beach", "lake", "water park", "fountain", "waterfall",
    "irrigation", "farm", "agriculture", "garden", "swimming", "pool", "shower",
    "decontamination", "washdown", "washing", "drinking water bottle", "ceremony",
    "graphic", "illustration", "poster", "logo", "animation", "render", "video game",
    "construction project", "pipeline construction", "new pipe installation",
)

@dataclass
class Candidate:
    media_kind: str
    media_id: str
    slug: str
    page_url: str
    thumb_url: str
    title: str
    author: str
    context: str
    query: str
    search_class: str
    page_number: int
    text_score: float
    incident_id: str


def normalize_incident(title: str, author: str, context: str) -> str:
    text = title.lower()
    text = re.sub(r"\[\s*(?:image|video)\s*\d+\s*of\s*\d+\s*\]", " ", text)
    text = re.sub(r"\b(?:image|photo|video)\s*\d+\b", " ", text)
    text = re.sub(r"\(\d+\)\s*$", " ", text)
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    a = re.sub(r"[^a-z0-9]+", "_", author.lower()).strip("_")[:28]
    c = re.sub(r"[^a-z0-9]+", "_", context.lower()).strip("_")[:28]
    return (text[:70] + "__" + a + "__" + c).strip("_")


def text_score(search_class: str, query: str, title: str, context: str) -> float:
    text = " ".join((query, title, context)).lower()
    score = 0.0
    for term in POSITIVE[search_class]:
        if term in text:
            score += 1.0 + min(1.5, len(term) / 18.0)
    # Exact active-event wording is especially valuable.
    for term in (
        "dripping", "active leak", "pipe rupture", "pipe burst", "broken pipe",
        "flooding casualty", "wet trainer", "standing water", "water on floor",
    ):
        if term in text:
            score += 2.0
    if search_class == "water_drop" and any(x in text for x in ("drip", "small leak", "slow leak")):
        score += 3.0
    if search_class == "water_accumulation" and any(x in text for x in ("flooded", "standing water", "water damage")):
        score += 2.5
    if search_class == "pipe_burst" and any(x in text for x in ("rupture", "burst", "pipe patch", "wet trainer")):
        score += 2.5
    return score


def parse_search_page(search_class: str, query: str, page: int) -> list[Candidate]:
    params = {
        "q": query,
        "page": page,
        "view": "grid",
        "filter[type]": "image",
    }
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    try:
        response = session.get(BASE, params=params, timeout=35)
        response.raise_for_status()
    except Exception as exc:
        print(f"SEARCH_FAIL {search_class} {query!r} p{page}: {exc}", flush=True)
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    output: list[Candidate] = []
    seen: set[str] = set()
    for slide in soup.select("div.dtv_slide_container"):
        image = slide.find("img", src=True)
        link = slide.find("a", href=MEDIA_RE)
        if image is None or link is None:
            continue
        match = MEDIA_RE.search(link.get("href", ""))
        if not match:
            continue
        kind, media_id, slug = match.group(1), match.group(2), match.group(3) or ""
        if kind != "image" or media_id in seen:
            continue
        seen.add(media_id)
        title_node = slide.find("h1")
        title = (title_node.get_text(" ", strip=True) if title_node else image.get("alt", "")).strip()
        h3 = slide.find("h3")
        author = (h3.get_text(" ", strip=True) if h3 else "").replace("Photo by", "").strip()
        p = slide.find("p")
        context = p.get_text(" ", strip=True) if p else ""
        combined = " ".join((title, author, context, query)).lower()
        if any(term in combined for term in BAD):
            continue
        thumb = urllib.parse.urljoin(response.url, image.get("src", ""))
        if not thumb.startswith("http"):
            continue
        page_url = urllib.parse.urljoin(response.url, link.get("href", ""))
        incident = normalize_incident(title, author, context)
        output.append(Candidate(
            media_kind=kind,
            media_id=media_id,
            slug=slug,
            page_url=page_url,
            thumb_url=thumb,
            title=title,
            author=author,
            context=context,
            query=query,
            search_class=search_class,
            page_number=page,
            text_score=text_score(search_class, query, title, context),
            incident_id=incident,
        ))
    print(f"SEARCH {search_class} {query!r} p{page}: {len(output)} kept", flush=True)
    return output


def bits_hex(bits: np.ndarray) -> str:
    return np.packbits(np.asarray(bits, dtype=np.uint8).reshape(-1)).tobytes().hex()


def phash(gray: np.ndarray) -> str:
    resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    values = cv2.dct(resized)[:8, :8].ravel()
    return bits_hex(values > float(np.median(values[1:])))


def dhash(gray: np.ndarray) -> str:
    resized = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    return bits_hex(resized[:, 1:] > resized[:, :-1])


def hamming(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


def download_one(candidate: Candidate):
    try:
        response = requests.get(
            candidate.thumb_url,
            headers={"User-Agent": UA, "Referer": candidate.page_url},
            timeout=(10, 30),
        )
        response.raise_for_status()
        if len(response.content) < 10_000:
            return candidate, None, "small"
        with Image.open(io.BytesIO(response.content)) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            width, height = image.size
            if min(width, height) < 300 or max(width, height) < 500:
                return candidate, None, "dimensions"
            if max(width, height) > 900:
                scale = 900.0 / max(width, height)
                image = image.resize((round(width * scale), round(height * scale)), Image.Resampling.LANCZOS)
                width, height = image.size
            thumb = np.asarray(image.resize((128, 128), Image.Resampling.BILINEAR))
            if float(cv2.cvtColor(thumb, cv2.COLOR_RGB2GRAY).std()) < 8.0:
                return candidate, None, "blank"
            buffer = io.BytesIO()
            image.save(buffer, "JPEG", quality=89, optimize=True, progressive=True)
            data = buffer.getvalue()
            gray = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
            return candidate, {
                "data": data,
                "width": width,
                "height": height,
                "sha256": hashlib.sha256(data).hexdigest(),
                "phash": phash(gray),
                "dhash": dhash(gray),
            }, ""
    except (requests.RequestException, UnidentifiedImageError, OSError, ValueError) as exc:
        return candidate, None, type(exc).__name__


def select_diverse(candidates: list[Candidate], target: int, max_incident: int) -> list[Candidate]:
    # Highest text relevance first, but round-robin across queries prevents one search
    # phrase or incident from dominating the pool.
    by_query: defaultdict[str, list[Candidate]] = defaultdict(list)
    for candidate in candidates:
        by_query[candidate.query].append(candidate)
    for values in by_query.values():
        values.sort(key=lambda c: (-c.text_score, c.page_number, int(c.media_id)))
    query_order = sorted(by_query, key=lambda q: (-max(c.text_score for c in by_query[q]), q))
    picked: list[Candidate] = []
    incident_counts: Counter[str] = Counter()
    media_seen: set[str] = set()
    while len(picked) < target:
        progressed = False
        for query in query_order:
            values = by_query[query]
            while values:
                candidate = values.pop(0)
                if candidate.media_id in media_seen:
                    continue
                if incident_counts[candidate.incident_id] >= max_incident:
                    continue
                picked.append(candidate)
                media_seen.add(candidate.media_id)
                incident_counts[candidate.incident_id] += 1
                progressed = True
                break
            if len(picked) >= target:
                break
        if not progressed:
            break
    return picked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="dvids_thumbnail_pool")
    parser.add_argument("--pages", type=int, default=8)
    parser.add_argument("--pipe-target", type=int, default=550)
    parser.add_argument("--drop-target", type=int, default=900)
    parser.add_argument("--accum-target", type=int, default=550)
    parser.add_argument("--max-incident-review", type=int, default=6)
    args = parser.parse_args()

    random.seed(20260821)
    output = Path(args.output)
    if output.exists():
        shutil.rmtree(output)
    images = output / "images"
    images.mkdir(parents=True)

    jobs = [
        (search_class, query, page)
        for search_class, queries in QUERIES.items()
        for query in queries
        for page in range(1, args.pages + 1)
    ]
    raw: list[Candidate] = []
    with futures.ThreadPoolExecutor(max_workers=8) as executor:
        for rows in executor.map(lambda values: parse_search_page(*values), jobs):
            raw.extend(rows)

    # Consolidate memberships for identical DVIDS image IDs while preserving each
    # class-specific search score for quota selection.
    unique_rows: dict[tuple[str, str, str], Candidate] = {}
    for candidate in raw:
        key = (candidate.search_class, candidate.query, candidate.media_id)
        old = unique_rows.get(key)
        if old is None or candidate.text_score > old.text_score:
            unique_rows[key] = candidate
    raw = list(unique_rows.values())

    targets = {
        "pipe_burst": args.pipe_target,
        "water_drop": args.drop_target,
        "water_accumulation": args.accum_target,
    }
    selected_by_class: dict[str, list[Candidate]] = {}
    for search_class, target in targets.items():
        selected_by_class[search_class] = select_diverse(
            [c for c in raw if c.search_class == search_class],
            target=target,
            max_incident=args.max_incident_review,
        )
        print(f"SELECT {search_class}: {len(selected_by_class[search_class])}/{target}", flush=True)

    # Merge class memberships. A visual appears once on disk and records all search
    # classes/queries that led to it.
    merged: dict[str, dict] = {}
    for search_class, candidates in selected_by_class.items():
        for candidate in candidates:
            record = merged.setdefault(candidate.media_id, {
                "candidate": candidate,
                "search_classes": set(),
                "queries": set(),
                "scores": {},
            })
            record["search_classes"].add(search_class)
            record["queries"].add(candidate.query)
            record["scores"][search_class] = max(
                float(record["scores"].get(search_class, -1e9)), candidate.text_score
            )
            if candidate.text_score > record["candidate"].text_score:
                record["candidate"] = candidate

    download_candidates = [record["candidate"] for record in merged.values()]
    print(f"DOWNLOAD unique media: {len(download_candidates)}", flush=True)
    downloaded = []
    failures: Counter[str] = Counter()
    with futures.ThreadPoolExecutor(max_workers=28) as executor:
        for index, (candidate, payload, error) in enumerate(executor.map(download_one, download_candidates), 1):
            if payload is None:
                failures[error] += 1
            else:
                downloaded.append((candidate, payload))
            if index % 200 == 0:
                print(f"DOWNLOAD {index}/{len(download_candidates)} ok={len(downloaded)}", flush=True)

    # Exact/perceptual dedupe. Keep the stronger text candidate when two search
    # thumbnails are effectively the same image.
    downloaded.sort(key=lambda item: (-item[0].text_score, int(item[0].media_id)))
    accepted: list[tuple[Candidate, dict]] = []
    shas: set[str] = set()
    phashes: list[str] = []
    dhashes: list[str] = []
    duplicate_count = 0
    for candidate, payload in downloaded:
        if payload["sha256"] in shas:
            duplicate_count += 1
            continue
        is_dup = False
        for old_ph, old_dh in zip(phashes, dhashes):
            pd = hamming(payload["phash"], old_ph)
            if pd == 0 or (pd <= 4 and hamming(payload["dhash"], old_dh) <= 6):
                is_dup = True
                break
        if is_dup:
            duplicate_count += 1
            continue
        shas.add(payload["sha256"])
        phashes.append(payload["phash"])
        dhashes.append(payload["dhash"])
        accepted.append((candidate, payload))

    manifest = []
    for review_id, (candidate, payload) in enumerate(accepted, 1):
        filename = f"candidate_{review_id:05d}.jpg"
        (images / filename).write_bytes(payload.pop("data"))
        membership = merged[candidate.media_id]
        scores = membership["scores"]
        suggested_class = max(scores, key=scores.get)
        manifest.append({
            "review_id": review_id,
            "filename": filename,
            "media_kind": candidate.media_kind,
            "media_id": candidate.media_id,
            "slug": candidate.slug,
            "page_url": candidate.page_url,
            "thumb_url": candidate.thumb_url,
            "title": candidate.title,
            "author": candidate.author,
            "context": candidate.context,
            "incident_id": candidate.incident_id,
            "search_classes": ";".join(sorted(membership["search_classes"])),
            "queries": ";".join(sorted(membership["queries"])),
            "class_scores_json": json.dumps(scores, sort_keys=True),
            "suggested_class": suggested_class,
            **payload,
        })

    fields = list(manifest[0].keys()) if manifest else []
    with (output / "manifest.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(manifest)
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    stats = {
        "search_jobs": len(jobs),
        "raw_class_query_media_rows": len(raw),
        "selected_before_cross_class_merge": {k: len(v) for k, v in selected_by_class.items()},
        "unique_media_selected": len(download_candidates),
        "downloaded_quality_pass": len(downloaded),
        "duplicate_images_removed": duplicate_count,
        "final_review_images": len(manifest),
        "suggested_class_counts": dict(Counter(row["suggested_class"] for row in manifest)),
        "search_membership_counts": dict(Counter(
            group for row in manifest for group in row["search_classes"].split(";") if group
        )),
        "unique_incidents": len({row["incident_id"] for row in manifest}),
        "download_failures": dict(failures),
    }
    (output / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")

    archive = output / "dvids_thumbnail_review_pool.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(images.glob("*.jpg")):
            zf.write(path, f"images/{path.name}")
        for name in ("manifest.csv", "manifest.json", "stats.json"):
            zf.write(output / name, name)
    print(json.dumps(stats, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
