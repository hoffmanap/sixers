# Sixers Sprawlball

A Kirk Goldsberry–style analysis of whether the 2026-27 76ers' star-stacked
roster (LeBron James, Jaylen Brown, Joel Embiid, Tyrese Maxey, VJ Edgecombe)
actually fits together — spacing, playmaking hierarchy, pace/mobility, and
defense.

## Repo layout

```
pull_shot_data.py     # nba_api script - pulls real shot/tracking data
data/                 # CSV output lands here (gitignored - regenerate locally)
site/                 # the GitHub Pages scrollytelling site
  index.html
  css/style.css
  js/data.js           # <- point this at your real pulled data
  js/chart.js
  js/scrolly.js
```

## 1. Pull the data

```bash
pip install nba_api pandas
python pull_shot_data.py
```

**Run this from a normal home/office network, not a cloud VM or CI runner —
stats.nba.com blocks most datacenter IP ranges.** It writes four CSVs to
`data/`: `raw_shot_chart.csv`, `zone_summary.csv`, `speed_distance.csv`,
`defend_summary.csv`, across the players and seasons configured at the top
of the script.

## 2. Feed it into the site

The site currently runs on placeholder numbers in `site/js/data.js` (labeled
as estimates in the write-up until real data replaces them). Convert your
pulled CSVs to the shapes `data.js` expects — e.g. in a notebook:

```python
import pandas as pd
zones = pd.read_csv("data/zone_summary.csv")
# reshape to [{player, rim, mid, three}, ...] per your zone-grouping logic,
# then paste as SPACING_DATA in site/js/data.js (or fetch it as JSON at
# runtime instead of hardcoding - either works for GitHub Pages)
```

## 3. Publish

Push `site/` to a `gh-pages` branch (or point GitHub Pages at `/site` in
repo settings) and it's live — no build step, it's plain HTML/CSS/JS + D3
loaded from a CDN.

## Design notes

Editorial scrollytelling layout: sticky chart on the right, annotated prose
scrolling on the left, one research question per chapter. The chart swaps
automatically as each chapter enters view. Key stat claims get a
hand-drawn highlighter-style underline that draws in on scroll — see
`mark` rules in `style.css` if you want to reuse that elsewhere.
