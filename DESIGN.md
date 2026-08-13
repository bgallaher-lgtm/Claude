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
  (see §3), not try to eliminate it.
- **Look-alike relatives / siblings** reduce match confidence — the
  threshold tuning in §2 trades off "auto-tag more, correct more" vs.
  "auto-tag conservatively, review more."
- **Old scanned/low-res photos** detect and embed faces less reliably;
  expect a higher fraction of those to land in manual review.

---

## 2. Data model

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

## 3. The review/tagging workflow (the part you interact with)

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

## 4. Curation → export for printing

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

## 5. Tech stack recommendation

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
| Export | Script that copies/renames the curated set into a numbered folder per book; optional PDF preview via `reportlab` or similar | Matches the "no book API" reality in §4. |

---

## 6. Suggested build order

1. **Phase 0 — Ingestion.** Folder/bulk import, checksum de-dupe, EXIF date/
   GPS extraction, thumbnail generation. Gets your whole library into the
   system and browsable by date even before any face work runs.
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

## 7. Open questions worth deciding before building

- **Where do the photos live?** Local drive/NAS vs. cloud storage (e.g. an
  existing Google Photos/iCloud library) changes the ingestion design
  significantly — pulling from an existing cloud library needs that
  service's export/API instead of a folder importer.
- **Approximate library size?** Hundreds vs. tens of thousands of photos
  changes whether SQLite is fine to start or Postgres+pgvector should be
  the first choice, and how long the initial detect/cluster batch job
  takes.
- **Hardware available?** Face embedding is CPU-friendly but faster with a
  GPU; matters mainly for how long the first full-library pass takes, not
  for feasibility.
- **How many distinct people do you expect to tag** (immediate family only,
  or also grandparents/friends/extended family)? Affects how much the
  Unidentified-directory workflow gets used in practice.

## Next steps

Tell me your rough photo count and where the library currently lives
(local folders, external drive, Google Photos/iCloud export, etc.), and
I'll turn Phase 0 (ingestion + EXIF) and Phase 1 (detect/cluster/name) into
an actual runnable prototype — that's the part worth validating first,
since it's the core of the "sort, then tell you who's who" workflow you
described.
