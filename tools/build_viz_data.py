"""
Builds the data blobs the site's court charts use and writes them to tools/viz_data.json:
  HEX     small-hex, zone-aware, kernel-smoothed shot data (2025-26)
  BANDS   disjoint defended-FG% bands (<6ft, 6-15ft, 15ft+ twos, threes), 2025-26
Run from the repo root:  python tools/build_viz_data.py
Then tools/inject_viz_data.py swaps them into docs/index.html.
"""
import json, math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import spacing
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SEASON = "2025-26"
R = 9.0                 # hex radius in court units (1 unit = 0.1 ft)  -> ~1.6 ft wide hexes
SIGMA = 14.0            # smoothing bandwidth (units)
NEAR = 25.0             # radius for the "share of shots from near here" count
MIN_W = 1.0             # a cell is drawn only if the kernel weight of nearby same-zone shots >= this
PRIOR_K = 3.0           # shrinkage toward the player's own zone FG%
PLAYERS = ["Tyrese Maxey", "Joel Embiid", "LeBron James", "Jaylen Brown", "VJ Edgecombe", "Dean Wade",
           "Anfernee Simons", "Kentavious Caldwell-Pope", "Adem Bona"]
CLASSES = ["ra", "lane", "mid", "three"]


def classify(x, y):
    d = math.hypot(x, y)
    if d >= 237.5 or abs(x) >= 220:
        return "three"
    if d <= 40:
        return "ra"
    if abs(x) <= 80 and y <= 142.5:
        return "lane"
    return "mid"


def build_cells():
    cells = {c: [] for c in CLASSES}
    dx, dy = 1.5 * R, math.sqrt(3) * R
    for i in range(-int(250 / dx) - 2, int(250 / dx) + 3):
        cx = i * dx
        off = 0.5 * dy if i % 2 else 0.0
        j0 = int((-47.5 - R) / dy) - 2
        j1 = int((420 + R) / dy) + 2
        for j in range(j0, j1):
            cy = j * dy + off
            pts = [(cx, cy)]
            for k in range(6):
                a = math.radians(60 * k); pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
                b = math.radians(60 * k + 30); pts.append((cx + R * .866 * math.cos(b), cy + R * .866 * math.sin(b)))
            seen = {classify(px, py) for px, py in pts if -250 <= px <= 250 and -47.5 <= py <= 420}
            for c in seen:
                if -250 - R <= cx <= 250 + R and -47.5 - R <= cy <= 420 + R:
                    cells[c].append((round(cx, 1), round(cy, 1)))
    return cells


def build_hex(shots, cells):
    out = {}
    for p in PLAYERS:
        s = shots[(shots.PLAYER_NAME_QUERY == p) & (shots.SEASON == SEASON)]
        s = s[(s.LOC_Y <= 420) & (s.LOC_Y >= -47.5)]
        xs, ys, mk = s.LOC_X.values.astype(float), s.LOC_Y.values.astype(float), s.SHOT_MADE_FLAG.values.astype(float)
        cl = np.array([classify(a, b) for a, b in zip(xs, ys)])
        rec = {"N": int(len(s))}
        for c in CLASSES:
            m = cl == c
            sx, sy, sm = xs[m], ys[m], mk[m]
            prior = float(sm.mean()) if len(sm) else 0.4
            rows = []
            for idx, (cx, cy) in enumerate(cells[c]):
                if not len(sx):
                    break
                d2 = (sx - cx) ** 2 + (sy - cy) ** 2
                w = np.exp(-d2 / (2 * SIGMA ** 2))
                ws = w.sum()
                if ws < MIN_W:
                    continue
                fg = (float((w * sm).sum()) + PRIOR_K * prior) / (ws + PRIOR_K)
                rows.append([idx, int((d2 <= NEAR ** 2).sum()), round(100 * fg, 1)])
            rec[c] = rows
        out[p] = rec
    return out


def build_bands(d):
    d = d[d.SEASON == SEASON]
    res = {}
    for n, g in d.groupby("PLAYER_NAME"):
        if n not in PLAYERS:
            continue
        c = g.set_index("DEFENSE_CATEGORY")
        try:
            A = lambda cat, col: float(c.loc[cat, col])
            a3, m3, e3 = A("3 Pointers", "FG3A"), A("3 Pointers", "FG3M"), A("3 Pointers", "FG3A") * A("3 Pointers", "NS_FG3_PCT")
            a2, m2, e2 = A("2 Pointers", "FG2A"), A("2 Pointers", "FG2M"), A("2 Pointers", "FG2A") * A("2 Pointers", "NS_FG2_PCT")
            a6, m6 = A("Less Than 6Ft", "FGA_LT_06"), A("Less Than 6Ft", "FGM_LT_06"); e6 = a6 * A("Less Than 6Ft", "NS_LT_06_PCT")
            a10, m10 = A("Less Than 10Ft", "FGA_LT_10"), A("Less Than 10Ft", "FGM_LT_10"); e10 = a10 * A("Less Than 10Ft", "NS_LT_10_PCT")
            a15, m15 = A("Greater Than 15Ft", "FGA_GT_15"), A("Greater Than 15Ft", "FGM_GT_15"); e15 = a15 * A("Greater Than 15Ft", "NS_GT_15_PCT")
        except KeyError:
            print("skip", n); continue
        # "Greater Than 15Ft" includes threes, so long twos = GT15 - 3PT. 6-15ft = all twos - <6ft - long twos.
        al, ml, el = a15 - a3, m15 - m3, e15 - e3
        bands = {"b6": (a6, m6, e6), "b15": (a2 - a6 - al, m2 - m6 - ml, e2 - e6 - el), "bl": (al, ml, el), "b3": (a3, m3, e3)}
        res[n] = {k: {"n": int(a), "diff": round(100 * (m - e) / a, 1), "dfg": round(100 * m / a, 1), "exp": round(100 * e / a, 1)}
                  for k, (a, m, e) in bands.items() if a > 0}
    return res


def main():
    shots = pd.read_csv(ROOT / "data" / "raw_shot_chart.csv")
    cells = build_cells()
    hexd = build_hex(shots, cells)
    bands = build_bands(pd.read_csv(ROOT / "data" / "defend_by_zone.csv"))
    phi = shots[shots.TEAM_ID == 1610612755]
    pres = {p: set(g.GAME_ID.astype(str)) for p, g in phi.groupby("PLAYER_NAME_QUERY")}
    gs = {str(a): b for a, b in zip(phi.GAME_ID, phi.SEASON)}
    trio = ["Tyrese Maxey", "Joel Embiid", "VJ Edgecombe"]   # only players with real Sixers history together
    space = spacing.build(phi, pres, trio, trio, gs)
    blob = {"HEX": {"R": R, "cells": cells, "players": hexd}, "BANDS": bands, "SPACE_HIST": space}
    (ROOT / "tools" / "viz_data.json").write_text(json.dumps(blob, separators=(",", ":")))
    print({c: len(v) for c, v in cells.items()}, "bytes:", (ROOT / "tools" / "viz_data.json").stat().st_size)
    for p, r in hexd.items():
        print(f"  {p:26s} N={r['N']:5d}  cells drawn:", {c: len(r[c]) for c in CLASSES})


if __name__ == "__main__":
    main()
