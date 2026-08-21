#!/usr/bin/env python3
"""Collect real-world industrial water-event image candidates for later visual review.

The script searches Bing Images in several languages, downloads the underlying image
URLs (not search thumbnails), validates and normalizes them, and performs exact plus
perceptual deduplication. It never generates or edits scene content.
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
from bs4 import BeautifulSoup
from PIL import Image, ImageOps, UnidentifiedImageError

QUERIES: dict[str, list[str]] = {
    "pipe_burst": [
        "industrial pipe burst water factory",
        "mechanical room pipe burst water",
        "chilled water pipe burst mechanical room",
        "pump room pipe rupture water",
        "boiler room pipe burst flooding",
        "industrial flange leak spray water",
        "process piping rupture water jet",
        "factory pipe rupture water spray",
        "water treatment plant pipe burst",
        "HVAC plant room pipe burst water spray",
        "industrial valve failure water jet",
        "industrial pipeline leak high pressure water spray indoors",
        "utility room pipe burst water",
        "manufacturing plant water line rupture",
        "industrial cooling water pipe burst",
        "industrial pump discharge pipe burst",
        "broken industrial water pipe spraying",
        "industrial pipe joint failure water jet",
        "工厂 管道 爆裂 喷水",
        "机房 水管 爆裂 喷水",
        "冷冻水管 爆裂 机房",
        "水泵房 管道 破裂 漏水",
        "工业 阀门 漏水 喷水",
        "Rohrbruch Maschinenraum Wasser",
        "Wasserrohrbruch Industriehalle",
        "Rohrbruch Pumpenraum",
        "Rohrleitung Leck Wasserstrahl Anlage",
        "rupture canalisation local technique eau",
        "fuite tuyau industriel jet d'eau usine",
        "rupture tuyauterie salle des machines",
        "rotura tubería sala de máquinas agua",
        "fuga tubería industrial chorro agua fábrica",
        "tubería rota sala de bombas",
        "rottura tubo locale tecnico acqua",
        "perdita tubazione industriale getto acqua",
        "pęknięta rura hala produkcyjna woda",
        "awaria rury maszynownia woda",
        "工場 配管 破裂 漏水",
        "機械室 配管 破裂 水漏れ",
        "공장 배관 파열 누수",
        "기계실 수도관 파열",
        "разрыв трубы машинный зал вода",
        "прорыв трубы в котельной",
    ],
    "water_drop": [
        "industrial valve dripping water",
        "industrial pipe joint drip leak",
        "industrial flange water drip factory",
        "mechanical room pipe dripping water",
        "pump seal leaking water drip",
        "industrial equipment dripping water",
        "boiler valve dripping water",
        "chiller pipe active drip leak",
        "water treatment plant valve dripping",
        "RO system pipe leak dripping water",
        "factory overhead pipe dripping water",
        "industrial tank fitting leak droplets",
        "pipe flange droplet leak closeup industrial",
        "industrial pump gland water dripping",
        "industrial pipe coupling drip leak",
        "mechanical plant valve leak droplets",
        "industrial water filter housing drip leak",
        "factory machinery water dripping leak",
        "industrial pipe pinhole leak dripping",
        "process plant pipe leak droplets",
        "工业 阀门 滴水",
        "机房 管道 滴水",
        "工厂 配管 漏水 水滴",
        "纯水设备 漏水 滴水",
        "水泵 密封 滴漏",
        "Ventil tropft Wasser Industrieanlage",
        "Rohr tropft Maschinenraum",
        "Flansch undicht Wassertropfen Industrie",
        "vanne industrielle goutte eau fuite",
        "tuyau goutte local technique",
        "bride fuite gouttes eau usine",
        "válvula industrial goteando agua",
        "tubería goteando sala de máquinas",
        "brida fuga gotas agua industria",
        "valvola industriale gocciola acqua",
        "tubo gocciola locale tecnico",
        "zawór przemysłowy kapie woda",
        "rura kapie maszynownia",
        "工場 バルブ 水滴 漏れ",
        "機械室 配管 水滴",
        "공장 밸브 물방울 누수",
        "기계실 배관 물방울",
        "промышленный клапан капает вода",
        "труба капает в машинном отделении",
    ],
    "water_accumulation": [
        "mechanical room flooding water",
        "pump room flooded water",
        "boiler room flooding water",
        "chiller plant flooding water",
        "industrial plant floor flooded",
        "factory floor water leak puddle machinery",
        "water treatment plant floor flooding",
        "utility room standing water pumps",
        "HVAC mechanical room water leak floor",
        "industrial warehouse water accumulation machinery",
        "plant room flooded equipment",
        "industrial basement flooding pumps pipes",
        "process plant puddle water leak",
        "factory production line flooded floor",
        "industrial equipment room standing water",
        "pump station indoor flooding",
        "industrial boiler plant standing water floor",
        "mechanical equipment room puddle leak",
        "industrial utility corridor flooding",
        "manufacturing facility indoor water flood",
        "机房 积水",
        "水泵房 淹水",
        "工厂 车间 积水",
        "工业 厂房 漏水 积水",
        "纯水房 漏水 积水",
        "新风机房 漏水",
        "冷冻机房 积水",
        "设备间 水浸",
        "Überschwemmung Maschinenraum",
        "Heizungsraum überflutet",
        "Pumpenraum Hochwasser innen",
        "Industriehalle Wasser auf Boden",
        "inondation local technique",
        "chaufferie inondée eau",
        "salle des pompes inondée",
        "usine sol inondé machines",
        "inundación sala de máquinas",
        "sala de bombas inundada",
        "fábrica suelo inundado maquinaria",
        "allagamento locale tecnico",
        "sala pompe allagata",
        "fabbrica pavimento allagato macchinari",
        "zalana maszynownia",
        "zalana hala produkcyjna woda",
        "overstroming technische ruimte",
        "工場 床 浸水 機械",
        "機械室 浸水",
        "공장 바닥 침수 기계",
        "기계실 침수",
        "затопление машинного зала",
        "затопило котельную оборудование",
    ],
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/123.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
]
BAD_HINTS = ("data:image", "favicon", "sprite", "logo", "icon", "avatar", "placeholder", "blank.", "transparent", "loading.", "pixel.")
BAD_PAGE_HOSTS = {"pinterest.com", "pinterest.ca", "pinterest.co.uk", "pinterest.de"}

@dataclass(frozen=True)
class Hit:
    image_url: str
    page_url: str
    query: str


def host(url: str) -> str:
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": random.choice(USER_AGENTS), "Accept-Language": "en-US,en;q=0.8"})
    return s


def bing_search(query: str, pages: int = 3) -> list[Hit]:
    s = session()
    found: list[Hit] = []
    seen: set[str] = set()
    for page in range(pages):
        url = "https://www.bing.com/images/search?" + urllib.parse.urlencode({
            "q": query,
            "first": 1 + page * 35,
            "count": 100,
            "qft": "+filterui:imagesize-medium",
        })
        try:
            r = s.get(url, timeout=30)
            r.raise_for_status()
        except Exception as exc:
            print(f"search failed {query!r} page {page}: {exc}", flush=True)
            break
        soup = BeautifulSoup(r.text, "html.parser")
        added = 0
        for node in soup.select("a.iusc"):
            raw = node.get("m")
            if not raw:
                continue
            try:
                meta = json.loads(raw)
            except Exception:
                continue
            image_url = str(meta.get("murl") or "").replace("&amp;", "&").strip()
            page_url = str(meta.get("purl") or "").replace("&amp;", "&").strip()
            low = image_url.lower()
            if not image_url.startswith(("http://", "https://")) or any(x in low for x in BAD_HINTS):
                continue
            if image_url in seen or host(page_url) in BAD_PAGE_HOSTS:
                continue
            seen.add(image_url)
            found.append(Hit(image_url, page_url, query))
            added += 1
        print(f"search {query!r} page {page}: {added} URLs", flush=True)
        if added < 8:
            break
        time.sleep(0.35)
    return found


def download(hit: Hit) -> tuple[Hit, bytes | None, str]:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": hit.page_url or "https://www.bing.com/",
    }
    try:
        with requests.get(hit.image_url, headers=headers, stream=True, timeout=(10, 25), allow_redirects=True) as r:
            r.raise_for_status()
            ctype = (r.headers.get("content-type") or "").lower()
            if "html" in ctype or "json" in ctype:
                return hit, None, "bad content type"
            chunks: list[bytes] = []
            size = 0
            for chunk in r.iter_content(65536):
                if not chunk:
                    continue
                size += len(chunk)
                if size > 18_000_000:
                    return hit, None, "too large"
                chunks.append(chunk)
            data = b"".join(chunks)
            if len(data) < 12_000:
                return hit, None, "too small"
            return hit, data, ""
    except Exception as exc:
        return hit, None, str(exc)[:160]


def bits_hex(bits: np.ndarray) -> str:
    return np.packbits(np.asarray(bits, dtype=np.uint8).reshape(-1)).tobytes().hex()


def phash(gray: np.ndarray) -> str:
    x = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    values = cv2.dct(x)[:8, :8].ravel()
    return bits_hex(values > float(np.median(values[1:])))


def dhash(gray: np.ndarray) -> str:
    x = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    return bits_hex(x[:, 1:] > x[:, :-1])


def hamming(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()


def normalize(raw: bytes) -> tuple[bytes, int, int, str, str, str] | None:
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image = ImageOps.exif_transpose(image)
            if getattr(image, "is_animated", False):
                image.seek(0)
            image = image.convert("RGB")
            w, h = image.size
            if min(w, h) < 480 or max(w, h) < 640 or max(w, h) / max(1, min(w, h)) > 4.2:
                return None
            thumb = np.asarray(image.resize((128, 128), Image.Resampling.BILINEAR))
            if float(cv2.cvtColor(thumb, cv2.COLOR_RGB2GRAY).std()) < 9.0:
                return None
            if max(w, h) > 1800:
                scale = 1800.0 / max(w, h)
                image = image.resize((round(w * scale), round(h * scale)), Image.Resampling.LANCZOS)
                w, h = image.size
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=90, optimize=True, progressive=True)
            data = buffer.getvalue()
            gray = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
            return data, w, h, hashlib.sha256(data).hexdigest(), phash(gray), dhash(gray)
    except (UnidentifiedImageError, OSError, ValueError):
        return None


def is_duplicate(sha: str, ph: str, dh: str, shas: set[str], phashes: list[str], dhashes: list[str]) -> bool:
    if sha in shas:
        return True
    for old_ph, old_dh in zip(phashes, dhashes):
        pd = hamming(ph, old_ph)
        if pd == 0 or (pd <= 5 and hamming(dh, old_dh) <= 7):
            return True
    return False


def collect(class_name: str, target: int, images: Path, writer: csv.DictWriter,
            shas: set[str], phashes: list[str], dhashes: list[str]) -> dict:
    queries = QUERIES[class_name][:]
    random.Random(20260821 + len(class_name)).shuffle(queries)
    accepted = 0
    attempted = 0
    seen_urls: set[str] = set()
    image_hosts: Counter[str] = Counter()
    page_hosts: Counter[str] = Counter()
    query_counts: Counter[str] = Counter()
    failures: Counter[str] = Counter()

    for index, query in enumerate(queries, 1):
        if accepted >= target:
            break
        hits = []
        for hit in bing_search(query, pages=3):
            if hit.image_url in seen_urls:
                continue
            seen_urls.add(hit.image_url)
            if image_hosts[host(hit.image_url)] >= 40 or (host(hit.page_url) and page_hosts[host(hit.page_url)] >= 25):
                continue
            hits.append(hit)
        random.Random(hash(query) & 0xFFFFFFFF).shuffle(hits)
        hits = hits[:90]
        with futures.ThreadPoolExecutor(max_workers=24) as pool:
            for hit, raw, error in pool.map(download, hits):
                if accepted >= target or query_counts[query] >= 28:
                    break
                attempted += 1
                if raw is None:
                    failures[error.split(":", 1)[0]] += 1
                    continue
                normalized = normalize(raw)
                if normalized is None:
                    failures["decode_or_quality"] += 1
                    continue
                data, w, h, sha, ph, dh = normalized
                if is_duplicate(sha, ph, dh, shas, phashes, dhashes):
                    failures["duplicate"] += 1
                    continue
                ih, phost = host(hit.image_url), host(hit.page_url)
                if image_hosts[ih] >= 40 or (phost and page_hosts[phost] >= 25):
                    failures["domain_cap"] += 1
                    continue
                accepted += 1
                filename = f"{class_name}_{accepted:04d}.jpg"
                (images / filename).write_bytes(data)
                shas.add(sha)
                phashes.append(ph)
                dhashes.append(dh)
                image_hosts[ih] += 1
                if phost:
                    page_hosts[phost] += 1
                query_counts[query] += 1
                writer.writerow({
                    "class": class_name,
                    "filename": filename,
                    "query": query,
                    "image_url": hit.image_url,
                    "page_url": hit.page_url,
                    "image_host": ih,
                    "page_host": phost,
                    "width": w,
                    "height": h,
                    "bytes": len(data),
                    "sha256": sha,
                    "phash": ph,
                    "dhash": dh,
                })
                if accepted % 25 == 0:
                    print(f"[{class_name}] {accepted}/{target}, query {index}/{len(queries)}", flush=True)
        time.sleep(0.25)

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
    fields = ["class", "filename", "query", "image_url", "page_url", "image_host", "page_host", "width", "height", "bytes", "sha256", "phash", "dhash"]
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
