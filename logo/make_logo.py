"""Generate Gallaher Computers logo files (SVG + transparent PNG).

Usage: python3 logo/make_logo.py
Text is converted to vector outlines, so the SVGs need no fonts installed.
"""
import os, subprocess, json
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

OUT = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = "/usr/share/fonts/opentype/inter"
BLACK, DKGREEN, GREEN, GRAY, WHITE = "#111111", "#0E6B2A", "#4CB848", "#4A4A4A", "#FFFFFF"

_fonts = {}
def font(name):
    if name not in _fonts:
        _fonts[name] = TTFont(os.path.join(FONT_DIR, name))
    return _fonts[name]

def text_path(txt, fname, size, x, y, tracking=0.0):
    """Return (svg path d, advance width) for txt with baseline at y."""
    f = font(fname); gs = f.getGlyphSet(); cmap = f.getBestCmap()
    upm = f["head"].unitsPerEm; s = size / upm
    pen = SVGPathPen(gs); cx = 0.0
    for i, ch in enumerate(txt):
        g = cmap[ord(ch)]
        tp = TransformPen(pen, (s, 0, 0, -s, x + cx, y))
        gs[g].draw(tp)
        cx += gs[g].width * s + (tracking * size if i < len(txt) - 1 else 0)
    return pen.getCommands(), cx

def width(txt, fname, size, tracking=0.0):
    return text_path(txt, fname, size, 0, 0, tracking)[1]

def icon(x, y, s, reverse=False):
    """'G' monogram built from a recycling arrow + circuit trace, in a 200x200 box."""
    badge = WHITE if reverse else DKGREEN
    ring = DKGREEN if reverse else WHITE
    return f'''<g transform="translate({x},{y}) scale({s/200})">
  <rect x="0" y="0" width="200" height="200" rx="44" fill="{badge}"/>
  <!-- arc of the G: from upper-right, round the left, back to the right -->
  <path d="M 125.36 45.62 A 60 60 0 1 0 160 100" fill="none" stroke="{ring}" stroke-width="24" stroke-linecap="butt"/>
  <!-- arrowhead on the open end (recycling motion) -->
  <path d="M 112.7 72.8 L 138.1 18.4 L 167.1 65.1 Z" fill="{ring}" stroke="{ring}" stroke-width="4" stroke-linejoin="round"/>
  <!-- crossbar as a circuit trace ending in a node -->
  <rect x="104" y="88" width="68" height="24" fill="{GREEN}"/>
  <circle cx="100" cy="100" r="19" fill="{GREEN}"/>
  <circle cx="100" cy="100" r="8" fill="{badge}"/>
</g>'''

def wordmark(x, y, reverse=False, align="left", w_total=None):
    main = WHITE if reverse else BLACK
    sub = GREEN if reverse else DKGREEN
    tag = "#D9D9D9" if reverse else GRAY
    big = ("GALLAHER", "InterDisplay-Black.otf", 120, -0.02)
    W = width(*big)
    # size COMPUTERS and the tagline to the same width as GALLAHER
    c_size = 74; c_track = (W - width("COMPUTERS", "InterDisplay-Black.otf", c_size)) / 8 / c_size
    t_txt = "ELECTRONICS RECYCLING"
    t_size = 30; t_track = (W - width(t_txt, "Inter-Bold.otf", t_size)) / (len(t_txt) - 1) / t_size
    ox = x if align == "left" else x - W / 2
    d1, _ = text_path(*big[:3], ox, y + 88, big[3])
    d2, _ = text_path("COMPUTERS", "InterDisplay-Black.otf", c_size, ox, y + 184, c_track)
    d3, _ = text_path(t_txt, "Inter-Bold.otf", t_size, ox, y + 234, t_track)
    rule = f'<rect x="{ox}" y="{y+108}" width="{W}" height="7" fill="{GREEN}"/>'
    return f'<path d="{d1}" fill="{main}"/>{rule}<path d="{d2}" fill="{sub}"/><path d="{d3}" fill="{tag}"/>', W

def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" '
            f'width="{w:.0f}" height="{h:.0f}">\n<title>Gallaher Computers</title>\n{body}\n</svg>\n')

files = {}
for rev in (False, True):
    sfx = "-white" if rev else ""
    # horizontal: icon left, wordmark right
    wm, W = wordmark(0, 0, rev)
    pad = 20; ic = 236
    body = icon(pad, pad + 2, ic, rev) + f'<g transform="translate({pad+ic+36},{pad})">{wm}</g>'
    files[f"gallaher-logo-horizontal{sfx}"] = svg(pad*2 + ic + 36 + W, pad*2 + 240, body)
    # stacked: icon on top, centered wordmark
    wm, W = wordmark(0, 0, rev)
    cw = W + 40; ic = 200
    body = icon((cw - ic) / 2, 20, ic, rev) + f'<g transform="translate(20,{20+ic+36})">{wm}</g>'
    files[f"gallaher-logo-stacked{sfx}"] = svg(cw, 20 + ic + 36 + 240 + 20, body)
    # icon only
    files[f"gallaher-icon{sfx}"] = svg(200, 200, icon(0, 0, 200, rev))

for name, s in files.items():
    open(os.path.join(OUT, name + ".svg"), "w").write(s)

# Render transparent PNGs with the pre-installed Chromium via Playwright (Node).
js = r"""
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
(async () => {
  const [dir, names, scale] = [process.argv[2], JSON.parse(process.argv[3]), 4];
  const b = await chromium.launch(); 
  for (const n of names) {
    const s = fs.readFileSync(path.join(dir, n + '.svg'), 'utf8');
    const [w, h] = s.match(/viewBox="0 0 ([\d.]+) ([\d.]+)"/).slice(1).map(Number);
    const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: scale });
    await p.setContent(`<html><body style="margin:0;background:transparent">${s}</body></html>`);
    await p.locator('svg').screenshot({ path: path.join(dir, n + '.png'), omitBackground: true });
    await p.close();
  }
  await b.close();
})();
"""
jsf = os.path.join(OUT, ".render.js"); open(jsf, "w").write(js)
subprocess.run(["node", jsf, OUT, json.dumps(list(files))], check=True)
os.remove(jsf)
print("wrote", len(files), "SVG + PNG pairs to", OUT)
