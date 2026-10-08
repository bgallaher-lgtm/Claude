import sys, qrcode
from PIL import Image, ImageDraw
src, out = sys.argv[1], sys.argv[2]
URL = "https://gallahercomputers.com/accepted-items"
S = 2400/1448  # scale to 600 DPI at 4" wide
im = Image.open(src).convert("RGB")
im = im.resize((2400, round(1086*S)), Image.LANCZOS).resize((2400,1800), Image.LANCZOS)
sx, sy = 2400/1448, 1800/1086
# inner white area of the QR frame (original px coords)
x0,y0,x1,y1 = 1073,488,1382,778
d = ImageDraw.Draw(im)
inset = 7
d.rectangle([ (x0+inset)*sx, (y0+inset)*sy, (x1-inset)*sx, (y1-inset)*sy ], fill="white")
qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0, box_size=1)
qr.add_data(URL); qr.make(fit=True)
m = qr.get_matrix(); n = len(m)
avail = min((x1-x0)*sx, (y1-y0)*sy)
mod = int(avail / (n + 4))  # >=2 module quiet zone each side inside the frame
size = mod*n
cx, cy = (x0+x1)/2*sx, (y0+y1)/2*sy
ox, oy = round(cx-size/2), round(cy-size/2)
for r,row in enumerate(m):
    for c,v in enumerate(row):
        if v: d.rectangle([ox+c*mod, oy+r*mod, ox+(c+1)*mod-1, oy+(r+1)*mod-1], fill="black")
print("version", qr.version, "modules", n, "module px", mod, "QR inches", size/600)
im.save(out+".png", dpi=(600,600))
im.save(out+".pdf", resolution=600)
