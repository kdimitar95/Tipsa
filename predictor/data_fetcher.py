"""Thin client for football-data.org (free tier: 10 requests/minute, 12 competitions)."""
import time
import datetime as dt

import requests

import config

_last_call = 0.0
_MIN_INTERVAL = 6.5  # seconds between calls -> ~9/min, safely under the free 10/min cap


def _get(path, params=None):
    global _last_call
    if not config.FOOTBALL_DATA_API_KEY:
        raise RuntimeError(
            "FOOTBALL_DATA_API_KEY is not set. Get a free key at "
            "https://www.football-data.org/client/register and put it in your .env file."
        )

    wait = _MIN_INTERVAL - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)

    url = f"{config.FOOTBALL_DATA_BASE_URL}{path}"
    headers = {"X-Auth-Token": config.FOOTBALL_DATA_API_KEY}

    resp = requests.get(url, headers=headers, params=params, timeout=20)
    _last_call = time.time()

    if resp.status_code == 429:
        # Rate limited despite our pacing -- back off hard and retry once.
        time.sleep(30)
        resp = requests.get(url, headers=headers, params=params, timeout=20)
        _last_call = time.time()

    resp.raise_for_status()
    return resp.json()


def get_competition_name(code):
    try:
        data = _get(f"/competitions/{code}")
        return data.get("name", config.LEAGUE_NAMES.get(code, code))
    except requests.HTTPError:
        return config.LEAGUE_NAMES.get(code, code)


def get_finished_matches(code, season=None):
    """Recent finished matches for a competition, used to estimate team strength."""
    params = {"status": "FINISHED"}
    if season:
        params["season"] = season
    data = _get(f"/competitions/{code}/matches", params=params)
    return [_normalize_match(m, code) for m in data.get("matches", [])]


def get_upcoming_matches(code, days_ahead=7):
    today = dt.date.today()
    params = {
        "status": "SCHEDULED",
        "dateFrom": today.isoformat(),
        "dateTo": (today + dt.timedelta(days=days_ahead)).isoformat(),
    }
    data = _get(f"/competitions/{code}/matches", params=params)
    return [_normalize_match(m, code) for m in data.get("matches", [])]


def _normalize_match(m, code):
    score = m.get("score", {}).get("fullTime", {}) or {}
    season_start = (m.get("season") or {}).get("startDate") or ""
    season_year = int(season_start[:4]) if season_start[:4].isdigit() else None
    return {
        "id": m["id"],
        "competition_code": code,
        "season": season_year,
        "matchday": m.get("matchday"),
        "utc_date": m.get("utcDate"),
        "status": m.get("status"),
        "home_team": (m.get("homeTeam") or {}).get("name", "Unknown"),
        "away_team": (m.get("awayTeam") or {}).get("name", "Unknown"),
        "home_goals": score.get("home"),
        "away_goals": score.get("away"),
    }
