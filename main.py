#!/usr/bin/env python3
"""The Passport Page of a Country That Isn't There.

Draws one open passport spread of the invented Republic of Velekia and
writes it to /output/entry.png. Pure Pillow, no network, deterministic.

The spread: left page is the data page (portrait, personal data in
Velekian/English, machine-readable zone); right page is a visa page
with an Aldanian transit visa, a consular fee stamp, a high-pass permit
and a coherent set of border stamps telling two trips (2023, 2025),
all dated after the passport's issue date.
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------- data
COUNTRY_EN = "REPUBLIC OF VELEKIA"
COUNTRY_VL = "VELEKISKÁ REPUBLIKA"
CODE = "VLK"
SURNAME = "HAVELKA"
GIVEN = "TOMÁŠ"
GIVEN_MRZ = "TOMAS"
NATIONALITY = "VELEKIAN / VELEKISKÝ"
DOB = "12 MAY 1988"
DOB_MRZ = "880512"
SEX = "M"
BIRTHPLACE = "OSTRANE"
ISSUE = "14 MAR 2021"
EXPIRY = "14 MAR 2031"
EXPIRY_MRZ = "310314"
AUTHORITY = "MINISTERSTVO VNÚTRA · OSTRANE"
DOC_NO = "E73920481"
PERSONAL_NO = "8805124417"

OUT_W, OUT_H = 1024, 724
S = 2  # supersampling factor
CW, CH = OUT_W * S, OUT_H * S

# spread geometry (output units)
SP_X0, SP_Y0, SP_X1, SP_Y1 = 26, 24, 998, 700
SPINE = (SP_X0 + SP_X1) // 2
LP = (SP_X0, SP_Y0, SPINE, SP_Y1)        # left page box
RP = (SPINE, SP_Y0, SP_X1, SP_Y1)        # right page box

# palette
PAPER_A = (243, 238, 224)
PAPER_B = (236, 228, 205)
NAVY = (30, 46, 78)
NAVY_SOFT = (52, 70, 102)
INK = (26, 26, 30)
LABEL = (96, 102, 112)
RULE = (168, 160, 140)
BURGUNDY = (122, 32, 46)
GOLD = (150, 118, 52)
STAMP_BLUE = (36, 84, 166)
STAMP_RED = (176, 52, 44)
STAMP_DARKBLUE = (28, 62, 128)
STAMP_TEAL = (24, 110, 96)
STAMP_VIOLET = (104, 66, 158)
STAMP_WINE = (140, 40, 60)

random.seed(20261121)

# ---------------------------------------------------------------- fonts
_HERE = os.path.dirname(os.path.abspath(__file__))
_FONT_FILES = {
    "serif_b": "LiberationSerif-Bold.ttf",
    "serif": "LiberationSerif-Regular.ttf",
    "serif_i": "LiberationSerif-Italic.ttf",
    "sans": "LiberationSans-Regular.ttf",
    "sans_b": "LiberationSans-Bold.ttf",
    "mono": "DejaVuSansMono.ttf",
}
_FONT_DIRS = [
    os.path.join(_HERE, "fonts"),
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype/dejavu",
]
_font_cache = {}


def F(name, size):
    """Font at `size` output units (scaled to the supersampled canvas)."""
    key = (name, size)
    if key in _font_cache:
        return _font_cache[key]
    fname = _FONT_FILES[name]
    path = None
    for d in _FONT_DIRS:
        p = os.path.join(d, fname)
        if os.path.exists(p):
            path = p
            break
    if path is None:  # last resort: PIL's bitmap font
        f = ImageFont.load_default()
    else:
        f = ImageFont.truetype(path, int(size * S))
    _font_cache[key] = f
    return f


# ---------------------------------------------------------------- helpers
def sc(v):
    return int(round(v * S))


def text(d, xy, s, font, fill, anchor="la", tracking=0):
    """Draw text; tracking is extra space per character in output units."""
    x, y = sc(xy[0]), sc(xy[1])
    if not tracking:
        d.text((x, y), s, font=font, fill=fill, anchor=anchor)
        return
    # tracked text: left-anchored manual advance
    total = 0.0
    widths = []
    for ch in s:
        w = d.textlength(ch, font=font)
        widths.append(w)
        total += w + sc(tracking)
    if anchor in ("ma", "mm", "ms"):
        x -= total / 2
    elif anchor in ("ra", "rm", "rs"):
        x -= total
    cx = x
    for ch, w in zip(s, widths):
        d.text((cx, y), ch, font=font, fill=fill, anchor="la")
        cx += w + sc(tracking)


def text_w(d, s, font, tracking=0):
    w = d.textlength(s, font=font)
    if tracking:
        w += sc(tracking) * max(0, len(s) - 1)
    return w / S


def line(d, pts, fill, width=1):
    d.line([(sc(x), sc(y)) for x, y in pts], fill=fill, width=max(1, sc(width)))


def rect(d, box, outline=None, fill=None, width=1):
    b = [sc(box[0]), sc(box[1]), sc(box[2]), sc(box[3])]
    d.rectangle(b, outline=outline, fill=fill, width=max(1, sc(width)))


def mrz_check_digit(field):
    weights = (7, 3, 1)
    total = 0
    for i, ch in enumerate(field):
        if ch.isdigit():
            v = int(ch)
        elif ch == "<":
            v = 0
        else:
            v = ord(ch) - 55  # A=10 .. Z=35
        total += v * weights[i % 3]
    return str(total % 10)


def mrz_lines():
    line1 = "P<" + CODE + SURNAME + "<<" + GIVEN_MRZ
    line1 = line1 + "<" * (44 - len(line1))
    doc = DOC_NO + mrz_check_digit(DOC_NO)
    dob = DOB_MRZ + mrz_check_digit(DOB_MRZ)
    exp = EXPIRY_MRZ + mrz_check_digit(EXPIRY_MRZ)
    pers = (PERSONAL_NO + "<<<<")[:14]
    pers += mrz_check_digit(pers)
    body = doc + CODE + dob + SEX + exp + pers
    composite = body[0:10] + body[13:20] + body[21:43]
    line2 = body + mrz_check_digit(composite)
    assert len(line1) == 44 and len(line2) == 44, (line1, line2)
    return line1, line2


def guilloche(d, box, ink, n_waves=5, amp=26, phase=0.0, step=7, vertical=False):
    """Fine interlaced security curves inside a page box (output units)."""
    x0, y0, x1, y1 = box
    span = (y1 - y0) if not vertical else (x1 - x0)
    for k in range(n_waves):
        pts = []
        t = 0.0
        base = (y0 if not vertical else x0) + span * (k + 0.5) / n_waves
        while t <= 1.0001:
            off = amp * math.sin(t * math.pi * 4 + phase + k * 1.7)
            off += amp * 0.45 * math.sin(t * math.pi * 9 + phase * 2 + k)
            if vertical:
                pts.append((base + off, y0 + (y1 - y0) * t) if False else (base + off, y0 + (y1 - y0) * t))
            else:
                pts.append((x0 + (x1 - x0) * t, base + off))
            t += step / 1000.0
        line(d, pts, ink, width=0.7)


# ---------------------------------------------------------------- emblem
def draw_emblem(d, cx, cy, w, ink=NAVY, accent=BURGUNDY):
    """Heraldic shield: three peaks over waves, one star. Output units."""
    h = w * 1.18
    x0, y0 = cx - w / 2, cy - h / 2
    x1, y1 = cx + w / 2, cy + h / 2
    # shield outline (flat top, curved point at bottom)
    pts = []
    steps = 24
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        y = y1 - (y1 - y0) * 0.28 * math.sin(t * math.pi) ** 1.5 - (y1 - y0) * 0.0
        pts.append((x, y))
    shield = [(x0, y0), (x1, y0)] + pts[::-1]
    d.polygon([(sc(x), sc(y)) for x, y in shield], outline=ink, width=max(2, sc(1.6)))
    inner = [(cx + (x - cx) * 0.86, cy + (y - cy) * 0.88) for x, y in shield]
    d.polygon([(sc(x), sc(y)) for x, y in inner], outline=ink, width=max(1, sc(0.8)))
    # star
    sy = y0 + h * 0.16
    star = []
    for i in range(10):
        r = w * 0.10 if i % 2 == 0 else w * 0.045
        a = -math.pi / 2 + i * math.pi / 5
        star.append((cx + r * math.cos(a), sy + r * math.sin(a)))
    d.polygon([(sc(x), sc(y)) for x, y in star], fill=accent)
    # three peaks
    base = y0 + h * 0.66
    peaks = [(x0 + w * 0.14, base), (x0 + w * 0.32, y0 + h * 0.34),
             (x0 + w * 0.47, base), (x0 + w * 0.60, y0 + h * 0.28),
             (x0 + w * 0.74, base), (x0 + w * 0.82, y0 + h * 0.44),
             (x0 + w * 0.88, base)]
    line(d, peaks, ink, width=1.6)
    # snow caps
    line(d, [(x0 + w * 0.285, y0 + h * 0.40), (x0 + w * 0.32, y0 + h * 0.34),
             (x0 + w * 0.355, y0 + h * 0.40)], accent, width=1.4)
    line(d, [(x0 + w * 0.565, y0 + h * 0.345), (x0 + w * 0.60, y0 + h * 0.28),
             (x0 + w * 0.635, y0 + h * 0.345)], accent, width=1.4)
    # waves
    for r in range(2):
        wy = base + h * (0.09 + 0.09 * r)
        pts = []
        t = 0.0
        while t <= 1.0001:
            pts.append((x0 + w * 0.14 + (w * 0.72) * t,
                        wy + h * 0.028 * math.sin(t * math.pi * 3 + r * 1.9)))
            t += 0.04
        line(d, pts, ink, width=1.3)


# ---------------------------------------------------------------- portrait
def draw_portrait(size_w=340, size_h=440):
    """A flat-shaded ID portrait of the holder, drawn at 2x of display size."""
    w, h = size_w * 2, size_h * 2
    img = Image.new("RGB", (w, h), (223, 229, 235))
    d = ImageDraw.Draw(img, "RGBA")
    # photo backdrop: gentle vertical gradient
    for yy in range(h):
        t = yy / h
        r = int(226 + (208 - 226) * t)
        g = int(232 + (216 - 232) * t)
        b = int(238 + (224 - 238) * t)
        d.line([(0, yy), (w, yy)], fill=(r, g, b))

    def P(x, y):
        return (x / size_w * w, y / size_h * h)

    def poly(pts, **kw):
        d.polygon([P(x, y) for x, y in pts], **kw)

    def ell(box, **kw):
        d.ellipse([P(box[0], box[1])[0], P(box[0], box[1])[1],
                   P(box[2], box[3])[0], P(box[2], box[3])[1]], **kw)

    skin = (216, 164, 124)
    skin_sh = (196, 142, 104)
    skin_hi = (228, 182, 142)
    hair = (74, 54, 40)
    jacket = (38, 44, 58)
    shirt = (232, 230, 224)

    cx = size_w / 2
    # shoulders / jacket
    poly([(cx - 128, size_h), (cx - 118, 356), (cx - 74, 322), (cx - 30, 312),
          (cx + 30, 312), (cx + 74, 322), (cx + 118, 356), (cx + 128, size_h)],
         fill=jacket)
    # shirt wedge + collar
    poly([(cx - 30, 312), (cx + 30, 312), (cx, 372)], fill=shirt)
    poly([(cx - 30, 312), (cx - 6, 336), (cx, 322), (cx - 14, 310)], fill=(214, 212, 204))
    poly([(cx + 30, 312), (cx + 6, 336), (cx, 322), (cx + 14, 310)], fill=(214, 212, 204))
    # neck
    poly([(cx - 24, 268), (cx + 24, 268), (cx + 20, 318), (cx - 20, 318)], fill=skin_sh)
    ell([cx - 26, 250, cx + 26, 292], fill=skin_sh)
    # ears
    ell([cx - 79, 168, cx - 58, 216], fill=skin)
    ell([cx + 58, 168, cx + 79, 216], fill=skin)
    ell([cx - 74, 178, cx - 62, 206], fill=skin_sh)
    ell([cx + 62, 178, cx + 74, 206], fill=skin_sh)
    # head
    ell([cx - 66, 62, cx + 66, 268], fill=skin)
    # jaw shaping: slightly narrower chin
    poly([(cx - 66, 190), (cx - 40, 262), (cx + 40, 262), (cx + 66, 190),
          (cx + 52, 250), (cx - 52, 250)], fill=skin)
    ell([cx - 44, 208, cx + 44, 276], fill=skin)
    # hair: cap with a smooth hairline, slightly higher at the parting
    hairline = []
    for i in range(13):
        t = i / 12
        hairline.append((cx + 64 - 130 * t,
                         146 - 42 * (math.sin(math.pi * t ** 0.85) ** 1.1)))
    poly([(cx - 68, 150), (cx - 70, 96), (cx - 52, 58), (cx - 8, 40),
          (cx + 38, 44), (cx + 62, 66), (cx + 68, 104)] + hairline +
         [(cx - 68, 150)], fill=hair)
    ell([cx - 68, 128, cx - 58, 190], fill=hair)
    ell([cx + 58, 128, cx + 68, 190], fill=hair)
    # eyebrows
    poly([(cx - 46, 152), (cx - 18, 147), (cx - 17, 155), (cx - 45, 159)], fill=hair)
    poly([(cx + 18, 147), (cx + 46, 152), (cx + 45, 159), (cx + 17, 155)], fill=hair)
    # eyes
    for sgn in (-1, 1):
        ex = cx + sgn * 31
        ell([ex - 15, 166, ex + 15, 180], fill=(246, 244, 240))
        ell([ex - 6.5, 165, ex + 6.5, 181], fill=(84, 62, 44))
        ell([ex - 3, 168, ex + 3, 178], fill=(20, 16, 12))
        ell([ex - 1.2, 169.5, ex + 1.6, 173], fill=(250, 250, 250))
        d.line([P(ex - 15, 166), P(ex + 15, 166)], fill=(120, 92, 70), width=2)
    # nose: soft bridge shading + nostrils + base line
    poly([(cx + 2, 178), (cx + 9, 208), (cx + 11, 216), (cx - 2, 216)], fill=(226, 178, 138))
    poly([(cx - 3, 178), (cx - 8, 210), (cx - 10, 216), (cx - 1, 217)], fill=(203, 148, 108))
    d.arc([P(cx - 12, 206)[0], P(cx - 12, 206)[1], P(cx + 12, 224)[0], P(cx + 12, 224)[1]],
          start=20, end=160, fill=(168, 118, 84), width=3)
    ell([cx - 9, 213, cx - 3.5, 218], fill=(150, 104, 72))
    ell([cx + 3.5, 213, cx + 9, 218], fill=(150, 104, 72))
    # mouth
    d.line([P(cx - 17, 240), P(cx + 17, 240)], fill=(150, 84, 74), width=3)
    d.arc([P(cx - 15, 232)[0], P(cx - 15, 232)[1], P(cx + 15, 248)[0], P(cx + 15, 248)[1]],
          start=15, end=165, fill=(172, 104, 92), width=2)
    # fine grain so it reads as a photograph, not a cartoon
    rng = random.Random(4417)
    px = img.load()
    for _ in range(26000):
        x = rng.randrange(w)
        y = rng.randrange(h)
        r, g, b = px[x, y]
        dv = rng.randint(-7, 7)
        px[x, y] = (max(0, min(255, r + dv)), max(0, min(255, g + dv)),
                    max(0, min(255, b + dv)))
    return img


def draw_signature(d, x, y, w, ink=(40, 40, 60)):
    """A fluent hand-inked signature squiggle ending in a flourish."""
    pts = []
    n = 90
    for i in range(n + 1):
        t = i / n
        px_ = x + w * t
        py_ = y + 10 * math.sin(t * math.pi * 5.2) * (1 - t * 0.35) \
            - 15 * math.exp(-((t - 0.16) ** 2) / 0.004) \
            + 7 * math.exp(-((t - 0.55) ** 2) / 0.002)
        pts.append((px_, py_))
    line(d, pts, ink, width=1.5)
    fl = [(x + w * 0.55 + w * 0.45 * t, y + 13 - 3 * math.sin(t * math.pi))
          for t in [i / 20 for i in range(21)]]
    line(d, fl, ink, width=1.1)


# ---------------------------------------------------------------- stamps
def _ink_layer(w, h, draw_fn, color):
    layer = Image.new("RGBA", (sc(w), sc(h)), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    draw_fn(d)
    # ink unevenness: erase speckles deterministically
    rng = random.Random(hash((w, h, color)) & 0xFFFF)
    px = layer.load()
    lw, lh = layer.size
    for _ in range(int(lw * lh / 90)):
        x = rng.randrange(lw)
        y = rng.randrange(lh)
        r, g, b, a = px[x, y]
        if a:
            px[x, y] = (r, g, b, int(a * 0.35))
    return layer


def stamp_rect(dummy, cx, cy, w, h, color, title, place, date, sub, angle, alpha=168):
    def draw(d):
        rect(d, (4, 4, w - 4, h - 4), outline=color + (alpha,), width=2.2)
        rect(d, (9, 9, w - 9, h - 9), outline=color + (int(alpha * 0.75),), width=0.9)
        text(d, (w / 2, h * 0.10), title, F("sans_b", 12.5), color + (alpha,), anchor="ma", tracking=0.6)
        text(d, (w / 2, h * 0.33), place, F("sans", 11), color + (alpha,), anchor="ma", tracking=0.4)
        text(d, (w / 2, h * 0.52), date, F("sans_b", 15), color + (alpha,), anchor="ma", tracking=0.8)
        text(d, (w / 2, h * 0.76), sub, F("sans", 9.5), color + (alpha,), anchor="ma", tracking=0.5)
    layer = _ink_layer(w, h, draw, color)
    layer = layer.rotate(angle, expand=True, resample=Image.BICUBIC)
    dummy.alpha_composite(layer, (sc(cx - layer.size[0] / S / 2), sc(cy - layer.size[1] / S / 2)))


def stamp_oval(dummy, cx, cy, w, h, color, title, place, date, sub, angle, alpha=165):
    def draw(d):
        d.ellipse([sc(4), sc(4), sc(w - 4), sc(h - 4)], outline=color + (alpha,), width=max(2, sc(2.2)))
        d.ellipse([sc(10), sc(10), sc(w - 10), sc(h - 10)], outline=color + (int(alpha * 0.7),), width=max(1, sc(0.9)))
        text(d, (w / 2, h * 0.20), title, F("sans_b", 11.5), color + (alpha,), anchor="ma", tracking=0.5)
        text(d, (w / 2, h * 0.38), place, F("sans", 10.5), color + (alpha,), anchor="ma")
        text(d, (w / 2, h * 0.53), date, F("sans_b", 14), color + (alpha,), anchor="ma", tracking=0.7)
        text(d, (w / 2, h * 0.72), sub, F("sans", 8.5), color + (alpha,), anchor="ma", tracking=0.4)
    layer = _ink_layer(w, h, draw, color)
    layer = layer.rotate(angle, expand=True, resample=Image.BICUBIC)
    dummy.alpha_composite(layer, (sc(cx - layer.size[0] / S / 2), sc(cy - layer.size[1] / S / 2)))


def stamp_round(dummy, cx, cy, r, color, top, mid, bottom, angle, alpha=170):
    def draw(d):
        d.ellipse([sc(3), sc(3), sc(2 * r - 3), sc(2 * r - 3)], outline=color + (alpha,), width=max(2, sc(2)))
        d.ellipse([sc(9), sc(9), sc(2 * r - 9), sc(2 * r - 9)], outline=color + (int(alpha * 0.7),), width=max(1, sc(0.9)))
        text(d, (r, r * 0.52), top, F("sans_b", 9), color + (alpha,), anchor="ma", tracking=0.4)
        text(d, (r, r * 0.86), mid, F("sans_b", 12.5), color + (alpha,), anchor="ma")
        text(d, (r, r * 1.22), bottom, F("sans", 8.5), color + (alpha,), anchor="ma", tracking=0.4)
    layer = _ink_layer(2 * r, 2 * r, draw, color)
    layer = layer.rotate(angle, expand=True, resample=Image.BICUBIC)
    dummy.alpha_composite(layer, (sc(cx - layer.size[0] / S / 2), sc(cy - layer.size[1] / S / 2)))


# ---------------------------------------------------------------- pages
def field(d, x, y, w, label, value, vfont="sans_b", vsize=13.5):
    text(d, (x, y), label, F("sans", 7.5), LABEL, tracking=0.3)
    text(d, (x, y + 11), value, F(vfont, vsize), INK)
    line(d, [(x, y + 33), (x + w, y + 33)], RULE, width=0.8)


def data_page(img):
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = LP
    m = 24  # inner margin
    ix0, ix1 = x0 + m, x1 - m
    # header
    text(d, (ix0, y0 + 20), "VELEKISKÁ REPUBLIKA", F("serif_b", 13), NAVY, tracking=2.2)
    text(d, (ix0, y0 + 40), COUNTRY_EN, F("serif_b", 21), BURGUNDY, tracking=1.2)
    text(d, (ix1, y0 + 22), "PAS", F("serif_b", 15), NAVY, anchor="ra", tracking=1.5)
    text(d, (ix1, y0 + 43), "PASSPORT", F("serif_b", 11), NAVY_SOFT, anchor="ra", tracking=1.5)
    draw_emblem(d, ix1 - 30, y0 + 86, 38)
    line(d, [(ix0, y0 + 66), (ix1 - 76, y0 + 66)], NAVY, width=1.4)
    line(d, [(ix0, y0 + 70), (ix1 - 76, y0 + 70)], GOLD, width=0.8)
    # photo
    ph_x, ph_y, ph_w, ph_h = ix0, y0 + 88, 128, 166
    photo = draw_portrait(256, 332).resize((sc(ph_w), sc(ph_h)), Image.LANCZOS)
    img.alpha_composite(photo.convert("RGBA"), (sc(ph_x), sc(ph_y)))
    rect(d, (ph_x, ph_y, ph_x + ph_w, ph_y + ph_h), outline=NAVY_SOFT, width=1)
    # ghost image (security reprint of the portrait, faded, below the data)
    ghost = draw_portrait(256, 332).resize((sc(52), sc(67)), Image.LANCZOS)
    ghost.putalpha(34)
    img.alpha_composite(ghost, (sc(ix1 - 64), sc(y0 + 420)))
    # signature under photo
    text(d, (ph_x, ph_y + ph_h + 8), "PODPIS / SIGNATURE", F("sans", 7.5), LABEL, tracking=0.5)
    draw_signature(d, ph_x + 4, ph_y + ph_h + 26, 108)
    line(d, [(ph_x, ph_y + ph_h + 46), (ph_x + ph_w, ph_y + ph_h + 46)], RULE, width=0.8)
    # fields column
    fx = ph_x + ph_w + 20
    fw = ix1 - fx
    fy = y0 + 84
    # type / code / number row
    field(d, fx, fy, 52, "TYP / TYPE", "P")
    field(d, fx + 62, fy, 62, "KÓD / CODE", CODE)
    field(d, fx + 134, fy, fw - 134, "ČÍSLO PASU / No.", DOC_NO)
    fy += 46
    field(d, fx, fy, fw, "PRIEZVISKO / SURNAME", SURNAME, vsize=15)
    fy += 46
    field(d, fx, fy, fw, "MENÁ / GIVEN NAMES", GIVEN, vsize=15)
    fy += 46
    field(d, fx, fy, fw, "OBČIANSTVO / NATIONALITY", NATIONALITY)
    fy += 46
    field(d, fx, fy, 168, "DÁTUM NARODENIA / DATE OF BIRTH", DOB)
    field(d, fx + 180, fy, fw - 180, "POHLAVIE / SEX", SEX)
    fy += 46
    field(d, fx, fy, fw, "MIESTO NARODENIA / PLACE OF BIRTH", BIRTHPLACE)
    fy += 46
    field(d, fx, fy, 168, "DÁTUM VYDANIA / DATE OF ISSUE", ISSUE)
    field(d, fx + 180, fy, fw - 180, "PLATNOSŤ DO / EXPIRY", EXPIRY)
    fy += 46
    field(d, fx, fy, fw, "VYDAL / AUTHORITY", AUTHORITY, vsize=11.5)
    # perforated document number down the outer edge
    text(d, (x0 + 9, y1 - 120), DOC_NO, F("mono", 9), (150, 144, 128), tracking=2)
    # machine-readable zone
    l1, l2 = mrz_lines()
    mz_y = y1 - 62
    line(d, [(ix0, mz_y - 10), (ix1, mz_y - 10)], RULE, width=0.8)
    text(d, (ix0, mz_y), l1, F("mono", 16.5), INK, tracking=0.4)
    text(d, (ix0, mz_y + 26), l2, F("mono", 16.5), INK, tracking=0.4)


def visa_page(img):
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = RP
    m = 24
    ix0, ix1 = x0 + m, x1 - m
    # header
    text(d, (ix0, y0 + 20), "VÍZA", F("serif_b", 15), NAVY, tracking=2)
    text(d, (ix0 + 62, y0 + 24), "/ VISAS", F("serif", 11), NAVY_SOFT, tracking=1)
    text(d, (ix1, y0 + 20), "7", F("serif_b", 14), NAVY_SOFT, anchor="ra")
    line(d, [(ix0, y0 + 52), (ix1, y0 + 52)], NAVY, width=1.2)
    line(d, [(ix0, y0 + 56), (ix1, y0 + 56)], GOLD, width=0.7)

    # --- Aldanian transit visa (sticker) — the telling paperwork detail
    vx, vy, vw, vh = ix0 + 6, y0 + 74, 300, 128
    rect(d, (vx, vy, vx + vw, vy + vh), outline=STAMP_VIOLET, fill=(238, 232, 246, 110), width=1.6)
    rect(d, (vx + 5, vy + 5, vx + vw - 5, vy + vh - 5), outline=STAMP_VIOLET, width=0.7)
    text(d, (vx + 14, vy + 10), "REPUBLIC OF ALDANIA", F("sans_b", 11.5), STAMP_VIOLET, tracking=0.8)
    text(d, (vx + 14, vy + 27), "TRANSIT VISA · TRANZITNÉ VÍZUM", F("sans_b", 10), STAMP_VIOLET, tracking=0.5)
    line(d, [(vx + 14, vy + 46), (vx + vw - 14, vy + 46)], STAMP_VIOLET, width=0.7)
    rows = [
        ("HOLDER", "HAVELKA TOMÁŠ"),
        ("VALID", "72 HOURS FROM FIRST ENTRY"),
        ("CONDITION", "NOT VALID FOR EMPLOYMENT"),
        ("ISSUED AT", "OSTRANE · 22 MAY 2023"),
        ("VISA No.", "AL-TR 0114827"),
    ]
    ry = vy + 54
    for lab, val in rows:
        text(d, (vx + 14, ry), lab, F("sans", 8), LABEL, tracking=0.5)
        text(d, (vx + 84, ry - 2), val, F("sans_b", 10), INK)
        ry += 14.5
    # consular fee stamp overlapping the visa's lower-right corner
    stamp_round(img, vx + vw - 4, vy + vh - 2, 33, STAMP_VIOLET,
                "FEE", "25 ALD", "PAID · 2023", -14)

    # --- border stamps: two coherent trips, all after 14 MAR 2021 issue
    # trip 1: fly to Aldania and back, June 2023
    stamp_rect(img, ix0 + 102, y0 + 264, 168, 86, STAMP_BLUE,
               "VELEKIA", "OSTRANE INT'L AIRPORT", "03 JUN 2023", "DEPARTURE · ODCHOD", -4)
    stamp_rect(img, ix0 + 322, y0 + 264, 168, 86, STAMP_RED,
               "ALDANIA", "BRANKA AIRPORT", "03 JUN 2023", "ARRIVAL", 3)
    stamp_rect(img, ix0 + 102, y0 + 358, 168, 86, STAMP_DARKBLUE,
               "ALDANIA", "BRANKA AIRPORT", "17 JUN 2023", "DEPARTURE", 2)
    stamp_rect(img, ix0 + 322, y0 + 358, 168, 86, STAMP_BLUE,
               "VELEKIA", "OSTRANE INT'L AIRPORT", "17 JUN 2023", "ARRIVAL · PRÍCHOD", -3)
    # trip 2: over the High Pass to Sorvena, autumn 2025
    stamp_oval(img, ix0 + 100, y0 + 452, 160, 88, STAMP_TEAL,
               "VELEKIA", "VYSOKÝ PRIESMYK", "28 SEP 2025", "HIGH PASS · EXIT", -6)
    stamp_oval(img, ix0 + 320, y0 + 452, 160, 88, STAMP_WINE,
               "SORVENA", "PORT ANSEL", "29 SEP 2025", "ARRIVAL", 4)
    stamp_oval(img, ix0 + 100, y0 + 548, 160, 84, STAMP_DARKBLUE,
               "SORVENA", "PORT ANSEL", "05 OCT 2025", "DEPARTURE", -2)
    # high-pass permit stamp beside the 2025 departure stamp
    stamp_rect(img, ix0 + 322, y0 + 548, 172, 86, STAMP_TEAL,
               "HIGH PASS PERMIT", "SEASON 2025 · VELEKIA", "PAID 40 VLR", "FOOT & VEHICLE", 5, alpha=150)


# ---------------------------------------------------------------- assembly
def paper_base():
    img = Image.new("RGBA", (CW, CH), (52, 58, 68, 255))
    d = ImageDraw.Draw(img, "RGBA")
    # desk vignette
    for yy in range(0, CH, 4):
        t = yy / CH
        c = int(58 - 16 * abs(t - 0.42))
        d.line([(0, yy), (CW, yy)], fill=(c - 6, c, c + 8, 255))
    # soft shadow under the spread
    sh = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle([sc(SP_X0 + 6), sc(SP_Y0 + 12), sc(SP_X1 + 8), sc(SP_Y1 + 14)],
                         radius=sc(14), fill=(0, 0, 0, 120))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(sc(9))))
    # the two pages
    for (x0, y0, x1, y1) in (LP, RP):
        page = Image.new("RGBA", (sc(x1 - x0), sc(y1 - y0)), PAPER_A + (255,))
        pd = ImageDraw.Draw(page, "RGBA")
        pw, ph = page.size
        for yy in range(ph):
            t = yy / ph
            r = int(PAPER_A[0] + (PAPER_B[0] - PAPER_A[0]) * t)
            g = int(PAPER_A[1] + (PAPER_B[1] - PAPER_A[1]) * t)
            b = int(PAPER_A[2] + (PAPER_B[2] - PAPER_A[2]) * t)
            pd.line([(0, yy), (pw, yy)], fill=(r, g, b, 255))
        # security guilloche fields (very fine, pale — a tint, not a scribble)
        guilloche(pd, (18, 30, (x1 - x0) - 18, (y1 - y0) - 30), (172, 198, 186, 30),
                  n_waves=13, amp=6, phase=0.7)
        guilloche(pd, (18, 30, (x1 - x0) - 18, (y1 - y0) - 30), (222, 190, 184, 20),
                  n_waves=11, amp=9, phase=2.4)
        img.alpha_composite(page, (sc(x0), sc(y0)))
    d = ImageDraw.Draw(img, "RGBA")
    # page outlines + spine gutter
    rect(d, (SP_X0, SP_Y0, SP_X1, SP_Y1), outline=(120, 112, 96), width=1)
    grad = Image.new("RGBA", (sc(46), sc(SP_Y1 - SP_Y0)), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for xx in range(grad.size[0]):
        t = xx / grad.size[0]
        a = int(105 * math.sin(t * math.pi) ** 1.5)
        gd.line([(xx, 0), (xx, grad.size[1])], fill=(30, 26, 20, a))
    img.alpha_composite(grad, (sc(SPINE - 23), sc(SP_Y0)))
    line(d, [(SPINE, SP_Y0 + 4), (SPINE, SP_Y1 - 4)], (90, 82, 66), width=0.8)
    return img


def main():
    img = paper_base()
    data_page(img)
    visa_page(img)
    # laminate sheen over the data page only
    sheen = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    sd.polygon([(sc(LP[0]), sc(LP[3])), (sc(LP[0] + 190), sc(LP[1])),
                (sc(LP[0] + 330), sc(LP[1])), (sc(LP[0] + 90), sc(LP[3]))],
               fill=(255, 255, 255, 16))
    img.alpha_composite(sheen)
    out = img.convert("RGB").resize((OUT_W, OUT_H), Image.LANCZOS)
    os.makedirs("/output", exist_ok=True)
    out.save("/output/entry.png", optimize=True)
    print("wrote /output/entry.png", out.size)


if __name__ == "__main__":
    main()
