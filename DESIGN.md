# Family Photo Archive & Auto-Tagging — Design Doc

**Goal:** ingest a large personal photo library, automatically recognize
recurring people (you, Holly, Myles, etc.), let you confirm/correct tags
through a review workflow, and then query the tagged archive to assemble
photo books ("Myles, by year," "Me + Holly + Myles") that get exported for
printing through a service like Shutterfly.

**Short answer: yes, this is very doable**, and the pieces are all
well-established (face detection, face recognition/clustering, a tagging
database, a query layer). The one piece that *isn't* fully automatable is
the final print step — no major photo-book printer (Shutterfly, Mixbook,
Snapfish, etc.) exposes a public API to auto-generate a book, so the
pipeline's job is to get you to a curated, ordered set of photos per book
that's a fast manual upload, not to place the Shutterfly order itself.

---

## 1. How the auto-tagging actually works

This breaks into four capabilities, each of which is standard (not
research-grade) computer vision at this point:

1. **Face detection** — find every face in every photo, output a bounding
   box per face. Fast, reliable, works on old and new photos alike.
2. **Face embedding** — for each detected face, compute a numeric vector
   ("faceprint") such that the same person's face — across photos, angles,
   lighting, years — lands at nearby points in vector space, and different
   people land far apart.
3. **Clustering (for the "who is this" problem)** — group all embeddings
   from your whole library by proximity, *before* any name is attached.
   Each cluster is (ideally) one real person appearing across many photos.
   This is what makes "sort first, tag later" possible: you don't need to
   label photo-by-photo, you label *clusters* — one decision covers every
   photo that person appears in.
4. **Nearest-neighbor matching (for ongoing auto-tag)** — once you've named
   a handful of clusters ("this is Myles"), every new photo you add gets its
   faces embedded and matched against the known-person embeddings. Above a
   confidence threshold, it's auto-tagged; below it, the face drops into the
   "unidentified" pool for you to review.

This maps directly onto your requested workflow:

- **Upload everything, including photos with no people** → step 1 simply
  finds zero faces in those; they're archived and searchable by date/place
  but never enter the tagging queue.
- **"Sort, then I tell you who people are"** → step 3. Instead of asking you
  to label thousands of individual photos, the system shows you maybe a few
  dozen to a few hundred *face clusters* (representative face crops), and
  you name each cluster once.
- **"Keep untagged people in a directory I can identify"** → any cluster
  that doesn't confidently match a named person (new person, or a bad
  cluster split) lands in an "Unidentified" review queue/folder — exactly
  the directory you described. You name them or merge/split clusters as
  needed, and the system re-propagates.
- **"Book by year of Myles" / "Me, Holly, and Myles"** → once faces are
  tagged, this is a straightforward database query: `photos WHERE
  person = 'Myles' AND year = 2024`, or `WHERE person IN ('Me','Holly','Myles')
  AND all present`. The interesting design work is in step 2 below (schema)
  and the query/curation UI, not in new CV work.

**Known hard cases worth setting expectations on up front:**

- **Young kids' faces change fast.** A recognizer trained on Myles at age 2
  will do worse on Myles at age 6. Practically this means re-reviewing/
  correcting the "Myles" cluster periodically rather than expecting one
  training pass to hold forever — the tools should make correction cheap
  (see §4), not try to eliminate it.
- **Look-alike relatives / siblings** reduce match confidence — the
  threshold tuning in §4 trades off "auto-tag more, correct more" vs.
  "auto-tag conservatively, review more."
- **Old scanned/low-res photos** detect and embed faces less reliably;
  expect a higher fraction of those to land in manual review.

---

## 2. Ingesting your existing library (Dropbox + discs), de-duplication, and directory strategy

At ~50,000 photos across Dropbox with more still to add from discs, and
likely duplicates throughout, three things need to happen before the
tagging pipeline even starts: pull everything into one place, find
duplicates without silently deleting anything, and give you a growing
"trusted, organized" directory you can watch fill up as photos get
processed.

**Pulling from Dropbox**
- If the Dropbox desktop app already syncs the full library to a local
  folder, ingestion can just read that folder directly — simplest option,
  no API integration needed.
