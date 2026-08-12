"""Collect reusable real-photo candidates through the Openverse image index."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError


API = "https://api.openverse.org/v1/images/"
USER_AGENT = "WaterDetectionDatasetCollector/1.0 (Openverse research dataset curation)"
TARGETS = {"pipe_burst": 80, "water_drops": 30, "water_accumulation": 20}
QUERIES = {
    "pipe_burst": [
        "burst water main", "water main break", "broken water main", "burst water pipe",
        "ruptured water pipe", "leaking pipe", "water pipe leak", "broken pipe water",
        "water line break", "water line leak", "pipe spraying water", "pipe rupture water",
        "fire hydrant leak", "water main rupture", "plumbing pipe leak",
    ],
    "water_drops": [
        "water droplet", "water droplets", "falling water drop", "dripping water",
        "water drip", "drop of water", "droplet falling", "leaking faucet drop",
    ],
    "water_accumulation": [
        "standing water", "wet floor", "indoor flooding", "water damage floor",
        "indoor puddle", "flooded room", "water accumulation floor", "basement water leak",
    ],
}
EXCLUDED_WORDS = {
    "illustration", "drawing", "painting", "render", "rendered", "digital art", "artwork",
    "diagram", "logo", "icon", "poster", "comic", "midjourney", "stable diffusion",
    "dall-e", "ai generated", "generative ai", "synthetic", "3d model", "clipart",
}
ALLOWED_LICENSES = {"cc0", "pdm", "by", "by-sa"}
ALLOWED_SOURCES = {"flickr", "wikimedia", "nasa", "smithsonian", "clevelandmuseum"}


def get_json(url: str, retries: int = 5) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in {429, 500, 502, 503, 504} or attempt == retries - 1:
                raise
            time.sleep(4 * (attempt + 1))
    raise RuntimeError("unreachable")


def search(query: str, pages: int = 2) -> list[dict]:
    results: list[dict] = []
    for page in range(1, pages + 1):
        params = urllib.parse.urlencode({
            "q": query, "license": "cc0,pdm,by,by-sa", "page_size": 50, "page": page,
            "extension": "jpg,jpeg,png,webp",
        })
        data = get_json(f"{API}?{params}")
        results.extend(data.get("results", []))
        if not data.get("next"):
            break
        time.sleep(0.4)
    return results


def dhash(image: Image.Image, size: int = 12) -> int:
    gray = ImageOps.grayscale(image).resize((size + 1, size), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    value = 0
    for row in range(size):
        offset = row * (size + 1)
        for col in range(size):
            value = (value << 1) | (pixels[offset + col] > pixels[offset + col + 1])
    return value


def hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def existing_hashes(root: Path) -> list[int]:
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
    excluded = {"real_water_photos_final", "real_water_photos_100plus", "collected_real_photos_2026-08-04"}
    hashes: list[int] = []
    for path in root.rglob("*"):
        if path.suffix.lower() not in extensions or any(part in excluded for part in path.parts):
            continue
        try:
            with Image.open(path) as image:
                hashes.append(dhash(image))
        except (OSError, UnidentifiedImageError):
            pass
    return hashes


def download(url: str, retries: int = 4) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "image/*"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def text_for(result: dict) -> str:
    tags = " ".join(tag.get("name", "") for tag in (result.get("tags") or []) if isinstance(tag, dict))
    return html.unescape(f"{result.get('title') or ''} {tags}").lower()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    known_hashes = existing_hashes(args.root.resolve())
    accepted_hashes: list[int] = []
    accepted: list[dict] = []
    rejected: list[dict] = []

    for category, target in TARGETS.items():
        folder = output / category
        folder.mkdir(exist_ok=True)
        discovered: dict[str, tuple[dict, str]] = {}
        for query in QUERIES[category]:
            try:
                for result in search(query):
                    identifier = result.get("id") or result.get("url")
                    if identifier:
                        discovered.setdefault(identifier, (result, query))
            except Exception as exc:
                rejected.append({"category": category, "title": query, "reason": f"search failed: {exc}"})
        candidates = list(discovered.values())
        candidates.sort(key=lambda pair: (pair[0].get("source") != "flickr", (pair[0].get("title") or "").lower()))
        count = 0
        for reviewed, (result, query) in enumerate(candidates, start=1):
            if count >= target:
                break
            title = (result.get("title") or "untitled").strip()
            try:
                license_name = (result.get("license") or "").lower()
                source = (result.get("source") or "").lower()
                if license_name not in ALLOWED_LICENSES:
                    raise ValueError("license not in allowlist")
                if source not in ALLOWED_SOURCES:
                    raise ValueError(f"source not in allowlist: {source}")
                if any(word in text_for(result) for word in EXCLUDED_WORDS):
                    raise ValueError("non-photographic or AI-related metadata")
                media_url = result.get("url") or result.get("thumbnail")
                if not media_url:
                    raise ValueError("missing media URL")
                raw = download(media_url)
                with Image.open(io.BytesIO(raw)) as source_image:
                    source_image.load()
                    if source_image.width < 300 or source_image.height < 300:
                        raise ValueError("image smaller than 300 px")
                    image_hash = dhash(source_image)
                    if any(hamming(image_hash, known) <= 5 for known in known_hashes):
                        raise ValueError("near-duplicate of existing repository image")
                    if any(hamming(image_hash, known) <= 5 for known in accepted_hashes):
                        raise ValueError("near-duplicate within new collection")
                    image = ImageOps.exif_transpose(source_image).convert("RGB")
                    image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
                    digest = hashlib.sha256(image.tobytes()).hexdigest()[:12]
                    safe_id = re.sub(r"[^a-zA-Z0-9]+", "", str(result.get("id") or ""))[:12]
                    filename = f"{category}_{count + 1:03d}_{safe_id}_{digest}.jpg"
                    destination = folder / filename
                    image.save(destination, "JPEG", quality=93, optimize=True)
                accepted_hashes.append(image_hash)
                accepted.append({
                    "filename": destination.relative_to(output).as_posix(),
                    "category": category,
                    "source_title": title,
                    "source_page": result.get("foreign_landing_url") or "",
                    "media_url": media_url,
                    "creator": result.get("creator") or "",
                    "creator_url": result.get("creator_url") or "",
                    "license": license_name,
                    "license_version": result.get("license_version") or "",
                    "license_url": result.get("license_url") or "",
                    "provider": result.get("provider") or "",
                    "source": source,
                    "search_query": query,
                    "openverse_id": result.get("id") or "",
                    "perceptual_hash": f"{image_hash:x}",
                })
                count += 1
            except Exception as exc:
                rejected.append({"category": category, "title": title, "reason": str(exc)})
            if reviewed % 25 == 0:
                print(f"{category}: reviewed {reviewed}, accepted {count}", flush=True)
            time.sleep(0.25)
        print(f"{category}: accepted {count}/{target} from {len(candidates)} candidates", flush=True)

    fields = list(accepted[0].keys()) if accepted else ["filename", "category"]
    with (output / "manifest.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(accepted)
    with (output / "rejected.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "title", "reason"])
        writer.writeheader()
        writer.writerows(rejected)
    print(f"TOTAL_ACCEPTED={len(accepted)}", flush=True)


if __name__ == "__main__":
    main()
