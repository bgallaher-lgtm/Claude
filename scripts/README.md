# Phase 0 ingestion prototype

Scans your Dropbox folder (and any disc folders), de-duplicates, reads each
photo's real capture date from EXIF, and copies confirmed-unique photos
into a dated `PhotoArchive/by-year/YYYY/` folder. It never modifies or
deletes anything in your source folders — see `DESIGN.md` §2 for the full
reasoning.

## Setup (Windows)

1. Install Python from [python.org](https://python.org) if you don't
   already have it (check "Add python.exe to PATH" during install).
2. Open a terminal in this `scripts` folder and run:
   ```
   pip install -r requirements.txt
   ```

## Test on a small subset first

Point `--source` at one small folder (not your whole Dropbox yet) and use
`--dry-run` to see what *would* happen without copying anything:

```
python phase0_ingest.py --source "C:\Users\you\Dropbox\Camera Uploads\2024" --archive "D:\PhotoArchive" --limit 200 --dry-run
```

Check the summary and open `manifest_near_duplicates.json` (only created
if any near-duplicates were flagged) to see what it *thinks* are
duplicates before trusting it on the full library. Nothing is ever
deleted — exact duplicates are just skipped from copying, and
near-duplicates are only ever flagged in that report for you to look at.

Once it looks right, drop `--limit` and `--dry-run` to actually run it:

```
python phase0_ingest.py --source "C:\Users\you\Dropbox" --archive "D:\PhotoArchive" --manifest manifest.json
```

Pass `--source` multiple times to include disc folders alongside Dropbox:

```
python phase0_ingest.py --source "C:\Users\you\Dropbox" --source "D:\Disc1" --archive "D:\PhotoArchive" --manifest manifest.json
```

The run is safe to stop and re-start — it checks `manifest.json` and
skips anything already archived, so re-running (e.g. after adding more
discs) only processes new files.

## Known limitations of this prototype

- **Near-duplicate detection is brute-force** (compares every new photo's
  perceptual hash against every previously seen one). Fine for testing on
  a subset; the full ~50,000-photo run will need this replaced with an
  indexed nearest-neighbor search (planned for the real Phase 0 build —
  see `DESIGN.md` §6).
- **HEIC/HEIF (iPhone photos)** need the optional `pillow-heif` package,
  already included in `requirements.txt`.
- This script only handles ingestion/dedup/dating — face detection and
  tagging (Phase 1) isn't built yet.
