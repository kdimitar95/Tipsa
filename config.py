"""Central configuration, loaded from .env (see .env.example)."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "").strip()
ODDS_API_KEY = os.getenv("ODDS_API_KEY", "").strip()

LEAGUES = [c.strip().upper() for c in os.getenv("LEAGUES", "PL,PD,BL1,SA,FL1,CL").split(",") if c.strip()]

DAYS_AHEAD = int(os.getenv("DAYS_AHEAD", "7"))

DB_PATH = BASE_DIR / "data" / "predictor.db"
DATA_JSON_PATH = BASE_DIR / "docs" / "data.json"

FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"

# Maps football-data.org competition codes to The Odds API sport keys,
# used only if ODDS_API_KEY is set.
ODDS_API_SPORT_KEYS = {
    "PL": "soccer_epl",
    "PD": "soccer_spain_la_liga",
    "BL1": "soccer_germany_bundesliga",
    "SA": "soccer_italy_serie_a",
    "FL1": "soccer_france_ligue_one",
    "CL": "soccer_uefa_champs_league",
    "DED": "soccer_netherlands_eredivisie",
    "PPL": "soccer_portugal_primeira_liga",
    "ELC": "soccer_efl_champ",
}

# Readable names, used as a fallback if the API's own name is missing.
LEAGUE_NAMES = {
    "PL": "Premier League",
    "PD": "La Liga",
    "BL1": "Bundesliga",
    "SA": "Serie A",
    "FL1": "Ligue 1",
    "CL": "Champions League",
    "DED": "Eredivisie",
    "PPL": "Primeira Liga",
    "ELC": "Championship",
    "BSA": "Brasileirao",
    "WC": "World Cup",
    "EC": "European Championship",
}
