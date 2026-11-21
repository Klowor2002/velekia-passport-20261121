#!/usr/bin/env python3
"""The Passport Page of a Country That Isn't There.

Draws one open passport spread of the invented Republic of Velekia and
writes it to /output/entry.png. Pure Python standard library — no PIL,
no font files, no network, deterministic.

The renderer is hand-rolled: an RGBA raster canvas with polygon/ellipse/
line primitives, a 5x7 bitmap font defined in code (with the Slovak-style
diacritics the Velekian text needs), stamp layers that are rotated and
alpha-composited like real ink, and a PNG encoder built on zlib.

The spread: left page is the data page (portrait, personal data in
Velekian/English, machine-readable zone); right page is a visa page
with an Aldanian transit visa, a consular fee stamp, a high-pass permit
and a coherent set of border stamps telling two trips (2023, 2025),
all dated after the passport's issue date.
"""
import math
import os
import random
import struct
import zlib

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


def rgba(c, a=255):
    return (c[0], c[1], c[2], a)


# ---------------------------------------------------------------- font
# 5x7 bitmap glyphs. Grid is 10 rows: rows 0-1 diacritics, 2-8 body,
# row 9 descender. '#' marks a set pixel.
_BODY = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "10001", "11001", "10101", "10011", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "01010", "00100", "00100", "00100", "01010", "10001"),
    "Y": ("10001", "01010", "00100", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "01100", "00100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "&": ("01100", "10010", "10010", "01000", "10101", "10010", "01101"),
    "·": ("00000", "00000", "00000", "01100", "01100", "00000", "00000"),
    "<": ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    "o": ("00000", "00000", "00000", "01110", "10001", "10001", "01110"),
}
_DIA = {
    "acute": ("00010", "00100"),
    "caron": ("01010", "00100"),
    "circ": ("00100", "01010"),
}
_VARIANTS = {
    "Á": ("A", "acute"), "É": ("E", "acute"), "Í": ("I", "acute"),
    "Ú": ("U", "acute"), "Ý": ("Y", "acute"),
    "Č": ("C", "caron"), "Š": ("S", "caron"), "Ž": ("Z", "caron"),
    "Ť": ("T", "caron"), "Ô": ("O", "circ"),
}
GLYPHS = {}


def _build_glyphs():
    for ch, body in _BODY.items():
        GLYPHS[ch] = ("00000", "00000") + body + ("00000",)
    for ch, (base, dia) in _VARIANTS.items():
        GLYPHS[ch] = _DIA[dia] + _BODY[base] + ("00000",)
    # comma needs its descender tail in row 9
    GLYPHS[","] = ("00000", "00000") + _BODY[","][:6] + ("00100", "01000")


_build_glyphs()
GLYPH_W = 5
GLYPH_H = 10


def font_scale(size):
    """Bitmap block size (canvas px per glyph pixel) for a text size.

    Floored, not rounded: the monospace advance (6 units per char) is
    wider than a proportional font's, so rounding up overflows the
    narrowest fields — the 31-char bilingual labels in their 168-unit
    columns and the fee stamp's bottom line inside its 66-unit circle.
    """
    return max(1, int(size / 5.0))


