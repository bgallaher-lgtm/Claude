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

## Triaging unknown folders before archiving them

If your Dropbox mixes personal photos with other stuff (e.g. client/backup
folders from work), don't run `phase0_ingest.py` blindly against
everything — use `scan_inventory.py` first. It's **read-only**: it never
copies your original photos anywhere. For each folder it finds, it counts
the images, reads an approximate date range from EXIF, and builds a small
thumbnail contact sheet so you can tell at a glance whose photos they are.

```
python scan_inventory.py --root "C:\Users\you\Dropbox" --skip "C:\Users\you\Dropbox\Camera Uploads\Myles Baby Pics" --output inventory_review
```

Pass `--skip` once for every folder you've already reviewed/archived (so
re-running only reports on what's left). Then open
`inventory_review\contact_sheets\` and flip through the thumbnails —
folder path is in the header of each sheet. Once you know which folders
are actually yours, pass those to `phase0_ingest.py --source`; leave
anything that looks like someone else's backup alone entirely.

This step doesn't need face recognition to be useful — a folder's contents
and date range are usually enough to tell whose photos they are. Once
Phase 1 (face detection/tagging) exists, it can add a second signal (e.g.
"zero matches to any named family member"), but it's not a prerequisite
for this triage pass.

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
