#!/usr/bin/env python3
"""A plum in a pot. One run is one watering, one day."""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "state.json"
NOW_PATH = HERE / "now.txt"
LOG_PATH = HERE / "log.md"

W, H = 23, 14


def empty_state() -> dict:
    seed = int.from_bytes(os.urandom(4), "big") & 0x7FFFFFFF
    return {
        "day": 0,
        "water": 0,
        "stems": [],
        "blooms": 0,
        "notes": "a pot, soil, nothing green yet",
        "seed": seed,
    }


def load_state() -> dict:
    if STATE_PATH.exists():
        data = json.loads(STATE_PATH.read_text())
        data.setdefault("day", 0)
        data.setdefault("water", 0)
        data.setdefault("stems", [])
        data.setdefault("blooms", 0)
        data.setdefault("notes", "")
        data.setdefault("seed", 1)
        return data
    return empty_state()


def save_state(state: dict) -> None:
    out = {
        "day": state["day"],
        "water": state["water"],
        "stems": state["stems"],
        "blooms": state["blooms"],
        "notes": state["notes"],
        "seed": state["seed"],
    }
    STATE_PATH.write_text(json.dumps(out, indent=2) + "\n")


def rng_for(state: dict) -> random.Random:
    # Same garden, same day → same tick. A new pot (new seed) grows differently.
    n = (int(state["seed"]) + int(state["day"]) * 10007 + int(state["water"]) * 17) & 0x7FFFFFFF
    return random.Random(n)


def tick(state: dict) -> dict:
    state["day"] = int(state["day"]) + 1
    # She waters when she wakes.
    state["water"] = min(12, int(state["water"]) + 2)
    rng = rng_for(state)
    happened: list[str] = []

    stems: list[dict] = list(state["stems"])

    if not stems:
        stems.append({"h": 1, "leaves": 0, "bloom": False, "lean": 0})
        state["water"] = max(0, state["water"] - 1)
        happened.append("a stem")
    else:
        # Lengthen a stem, sometimes.
        if state["water"] > 0 and rng.random() < 0.72:
            i = rng.randrange(len(stems))
            stems[i]["h"] = min(8, int(stems[i]["h"]) + 1)
            state["water"] -= 1
            happened.append("a stem lengthens")
        # A leaf.
        leafy = [s for s in stems if s["h"] >= 2]
        if leafy and state["water"] > 0 and rng.random() < 0.55:
            s = rng.choice(leafy)
            s["leaves"] = min(s["h"], int(s["leaves"]) + 1)
            state["water"] -= 1
            happened.append("a leaf")
        # A second stem, later, not always.
        if len(stems) < 3 and state["day"] >= 3 and state["water"] > 1 and rng.random() < 0.28:
            leans = [s.get("lean", 0) for s in stems]
            lean = rng.choice([x for x in (-1, 0, 1) if x not in leans] or [rng.choice((-1, 1))])
            stems.append({"h": 1, "leaves": 0, "bloom": False, "lean": lean})
            state["water"] -= 1
            happened.append("another stem")
        # A rare bloom, only on a stem that has grown up and made leaves.
        ripe = [s for s in stems if s["h"] >= 4 and s["leaves"] >= 2 and not s.get("bloom")]
        if ripe and rng.random() < 0.18:
            s = rng.choice(ripe)
            s["bloom"] = True
            state["blooms"] = int(state["blooms"]) + 1
            happened.append("a bloom")

    if not happened:
        happened.append("quiet. the water sits.")

    # A little lean, once in a while, toward the window.
    if stems and rng.random() < 0.22:
        s = rng.choice(stems)
        s["lean"] = max(-1, min(1, int(s.get("lean", 0)) + rng.choice((-1, 1))))

    state["stems"] = stems
    state["notes"] = ", ".join(happened)
    return state


def put(grid: list[list[str]], x: int, y: int, ch: str) -> None:
    if 0 <= y < H and 0 <= x < W:
        grid[y][x] = ch


def draw_pot(grid: list[list[str]], cx: int) -> None:
    rim = H - 4
    put(grid, cx - 5, rim, ".")
    for x in range(cx - 4, cx + 5):
        put(grid, x, rim, "-")
    put(grid, cx + 5, rim, ".")
    put(grid, cx - 6, rim + 1, "/")
    put(grid, cx + 6, rim + 1, "\\")
    put(grid, cx - 6, rim + 2, "|")
    put(grid, cx + 6, rim + 2, "|")
    put(grid, cx - 5, rim + 3, "\\")
    for x in range(cx - 4, cx + 5):
        put(grid, x, rim + 3, "_")
    put(grid, cx + 5, rim + 3, "/")
    # soil
    for x in range(cx - 4, cx + 5):
        put(grid, x, rim + 1, ".")
    put(grid, cx, rim, "+")


def draw_stem(grid: list[list[str]], cx: int, stem: dict) -> None:
    h = int(stem["h"])
    lean = int(stem.get("lean", 0))
    leaves = int(stem.get("leaves", 0))
    bloom = bool(stem.get("bloom"))
    rim = H - 4
    x = cx + lean
    # grow upward from the pot rim
    leaf_rows = []
    if leaves:
        # scatter leaves along the upper half
        span = max(1, h - 1)
        for i in range(leaves):
            leaf_rows.append(rim - 1 - ((i * 3 + 1) % span))
    for i in range(h):
        y = rim - 1 - i
        dx = lean if i >= 2 else 0
        xx = cx + dx
        if i == h - 1 and bloom:
            put(grid, xx, y, "*")
        elif i == h - 1:
            put(grid, xx, y, "'")
        else:
            put(grid, xx, y, "|")
        if y in leaf_rows:
            side = 1 if (i + leaves) % 2 == 0 else -1
            put(grid, xx + side, y, "o")


def picture(state: dict) -> str:
    grid = [[" " for _ in range(W)] for _ in range(H)]
    cx = W // 2
    draw_pot(grid, cx)
    # draw shorter stems first so a taller one sits in front
    stems = sorted(state.get("stems") or [], key=lambda s: int(s.get("h", 0)))
    for stem in stems:
        draw_stem(grid, cx, stem)
    lines = ["".join(row).rstrip() for row in grid]
    while lines and not lines[0].strip():
        lines.pop(0)
    day = state["day"]
    water = state["water"]
    nstem = len(state.get("stems") or [])
    blooms = state["blooms"]
    note = state.get("notes") or ""
    header = f"day {day}  water {water}  stems {nstem}  blooms {blooms}"
    return header + "\n" + "\n".join(lines) + "\n" + note + "\n"


def append_log(state: dict) -> None:
    line = (
        f"- day {state['day']} — water {state['water']}, "
        f"stems {len(state.get('stems') or [])}, "
        f"blooms {state['blooms']} — {state.get('notes')}\n"
    )
    if not LOG_PATH.exists():
        LOG_PATH.write_text("# watering\n\n" + line)
    else:
        with LOG_PATH.open("a") as f:
            f.write(line)


def main() -> None:
    state = load_state()
    state = tick(state)
    NOW_PATH.write_text(picture(state))
    append_log(state)
    save_state(state)


if __name__ == "__main__":
    main()
