"""Three alternative Gallaher Computers logo concepts (A: sign lettering, B: round emblem, C: monitor + leaf)."""
import os, math, subprocess, json
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

OUT = os.path.dirname(os.path.abspath(__file__))
FD = "/usr/share/fonts/opentype/inter"
BLACK, DK, GR, GRAY, WH = "#111111", "#0E6B2A", "#4CB848", "#4A4A4A", "#FFFFFF"
_f = {}
def F(n):
    if n not in _f: _f[n] = TTFont(os.path.join(FD, n))
    f = _f[n]; return f, f.getGlyphSet(), f.getBestCmap(), f["head"].unitsPerEm

def adv(ch, fn, size):
    f, gs, cm, upm = F(fn); return gs[cm[ord(ch)]].width * size / upm

def width(t, fn, size, tr=0):
    return sum(adv(c, fn, size) for c in t) + tr * size * (len(t) - 1)

def glyph(ch, fn, size, m):
    """m = affine (a,b,c,d,e,f) applied to glyph in font units scaled to size (y up)."""
    f, gs, cm, upm = F(fn); s = size / upm
    a, b, c, d, e, ff = m
    pen = SVGPathPen(gs)
    gs[cm[ord(ch)]].draw(TransformPen(pen, (a*s, b*s, -c*s, -d*s, e, ff)))
    return pen.getCommands()

def text(t, fn, size, x, y, tr=0, skew=0):
    out, cx = [], x
    for ch in t:
        k = math.tan(math.radians(skew))
        out.append(glyph(ch, fn, size, (1, 0, -k, 1, cx, y)))
        cx += adv(ch, fn, size) + tr * size
    return " ".join(out)

def arc_text(t, fn, size, cx, cy, r, center_deg, tr=0, bottom=False):
    """Text centered on angle center_deg (0 = top, clockwise). Bottom text reads left-to-right."""
    W = width(t, fn, size, tr); span = W / r
    out = []
    if not bottom:
        a = math.radians(center_deg) - span / 2
        for ch in t:
            w = adv(ch, fn, size); th = a + (w / 2) / r
            ux, uy = math.sin(th), -math.cos(th)          # outward unit
            px, py = cx + r * ux, cy + r * uy               # baseline point
            tx, ty = math.cos(th), math.sin(th)             # tangent
            # glyph x along tangent, glyph up along outward
            ox, oy = px - tx * w / 2, py - ty * w / 2
            out.append(glyph(ch, fn, size, (tx, ty, -ux, -uy, ox, oy)))
            a += (w + tr * size) / r
    else:
        a = math.radians(center_deg) + span / 2
        for ch in t:
            w = adv(ch, fn, size); th = a - (w / 2) / r
            ux, uy = math.sin(th), -math.cos(th)
            px, py = cx + r * ux, cy + r * uy
            tx, ty = -math.cos(th), -math.sin(th)            # tangent pointing left-to-right at bottom
            ox, oy = px - tx * w / 2, py - ty * w / 2
            # glyph up = inward (toward center)
            out.append(glyph(ch, fn, size, (tx, ty, ux, uy, ox, oy)))
            a -= (w + tr * size) / r
    return " ".join(out)

def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" width="{w:.0f}" height="{h:.0f}">'
            f'<title>Gallaher Computers</title>{body}</svg>\n')

# ---------- A: sign-style lettering (echoes the magnet) ----------
def concept_a():
    fn = "InterDisplay-Black.otf"; size = 190; sk = 12
    W = width("GALLAHER", fn, size, -0.01)
    x0, y0 = 40, 190
    d = text("GALLAHER", fn, size, x0, y0, -0.01, sk)
    layers = (f'<path d="{d}" fill="{BLACK}" stroke="{BLACK}" stroke-width="40" stroke-linejoin="round"/>'
              f'<path d="{d}" fill="{GR}" stroke="{GR}" stroke-width="24" stroke-linejoin="round"/>'
              f'<path d="{d}" fill="{WH}" stroke="{WH}" stroke-width="9" stroke-linejoin="round"/>'
              f'<path d="{d}" fill="{BLACK}"/>')
    # green slanted banner with COMPUTERS
    by, bh = 240, 92; bx0, bx1 = x0 + 30, x0 + W - 20; sl = bh * math.tan(math.radians(10))
    banner = (f'<path d="M {bx0+sl} {by} L {bx1+sl} {by} L {bx1} {by+bh} L {bx0} {by+bh} Z" fill="{DK}" stroke="{BLACK}" stroke-width="8" stroke-linejoin="round"/>')
    cs = 66; cw = width("COMPUTERS", fn, cs, 0.12)
    comp = text("COMPUTERS", fn, cs, (bx0 + bx1 + sl) / 2 - cw / 2, by + bh / 2 + cs * 0.36, 0.12, sk)
    ts = 30; t = "ELECTRONICS RECYCLING"; tw = width(t, "Inter-ExtraBold.otf", ts, 0.16)
    tx = (bx0 + bx1 + sl) / 2 - tw / 2 - sl / 2; ty = by + bh + 56
    tag = text(t, "Inter-ExtraBold.otf", ts, tx, ty, 0.16)
    lines = (f'<rect x="{bx0}" y="{ty-14}" width="{tx-bx0-24}" height="6" fill="{GR}"/>'
             f'<rect x="{tx+tw+24}" y="{ty-14}" width="{bx1-tx-tw-24}" height="6" fill="{GR}"/>')
    body = layers + banner + f'<path d="{comp}" fill="{WH}"/>' + f'<path d="{tag}" fill="{BLACK}"/>' + lines
    return svg(x0 * 2 + W + 30, ty + 30, body)

