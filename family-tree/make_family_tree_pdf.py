"""Generate a printable, fill-in-by-hand family tree research workbook (PDF)."""
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

INK = HexColor("#2b2b2b")
SOFT = HexColor("#6b6b6b")
RULE = HexColor("#a8a8a8")
ACCENT = HexColor("#5a3e2b")
TINT = HexColor("#f4efe8")

OUT = "family_tree_research_workbook.pdf"


def label_line(c, x, y, w, label, size=7.5, gap=3):
    """Small label followed by a writing line to x+w."""
    c.setFont("Helvetica", size)
    c.setFillColor(SOFT)
    c.drawString(x, y, label)
    lw = c.stringWidth(label, "Helvetica", size)
    c.setStrokeColor(RULE)
    c.setLineWidth(0.5)
    c.line(x + lw + gap, y - 1.5, x + w, y - 1.5)


def page_title(c, title, subtitle, pw, ph, top=0.45 * inch):
    c.setFillColor(ACCENT)
    c.setFont("Times-Bold", 20)
    c.drawString(0.5 * inch, ph - top - 14, title)
    c.setFillColor(SOFT)
    c.setFont("Helvetica", 8.5)
    c.drawString(0.5 * inch, ph - top - 28, subtitle)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1)
    c.line(0.5 * inch, ph - top - 34, pw - 0.5 * inch, ph - top - 34)


def footer(c, pw, text):
    c.setFont("Helvetica", 7)
    c.setFillColor(SOFT)
    c.drawRightString(pw - 0.5 * inch, 0.3 * inch, text)


# --------------------------------------------------------------------------
# Page 1: cover + how to use
# --------------------------------------------------------------------------
def cover(c):
    pw, ph = letter
    c.setFillColor(ACCENT)
    c.setFont("Times-Bold", 34)
    c.drawCentredString(pw / 2, ph - 2.0 * inch, "Family Tree")
    c.setFont("Times-Roman", 18)
    c.drawCentredString(pw / 2, ph - 2.45 * inch, "Research Workbook")
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1)
    c.line(pw / 2 - 1.5 * inch, ph - 2.7 * inch, pw / 2 + 1.5 * inch, ph - 2.7 * inch)

    x, w = 1.5 * inch, pw - 3 * inch
    y = ph - 3.4 * inch
    for lab in ("The family of", "Compiled by", "Started on"):
        c.setFont("Helvetica", 10)
        c.setFillColor(SOFT)
        c.drawString(x, y, lab)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.6)
        c.line(x + 1.2 * inch, y - 2, x + w, y - 2)
        y -= 0.45 * inch

    y -= 0.3 * inch
    c.setFillColor(ACCENT)
    c.setFont("Times-Bold", 14)
    c.drawString(x, y, "What's inside")
    y -= 0.3 * inch
    items = [
        ("Pedigree Chart", "Four generations of direct ancestors on one page, with birth, "
                           "marriage and death dates and places. Print one per branch."),
        ("Family Group Sheet", "One couple and all of their children. Print one for every "
                               "couple on your pedigree chart."),
        ("Research Log", "Track where you've looked and what you found, so you never "
                         "search the same record twice."),
    ]
    for head, body in items:
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(INK)
        c.drawString(x, y, head)
        c.setFont("Helvetica", 9.5)
        c.setFillColor(SOFT)
        for i, ln in enumerate(simpleSplit(body, "Helvetica", 9.5, w - 1.5 * inch)):
            c.drawString(x + 1.5 * inch, y - i * 13, ln)
        y -= 13 * i
        y -= 22

    y -= 0.15 * inch
    c.setFillColor(ACCENT)
    c.setFont("Times-Bold", 14)
    c.drawString(x, y, "Tips for recording")
    y -= 0.28 * inch
    tips = [
        "Write dates as day, month, year: 12 Mar 1890. It avoids 3/12 vs 12/3 confusion.",
        "Use maiden names for women (the surname they were born with).",
        "Write places from smallest to largest: town, county, state, country.",
        "Mark estimates clearly: abt. 1850, bef. 1900, aft. 1875, or a range 1850-1855.",
        "Write SURNAMES IN CAPITALS so they stand out: Mary Ellen O'BRIEN.",
        "Use pencil for anything you haven't confirmed with a record.",
        "Numbering: you are #1. Your father is 2x your number, your mother 2x + 1.",
        "    So #2's parents are #4 and #5; #7's parents are #14 and #15.",
        "Chart #2+ : each #8-#15 on chart 1 becomes #1 on a new chart.",
    ]
    c.setFont("Helvetica", 9.5)
    c.setFillColor(INK)
    for t in tips:
        if t.startswith("    "):
            c.drawString(x + 11, y, t.strip())
        else:
            c.drawString(x, y, "\u2022  " + t)
        y -= 15
    footer(c, pw, "Family Tree Research Workbook")
    c.showPage()


