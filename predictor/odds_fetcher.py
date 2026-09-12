"""Optional client for The Odds API (free tier: 500 credits/month).

Only used if ODDS_API_KEY is set in .env. Matches are linked to football-data.org
fixtures by normalized team name, which is imperfect -- mismatches are skipped
rather than guessed.
"""
import re
import requests

import config

_SUFFIXES = re.compile(
    r"\b(fc|cf|afc|sc|ac|cd|ud|rc|club|calcio|futbol|football|club de futbol)\b",
    re.IGNORECASE,
)


def _normalize(name):
    name = name.lower()
    name = _SUFFIXES.sub("", name)
    name = re.sub(r"[^a-z0-9]", "", name)
    return name


def is_configured():
    return bool(config.ODDS_API_KEY)


def get_odds_for_league(code):
    """Returns {(normalized_home, normalized_away): {home, draw, away}} decimal odds,
    averaged across whatever bookmakers the API returns."""
    sport_key = config.ODDS_API_SPORT_KEYS.get(code)
    if not sport_key or not config.ODDS_API_KEY:
        return {}

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": config.ODDS_API_KEY,
        "regions": "uk,eu",
        "markets": "h2h",
        "oddsFormat": "decimal",
    }
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        events = resp.json()
    except requests.RequestException:
        return {}

    result = {}
    for event in events:
        home = event.get("home_team", "")
        away = event.get("away_team", "")
        home_odds, draw_odds, away_odds = [], [], []
        for book in event.get("bookmakers", []):
            for market in book.get("markets", []):
                if market.get("key") != "h2h":
                    continue
                for outcome in market.get("outcomes", []):
                    if outcome["name"] == home:
                        home_odds.append(outcome["price"])
                    elif outcome["name"] == away:
                        away_odds.append(outcome["price"])
                    else:
                        draw_odds.append(outcome["price"])
        if home_odds and draw_odds and away_odds:
            key = (_normalize(home), _normalize(away))
            result[key] = {
                "home": sum(home_odds) / len(home_odds),
                "draw": sum(draw_odds) / len(draw_odds),
                "away": sum(away_odds) / len(away_odds),
            }
    return result


def match_odds(odds_by_key, home_team, away_team):
    key = (_normalize(home_team), _normalize(away_team))
    return odds_by_key.get(key)