# ---------- B: round emblem ----------
def leaf(x, y, s, fill, vein, rot=-35, node=True):
    v = (f'<path d="M 50 92 L 50 30" stroke="{vein}" stroke-width="7" stroke-linecap="round" fill="none"/>'
         f'<path d="M 50 62 L 66 46" stroke="{vein}" stroke-width="6" stroke-linecap="round" fill="none"/>'
         + (f'<circle cx="68" cy="44" r="7" fill="{vein}"/><circle cx="50" cy="28" r="7" fill="{vein}"/>' if node else ''))
    return (f'<g transform="translate({x},{y}) scale({s/100}) rotate({rot} 50 50)">'
            f'<path d="M 50 2 C 88 24 92 70 50 98 C 8 70 12 24 50 2 Z" fill="{fill}"/>{v}</g>')

def monitor(x, y, s, frame, screen, leaf_fill, vein):
    return (f'<g transform="translate({x},{y}) scale({s/200})">'
            f'<rect x="10" y="10" width="180" height="124" rx="16" fill="{screen}" stroke="{frame}" stroke-width="16"/>'
            f'<path d="M 82 142 L 76 170 L 124 170 L 118 142 Z" fill="{frame}"/>'
            f'<rect x="56" y="166" width="88" height="14" rx="7" fill="{frame}"/>'
            + leaf(52, 24, 94, leaf_fill, vein) + '</g>')

def concept_b():
    S = 640; c = S / 2
    body = (f'<circle cx="{c}" cy="{c}" r="310" fill="{DK}"/>'
            f'<circle cx="{c}" cy="{c}" r="292" fill="none" stroke="{WH}" stroke-width="6"/>'
            f'<circle cx="{c}" cy="{c}" r="198" fill="{WH}"/>'
            f'<circle cx="{c}" cy="{c}" r="198" fill="none" stroke="{GR}" stroke-width="12"/>')
    top = arc_text("GALLAHER COMPUTERS", "InterDisplay-Black.otf", 48, c, c, 228, 0, 0.05)
    bot = arc_text("ELECTRONICS RECYCLING", "Inter-ExtraBold.otf", 34, c, c, 260, 180, 0.12, bottom=True)
    body += f'<path d="{top}" fill="{WH}"/><path d="{bot}" fill="{WH}"/>'
    for ang in (-90, 90):
        x = c + 248 * math.cos(math.radians(ang + 90 - 90)) if False else c + (248 if ang == 90 else -248)
        body += f'<circle cx="{x}" cy="{c}" r="10" fill="{GR}"/>'
    body += monitor(c - 125, c - 140, 250, DK, WH, GR, DK)
    ms = 26; mt = "MT. STERLING, IL"; mw = width(mt, "Inter-Bold.otf", ms, 0.1)
    body += f'<path d="{text(mt, "Inter-Bold.otf", ms, c - mw/2, c + 130, 0.1)}" fill="{GRAY}"/>'
    return svg(S, S, body)

# ---------- C: monitor + leaf, clean wordmark ----------
def concept_c():
    ic = 250
    body = monitor(20, 25, ic, DK, WH, GR, DK)
    fx = 20 + ic + 40
    d1 = text("Gallaher", "InterDisplay-ExtraBold.otf", 150, fx, 150, -0.02)
    W = width("Gallaher", "InterDisplay-ExtraBold.otf", 150, -0.02)
    cs = 56; ctr = (W - width("COMPUTERS", "InterDisplay-Bold.otf", cs)) / 8 / cs
    d2 = text("COMPUTERS", "InterDisplay-Bold.otf", cs, fx + 4, 222, ctr)
    ts = 25; t = "ELECTRONICS RECYCLING"; ttr = (W - width(t, "Inter-SemiBold.otf", ts)) / (len(t) - 1) / ts
    d3 = text(t, "Inter-SemiBold.otf", ts, fx + 4, 268, ttr)
    body += (f'<path d="{d1}" fill="{DK}"/><path d="{d2}" fill="{GR}"/>'
             f'<rect x="{fx+4}" y="236" width="{W}" height="4" fill="{GR}" opacity=".5"/>'
             f'<path d="{d3}" fill="{GRAY}"/>')
    return svg(fx + W + 30, 300, body)

files = {"concept-a-sign": concept_a(), "concept-b-emblem": concept_b(), "concept-c-monitor": concept_c()}
for n, s in files.items(): open(os.path.join(OUT, n + ".svg"), "w").write(s)
js = r"""
const { chromium } = require('playwright'); const fs=require('fs'), path=require('path');
(async () => { const dir=process.argv[2], names=JSON.parse(process.argv[3]); const b=await chromium.launch();
 for (const n of names) { const s=fs.readFileSync(path.join(dir,n+'.svg'),'utf8');
  const [w,h]=s.match(/viewBox="0 0 ([\d.]+) ([\d.]+)"/).slice(1).map(Number);
  const p=await b.newPage({viewport:{width:w,height:h},deviceScaleFactor:3});
  await p.setContent(`<html><body style="margin:0;background:transparent">${s}</body></html>`);
  await p.locator('svg').screenshot({path:path.join(dir,n+'.png'),omitBackground:true}); await p.close(); }
 await b.close(); })();
"""
jf = os.path.join(OUT, ".r.js"); open(jf, "w").write(js)
subprocess.run(["node", jf, OUT, json.dumps(list(files))], check=True); os.remove(jf)
print("ok")
