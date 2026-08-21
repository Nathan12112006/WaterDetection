#!/usr/bin/env python3
"""Collect real industrial water-event image candidates through structured search.

This version uses DDGS structured image results instead of scraping a search page,
rejects obvious illustration/celebrity/wallpaper sources, downloads original image
URLs, validates files, and performs exact plus perceptual deduplication. The output
remains a candidate pool for later visual review; nothing is AI-generated.
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import csv
import hashlib
import io
import json
import random
import shutil
import time
import urllib.parse
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import requests
from ddgs import DDGS
from PIL import Image, ImageOps, UnidentifiedImageError

QUERIES: dict[str, list[str]] = {
    "pipe_burst": [
        '"mechanical room" "pipe burst" water',
        '"industrial pipe" water spray leak',
        '"pump room" pipe rupture water',
        '"chilled water pipe" burst',
        '"boiler room" pipe burst water',
        '"factory" broken pipe water spray',
        '"industrial flange" water spray leak',
        '"process piping" rupture water jet',
        '"water treatment plant" pipe burst',
        '"utility room" pipe burst water',
        '"industrial valve" water jet leak',
        '"manufacturing plant" water line rupture',
        '"cooling water pipe" burst factory',
        '"pump discharge pipe" burst water',
        '"industrial pipe joint" failure water spray',
        '"machine room" broken water pipe',
        '"HVAC plant room" pipe burst',
        '"plant room" water pipe spraying',
        'Rohrbruch Maschinenraum Wasser',
        'Rohrbruch Pumpenraum Wasser',
        'rupture tuyauterie salle des machines eau',
        'fuite tuyau industriel jet eau usine',
        'rotura tubería sala de máquinas agua',
        'fuga tubería industrial chorro agua fábrica',
        'rottura tubo locale tecnico acqua',
        'perdita tubazione industriale getto acqua',
        '工厂 管道 爆裂 喷水',
        '机房 水管 爆裂 喷水',
        '水泵房 管道 破裂 漏水',
        '工場 配管 破裂 漏水',
        '機械室 配管 破裂 水漏れ',
        '공장 배관 파열 누수',
        'разрыв трубы машинный зал вода',
    ],
    "water_drop": [
        '"industrial valve" dripping water',
        '"industrial pipe joint" drip leak',
        '"pipe flange" water droplet leak',
        '"mechanical room" pipe dripping',
        '"pump seal" leaking water drip',
        '"industrial equipment" dripping water',
        '"boiler valve" dripping water',
        '"chiller pipe" active drip leak',
        '"water treatment plant" valve dripping',
        '"RO system" pipe leak dripping',
        '"factory overhead pipe" dripping water',
        '"industrial tank fitting" leak droplets',
        '"pump gland" water dripping',
        '"industrial pipe coupling" drip leak',
        '"mechanical plant" valve leak droplets',
        '"water filter housing" drip leak industrial',
        '"factory machinery" water dripping leak',
        '"industrial pipe" pinhole leak dripping',
        '"process plant" pipe leak droplets',
        'Ventil tropft Wasser Industrieanlage',
        'Rohr tropft Maschinenraum',
        'Flansch undicht Wassertropfen Industrie',
        'vanne industrielle goutte eau fuite',
        'tuyau goutte local technique',
        'válvula industrial goteando agua',
        'tubería goteando sala de máquinas',
        'valvola industriale gocciola acqua',
        'tubo gocciola locale tecnico',
        '工业 阀门 滴水',
        '机房 管道 滴水',
        '工場 バルブ 水滴 漏れ',
        '機械室 配管 水滴',
        '공장 밸브 물방울 누수',
        'промышленный клапан капает вода',
    ],
    "water_accumulation": [
        '"mechanical room" flooding water',
        '"pump room" flooded water',
        '"boiler room" flooding water',
        '"chiller plant" flooding water',
        '"industrial plant" floor flooded',
        '"factory floor" water leak puddle machinery',
        '"water treatment plant" floor flooding',
        '"utility room" standing water pumps',
        '"HVAC mechanical room" water leak floor',
        '"industrial warehouse" water accumulation machinery',
        '"plant room" flooded equipment',
        '"industrial basement" flooding pumps pipes',
        '"process plant" puddle water leak',
        '"factory production line" flooded floor',
        '"industrial equipment room" standing water',
        '"pump station" indoor flooding',
        '"boiler plant" standing water floor',
        '"mechanical equipment room" puddle leak',
        '"industrial utility corridor" flooding',
        '"manufacturing facility" indoor water flood',
        'Überschwemmung Maschinenraum',
        'Heizungsraum überflutet Wasser',
        'Pumpenraum Hochwasser innen',
        'Industriehalle Wasser auf Boden',
        'inondation local technique eau',
        'chaufferie inondée eau',
        'salle des pompes inondée',
        'usine sol inondé machines',
        'inundación sala de máquinas',
        'sala de bombas inundada',
        'fábrica suelo inundado maquinaria',
        'allagamento locale tecnico',
        'sala pompe allagata',
        'fabbrica pavimento allagato macchinari',
        '机房 积水',
        '水泵房 淹水',
        '工厂 车间 积水',
        '工业 厂房 漏水 积水',
        '純水房 漏水 积水',
        '冷冻机房 积水',
        '工場 床 浸水 機械',
        '機械室 浸水',
        '공장 바닥 침수 기계',
        'затопление машинного зала',
    ],
}

INDUSTRIAL_TERMS = (
    "industrial", "industry", "factory", "manufacturing", "plant", "mechanical",
    "machine room", "pump room", "boiler", "chiller", "hvac", "ahu", "utility",
    "process", "pipeline", "piping", "pipe", "valve", "flange", "pump", "equipment",
    "machinery", "warehouse", "water treatment", "filtration", "technical room",
    "maschinenraum", "pumpenraum", "industrie", "usine", "industriel", "salle des machines",
    "fábrica", "industrial", "sala de máquinas", "fabbrica", "locale tecnico",
    "工厂", "机房", "水泵房", "工业", "工場", "機械室", "공장", "기계실", "машин",
)
EVENT_TERMS: dict[str, tuple[str, ...]] = {
    "pipe_burst": (
        "burst", "rupture", "broken pipe", "pipe break", "spray", "spraying", "water jet",
        "gushing", "leak", "rohrbruch", "wasserstrahl", "rupture", "jet eau", "rotura",
        "chorro", "rottura", "getto", "爆裂", "破裂", "喷水", "破裂", "파열", "разрыв",
    ),
    "water_drop": (
        "drip", "dripping", "droplet", "drop leak", "leak", "tropft", "wassertropfen",
        "goutte", "goteando", "gocciola", "滴水", "水滴", "물방울", "капает",
    ),
    "water_accumulation": (
        "flood", "flooded", "flooding", "standing water", "puddle", "water damage", "water leak",
        "überflutet", "hochwasser", "inond", "inund", "allagat", "积水", "淹水", "浸水", "침수", "затоп",
    ),
}
BAD_TEXT = (
    "illustration", "vector", "clipart", "cartoon", "drawing", "diagram", "3d render", "rendering",
    "ai generated", "generative ai", "craiyon", "midjourney", "stable diffusion", "wallpaper",
    "celebrity", "actress", "actor", "model photo", "fashion", "temple", "church", "tourism",
    "swimming pool", "beach", "fountain", "hydrant", "firefighter", "washdown", "washing",
)
BAD_HOSTS = (
    "pinterest.", "deviantart.com", "craiyon.com", "wallpapers.com", "wallpaperaccess.com",
    "pngtree.com", "vecteezy.com", "vectorstock.com", "clipart", "freepik.com",
)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/123.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
]

@dataclass(frozen=True)
class Hit:
    image_url: str
    page_url: str
    title: str
    source: str
    query: str


def host(url: str) -> str:
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def useful_result(class_name: str, title: str, page_url: str, image_url: str) -> bool:
    text = " ".join((title, page_url, image_url)).lower()
    if any(term in text for term in BAD_TEXT) or any(term in host(page_url) for term in BAD_HOSTS):
        return False
    industrial = any(term in text for term in INDUSTRIAL_TERMS)
    event = any(term in text for term in EVENT_TERMS[class_name])
    return industrial and event


def structured_search(class_name: str, query: str, max_results: int = 120) -> list[Hit]:
    try:
        results = DDGS(timeout=20).images(
            query=query,
            region="us-en",
            safesearch="moderate",
            max_results=max_results,
            backend="auto",
            size="Large",
            type_image="photo",
        )
    except Exception as exc:
        print(f"DDGS failed {query!r}: {exc}", flush=True)
        return []
    hits: list[Hit] = []
    seen: set[str] = set()
    for item in results or []:
        image_url = str(item.get("image") or "").strip()
        page_url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        source = str(item.get("source") or "").strip()
        if not image_url.startswith(("http://", "https://")) or image_url in seen:
            continue
        seen.add(image_url)
        if useful_result(class_name, title, page_url, image_url):
            hits.append(Hit(image_url, page_url, title, source, query))
    print(f"DDGS {query!r}: {len(hits)} filtered hits from {len(results or [])}", flush=True)
    return hits


def download(hit: Hit) -> tuple[Hit, bytes | None, str]:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": hit.page_url or "https://duckduckgo.com/",
    }
    try:
        with requests.get(hit.image_url, headers=headers, stream=True, timeout=(10, 25), allow_redirects=True) as response:
            response.raise_for_status()
            content_type = (response.headers.get("content-type") or "").lower()
            if "html" in content_type or "json" in content_type:
                return hit, None, "bad content type"
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(65536):
                if not chunk:
                    continue
                size += len(chunk)
                if size > 18_000_000:
                    return hit, None, "too large"
                chunks.append(chunk)
            raw = b"".join(chunks)
            if len(raw) < 12_000:
                return hit, None, "too small"
            return hit, raw, ""
    except Exception as exc:
        return hit, None, str(exc)[:160]


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


def normalize(raw: bytes) -> tuple[bytes, int, int, str, str, str] | None:
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image = ImageOps.exif_transpose(image)
            if getattr(image, "is_animated", False):
                image.seek(0)
            image = image.convert("RGB")
            width, height = image.size
            if min(width, height) < 480 or max(width, height) < 640:
                return None
            if max(width, height) / max(1, min(width, height)) > 4.2:
                return None
            thumb = np.asarray(image.resize((128, 128), Image.Resampling.BILINEAR))
            if float(cv2.cvtColor(thumb, cv2.COLOR_RGB2GRAY).std()) < 9.0:
                return None
            if max(width, height) > 1800:
                scale = 1800.0 / max(width, height)
                image = image.resize((round(width * scale), round(height * scale)), Image.Resampling.LANCZOS)
                width, height = image.size
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=90, optimize=True, progressive=True)
            data = buffer.getvalue()
            gray = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
            return data, width, height, hashlib.sha256(data).hexdigest(), phash(gray), dhash(gray)
    except (UnidentifiedImageError, OSError, ValueError):
        return None


def duplicate(sha: str, ph: str, dh: str, shas: set[str], phashes: list[str], dhashes: list[str]) -> bool:
    if sha in shas:
        return True
    for old_ph, old_dh in zip(phashes, dhashes):
        distance = hamming(ph, old_ph)
        if distance == 0 or (distance <= 5 and hamming(dh, old_dh) <= 7):
            return True
    return False


def collect(class_name: str, target: int, images: Path, writer: csv.DictWriter,
            shas: set[str], phashes: list[str], dhashes: list[str]) -> dict:
    accepted = 0
    attempted = 0
    seen_urls: set[str] = set()
    image_hosts: Counter[str] = Counter()
    page_hosts: Counter[str] = Counter()
    query_counts: Counter[str] = Counter()
    failures: Counter[str] = Counter()

    for query_index, query in enumerate(QUERIES[class_name], 1):
        if accepted >= target:
            break
        hits: list[Hit] = []
        for hit in structured_search(class_name, query):
            if hit.image_url in seen_urls:
                continue
            seen_urls.add(hit.image_url)
            image_host, page_host = host(hit.image_url), host(hit.page_url)
            if image_hosts[image_host] >= 30 or (page_host and page_hosts[page_host] >= 18):
                continue
            hits.append(hit)
        random.Random(hash(query) & 0xFFFFFFFF).shuffle(hits)
        hits = hits[:65]
        with futures.ThreadPoolExecutor(max_workers=20) as pool:
            for hit, raw, error in pool.map(download, hits):
                if accepted >= target or query_counts[query] >= 12:
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
                if image_hosts[image_host] >= 30 or (page_host and page_hosts[page_host] >= 18):
                    failures["domain_cap"] += 1
                    continue
                accepted += 1
                filename = f"{class_name}_{accepted:04d}.jpg"
                (images / filename).write_bytes(data)
                shas.add(sha)
                phashes.append(ph)
                dhashes.append(dh)
                image_hosts[image_host] += 1
                if page_host:
                    page_hosts[page_host] += 1
                query_counts[query] += 1
                writer.writerow({
                    "class": class_name,
                    "filename": filename,
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
                if accepted % 10 == 0:
                    print(f"[{class_name}] {accepted}/{target}; query {query_index}/{len(QUERIES[class_name])}", flush=True)
        time.sleep(0.3)

    return {
        "target": target,
        "accepted": accepted,
        "attempted_downloads": attempted,
        "unique_urls_seen": len(seen_urls),
        "top_image_hosts": image_hosts.most_common(20),
        "top_page_hosts": page_hosts.most_common(20),
        "query_counts": dict(query_counts),
        "failures": dict(failures),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="collector_output")
    parser.add_argument("--per-class", type=int, default=650)
    args = parser.parse_args()
    random.seed(20260821)

    output = Path(args.output)
    if output.exists():
        shutil.rmtree(output)
    images = output / "images"
    images.mkdir(parents=True)
    manifest = output / "manifest.csv"
    fields = [
        "class", "filename", "query", "title", "source", "image_url", "page_url",
        "image_host", "page_host", "width", "height", "bytes", "sha256", "phash", "dhash",
    ]
    stats: dict[str, object] = {}
    shas: set[str] = set()
    phashes: list[str] = []
    dhashes: list[str] = []
    with manifest.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for class_name in ("pipe_burst", "water_drop", "water_accumulation"):
            stats[class_name] = collect(class_name, args.per_class, images, writer, shas, phashes, dhashes)
            file.flush()

    stats["total_images"] = len(list(images.glob("*.jpg")))
    stats["generated_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    (output / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    archive = output / "industrial_water_candidates.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(images.glob("*.jpg")):
            zf.write(path, f"images/{path.name}")
        zf.write(manifest, "manifest.csv")
        zf.write(output / "stats.json", "stats.json")
    print(json.dumps(stats, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
