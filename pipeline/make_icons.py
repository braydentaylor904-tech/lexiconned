"""Draw the site icons: the game's pencil, diagonal from bottom-left (eraser) to top-right (point), on a transparent background.

Each size is drawn on its own pixel grid (16 and 32 natively; the 180 apple-touch icon on a 45-pixel grid
scaled 4x), so every edge lands on whole pixels. Writes favicon-16.png, favicon-32.png, favicon.ico and
apple-touch-icon.png to the site root. No dependencies: PNGs are encoded with zlib directly.

    python pipeline/make_icons.py [--preview DIR]   (--preview also writes 12x enlargements for checking)
"""
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def hexc(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


# Same colours as drawPencil() and the desk in index.html.
O = hexc("#3a2a10")
ERASER = [hexc("#f0a3ad"), hexc("#e0808c"), hexc("#b05b67")]
BAND = [hexc("#e3e7ec"), hexc("#a5abb4"), hexc("#6c727b")]
BODY = [hexc("#fbe08a"), hexc("#efc044"), hexc("#e2ac2e"), hexc("#b7832a")]
WOOD_TIP = [hexc("#f2d6ad"), hexc("#d9b383")]
GRAPHITE = hexc("#3b3b42")

# Per grid size: half-width of the pencil (in diagonal lines) and where each part starts along the pencil.
# Positions are in "a" units: a = x + (N-1-y), which grows by 2 for each pixel step along the diagonal.
SPECS = {
    16: {"w": 2, "parts": [("eraser", 4), ("band", 9), ("body", 12), ("wood", 19), ("lead", 24), ("end", 27)], },
    32: {"w": 4, "parts": [("eraser", 9), ("band", 19), ("body", 25), ("wood", 45), ("lead", 53), ("end", 57)]},
    45: {"w": 5, "parts": [("eraser", 13), ("band", 26), ("body", 34), ("wood", 64), ("lead", 75), ("end", 80)]},
}


def draw(n):
    spec = SPECS[n]
    w, parts = spec["w"], spec["parts"]
    bounds = {name: start for name, start in parts}
    a0, wood, lead, end = bounds["eraser"], bounds["wood"], bounds["lead"], bounds["end"]

    img = [[None] * n for _ in range(n)]    # transparent: just the pencil

    def half_width(a):
        if a < wood:
            return w
        if a >= lead:
            return max(0, round(1 * (end - a) / (end - lead))) if n > 16 else 0
        return max(1, round(w * (lead - a) / (lead - wood) + .3))

    def part(a):
        name = None
        for nm, start in parts:
            if a >= start:
                name = nm
        return name

    shape = {}
    for y in range(n):
        yf = n - 1 - y
        for x in range(n):
            a, c = x + yf, x - yf
            if a < a0 or a >= end:
                continue
            hw = half_width(a)
            if abs(c) > hw:
                continue
            p = part(a)
            t = (c + hw) / (2 * hw) if hw else .5          # 0 = upper-left (lit) edge, 1 = lower-right (shade)
            if p == "eraser":
                col = ERASER[0] if t < .3 else ERASER[2] if t > .75 else ERASER[1]
            elif p == "band":
                col = BAND[0] if t < .3 else BAND[2] if t > .75 else BAND[1]
                if n > 16 and (a - bounds["band"]) % 4 == 2:
                    col = BAND[2]
            elif p == "body":
                col = BODY[0] if t < .25 else BODY[3] if t > .8 else BODY[1] if t < .55 else BODY[2]
            elif p == "wood":
                col = WOOD_TIP[0] if t < .45 else WOOD_TIP[1]
            else:
                col = GRAPHITE
            shape[(x, y)] = col

    # Outline: empty pixels touching the pencil on a side.
    outline = {(x + dx, y + dy) for (x, y) in shape for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
               if (x + dx, y + dy) not in shape and 0 <= x + dx < n and 0 <= y + dy < n}
    for (x, y) in outline:
        img[y][x] = O
    for (x, y), col in shape.items():
        img[y][x] = col
    return img


def scale(img, k):
    return [[px for px in row for _ in range(k)] for row in img for _ in range(k)]


def png(img):
    h, w = len(img), len(img[0])
    raw = b"".join(b"\x00" + bytes(v for px in row for v in ((*px, 255) if px else (0, 0, 0, 0))) for row in img)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def ico(pngs):
    """An .ico holding PNG images (supported by every current browser)."""
    head = struct.pack("<HHH", 0, 1, len(pngs))
    off = 6 + 16 * len(pngs)
    entries, data = b"", b""
    for size, blob in pngs:
        entries += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(blob), off + len(data))
        data += blob
    return head + entries + data


def main():
    i16, i32, i45 = draw(16), draw(32), draw(45)
    p16, p32 = png(i16), png(i32)
    (ROOT / "favicon-16.png").write_bytes(p16)
    (ROOT / "favicon-32.png").write_bytes(p32)
    (ROOT / "favicon.ico").write_bytes(ico([(16, p16), (32, p32)]))
    (ROOT / "apple-touch-icon.png").write_bytes(png(scale(i45, 4)))
    if "--preview" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--preview") + 1])
        out.mkdir(parents=True, exist_ok=True)
        for name, im, k in (("p16.png", i16, 16), ("p32.png", i32, 8), ("p180.png", scale(i45, 4), 1)):
            (out / name).write_bytes(png(scale(im, k)))
    print("wrote favicon-16.png, favicon-32.png, favicon.ico, apple-touch-icon.png")


if __name__ == "__main__":
    main()