# ---------------------------------------------------------------- canvas
class Canvas:
    """RGBA raster, coordinates in `units`; self.u = canvas px per unit."""

    def __init__(self, w_units, h_units, u, color=(0, 0, 0, 0)):
        self.u = float(u)
        self.w = int(round(w_units * self.u))
        self.h = int(round(h_units * self.u))
        self.buf = bytearray(bytes(color) * (self.w * self.h))

    def px(self, v):
        return v * self.u

    # -- pixel core ------------------------------------------------------
    def blend_px(self, x, y, color):
        if x < 0 or y < 0 or x >= self.w or y >= self.h:
            return
        sr, sg, sb, sa = color
        if sa == 0:
            return
        i = (y * self.w + x) * 4
        if sa == 255:
            self.buf[i:i + 4] = bytes((sr, sg, sb, 255))
            return
        dr, dg, db, da = self.buf[i], self.buf[i + 1], self.buf[i + 2], self.buf[i + 3]
        oa = sa + da * (255 - sa) / 255.0
        if oa <= 0:
            return
        t = da * (255 - sa) / 255.0
        self.buf[i] = int((sr * sa + dr * t) / oa)
        self.buf[i + 1] = int((sg * sa + dg * t) / oa)
        self.buf[i + 2] = int((sb * sa + db * t) / oa)
        self.buf[i + 3] = int(oa)

    def fill_span(self, x0, x1, y, color):
        """Fill canvas-px span [x0, x1] on row y (inclusive)."""
        if y < 0 or y >= self.h:
            return
        x0 = max(0, int(math.floor(x0)))
        x1 = min(self.w - 1, int(math.ceil(x1)))
        if x1 < x0:
            return
        if color[3] == 255:
            row = bytes(color) * (x1 - x0 + 1)
            i = (y * self.w + x0) * 4
            self.buf[i:i + len(row)] = row
        else:
            for x in range(x0, x1 + 1):
                self.blend_px(x, y, color)

    def fill_rect_px(self, x0, y0, x1, y1, color):
        for y in range(max(0, y0), min(self.h, y1)):
            self.fill_span(x0, x1 - 1, y, color)

    # -- primitives (unit coords) ----------------------------------------
    def stamp_disc(self, cx, cy, r, color):
        """Filled disc in canvas px."""
        if r < 0.6:
            self.blend_px(int(round(cx)), int(round(cy)), color)
            return
        y0 = int(math.floor(cy - r))
        y1 = int(math.ceil(cy + r))
        for y in range(y0, y1 + 1):
            dy = y + 0.5 - cy
            if abs(dy) > r:
                continue
            dx = math.sqrt(max(0.0, r * r - dy * dy))
            self.fill_span(cx - dx, cx + dx, y, color)

    def line(self, pts, color, width=1.0):
        """Polyline through unit-coord points; width in units."""
        r = max(0.45, width * self.u / 2.0)
        pp = [(self.px(x), self.px(y)) for x, y in pts]
        for (ax, ay), (bx, by) in zip(pp, pp[1:]):
            n = max(2, int(math.hypot(bx - ax, by - ay) / 0.7) + 1)
            for i in range(n + 1):
                t = i / n
                self.stamp_disc(ax + (bx - ax) * t, ay + (by - ay) * t, r, color)

    def polygon(self, pts, fill=None, outline=None, width=1.0):
        pp = [(self.px(x), self.px(y)) for x, y in pts]
        if fill is not None:
            ys = [p[1] for p in pp]
            y_lo = max(0, int(math.floor(min(ys))))
            y_hi = min(self.h - 1, int(math.ceil(max(ys))))
            n = len(pp)
            for y in range(y_lo, y_hi + 1):
                yc = y + 0.5
                xs = []
                for i in range(n):
                    ax, ay = pp[i]
                    bx, by = pp[(i + 1) % n]
                    if (ay <= yc < by) or (by <= yc < ay):
                        xs.append(ax + (yc - ay) * (bx - ax) / (by - ay))
                xs.sort()
                for i in range(0, len(xs) - 1, 2):
                    self.fill_span(xs[i], xs[i + 1], y, fill)
        if outline is not None:
            self.line(list(pts) + [pts[0]], outline, width)

    def ellipse(self, box, fill=None, outline=None, width=1.0):
        x0, y0, x1, y1 = (self.px(box[0]), self.px(box[1]),
                          self.px(box[2]), self.px(box[3]))
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        rx, ry = abs(x1 - x0) / 2.0, abs(y1 - y0) / 2.0
        if fill is not None and rx > 0 and ry > 0:
            for y in range(max(0, int(cy - ry)), min(self.h, int(cy + ry) + 1)):
                t = (y + 0.5 - cy) / ry
                if abs(t) > 1:
                    continue
                dx = rx * math.sqrt(1 - t * t)
                self.fill_span(cx - dx, cx + dx, y, fill)
        if outline is not None:
            r = max(0.45, width * self.u / 2.0)
            steps = max(28, int(2 * math.pi * max(rx, ry) / 1.6) + 1)
            for i in range(steps + 1):
                a = 2 * math.pi * i / steps
                self.stamp_disc(cx + rx * math.cos(a), cy + ry * math.sin(a), r, outline)

    def rect(self, box, fill=None, outline=None, width=1.0):
        x0, y0 = self.px(box[0]), self.px(box[1])
        x1, y1 = self.px(box[2]), self.px(box[3])
        if fill is not None:
            self.fill_rect_px(int(x0), int(y0), int(x1), int(y1), fill)
        if outline is not None:
            wu = width
            pts = [(box[0], box[1]), (box[2], box[1]), (box[2], box[3]),
                   (box[0], box[3]), (box[0], box[1])]
            self.line(pts, outline, wu)

    def rounded_rect(self, box, radius, fill):
        x0, y0 = self.px(box[0]), self.px(box[1])
        x1, y1 = self.px(box[2]), self.px(box[3])
        r = self.px(radius)
        for y in range(max(0, int(y0)), min(self.h, int(y1) + 1)):
            cy = y + 0.5
            if cy < y0 + r:
                d = (y0 + r) - cy
                inset = r - math.sqrt(max(0.0, r * r - d * d))
            elif cy > y1 - r:
                d = cy - (y1 - r)
                inset = r - math.sqrt(max(0.0, r * r - d * d))
            else:
                inset = 0.0
            self.fill_span(x0 + inset, x1 - inset, y, fill)

    # -- text --------------------------------------------------------------
    def text_w(self, s, size, bold=False, tracking=0.0):
        k = font_scale(size)
        adv = (GLYPH_W + 1) * k + (1 if bold else 0)
        w = sum(adv for _ in s) + self.px(tracking) * len(s)
        return w / self.u

    def text(self, xy, s, size, color, bold=False, anchor="la", tracking=0.0):
        k = font_scale(size)
        adv = (GLYPH_W + 1) * k + (1 if bold else 0)
        trk = self.px(tracking)
        total = adv * len(s) + trk * len(s)
        x = self.px(xy[0])
        y = self.px(xy[1])
        if anchor in ("ma", "mm", "ms"):
            x -= total / 2.0
        elif anchor in ("ra", "rm", "rs"):
            x -= total
        cx = x
        for ch in s:
            glyph = GLYPHS.get(ch)
            if glyph is not None:
                for row_i, row in enumerate(glyph):
                    for col_i, bit in enumerate(row):
                        if bit == "1":
                            gx = int(cx + col_i * k)
                            gy = int(y + row_i * k)
                            self.fill_rect_px(gx, gy, gx + k, gy + k, color)
                            if bold:
                                self.fill_rect_px(gx + 1, gy, gx + k + 1, gy + k, color)
            cx += adv + trk

    # -- compositing -------------------------------------------------------
    def alpha_composite(self, src, dx_units, dy_units, alpha_scale=1.0):
        dx = int(round(self.px(dx_units)))
        dy = int(round(self.px(dy_units)))
        for sy in range(src.h):
            ty = dy + sy
            if ty < 0 or ty >= self.h:
                continue
            for sx in range(src.w):
                tx = dx + sx
                if tx < 0 or tx >= self.w:
                    continue
                i = (sy * src.w + sx) * 4
                sa = src.buf[i + 3]
                if sa == 0:
                    continue
                if alpha_scale != 1.0:
                    sa = int(sa * alpha_scale)
                    if sa == 0:
                        continue
                self.blend_px(tx, ty, (src.buf[i], src.buf[i + 1], src.buf[i + 2], sa))

    def rotate(self, angle_deg):
        """Rotate counter-clockwise (PIL convention), expanding the canvas."""
        ang = math.radians(angle_deg)
        cos_a, sin_a = math.cos(ang), math.sin(ang)
        w, h = self.w, self.h
        nw = int(math.ceil(abs(w * cos_a) + abs(h * sin_a)))
        nh = int(math.ceil(abs(w * sin_a) + abs(h * cos_a)))
        out = Canvas.__new__(Canvas)
        out.u = self.u
        out.w, out.h = nw, nh
        out.buf = bytearray(nw * nh * 4)
        ccx, ccy = w / 2.0, h / 2.0
        ocx, ocy = nw / 2.0, nh / 2.0
        for oy in range(nh):
            dy = oy + 0.5 - ocy
            for ox in range(nw):
                dx = ox + 0.5 - ocx
                # inverse map: rotate by -angle
                sx = ccx + dx * cos_a - dy * sin_a
                sy = ccy + dx * sin_a + dy * cos_a
                if sx < 0 or sy < 0 or sx >= w or sy >= h:
                    continue
                x0 = int(math.floor(sx - 0.5))
                y0 = int(math.floor(sy - 0.5))
                fx = (sx - 0.5) - x0
                fy = (sy - 0.5) - y0
                acc = [0.0, 0.0, 0.0, 0.0]
                for yy in (y0, y0 + 1):
                    for xx in (x0, x0 + 1):
                        wgt = ((1 - fx) if xx == x0 else fx) * ((1 - fy) if yy == y0 else fy)
                        if wgt == 0:
                            continue
                        cxx = min(max(xx, 0), w - 1)
                        cyy = min(max(yy, 0), h - 1)
                        i = (cyy * w + cxx) * 4
                        for c in range(4):
                            acc[c] += self.buf[i + c] * wgt
                j = (oy * nw + ox) * 4
                for c in range(4):
                    out.buf[j + c] = int(round(acc[c]))
        return out

    def downsample2(self):
        """Box-downsample by 2 (canvas must be even-sized); returns RGB bytes."""
        ow, oh = self.w // 2, self.h // 2
        out = bytearray(ow * oh * 3)
        w4 = self.w * 4
        for oy in range(oh):
            y = oy * 2
            r0 = y * w4
            r1 = (y + 1) * w4
            orow = oy * ow * 3
            for ox in range(ow):
                x4 = ox * 8
                j = orow + ox * 3
                for c in range(3):
                    out[j + c] = (self.buf[r0 + x4 + c] + self.buf[r0 + x4 + 4 + c]
                                  + self.buf[r1 + x4 + c] + self.buf[r1 + x4 + 4 + c]) // 4
        return bytes(out), ow, oh


