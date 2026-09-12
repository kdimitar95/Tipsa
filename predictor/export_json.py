"""Turns the SQLite predictions/matches tables into a single JSON snapshot
that the static frontend (docs/) can fetch with no server involved."""
import datetime as dt
import json

import config
from predictor import database


def _row_to_fixture(row):
    return {
        "match_id": row["match_id"],
        "competition_code": row["competition_code"],
        "competition_name": config.LEAGUE_NAMES.get(row["competition_code"], row["competition_code"]),
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "utc_date": row["utc_date"],
        "home_win_prob": row["home_win_prob"],
        "draw_prob": row["draw_prob"],
        "away_win_prob": row["away_win_prob"],
        "expected_home_goals": row["expected_home_goals"],
        "expected_away_goals": row["expected_away_goals"],
        "best_scoreline": row["best_scoreline"],
        "over_2_5_prob": row["over_2_5_prob"],
        "btts_prob": row["btts_prob"],
        "home_odds": row["home_odds"],
        "draw_odds": row["draw_odds"],
        "away_odds": row["away_odds"],
        "value_side": row["value_side"],
        "value_edge": row["value_edge"],
    }


def _row_to_history(row):
    if row["home_goals"] is None or row["away_goals"] is None:
        return None
    probs = {"home": row["home_win_prob"], "draw": row["draw_prob"], "away": row["away_win_prob"]}
    predicted = max(probs, key=probs.get)
    if row["home_goals"] > row["away_goals"]:
        actual = "home"
    elif row["home_goals"] < row["away_goals"]:
        actual = "away"
    else:
        actual = "draw"
    fixture = _row_to_fixture(row)
    fixture.update(
        actual_home_goals=row["home_goals"],
        actual_away_goals=row["away_goals"],
        predicted_outcome=predicted,
        actual_outcome=actual,
        hit=predicted == actual,
    )
    return fixture


def _row_to_match(row):
    return {
        "id": row["id"],
        "competition_code": row["competition_code"],
        "utc_date": row["utc_date"],
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "home_goals": row["home_goals"],
        "away_goals": row["away_goals"],
    }


def build_snapshot():
    with database.get_conn() as conn:
        upcoming = [_row_to_fixture(r) for r in database.get_upcoming_predictions(conn)]
        history_rows = [_row_to_history(r) for r in database.get_settled_predictions(conn)]
        history = [r for r in history_rows if r is not None]
        last_update = database.get_last_update(conn)

        recent_matches = []
        for code in config.LEAGUES:
            recent_matches.extend(
                _row_to_match(r) for r in database.get_finished_matches(conn, code, limit=60)
            )

    hits = sum(1 for h in history if h["hit"])
    accuracy = round(100 * hits / len(history)) if history else None

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "last_update": dict(last_update) if last_update else None,
        "leagues": {code: config.LEAGUE_NAMES.get(code, code) for code in config.LEAGUES},
        "upcoming": upcoming,
        "history": history,
        "recent_matches": recent_matches,
        "accuracy": accuracy,
    }


def write_snapshot():
    snapshot = build_snapshot()
    config.DATA_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(config.DATA_JSON_PATH, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)
    return snapshot
