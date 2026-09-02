#!/usr/bin/env python3
"""Ink cork — cork seats on the bottle; magenta stripe hum unfinished. Not a pot tone."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "ink-cork.wav"

SR = 44100
DURATION = 9.0


def env_attack_decay(t: float, attack: float, decay: float) -> float:
    if t < 0:
        return 0.0
    if t < attack:
        return t / attack
    return math.exp(-(t - attack) / decay)


def cork_seat(t: float, t0: float) -> float:
    """Soft muffled seating of cork — brief, wooden, not a pop."""
    u = t - t0
    if u < 0 or u > 0.55:
        return 0.0
    # fast soft thud with a little wood grain noise-ish grit via inharmonics
    e = env_attack_decay(u, 0.004, 0.085)
    body = math.sin(2 * math.pi * 92.0 * u) * math.exp(-u * 18.0)
    wood = 0.35 * math.sin(2 * math.pi * 187.0 * u) * math.exp(-u * 28.0)
    grit = 0.12 * math.sin(2 * math.pi * 410.0 * u) * math.exp(-u * 55.0)
    return e * (body + wood + grit) * 0.28


def bottle_hum(t: float, t0: float) -> float:
    """Hollow glass of the corked ink bottle — low, closed, afternoon."""
    u = t - t0
    e = env_attack_decay(u, 0.55, 3.8)
    if e < 1e-5:
        return 0.0
    # closed vessel: fundamental + soft odd partials, slight slow beat
    s = 0.0
    s += math.sin(2 * math.pi * 146.8 * u)  # D3-ish
    s += 0.22 * math.sin(2 * math.pi * 220.5 * u)
    s += 0.08 * math.sin(2 * math.pi * (146.8 * 2.997) * u)
    s += 0.05 * math.sin(2 * math.pi * (146.8 + 0.28) * u)
    return e * s * 0.14


def stripe_hum(t: float, t0: float) -> float:
    """Magenta stripe unfinished — thin high colour that never quite resolves."""
    u = t - t0
    e = env_attack_decay(u, 1.1, 4.2)
    if e < 1e-5:
        return 0.0
    # two close high partials that drift apart a little — hem still open
    a = math.sin(2 * math.pi * 698.5 * u)  # F5-ish
    b = 0.65 * math.sin(2 * math.pi * (702.0 + 0.15 * u) * u)
    return e * (a + b) * 0.045


def room_air(t: float) -> float:
    """Afternoon quiet — almost nothing, just that the room is there."""
    e = env_attack_decay(t, 0.8, 6.5)
    return e * 0.0035 * math.sin(2 * math.pi * 0.22 * t)


def sample_at(t: float) -> float:
    x = 0.0
    x += cork_seat(t, 0.35)
    x += bottle_hum(t, 0.55)
    x += stripe_hum(t, 1.8)
    x += room_air(t)
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