# ---------------------------------------------------------------- PNG out
def write_png(path, rgb, w, h):
    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        c += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        return c

    stride = w * 3
    raw = bytearray()
    prev = bytes(stride)
    for y in range(h):
        row = rgb[y * stride:(y + 1) * stride]
        # pick the better of filter 0 (none) and 2 (up) by signed-byte cost
        up = bytes((a - b) & 0xFF for a, b in zip(row, prev))
        cost0 = sum(b if b < 128 else 256 - b for b in row[::37])
        cost2 = sum(b if b < 128 else 256 - b for b in up[::37])
        if cost2 < cost0:
            raw.append(2)
            raw.extend(up)
        else:
            raw.append(0)
            raw.extend(row)
        prev = row
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- MRZ
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


# ---------------------------------------------------------------- helpers
def guilloche(cv, box, ink, n_waves=5, amp=26, phase=0.0, step=7, vertical=False):
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
                pts.append((base + off, y0 + (y1 - y0) * t))
            else:
                pts.append((x0 + (x1 - x0) * t, base + off))
            t += step / 1000.0
        cv.line(pts, ink, width=0.7)


# ---------------------------------------------------------------- emblem
def draw_emblem(cv, cx, cy, w, ink=NAVY, accent=BURGUNDY):
    """Heraldic shield: three peaks over waves, one star. Output units."""
    ink4, acc4 = rgba(ink), rgba(accent)
    h = w * 1.18
    x0, y0 = cx - w / 2, cy - h / 2
    x1, y1 = cx + w / 2, cy + h / 2
    pts = []
    steps = 24
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        y = y1 - (y1 - y0) * 0.28 * math.sin(t * math.pi) ** 1.5
        pts.append((x, y))
    shield = [(x0, y0), (x1, y0)] + pts[::-1]
    cv.polygon(shield, outline=ink4, width=1.6)
    inner = [(cx + (x - cx) * 0.86, cy + (y - cy) * 0.88) for x, y in shield]
    cv.polygon(inner, outline=ink4, width=0.8)
    # star
    sy = y0 + h * 0.16
    star = []
    for i in range(10):
        r = w * 0.10 if i % 2 == 0 else w * 0.045
        a = -math.pi / 2 + i * math.pi / 5
        star.append((cx + r * math.cos(a), sy + r * math.sin(a)))
    cv.polygon(star, fill=acc4)
    # three peaks
    base = y0 + h * 0.66
    peaks = [(x0 + w * 0.14, base), (x0 + w * 0.32, y0 + h * 0.34),
             (x0 + w * 0.47, base), (x0 + w * 0.60, y0 + h * 0.28),
             (x0 + w * 0.74, base), (x0 + w * 0.82, y0 + h * 0.44),
             (x0 + w * 0.88, base)]
    cv.line(peaks, ink4, width=1.6)
    # snow caps
    cv.line([(x0 + w * 0.285, y0 + h * 0.40), (x0 + w * 0.32, y0 + h * 0.34),
             (x0 + w * 0.355, y0 + h * 0.40)], acc4, width=1.4)
    cv.line([(x0 + w * 0.565, y0 + h * 0.345), (x0 + w * 0.60, y0 + h * 0.28),
             (x0 + w * 0.635, y0 + h * 0.345)], acc4, width=1.4)
    # waves
    for r in range(2):
        wy = base + h * (0.09 + 0.09 * r)
        pts = []
        t = 0.0
        while t <= 1.0001:
            pts.append((x0 + w * 0.14 + (w * 0.72) * t,
                        wy + h * 0.028 * math.sin(t * math.pi * 3 + r * 1.9)))
            t += 0.04
        cv.line(pts, ink4, width=1.3)


