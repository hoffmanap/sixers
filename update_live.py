"""
Sixers live tracker: predicted vs actual
=========================================
Pulls 2026-27 season-to-date data from stats.nba.com (via nba_api), turns it
into the metrics defined in predictions.json, compares them to the 2025-26
baselines in baselines.json, and writes docs/live_data.json for the site's
"Live tracker" tab.

    python update_live.py                      # normal run (needs a home/office IP)
    python update_live.py --make-baselines --data-dir data   # rebuild baselines.json from your CSV pulls
    python update_live.py --replay-csv data --replay-season 2025-26 --out replay.json
                                               # offline self-test: runs the SAME metric code on old CSVs

stats.nba.com blocks most cloud IPs. If the GitHub Action times out, run this
locally (run_update.bat on Windows) - see README.
"""
import argparse, json, sys, time, datetime as dt
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent
SEASON = "2026-27"
PHI = 1610612755
DELAY = 1.2
PLAYERS = ["Tyrese Maxey", "Joel Embiid", "LeBron James", "Jaylen Brown", "VJ Edgecombe",
           "Dean Wade", "Anfernee Simons", "Kentavious Caldwell-Pope", "Adem Bona", "Ariel Hukporti"]
# short key -> (last-name token used to match lineup GROUP_NAME, full name)
PAIRS = [("Maxey", "Embiid"), ("Maxey", "Edgecombe"), ("James", "Brown"), ("Embiid", "Brown"),
         ("Wade", "Maxey"), ("Wade", "Brown"), ("Simons", "Maxey"), ("Bona", "Maxey"), ("Hukporti", "Maxey")]
ZONE = {"Restricted Area": "rim", "In The Paint (Non-RA)": "rim", "Mid-Range": "mid",
        "Above the Break 3": "three", "Left Corner 3": "three", "Right Corner 3": "three"}


def last(name):  # "Kentavious Caldwell-Pope" -> "Caldwell-Pope"
    return name.split(" ", 1)[1] if " " in name else name


# ---------------------------------------------------------------- compute (pure functions)
def shot_profile(shots):
    out = {}
    for p, g in shots.groupby("PLAYER_NAME_QUERY"):
        g = g.assign(z=g.SHOT_ZONE_BASIC.map(ZONE)).dropna(subset=["z"])
        n = len(g)
        if n == 0:
            continue
        row = {"fga": n}
        for z in ("rim", "mid", "three"):
            s = g[g.z == z]
            row[z] = round(100 * len(s) / n, 1)
            row[z + "_fg"] = round(100 * s.SHOT_MADE_FLAG.mean(), 1) if len(s) else None
        out[p] = row
    return out


def cumulative_trend(shots, player, zone="mid", min_fga=30):
    """Season-to-date zone share after each game date (real backfill, no snapshots needed)."""
    g = shots[shots.PLAYER_NAME_QUERY == player].copy()
    g["z"] = g.SHOT_ZONE_BASIC.map(ZONE)
    g = g.dropna(subset=["z"]).sort_values("GAME_DATE")
    pts, n, k = [], 0, 0
    for d, day in g.groupby("GAME_DATE", sort=True):
        n += len(day); k += int((day.z == zone).sum())
        if n >= min_fga:
            pts.append({"date": f"{str(d)[:4]}-{str(d)[4:6]}-{str(d)[6:8]}", "value": round(100 * k / n, 1), "n": n})
    return pts


def defense_table(d):
    out = {}
    for _, r in d.iterrows():
        if r.PLAYER_NAME in PLAYERS:
            out[r.PLAYER_NAME] = {"diff": round(100 * float(r.PCT_PLUSMINUS), 1), "fga": int(r.D_FGA),
                                  "d_fg": round(100 * float(r.D_FG_PCT), 1), "gp": int(r.GP)}
    return out


def speed_table(s):
    return {r.PLAYER_NAME: {"speed": float(r.AVG_SPEED), "gp": int(r.GP)} for _, r in s.iterrows() if r.PLAYER_NAME in PLAYERS}


def pair_table(l):
    out = {}
    for a, b in PAIRS:
        hit = l[l.GROUP_NAME.apply(lambda g: a in g and b in g)]
        if len(hit):
            r = hit.sort_values("MIN", ascending=False).iloc[0]
            out[f"{a}|{b}"] = {"min": round(float(r.MIN), 0), "net": round(float(r.NET_RATING), 1),
                               "off": round(float(r.OFF_RATING), 1), "def": round(float(r.DEF_RATING), 1)}
    return out


def prbh_share(pt, name):
    r = pt[(pt.PLAYER_NAME == name) & (pt.PLAY_TYPE == "PRBallHandler")]
    return (round(100 * float(r.iloc[0].POSS_PCT), 1), int(r.iloc[0].POSS)) if len(r) else (None, 0)


