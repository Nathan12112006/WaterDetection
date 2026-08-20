"""Build labeled contact sheets for manual dataset candidate review."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("inputs", nargs="+", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for folder in args.inputs:
        paths.extend(path for path in folder.rglob("*.jpg") if "_review" not in path.parts)
    paths.sort(key=lambda path: (path.parent.name, path.name))
    font = ImageFont.load_default(size=15)
    columns, rows = 5, 4
    cell_width, image_height, label_height = 280, 210, 48
    per_sheet = columns * rows
    for sheet_index in range(0, len(paths), per_sheet):
        batch = paths[sheet_index:sheet_index + per_sheet]
        canvas = Image.new("RGB", (columns * cell_width, rows * (image_height + label_height)), "white")
        draw = ImageDraw.Draw(canvas)
        for index, path in enumerate(batch):
            row, column = divmod(index, columns)
            x, y = column * cell_width, row * (image_height + label_height)
            with Image.open(path) as source:
                thumb = ImageOps.contain(ImageOps.exif_transpose(source).convert("RGB"), (cell_width - 8, image_height - 8))
            paste_x = x + (cell_width - thumb.width) // 2
            paste_y = y + (image_height - thumb.height) // 2
            canvas.paste(thumb, (paste_x, paste_y))
            short = f"{path.parent.name}/{path.name}"
            if len(short) > 39:
                short = short[:36] + "..."
            draw.text((x + 5, y + image_height + 4), short, fill="black", font=font)
        output = args.output / f"contact_sheet_{sheet_index // per_sheet + 1:02d}.jpg"
        canvas.save(output, "JPEG", quality=92)
    print(f"Created {(len(paths) + per_sheet - 1) // per_sheet} sheets for {len(paths)} images")


if __name__ == "__main__":
    main()
