"""
With / without teammate shot profiles.
For a player P and teammate T, splits P's shots into games where T also played ("with") and games
where T did not ("without"), and summarises each as zone-aware hex counts plus zone shares.
Used by tools/build_viz_data.py (history) and update_live.py (2026-27).
Caveat: this is game level (T played that game vs. didn't), not minute-by-minute on-court.
"""
import math
import numpy as np

R = 14.0        # hex radius, court units (1 unit = 0.1 ft)
NEAR = 45.0     # a hex counts shots within 4.5 ft of its center (smooths the with/without difference)
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


GROUP = {"ra": "rim", "lane": "rim", "mid": "mid", "three": "three"}


def build_cells(r=R):
    cells = {c: [] for c in CLASSES}
    dx, dy = 1.5 * r, math.sqrt(3) * r
    for i in range(-int(250 / dx) - 2, int(250 / dx) + 3):
        cx = i * dx
        off = 0.5 * dy if i % 2 else 0.0
        for j in range(int((-47.5 - r) / dy) - 2, int((420 + r) / dy) + 2):
            cy = j * dy + off
            pts = [(cx, cy)]
            for k in range(6):
                a = math.radians(60 * k); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
                b = math.radians(60 * k + 30); pts.append((cx + r * .866 * math.cos(b), cy + r * .866 * math.sin(b)))
            seen = {classify(px, py) for px, py in pts if -250 <= px <= 250 and -47.5 <= py <= 420}
            for c in seen:
                if -250 - r <= cx <= 250 + r and -47.5 - r <= cy <= 420 + r:
                    cells[c].append((round(cx, 1), round(cy, 1)))
    return cells


def condition_set(df, cells, games):
    xs = df.LOC_X.values.astype(float); ys = df.LOC_Y.values.astype(float); mk = df.SHOT_MADE_FLAG.values.astype(float)
    cl = np.array([classify(a, b) for a, b in zip(xs, ys)]) if len(df) else np.array([])
    out = {"N": int(len(df)), "games": int(games)}
    z = {}
    for g in ("rim", "mid", "three"):
        m = np.array([GROUP[c] == g for c in cl]) if len(cl) else np.array([], dtype=bool)
        n = int(m.sum())
        z[g] = {"n": n, "fg": round(100 * float(mk[m].mean()), 1) if n else None}
    out["zones"] = z
    for c in CLASSES:
        rows = []
        m = cl == c if len(cl) else np.array([], dtype=bool)
        sx, sy = xs[m], ys[m]
        if len(sx):
            for idx, (cx, cy) in enumerate(cells[c]):
                n = int((((sx - cx) ** 2 + (sy - cy) ** 2) <= NEAR ** 2).sum())
                if n:
                    rows.append([idx, n])
        out[c] = rows
    return out


def build(shots, presence, p_list, t_list, game_season=None):
    """shots: DataFrame with PLAYER_NAME_QUERY, GAME_ID, LOC_X, LOC_Y, SHOT_MADE_FLAG.
    presence: {player: set(GAME_ID)}. game_season: optional {GAME_ID: season}; when given, only seasons
    in which both players appeared are compared."""
    shots = shots[(shots.LOC_Y <= 420) & (shots.LOC_Y >= -47.5)].copy()
    shots["GAME_ID"] = shots.GAME_ID.astype(str)
    cells = build_cells()
    out = {"R": R, "cells": cells, "sets": {}}
    for p in p_list:
        sp = shots[shots.PLAYER_NAME_QUERY == p]
        pg = {str(g) for g in presence.get(p, set())}
        for t in t_list:
            if t == p:
                continue
            tg = {str(g) for g in presence.get(t, set())}
            if game_season:
                ps = {game_season[g] for g in pg if g in game_season}; ts = {game_season[g] for g in tg if g in game_season}
                common = ps & ts
                pg_use = {g for g in pg if game_season.get(g) in common}
            else:
                pg_use = pg
            gw, go = pg_use & tg, pg_use - tg
            if not gw and not go:
                continue
            out["sets"][f"{p}|{t}"] = {
                "with": condition_set(sp[sp.GAME_ID.isin(gw)], cells, len(gw)),
                "without": condition_set(sp[sp.GAME_ID.isin(go)], cells, len(go)),
            }
    return out