def compute_metrics(shots, defense, pairs, playtypes, team, players_gp):
    """-> {metric_id: {value, n}} using the ids in predictions.json."""
    m = {}
    sp = shot_profile(shots) if len(shots) else {}
    b = sp.get("Jaylen Brown")
    m["brown_mid"] = {"value": b["mid"], "n": b["fga"]} if b else {"value": None, "n": 0}
    emb_gp = players_gp.get("Joel Embiid")
    tgp = team.get("gp") if team else None
    m["embiid_games"] = ({"value": round(emb_gp / tgp * 82, 1), "n": tgp} if emb_gp is not None and tgp else {"value": None, "n": 0})
    p = pairs.get("Maxey|Embiid")
    m["maxey_embiid_net"] = {"value": p["net"], "n": p["min"]} if p else {"value": None, "n": 0}
    v, n = prbh_share(playtypes, "LeBron James") if len(playtypes) else (None, 0)
    m["lebron_prbh"] = {"value": v, "n": n}
    for key, nm in (("lebron_def", "LeBron James"), ("kcp_def", "Kentavious Caldwell-Pope")):
        d = defense.get(nm)
        m[key] = {"value": d["diff"], "n": d["fga"]} if d else {"value": None, "n": 0}
    m["team_off_rank"] = {"value": team.get("off_rank"), "n": team.get("gp", 0)} if team else {"value": None, "n": 0}
    m["team_def_rank"] = {"value": team.get("def_rank"), "n": team.get("gp", 0)} if team else {"value": None, "n": 0}
    return m


def verdict(pred, cur):
    v, n = cur["value"], cur["n"]
    if v is None:
        return "awaiting"
    if n < pred["min_n"]:
        return "early"
    ok = v <= pred["target"] if pred["direction"] == "lower" else v >= pred["target"]
    return "on_track" if ok else "off_track"


# ---------------------------------------------------------------- stats.nba.com pulls
def _call(fn, retries=3, **kw):
    for i in range(retries):
        try:
            df = fn(timeout=60, **kw).get_data_frames()[0]
            time.sleep(DELAY)
            return df
        except Exception as e:
            print(f"    retry {i+1}/{retries}: {type(e).__name__}: {str(e)[:90]}")
            time.sleep(3 * (i + 1))
    raise RuntimeError("stats.nba.com unreachable (cloud IPs are often blocked - run locally)")


def pull_live(season):
    from nba_api.stats.static import players as sp
    from nba_api.stats.endpoints import (shotchartdetail, leaguedashptdefend, leaguedashptstats,
                                         leaguedashlineups, synergyplaytypes,
                                         leaguedashplayerstats, leaguedashteamstats)
    shots = []
    for name in PLAYERS:
        hit = sp.find_players_by_full_name(name)
        if not hit:
            continue
        df = _call(shotchartdetail.ShotChartDetail, team_id=0, player_id=hit[0]["id"], season_nullable=season,
                   season_type_all_star="Regular Season", context_measure_simple="FGA")
        if len(df):
            df["PLAYER_NAME_QUERY"] = name
            shots.append(df)
    shots = pd.concat(shots, ignore_index=True) if shots else pd.DataFrame(columns=["PLAYER_NAME_QUERY"])
    defense = _call(leaguedashptdefend.LeagueDashPtDefend, season=season, season_type_all_star="Regular Season",
                    defense_category="Overall")
    speed = _call(leaguedashptstats.LeagueDashPtStats, season=season, season_type_all_star="Regular Season",
                  player_or_team="Player", pt_measure_type="SpeedDistance")
    lineups = _call(leaguedashlineups.LeagueDashLineups, team_id_nullable=PHI, season=season,
                    season_type_all_star="Regular Season", group_quantity=2,
                    measure_type_detailed_defense="Advanced", per_mode_detailed="Per100Possessions")
    pt = _call(synergyplaytypes.SynergyPlayTypes, season=season, season_type_all_star="Regular Season",
               player_or_team_abbreviation="P", play_type_nullable="PRBallHandler", type_grouping_nullable="offensive")
    pt["PLAY_TYPE"] = "PRBallHandler"
    pstats = _call(leaguedashplayerstats.LeagueDashPlayerStats, season=season, team_id_nullable=PHI,
                   season_type_all_star="Regular Season")
    tstats = _call(leaguedashteamstats.LeagueDashTeamStats, season=season, season_type_all_star="Regular Season",
                   measure_type_detailed_defense="Advanced", per_mode_detailed="Per100Possessions")
    return shots, defense, speed, lineups, pt, pstats, tstats


def team_row(tstats):
    r = tstats[tstats.TEAM_ID == PHI]
    if r.empty:
        return {}
    r = r.iloc[0]
    return {"gp": int(r.GP), "w": int(r.W), "l": int(r.L), "off_rtg": float(r.OFF_RATING), "def_rtg": float(r.DEF_RATING),
            "net_rtg": float(r.NET_RATING), "off_rank": int(r.OFF_RATING_RANK), "def_rank": int(r.DEF_RATING_RANK)}


