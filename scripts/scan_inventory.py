#!/usr/bin/env python3
"""Phase 0.5 — read-only inventory scan for un-reviewed folders.

Before running phase0_ingest.py against a folder, use this to answer
"whose photos are these" quickly: it walks folders, counts images, shows
an approximate date range, and builds a small thumbnail contact sheet per
folder so you can eyeball it. It NEVER copies, moves, or touches your
original photos — it only writes small thumbnail contact sheets and a
summary report to --output.

Usage (Windows example):
    python scan_inventory.py ^
        --root "C:\\Users\\you\\Dropbox" ^
        --skip "C:\\Users\\you\\Dropbox\\Camera Uploads\\Myles Baby Pics" ^
        --output "inventory_review"

Pass --skip once per folder you've already reviewed/approved (e.g. the
folders you've already run through phase0_ingest.py), so re-running this
only reports on what's left. --root can be passed more than once.

After reviewing the contact sheets in --output/contact_sheets/, pass the
folders you recognize as yours to phase0_ingest.py's --source; leave
anything that looks like a customer/client backup alone entirely.
"""
import argparse
import csv
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Missing dependency. Run: pip install -r requirements.txt", file=sys.stderr)
    raise

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

# Reuse the same EXIF date logic as the ingestion script so dates are
# consistent between the scan report and the real archive run.
from phase0_ingest import extract_taken_at, IMAGE_EXTENSIONS

THUMB_SIZE = (150, 150)
GRID_COLUMNS = 4


def find_review_units(roots, depth):
    """Return folders at `depth` levels below each root that contain any
    images (recursively). depth=1 means immediate subfolders of --root."""
    units = []
    for root in roots:
        root = Path(root)
        if depth <= 0:
            candidates = [root]
        else:
            candidates = [root]
            for _ in range(depth):
                candidates = [c for r in candidates for c in r.iterdir() if c.is_dir()]
        for candidate in candidates:
            units.append(candidate)
    return units


def is_under_any(path: Path, skip_paths) -> bool:
    resolved = path.resolve()
    for skip in skip_paths:
        skip_resolved = Path(skip).resolve()
        if resolved == skip_resolved or skip_resolved in resolved.parents:
            return True
    return False


def iter_images_in(folder: Path):
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def sample_evenly(items, count):
    if len(items) <= count:
        return items
    step = len(items) / count
    return [items[int(i * step)] for i in range(count)]


def analyze_samples(sample_paths):
    """Open each sample once, returning (name, thumbnail, taken_at) triples.
    Reusing the same open() for both the thumbnail and the EXIF date avoids
    reading each file twice, and gives a far more meaningful date range than
    file mtime — Dropbox sync can rewrite every file's mtime to the sync
    date, unrelated to when the photo was actually taken."""
    results = []
    for path in sample_paths:
        try:
            with Image.open(path) as img:
                taken_at = extract_taken_at(img, path)
                img = img.convert("RGB")
                img.thumbnail(THUMB_SIZE)
                results.append((path.name, img.copy(), taken_at))
        except Exception:
            results.append((f"(unreadable: {path.name})", None, None))
    return results


def build_contact_sheet(folder_label: str, samples, output_path: Path):
    thumbs = [(name, thumb) for name, thumb, _ in samples]
    if not thumbs:
        return None

    rows = (len(thumbs) + GRID_COLUMNS - 1) // GRID_COLUMNS
    cell_w, cell_h = THUMB_SIZE[0] + 10, THUMB_SIZE[1] + 30
    sheet = Image.new("RGB", (GRID_COLUMNS * cell_w, rows * cell_h + 30), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    draw.text((5, 5), folder_label, fill="black", font=font)

    for i, (name, thumb) in enumerate(thumbs):
        col, row = i % GRID_COLUMNS, i // GRID_COLUMNS
        x, y = col * cell_w + 5, row * cell_h + 35
        if thumb is not None:
            sheet.paste(thumb, (x, y))
        draw.text((x, y + THUMB_SIZE[1] + 2), name[:22], fill="black", font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=80)
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", action="append", required=True, help="Top-level folder to scan (repeatable)")
    parser.add_argument("--skip", action="append", default=[], help="Folder to skip entirely, e.g. already-reviewed folders (repeatable)")
    parser.add_argument("--depth", type=int, default=1, help="Folder depth below --root to treat as one review unit (default: 1)")
    parser.add_argument("--samples", type=int, default=12, help="Max thumbnails per contact sheet (default: 12)")
    parser.add_argument("--output", default="inventory_review", help="Output folder for contact sheets + report")
    args = parser.parse_args()

    output_root = Path(args.output)
    sheets_dir = output_root / "contact_sheets"
    units = find_review_units(args.root, args.depth)

    rows = []
    print(f"Found {len(units)} folder(s) to consider at depth {args.depth}.\n")

    for unit in units:
        if is_under_any(unit, args.skip):
            continue

        images = sorted(iter_images_in(unit))
        if not images:
            continue

        sample_paths = sample_evenly(images, args.samples)
        samples = analyze_samples(sample_paths)
        safe_name = "_".join(unit.parts[-3:]).replace(":", "").replace(" ", "_")
        sheet_path = sheets_dir / f"{safe_name}.jpg"
        build_contact_sheet(str(unit), samples, sheet_path)

        taken_dates = [taken_at.date() for _, _, taken_at in samples if taken_at is not None]
        if taken_dates:
            date_range = f"{min(taken_dates)} to {max(taken_dates)}"
        else:
            date_range = "unknown"

        rows.append(
            {
                "folder": str(unit),
                "image_count": len(images),
                "sample_date_range": date_range,
                "contact_sheet": str(sheet_path),
            }
        )
        print(f"{unit}  ({len(images)} images, sample dates: {date_range})")
        print(f"  -> contact sheet: {sheet_path}")

    if rows:
        report_path = output_root / "inventory_report.csv"
        output_root.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nWrote summary for {len(rows)} folder(s) to {report_path}")
        print(f"Contact sheets in {sheets_dir} — review these, then pass the folders")
        print("you recognize as yours to phase0_ingest.py's --source.")
    else:
        print("\nNothing new to review (everything under --root was in --skip, or had no images).")


if __name__ == "__main__":
    main()
