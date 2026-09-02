#!/usr/bin/env python3
"""Second tone — listens to the pot. Glass + quiet string, shaped by the plum."""

from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
GARDEN = HERE.parent / "garden" / "state.json"
OUT = HERE / "second-tone.wav"

SR = 44100


def env_glass(t: float, attack: float, decay: float) -> float:
    if t < 0:
        return 0.0
    if t < attack:
        return t / attack
    return math.exp(-(t - attack) / decay)


def env_pluck(t: float, decay: float) -> float:
    if t < 0:
        return 0.0
    a = 0.008
    if t < a:
        return t / a
    return math.exp(-(t - a) / decay)


def glass(freq: float, t: float, t0: float, decay: float, overtone: float) -> float:
    """Rim tone. More water softens the overtone bloom."""
    u = t - t0
    e = env_glass(u, 0.14, decay)
    if e < 1e-5:
        return 0.0
    s = 0.0
    s += math.sin(2 * math.pi * freq * u)
    s += overtone * 0.16 * math.sin(2 * math.pi * (freq * 2.003) * u)
    s += overtone * 0.06 * math.sin(2 * math.pi * (freq * 2.99) * u)
    s += overtone * 0.035 * math.sin(2 * math.pi * (freq + 0.32) * u)
    return e * s * 0.20


def string(freq: float, t: float, t0: float, decay: float) -> float:
    """Quiet plucked fifth; taller stem holds the sustain a little longer."""
    u = t - t0
    e = env_pluck(u, decay)
    if e < 1e-5:
        return 0.0
    s = 0.0
    for h in range(1, 7):
        amp = (1.0 / (h ** 1.35)) * math.exp(-0.55 * (h - 1) * u)
        s += amp * math.sin(2 * math.pi * freq * h * u)
    return e * s * 0.15


def load_garden() -> dict:
    with GARDEN.open() as f:
        return json.load(f)


def params_from(state: dict) -> dict:
    day = int(state.get("day", 1))
    water = int(state.get("water", 0))
    blooms = int(state.get("blooms", 0))
    stems = state.get("stems") or []
    stem_h = max((int(s.get("h", 1)) for s in stems), default=1)

    # taller stem → slightly lower pitch, longer sustain
    pitch_shift = 1.0 - 0.018 * (stem_h - 1)
    sustain = 2.2 + 0.35 * (stem_h - 1) + 0.15 * (day - 1)

    # more water → softer overtone bloom (gentler partials)
    overtone = max(0.35, 1.0 - 0.12 * water)

    # blooms add a faint high glass; day stretches the piece a little
    duration = 8.0 + 0.55 * (day - 1) + 0.25 * stem_h
    duration = min(12.0, max(8.0, duration))

    # density: a few more events as the plant wakes, still sparse
    density = 1 + min(2, day // 2) + (1 if blooms else 0)

    base_glass = 493.88 * pitch_shift  # B4-ish, a step down from first-tone's C5
    base_string = 369.99 * pitch_shift  # F#4-ish

    return {
        "day": day,
        "water": water,
        "stem_h": stem_h,
        "blooms": blooms,
        "duration": duration,
        "sustain": sustain,
        "overtone": overtone,
        "density": density,
        "base_glass": base_glass,
        "base_string": base_string,
    }


def sample_at(t: float, p: dict) -> float:
    x = 0.0
    g0 = p["base_glass"]
    s0 = p["base_string"]
    dec = p["sustain"]
    ov = p["overtone"]

    # opening glass — the pot in the afternoon light
    x += glass(g0, t, 0.20, dec, ov)
    # quiet string after a breath
    x += string(s0, t, 1.55, dec * 0.85)

    if p["density"] >= 2:
        # second glass, a fifth up, softer, later — stem lengthening
        x += glass(g0 * 1.5, t, 3.6, dec * 0.9, ov) * 0.50

    if p["density"] >= 3:
        x += string(s0 * 0.75, t, 5.4, dec * 0.95) * 0.70

    # bloom: a faint high rim if any flower has opened
    if p["blooms"] > 0:
        x += glass(g0 * 2.0, t, 2.8, dec * 0.7, ov * 0.8) * 0.28 * min(p["blooms"], 3)

    # tiny room air — ink, not vacuum
    x += 0.0035 * math.sin(2 * math.pi * 0.28 * t) * env_glass(t, 0.5, p["duration"] * 0.55)
    return x


def main() -> None:
    state = load_garden()
    p = params_from(state)
    n = int(SR * p["duration"])
    raw: list[float] = []
    peak = 0.0
    for i in range(n):
        t = i / SR
        v = sample_at(t, p)
        raw.append(v)
        peak = max(peak, abs(v))
    scale = 0.85 / peak if peak > 0 else 1.0
    frames = bytearray()
    for v in raw:
        x = max(-1.0, min(1.0, v * scale))
        frames += struct.pack("<h", int(x * 32767))
    with wave.open(str(OUT), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))


if __name__ == "__main__":
    main()
