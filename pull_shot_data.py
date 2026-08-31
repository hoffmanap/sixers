"""
Sixers Sprawlball Data Puller
==============================
Pulls shot chart + zone + tracking data for a set of players across multiple
seasons, using the (unofficial but excellent) `nba_api` wrapper around
stats.nba.com.

WHY THIS MIGHT NOT WORK IN A SANDBOX / CLOUD ENV
-------------------------------------------------
stats.nba.com aggressively blocks requests from datacenter / cloud IP ranges
(AWS, GCP, Azure, and by extension most hosted notebooks/agents). It's much
more permissive of normal home/residential IPs. If you get repeated
ReadTimeout / 403 errors:
  1. Run this from a normal laptop on a home network, not a VM.
  2. Add delays between calls (already built in below) - stats.nba.com rate
     limits aggressively.
  3. If it's still flaky, consider a paid alternative like pbpstats.com's API
     or scraping Basketball-Reference's shooting/pbp pages (see note at
     bottom of this file).

SETUP
-----
    pip install nba_api pandas

USAGE
-----
    python pull_shot_data.py

Edit PLAYERS / SEASONS below to change scope. Output lands in ./data/ as
both raw per-shot CSVs and a rolled-up zone-summary CSV you can plug
straight into the site's data/ folder.
"""

import time
import json
from pathlib import Path

import pandas as pd
from nba_api.stats.static import players as static_players, teams as static_teams
from nba_api.stats.endpoints import (
    shotchartdetail,
    playerdashboardbyshootingsplits,
    leaguedashptstats,      # speed/distance tracking (Maxey's game)
    leaguedashptdefend,     # defensive tracking (drop coverage etc.)
    leaguedashlineups,      # on/off pairs - e.g. Maxey+Embiid vs. Maxey w/o Embiid
    synergyplaytypes,       # who's initiating what (PnR ball-handler, iso, spot-up...)
)

OUT_DIR = Path(__file__).parent / "data"
OUT_DIR.mkdir(exist_ok=True)

# ---- Configure your player pool -------------------------------------------
PLAYERS = [
    "Tyrese Maxey",
    "Joel Embiid",
    "LeBron James",
    "Jaylen Brown",
    "VJ Edgecombe",
    "Kyle Lowry",
    "Eric Gordon",
    "Kentavious Caldwell-Pope",
    "Jared McCain",
]

# Multi-season so you can track shot-profile drift over time, not just a
# single-season snapshot.
SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26"]

REQUEST_DELAY_SEC = 1.2  # be polite / avoid rate-limit bans

# 2-man lineup combos to check on/off fit for - edit as the real roster
# settles. These are name pairs; resolved to IDs at runtime.
LINEUP_PAIRS_TO_WATCH = [
    ("Tyrese Maxey", "Joel Embiid"),
    ("Tyrese Maxey", "VJ Edgecombe"),
    ("LeBron James", "Jaylen Brown"),
    ("Joel Embiid", "Jaylen Brown"),
]

PHI_TEAM_ID = 1610612755


def get_player_id(full_name: str) -> int | None:
    matches = static_players.find_players_by_full_name(full_name)
    if not matches:
        print(f"  !! No player_id found for '{full_name}'")
        return None
    return matches[0]["id"]


def pull_shot_chart(player_id: int, player_name: str, season: str) -> pd.DataFrame:
    """Every shot attempt with x/y court coords, shot zone, made/miss."""
    resp = shotchartdetail.ShotChartDetail(
        team_id=0,
        player_id=player_id,
        season_nullable=season,
        season_type_all_star="Regular Season",
        context_measure_simple="FGA",
        timeout=30,
    )
    df = resp.get_data_frames()[0]
    df["PLAYER_NAME_QUERY"] = player_name
    df["SEASON"] = season
    return df


def pull_zone_summary(player_id: int, player_name: str, season: str) -> pd.DataFrame:
    """Pre-aggregated FG%/FGA by shot zone/distance — good for the
    rim / mid-range / three bar chart without processing raw shot coords."""
    resp = playerdashboardbyshootingsplits.PlayerDashboardByShootingSplits(
        player_id=player_id,
        season=season,
        season_type_playoffs="Regular Season",
        timeout=30,
    )
    frames = resp.get_data_frames()
    # 'ShotAreaPlayerDashboard' index varies by nba_api version; find it by name
    zone_df = None
    for f in frames:
        if "GROUP_VALUE" in f.columns and "FG_PCT" in f.columns:
            zone_df = f
            break
    if zone_df is None:
        return pd.DataFrame()
    zone_df = zone_df.copy()
    zone_df["PLAYER_NAME_QUERY"] = player_name
    zone_df["SEASON"] = season
    return zone_df


