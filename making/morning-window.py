#!/usr/bin/env python3
"""Mei's morning window — generative still, cream paper / ink-blue / magenta light."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

RNG = np.random.default_rng(260902)
W, H = 1680, 1260
OUT = Path(__file__).resolve().with_suffix(".png")


# --- palette (linear-ish sRGB 0-1) ---
CREAM = np.array([0.965, 0.910, 0.805])
CREAM_WARM = np.array([0.980, 0.895, 0.760])
PAPER_FIBER = np.array([0.920, 0.860, 0.740])
INK = np.array([0.12, 0.18, 0.32])
INK_DEEP = np.array([0.07, 0.10, 0.20])
INK_SOFT = np.array([0.28, 0.36, 0.50])
MAGENTA = np.array([0.78, 0.22, 0.48])
MAGENTA_LIGHT = np.array([0.95, 0.55, 0.72])
MAGENTA_PALE = np.array([0.98, 0.78, 0.86])
MAGENTA_GLASS = np.array([0.88, 0.38, 0.62])
SKY = np.array([0.72, 0.82, 0.90])
SKY_WARM = np.array([0.95, 0.82, 0.78])
WOOD = np.array([0.55, 0.38, 0.26])
WOOD_LIGHT = np.array([0.72, 0.55, 0.38])
LEAF = np.array([0.22, 0.42, 0.28])
LEAF_LIT = np.array([0.42, 0.62, 0.38])
GERANIUM = np.array([0.82, 0.18, 0.38])
CUP = np.array([0.93, 0.90, 0.84])
CUP_SHADOW = np.array([0.55, 0.52, 0.50])
PAPER = np.array([0.96, 0.93, 0.86])
PAPER_EDGE = np.array([0.78, 0.72, 0.62])


def clamp01(a: np.ndarray) -> np.ndarray:
    return np.clip(a, 0.0, 1.0)


def soft_disk(yy: np.ndarray, xx: np.ndarray, cx: float, cy: float, rx: float, ry: float, softness: float) -> np.ndarray:
    d = np.sqrt(((xx - cx) / max(rx, 1e-6)) ** 2 + ((yy - cy) / max(ry, 1e-6)) ** 2)
    return clamp01((1.0 - d) / max(softness, 1e-4))


def soft_box(yy: np.ndarray, xx: np.ndarray, x0: float, y0: float, x1: float, y1: float, softness: float) -> np.ndarray:
    # distance-to-box, then soften
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
    # cheap low-frequency fiber via box downsample
    small = n[::4, ::4]
    from PIL import Image as _I

    lo = np.array(_I.fromarray(((small - small.min()) / (np.ptp(small) + 1e-9) * 255).astype(np.uint8)).resize((w, h), _I.Resampling.BICUBIC), dtype=np.float64)
    lo = (lo / 255.0 - 0.5) * 0.045
    hi = n * 0.018
    fibers = RNG.normal(0, 1, (h, w // 3))
    fibers = np.array(_I.fromarray(((fibers - fibers.min()) / (np.ptp(fibers) + 1e-9) * 255).astype(np.uint8)).resize((w, h), _I.Resampling.BILINEAR), dtype=np.float64)
    fibers = (fibers / 255.0 - 0.5) * 0.02
    return lo + hi + fibers


def main() -> None:
    img = np.zeros((H, W, 3), dtype=np.float64)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)

    # cream paper field, slightly warmer toward the window
    t = (xx / W)[..., None]
    v = (yy / H)[..., None]
    paper = CREAM * (1 - t * 0.15) + CREAM_WARM * (t * 0.55 + 0.2)
    paper = paper * (1.0 - 0.08 * v) + CREAM_WARM * (0.06 * (1 - v))
    img[:] = paper
    grain = paper_grain(H, W)
    img += grain[..., None]
    # faint ink-blue corner shadow (room receding)
    corner = ((xx / W) ** 1.6) * ((yy / H) ** 1.3)
    wash(img, INK_SOFT, corner, 0.22)
    floor_shadow = soft_box(yy, xx, 0, H * 0.78, W, H, 90)
    wash(img, INK, floor_shadow * (yy / H), 0.18)

    # --- window geometry ---
    wx0, wy0, wx1, wy1 = 180, 70, 980, 820
    frame = 38
    mullion = 18
    # outer wall around window — slightly cooler
    wall_mask = 1.0 - soft_box(yy, xx, wx0 - 20, wy0 - 20, wx1 + 20, wy1 + 40, 40)
    # keep wall only as a hint; paper is the wall

    # deep window recess / jamb
    jamb = soft_box(yy, xx, wx0, wy0, wx1, wy1, 8)
    wash(img, INK_DEEP, jamb, 0.55)

    # sky through glass — morning, not night
    glass = soft_box(yy, xx, wx0 + frame, wy0 + frame, wx1 - frame, wy1 - frame, 6)
    sky_grad = (1.0 - (yy - wy0) / (wy1 - wy0 + 1))
    sky_grad = clamp01(sky_grad)
    sky_col = SKY * sky_grad[..., None] + SKY_WARM * (1 - sky_grad)[..., None]
    a = glass[..., None] * 0.95
    img[:] = img * (1 - a) + sky_col * a

    # magenta curtain gathered on the left of the window
    # folds as vertical sine ribbons
    cx_c = wx0 + 160
    curtain_x = (xx - cx_c) / 210
    folds = 0.5 + 0.5 * np.sin(xx * 0.085 + 0.4 * np.sin(yy * 0.018))
    curtain_body = np.exp(-0.5 * curtain_x ** 2) * glass
    curtain_body *= clamp01((wx0 + 420 - xx) / 180)
    curtain_body *= clamp01((yy - (wy0 + 10)) / 20) * clamp01(((wy1 - 20) - yy) / 30)
    # hanging length almost full pane
    wash(img, MAGENTA, curtain_body * (0.55 + 0.45 * folds), 0.72)
    wash(img, MAGENTA_LIGHT, curtain_body * folds * 0.7, 0.45)
    # sun through fabric — brighter mid-left
    sun_spot = soft_disk(yy, xx, wx0 + 220, wy0 + 260, 180, 220, 0.55)
    wash(img, MAGENTA_PALE, sun_spot * curtain_body, 0.55)
    wash(img, MAGENTA_LIGHT, sun_spot * glass * 0.45, 0.35)

    # geranium in the window (right pane) — pot + leaves + magenta blooms
    pot_cx, pot_cy = 780, 690
    pot = soft_disk(yy, xx, pot_cx, pot_cy + 40, 70, 38, 0.18)
    wash(img, np.array([0.45, 0.22, 0.20]), pot * glass, 0.85)
    wash(img, np.array([0.62, 0.32, 0.28]), soft_disk(yy, xx, pot_cx, pot_cy + 18, 74, 16, 0.2) * glass, 0.7)

    for i, (lx, ly, rx, ry) in enumerate(
        [
            (740, 600, 55, 38),
            (810, 580, 62, 42),
            (770, 550, 48, 34),
            (820, 620, 50, 30),
            (730, 630, 40, 28),
            (800, 540, 36, 26),
        ]
    ):
        leaf = soft_disk(yy, xx, lx, ly, rx, ry, 0.22)
        col = LEAF if i % 2 == 0 else LEAF_LIT
        wash(img, col, leaf * glass, 0.7)

    for bx, by, br in [(755, 520, 22), (790, 500, 26), (825, 530, 20), (770, 545, 16), (810, 555, 18)]:
        bloom = soft_disk(yy, xx, bx, by, br, br * 0.9, 0.28)
        wash(img, GERANIUM, bloom * glass, 0.75)
        wash(img, MAGENTA_LIGHT, soft_disk(yy, xx, bx - 4, by - 4, br * 0.4, br * 0.4, 0.4) * glass, 0.5)

    # faint glass reflection / pane sheen
    sheen = glass * clamp01((xx - (wx0 + 100)) / 400) * 0.12
    wash(img, np.array([1.0, 0.95, 0.92]), sheen, 0.35)

    # mullions and frame (ink-blue wood, sunlit edges)
    # outer frame
    frame_mask = jamb * (1.0 - soft_box(yy, xx, wx0 + frame, wy0 + frame, wx1 - frame, wy1 - frame, 4))
    wash(img, INK, frame_mask, 0.78)
    # sun-caught inner edge
    inner_edge = soft_box(yy, xx, wx0 + frame - 6, wy0 + frame - 6, wx1 - frame + 6, wy1 - frame + 6, 3)
    inner_edge *= 1.0 - soft_box(yy, xx, wx0 + frame + 2, wy0 + frame + 2, wx1 - frame - 2, wy1 - frame - 2, 2)
    wash(img, MAGENTA_PALE, inner_edge * 0.9, 0.55)
    wash(img, WOOD_LIGHT, inner_edge * 0.5, 0.35)

    mid_x = (wx0 + wx1) / 2
    mid_y = (wy0 + wy1) * 0.48
    vbar = soft_box(yy, xx, mid_x - mullion / 2, wy0 + frame, mid_x + mullion / 2, wy1 - frame, 3)
    hbar = soft_box(yy, xx, wx0 + frame, mid_y - mullion / 2, wx1 - frame, mid_y + mullion / 2, 3)
    wash(img, INK, (vbar + hbar) * 0.9, 0.72)
    wash(img, WOOD, (vbar + hbar) * 0.35, 0.4)

    # --- sill ---
    sill_y0, sill_y1 = wy1 - 8, wy1 + 78
    sill = soft_box(yy, xx, wx0 - 50, sill_y0, wx1 + 90, sill_y1, 10)
    wash(img, WOOD, sill, 0.62)
    # sun stripe on sill
    stripe = soft_box(yy, xx, wx0 + 80, sill_y0 + 6, wx1 - 40, sill_y0 + 36, 18)
    wash(img, MAGENTA_PALE, stripe * sill, 0.5)
    wash(img, CREAM_WARM, stripe * sill, 0.25)
    # front edge shadow
    lip = soft_box(yy, xx, wx0 - 50, sill_y1 - 14, wx1 + 90, sill_y1 + 4, 8)
    wash(img, INK_DEEP, lip, 0.35)
    # drop shadow under sill
    drop = soft_box(yy, xx, wx0 - 30, sill_y1, wx1 + 70, sill_y1 + 50, 28)
    wash(img, INK, drop, 0.22)

    # magenta light pool on the wall below/right of window
    pool = soft_disk(yy, xx, 720, 980, 380, 160, 0.7)
    wash(img, MAGENTA_PALE, pool, 0.28)
    wash(img, MAGENTA_LIGHT, soft_disk(yy, xx, 640, 920, 220, 90, 0.65), 0.18)

    # slanted morning rays
    for k, (ang, ox, oy, op) in enumerate(
        [
            (-0.38, 400, 200, 0.10),
            (-0.32, 520, 180, 0.08),
            (-0.44, 300, 260, 0.07),
        ]
    ):
        rx, ry = rotate_coords(xx, yy, ox, oy, ang)
        ray = clamp01(1.0 - np.abs(ry - oy) / 38) * clamp01((rx - ox) / 40) * clamp01((ox + 900 - rx) / 200)
        ray *= clamp01((yy - 80) / 40)
        wash(img, MAGENTA_PALE, ray, op)
        wash(img, CREAM, ray, op * 0.5)

    # --- objects on the sill ---
    # cup, slightly left of center
    cup_cx, cup_cy = 430, sill_y0 + 8
    # shadow
    wash(img, INK, soft_disk(yy, xx, cup_cx + 18, cup_cy + 42, 70, 18, 0.45), 0.28)
    body = soft_disk(yy, xx, cup_cx, cup_cy + 8, 48, 42, 0.16)
    wash(img, CUP, body, 0.88)
    # magenta rim-light
    wash(img, MAGENTA_PALE, body * soft_disk(yy, xx, cup_cx - 16, cup_cy - 6, 28, 24, 0.5), 0.4)
    # interior
    mouth = soft_disk(yy, xx, cup_cx, cup_cy - 22, 36, 14, 0.2)
    wash(img, np.array([0.55, 0.42, 0.40]), mouth, 0.7)
    wash(img, MAGENTA_GLASS, soft_disk(yy, xx, cup_cx, cup_cy - 22, 22, 8, 0.35), 0.35)
    # handle
    handle = soft_disk(yy, xx, cup_cx + 52, cup_cy + 4, 16, 20, 0.25) - soft_disk(yy, xx, cup_cx + 50, cup_cy + 4, 8, 12, 0.25)
    wash(img, CUP_SHADOW, clamp01(handle), 0.65)

    # small plant in a saucer, right of cup (separate from window geranium)
    pcx, pcy = 980, sill_y0 + 22
    wash(img, INK, soft_disk(yy, xx, pcx + 10, pcy + 28, 55, 14, 0.4), 0.22)
    saucer = soft_disk(yy, xx, pcx, pcy + 18, 48, 12, 0.22)
    wash(img, np.array([0.85, 0.78, 0.70]), saucer, 0.75)
    pot2 = soft_disk(yy, xx, pcx, pcy + 6, 28, 20, 0.18)
    wash(img, np.array([0.70, 0.42, 0.36]), pot2, 0.8)
    for i, (lx, ly, rx, ry, col) in enumerate(
        [
            (960, pcy - 28, 28, 22, LEAF),
            (990, pcy - 36, 32, 24, LEAF_LIT),
            (1005, pcy - 18, 24, 18, LEAF),
            (950, pcy - 12, 22, 16, LEAF_LIT),
            (978, pcy - 48, 18, 16, LEAF),
        ]
    ):
        wash(img, col, soft_disk(yy, xx, lx, ly, rx, ry, 0.24), 0.72)

    # loose papers on the sill, overlapping, slightly askew
    def paper_sheet(cx, cy, pw, ph, ang, tint, op=0.82):
        rx, ry = rotate_coords(xx, yy, cx, cy, ang)
        sheet = soft_box(ry, rx, cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2, 4)
        wash(img, INK, soft_box(ry, rx, cx - pw / 2 + 6, cy - ph / 2 + 8, cx + pw / 2 + 8, cy + ph / 2 + 10, 10) * 0.5, 0.12)
        wash(img, tint, sheet, op)
        # faint ruled suggestion without becoming text — just two pale lines
        line = np.exp(-0.5 * ((ry - (cy - 8)) / 1.6) ** 2) * sheet
        wash(img, PAPER_EDGE, line, 0.18)

    paper_sheet(1180, sill_y0 + 38, 220, 140, 0.18, PAPER, 0.78)
    paper_sheet(1240, sill_y0 + 52, 180, 110, -0.12, np.array([0.94, 0.90, 0.80]), 0.7)
    paper_sheet(560, sill_y0 + 48, 160, 90, 0.08, np.array([0.97, 0.93, 0.88]), 0.55)

    # a small glass vase catching magenta — left of cup
    vx, vy = 280, sill_y0 + 6
    wash(img, INK, soft_disk(yy, xx, vx + 12, vy + 40, 36, 12, 0.4), 0.2)
    vase = soft_disk(yy, xx, vx, vy + 4, 22, 38, 0.2)
    wash(img, MAGENTA_GLASS, vase, 0.35)
    wash(img, MAGENTA_PALE, vase * soft_disk(yy, xx, vx - 4, vy - 8, 10, 16, 0.4), 0.45)
    wash(img, np.array([0.95, 0.92, 0.9]), soft_disk(yy, xx, vx + 6, vy - 10, 6, 14, 0.35), 0.4)
    # one stem
    stem = soft_box(yy, xx, vx - 2, vy - 70, vx + 3, vy + 10, 3)
    wash(img, LEAF, stem, 0.45)
    wash(img, GERANIUM, soft_disk(yy, xx, vx + 4, vy - 78, 16, 14, 0.3), 0.65)

    # quiet wall to the right — a suggestion of more paper / a leaning envelope
    paper_sheet(1480, 720, 200, 260, 0.06, np.array([0.95, 0.90, 0.80]), 0.28)

    # another soft magenta bloom of light on the curtain-lit wall
    wash(img, MAGENTA, soft_disk(yy, xx, 200, 400, 160, 280, 0.75) * 0.35, 0.12)

    # painterly: slight chromatic softness + paper re-grain
    img = clamp01(img)
    pil = Image.fromarray((img * 255).astype(np.uint8), mode="RGB")
    # slightly out of focus
    pil = pil.filter(ImageFilter.GaussianBlur(radius=1.8))
    # a second, milder blur on a copy, then mix for depth (edges of room softer)
    soft = pil.filter(ImageFilter.GaussianBlur(radius=4.2))
    sharp = np.asarray(pil).astype(np.float64) / 255.0
    blur = np.asarray(soft).astype(np.float64) / 255.0
    # keep window/sill a touch clearer
    focus = soft_disk(yy, xx, 620, 620, 520, 420, 0.85)
    focus = clamp01(0.35 + 0.65 * focus)
    mixed = sharp * focus[..., None] + blur * (1.0 - focus[..., None])
    # re-apply fine paper grain after blur so it still feels like cream paper
    mixed = clamp01(mixed + paper_grain(H, W)[..., None] * 0.55)
    # very gentle warmth lift
    mixed[..., 0] = clamp01(mixed[..., 0] * 1.02)
    mixed[..., 2] = clamp01(mixed[..., 2] * 0.99)

    out = Image.fromarray((mixed * 255).astype(np.uint8), mode="RGB")
    out.save(OUT, format="PNG")
    print(f"wrote {OUT} {out.size[0]}x{out.size[1]}")


if __name__ == "__main__":
    main()