# ---------------------------------------------------------------- portrait
def draw_portrait(out_w=256, out_h=332):
    """A flat-shaded ID portrait of the holder.

    Drawn in the original 340x440 design space onto an out_w x out_h
    canvas (units = design units).
    """
    size_w, size_h = 340.0, 440.0
    cv = Canvas(size_w, size_h, out_w / size_w, (226, 232, 238, 255))
    # photo backdrop: gentle vertical gradient
    for yy in range(cv.h):
        t = yy / cv.h
        c = (int(226 + (208 - 226) * t), int(232 + (216 - 232) * t),
             int(238 + (224 - 238) * t), 255)
        cv.fill_span(0, cv.w - 1, yy, c)

    cx = size_w / 2
    skin = rgba((216, 164, 124))
    skin_sh = rgba((196, 142, 104))
    hair = rgba((74, 54, 40))
    jacket = rgba((38, 44, 58))
    shirt = rgba((232, 230, 224))

    # shoulders / jacket
    cv.polygon([(cx - 128, size_h), (cx - 118, 356), (cx - 74, 322), (cx - 30, 312),
                (cx + 30, 312), (cx + 74, 322), (cx + 118, 356), (cx + 128, size_h)],
               fill=jacket)
    # shirt wedge + collar
    cv.polygon([(cx - 30, 312), (cx + 30, 312), (cx, 372)], fill=shirt)
    cv.polygon([(cx - 30, 312), (cx - 6, 336), (cx, 322), (cx - 14, 310)],
               fill=rgba((214, 212, 204)))
    cv.polygon([(cx + 30, 312), (cx + 6, 336), (cx, 322), (cx + 14, 310)],
               fill=rgba((214, 212, 204)))
    # neck
    cv.polygon([(cx - 24, 268), (cx + 24, 268), (cx + 20, 318), (cx - 20, 318)], fill=skin_sh)
    cv.ellipse((cx - 26, 250, cx + 26, 292), fill=skin_sh)
    # ears
    cv.ellipse((cx - 79, 168, cx - 58, 216), fill=skin)
    cv.ellipse((cx + 58, 168, cx + 79, 216), fill=skin)
    cv.ellipse((cx - 74, 178, cx - 62, 206), fill=skin_sh)
    cv.ellipse((cx + 62, 178, cx + 74, 206), fill=skin_sh)
    # head
    cv.ellipse((cx - 66, 62, cx + 66, 268), fill=skin)
    # jaw shaping: slightly narrower chin
    cv.polygon([(cx - 66, 190), (cx - 40, 262), (cx + 40, 262), (cx + 66, 190),
                (cx + 52, 250), (cx - 52, 250)], fill=skin)
    cv.ellipse((cx - 44, 208, cx + 44, 276), fill=skin)
    # hair: cap with a smooth hairline, slightly higher at the parting
    hairline = []
    for i in range(13):
        t = i / 12
        hairline.append((cx + 64 - 130 * t,
                         146 - 42 * (math.sin(math.pi * t ** 0.85) ** 1.1)))
    cv.polygon([(cx - 68, 150), (cx - 70, 96), (cx - 52, 58), (cx - 8, 40),
                (cx + 38, 44), (cx + 62, 66), (cx + 68, 104)] + hairline +
               [(cx - 68, 150)], fill=hair)
    cv.ellipse((cx - 68, 128, cx - 58, 190), fill=hair)
    cv.ellipse((cx + 58, 128, cx + 68, 190), fill=hair)
    # eyebrows
    cv.polygon([(cx - 46, 152), (cx - 18, 147), (cx - 17, 155), (cx - 45, 159)], fill=hair)
    cv.polygon([(cx + 18, 147), (cx + 46, 152), (cx + 45, 159), (cx + 17, 155)], fill=hair)
    # eyes
    for sgn in (-1, 1):
        ex = cx + sgn * 31
        cv.ellipse((ex - 15, 166, ex + 15, 180), fill=rgba((246, 244, 240)))
        cv.ellipse((ex - 6.5, 165, ex + 6.5, 181), fill=rgba((84, 62, 44)))
        cv.ellipse((ex - 3, 168, ex + 3, 178), fill=rgba((20, 16, 12)))
        cv.ellipse((ex - 1.2, 169.5, ex + 1.6, 173), fill=rgba((250, 250, 250)))
        cv.line([(ex - 15, 166), (ex + 15, 166)], rgba((120, 92, 70)), width=2.6)
    # nose: soft bridge shading + nostrils + base line
    cv.polygon([(cx + 2, 178), (cx + 9, 208), (cx + 11, 216), (cx - 2, 216)],
               fill=rgba((226, 178, 138)))
    cv.polygon([(cx - 3, 178), (cx - 8, 210), (cx - 10, 216), (cx - 1, 217)],
               fill=rgba((203, 148, 108)))
    cv.ellipse((cx - 9, 213, cx - 3.5, 218), fill=rgba((150, 104, 72)))
    cv.ellipse((cx + 3.5, 213, cx + 9, 218), fill=rgba((150, 104, 72)))
    # mouth
    cv.line([(cx - 17, 240), (cx + 17, 240)], rgba((150, 84, 74)), width=3.6)
    cv.line([(cx - 15, 243), (cx + 15, 243)], rgba((172, 104, 92)), width=2.2)
    # fine grain so it reads as a photograph, not a cartoon
    rng = random.Random(4417)
    for _ in range(7000):
        x = rng.randrange(cv.w)
        y = rng.randrange(cv.h)
        i = (y * cv.w + x) * 4
        dv = rng.randint(-7, 7)
        for c in range(3):
            cv.buf[i + c] = max(0, min(255, cv.buf[i + c] + dv))
    return cv


