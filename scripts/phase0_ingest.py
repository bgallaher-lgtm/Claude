#!/usr/bin/env python3
"""Phase 0 ingestion: scan source photo folders, de-duplicate, extract
EXIF dates, and build a dated PhotoArchive/ directory.

Usage (Windows example):
    python phase0_ingest.py ^
        --source "C:\\Users\\you\\Dropbox\\Camera Uploads" ^
        --archive "D:\\PhotoArchive" ^
        --limit 200 --dry-run

Pass --source multiple times to include disc folders alongside Dropbox.
Drop --dry-run once a subset run looks right, to actually copy files.

Safe by design: never modifies or deletes anything under --source. Only
writes new files under --archive and a manifest tracking what's been
processed, which exact duplicates were skipped, and which files look like
possible near-duplicates for you to review (nothing gets auto-deleted).
"""
import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ExifTags
except ImportError:
    print("Missing dependency. Run: pip install -r requirements.txt", file=sys.stderr)
    raise

try:
    import imagehash
except ImportError:
    print("Missing dependency. Run: pip install -r requirements.txt", file=sys.stderr)
    raise

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass  # HEIC/HEIF (iPhone) support is optional; see requirements.txt.

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".tif", ".tiff", ".bmp", ".gif"}

# Hamming distance between perceptual hashes below this is flagged as a
# possible near-duplicate. Lower = stricter (fewer false flags, may miss
# some real near-duplicates). Tune after looking at a real report.
NEAR_DUP_HASH_THRESHOLD = 5


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_taken_at(img: "Image.Image", path: Path) -> datetime:
    try:
        exif = img.getexif()
        if exif:
            # DateTimeOriginal lives in the Exif sub-IFD, not the top-level
            # IFD that getexif() returns directly — it has to be fetched
            # separately and merged in, or capture dates silently vanish
            # and every photo falls back to file-modified date.
            tags = {ExifTags.TAGS.get(tag_id): value for tag_id, value in exif.items()}
            try:
                sub_ifd = exif.get_ifd(0x8769)  # Exif SubIFD pointer
                tags.update({ExifTags.TAGS.get(tag_id): value for tag_id, value in sub_ifd.items()})
            except Exception:
                pass
            for tag in ("DateTimeOriginal", "DateTime"):
                value = tags.get(tag)
                if value:
                    try:
                        return datetime.strptime(str(value).strip(), "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        continue
    except Exception:
        pass
    return datetime.fromtimestamp(path.stat().st_mtime)  # fallback: file date


def compute_phash(img: "Image.Image"):
    try:
        return imagehash.phash(img)
    except Exception:
        return None


def load_manifest(manifest_path: Path) -> dict:
    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"by_checksum": {}, "phashes": {}}


def save_manifest(manifest_path: Path, manifest: dict) -> None:
    tmp = manifest_path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, default=str)
    tmp.replace(manifest_path)


def hamming_distance(hash_a: str, hash_b: str) -> int:
    return bin(int(hash_a, 16) ^ int(hash_b, 16)).count("1")


def archive_destination(archive_root: Path, taken_at: datetime, checksum: str, ext: str) -> Path:
    year_dir = archive_root / "by-year" / str(taken_at.year)
    filename = f"{taken_at.strftime('%Y-%m-%d_%H%M%S')}_{checksum[:8]}{ext.lower()}"
    return year_dir / filename


def iter_image_files(source_dirs):
    for source in source_dirs:
        for path in Path(source).rglob("*"):
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                yield path


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--source", action="append", required=True,
        help="Source folder to scan (repeat --source for Dropbox + each disc folder)",
    )
    parser.add_argument("--archive", required=True, help="Destination PhotoArchive root folder")
    parser.add_argument("--manifest", default="manifest.json", help="Path to manifest JSON (default: manifest.json)")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N files (for testing on a subset)")
    parser.add_argument("--dry-run", action="store_true", help="Report what would happen without copying files or saving the manifest")
    args = parser.parse_args()

    archive_root = Path(args.archive)
    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)

    stats = {"scanned": 0, "archived": 0, "exact_duplicates": 0, "near_duplicate_flags": 0, "errors": 0}
    near_duplicate_report = []

    files = list(iter_image_files(args.source))
    if args.limit:
        files = files[: args.limit]

    print(f"Found {len(files)} image file(s) to process across {len(args.source)} source folder(s).")
    if args.dry_run:
        print("(dry run — nothing will be copied or saved)")

    for path in files:
        stats["scanned"] += 1
        try:
            checksum = sha256_of_file(path)
        except Exception as e:
            print(f"  ERROR reading {path}: {e}")
            stats["errors"] += 1
            continue

        if checksum in manifest["by_checksum"]:
            manifest["by_checksum"][checksum]["source_paths"].append(str(path))
            stats["exact_duplicates"] += 1
            continue

        try:
            with Image.open(path) as img:
                img.load()
                taken_at = extract_taken_at(img, path)
                phash = compute_phash(img)
        except Exception as e:
            print(f"  ERROR reading image {path}: {e}")
            stats["errors"] += 1
            continue

        phash_str = str(phash) if phash is not None else None
        if phash_str:
            # NOTE: brute-force scan against every prior phash. Fine for a
            # subset test; the real 50k-photo run needs an indexed nearest-
            # neighbor search instead of this O(n^2) loop (see DESIGN.md §6).
            for other_checksum, other_hash in manifest["phashes"].items():
                if hamming_distance(phash_str, other_hash) <= NEAR_DUP_HASH_THRESHOLD:
                    near_duplicate_report.append(
                        {
                            "new_file": str(path),
                            "possible_match_checksum": other_checksum,
                            "possible_match_path": manifest["by_checksum"][other_checksum]["archive_path"],
                        }
                    )
                    stats["near_duplicate_flags"] += 1
                    break

        dest = archive_destination(archive_root, taken_at, checksum, path.suffix)

        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                dest = dest.with_name(dest.stem + "_" + checksum[8:12] + dest.suffix)
            shutil.copy2(path, dest)

        manifest["by_checksum"][checksum] = {
            "archive_path": str(dest),
            "taken_at": taken_at.isoformat(),
            "source_paths": [str(path)],
        }
        if phash_str:
            manifest["phashes"][checksum] = phash_str

        stats["archived"] += 1
        if stats["scanned"] % 100 == 0:
            print(f"  ...{stats['scanned']} scanned so far")

    if not args.dry_run:
        save_manifest(manifest_path, manifest)

    if near_duplicate_report:
        report_path = manifest_path.with_name(manifest_path.stem + "_near_duplicates.json")
        with report_path.open("w", encoding="utf-8") as f:
            json.dump(near_duplicate_report, f, indent=2)
        print(f"\nWrote {len(near_duplicate_report)} possible near-duplicate flag(s) to {report_path}")
        print("Review these yourself — nothing is auto-deleted or auto-merged.")

    print("\n--- Summary ---")
    for key, value in stats.items():
        print(f"{key}: {value}")
    if args.dry_run:
        print("(dry run — no files were copied, no manifest changes saved)")


if __name__ == "__main__":
    main()
