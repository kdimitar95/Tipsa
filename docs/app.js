// Fixture Room — static frontend. Fetches data.json (written daily by the
// GitHub Actions workflow) and renders it. No server, no API calls from
// the browser at all.

const fmtPct = (x) => (x == null ? "—" : `${Math.round(x * 100)}%`);

function parseUtc(s) {
  if (!s) return null;
  const d = new Date(s);
  return isNaN(d) ? null : d;
}

function teamLink(name) {
  return `team.html?team=${encodeURIComponent(name)}`;
}

function fixtureCardHtml(m) {
  const kickoff = parseUtc(m.utc_date);
  const kickoffLabel = kickoff
    ? kickoff.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) + " UTC"
    : "TBC";
  const compName = m.competition_name || m.competition_code;
  const valueClass = m.value_side ? "has-value" : "";
  const valueOdds =
    m.value_side === "home" ? m.home_odds : m.value_side === "draw" ? m.draw_odds : m.away_odds;

  return `
    <article class="fixture-card ${valueClass}">
      <div class="fixture-top">
        <span class="competition-badge">${compName}</span>
        <span class="kickoff">${kickoffLabel}</span>
      </div>
      <div class="teams-row">
        <a class="team-name" href="${teamLink(m.home_team)}">${m.home_team}</a>
        <span class="vs">vs</span>
        <a class="team-name" href="${teamLink(m.away_team)}">${m.away_team}</a>
      </div>
      <div class="prob-bar" title="Home ${fmtPct(m.home_win_prob)} / Draw ${fmtPct(m.draw_prob)} / Away ${fmtPct(m.away_win_prob)}">
        <span class="prob-home" style="width:${(m.home_win_prob * 100).toFixed(1)}%"></span>
        <span class="prob-draw" style="width:${(m.draw_prob * 100).toFixed(1)}%"></span>
        <span class="prob-away" style="width:${(m.away_win_prob * 100).toFixed(1)}%"></span>
      </div>
      <div class="prob-labels">
        <span>${fmtPct(m.home_win_prob)} home</span>
        <span>${fmtPct(m.draw_prob)} draw</span>
        <span>${fmtPct(m.away_win_prob)} away</span>
      </div>
      <div class="fixture-meta">
        <span class="meta-item">Likeliest score <strong>${m.best_scoreline}</strong></span>
        <span class="meta-item">xG ${m.expected_home_goals}&ndash;${m.expected_away_goals}</span>
        <span class="meta-item">O2.5 ${fmtPct(m.over_2_5_prob)}</span>
        <span class="meta-item">BTTS ${fmtPct(m.btts_prob)}</span>
      </div>
      ${m.value_side ? `<div class="value-flag">Value on ${m.value_side} &middot; odds ${valueOdds}</div>` : ""}
    </article>`;
}

function groupByDate(fixtures) {
  const groups = new Map();
  for (const m of fixtures) {
    const d = parseUtc(m.utc_date);
    const key = d ? d.toISOString().slice(0, 10) : "tbc";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(m);
  }
  const today = new Date().toISOString().slice(0, 10);
  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);

  return [...groups.entries()]
    .sort(([a], [b]) => (a === "tbc" ? 1 : b === "tbc" ? -1 : a.localeCompare(b)))
    .map(([key, matches]) => {
      let label;
      if (key === "tbc") label = "Date to be confirmed";
      else if (key === today) label = "Today";
      else if (key === tomorrow) label = "Tomorrow";
      else
        label = new Date(key + "T00:00:00Z").toLocaleDateString([], {
          weekday: "long",
          day: "numeric",
          month: "short",
          timeZone: "UTC",
        });
      return { label, matches };
    });
}

function renderDashboard(snapshot) {
  const params = new URLSearchParams(location.search);
  const activeLeague = params.get("league");

  const statusEl = document.getElementById("status-line");
  if (snapshot.last_update) {
    statusEl.textContent = `Last updated ${snapshot.last_update.ran_at} UTC · ${snapshot.last_update.predictions_made} predictions from ${snapshot.last_update.matches_fetched} matches`;
  } else {
    statusEl.textContent = "No data yet — the first scheduled update hasn't run.";
  }

  const tabsEl = document.getElementById("league-tabs");
  const allTab = `<a href="index.html" class="${!activeLeague ? "active" : ""}">All leagues</a>`;
  const leagueTabs = Object.entries(snapshot.leagues)
    .map(
      ([code, name]) =>
        `<a href="index.html?league=${code}" class="${activeLeague === code ? "active" : ""}">${name}</a>`
    )
    .join("");
  tabsEl.innerHTML = allTab + leagueTabs;

  let fixtures = snapshot.upcoming;
  if (activeLeague) fixtures = fixtures.filter((m) => m.competition_code === activeLeague);

  const valueBets = fixtures.filter((m) => m.value_side);
  const valuePanel = document.getElementById("value-panel");
  if (valueBets.length) {
    valuePanel.innerHTML = `
      <section class="value-panel">
        <h2>Where the model and the market disagree</h2>
        <p class="value-note">The model sees more chance of this outcome than the odds imply. Not a tip &mdash; a discrepancy worth a second look.</p>
        <div class="value-grid">
          ${valueBets
            .map(
              (v) => `
            <div class="value-chip">
              <span class="value-fixture"><a href="${teamLink(v.home_team)}">${v.home_team}</a> vs <a href="${teamLink(v.away_team)}">${v.away_team}</a></span>
              <span class="value-side">${v.value_side} &middot; +${fmtPct(v.value_edge)} edge</span>
            </div>`
            )
            .join("")}
        </div>
      </section>`;
  } else {
    valuePanel.innerHTML = "";
  }

  const contentEl = document.getElementById("content");
  if (!fixtures.length) {
    contentEl.innerHTML = `<div class="empty-state"><p>Nothing on the board yet for this view.</p></div>`;
    return;
  }

  const groups = groupByDate(fixtures);
  contentEl.innerHTML = groups
    .map(
      (g) => `
      <section class="date-group">
        <h2 class="date-heading">${g.label}</h2>
        <div class="fixture-list">${g.matches.map(fixtureCardHtml).join("")}</div>
      </section>`
    )
    .join("");
}

