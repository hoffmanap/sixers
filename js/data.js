// REAL DATA — derived from pull_shot_data.py output (24,505 shots, 2022-23
// through 2025-26). Zone splits computed from raw_shot_chart.csv;
// playmaking from playtypes.csv (Synergy PRBallHandler POSS_PCT); pace
// from speed_distance.csv + lineups_pairs_to_watch.csv; defense from
// defend_summary.csv (PCT_PLUSMINUS: negative = shooter held below their
// normal FG% = good defense).

// Shot-zone %, 2025-26 season (most recent full pull)
const SPACING_DATA = [
  { player: "Maxey",     rim: 48.0, mid: 12.1, three: 40.0 },
  { player: "Edgecombe", rim: 45.9, mid: 13.2, three: 40.9 },
  { player: "Embiid",    rim: 46.5, mid: 30.7, three: 22.8 },
  { player: "LeBron",    rim: 56.4, mid: 17.2, three: 26.4 },
  { player: "Brown",     rim: 50.1, mid: 23.7, three: 26.2 },
];

// Same players, all four seasons - powers the "Brown's mid-range creep"
// callout specifically
const SPACING_TRAJECTORY = {
  Brown: [
    { season: "2022-23", mid: 14.9 },
    { season: "2023-24", mid: 14.6 },
    { season: "2024-25", mid: 14.3 },
    { season: "2025-26", mid: 23.7 },
  ],
  Embiid: [
    { season: "2022-23", mid: 26.4 },
    { season: "2023-24", mid: 30.0 },
    { season: "2024-25", mid: 26.3 },
    { season: "2025-26", mid: 30.7 },
  ],
};

// Synergy PRBallHandler POSS_PCT by season - share of a player's offensive
// possessions spent as the pick-and-roll ball-handler. Best available
// direct proxy for "who's initiating."
const PLAYMAKING_DATA = [
  { player: "Maxey",  season: "2022-23", prbh: 32.9 },
  { player: "Maxey",  season: "2023-24", prbh: 35.0 },
  { player: "Maxey",  season: "2024-25", prbh: 33.1 },
  { player: "Maxey",  season: "2025-26", prbh: 28.5 },
  { player: "Brown",  season: "2022-23", prbh: 16.8 },
  { player: "Brown",  season: "2023-24", prbh: 16.3 },
  { player: "Brown",  season: "2024-25", prbh: 17.4 },
  { player: "Brown",  season: "2025-26", prbh: 22.4 },
  { player: "LeBron", season: "2022-23", prbh: 20.8 },
  { player: "LeBron", season: "2023-24", prbh: 18.7 },
  { player: "LeBron", season: "2024-25", prbh: 17.8 },
  { player: "LeBron", season: "2025-26", prbh: 11.7 },
  { player: "Embiid", season: "2022-23", prbh: 1.2 },
  { player: "Embiid", season: "2023-24", prbh: 1.2 },
  { player: "Embiid", season: "2024-25", prbh: 0.0 },
  { player: "Embiid", season: "2025-26", prbh: 0.0 },
];

// Miles run per game, Maxey vs. full-league average (no position filter
// available in this endpoint - labeled accordingly in the chart caption)
const PACE_DATA = [
  { season: "2022-23", maxey: 154.5 / 82, leagueAvg: 81.62 / 82 },
  { season: "2023-24", maxey: 200.7 / 82, leagueAvg: 77.63 / 82 },
  { season: "2024-25", maxey: 150.4 / 82, leagueAvg: 79.28 / 82 },
  { season: "2025-26", maxey: 194.9 / 82, leagueAvg: 75.88 / 82 },
];

// Maxey+Embiid on-court net rating by season (Per100Possessions) -
// the direct on/off answer to "does this pairing work"
const MAXEY_EMBIID_NET_RATING = [
  { season: "2022-23", minutes: 1201, netRating: 10.6, pace: 97.62 },
  { season: "2023-24", minutes: 958,  netRating: 12.4, pace: 101.85 },
  { season: "2024-25", minutes: 389,  netRating: -3.2, pace: 100.80 },
  { season: "2025-26", minutes: 961,  netRating: 7.2,  pace: 100.57 },
];

// PCT_PLUSMINUS, 2025-26 (x100): (defended FG% allowed) minus (shooter's
// normal FG%). Negative = player suppresses opponents below their usual
// efficiency = good individual defense.
const DEFENSE_DATA = [
  { player: "Maxey",     pctPlusMinus: 0.6 },
  { player: "Edgecombe", pctPlusMinus: 0.7 },
  { player: "Embiid",    pctPlusMinus: -4.1 },
  { player: "LeBron",    pctPlusMinus: 1.5 },
  { player: "Brown",     pctPlusMinus: -4.2 },
];