def draw_signature(cv, x, y, w, ink=(40, 40, 60)):
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
    cv.line(pts, rgba(ink), width=1.5)
    fl = [(x + w * 0.55 + w * 0.45 * t, y + 13 - 3 * math.sin(t * math.pi))
          for t in [i / 20 for i in range(21)]]
    cv.line(fl, rgba(ink), width=1.1)


# ---------------------------------------------------------------- stamps
def _ink_layer(w, h, draw_fn, seed):
    layer = Canvas(w, h, S, (0, 0, 0, 0))
    draw_fn(layer)
    # ink unevenness: erase speckles deterministically
    rng = random.Random(seed)
    lw, lh = layer.w, layer.h
    for _ in range(int(lw * lh / 90)):
        x = rng.randrange(lw)
        y = rng.randrange(lh)
        i = (y * lw + x) * 4
        if layer.buf[i + 3]:
            layer.buf[i + 3] = int(layer.buf[i + 3] * 0.35)
    return layer


def _place(img, layer, cx, cy, angle):
    rot = layer.rotate(angle)
    img.alpha_composite(rot, cx - (rot.w / rot.u) / 2.0, cy - (rot.h / rot.u) / 2.0)


def stamp_rect(img, cx, cy, w, h, color, title, place, date, sub, angle, alpha=168, seed=11):
    col = rgba(color, alpha)
    col_soft = rgba(color, int(alpha * 0.75))

    def draw(cv):
        cv.rect((4, 4, w - 4, h - 4), outline=col, width=2.2)
        cv.rect((9, 9, w - 9, h - 9), outline=col_soft, width=0.9)
        cv.text((w / 2, h * 0.10), title, 12.5, col, bold=True, anchor="ma", tracking=0.6)
        cv.text((w / 2, h * 0.33), place, 11, col, anchor="ma", tracking=0.4)
        cv.text((w / 2, h * 0.52), date, 15, col, bold=True, anchor="ma", tracking=0.8)
        cv.text((w / 2, h * 0.76), sub, 9.5, col, anchor="ma", tracking=0.5)

    _place(img, _ink_layer(w, h, draw, seed), cx, cy, angle)


