#!/usr/bin/env python3
"""Render a house app icon.

    python3 icons/make-icon.py --glyph <name> --out AppIcon.icns   (names: --help)
    python3 icons/make-icon.py --glyph bolt --png preview.png --size 256
    python3 icons/make-icon.py --glyph bolt --iconset Out.iconset   (PNGs only, no iconutil)

Rule (DESIGN.md): rounded square at the macOS squircle radius, one flat
near-black fill, one white glyph at a fixed optical size. No gradients, no
letters. Values come from tokens.json `icon`. Rendering: PIL at 4x
supersample, then a Lanczos downsample per size.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
TOKENS = json.loads((ROOT / "tokens.json").read_text())["icon"]
SS = 4  # supersample factor

ICONSET_SIZES = [16, 32, 128, 256, 512]


# --- glyph paths: unit square [0,1]x[0,1], y down, drawn inside the glyph box.
def glyph_bolt(d, box, fill):
    x0, y0, w, h = box
    pts = [(0.60, 0.0), (0.12, 0.56), (0.44, 0.56), (0.38, 1.0), (0.88, 0.42), (0.56, 0.42)]
    d.polygon([(x0 + px * w, y0 + py * h) for px, py in pts], fill=fill)


def glyph_waveform(d, box, fill):
    x0, y0, w, h = box
    heights = [0.34, 0.68, 1.0, 0.56, 0.80, 0.42]
    n = len(heights)
    bar_w = w / (2 * n - 1)
    for i, hh in enumerate(heights):
        bx = x0 + i * 2 * bar_w
        bh = h * hh
        by = y0 + (h - bh) / 2
        d.rounded_rectangle([bx, by, bx + bar_w, by + bh], radius=bar_w / 2, fill=fill)


def glyph_record(d, box, fill):
    x0, y0, w, h = box
    ring = w * 0.075
    d.ellipse([x0, y0, x0 + w, y0 + h], outline=fill, width=int(ring))
    r = w * 0.30
    cx, cy = x0 + w / 2, y0 + h / 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


def glyph_mic(d, box, fill):
    x0, y0, w, h = box
    cw = w * 0.36
    cx = x0 + w / 2
    d.rounded_rectangle([cx - cw / 2, y0, cx + cw / 2, y0 + h * 0.62], radius=cw / 2, fill=fill)
    stroke = int(w * 0.075)
    aw = w * 0.62
    d.arc([cx - aw / 2, y0 + h * 0.18, cx + aw / 2, y0 + h * 0.80], start=0, end=180, fill=fill, width=stroke)
    d.rectangle([cx - stroke / 2, y0 + h * 0.80 - stroke / 2, cx + stroke / 2, y0 + h * 0.90], fill=fill)
    d.rectangle([cx - w * 0.20, y0 + h * 0.90, cx + w * 0.20, y0 + h * 0.90 + stroke], fill=fill)


def glyph_cotype(d, box, fill):
    """Text-cursor I-beam: the verb is 'complete what you are typing'."""
    x0, y0, w, h = box
    stroke = w * 0.11
    # the I-beam sits left of centre so beam + dots read as one centred mark
    cx = x0 + w * 0.34
    # stem
    d.rounded_rectangle([cx - stroke / 2, y0 + h * 0.06, cx + stroke / 2, y0 + h * 0.94], radius=stroke / 2, fill=fill)
    # serifs, top and bottom, each a pair of short bars leaning out from the stem
    arm = w * 0.20
    for y in (y0, y0 + h - stroke):
        d.rounded_rectangle([cx - arm - stroke * 0.25, y, cx - stroke * 0.25, y + stroke], radius=stroke / 2, fill=fill)
        d.rounded_rectangle([cx + stroke * 0.25, y, cx + arm + stroke * 0.25, y + stroke], radius=stroke / 2, fill=fill)
    # three ghost dots trailing to the right: the completion waiting to land
    dot = w * 0.10
    gy = y0 + h * 0.60
    for i in range(3):
        gx = cx + w * 0.24 + i * (dot * 2.1)
        d.ellipse([gx, gy - dot / 2, gx + dot, gy + dot / 2], fill=fill)


def glyph_models(d, box, fill):
    """A chip: the local model daemon that other apps call."""
    x0, y0, w, h = box
    stroke = int(w * 0.075)
    pin = w * 0.055
    pin_len = w * 0.13
    body = [x0 + pin_len, y0 + pin_len, x0 + w - pin_len, y0 + h - pin_len]
    d.rounded_rectangle(body, radius=w * 0.10, outline=fill, width=stroke)
    inner = w * 0.16
    d.rounded_rectangle([body[0] + inner, body[1] + inner, body[2] - inner, body[3] - inner], radius=w * 0.05, fill=fill)
    # pins: three per side
    for t in (0.32, 0.50, 0.68):
        px = x0 + w * t
        py = y0 + h * t
        d.rounded_rectangle([px - pin / 2, y0, px + pin / 2, y0 + pin_len], radius=pin / 2, fill=fill)
        d.rounded_rectangle([px - pin / 2, y0 + h - pin_len, px + pin / 2, y0 + h], radius=pin / 2, fill=fill)
        d.rounded_rectangle([x0, py - pin / 2, x0 + pin_len, py + pin / 2], radius=pin / 2, fill=fill)
        d.rounded_rectangle([x0 + w - pin_len, py - pin / 2, x0 + w, py + pin / 2], radius=pin / 2, fill=fill)


def glyph_memory(d, box, fill):
    """A bookmark: keep this, find it again."""
    x0, y0, w, h = box
    bw = w * 0.62
    x = x0 + (w - bw) / 2
    top = y0 + h * 0.04
    bottom = y0 + h * 0.96
    notch = h * 0.22
    r = bw * 0.16
    # body with rounded top corners, then a V notch cut out of the bottom
    d.rounded_rectangle([x, top, x + bw, bottom], radius=r, fill=fill)
    d.rectangle([x, bottom - r - 1, x + bw, bottom], fill=fill)
    cx = x + bw / 2
    # the notch is painted in the tile colour, not cleared, so the tile stays whole
    tile = tuple(int(round(c)) for c in TOKENS["fill"][:3]) + (int(round(TOKENS["fill"][3] * 255)),)
    d.polygon([(x - 1, bottom + 1), (cx, bottom - notch), (x + bw + 1, bottom + 1)], fill=tile)


def glyph_gauge(d, box, fill):
    """A gauge: an open arc and a needle, how much of the window is used."""
    import math
    x0, y0, w, h = box
    cx = x0 + w / 2
    cy = y0 + h * 0.56
    r = w * 0.46
    stroke = w * 0.13
    # the dial: a 240-degree arc, open at the bottom
    d.arc([cx - r, cy - r, cx + r, cy + r], start=150, end=390, fill=fill, width=int(round(stroke)))
    # the needle: a rounded bar from the hub toward two o'clock
    angle = math.radians(-38)
    length = r * 0.72
    nw = stroke * 0.85
    tip = (cx + math.cos(angle) * length, cy + math.sin(angle) * length)
    px, py = -math.sin(angle) * nw / 2, math.cos(angle) * nw / 2
    d.polygon([(cx + px, cy + py), (cx - px, cy - py), (tip[0] - px, tip[1] - py), (tip[0] + px, tip[1] + py)], fill=fill)
    d.ellipse([tip[0] - nw / 2, tip[1] - nw / 2, tip[0] + nw / 2, tip[1] + nw / 2], fill=fill)
    # the hub
    hub = stroke * 1.1
    d.ellipse([cx - hub, cy - hub, cx + hub, cy + hub], fill=fill)


def glyph_tray(d, box, fill):
    """A tray, as SF Symbols draws it: an outlined box and a lip with a dip
    where a sheet sits. Proposals wait here for a verdict (Chief of Staff)."""
    x0, y0, w, h = box
    stroke = w * 0.10
    left, right = x0 + w * 0.02, x0 + w * 0.98
    top, bottom = y0 + h * 0.12, y0 + h * 0.88
    d.rounded_rectangle([left, top, right, bottom], radius=w * 0.20, outline=fill, width=int(round(stroke)))
    lip = y0 + h * 0.54
    dip = y0 + h * 0.70
    pts = [(left + stroke / 2, lip), (x0 + w * 0.30, lip), (x0 + w * 0.38, dip), (x0 + w * 0.62, dip),
           (x0 + w * 0.70, lip), (right - stroke / 2, lip)]
    d.line(pts, fill=fill, width=int(round(stroke)), joint="curve")
    # round the two bends of the dip so the line reads as one stroke
    for px, py in pts[1:5]:
        d.ellipse([px - stroke / 2, py - stroke / 2, px + stroke / 2, py + stroke / 2], fill=fill)


GLYPHS = {
    "bolt": glyph_bolt,
    "memory": glyph_memory,
    "waveform": glyph_waveform,
    "record": glyph_record,
    "mic": glyph_mic,
    "cotype": glyph_cotype,
    "models": glyph_models,
    "gauge": glyph_gauge,
    "tray": glyph_tray,
}


def render_master(glyph):
    side = TOKENS["canvas"] * SS
    inset = TOKENS["inset"] * SS
    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    tile = side - 2 * inset
    fill = tuple(int(round(c)) for c in TOKENS["fill"][:3]) + (int(round(TOKENS["fill"][3] * 255)),)
    d.rounded_rectangle([inset, inset, inset + tile, inset + tile], radius=tile * TOKENS["cornerRatio"], fill=fill)
    g = tile * TOKENS["glyphRatio"]
    gx = inset + (tile - g) / 2
    gy = inset + (tile - g) / 2
    white = tuple(int(round(c)) for c in TOKENS["glyph"][:3]) + (int(round(TOKENS["glyph"][3] * 255)),)
    GLYPHS[glyph](d, (gx, gy, g, g), white)
    return img


def downsample(master, size):
    return master.resize((size, size), Image.LANCZOS)


def write_iconset(master, iconset):
    iconset.mkdir(parents=True, exist_ok=True)
    for s in ICONSET_SIZES:
        downsample(master, s).save(iconset / f"icon_{s}x{s}.png")
        downsample(master, s * 2).save(iconset / f"icon_{s}x{s}@2x.png")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glyph", required=True, choices=sorted(GLYPHS))
    ap.add_argument("--out", help=".icns path (needs iconutil)")
    ap.add_argument("--iconset", help="write an .iconset directory")
    ap.add_argument("--png", help="write one PNG preview")
    ap.add_argument("--size", type=int, default=256, help="PNG preview size")
    a = ap.parse_args()
    master = render_master(a.glyph)
    if a.png:
        downsample(master, a.size).save(a.png)
    if a.iconset:
        write_iconset(master, Path(a.iconset))
    if a.out:
        tmp = Path(tempfile.mkdtemp(prefix="house-icon-"))
        try:
            write_iconset(master, tmp / "AppIcon.iconset")
            subprocess.run(["iconutil", "-c", "icns", str(tmp / "AppIcon.iconset"), "-o", a.out], check=True)
        finally:
            shutil.rmtree(tmp)
    if not (a.png or a.iconset or a.out):
        sys.exit("nothing to do: pass --out, --iconset, or --png")


if __name__ == "__main__":
    main()