- If you'd rather not sync all 50k photos to a local machine, the Dropbox
  API (official Python SDK) can list and download in batches instead.
  Either way, this is a one-time bulk pull; at this volume, budget for it
  taking a while over ordinary internet bandwidth — 50,000 photos is
  plausibly 100–250GB depending on typical file size.

**Adding the discs**
- Each disc feeds through the same ingestion path (checksum + EXIF
  extraction) as the Dropbox pull — a disc is just another source folder.
  Disc photos are often *older* scans/exports that may already exist in
  Dropbox in some form, so this is exactly where duplicate detection earns
  its keep.

**Duplicate detection — two tiers, because deleting the wrong photo is not
an acceptable failure mode here:**
1. **Exact duplicates (safe to auto-collapse):** a SHA-256 checksum of the
   file bytes. Byte-identical copies — the same file synced twice, the
   same export downloaded twice, a disc that turns out to be a backup of
   files already in Dropbox — are true duplicates regardless of filename
   or folder. These get merged into a single library entry automatically;
   nothing is deleted, the extra copies just aren't re-imported as
   separate photos.
2. **Near-duplicates (flagged for your review, never auto-removed):**
   perceptual hashing (pHash) catches the same photo re-saved at a
   different size/quality/format — common when a disc scan and a Dropbox
   upload are technically different files but the same picture. This is
   fundamentally different from two similar-but-distinct shots (e.g., a
   burst of 5 frames a second apart at an event) — the tool should surface
   near-duplicate groups as *suggestions* in a review screen, not delete
   anything automatically. Given these are irreplaceable family photos,
   the only fully automatic action is on byte-exact copies; everything
   else stays a human decision.

**Directory strategy — protecting your sources and building a trusted
archive you can watch grow:**
- **Sources stay read-only.** The Dropbox export and disc images are never
  modified or deleted by the tool — they remain the untouched safety-net
  backup, full stop.
- **A new canonical archive directory** (e.g. `PhotoArchive/by-year/2024/…`)
  is what the tool actually writes to: organized by year (matching your
  "book by year" use case), with chronologically-sortable filenames, and
  containing exactly one de-duplicated copy of each unique photo.
