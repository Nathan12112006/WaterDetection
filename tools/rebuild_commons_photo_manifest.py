"""Rebuild source/license metadata for Commons downloads from page IDs in filenames."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "WaterDetectionDatasetCollector/1.0 (manifest reconstruction)"


def clean(value: str | None) -> str:
    value = html.unescape(value or "")
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def query(page_ids: list[str]) -> list[dict]:
    params = urllib.parse.urlencode({
        "action": "query", "format": "json", "formatversion": 2,
        "pageids": "|".join(page_ids), "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata",
    })
    request = urllib.request.Request(f"{API}?{params}", headers={"User-Agent": USER_AGENT})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response).get("query", {}).get("pages", [])
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 4:
                raise
            time.sleep(10 * (attempt + 1))
    return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args()
    files: dict[str, Path] = {}
    for root in args.inputs:
        for path in root.rglob("*.jpg"):
            match = re.search(r"_(\d+)_([0-9a-f]{12})\.jpg$", path.name, re.I)
            if match:
                files[match.group(1)] = path.resolve()
    metadata: dict[str, dict] = {}
    ids = list(files)
    for offset in range(0, len(ids), 40):
        for page in query(ids[offset:offset + 40]):
            metadata[str(page.get("pageid"))] = page
        time.sleep(1)
    rows = []
    for page_id, path in files.items():
        page = metadata.get(page_id, {})
        info = (page.get("imageinfo") or [{}])[0]
        ext = info.get("extmetadata") or {}
        get = lambda key: clean((ext.get(key) or {}).get("value"))
        rows.append({
            "filename": str(path), "category": path.parent.name,
            "source_title": page.get("title", ""),
            "source_page": info.get("descriptionurl", ""),
            "original_file_url": info.get("url", ""),
            "author": get("Artist") or get("Credit"),
            "license": get("LicenseShortName") or get("UsageTerms"),
            "license_url": get("LicenseUrl"),
            "description": get("ImageDescription"),
            "commons_page_id": page_id,
        })
    fields = list(rows[0]) if rows else ["filename", "category"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote metadata for {sum(bool(row['source_page']) for row in rows)}/{len(rows)} files")


if __name__ == "__main__":
    main()