# ---------------------------------------------------------------- assemble
def assemble(season, shots, defense, speed, lineups, pt, pstats, tstats, preds, base, history):
    d_tab, s_tab, p_tab = defense_table(defense), speed_table(speed), pair_table(lineups)
    team = team_row(tstats) if tstats is not None and len(tstats) else {}
    gp = {r.PLAYER_NAME: int(r.GP) for _, r in pstats.iterrows()} if pstats is not None and len(pstats) else {}
    met = compute_metrics(shots, d_tab, p_tab, pt, team, gp)
    for p in preds["predictions"]:
        met[p["id"]]["status"] = verdict(p, met[p["id"]])
    today = dt.date.today().isoformat()
    snap = {"date": today, "values": {k: v["value"] for k, v in met.items()}, "n": {k: v["n"] for k, v in met.items()}}
    history = [h for h in history if h["date"] != today] + [snap]
    has_data = any(v["value"] is not None for v in met.values())
    return {"season": season, "status": "ok" if has_data else "awaiting",
            "updated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "team": team, "metrics": met, "zones": shot_profile(shots) if len(shots) else {},
            "defense": d_tab, "speed": s_tab, "pairs": p_tab, "games_played": gp,
            "trend": {"brown_mid": cumulative_trend(shots, "Jaylen Brown")} if len(shots) else {},
            "history": history, "predictions": preds["predictions"], "baselines": base}


# ---------------------------------------------------------------- baselines / replay from CSVs
def load_csv_frames(data_dir, season):
    d = Path(data_dir)
    rd = lambda f: pd.read_csv(d / f)
    shots = rd("raw_shot_chart.csv"); shots = shots[shots.SEASON == season]
    defense = rd("defend_summary.csv"); defense = defense[defense.SEASON == season]
    speed = rd("speed_distance.csv"); speed = speed[speed.SEASON == season]
    lineups = rd("lineups_2man.csv"); lineups = lineups[lineups.SEASON == season]
    pt = rd("playtypes.csv"); pt = pt[pt.SEASON == season]
    return shots, defense, speed, lineups, pt


def baselines_from_csv(data_dir, season, preds):
    shots, defense, speed, lineups, pt = load_csv_frames(data_dir, season)
    d_tab, s_tab, p_tab = defense_table(defense), speed_table(speed), pair_table(lineups)
    emb = d_tab.get("Joel Embiid", {}).get("gp")
    team = {"gp": 82, "off_rank": None, "def_rank": None}
    met = compute_metrics(shots, d_tab, p_tab, pt, team, {"Joel Embiid": emb} if emb else {})
    base_metrics = {k: v["value"] for k, v in met.items() if v["value"] is not None}
    return {"season": season, "metrics": base_metrics, "zones": shot_profile(shots), "defense": d_tab, "speed": s_tab,
            "pairs": p_tab, "brown_mid_norm": 14.3,
            "note": "team_off_rank/team_def_rank have no 2025-26 baseline file; add them by hand if you want one."}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "live_data.json"))
    ap.add_argument("--make-baselines", action="store_true")
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--replay-csv"); ap.add_argument("--replay-season", default="2025-26")
    a = ap.parse_args()
    preds = json.loads((ROOT / "predictions.json").read_text())
    if a.make_baselines:
        b = baselines_from_csv(a.data_dir, "2025-26", preds)
        (ROOT / "baselines.json").write_text(json.dumps(b, indent=1)); print("wrote baselines.json"); return
    base = json.loads((ROOT / "baselines.json").read_text())
    out = Path(a.out)
    history = json.loads(out.read_text()).get("history", []) if out.exists() and not a.replay_csv else []
    if a.replay_csv:
        shots, defense, speed, lineups, pt = load_csv_frames(a.replay_csv, a.replay_season)
        gp = {"Joel Embiid": int(defense[defense.PLAYER_NAME == "Joel Embiid"].GP.iloc[0])}
        tstats = pd.DataFrame([{"TEAM_ID": PHI, "GP": 82, "W": 45, "L": 37, "OFF_RATING": 116.0, "DEF_RATING": 114.0,
                                "NET_RATING": 2.0, "OFF_RATING_RANK": 7, "DEF_RATING_RANK": 14}])
        pstats = pd.DataFrame([{"PLAYER_NAME": k, "GP": v} for k, v in gp.items()])
        res = assemble(a.replay_season + " (REPLAY)", shots, defense, speed, lineups, pt, pstats, tstats, preds, base, [])
    else:
        try:
            shots, defense, speed, lineups, pt, pstats, tstats = pull_live(SEASON)
        except Exception as e:
            print("PULL FAILED:", e); sys.exit(1)
        res = assemble(SEASON, shots, defense, speed, lineups, pt, pstats, tstats, preds, base, history)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, default=str))
    print(f"wrote {out}  status={res['status']}")
    for p in preds["predictions"]:
        c = res["metrics"][p["id"]]
        print(f"  {p['title'][:48]:48s} value={c['value']} n={c['n']} -> {c['status']}")


if __name__ == "__main__":
    main()