- **This archive grows incrementally as photos get processed** — the "new
  folder, land here, I know it's safe" behavior you're after. A photo
  earns its place in `PhotoArchive/` once it's been de-duplicated and
  dated, *before* it necessarily has a person tag — person-tagging can lag
  behind (that's what the Unidentified-review workflow in §4 is for), but
  "is this a confirmed unique, dated, archived photo" happens up front, so
  the protected archive fills in steadily rather than waiting on every
  face to be named.
- **Person-based views stay virtual, not physical duplicate folders.** A
  photo with three people in it shouldn't need three physical copies —
  "Myles" or "Me + Holly + Myles" stay as database queries/saved albums
  (§6) rather than folders that would need to be kept in sync. If a
  literal browsable folder-per-person is still useful day-to-day, it can
  be done cheaply with symlinks into `PhotoArchive/by-year/` rather than
  real copies — worth deciding once the base archive exists.
- **Storage planning:** since sources stay untouched *and* the archive is
  a second full copy, budget roughly double the source library's disk
  space (~200–500GB round-tripped, depending on original file sizes).
  Worth confirming you have a drive/NAS with that headroom before the
  first big import — this is the one practical blocker worth resolving
  before writing any code.

---

## 3. Data model

```
Photo
  id, file_path, checksum (dedupe), taken_at (from EXIF, fallback to file
  date), gps_lat/lng (from EXIF, optional), width/height, imported_at

Face
  id, photo_id, bounding_box, embedding (vector), cluster_id,
  person_id (nullable — null until a cluster is named),
  confidence (match score if auto-assigned vs. human-confirmed)

Person
  id, name, cover_face_id (representative thumbnail), notes

Cluster
  id, representative_face_id, status (unreviewed / named / merged / split)

Album / Book (derived, not stored redundantly)
  A saved query + manual overrides: e.g. {person: Myles, year: 2024} plus
  a curator can drag photos in/out and set an explicit order before export.
```

Keeping `Face` separate from `Photo` (rather than a flat `photo.people[]`
list) matters because a photo can have multiple faces, a face can be
reassigned independently (fixing one mistagged face in a group photo
without touching the others), and confidence/audit info lives per-face.

---

## 4. The review/tagging workflow (the part you interact with)

1. **Import.** Point the tool at a folder (or upload in bulk). It hashes
   each file (skip exact duplicates), extracts EXIF date/GPS, and queues
   faces for detection.
2. **Detect + embed + cluster.** Runs as a background batch job — for a
   large existing library (thousands of photos) this is the slow step
   (minutes to a few hours depending on volume and hardware), but it's a
   one-time cost per import batch, not something you wait on interactively.
3. **Review screen: "Name this person."** Shows one representative face per
   cluster, largest clusters first (biggest bang-per-tag). You type a name
   or pick from existing people. Actions needed: **name**, **merge** (two
   clusters are the same person), **split** (a cluster wrongly grouped two
   people), **ignore** (not a real face / stranger in the background you
   don't want tagged).
4. **Propagation.** Naming a cluster tags every face in it — potentially
   hundreds of photos — in one action.
5. **Unidentified directory.** Clusters left unnamed (or individual
   low-confidence faces that didn't join any cluster confidently) sit in a
   persistent "Unidentified" view, sorted by frequency, so recurring people
   you haven't named yet (grandparents, friends) bubble up for you to
   handle whenever you get to them — this is literally the directory you
   described.
6. **Ongoing imports.** New photos auto-match against named people; anything
   below the confidence threshold goes back into Unidentified rather than
   guessing.

---

## 5. Curation → export for printing

Since Shutterfly/Mixbook/Snapfish don't offer book-building APIs, the
pipeline's output is a **curated, ordered photo set per book**, exported in
whatever form is fastest to hand off:

- A **date-ordered folder/export per book** (e.g. `Myles_2024/001.jpg,
  002.jpg, …`) — Shutterfly's own uploader accepts bulk folder uploads and
  will preserve order if filenames are numbered, which is the lowest-effort
  bridge.
- Optionally, a **simple auto-layout PDF** (e.g. via a Python layout tool)
  as a "preview book" — useful for reviewing the story/flow of the book
  before spending time in Shutterfly's own editor, even though you'd still
  rebuild it in their tool for the actual print order.
- A **curation UI step** before export: the query (`Myles, 2024`) gives you
  a candidate set, but you'll usually want to hand-trim (drop near-duplicate
  burst shots, blurry frames) and set final order — worth building this as
  a lightweight step, not assuming the auto-selected set is print-ready
  as-is.

---

## 6. Tech stack recommendation

Given these are personal/family photos, **local-first (no cloud face API)
is the right default** — both for privacy and because it avoids per-photo
cloud costs at your volume.

| Layer | Recommendation | Why |
|---|---|---|
| Face detection + embeddings | **InsightFace** or `face_recognition` (dlib-based), running locally | Mature, free, no per-image API cost, no photos leaving your machine. InsightFace is more accurate on modern benchmarks; `face_recognition` is simpler to get running fast. |
| Clustering | Chinese-whispers or HDBSCAN over embeddings (both available via existing Python libraries) | Standard approach paired with face embeddings; HDBSCAN handles "unknown number of people" well, which matches your use case. |
| Metadata extraction | `exiftool` / Python `Pillow`+`exifread` | Pulls date/GPS reliably, including from old camera/phone exports. |
| Database | PostgreSQL (+ `pgvector` for embedding similarity search) | One database for structured metadata *and* fast nearest-neighbor face matching — avoids running a separate vector DB. SQLite is a fine starting point if you want zero setup first, with a later migration path to Postgres if the library grows large. |
| Backend | Python (FastAPI) | Face-recognition ecosystem (InsightFace, dlib, face_recognition, HDBSCAN) is overwhelmingly Python-first; keeping the backend in Python avoids a cross-language bridge. |
| Review/tagging UI | Simple web app (FastAPI + a lightweight frontend — even server-rendered HTML/HTMX is enough for a personal tool) | The UI surface is small: a cluster-naming grid, a per-person/year gallery, and a book-curation drag-reorder view. Doesn't need a heavy SPA framework. |
| Storage | Original files stay on disk (local NAS/external drive recommended given photo volume); DB stores paths + thumbnails, not the originals | Keeps you in control of the source files and avoids duplicating multi-GB libraries into a database. |
| Export | Script that copies/renames the curated set into a numbered folder per book; optional PDF preview via `reportlab` or similar | Matches the "no book API" reality in §5. |
| Dedup | SHA-256 for exact matches, `imagehash` (pHash) for near-duplicate detection | Exact matches auto-collapse safely; near-duplicates only ever get flagged for review — see §2. |

---

## 7. Suggested build order

1. **Phase 0 — Ingestion.** Dropbox pull + disc import, checksum de-dupe,
   near-duplicate flagging, EXIF date/GPS extraction, thumbnail generation,
   and writing confirmed-unique photos into the growing `PhotoArchive/`
   directory (§2). Gets your whole ~50,000-photo library into one place,
   de-duplicated, dated, and browsable, even before any face work runs.
2. **Phase 1 — Detect + cluster + name.** Face detection/embedding
   pipeline, clustering, and the cluster-naming review screen (including
   merge/split/ignore). This is the core "sort, then I tell you who people
   are" loop — the most valuable phase, worth getting right before
   anything else.
3. **Phase 2 — Unidentified directory + ongoing auto-tag.** Persistent
   review queue for unnamed/low-confidence clusters; new imports auto-match
   against named people.
4. **Phase 3 — Query/album builder.** "By person," "by person + year,"
   "by multiple people present," saved as reusable album definitions.
5. **Phase 4 — Book curation + export.** Drag-reorder, drop/keep decisions,
   numbered-folder export (and optional PDF preview).

Phase 0–1 alone gets you a searchable, self-tagging photo archive; Phases
3–4 are what turn that into actual printable books.

---

## 8. Open questions worth deciding before building

- ~~Where do the photos live?~~ **Answered: Dropbox (~50,000 photos),
  plus discs still to be imported.**
- ~~Approximate library size?~~ **Answered: ~50,000 and growing** — this
  puts us past the point where SQLite is the comfortable choice; plan on
  PostgreSQL + `pgvector` from the start (§6).
- ~~Is the Dropbox library already synced locally via the desktop app, or
  Dropbox-only?~~ **Answered: Dropbox is synced locally on this machine** —
  Phase 0 ingestion reads the local synced folder directly; no Dropbox API
  integration needed.
- **What format are the discs** (CD/DVD data discs with image files, or
  something like old Shutterfly/Kodak CD-with-viewer-software discs)? Plain
  image files just get pointed at like any other source folder; a
  proprietary viewer format may need a manual export step first.
- ~~Do you have a drive/NAS with room for a second full copy of the
  library?~~ **Answered: a 2TB external hard drive is available** — well
  above the ~200–500GB estimate, with plenty of headroom as the disc
  imports get added too.
- **Hardware available for the face-detection pass?** CPU-friendly but
  faster with a GPU — matters for how long the first full 50,000-photo
  pass takes (plausibly hours on CPU), not for feasibility.
- **How many distinct people do you expect to tag** (immediate family only,
  or also grandparents/friends/extended family)? Affects how much the
  Unidentified-directory workflow gets used in practice.

## Next steps

The two blockers worth resolving before writing code are (1) whether
Dropbox is locally synced or needs API-based bulk download, and (2)
confirming you have enough storage for a second, de-duplicated copy of the
library. Once those are settled, Phase 0 (Dropbox/disc ingestion, exact +
near-duplicate detection, EXIF extraction, and the growing `PhotoArchive/`
directory) is the right first thing to actually build and run against a
real subset of your library — it's the part worth validating first, since
everything else (tagging, querying, book export) depends on having a
clean, de-duplicated, dated archive underneath it.