def stamp_oval(img, cx, cy, w, h, color, title, place, date, sub, angle, alpha=165, seed=23):
    col = rgba(color, alpha)
    col_soft = rgba(color, int(alpha * 0.7))

    def draw(cv):
        cv.ellipse((4, 4, w - 4, h - 4), outline=col, width=2.2)
        cv.ellipse((10, 10, w - 10, h - 10), outline=col_soft, width=0.9)
        cv.text((w / 2, h * 0.20), title, 11.5, col, bold=True, anchor="ma", tracking=0.5)
        cv.text((w / 2, h * 0.38), place, 10.5, col, anchor="ma")
        cv.text((w / 2, h * 0.53), date, 14, col, bold=True, anchor="ma", tracking=0.7)
        cv.text((w / 2, h * 0.72), sub, 8.5, col, anchor="ma", tracking=0.4)

    _place(img, _ink_layer(w, h, draw, seed), cx, cy, angle)


def stamp_round(img, cx, cy, r, color, top, mid, bottom, angle, alpha=170, seed=37):
    col = rgba(color, alpha)
    col_soft = rgba(color, int(alpha * 0.7))
    d = 2 * r

    def draw(cv):
        cv.ellipse((3, 3, d - 3, d - 3), outline=col, width=2.0)
        cv.ellipse((9, 9, d - 9, d - 9), outline=col_soft, width=0.9)
        cv.text((r, r * 0.52), top, 9, col, bold=True, anchor="ma", tracking=0.4)
        cv.text((r, r * 0.86), mid, 12.5, col, bold=True, anchor="ma")
        cv.text((r, r * 1.22), bottom, 8.5, col, anchor="ma", tracking=0.4)

    _place(img, _ink_layer(d, d, draw, seed), cx, cy, angle)


# ---------------------------------------------------------------- pages
def field(cv, x, y, w, label, value, vsize=13.5, vbold=True):
    cv.text((x, y), label, 7.5, rgba(LABEL), tracking=0.3)
    cv.text((x, y + 11), value, vsize, rgba(INK), bold=vbold)
    cv.line([(x, y + 33), (x + w, y + 33)], rgba(RULE), width=0.8)


def data_page(img):
    x0, y0, x1, y1 = LP
    m = 24  # inner margin
    ix0, ix1 = x0 + m, x1 - m
    # header
    img.text((ix0, y0 + 20), COUNTRY_VL, 13, rgba(NAVY), bold=True, tracking=2.2)
    img.text((ix0, y0 + 40), COUNTRY_EN, 21, rgba(BURGUNDY), bold=True, tracking=1.2)
    img.text((ix1, y0 + 22), "PAS", 15, rgba(NAVY), bold=True, anchor="ra", tracking=1.5)
    img.text((ix1, y0 + 43), "PASSPORT", 11, rgba(NAVY_SOFT), bold=True, anchor="ra", tracking=1.5)
    draw_emblem(img, ix1 - 30, y0 + 86, 38)
    img.line([(ix0, y0 + 66), (ix1 - 76, y0 + 66)], rgba(NAVY), width=1.4)
    img.line([(ix0, y0 + 70), (ix1 - 76, y0 + 70)], rgba(GOLD), width=0.8)
    # photo
    ph_x, ph_y, ph_w, ph_h = ix0, y0 + 88, 128, 166
    photo = draw_portrait(int(ph_w * S), int(ph_h * S))
    img.alpha_composite(photo, ph_x, ph_y)
    img.rect((ph_x, ph_y, ph_x + ph_w, ph_y + ph_h), outline=rgba(NAVY_SOFT), width=1)
    # ghost image (security reprint of the portrait, faded, below the data)
    ghost = draw_portrait(104, 134)
    img.alpha_composite(ghost, ix1 - 64, y0 + 420, alpha_scale=34 / 255.0)
    # signature under photo
    img.text((ph_x, ph_y + ph_h + 8), "PODPIS / SIGNATURE", 7.5, rgba(LABEL), tracking=0.5)
    draw_signature(img, ph_x + 4, ph_y + ph_h + 26, 108)
    img.line([(ph_x, ph_y + ph_h + 46), (ph_x + ph_w, ph_y + ph_h + 46)], rgba(RULE), width=0.8)
    # fields column
    fx = ph_x + ph_w + 20
    fw = ix1 - fx
    fy = y0 + 84
    # type / code / number row
    field(img, fx, fy, 52, "TYP / TYPE", "P")
    field(img, fx + 62, fy, 62, "KÓD / CODE", CODE)
    field(img, fx + 134, fy, fw - 134, "ČÍSLO PASU / No.", DOC_NO)
    fy += 46
    field(img, fx, fy, fw, "PRIEZVISKO / SURNAME", SURNAME, vsize=15)
    fy += 46
    field(img, fx, fy, fw, "MENÁ / GIVEN NAMES", GIVEN, vsize=15)
    fy += 46
    field(img, fx, fy, fw, "OBČIANSTVO / NATIONALITY", NATIONALITY)
    fy += 46
    field(img, fx, fy, 168, "DÁTUM NARODENIA / DATE OF BIRTH", DOB)
    field(img, fx + 180, fy, fw - 180, "POHLAVIE / SEX", SEX)
    fy += 46
    field(img, fx, fy, fw, "MIESTO NARODENIA / PLACE OF BIRTH", BIRTHPLACE)
    fy += 46
    field(img, fx, fy, 168, "DÁTUM VYDANIA / DATE OF ISSUE", ISSUE)
    field(img, fx + 180, fy, fw - 180, "PLATNOSŤ DO / EXPIRY", EXPIRY)
    fy += 46
    field(img, fx, fy, fw, "VYDAL / AUTHORITY", AUTHORITY, vsize=11.5)
    # perforated document number down the outer edge
    img.text((x0 + 9, y1 - 120), DOC_NO, 9, rgba((150, 144, 128)), tracking=2)
    # machine-readable zone
    l1, l2 = mrz_lines()
    mz_y = y1 - 62
    img.line([(ix0, mz_y - 10), (ix1, mz_y - 10)], rgba(RULE), width=0.8)
    img.text((ix0, mz_y), l1, 16.5, rgba(INK), tracking=0.4)
    img.text((ix0, mz_y + 26), l2, 16.5, rgba(INK), tracking=0.4)