# --------------------------------------------------------------------------
# Page 2: four-generation pedigree chart (landscape)
# --------------------------------------------------------------------------
def person_box(c, x, yc, w, h, num, compact=False):
    y0 = yc - h / 2
    c.setFillColor(TINT)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.8)
    c.roundRect(x, y0, w, h, 4, stroke=1, fill=1)

    pad = 5
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + pad, y0 + h - 12, str(num))
    nx = x + pad + 14
    name_end = x + w - pad
    if compact:
        # ancestors at the edge of the chart continue on another chart
        c.setFont("Helvetica", 5.5)
        c.setFillColor(SOFT)
        c.drawRightString(name_end, y0 + h - 12, "chart #____")
        name_end -= 0.5 * inch
    c.setStrokeColor(INK)
    c.setLineWidth(0.6)
    c.line(nx, y0 + h - 13, name_end, y0 + h - 13)

    size = 6.5
    if compact:
        # one row per event: date on the left, place on the right
        rows = ["B.", "M.", "D."]
        top, bottom = y0 + h - 26, y0 + 7
        step = (top - bottom) / (len(rows) - 1)
        dw = 0.95 * inch
        for i, r in enumerate(rows):
            yy = top - i * step
            label_line(c, x + pad, yy, dw, r, size=size)
            label_line(c, x + pad + dw + 4, yy, w - 2 * pad - dw - 4, "in", size=size)
    else:
        rows = ["Born", "Place", "Married", "Place", "Died", "Place"]
        top, bottom = y0 + h - 27, y0 + 7
        step = (top - bottom) / (len(rows) - 1)
        for i, r in enumerate(rows):
            label_line(c, x + pad, top - i * step, w - 2 * pad, r, size=size)


def pedigree(c):
    pw, ph = landscape(letter)
    page_title(c, "Pedigree Chart",
               "Chart #______   •   Person #1 on this chart is the same person as #______ on chart #______",
               pw, ph, top=0.35 * inch)

    widths = [2.2 * inch, 2.3 * inch, 2.4 * inch, 2.5 * inch]
    gap = 0.2 * inch
    xs = [0.5 * inch]
    for i in range(3):
        xs.append(xs[-1] + widths[i] + gap)

    top = ph - 0.95 * inch
    bottom = 0.5 * inch
    H = top - bottom
    slot = H / 8
    g4 = [top - slot * (i + 0.5) for i in range(8)]
    g3 = [(g4[2 * i] + g4[2 * i + 1]) / 2 for i in range(4)]
    g2 = [(g3[2 * i] + g3[2 * i + 1]) / 2 for i in range(2)]
    g1 = [(g2[0] + g2[1]) / 2]
    gens = [g1, g2, g3, g4]
    heights = [1.55 * inch, 1.55 * inch, 1.4 * inch, slot - 0.08 * inch]

    # connectors (draw first so boxes sit on top)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.8)
    for gi in range(3):
        for i, yc in enumerate(gens[gi]):
            xr = xs[gi] + widths[gi]
            xm = xr + gap / 2
            yf, ym = gens[gi + 1][2 * i], gens[gi + 1][2 * i + 1]
            c.line(xr, yc, xm, yc)
            c.line(xm, yf, xm, ym)
            c.line(xm, yf, xs[gi + 1], yf)
            c.line(xm, ym, xs[gi + 1], ym)

    num = 1
    for gi, centers in enumerate(gens):
        for i, yc in enumerate(centers):
            person_box(c, xs[gi], yc, widths[gi], heights[gi], num, compact=(gi == 3))
            num += 1

    # Spouse of #1 note, under the #1 box
    sx, sy = xs[0], g1[0] - heights[0] / 2 - 0.35 * inch
    label_line(c, sx, sy, widths[0], "Spouse of #1", size=7)
    label_line(c, sx, sy - 0.3 * inch, widths[0], "Prepared by", size=7)
    label_line(c, sx, sy - 0.6 * inch, widths[0], "Date", size=7)

    c.setFont("Helvetica-Oblique", 6.5)
    c.setFillColor(SOFT)
    c.drawString(xs[0], g1[0] + heights[0] / 2 + 0.25 * inch, "Even numbers = fathers,  odd = mothers")
    c.drawString(xs[0], g1[0] + heights[0] / 2 + 0.12 * inch, "Father of #n is 2n,  mother is 2n + 1")
    footer(c, pw, "Family Tree Research Workbook  •  Pedigree Chart")
    c.showPage()


# --------------------------------------------------------------------------
# Page 3: family group sheet
# --------------------------------------------------------------------------
def parent_block(c, x, y, w, role):
    c.setFillColor(TINT)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.8)
    h = 1.68 * inch
    c.roundRect(x, y - h, w, h, 4, stroke=1, fill=1)
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + 6, y - 13, role.upper())
    label_line(c, x + 70, y - 13, w - 76, "Full name", size=7.5)
    half = (w - 18) / 2
    rows = [
        (("Born", "Place"),),
        (("Christened", "Place"),),
        (("Died", "Place"),),
        (("Buried", "Place"),),
        (("Father", "Mother"),),
        (("Occupation", "Religion"),),
    ]
    yy = y - 32
    for (a, b), in rows:
        label_line(c, x + 6, yy, half * 0.8, a, size=7.5)
        label_line(c, x + 12 + half * 0.8, yy, w - 18 - half * 0.8, b, size=7.5)
        yy -= 15.5
    return y - h


