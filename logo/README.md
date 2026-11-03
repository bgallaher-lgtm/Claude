# Gallaher Computers logo

| File | Use |
|---|---|
| `gallaher-logo-horizontal.svg/.png` | Main logo — website header, invoices, letterhead, email signature |
| `gallaher-logo-stacked.svg/.png` | Square-ish spaces — social posts, signs, flyers |
| `gallaher-icon.svg/.png` | Icon only — Facebook/Google profile picture, favicon, stickers |
| `*-white.*` | Same designs for dark backgrounds (shirts, dark photos, black vinyl) |

- **SVG** files are vector: scale to any size (send these to sign/print shops).
- **PNG** files have transparent backgrounds, rendered at 4× resolution.

**Colors**
- Dark green `#0E6B2A`
- Bright green `#4CB848`
- Black `#111111`
- Gray (tagline) `#4A4A4A`

**Font:** Inter Display Black / Inter Bold (text is already converted to outlines in the SVGs).

To change anything (colors, tagline), edit `make_logo.py` and run `python3 logo/make_logo.py`
(needs `pip install fonttools` and Node Playwright for the PNGs).
