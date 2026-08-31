const svg = d3.select("#chart");
const W = 640, H = 520, M = { top: 30, right: 30, bottom: 60, left: 60 };
const caption = document.getElementById("chart-caption");

const navy = "#04275C";
const ink = "#1A1A1A";
const inkSoft = "#4A4640";
const risk = "#C1440E";
const paletteZone = { rim: "#04275C", mid: "#C1440E", three: "#7A8B5C" };

function clear() { svg.selectAll("*").remove(); }

function renderSpacing() {
  clear();
  caption.textContent = "Real shot-zone distribution, 2025-26 season (% of FGA) — five 76ers starters";
  const zones = ["rim", "mid", "three"];
  const x0 = d3.scaleBand().domain(SPACING_DATA.map(d => d.player)).range([M.left, W - M.right]).padding(0.3);
  const x1 = d3.scaleBand().domain(zones).range([0, x0.bandwidth()]).padding(0.08);
  const y = d3.scaleLinear().domain([0, 60]).range([H - M.bottom, M.top]);

  svg.append("g").attr("transform", `translate(0,${H - M.bottom})`)
    .call(d3.axisBottom(x0).tickSize(0)).call(g => g.select(".domain").attr("stroke", "#D9D2C2"))
    .selectAll("text").attr("font-family", "IBM Plex Sans").attr("font-size", 12).attr("fill", ink);

  svg.append("g").attr("transform", `translate(${M.left},0)`)
    .call(d3.axisLeft(y).ticks(6).tickSize(-(W - M.left - M.right)))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").attr("stroke", "#EDE8DC"))
    .selectAll("text").attr("font-family", "IBM Plex Mono").attr("font-size", 10).attr("fill", inkSoft);

  const groups = svg.selectAll(".pgroup").data(SPACING_DATA).enter().append("g")
    .attr("transform", d => `translate(${x0(d.player)},0)`);

  groups.selectAll("rect").data(d => zones.map(z => ({ zone: z, val: d[z], player: d.player })))
    .enter().append("rect")
    .attr("x", d => x1(d.zone)).attr("width", x1.bandwidth())
    .attr("y", H - M.bottom).attr("height", 0)
    .attr("fill", d => paletteZone[d.zone])
    .transition().duration(600).delay((d, i) => i * 60)
    .attr("y", d => y(d.val)).attr("height", d => (H - M.bottom) - y(d.val));

  const legend = svg.append("g").attr("transform", `translate(${M.left},${M.top - 15})`);
  zones.forEach((z, i) => {
    const g = legend.append("g").attr("transform", `translate(${i * 90},0)`);
    g.append("rect").attr("width", 10).attr("height", 10).attr("fill", paletteZone[z]);
    g.append("text").attr("x", 15).attr("y", 9).attr("font-family", "IBM Plex Mono")
      .attr("font-size", 10).attr("fill", inkSoft).text(z);
  });
}

function renderPlaymaking() {
  clear();
  caption.textContent = "Pick-and-roll ball-handler frequency (% of offensive possessions), by season";
  const seasons = [...new Set(PLAYMAKING_DATA.map(d => d.season))].sort();
  const x = d3.scalePoint().domain(seasons).range([M.left, W - M.right]).padding(0.5);
  const y = d3.scaleLinear().domain([0, 40]).range([H - M.bottom, M.top]);
  const players = [...new Set(PLAYMAKING_DATA.map(d => d.player))];
  const color = d3.scaleOrdinal().domain(players).range([navy, risk, "#7A8B5C", "#8A6BB0"]);

  svg.append("g").attr("transform", `translate(0,${H - M.bottom})`)
    .call(d3.axisBottom(x)).call(g => g.select(".domain").attr("stroke", "#D9D2C2"))
    .selectAll("text").attr("font-family", "IBM Plex Mono").attr("font-size", 10).attr("fill", inkSoft);

  svg.append("g").attr("transform", `translate(${M.left},0)`)
    .call(d3.axisLeft(y).ticks(5).tickSize(-(W - M.left - M.right)))
    .call(g => g.select(".domain").remove())
    .call(g => g.selectAll(".tick line").attr("stroke", "#EDE8DC"))
    .selectAll("text").attr("font-family", "IBM Plex Mono").attr("font-size", 10).attr("fill", inkSoft);
  svg.append("text").attr("transform", "rotate(-90)").attr("x", -H / 2).attr("y", 18)
    .attr("text-anchor", "middle").attr("font-family", "IBM Plex Sans").attr("font-size", 11)
    .attr("fill", inkSoft).text("PR ball-handler poss. %");

  players.forEach(p => {
    const rows = PLAYMAKING_DATA.filter(d => d.player === p).sort((a, b) => a.season.localeCompare(b.season));
    const line = d3.line().x(d => x(d.season)).y(d => y(d.prbh)).curve(d3.curveMonotoneX);
    svg.append("path").datum(rows).attr("fill", "none").attr("stroke", color(p))
      .attr("stroke-width", 2.5).attr("opacity", 0.7).attr("d", line);
    svg.selectAll(`.dot-${p}`).data(rows).enter().append("circle")
      .attr("cx", d => x(d.season)).attr("cy", d => y(d.prbh)).attr("r", 5)
      .attr("fill", color(p)).attr("stroke", "#FFFDF8").attr("stroke-width", 1.5);
    const last = rows[rows.length - 1];
    svg.append("text").attr("x", x(last.season) + 10).attr("y", y(last.prbh) + 4)
      .attr("font-family", "IBM Plex Sans").attr("font-size", 11).attr("fill", ink).text(p);
  });
}