def visa_page(img):
    x0, y0, x1, y1 = RP
    m = 24
    ix0, ix1 = x0 + m, x1 - m
    # header
    img.text((ix0, y0 + 20), "VÍZA", 15, rgba(NAVY), bold=True, tracking=2)
    img.text((ix0 + 62, y0 + 24), "/ VISAS", 11, rgba(NAVY_SOFT), tracking=1)
    img.text((ix1, y0 + 20), "7", 14, rgba(NAVY_SOFT), bold=True, anchor="ra")
    img.line([(ix0, y0 + 52), (ix1, y0 + 52)], rgba(NAVY), width=1.2)
    img.line([(ix0, y0 + 56), (ix1, y0 + 56)], rgba(GOLD), width=0.7)

    # --- Aldanian transit visa (sticker) — the telling paperwork detail
    vx, vy, vw, vh = ix0 + 6, y0 + 74, 300, 128
    img.rect((vx, vy, vx + vw, vy + vh), outline=rgba(STAMP_VIOLET), width=1.6,
             fill=rgba((238, 232, 246), 110))
    img.rect((vx + 5, vy + 5, vx + vw - 5, vy + vh - 5), outline=rgba(STAMP_VIOLET), width=0.7)
    img.text((vx + 14, vy + 10), "REPUBLIC OF ALDANIA", 11.5, rgba(STAMP_VIOLET),
             bold=True, tracking=0.8)
    img.text((vx + 14, vy + 27), "TRANSIT VISA · TRANZITNÉ VÍZUM", 10, rgba(STAMP_VIOLET),
             bold=True, tracking=0.5)
    img.line([(vx + 14, vy + 46), (vx + vw - 14, vy + 46)], rgba(STAMP_VIOLET), width=0.7)
    rows = [
        ("HOLDER", "HAVELKA TOMÁŠ"),
        ("VALID", "72 HOURS FROM FIRST ENTRY"),
        ("CONDITION", "NOT VALID FOR EMPLOYMENT"),
        ("ISSUED AT", "OSTRANE · 22 MAY 2023"),
        ("VISA No.", "AL-TR 0114827"),
    ]
    ry = vy + 54
    for lab, val in rows:
        img.text((vx + 14, ry), lab, 8, rgba(LABEL), tracking=0.5)
        img.text((vx + 84, ry - 2), val, 10, rgba(INK), bold=True)
        ry += 14.5
    # consular fee stamp overlapping the visa's lower-right corner
    stamp_round(img, vx + vw - 4, vy + vh - 2, 33, STAMP_VIOLET,
                "FEE", "25 ALD", "PAID · 2023", -14, seed=41)

    # --- border stamps: two coherent trips, all after 14 MAR 2021 issue
    # trip 1: fly to Aldania and back, June 2023
    stamp_rect(img, ix0 + 102, y0 + 264, 168, 86, STAMP_BLUE,
               "VELEKIA", "OSTRANE INT'L AIRPORT", "03 JUN 2023", "DEPARTURE · ODCHOD", -4, seed=51)
    stamp_rect(img, ix0 + 322, y0 + 264, 168, 86, STAMP_RED,
               "ALDANIA", "BRANKA AIRPORT", "03 JUN 2023", "ARRIVAL", 3, seed=52)
    stamp_rect(img, ix0 + 102, y0 + 358, 168, 86, STAMP_DARKBLUE,
               "ALDANIA", "BRANKA AIRPORT", "17 JUN 2023", "DEPARTURE", 2, seed=53)
    stamp_rect(img, ix0 + 322, y0 + 358, 168, 86, STAMP_BLUE,
               "VELEKIA", "OSTRANE INT'L AIRPORT", "17 JUN 2023", "ARRIVAL · PRÍCHOD", -3, seed=54)
    # trip 2: over the High Pass to Sorvena, autumn 2025
    stamp_oval(img, ix0 + 100, y0 + 452, 160, 88, STAMP_TEAL,
               "VELEKIA", "VYSOKÝ PRIESMYK", "28 SEP 2025", "HIGH PASS · EXIT", -6, seed=61)
    stamp_oval(img, ix0 + 320, y0 + 452, 160, 88, STAMP_WINE,
               "SORVENA", "PORT ANSEL", "29 SEP 2025", "ARRIVAL", 4, seed=62)
    stamp_oval(img, ix0 + 100, y0 + 548, 160, 84, STAMP_DARKBLUE,
               "SORVENA", "PORT ANSEL", "05 OCT 2025", "DEPARTURE", -2, seed=63)
    # high-pass permit stamp beside the 2025 departure stamp
    stamp_rect(img, ix0 + 322, y0 + 548, 172, 86, STAMP_TEAL,
               "HIGH PASS PERMIT", "SEASON 2025 · VELEKIA", "PAID 40 VLR", "FOOT & VEHICLE",
               5, alpha=150, seed=64)


