"""Generate the Gallaher Computers logo set (sign-lettering design).

Usage: python3 logo/make_logo.py
Needs: pip install fonttools; Node Playwright (pre-installed Chromium) for PNGs.
Text is converted to outlines, so the SVGs need no fonts installed.
"""
import os, math, subprocess, json
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

OUT = os.path.dirname(os.path.abspath(__file__))
FD = "/usr/share/fonts/opentype/inter"
BLACK, DK, GR, WH = "#111111", "#0E6B2A", "#4CB848", "#FFFFFF"
HEAVY, TAGF = "InterDisplay-Black.otf", "Inter-ExtraBold.otf"
SKEW = 12  # degrees of forward slant

_f = {}
def F(n):
    if n not in _f: _f[n] = TTFont(os.path.join(FD, n))
    f = _f[n]; return f.getGlyphSet(), f.getBestCmap(), f["head"].unitsPerEm

def adv(ch, fn, size):
    gs, cm, upm = F(fn); return gs[cm[ord(ch)]].width * size / upm

def width(t, fn, size, tr=0):
    return sum(adv(c, fn, size) for c in t) + tr * size * (len(t) - 1)

def text(t, fn, size, x, y, tr=0, skew=0):
    gs, cm, upm = F(fn); s = size / upm; k = math.tan(math.radians(skew))
    pen = SVGPathPen(gs); cx = x
    for ch in t:
        gs[cm[ord(ch)]].draw(TransformPen(pen, (s, 0, k * s, -s, cx, y)))
        cx += adv(ch, fn, size) + tr * size
    return pen.getCommands()

def layered(d):
    """Sign-style lettering: black outline, green outline, thin white line, black fill."""
    return (f'<path d="{d}" fill="{BLACK}" stroke="{BLACK}" stroke-width="40" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="{GR}" stroke="{GR}" stroke-width="24" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="{WH}" stroke="{WH}" stroke-width="9" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="{BLACK}"/>')

def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}">'
            f'<title>Gallaher Computers</title>{body}</svg>\n')

def full_logo(dark=False, tagline=True):
    size = 190; x0, y0 = 40, 190
    W = width("GALLAHER", HEAVY, size, -0.01)
    body = layered(text("GALLAHER", HEAVY, size, x0, y0, -0.01, SKEW))
    by, bh = 240, 92; bx0, bx1 = x0 + 30, x0 + W - 20
    sl = bh * math.tan(math.radians(10))
    body += (f'<path d="M {bx0+sl} {by} L {bx1+sl} {by} L {bx1} {by+bh} L {bx0} {by+bh} Z" '
             f'fill="{DK}" stroke="{BLACK}" stroke-width="8" stroke-linejoin="round"/>')
    cs = 66; cw = width("COMPUTERS", HEAVY, cs, 0.12)
    body += f'<path d="{text("COMPUTERS", HEAVY, cs, (bx0+bx1+sl)/2 - cw/2, by+bh/2 + cs*0.36, 0.12, SKEW)}" fill="{WH}"/>'
    h = by + bh + 24
    if tagline:
        ts = 30; t = "ELECTRONICS RECYCLING"; tw = width(t, TAGF, ts, 0.16)
        tx = (bx0 + bx1) / 2 - tw / 2; ty = by + bh + 56
        body += (f'<path d="{text(t, TAGF, ts, tx, ty, 0.16)}" fill="{WH if dark else BLACK}"/>'
                 f'<rect x="{bx0}" y="{ty-14}" width="{tx-bx0-24}" height="6" fill="{GR}"/>'
                 f'<rect x="{tx+tw+24}" y="{ty-14}" width="{bx1-tx-tw-24}" height="6" fill="{GR}"/>')
        h = ty + 30
    return svg(x0 * 2 + W + 30, h, body)

def icon(badge=True):
    """Single 'G' in the same lettering; badge=True puts it on a round green-ringed disc."""
    S = 400; size = 300 if not badge else 236
    w = adv("G", HEAVY, size); cap = 0.727 * size
    k = math.tan(math.radians(SKEW))
    x = S / 2 - w / 2 - k * cap / 2; y = S / 2 + cap / 2
    g = layered(text("G", HEAVY, size, x, y, 0, SKEW))
    if not badge:
        return svg(S, S, g)
    disc = (f'<circle cx="200" cy="200" r="196" fill="{BLACK}"/>'
            f'<circle cx="200" cy="200" r="186" fill="{DK}"/>'
            f'<circle cx="200" cy="200" r="168" fill="{WH}"/>')
    return svg(S, S, disc + g)

files = {
    "gallaher-logo": full_logo(),
    "gallaher-logo-dark-bg": full_logo(dark=True),
    "gallaher-logo-compact": full_logo(tagline=False),
    "gallaher-icon-badge": icon(True),
    "gallaher-icon-g": icon(False),
}
for n, s in files.items(): open(os.path.join(OUT, n + ".svg"), "w").write(s)

js = r"""
const { chromium } = require('playwright'); const fs=require('fs'), path=require('path');
(async () => { const dir=process.argv[2], names=JSON.parse(process.argv[3]); const b=await chromium.launch();
 for (const n of names) { const s=fs.readFileSync(path.join(dir,n+'.svg'),'utf8');
  const [w,h]=s.match(/viewBox="0 0 ([\d.]+) ([\d.]+)"/).slice(1).map(Number);
  const p=await b.newPage({viewport:{width:w,height:h},deviceScaleFactor:4});
  await p.setContent(`<html><body style="margin:0;background:transparent">${s}</body></html>`);
  await p.locator('svg').screenshot({path:path.join(dir,n+'.png'),omitBackground:true}); await p.close(); }
 await b.close(); })();
"""
jf = os.path.join(OUT, ".r.js"); open(jf, "w").write(js)
subprocess.run(["node", jf, OUT, json.dumps(list(files))], check=True); os.remove(jf)
print("wrote", ", ".join(files))