def pull_speed_distance(season: str) -> pd.DataFrame:
    """League-wide speed/distance tracking — this is your Maxey-vs-Embiid
    data: avg speed, distance run per game, by player, for one season."""
    resp = leaguedashptstats.LeagueDashPtStats(
        season=season,
        season_type_all_star="Regular Season",
        player_or_team="Player",
        pt_measure_type="SpeedDistance",
        timeout=30,
    )
    df = resp.get_data_frames()[0]
    df["SEASON"] = season
    return df


def pull_drop_coverage_defense(season: str) -> pd.DataFrame:
    """Defender-tracking splits (e.g. rim protection numbers for Embiid)."""
    resp = leaguedashptdefend.LeagueDashPtDefend(
        season=season,
        season_type_all_star="Regular Season",
        defense_category="Overall",
        timeout=30,
    )
    df = resp.get_data_frames()[0]
    df["SEASON"] = season
    return df


def pull_lineups(season: str, min_group_size: int = 2) -> pd.DataFrame:
    """All 76ers 2-man combos with minutes, net rating, on-court numbers.
    This is how you actually answer 'does X fit with Y' - not shot profiles
    in isolation, but what the team's net rating looks like when specific
    pairs share the floor."""
    resp = leaguedashlineups.LeagueDashLineups(
        team_id_nullable=PHI_TEAM_ID,
        season=season,
        season_type_all_star="Regular Season",
        group_quantity=min_group_size,
        measure_type_detailed_defense="Advanced",
        per_mode_detailed="Per100Possessions",
        timeout=30,
    )
    df = resp.get_data_frames()[0]
    df["SEASON"] = season
    return df