# ---------------------------------------------------------------- assembly
def paper_base():
    img = Canvas(OUT_W, OUT_H, S, (52, 58, 68, 255))
    # desk vignette (each band drawn at full step height — no striping)
    for yy in range(0, CH, 4):
        t = yy / CH
        c = int(58 - 16 * abs(t - 0.42))
        col = (c - 6, c, c + 8, 255)
        for y in range(yy, min(yy + 4, CH)):
            img.fill_span(0, CW - 1, y, col)
    # soft shadow under the spread (nested rounded rects fake the blur)
    for grow, a in ((10, 34), (6, 55), (3, 85)):
        sh = Canvas(OUT_W, OUT_H, S, (0, 0, 0, 0))
        sh.rounded_rect((SP_X0 + 6 - grow, SP_Y0 + 12 - grow,
                         SP_X1 + 8 + grow, SP_Y1 + 14 + grow), 14, (0, 0, 0, a))
        img.alpha_composite(sh, 0, 0)
    # the two pages
    for (x0, y0, x1, y1) in (LP, RP):
        pw_u, ph_u = x1 - x0, y1 - y0
        page = Canvas(pw_u, ph_u, S, rgba(PAPER_A))
        for yy in range(page.h):
            t = yy / page.h
            c = (int(PAPER_A[0] + (PAPER_B[0] - PAPER_A[0]) * t),
                 int(PAPER_A[1] + (PAPER_B[1] - PAPER_A[1]) * t),
                 int(PAPER_A[2] + (PAPER_B[2] - PAPER_A[2]) * t), 255)
            page.fill_span(0, page.w - 1, yy, c)
        # security guilloche fields (very fine, pale — a tint, not a scribble)
        guilloche(page, (18, 30, pw_u - 18, ph_u - 30), (172, 198, 186, 30),
                  n_waves=13, amp=6, phase=0.7)
        guilloche(page, (18, 30, pw_u - 18, ph_u - 30), (222, 190, 184, 20),
                  n_waves=11, amp=9, phase=2.4)
        img.alpha_composite(page, x0, y0)
    # page outlines + spine gutter
    img.rect((SP_X0, SP_Y0, SP_X1, SP_Y1), outline=rgba((120, 112, 96)), width=1)
    # spine gutter gradient, drawn column by column
    grad = Canvas(46, SP_Y1 - SP_Y0, S, (0, 0, 0, 0))
    for xx in range(grad.w):
        t = xx / grad.w
        a = int(105 * math.sin(t * math.pi) ** 1.5)
        col = (30, 26, 20, a)
        for y in range(grad.h):
            grad.fill_span(xx, xx, y, col)
    img.alpha_composite(grad, SPINE - 23, SP_Y0)
    img.line([(SPINE, SP_Y0 + 4), (SPINE, SP_Y1 - 4)], rgba((90, 82, 66)), width=0.8)
    return img


def main():
    img = paper_base()
    data_page(img)
    visa_page(img)
    # laminate sheen over the data page only
    img.polygon([(LP[0], LP[3]), (LP[0] + 190, LP[1]),
                 (LP[0] + 330, LP[1]), (LP[0] + 90, LP[3])],
                fill=(255, 255, 255, 16))
    rgb, w, h = img.downsample2()
    os.makedirs("/output", exist_ok=True)
    n = write_png("/output/entry.png", rgb, w, h)
    print("wrote /output/entry.png", (w, h), n, "bytes")


if __name__ == "__main__":
    main()
