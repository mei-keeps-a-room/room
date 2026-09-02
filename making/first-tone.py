#!/usr/bin/env python3
"""A few seconds to sit with. Glass, then a quieter string. Not a picture."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "first-tone.wav"

SR = 44100
DURATION = 7.0  # seconds, including the tail


def env_glass(t: float, attack: float, decay: float) -> float:
    if t < 0:
        return 0.0
    if t < attack:
        return t / attack
    return math.exp(-(t - attack) / decay)


def env_pluck(t: float, decay: float) -> float:
    if t < 0:
        return 0.0
    # fast rise, long quiet fall — like a string after the finger leaves
    a = 0.008
    if t < a:
        return t / a
    return math.exp(-(t - a) / decay)


def glass(freq: float, t: float, t0: float) -> float:
    """Mostly sine, slow beat, a little inharmonic air. A rim, not a bell."""
    u = t - t0
    e = env_glass(u, 0.12, 2.35)
    if e < 1e-5:
        return 0.0
    # two close partials so it breathes
    s = 0.0
    s += math.sin(2 * math.pi * freq * u)
    s += 0.18 * math.sin(2 * math.pi * (freq * 2.003) * u)
    s += 0.07 * math.sin(2 * math.pi * (freq * 2.99) * u)
    s += 0.04 * math.sin(2 * math.pi * (freq + 0.35) * u)
    return e * s * 0.22


def string(freq: float, t: float, t0: float) -> float:
    """A plucked fifth, harmonics that leave first."""
    u = t - t0
    e = env_pluck(u, 1.85)
    if e < 1e-5:
        return 0.0
    s = 0.0
    for h in range(1, 7):
        amp = (1.0 / (h ** 1.35)) * math.exp(-0.55 * (h - 1) * u)
        s += amp * math.sin(2 * math.pi * freq * h * u)
    return e * s * 0.16


def sample_at(t: float) -> float:
    # C5 glass, then a quieter G4 string a breath later. Sit with both.
    x = 0.0
    x += glass(523.25, t, 0.15)
    x += glass(783.99, t, 2.4) * 0.55  # G5, softer, later
    x += string(392.00, t, 1.35)
    # tiny room air so it is not a vacuum
    x += 0.004 * math.sin(2 * math.pi * 0.35 * t) * env_glass(t, 0.4, 4.0)
    return x


def main() -> None:
    n = int(SR * DURATION)
    frames = bytearray()
    peak = 0.0
    raw: list[float] = []
    for i in range(n):
        t = i / SR
        v = sample_at(t)
        raw.append(v)
        peak = max(peak, abs(v))
    # leave headroom; never clip
    scale = 0.85 / peak if peak > 0 else 1.0
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
