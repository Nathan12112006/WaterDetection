#!/usr/bin/env python3
"""Second-wave industrial water-event collector.

Uses later Bing/DDG image pages plus news images and video thumbnails. The search
strategy is intentionally independent of v2 so the two waves can be deduplicated
locally before final human review. All files are real web images; no generation or
scene modification is performed.
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import csv
import json
import random
import shutil
import time
import zipfile
from collections import Counter
from pathlib import Path

from ddgs import DDGS

from collect_industrial_water_candidates_v2 import (
    BAD_HOSTS,
    BAD_TEXT,
    EVENT_TERMS,
    INDUSTRIAL_TERMS,
    QUERIES,
    Hit,
    download,
    duplicate,
    host,
    normalize,
)

EXTRA_QUERIES: dict[str, list[str]] = {
    "pipe_burst": [
        'factory utility piping water rupture',
        'industrial maintenance pipe failure water spray',
        'process plant water line break spray',
        'plant engineering pipe burst incident water',
        'industrial cooling system pipe rupture water',
        'manufacturing facility pipe leak high pressure water',
        'indoor water main break factory machinery',
        'warehouse sprinkler pipe burst flooding',
        'industrial pump flange failure water jet',
        'water treatment facility pipe failure spray',
        'chiller plant broken water line spray',
        'mechanical equipment room burst pipe',
        'industrial valve packing failure water spray',
        'factory overhead water pipe rupture',
        'production plant pipe burst accident',
        'utility tunnel water pipe burst industrial',
        'boiler plant water line rupture',
        'cooling tower pump pipe burst water',
        'industrial filter housing pipe burst water',
        'RO plant high pressure water leak spray',
    ],
    "water_drop": [
        'industrial valve packing leak water drops',
        'pump mechanical seal leaking water droplets',
        'pump gland packing water drip industrial',
        'process pipe flange slow water leak drops',
        'factory pipe joint active dripping water',
        'chiller plant pipe coupling drip leak',
        'water treatment valve stem leak droplets',
        'industrial filter housing dripping leak',
        'RO membrane housing pipe drip leak',
        'industrial tank outlet valve dripping water',
        'mechanical room overhead pipe active drip',
        'factory utility pipe pinhole dripping water',
        'industrial pump casing leak water drip',
        'cooling water pipe small leak droplets plant',
        'process equipment fitting dripping water',
        'industrial flange gasket seep drip water',
        'boiler feedwater valve dripping leak',
        'industrial pipeline threaded joint water drops',
        'plant maintenance water leak droplet valve',
        'industrial instrumentation fitting water drip',
    ],
    "water_accumulation": [
        'industrial mechanical room water damage flood pumps',
        'factory utility room floor standing water',
        'manufacturing plant indoor flooding machinery',
        'water treatment equipment room flooded floor',
        'chilled water plant room floor flood',
        'boiler plant equipment room standing water',
        'industrial pump gallery flooding indoors',
        'factory production machinery water on floor flood',
        'warehouse machinery flooded floor indoors',
        'process facility floor puddle pipe leak',
        'industrial filtration room standing water',
        'RO water plant room floor flooded',
        'mechanical basement flooded pumps valves',
        'industrial control room adjacent flooding equipment',
        'plant utility corridor standing water pipes',
        'chiller equipment room puddle water leak',
        'factory compressor room flooded floor',
        'industrial tank room water accumulation floor',
        'manufacturing utility basement flood machinery',
        'pump station building indoor flood equipment',
    ],
}

ADDITIONAL_BAD = (
    "bathroom", "kitchen", "toilet", "bathtub", "shower", "residential", "apartment",
    "living room", "bedroom", "garden hose", "lawn", "swimming", "waterfall", "river",
    "lake", "street flood", "road flood", "natural disaster", "hurricane", "monsoon",
    "game", "movie", "anime", "manga", "poster", "infographic", "product mockup",
)


def loosely_useful(class_name: str, title: str, page_url: str, image_url: str) -> bool:
    text = " ".join((title, page_url, image_url)).lower()
    page_host = host(page_url)
    if any(term in text for term in BAD_TEXT + ADDITIONAL_BAD):
        return False
    if any(term in page_host for term in BAD_HOSTS):
        return False
    industrial = any(term in text for term in INDUSTRIAL_TERMS)
    event = any(term in text for term in EVENT_TERMS[class_name])
    return industrial or event


def image_hits(class_name: str, query: str) -> list[tuple[str, Hit]]:
    output: list[tuple[str, Hit]] = []
    seen: set[str] = set()
    for backend, pages in (("duckduckgo", (1, 2)), ("bing", (2, 3))):
        for page in pages:
            try:
                results = DDGS(timeout=20).images(
                    query=query,
                    region="us-en",
                    safesearch="moderate",
                    max_results=100,
                    page=page,
                    backend=backend,
                    size="Large",
                    type_image="photo",
                )
            except Exception as exc:
                print(f"images {backend} p{page} failed {query!r}: {exc}", flush=True)
                continue
            accepted = 0
            for item in results or []:
                image_url = str(item.get("image") or "").strip()
                page_url = str(item.get("url") or "").strip()
                title = str(item.get("title") or "").strip()
                source = str(item.get("source") or backend).strip()
                if not image_url.startswith(("http://", "https://")) or image_url in seen:
                    continue
                seen.add(image_url)
                if loosely_useful(class_name, title, page_url, image_url):
                    output.append((f"image:{backend}:p{page}", Hit(image_url, page_url, title, source, query)))
                    accepted += 1
            print(f"images {backend} p{page} {query!r}: {accepted}", flush=True)
    return output


def news_hits(class_name: str, query: str) -> list[tuple[str, Hit]]:
    output: list[tuple[str, Hit]] = []
    try:
        results = DDGS(timeout=20).news(
            query=query,
            region="us-en",
            safesearch="moderate",
            max_results=80,
            page=1,
            backend="bing,duckduckgo,yahoo",
        )
    except Exception as exc:
        print(f"news failed {query!r}: {exc}", flush=True)
        return output
    for item in results or []:
        image_url = str(item.get("image") or "").strip()
        page_url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        source = str(item.get("source") or "news").strip()
        if image_url.startswith(("http://", "https://")) and loosely_useful(class_name, title, page_url, image_url):
            output.append(("news", Hit(image_url, page_url, title, source, query)))
    print(f"news {query!r}: {len(output)}", flush=True)
    return output


def video_hits(class_name: str, query: str) -> list[tuple[str, Hit]]:
    output: list[tuple[str, Hit]] = []
    try:
        results = DDGS(timeout=20).videos(
            query=query,
            region="us-en",
            safesearch="moderate",
            max_results=80,
            page=1,
            backend="duckduckgo",
            resolution="high",
        )
    except Exception as exc:
        print(f"videos failed {query!r}: {exc}", flush=True)
        return output
    for item in results or []:
        images = item.get("images") or {}
        image_url = str(images.get("large") or images.get("medium") or images.get("small") or "").replace(" ", "").strip()
        page_url = str(item.get("content") or item.get("embed_url") or "").strip()
        title = str(item.get("title") or "").strip()
        source = str(item.get("publisher") or item.get("provider") or "video").strip()
        if image_url.startswith(("http://", "https://")) and loosely_useful(class_name, title, page_url, image_url):
            output.append(("video", Hit(image_url, page_url, title, source, query)))
    print(f"videos {query!r}: {len(output)}", flush=True)
    return output


def search_wave(class_name: str, query: str, index: int) -> list[tuple[str, Hit]]:
    hits = image_hits(class_name, query)
    if index % 2 == 0:
        hits.extend(news_hits(class_name, query))
    if index % 3 == 0:
        hits.extend(video_hits(class_name, query))
    unique: list[tuple[str, Hit]] = []
    seen: set[str] = set()
    for kind, hit in hits:
        if hit.image_url not in seen:
            seen.add(hit.image_url)
            unique.append((kind, hit))
    return unique


def collect(class_name: str, target: int, images: Path, writer: csv.DictWriter,
            shas: set[str], phashes: list[str], dhashes: list[str]) -> dict:
    queries = QUERIES[class_name] + EXTRA_QUERIES[class_name]
    accepted = 0
    attempted = 0
    seen_urls: set[str] = set()
    image_hosts: Counter[str] = Counter()
    page_hosts: Counter[str] = Counter()
    query_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    failures: Counter[str] = Counter()

    for query_index, query in enumerate(queries, 1):
        if accepted >= target:
            break
        candidates: list[tuple[str, Hit]] = []
        for kind, hit in search_wave(class_name, query, query_index):
            if hit.image_url in seen_urls:
                continue
            seen_urls.add(hit.image_url)
            image_host, page_host = host(hit.image_url), host(hit.page_url)
            if image_hosts[image_host] >= 30 or (page_host and page_hosts[page_host] >= 15):
                continue
            candidates.append((kind, hit))
        random.Random((hash(query) ^ 0xA55A5AA5) & 0xFFFFFFFF).shuffle(candidates)
        candidates = candidates[:100]
        with futures.ThreadPoolExecutor(max_workers=20) as pool:
            downloaded = pool.map(lambda pair: (pair[0],) + download(pair[1]), candidates)
            for kind, hit, raw, error in downloaded:
                if accepted >= target or query_counts[query] >= 10:
                    break
                attempted += 1
                if raw is None:
                    failures[error.split(":", 1)[0]] += 1
                    continue
                normalized = normalize(raw)
                if normalized is None:
                    failures["decode_or_quality"] += 1
                    continue
                data, width, height, sha, ph, dh = normalized
                if duplicate(sha, ph, dh, shas, phashes, dhashes):
                    failures["duplicate"] += 1
                    continue
                image_host, page_host = host(hit.image_url), host(hit.page_url)
                if image_hosts[image_host] >= 30 or (page_host and page_hosts[page_host] >= 15):
                    failures["domain_cap"] += 1
                    continue
                accepted += 1
                filename = f"wave2_{class_name}_{accepted:04d}.jpg"
                (images / filename).write_bytes(data)
                shas.add(sha); phashes.append(ph); dhashes.append(dh)
                image_hosts[image_host] += 1
                if page_host:
                    page_hosts[page_host] += 1
                query_counts[query] += 1
                kind_counts[kind] += 1
                writer.writerow({
                    "class": class_name,
                    "filename": filename,
                    "search_kind": kind,
                    "query": query,
                    "title": hit.title,
                    "source": hit.source,
                    "image_url": hit.image_url,
                    "page_url": hit.page_url,
                    "image_host": image_host,
                    "page_host": page_host,
                    "width": width,
                    "height": height,
                    "bytes": len(data),
                    "sha256": sha,
                    "phash": ph,
                    "dhash": dh,
                })
                if accepted % 20 == 0:
                    print(f"[{class_name}] {accepted}/{target}; query {query_index}/{len(queries)}", flush=True)
        time.sleep(0.25)

    return {
        "target": target,
        "accepted": accepted,
        "attempted_downloads": attempted,
        "unique_urls_seen": len(seen_urls),
        "search_kind_counts": dict(kind_counts),
        "top_image_hosts": image_hosts.most_common(20),
        "top_page_hosts": page_hosts.most_common(20),
        "query_counts": dict(query_counts),
        "failures": dict(failures),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="collector_output_wave2")
    parser.add_argument("--per-class", type=int, default=400)
    args = parser.parse_args()
    random.seed(20260822)

    output = Path(args.output)
    if output.exists():
        shutil.rmtree(output)
    images = output / "images"
    images.mkdir(parents=True)
    manifest = output / "manifest.csv"
    fields = [
        "class", "filename", "search_kind", "query", "title", "source", "image_url",
        "page_url", "image_host", "page_host", "width", "height", "bytes", "sha256",
        "phash", "dhash",
    ]
    stats: dict[str, object] = {}
    shas: set[str] = set(); phashes: list[str] = []; dhashes: list[str] = []
    with manifest.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for class_name in ("pipe_burst", "water_drop", "water_accumulation"):
            stats[class_name] = collect(class_name, args.per_class, images, writer, shas, phashes, dhashes)
            file.flush()

    stats["total_images"] = len(list(images.glob("*.jpg")))
    stats["generated_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (output / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    archive = output / "industrial_water_candidates_wave2.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(images.glob("*.jpg")):
            zf.write(path, f"images/{path.name}")
        zf.write(manifest, "manifest.csv")
        zf.write(output / "stats.json", "stats.json")
    print(json.dumps(stats, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
