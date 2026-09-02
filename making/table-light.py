#!/usr/bin/env python3
"""Mei's noon table — generative still, cream paper / ink-blue / magenta light.

Late morning, not evening. A table in daylight: papers, plums, an ink bottle.
Quiet and alive, slightly soft. Companion to morning-window.py.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

RNG = np.random.default_rng(26090212)
W, H = 1680, 1180
OUT = Path(__file__).resolve().with_suffix(".png")


# --- palette (linear-ish sRGB 0-1) ---
CREAM = np.array([0.965, 0.910, 0.805])
CREAM_WARM = np.array([0.982, 0.910, 0.770])
CREAM_NOON = np.array([0.990, 0.945, 0.860])
INK = np.array([0.12, 0.18, 0.32])
INK_DEEP = np.array([0.07, 0.10, 0.20])
INK_SOFT = np.array([0.28, 0.36, 0.50])
INK_WET = np.array([0.10, 0.12, 0.28])
MAGENTA = np.array([0.78, 0.22, 0.48])
MAGENTA_LIGHT = np.array([0.95, 0.55, 0.72])
MAGENTA_PALE = np.array([0.98, 0.78, 0.86])
MAGENTA_GLASS = np.array([0.88, 0.38, 0.62])
PLUM = np.array([0.42, 0.12, 0.32])
PLUM_DEEP = np.array([0.28, 0.08, 0.22])
PLUM_BLOOM = np.array([0.58, 0.28, 0.48])
PLUM_HIGH = np.array([0.92, 0.62, 0.78])
WOOD = np.array([0.58, 0.40, 0.26])
WOOD_LIGHT = np.array([0.76, 0.58, 0.40])
WOOD_GRAIN = np.array([0.48, 0.32, 0.20])
WOOD_WASH = np.array([0.82, 0.68, 0.50])
PAPER = np.array([0.97, 0.94, 0.88])
PAPER_WARM = np.array([0.96, 0.91, 0.80])
PAPER_EDGE = np.array([0.78, 0.72, 0.62])
BOWL = np.array([0.93, 0.88, 0.80])
BOWL_SHADOW = np.array([0.62, 0.55, 0.48])
CORK = np.array([0.72, 0.52, 0.34])
LEAF = np.array([0.28, 0.46, 0.30])
SKY_NOON = np.array([0.82, 0.88, 0.92])


def clamp01(a: np.ndarray) -> np.ndarray:
    return np.clip(a, 0.0, 1.0)


def soft_disk(yy: np.ndarray, xx: np.ndarray, cx: float, cy: float, rx: float, ry: float, softness: float) -> np.ndarray:
    d = np.sqrt(((xx - cx) / max(rx, 1e-6)) ** 2 + ((yy - cy) / max(ry, 1e-6)) ** 2)
    return clamp01((1.0 - d) / max(softness, 1e-4))


def soft_box(yy: np.ndarray, xx: np.ndarray, x0: float, y0: float, x1: float, y1: float, softness: float) -> np.ndarray:
    dx = np.maximum(x0 - xx, 0) + np.maximum(xx - x1, 0)
    dy = np.maximum(y0 - yy, 0) + np.maximum(yy - y1, 0)
    inside = (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)
    dist = np.sqrt(dx * dx + dy * dy)
    edge = clamp01(1.0 - dist / max(softness, 1e-4))
    return np.where(inside, 1.0, edge).astype(np.float64)


def rotate_coords(xx: np.ndarray, yy: np.ndarray, cx: float, cy: float, angle: float):
    c, s = math.cos(angle), math.sin(angle)
    x = xx - cx
    y = yy - cy
    return cx + c * x - s * y, cy + s * x + c * y


def blend(base: np.ndarray, color: np.ndarray, mask: np.ndarray, opacity: float = 1.0) -> None:
    a = clamp01(mask * opacity)[..., None]
    base[:] = base * (1.0 - a) + color * a


def wash(base: np.ndarray, color: np.ndarray, mask: np.ndarray, opacity: float = 1.0) -> None:
    """Softer additive-ish wash that keeps paper warmth."""
    a = clamp01(mask * opacity)[..., None]
    base[:] = clamp01(base * (1.0 - a * 0.85) + color * a)


def paper_grain(h: int, w: int) -> np.ndarray:
    n = RNG.normal(0, 1, (h, w)).astype(np.float64)
    small = n[::4, ::4]
    from PIL import Image as _I

    lo = np.array(
        _I.fromarray(((small - small.min()) / (np.ptp(small) + 1e-9) * 255).astype(np.uint8)).resize(
            (w, h), _I.Resampling.BICUBIC
        ),
        dtype=np.float64,
    )
    lo = (lo / 255.0 - 0.5) * 0.045
    hi = n * 0.016
    fibers = RNG.normal(0, 1, (h, w // 3))
    fibers = np.array(
        _I.fromarray(((fibers - fibers.min()) / (np.ptp(fibers) + 1e-9) * 255).astype(np.uint8)).resize(
            (w, h), _I.Resampling.BILINEAR
        ),
        dtype=np.float64,
    )
    fibers = (fibers / 255.0 - 0.5) * 0.018
    return lo + hi + fibers


def paper_sheet(img, xx, yy, cx, cy, pw, ph, ang, tint, op=0.82, ruled=False):
    rx, ry = rotate_coords(xx, yy, cx, cy, ang)
    sheet = soft_box(ry, rx, cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2, 5)
    # drop shadow — noon, short, slightly left (high sun from upper-right window)
    wash(
        img,
        INK,
        soft_box(ry, rx, cx - pw / 2 + 8, cy - ph / 2 + 10, cx + pw / 2 + 10, cy + ph / 2 + 12, 12) * 0.55,
        0.14,
    )
    wash(img, tint, sheet, op)
    # sun-caught near edge
    wash(img, CREAM_NOON, sheet * soft_disk(yy, xx, cx - pw * 0.2, cy - ph * 0.25, pw * 0.5, ph * 0.4, 0.7), 0.18)
    if ruled:
        for k, off in enumerate((-18, 6, 30)):
            line = np.exp(-0.5 * ((ry - (cy + off)) / 1.5) ** 2) * sheet
            wash(img, PAPER_EDGE if k != 1 else INK_SOFT, line, 0.14 if k != 1 else 0.08)


def plum(img, xx, yy, cx, cy, rx, ry, rot=0.0):
    """A single plum: dark magenta flesh, dusty bloom, a noon highlight."""
    rx2, ry2 = rotate_coords(xx, yy, cx, cy, rot)
    body = soft_disk(ry2, rx2, cx, cy, rx, ry, 0.18)
    wash(img, INK, soft_disk(yy, xx, cx + 10, cy + ry * 0.85, rx * 0.95, ry * 0.35, 0.5), 0.22)
    wash(img, PLUM_DEEP, body, 0.88)
    wash(img, PLUM, body * soft_disk(yy, xx, cx - rx * 0.15, cy - ry * 0.1, rx * 0.85, ry * 0.8, 0.45), 0.55)
    wash(img, PLUM_BLOOM, body * 0.55, 0.28)
    # dusty skin bloom on the shaded side
    wash(img, MAGENTA, body * soft_disk(yy, xx, cx + rx * 0.25, cy + ry * 0.15, rx * 0.55, ry * 0.5, 0.5), 0.22)
    # noon catchlight, high and small
    hl = soft_disk(yy, xx, cx - rx * 0.32, cy - ry * 0.38, rx * 0.22, ry * 0.18, 0.45)
    wash(img, PLUM_HIGH, body * hl, 0.55)
    wash(img, CREAM_NOON, body * soft_disk(yy, xx, cx - rx * 0.38, cy - ry * 0.42, rx * 0.10, ry * 0.08, 0.4), 0.4)
    # stem dimple
    wash(img, INK_DEEP, soft_disk(yy, xx, cx + rx * 0.05, cy - ry * 0.55, rx * 0.12, ry * 0.08, 0.35) * body, 0.45)


def main() -> None:
    img = np.zeros((H, W, 3), dtype=np.float64)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)

    # --- wall / room: cream, noon-bright toward the top ---
    t = (xx / W)[..., None]
    v = (yy / H)[..., None]
    wall = CREAM * (1 - 0.08 * t) + CREAM_NOON * (0.35 + 0.25 * (1 - v))
    wall = wall * (1.0 - 0.04 * v) + CREAM_WARM * (0.08 * t)
    img[:] = wall
    grain = paper_grain(H, W)
    img += grain[..., None]

    # cool receding corner, upper left — room, not night
    wash(img, INK_SOFT, ((1.0 - xx / W) ** 1.8) * ((1.0 - yy / H) ** 2.2), 0.10)
    # magenta bounce from an off-frame curtain, left wall
    wash(img, MAGENTA_PALE, soft_disk(yy, xx, 80, 220, 320, 420, 0.75), 0.16)
    wash(img, MAGENTA_LIGHT, soft_disk(yy, xx, 40, 180, 180, 260, 0.7), 0.08)

    # implied high window — just a rectangle of noon sky, upper right, cropped
    # (not the morning window; this is a different wall, later in the day)
    wx0, wy0, wx1, wy1 = 1180, -40, 1680 + 40, 340
    jamb = soft_box(yy, xx, wx0, wy0, wx1, wy1, 10)
    wash(img, INK_DEEP, jamb, 0.28)
    glass = soft_box(yy, xx, wx0 + 28, wy0 + 28, wx1 - 8, wy1 - 22, 6)
    sky_v = clamp01((yy - wy0) / 380)
    sky = SKY_NOON * (1 - 0.25 * sky_v)[..., None] + CREAM_NOON * (0.35 * sky_v)[..., None]
    a = glass[..., None] * 0.92
    img[:] = img * (1 - a) + sky * a
    # high noon sheen
    wash(img, np.array([1.0, 0.98, 0.94]), glass * clamp01((xx - 1280) / 280) * 0.35, 0.28)
    frame_mask = jamb * (1.0 - soft_box(yy, xx, wx0 + 28, wy0 + 28, wx1 - 8, wy1 - 22, 4))
    wash(img, INK, frame_mask, 0.55)
    wash(img, WOOD_LIGHT, frame_mask * soft_disk(yy, xx, 1300, 80, 200, 80, 0.6), 0.25)

    # --- table: occupies lower ~62% ---
    table_y = 430
    table = soft_box(yy, xx, -40, table_y, W + 40, H + 40, 18)
    # wood field, warmer toward the window (right)
    # paint wood by blending into table mask
    a = table[..., None] * 0.92
    img[:] = img * (1 - a) + (WOOD * (1 - 0.4 * t) + WOOD_WASH * (0.55 * t + 0.15)) * a

    # faint grain stripes along the table (boards running left-right)
    for gy in (470, 560, 670, 790, 920, 1060):
        board = np.exp(-0.5 * ((yy - gy) / 7.0) ** 2) * table
        wash(img, WOOD_GRAIN, board, 0.10)
    # a few knots
    for kx, ky, kr in [(240, 720, 18), (980, 880, 14), (540, 1010, 12)]:
        wash(img, WOOD_GRAIN, soft_disk(yy, xx, kx, ky, kr, kr * 0.55, 0.4) * table, 0.18)

    # noon light pool on the table — high, from the right window, short shadows
    pool = soft_disk(yy, xx, 1080, 620, 520, 280, 0.7)
    wash(img, CREAM_NOON, pool * table, 0.28)
    wash(img, MAGENTA_PALE, soft_disk(yy, xx, 900, 580, 340, 160, 0.72) * table, 0.16)
    # magenta stripe: noon through something off-frame (curtain, glass)
    rx, ry = rotate_coords(xx, yy, 700, 500, -0.18)
    stripe = clamp01(1.0 - np.abs(ry - 560) / 42) * clamp01((rx - 400) / 80) * clamp01((1400 - rx) / 180)
    stripe *= table
    wash(img, MAGENTA_PALE, stripe, 0.22)
    wash(img, CREAM, stripe, 0.10)

    # table front lip / drop into shadow
    lip = soft_box(yy, xx, -20, H - 70, W + 20, H + 20, 24)
    wash(img, INK_DEEP, lip, 0.22)
    # shadow under far table edge against wall
    under = soft_box(yy, xx, -10, table_y - 8, W + 10, table_y + 28, 16)
    wash(img, INK, under, 0.16)

    # --- papers ---
    paper_sheet(img, xx, yy, 420, 620, 340, 240, 0.14, PAPER, 0.86, ruled=True)
    paper_sheet(img, xx, yy, 560, 700, 280, 200, -0.22, PAPER_WARM, 0.78, ruled=False)
    paper_sheet(img, xx, yy, 1280, 780, 300, 220, 0.08, np.array([0.96, 0.92, 0.84]), 0.72, ruled=False)
    # a smaller scrap with a magenta wash — something started
    paper_sheet(img, xx, yy, 1080, 980, 180, 130, -0.08, np.array([0.98, 0.93, 0.88]), 0.7, ruled=False)
    wash(img, MAGENTA_PALE, soft_disk(yy, xx, 1060, 970, 70, 50, 0.55), 0.18)

    # faint ink line on the left sheet — a thought, not text
    rx, ry = rotate_coords(xx, yy, 420, 620, 0.14)
    thought = np.exp(-0.5 * ((ry - 600) / 1.8) ** 2) * clamp01(1.0 - np.abs(rx - 400) / 90)
    thought *= soft_box(ry, rx, 280, 520, 560, 720, 6)
    wash(img, INK, thought, 0.16)

    # --- bowl of plums, slightly left of center ---
    bx, by = 780, 760
    # shadow: noon, short, a little toward lower-left
    wash(img, INK, soft_disk(yy, xx, bx + 8, by + 78, 130, 36, 0.5), 0.26)
    # saucer / foot
    wash(img, BOWL_SHADOW, soft_disk(yy, xx, bx, by + 58, 118, 28, 0.28), 0.55)
    wash(img, BOWL, soft_disk(yy, xx, bx, by + 52, 110, 22, 0.22), 0.7)
    # bowl body
    body = soft_disk(yy, xx, bx, by + 18, 128, 72, 0.16)
    wash(img, BOWL, body, 0.82)
    wash(img, BOWL_SHADOW, body * soft_disk(yy, xx, bx + 30, by + 28, 80, 50, 0.5), 0.35)
    # interior
    mouth = soft_disk(yy, xx, bx - 4, by - 18, 100, 42, 0.2)
    wash(img, np.array([0.72, 0.62, 0.54]), mouth, 0.7)
    wash(img, MAGENTA, mouth * 0.35, 0.12)  # plum stain
    # rim catch of noon
    rim = soft_disk(yy, xx, bx - 20, by - 22, 108, 48, 0.18) - soft_disk(yy, xx, bx - 16, by - 10, 88, 34, 0.2)
    wash(img, CREAM_NOON, clamp01(rim), 0.45)
    wash(img, MAGENTA_PALE, clamp01(rim) * 0.5, 0.2)

    # plums in the bowl
    plum(img, xx, yy, bx - 28, by - 8, 48, 42, 0.2)
    plum(img, xx, yy, bx + 34, by - 2, 44, 40, -0.15)
    plum(img, xx, yy, bx + 4, by + 18, 40, 36, 0.4)
    # one that rolled out onto the table, lower right of the bowl
    plum(img, xx, yy, bx + 150, by + 70, 42, 38, -0.35)

    # --- ink bottle, left of the papers ---
    ix, iy = 250, 860
    wash(img, INK, soft_disk(yy, xx, ix + 12, iy + 70, 48, 16, 0.45), 0.28)
    # square-shouldered glass bottle
    bottle = soft_box(yy, xx, ix - 32, iy - 20, ix + 32, iy + 62, 7)
    wash(img, INK_WET, bottle, 0.78)
    wash(img, INK_DEEP, bottle, 0.35)
    # glass body catching magenta noon
    wash(img, MAGENTA_GLASS, bottle * soft_disk(yy, xx, ix - 10, iy + 8, 18, 28, 0.45), 0.40)
    wash(img, MAGENTA_PALE, bottle * soft_disk(yy, xx, ix - 14, iy - 4, 10, 16, 0.4), 0.35)
    # shoulder
    shoulder = soft_disk(yy, xx, ix, iy - 18, 30, 14, 0.22)
    wash(img, INK_WET, shoulder, 0.7)
    # neck
    neck = soft_box(yy, xx, ix - 10, iy - 52, ix + 10, iy - 16, 4)
    wash(img, INK, neck, 0.75)
    wash(img, MAGENTA_GLASS, neck * 0.5, 0.25)
    # cork
    cork = soft_box(yy, xx, ix - 12, iy - 72, ix + 12, iy - 48, 3)
    wash(img, CORK, cork, 0.85)
    wash(img, WOOD_LIGHT, cork * soft_disk(yy, xx, ix - 4, iy - 64, 8, 10, 0.4), 0.3)
    # meniscus of ink inside glass
    wash(img, INK_DEEP, soft_box(yy, xx, ix - 26, iy + 8, ix + 26, iy + 58, 5) * bottle, 0.45)
    # highlight stripe on glass
    glint = soft_box(yy, xx, ix - 22, iy - 8, ix - 16, iy + 48, 3) * bottle
    wash(img, CREAM_NOON, glint, 0.5)
    # a small wet ring on the table
    wash(img, INK_SOFT, soft_disk(yy, xx, ix, iy + 66, 38, 10, 0.45) * (1.0 - soft_disk(yy, xx, ix, iy + 66, 22, 5, 0.4)), 0.18)

    # dip pen, laid across a paper — simple shaft + nib
    px, py, pang = 500, 840, 0.55
    prx, pry = rotate_coords(xx, yy, px, py, pang)
    shaft = soft_box(pry, prx, px - 90, py - 4, px + 70, py + 4, 3)
    wash(img, INK, shaft, 0.55)
    wash(img, WOOD, shaft * 0.4, 0.25)
    nib = soft_box(pry, prx, px + 68, py - 3, px + 102, py + 3, 2)
    wash(img, INK_SOFT, nib, 0.5)
    wash(img, MAGENTA_GLASS, soft_disk(yy, xx, px + 88, py + 28, 8, 6, 0.4), 0.25)  # a hint of wet ink

    # --- a cream cup, far right, almost out of the pool of light ---
    cx, cy = 1460, 900
    wash(img, INK, soft_disk(yy, xx, cx + 10, cy + 48, 56, 16, 0.45), 0.22)
    cup = soft_disk(yy, xx, cx, cy + 8, 44, 40, 0.16)
    wash(img, BOWL, cup, 0.86)
    wash(img, MAGENTA_PALE, cup * soft_disk(yy, xx, cx - 14, cy - 4, 22, 20, 0.5), 0.28)
    mouth = soft_disk(yy, xx, cx, cy - 20, 32, 13, 0.22)
    wash(img, np.array([0.55, 0.46, 0.42]), mouth, 0.65)
    wash(img, MAGENTA_GLASS, soft_disk(yy, xx, cx, cy - 20, 18, 7, 0.4), 0.25)

    # a small green leaf that drifted onto the table near the loose plum
    wash(img, LEAF, soft_disk(yy, xx, bx + 210, by + 40, 28, 12, 0.28), 0.55)
    wash(img, np.array([0.42, 0.58, 0.34]), soft_disk(yy, xx, bx + 222, by + 36, 18, 9, 0.3), 0.4)

    # --- quiet wall papers, left of the high window ---
    paper_sheet(img, xx, yy, 980, 220, 160, 210, 0.04, np.array([0.95, 0.90, 0.80]), 0.22)
    paper_sheet(img, xx, yy, 1080, 250, 140, 180, -0.06, np.array([0.97, 0.93, 0.86]), 0.18)

    # a last magenta bloom of light on the table, under the bowl
    wash(img, MAGENTA_LIGHT, soft_disk(yy, xx, 700, 820, 180, 70, 0.7) * table, 0.10)

    # painterly: slight chromatic softness + paper re-grain
    img = clamp01(img)
    pil = Image.fromarray((img * 255).astype(np.uint8), mode="RGB")
    pil = pil.filter(ImageFilter.GaussianBlur(radius=1.7))
    soft = pil.filter(ImageFilter.GaussianBlur(radius=4.4))
    sharp = np.asarray(pil).astype(np.float64) / 255.0
    blur = np.asarray(soft).astype(np.float64) / 255.0
    # keep bowl / papers / bottle a touch clearer; edges of room softer
    focus = soft_disk(yy, xx, 780, 760, 560, 380, 0.82)
    focus = clamp01(0.32 + 0.68 * focus)
    mixed = sharp * focus[..., None] + blur * (1.0 - focus[..., None])
    mixed = clamp01(mixed + paper_grain(H, W)[..., None] * 0.50)
    # noon warmth: a little more cream, not tungsten gold
    mixed[..., 0] = clamp01(mixed[..., 0] * 1.015)
    mixed[..., 1] = clamp01(mixed[..., 1] * 1.005)
    mixed[..., 2] = clamp01(mixed[..., 2] * 0.995)

    out = Image.fromarray((mixed * 255).astype(np.uint8), mode="RGB")
    out.save(OUT, format="PNG")
    print(f"wrote {OUT} {out.size[0]}x{out.size[1]}")


if __name__ == "__main__":
    main()