def pull_playtypes(season: str) -> pd.DataFrame:
    """Synergy play-type frequency/efficiency league-wide, one call per
    play type per season - e.g. who's actually the pick-and-roll
    ball-handler vs. who's a roll man vs. who's parked in spot-up
    situations. This is the real answer to 'who's the facilitator'."""
    play_types = [
        "Isolation",
        "PRBallHandler",
        "PRRollman",
        "Postup",
        "Spotup",
        "Handoff",
        "Cut",
        "OffScreen",
        "Transition",
    ]
    frames = []
    for pt in play_types:
        try:
            resp = synergyplaytypes.SynergyPlayTypes(
                season=season,
                season_type_all_star="Regular Season",
                player_or_team_abbreviation="P",
                play_type_nullable=pt,
                type_grouping_nullable="offensive",
                timeout=30,
            )
            df = resp.get_data_frames()[0]
            df["PLAY_TYPE"] = pt
            df["SEASON"] = season
            frames.append(df)
            time.sleep(REQUEST_DELAY_SEC)
        except Exception as e:
            print(f"    playtype {pt} {season} FAILED ({e})")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def main():
    all_shots = []
    all_zones = []

    for name in PLAYERS:
        pid = get_player_id(name)
        if pid is None:
            continue
        print(f"{name} (id={pid})")
        for season in SEASONS:
            try:
                shots = pull_shot_chart(pid, name, season)
                if not shots.empty:
                    all_shots.append(shots)
                    print(f"    {season}: {len(shots)} shots")
                time.sleep(REQUEST_DELAY_SEC)

                zones = pull_zone_summary(pid, name, season)
                if not zones.empty:
                    all_zones.append(zones)
                time.sleep(REQUEST_DELAY_SEC)
            except Exception as e:
                print(f"    {season}: FAILED ({e})")
                time.sleep(REQUEST_DELAY_SEC)

    if all_shots:
        shots_df = pd.concat(all_shots, ignore_index=True)
        shots_df.to_csv(OUT_DIR / "raw_shot_chart.csv", index=False)
        print(f"\nWrote {len(shots_df)} rows -> data/raw_shot_chart.csv")

    if all_zones:
        zones_df = pd.concat(all_zones, ignore_index=True)
        zones_df.to_csv(OUT_DIR / "zone_summary.csv", index=False)
        print(f"Wrote {len(zones_df)} rows -> data/zone_summary.csv")

    # League-wide tracking pulls (one call per season, not per-player) -
    # these come back with EVERY player in the league, so we filter down
    # to our roster before saving.
    speed_frames, defend_frames = [], []
    for season in SEASONS:
        try:
            speed_frames.append(pull_speed_distance(season))
            time.sleep(REQUEST_DELAY_SEC)
        except Exception as e:
            print(f"SpeedDistance {season} FAILED ({e})")
        try:
            defend_frames.append(pull_drop_coverage_defense(season))
            time.sleep(REQUEST_DELAY_SEC)
        except Exception as e:
            print(f"Defend {season} FAILED ({e})")

    if speed_frames:
        speed_df = pd.concat(speed_frames, ignore_index=True)
        speed_df.to_csv(OUT_DIR / "speed_distance_league.csv", index=False)
        speed_df[speed_df["PLAYER_NAME"].isin(PLAYERS)].to_csv(
            OUT_DIR / "speed_distance.csv", index=False
        )
        print("Wrote data/speed_distance.csv (+ _league.csv full version)")

    if defend_frames:
        defend_df = pd.concat(defend_frames, ignore_index=True)
        defend_df.to_csv(OUT_DIR / "defend_summary_league.csv", index=False)
        # column is usually CLOSE_DEF_PERSON_ID / PLAYER_NAME depending on
        # nba_api version - print columns once if this filter comes up empty
        name_col = "PLAYER_NAME" if "PLAYER_NAME" in defend_df.columns else "CLOSE_DEF_PERSON_ID"
        if name_col == "PLAYER_NAME":
            defend_df[defend_df["PLAYER_NAME"].isin(PLAYERS)].to_csv(
                OUT_DIR / "defend_summary.csv", index=False
            )
        print("Wrote data/defend_summary.csv (+ _league.csv full version)")

    # 76ers-specific lineup on/off data - answers "does X fit with Y"
    # directly via net rating, not shot-profile inference.
    lineup_frames = []
    for season in SEASONS:
        try:
            lu = pull_lineups(season)
            if not lu.empty:
                lineup_frames.append(lu)
                print(f"Lineups {season}: {len(lu)} 2-man combos")
            time.sleep(REQUEST_DELAY_SEC)
        except Exception as e:
            print(f"Lineups {season} FAILED ({e})")
    if lineup_frames:
        lineups_df = pd.concat(lineup_frames, ignore_index=True)
        lineups_df.to_csv(OUT_DIR / "lineups_2man.csv", index=False)
        print("Wrote data/lineups_2man.csv")
        # Highlight just the pairs we actually care about, if both players
        # were on the 76ers that season (won't match for pre-trade seasons -
        # that's expected, not a bug)
        watch_rows = []
        for a, b in LINEUP_PAIRS_TO_WATCH:
            mask = lineups_df["GROUP_NAME"].str.contains(a.split()[-1], na=False) & \
                   lineups_df["GROUP_NAME"].str.contains(b.split()[-1], na=False)
            watch_rows.append(lineups_df[mask])
        watched = pd.concat(watch_rows, ignore_index=True) if watch_rows else pd.DataFrame()
        if not watched.empty:
            watched.to_csv(OUT_DIR / "lineups_pairs_to_watch.csv", index=False)
            print("Wrote data/lineups_pairs_to_watch.csv (filtered to LINEUP_PAIRS_TO_WATCH)")

    # League-wide play-type frequency/efficiency - who's initiating what
    playtype_frames = []
    for season in SEASONS:
        try:
            pt = pull_playtypes(season)
            if not pt.empty:
                playtype_frames.append(pt)
        except Exception as e:
            print(f"Playtypes {season} FAILED ({e})")
    if playtype_frames:
        pt_df = pd.concat(playtype_frames, ignore_index=True)
        pt_df.to_csv(OUT_DIR / "playtypes_league.csv", index=False)
        name_col = "PLAYER_NAME" if "PLAYER_NAME" in pt_df.columns else None
        if name_col:
            pt_df[pt_df["PLAYER_NAME"].isin(PLAYERS)].to_csv(
                OUT_DIR / "playtypes.csv", index=False
            )
            print("Wrote data/playtypes.csv (+ _league.csv full version)")


if __name__ == "__main__":
    main()

# -----------------------------------------------------------------------
# FALLBACK: Basketball-Reference scrape (no official API, be gentle -
# add delays, respect robots.txt, this is for personal research use)
# -----------------------------------------------------------------------
# If stats.nba.com is unreachable even locally, basketball-reference.com
# publishes shooting-by-distance tables per player/season at URLs like:
#   https://www.basketball-reference.com/players/j/jamesle01/shooting/2026
# You can pull these with `pandas.read_html()` directly - no scraping
# framework needed:
#
#   import pandas as pd
#   tables = pd.read_html(
#       "https://www.basketball-reference.com/players/j/jamesle01/shooting/2026"
#   )
#   # inspect `tables` to find the by-distance FG%/FGA breakdown table
#
# Basketball-Reference player IDs follow last-name(5)+first-name(2)+00
# pattern (e.g. jamesle01), with a suffix number bumped for name
# collisions - easiest to grab the exact ID from the URL when you look
# the player up on the site once.
