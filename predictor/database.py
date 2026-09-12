"""SQLite storage for matches, team stats, and predictions."""
import sqlite3
from contextlib import contextmanager

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY,              -- football-data.org match id
    competition_code TEXT NOT NULL,
    season INTEGER,
    matchday INTEGER,
    utc_date TEXT,
    status TEXT,
    home_team TEXT,
    away_team TEXT,
    home_goals INTEGER,
    away_goals INTEGER
);

CREATE TABLE IF NOT EXISTS predictions (
    match_id INTEGER PRIMARY KEY,
    generated_at TEXT,
    competition_code TEXT,
    home_team TEXT,
    away_team TEXT,
    utc_date TEXT,
    home_win_prob REAL,
    draw_prob REAL,
    away_win_prob REAL,
    expected_home_goals REAL,
    expected_away_goals REAL,
    best_scoreline TEXT,
    over_2_5_prob REAL,
    btts_prob REAL,
    home_odds REAL,
    draw_odds REAL,
    away_odds REAL,
    value_side TEXT,
    value_edge REAL,
    FOREIGN KEY (match_id) REFERENCES matches (id)
);

CREATE TABLE IF NOT EXISTS update_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ran_at TEXT,
    leagues TEXT,
    matches_fetched INTEGER,
    predictions_made INTEGER,
    notes TEXT
);
"""


def init_db():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_match(conn, m):
    conn.execute(
        """
        INSERT INTO matches (id, competition_code, season, matchday, utc_date, status,
                              home_team, away_team, home_goals, away_goals)
        VALUES (:id, :competition_code, :season, :matchday, :utc_date, :status,
                :home_team, :away_team, :home_goals, :away_goals)
        ON CONFLICT(id) DO UPDATE SET
            status=excluded.status,
            home_goals=excluded.home_goals,
            away_goals=excluded.away_goals,
            utc_date=excluded.utc_date,
            matchday=excluded.matchday
        """,
        m,
    )


def upsert_prediction(conn, p):
    conn.execute(
        """
        INSERT INTO predictions (match_id, generated_at, competition_code, home_team, away_team,
                                  utc_date, home_win_prob, draw_prob, away_win_prob,
                                  expected_home_goals, expected_away_goals, best_scoreline,
                                  over_2_5_prob, btts_prob, home_odds, draw_odds, away_odds,
                                  value_side, value_edge)
        VALUES (:match_id, :generated_at, :competition_code, :home_team, :away_team,
                :utc_date, :home_win_prob, :draw_prob, :away_win_prob,
                :expected_home_goals, :expected_away_goals, :best_scoreline,
                :over_2_5_prob, :btts_prob, :home_odds, :draw_odds, :away_odds,
                :value_side, :value_edge)
        ON CONFLICT(match_id) DO UPDATE SET
            generated_at=excluded.generated_at,
            home_win_prob=excluded.home_win_prob,
            draw_prob=excluded.draw_prob,
            away_win_prob=excluded.away_win_prob,
            expected_home_goals=excluded.expected_home_goals,
            expected_away_goals=excluded.expected_away_goals,
            best_scoreline=excluded.best_scoreline,
            over_2_5_prob=excluded.over_2_5_prob,
            btts_prob=excluded.btts_prob,
            home_odds=excluded.home_odds,
            draw_odds=excluded.draw_odds,
            away_odds=excluded.away_odds,
            value_side=excluded.value_side,
            value_edge=excluded.value_edge
        """,
        p,
    )


def log_update(conn, leagues, matches_fetched, predictions_made, notes=""):
    conn.execute(
        "INSERT INTO update_log (ran_at, leagues, matches_fetched, predictions_made, notes) "
        "VALUES (datetime('now'), ?, ?, ?, ?)",
        (",".join(leagues), matches_fetched, predictions_made, notes),
    )


def get_upcoming_predictions(conn, competition_code=None):
    q = "SELECT * FROM predictions WHERE utc_date >= datetime('now', '-2 hours')"
    args = []
    if competition_code:
        q += " AND competition_code = ?"
        args.append(competition_code)
    q += " ORDER BY utc_date ASC"
    return conn.execute(q, args).fetchall()


def get_finished_matches(conn, competition_code, season=None, limit=380):
    q = "SELECT * FROM matches WHERE competition_code = ? AND status = 'FINISHED'"
    args = [competition_code]
    if season:
        q += " AND season = ?"
        args.append(season)
    q += " ORDER BY utc_date DESC LIMIT ?"
    args.append(limit)
    return conn.execute(q, args).fetchall()


def get_settled_predictions(conn, limit=200):
    """Predictions whose matches have since finished, for accuracy tracking."""
    return conn.execute(
        """
        SELECT p.*, m.home_goals, m.away_goals, m.status
        FROM predictions p
        JOIN matches m ON m.id = p.match_id
        WHERE m.status = 'FINISHED'
        ORDER BY p.utc_date DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def get_last_update(conn):
    return conn.execute("SELECT * FROM update_log ORDER BY id DESC LIMIT 1").fetchone()
