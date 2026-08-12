"""Collect license-verifiable real water-event photos from Wikimedia Commons.

The output is a candidate pool for human annotation, not an automatic addition to
the project's train/valid/test splits. Files are resized by Commons to a maximum
width of 1600 px and deduplicated perceptually against the existing repository.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import html
import io
import json
import re
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError


API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "WaterDetectionDatasetCollector/1.0 (research dataset curation)"
LAST_API_REQUEST = 0.0
LAST_FILE_REQUEST = 0.0
TARGETS = {"pipe_burst": 72, "water_drops": 34, "water_accumulation": 22}
SEEDS = {
    "pipe_burst": [
        "Category:Pipe bursts",
        "Category:Water pipeline leaks",
        "Category:Water leakage",
        "Category:Water main breaks",
        "Category:Broken water mains",
    ],
    "water_drops": [
        "Category:Falling water droplets",
        "Category:Dripping water",
        "Category:Water droplets",
        "Category:Videos of water droplets",
    ],
    "water_accumulation": [
        "Category:Puddles",
        "Category:Indoor flooding",
        "Category:Water damage",
        "Category:Flooded buildings",
    ],
}
SEARCHES = {
    "pipe_burst": [
        '"pipe burst"', '"burst water main"', '"water main break"',
        '"broken water main"', '"ruptured pipe"', '"pipe patching"',
        '"leaking pipe"', '"water pipe leak"', '"pipeline leak"',
        '"water line break"', '"water line leak"', '"broken pipe" water',
    ],
    "water_drops": [
        '"water droplet"', '"water droplets"', '"falling water drop"',
        '"dripping water"', '"water drip"', '"drop of water"',
    ],
    "water_accumulation": [
        '"standing water"', '"wet floor"', '"indoor flooding"',
        '"water damage" floor', 'puddle indoors', '"flooded room"',
    ],
}

EXCLUDED_MEDIA_WORDS = {
    "illustration", "diagram", "drawing", "painting", "artwork", "icon",
    "logo", "map", "animation", "render", "rendered", "synthetic",
    "midjourney", "stable diffusion", "dall-e", "ai generated", "generated ai",
    "screenshot", "comic", "poster", "chart", "schema", "3d model",
}
ALLOWED_LICENSE_PATTERNS = (
    "public domain", "cc0", "pdm", "cc by ", "cc-by-", "cc by-sa", "cc-by-sa",
)


@dataclass
class Candidate:
    category: str
    title: str
    page_id: int
    page_url: str
    original_url: str
    download_url: str
    author: str
    license_name: str
    license_url: str
    description: str
    source_category: str


def api_get(params: dict[str, object], retries: int = 4) -> dict:
    global LAST_API_REQUEST
    query = {"format": "json", "formatversion": 2, **params}
    url = API + "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            since_last = time.monotonic() - LAST_API_REQUEST
            if since_last < 0.65:
                time.sleep(0.65 - since_last)
            with urllib.request.urlopen(request, timeout=45) as response:
                LAST_API_REQUEST = time.monotonic()
                return json.load(response)
        except urllib.error.HTTPError as exc:
            LAST_API_REQUEST = time.monotonic()
            if exc.code != 429 or attempt == retries - 1:
                raise
            retry_after = exc.headers.get("Retry-After")
            time.sleep(float(retry_after) if retry_after and retry_after.isdigit() else 12 * (attempt + 1))
        except Exception:
            LAST_API_REQUEST = time.monotonic()
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")


def clean_html(value: str | None) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def category_files(category: str, max_depth: int = 0, max_files: int = 300) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    queue = [(category, 0)]
    visited: set[str] = set()
    while queue:
        current, depth = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        continuation: str | None = None
        while True:
            params: dict[str, object] = {
                "action": "query", "list": "categorymembers", "cmtitle": current,
                "cmtype": "file|subcat", "cmlimit": "max",
            }
            if continuation:
                params["cmcontinue"] = continuation
            data = api_get(params)
            members = data.get("query", {}).get("categorymembers", [])
            for member in members:
                title = member["title"]
                if member["ns"] == 6:
                    found.append((title, current))
                    if len(found) >= max_files:
                        return found
                elif member["ns"] == 14 and depth < max_depth:
                    queue.append((title, depth + 1))
            continuation = data.get("continue", {}).get("cmcontinue")
            if not continuation:
                break
    return found


def chunks(values: list[tuple[str, str]], size: int) -> list[list[tuple[str, str]]]:
    return [values[index:index + size] for index in range(0, len(values), size)]


def search_files(query: str, limit: int = 100) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    continuation: int | None = None
    while len(found) < limit:
        params: dict[str, object] = {
            "action": "query", "list": "search", "srnamespace": 6,
            "srsearch": query, "srlimit": min(100, limit - len(found)),
        }
        if continuation is not None:
            params["sroffset"] = continuation
        data = api_get(params)
        for result in data.get("query", {}).get("search", []):
            found.append((result["title"], f"Commons search: {query}"))
        continuation = data.get("continue", {}).get("sroffset")
        if continuation is None:
            break
    return found


def metadata_for(category: str, titles: list[tuple[str, str]]) -> list[Candidate]:
    results: list[Candidate] = []
    source_by_title = dict(titles)
    for batch in chunks(titles, 40):
        data = api_get({
            "action": "query", "prop": "imageinfo", "titles": "|".join(x[0] for x in batch),
            "iiprop": "url|mime|size|extmetadata", "iiurlwidth": 1600,
        })
        for page in data.get("query", {}).get("pages", []):
            if page.get("missing") or not page.get("imageinfo"):
                continue
            info = page["imageinfo"][0]
            if info.get("mime") not in {"image/jpeg", "image/png", "image/webp"}:
                continue
            meta = info.get("extmetadata", {})
            get = lambda key: clean_html(meta.get(key, {}).get("value"))
            license_name = get("LicenseShortName") or get("UsageTerms")
            searchable = " ".join((page["title"], get("ImageDescription"), get("ObjectName"))).lower()
            if any(word in searchable for word in EXCLUDED_MEDIA_WORDS):
                continue
            normalized_license = license_name.lower()
            if not any(pattern in normalized_license for pattern in ALLOWED_LICENSE_PATTERNS):
                continue
            if "noncommercial" in normalized_license or "no derivatives" in normalized_license:
                continue
            results.append(Candidate(
                category=category,
                title=page["title"],
                page_id=int(page["pageid"]),
                page_url=info.get("descriptionurl", ""),
                original_url=info.get("url", ""),
                download_url=info.get("thumburl") or info.get("url", ""),
                author=get("Artist") or get("Credit"),
                license_name=license_name,
                license_url=get("LicenseUrl"),
                description=get("ImageDescription"),
                source_category=source_by_title.get(page["title"], ""),
            ))
        time.sleep(0.08)
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
    hashes: list[int] = []
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
    for path in root.rglob("*"):
        if path.suffix.lower() not in extensions or "collected_real_photos_" in str(path):
            continue
        try:
            with Image.open(path) as image:
                hashes.append(dhash(image))
        except (OSError, UnidentifiedImageError):
            continue
    return hashes


def download(url: str, retries: int = 2) -> bytes:
    global LAST_FILE_REQUEST
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        since_last = time.monotonic() - LAST_FILE_REQUEST
        if since_last < 1.1:
            time.sleep(1.1 - since_last)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                LAST_FILE_REQUEST = time.monotonic()
                return response.read()
        except urllib.error.HTTPError as exc:
            LAST_FILE_REQUEST = time.monotonic()
            if exc.code != 429 or attempt == retries - 1:
                raise
            retry_after = exc.headers.get("Retry-After")
            time.sleep(float(retry_after) if retry_after and retry_after.isdigit() else 5 * (attempt + 1))
    raise RuntimeError("unreachable")


def download_candidate(candidate: Candidate) -> tuple[Candidate, bytes | None, str]:
    try:
        return candidate, download(candidate.download_url), ""
    except Exception as exc:
        return candidate, None, str(exc)


def relevance(candidate: Candidate) -> int:
    text = f"{candidate.title} {candidate.description} {candidate.source_category}".lower()
    terms = {
        "pipe_burst": ("burst", "broken", "rupture", "main break", "pipeline leak", "pipe leak", "leaking pipe", "water leak"),
        "water_drops": ("droplet", "water drop", "drip", "dripping", "falling drop"),
        "water_accumulation": ("puddle", "standing water", "water damage", "flooded", "flooding", "wet floor"),
    }[candidate.category]
    return sum(5 for term in terms if term in text) + (3 if "photograph" in text else 0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--targets-json", default="")
    parser.add_argument("--drops-target", type=int)
    parser.add_argument("--accumulation-target", type=int)
    args = parser.parse_args()
    targets = TARGETS if not args.targets_json else json.loads(args.targets_json)
    if args.drops_target is not None or args.accumulation_target is not None:
        targets = {}
        if args.drops_target is not None:
            targets["water_drops"] = args.drops_target
        if args.accumulation_target is not None:
            targets["water_accumulation"] = args.accumulation_target
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    known_hashes = existing_hashes(args.root.resolve())
    accepted_hashes: list[int] = []
    accepted: list[dict[str, object]] = []
    rejected: list[dict[str, str]] = []

    for category, target in targets.items():
        folder = output / category
        folder.mkdir(exist_ok=True)
        discovered: dict[str, tuple[str, str]] = {}
        for seed in SEEDS[category]:
            try:
                for title, source in category_files(seed):
                    discovered.setdefault(title, (title, source))
            except Exception as exc:
                rejected.append({"category": category, "title": seed, "reason": f"category query failed: {exc}"})
        for query in SEARCHES[category]:
            try:
                for title, source in search_files(query):
                    discovered.setdefault(title, (title, source))
            except Exception as exc:
                rejected.append({"category": category, "title": query, "reason": f"search query failed: {exc}"})
        candidates = metadata_for(category, list(discovered.values()))
        candidates.sort(key=lambda item: (-relevance(item), item.title.lower()))
        count = 0
        download_candidates = candidates[: max(target * 7, 250)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            downloaded = executor.map(download_candidate, download_candidates)
            for processed, (candidate, raw, download_error) in enumerate(downloaded, start=1):
                if count >= target:
                    break
                try:
                    if raw is None:
                        raise ValueError(f"download failed: {download_error}")
                    with Image.open(io.BytesIO(raw)) as source_image:
                        source_image.load()
                        if source_image.width < 300 or source_image.height < 300:
                            raise ValueError("image smaller than 300 px")
                        image_hash = dhash(source_image)
                        if any(hamming(image_hash, known) <= 5 for known in known_hashes):
                            raise ValueError("near-duplicate of existing repository image")
                        if any(hamming(image_hash, known) <= 5 for known in accepted_hashes):
                            raise ValueError("near-duplicate within new collection")
                        rgb = ImageOps.exif_transpose(source_image).convert("RGB")
                        digest = hashlib.sha256(rgb.tobytes()).hexdigest()[:12]
                        filename = f"{category}_{count + 1:03d}_{candidate.page_id}_{digest}.jpg"
                        destination = folder / filename
                        rgb.save(destination, "JPEG", quality=93, optimize=True)
                    accepted_hashes.append(image_hash)
                    accepted.append({
                        "filename": destination.relative_to(output).as_posix(),
                        "category": category,
                        "source_title": candidate.title,
                        "source_page": candidate.page_url,
                        "original_file_url": candidate.original_url,
                        "downloaded_thumbnail_url": candidate.download_url,
                        "author": candidate.author,
                        "license": candidate.license_name,
                        "license_url": candidate.license_url,
                        "source_category": candidate.source_category,
                        "description": candidate.description,
                        "perceptual_hash": f"{image_hash:x}",
                    })
                    count += 1
                except Exception as exc:
                    rejected.append({"category": category, "title": candidate.title, "reason": str(exc)})
                if processed % 25 == 0:
                    print(f"{category}: reviewed {processed}, accepted {count}", flush=True)
        print(f"{category}: accepted {count}/{target} from {len(candidates)} licensed candidates", flush=True)

    fields = list(accepted[0].keys()) if accepted else ["filename", "category"]
    with (output / "manifest.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(accepted)
    with (output / "rejected.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["category", "title", "reason"])
        writer.writeheader()
        writer.writerows(rejected)
    print(f"TOTAL_ACCEPTED={len(accepted)}")


if __name__ == "__main__":
    main()