function renderTeam(snapshot) {
  const params = new URLSearchParams(location.search);
  const team = params.get("team");
  const contentEl = document.getElementById("content");

  if (!team) {
    contentEl.innerHTML = `<p class="empty-note">No team specified.</p>`;
    return;
  }

  document.title = `${team} — Fixture Room`;

  const upcoming = snapshot.upcoming.filter((m) => m.home_team === team || m.away_team === team);
  const recent = snapshot.recent_matches
    .filter((m) => m.home_team === team || m.away_team === team)
    .sort((a, b) => (b.utc_date || "").localeCompare(a.utc_date || ""))
    .slice(0, 10);

  const upcomingHtml = upcoming.length
    ? `<div class="fixture-list">${upcoming.map(fixtureCardHtml).join("")}</div>`
    : `<p class="empty-note">No upcoming fixtures in the tracked window.</p>`;

  const recentHtml = recent.length
    ? `<table class="results-table"><thead><tr><th>Date</th><th>Fixture</th><th>Score</th></tr></thead><tbody>
        ${recent
          .map(
            (r) => `
          <tr>
            <td>${(r.utc_date || "").slice(0, 10)}</td>
            <td>${r.home_team} &ndash; ${r.away_team}</td>
            <td class="score-cell">${r.home_goals}&ndash;${r.away_goals}</td>
          </tr>`
          )
          .join("")}
      </tbody></table>`
    : `<p class="empty-note">No finished matches stored yet for this team.</p>`;

  contentEl.innerHTML = `
    <h1 class="team-heading">${team}</h1>
    <section class="team-section"><h2>Upcoming</h2>${upcomingHtml}</section>
    <section class="team-section"><h2>Recent results</h2>${recentHtml}</section>`;
}

function renderHistory(snapshot) {
  const contentEl = document.getElementById("content");
  const results = [...snapshot.history].sort((a, b) =>
    (b.utc_date || "").localeCompare(a.utc_date || "")
  );

  const accuracyHtml =
    snapshot.accuracy != null
      ? `<div class="accuracy-panel">
           <div class="accuracy-number">${snapshot.accuracy}%</div>
           <div class="accuracy-label">of ${results.length} settled fixtures, the model's most likely outcome (home / draw / away) matched what happened.</div>
         </div>
         <p class="value-note">This is result accuracy, not stake accuracy &mdash; it says nothing about whether following the odds would have been profitable.</p>`
      : `<p class="empty-note">No settled fixtures yet. Once predicted matches are played and the next daily update runs, results will appear here.</p>`;

  const tableHtml = results.length
    ? `<table class="results-table history-table"><thead>
        <tr><th>Date</th><th>Fixture</th><th>Predicted</th><th>Actual</th><th>Score (pred / actual)</th><th></th></tr>
        </thead><tbody>
        ${results
          .map(
            (r) => `
          <tr class="${r.hit ? "hit-row" : "miss-row"}">
            <td>${(r.utc_date || "").slice(0, 10)}</td>
            <td>${r.home_team} &ndash; ${r.away_team}</td>
            <td>${r.predicted_outcome} (${fmtPct(r.home_win_prob)}/${fmtPct(r.draw_prob)}/${fmtPct(r.away_win_prob)})</td>
            <td>${r.actual_outcome}</td>
            <td>${r.best_scoreline} / ${r.actual_home_goals}-${r.actual_away_goals}</td>
            <td class="hit-mark">${r.hit ? "&check;" : "&times;"}</td>
          </tr>`
          )
          .join("")}
        </tbody></table>`
    : "";

  contentEl.innerHTML = accuracyHtml + tableHtml;
}

async function init() {
  const page = document.body.dataset.page;
  let snapshot;
  try {
    const res = await fetch("data.json", { cache: "no-store" });
    if (!res.ok) throw new Error(res.status);
    snapshot = await res.json();
  } catch (e) {
    document.getElementById("content").innerHTML =
      `<div class="empty-state"><p>Couldn't load data.json yet. If this is a brand-new setup, trigger the "Daily update" workflow once from the Actions tab on GitHub.</p></div>`;
    const statusEl = document.getElementById("status-line");
    if (statusEl) statusEl.textContent = "";
    return;
  }

  if (page === "dashboard") renderDashboard(snapshot);
  else if (page === "team") renderTeam(snapshot);
  else if (page === "history") renderHistory(snapshot);
}

document.addEventListener("DOMContentLoaded", init);

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  });
}