function renderPace() {
  clear();
  caption.textContent = "Miles run per game — Maxey vs. league avg.  ·  bars: Maxey+Embiid on-court net rating";
  const x = d3.scaleBand().domain(PACE_DATA.map(d => d.season)).range([M.left, W - M.right]).padding(0.5);
  const y = d3.scaleLinear().domain([1.7, 2.6]).range([H - M.bottom - 140, M.top]);
  const yNet = d3.scaleLinear().domain([-8, 16]).range([H - M.bottom, H - M.bottom - 120]);

  svg.append("g").attr("transform", `translate(0,${H - M.bottom})`)
    .call(d3.axisBottom(x)).call(g => g.select(".domain").attr("stroke", "#D9D2C2"))
    .selectAll("text").attr("font-family", "IBM Plex Mono").attr("font-size", 11).attr("fill", inkSoft);

  // net rating bars (bottom strip)
  svg.append("g").attr("transform", `translate(${x(PACE_DATA[0].season)},0)`);
  svg.append("line").attr("x1", M.left).attr("x2", W - M.right).attr("y1", yNet(0)).attr("y2", yNet(0)).attr("stroke", "#D9D2C2");
  svg.selectAll(".netbar").data(MAXEY_EMBIID_NET_RATING).enter().append("rect")
    .attr("x", d => x(d.season) + x.bandwidth() / 2 - 18).attr("width", 36)
    .attr("y", yNet(0)).attr("height", 0)
    .attr("fill", d => d.netRating >= 0 ? "#7A8B5C" : risk)
    .transition().duration(600)
    .attr("y", d => Math.min(yNet(0), yNet(d.netRating)))
    .attr("height", d => Math.abs(yNet(d.netRating) - yNet(0)));
  svg.selectAll(".netlbl").data(MAXEY_EMBIID_NET_RATING).enter().append("text")
    .attr("x", d => x(d.season) + x.bandwidth() / 2).attr("y", d => yNet(d.netRating) + (d.netRating >= 0 ? -6 : 14))
    .attr("text-anchor", "middle").attr("font-family", "IBM Plex Mono").attr("font-size", 10).attr("fill", ink)
    .text(d => (d.netRating > 0 ? "+" : "") + d.netRating);
  svg.append("text").attr("x", M.left).attr("y", yNet(16) - 6).attr("font-family", "IBM Plex Sans")
    .attr("font-size", 10).attr("fill", inkSoft).text("Maxey+Embiid on-court net rating");

  // distance line (top strip)
  const lineMaxey = d3.line().x(d => x(d.season) + x.bandwidth() / 2).y(d => y(d.maxey)).curve(d3.curveMonotoneX);
  const lineLeague = d3.line().x(d => x(d.season) + x.bandwidth() / 2).y(d => y(d.leagueAvg)).curve(d3.curveMonotoneX);

  svg.append("path").datum(PACE_DATA).attr("fill", "none").attr("stroke", "#D9D2C2")
    .attr("stroke-width", 2).attr("stroke-dasharray", "4,3").attr("d", lineLeague);
  svg.append("path").datum(PACE_DATA).attr("fill", "none").attr("stroke", navy)
    .attr("stroke-width", 3).attr("d", lineMaxey);
  svg.selectAll(".dotm").data(PACE_DATA).enter().append("circle")
    .attr("cx", d => x(d.season) + x.bandwidth() / 2).attr("cy", d => y(d.maxey))
    .attr("r", 5).attr("fill", navy);

  svg.append("text").attr("x", M.left).attr("y", M.top).attr("font-family", "IBM Plex Sans")
    .attr("font-size", 10).attr("fill", navy).text("Maxey (miles/game)");
  svg.append("text").attr("x", M.left).attr("y", M.top + 14).attr("font-family", "IBM Plex Sans")
    .attr("font-size", 10).attr("fill", inkSoft).text("league avg. (miles/game)");
}

function renderDefense() {
  clear();
  caption.textContent = "Defended FG% vs. shooter's normal FG% (2025-26) — negative = suppresses efficiency";
  const y = d3.scaleBand().domain(DEFENSE_DATA.map(d => d.player)).range([M.top, H - M.bottom]).padding(0.35);
  const x = d3.scaleLinear().domain([-5, 2]).range([M.left, W - M.right]);

  svg.append("g").attr("transform", `translate(0,${H - M.bottom})`)
    .call(d3.axisBottom(x).ticks(7)).call(g => g.select(".domain").attr("stroke", "#D9D2C2"))
    .selectAll("text").attr("font-family", "IBM Plex Mono").attr("font-size", 10).attr("fill", inkSoft);
  svg.append("g").attr("transform", `translate(${x(0)},0)`)
    .call(g => g.append("line").attr("y1", M.top).attr("y2", H - M.bottom).attr("stroke", "#D9D2C2"));

  svg.selectAll("rect").data(DEFENSE_DATA).enter().append("rect")
    .attr("y", d => y(d.player)).attr("height", y.bandwidth())
    .attr("x", d => x(Math.min(0, d.pctPlusMinus))).attr("width", 0)
    .attr("fill", d => d.pctPlusMinus <= 0 ? navy : risk)
    .transition().duration(600).delay((d, i) => i * 80)
    .attr("width", d => Math.abs(x(d.pctPlusMinus) - x(0)));

  svg.selectAll(".lbl").data(DEFENSE_DATA).enter().append("text")
    .attr("x", M.left - 10).attr("y", d => y(d.player) + y.bandwidth() / 2 + 4)
    .attr("text-anchor", "end").attr("font-family", "IBM Plex Sans").attr("font-size", 12)
    .attr("fill", ink).text(d => d.player);
}

const CHART_RENDERERS = {
  spacing: renderSpacing,
  playmaking: renderPlaymaking,
  pace: renderPace,
  defense: renderDefense,
};

renderSpacing();