def family_group(c):
    pw, ph = letter
    page_title(c, "Family Group Sheet",
               "Sheet #______   •   Pedigree chart #______, person #______",
               pw, ph, top=0.35 * inch)
    x = 0.5 * inch
    w = pw - 1 * inch
    y = ph - 0.95 * inch
    y = parent_block(c, x, y, w, "Husband") - 0.12 * inch
    y = parent_block(c, x, y, w, "Wife") - 0.2 * inch

    label_line(c, x, y, w * 0.32, "Marriage date", size=8)
    label_line(c, x + w * 0.35, y, w * 0.65, "Place", size=8)
    y -= 0.32 * inch

    # Children table
    c.setFillColor(ACCENT)
    c.setFont("Times-Bold", 13)
    c.drawString(x, y, "Children")
    y -= 0.12 * inch
    cols = [("#", 0.3), ("Sex", 0.4), ("Name", 2.0), ("Born (date & place)", 1.85),
            ("Died (date & place)", 1.55), ("Spouse & marriage date", 1.4)]
    total = sum(cw for _, cw in cols)
    scale = w / (total * inch)
    hdr_h = 0.25 * inch
    c.setFillColor(ACCENT)
    c.rect(x, y - hdr_h, w, hdr_h, stroke=0, fill=1)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 7.5)
    cx = x
    edges = [x]
    for name, cw in cols:
        cwp = cw * inch * scale
        c.drawString(cx + 4, y - hdr_h + 6, name)
        cx += cwp
        edges.append(cx)
    y -= hdr_h
    row_h = 0.4 * inch
    n_rows = 10
    c.setStrokeColor(RULE)
    c.setLineWidth(0.5)
    for r in range(n_rows):
        if r % 2:
            c.setFillColor(TINT)
            c.rect(x, y - row_h, w, row_h, stroke=0, fill=1)
        c.setFillColor(SOFT)
        c.setFont("Helvetica", 7.5)
        c.drawString(x + 5, y - row_h / 2 - 3, str(r + 1))
        c.line(x, y - row_h, x + w, y - row_h)
        y -= row_h
    top_tbl = y + row_h * n_rows
    for e in edges:
        c.line(e, top_tbl, e, y)

    y -= 0.3 * inch
    c.setFillColor(ACCENT)
    c.setFont("Times-Bold", 13)
    c.drawString(x, y, "Sources & notes")
    y -= 0.25 * inch
    c.setStrokeColor(RULE)
    while y > 0.6 * inch:
        c.line(x, y, x + w, y)
        y -= 0.27 * inch
    footer(c, pw, "Family Tree Research Workbook  •  Family Group Sheet")
    c.showPage()


# --------------------------------------------------------------------------
# Page 4: research log (landscape)
# --------------------------------------------------------------------------
def research_log(c):
    pw, ph = landscape(letter)
    page_title(c, "Research Log",
               "Ancestor / family being researched: ________________________________________     "
               "Goal: ________________________________________",
               pw, ph, top=0.35 * inch)
    x = 0.5 * inch
    w = pw - 1 * inch
    y = ph - 0.95 * inch
    cols = [("Date", 0.8), ("Where I looked (library, website)", 2.0),
            ("Record / source searched", 2.0), ("Looking for", 1.6),
            ("What I found", 2.6), ("Ref #", 0.6)]
    total = sum(cw for _, cw in cols)
    scale = w / (total * inch)
    hdr_h = 0.28 * inch
    c.setFillColor(ACCENT)
    c.rect(x, y - hdr_h, w, hdr_h, stroke=0, fill=1)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 7.5)
    edges = [x]
    cx = x
    for name, cw in cols:
        c.drawString(cx + 4, y - hdr_h + 8, name)
        cx += cw * inch * scale
        edges.append(cx)
    y -= hdr_h
    row_h = 0.4 * inch
    top_tbl = y
    c.setStrokeColor(RULE)
    c.setLineWidth(0.5)
    r = 0
    while y - row_h > 0.55 * inch:
        if r % 2:
            c.setFillColor(TINT)
            c.rect(x, y - row_h, w, row_h, stroke=0, fill=1)
        c.line(x, y - row_h, x + w, y - row_h)
        y -= row_h
        r += 1
    for e in edges:
        c.line(e, top_tbl, e, y)
    footer(c, pw, "Family Tree Research Workbook  •  Research Log")
    c.showPage()


def main():
    c = canvas.Canvas(OUT, pagesize=letter)
    c.setTitle("Family Tree Research Workbook")
    c.setAuthor("Family Tree Research Workbook")
    cover(c)
    c.setPageSize(landscape(letter))
    pedigree(c)
    c.setPageSize(letter)
    family_group(c)
    c.setPageSize(landscape(letter))
    research_log(c)
    c.save()


if __name__ == "__main__":
    main()
