# Sixers Sprawlball

**Live site:** https://hoffmanap.github.io/sixers/

A Kirk Goldsberry–style analysis of whether the 2026-27 76ers' star-stacked
roster (LeBron James, Jaylen Brown, Joel Embiid, Tyrese Maxey, VJ Edgecombe)
actually fits together. Built entirely on real shot-log, tracking, lineup,
and play-type data pulled via `nba_api`, 2022-23 through 2025-26 (24,505
shot attempts, plus lineup and Synergy play-type data).

## Findings

### 1. Spacing — Brown is the fit risk, not LeBron

2025-26 shot-zone splits (rim / mid-range / three, as % of FGA):

| Player     | Rim   | Mid-range | Three |
|------------|-------|-----------|-------|
| LeBron     | 56.4% | 17.2%     | 26.4% |
| Maxey      | 48.0% | 12.1%     | 40.0% |
| Brown      | 50.1% | 23.7%     | 26.2% |
| Edgecombe  | 45.9% | 13.2%     | 40.9% |
| Embiid     | 46.5% | 30.7%     | 22.8% |

Maxey and Edgecombe are the roster's Sprawlball-compliant players — under
15% mid-range each. The concerning trend: **Brown's mid-range rate nearly
doubled year over year**, from 14.3% in 2024-25 to 23.7% in 2025-26 — the
single biggest shot-profile swing on the roster, moving the wrong direction
right as he joins a team that needs him spacing the floor. Embiid's
mid-range share is also up (30.7%, his highest since 2023-24) — the
"modernized" version of his shot profile hasn't held steady either.

**Important nuance from the play-type data:** Brown's mid-range volume
isn't necessarily *bad* shot selection in isolation — his isolation
possessions (many of which end in pull-up mid-range Js) score at 1.013
points per possession, the **77th percentile leaguewide**, right behind
Embiid's isolation efficiency (1.015 PPP, 77th percentile). The spacing
risk isn't that Brown's shots are inefficient for him individually — it's
that a possession spent on a Brown mid-range iso is a possession where
four other players (three of them plus shooters) stand and watch instead
of moving, cutting, or drawing extra defensive attention. Efficient-for-him
and good-for-the-offense's floor geometry are two different questions, and
this roster has three or four players who could each make a credible case
for volume touches in that exact possession type.

### 2. Playmaking — Maxey is the engine, Embiid was never one

Synergy pick-and-roll ball-handler frequency (% of a player's offensive
possessions spent running the action) as the direct proxy for "who
initiates":

- **Maxey**: 28–35% every season, more than double anyone else on the
  roster, every year measured.
- **LeBron**: declining fast — 20.8% (2022-23) down to 11.7% (2025-26), a
  real, measurable step back from ball-handling duty.
- **Brown**: climbing — 16.8% up to 22.4% this season.
- **Embiid**: essentially 0% every single season. He has never been a
  pick-and-roll initiator; whatever playmaking he provides runs through
  the post or short roll, a structurally different mechanism — and his
  post-up efficiency (1.139 PPP, 79th percentile) backs that up as a real,
  productive alternate engine, not a consolation option.

One flag from the same data: **LeBron's post-up efficiency has fallen to
0.854 PPP, the 24th percentile leaguewide**, despite him running post-ups
on 13.4% of his possessions. That's a real decline signal sitting right
next to his falling ball-handling volume — LeBron is doing less
initiating *and* what initiating he does (via the post) is less efficient
than it used to be.

### 3. Maxey + Embiid fit — it's an availability problem, not a pace mismatch

On-court net rating for the Maxey-Embiid pairing specifically
(Per100Possessions):

| Season  | Minutes | Net Rating |
|---------|---------|------------|
| 2022-23 | 1201    | +10.6      |
| 2023-24 | 958     | +12.4      |
| 2024-25 | 389     | **-3.2**   |
| 2025-26 | 961     | +7.2       |

The pairing's net rating collapsed in 2024-25 — the exact season Embiid's
health limited him to a fraction of his normal shot volume — and recovered
this year alongside his health. Worth noting: **among every two-man
combination on the 2025-26 team with 600+ shared minutes, Maxey+Embiid
posts the single best net rating (+7.2)** — better than Maxey's pairings
with any other regular teammate this season. The data doesn't support a
genuine pace-and-space incompatibility between the two; it looks much more
like an availability problem wearing a scheme-fit costume.

### 4. Defense — Embiid and Brown are the anchors, LeBron is now a real minus

Defended FG% minus the shooter's normal FG% (negative = player suppresses
opponents below their own efficiency = good defense), 2025-26:

| Player     | Defended FG% vs. normal |
|------------|--------------------------|
| Brown      | -4.2                    |
| Embiid     | -4.1                    |
| Maxey      | +0.6                    |
| Edgecombe  | +0.7                    |
| LeBron     | +1.5                    |

Embiid and Brown are essentially tied as the roster's best individual
defenders by this measure. LeBron shows up as a measurable defensive
minus for the first time in this four-season window — combined with his
declining post-up efficiency and ball-handling volume above, this is the
clearest statistical evidence in the dataset that his role needs to keep
shrinking, not just stay flat, for this roster to work optimally.

## Bottom line

The roster's clearest strength is Maxey — rising usage, unmatched
ball-handling volume, clean shot profile, and (on the numbers) the best
on-court chemistry with Embiid of anyone on the team. The clearest risk
isn't Embiid's health or LeBron's age in isolation — both are real, but
expected and somewhat priced in — it's **Brown's shot profile moving
toward mid-range at the exact moment the offense needs him spacing it**,
combined with a genuine logjam of players (Maxey, LeBron, Brown, Embiid)
who each have a real, data-backed claim to shot-creation touches.

## Repo layout, regenerating the data, and caveats

```
sixers-sprawlball/
├── README.md
├── pull_shot_data.py     # nba_api script - regenerate the data yourself
├── data/                 # raw + derived CSVs (optional to keep in repo)
└── docs/                 # the GitHub Pages site (served from /docs)
    ├── index.html
    ├── css/style.css
    └── js/{data.js, chart.js, scrolly.js}
```

Regenerate with `pip install nba_api pandas && python pull_shot_data.py`
from a normal home/office network (stats.nba.com blocks most datacenter
IP ranges).

**Caveats:** shot-zone and playmaking splits are individual-player data
across prior teams/seasons, not simulated 76ers lineup data, since most of
this roster hasn't played a game together yet. Defended-FG%-vs.-normal and
PR-ball-handler-frequency are useful proxies, not perfect measures —
small-sample seasons (e.g. Embiid's 315 shots in 2024-25) should be read
with appropriate skepticism. All 2025-26 numbers are a season-in-progress
snapshot, not a final season total.
