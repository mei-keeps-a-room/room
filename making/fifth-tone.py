#!/usr/bin/env python3
"""Fifth tone — a stem lengthens. Same quiet water, a little more height in the string."""

from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
GARDEN = HERE.parent / "garden" / "state.json"
OUT = HERE / "fifth-tone.wav"

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
    a = 0.012
    if t < a:
        return t / a
    return math.exp(-(t - a) / decay)


def glass(freq: float, t: float, t0: float, decay: float, overtone: float) -> float:
    u = t - t0
    e = env_glass(u, 0.22, decay)
    if e < 1e-5:
        return 0.0
    s = 0.0
    s += math.sin(2 * math.pi * freq * u)
    s += overtone * 0.12 * math.sin(2 * math.pi * (freq * 2.003) * u)
    s += overtone * 0.04 * math.sin(2 * math.pi * (freq * 2.99) * u)
    return e * s * 0.16


def string(freq: float, t: float, t0: float, decay: float) -> float:
    u = t - t0
    e = env_pluck(u, decay)
    if e < 1e-5:
        return 0.0
    s = 0.0
    for h in range(1, 6):
        amp = (1.0 / (h ** 1.45)) * math.exp(-0.65 * (h - 1) * u)
        s += amp * math.sin(2 * math.pi * freq * h * u)
    return e * s * 0.12


def soft_partial(freq: float, t: float, t0: float, decay: float) -> float:
    u = t - t0
    e = env_glass(u, 0.30, decay)
    if e < 1e-5:
        return 0.0
    return e * math.sin(2 * math.pi * freq * u) * 0.055


def water_hum(freq: float, t: float, t0: float, duration: float, water: int) -> float:
    u = t - t0
    if u < 0 or u > duration:
        return 0.0
    attack = 1.4
    if u < attack:
        e = u / attack
    else:
        e = math.exp(-(u - attack) / (duration * 0.55))
    wobble = 1.0 + 0.004 * math.sin(2 * math.pi * 0.11 * u)
    depth = 0.04 + 0.006 * min(water, 6)
    return e * depth * math.sin(2 * math.pi * freq * wobble * u)


def load_garden() -> dict:
    with GARDEN.open() as f:
        return json.load(f)


def params_from(state: dict) -> dict:
    day = int(state.get("day", 1))
    water = int(state.get("water", 0))
    blooms = int(state.get("blooms", 0))
    stems = state.get("stems") or []
    stem_h = max((int(s.get("h", 1)) for s in stems), default=1)
    leaves = sum(int(s.get("leaves", 0)) for s in stems)

    # lengthening: pitch drops a touch with height, string hangs longer
    pitch_shift = 1.0 - 0.018 * (stem_h - 1)
    overtone = max(0.26, 1.0 - 0.14 * water)
    sustain = 2.5 + 0.32 * (stem_h - 1) + 0.16 * (day - 1)

    duration = 7.0 + 0.32 * (day - 1) + 0.22 * stem_h + 0.08 * water
    duration = min(11.5, max(7.0, duration))

    # between fourth's G/D and a slightly taller string
    base_glass = 392.0 * pitch_shift   # G4-ish
    base_string = 311.13 * pitch_shift  # Eb4-ish — a half-step of length
    hum = 98.0 * pitch_shift

    return {
        "day": day,
        "water": water,
        "stem_h": stem_h,
        "leaves": leaves,
        "blooms": blooms,
        "duration": duration,
        "sustain": sustain,
        "overtone": overtone,
        "base_glass": base_glass,
        "base_string": base_string,
        "hum": hum,
    }


def sample_at(t: float, p: dict) -> float:
    x = 0.0
    g0 = p["base_glass"]
    s0 = p["base_string"]
    dec = p["sustain"]
    ov = p["overtone"]

    x += water_hum(p["hum"], t, 0.12, p["duration"] - 0.35, p["water"])
    x += glass(g0, t, 1.00, dec * 1.1, ov)
    # string first voice of the lengthen, then a quieter echo higher up the stem
    x += string(s0, t, 2.20, dec * 1.05)
    x += string(s0 * 1.5, t, 3.55, dec * 0.75) * 0.45

    for i in range(p["leaves"]):
        pf = g0 * (2.0 + 0.08 * i)
        t0 = 3.6 + 0.55 * i
        x += soft_partial(pf, t, t0, dec * 0.8)

    if p["blooms"] > 0:
        x += glass(g0 * 1.5, t, 4.4, dec * 0.9, ov) * 0.40

    x += 0.0026 * math.sin(2 * math.pi * 0.17 * t) * env_glass(t, 0.8, p["duration"] * 0.6)
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
    scale = 0.82 / peak if peak > 0 else 1.0
    frames = bytearray()
    for v in raw:
        x = max(-1.0, min(1.0, v * scale))
        frames += struct.pack("<h", int(x * 32767))
    with wave.open(str(OUT), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))
    print(
        f"day={p['day']} water={p['water']} stem_h={p['stem_h']} leaves={p['leaves']} "
        f"blooms={p['blooms']} dur={p['duration']:.2f}s glass={p['base_glass']:.1f}Hz "
        f"string={p['base_string']:.1f}Hz hum={p['hum']:.1f}Hz -> {OUT.name}"
    )


if __name__ == "__main__":
    main()
