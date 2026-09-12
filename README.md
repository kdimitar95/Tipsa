# Fixture Room — phone edition

The same idea as before — football fixtures, a Poisson prediction model,
optional value-bet flags against the odds, a track record page — but
restructured so nothing needs to run on a computer you own:

- **A free GitHub Actions job** fetches the data and rebuilds predictions
  once a day. It's a real Python process on GitHub's servers, so it isn't
  subject to the CORS restrictions a phone browser would hit calling
  football-data.org directly.
- **A free GitHub Pages site** serves a small static app (no backend) that
  reads the results. You open it in Safari and add it to your home screen
  like a normal app icon.
- Nothing to keep running, nothing that sleeps or expires, no credit card.

**Trade-off to know about:** this setup has to happen once, and it's
genuinely easier with a few minutes of computer access (even a borrowed
one) than doing it entirely on a phone keyboard. Everything *after* that
one-time setup — using the app, and it updating itself daily — needs
nothing but your phone. Two ways to do the one-time part are below; pick
whichever you have access to.

## One-time setup

### 1. Create a GitHub account and a new repository

Free, no card needed, at https://github.com/join if you don't have one.
Then create a new repository (the **+** in the top right → *New
repository*). **It needs to be public** — GitHub Pages on a free account
only serves public repos. That's fine: your API keys never go in the code
(see step 3), so nothing sensitive is exposed — only fixtures/predictions
data, which isn't sensitive.

### 2. Get the project files into that repository

**Easiest, if you can get a few minutes on any computer** (yours,
work, a library, a friend's — you won't need it again after this):
```bash
cd fixture-room-cloud
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPO.git
git push -u origin main
```

**Entirely from your phone**, if that's not an option: unzip the project
in the Files app, then on github.com (in Safari) use **Add file → Upload
files** on your new repo and drag the whole unzipped folder in. Folder
uploads usually preserve subfolders, but dot-prefixed folders (like
`.github`) sometimes get skipped by upload tools — if the workflow doesn't
show up under `.github/workflows/` afterwards, add it by hand: **Add file
→ Create new file**, type the full path
`.github/workflows/daily-update.yml` as the filename (GitHub creates the
folders for you), and paste in that file's contents.

### 3. Add your API keys as repository secrets

**Required** — free key from https://www.football-data.org/client/register
(instant, no card). **Optional** — free key from https://the-odds-api.com
(500 credits/month) if you want value-bet flags.

In your repo: **Settings → Secrets and variables → Actions → New
repository secret**. Add:
- `FOOTBALL_DATA_API_KEY`
- `ODDS_API_KEY` (optional — leave the app without it and everything else still works)

These are encrypted and never appear in the code, the site, or the
committed data.

### 4. Let the workflow push its own updates

**Settings → Actions → General → Workflow permissions** → select **Read
and write permissions** → Save. (Without this, the daily job can fetch
data but can't commit the results back.)

### 5. Turn on GitHub Pages

**Settings → Pages** → under *Build and deployment*, set **Source** to
*Deploy from a branch*, branch **main**, folder **/docs** → **Save**.
GitHub gives you a URL like `https://your-username.github.io/your-repo/`
— that's your app.

### 6. Run it once by hand

**Actions tab → Daily update → Run workflow.** This does the first fetch
so there's something to look at (otherwise you're waiting for the next
6 AM UTC scheduled run). Takes a minute or two.

### 7. Install it on your iPhone

Open your Pages URL from step 5 in Safari → **Share → Add to Home
Screen**. It now behaves like an app: its own icon, opens full-screen,
no address bar.

## Using it day to day

Nothing to do. The workflow runs on its own every day at 06:00 UTC (edit
the `cron:` line in `.github/workflows/daily-update.yml` to change the
time — it's always in UTC) and commits fresh predictions; the app on your
phone just displays whatever the last run produced. Pull down/reopen the
app to see the latest.

To change which leagues are tracked, edit `LEAGUES` in `config.py` in the
repo (GitHub's web editor works fine for this — click the file, pencil
icon, edit, commit).

## How the model works, and its limits

Same model as the original build: each team gets a home/away attack and
defence rating relative to the league average, combined into expected
goals for a specific fixture, then treated as independent Poisson draws
to get a full probability distribution (win/draw/win, scoreline,
over/under, BTTS). It's a solid statistical baseline — it does **not**
know about injuries, suspensions, or team news, and "value bet" flags
just mean the model's number is higher than the market's, which is a
discrepancy worth a second look, not a tip. Treat it as one input, and
only ever stake what you can afford to lose.

## Project structure

```
daily_update.py            Entry point the GitHub Action runs
config.py                  Reads LEAGUES / API keys (keys come from
                            environment variables — GitHub Actions secrets
                            in production; a local .env if you ever test
                            by hand)
predictor/
  data_fetcher.py            football-data.org client
  odds_fetcher.py             The Odds API client (optional)
  model.py                   Poisson prediction engine
  database.py                 SQLite storage (committed to the repo —
                              git is the persistence layer between runs)
  export_json.py              Turns the database into docs/data.json
.github/workflows/
  daily-update.yml            The scheduled job
docs/                       Served by GitHub Pages — the whole frontend
  index.html, team.html, history.html, style.css, app.js
  manifest.json, sw.js        Home-screen install + offline app shell
  data.json                   Overwritten by the daily workflow
data/predictor.db            Created and updated by the workflow
```

## Troubleshooting

- **"No data yet" never goes away** — check the Actions tab for a failed
  run (red X). The most common cause is a missing/incorrect
  `FOOTBALL_DATA_API_KEY` secret.
- **Workflow runs but nothing changes** — check *Settings → Actions →
  General → Workflow permissions* is set to read-and-write (step 4).
- **Pages URL 404s** — double-check the Pages source folder is `/docs`,
  and give it a minute or two after saving; first deploys aren't instant.
- **Want it to update more than once a day** — edit the `cron:` schedule
  in `.github/workflows/daily-update.yml`. Free Actions minutes (2,000/mo)
  comfortably cover several runs a day for a job this small.
