"""
Run once a day by the GitHub Actions workflow (.github/workflows/daily-update.yml):
  1. pull recent finished results + upcoming fixtures for each configured league
  2. rebuild each league's team-strength model from finished matches
  3. generate predictions for upcoming fixtures
  4. (optional) pull odds and flag value bets, if ODDS_API_KEY is set
  5. export everything to docs/data.json for the static frontend

Can also be run by hand: python daily_update.py
"""
import datetime as dt
import sys

import config
from predictor import database, data_fetcher, model, odds_fetcher, export_json


def run():
    database.init_db()
    total_matches_seen = 0
    total_predictions = 0

    with database.get_conn() as conn:
        for code in config.LEAGUES:
            print(f"[{code}] fetching finished matches...")
            try:
                finished = data_fetcher.get_finished_matches(code)
            except Exception as e:
                print(f"[{code}] skipped (finished matches fetch failed: {e})", file=sys.stderr)
                continue

            for m in finished:
                database.upsert_match(conn, m)
            total_matches_seen += len(finished)
            print(f"[{code}] {len(finished)} finished matches stored")

            print(f"[{code}] fetching upcoming fixtures ({config.DAYS_AHEAD} days ahead)...")
            try:
                upcoming = data_fetcher.get_upcoming_matches(code, config.DAYS_AHEAD)
            except Exception as e:
                print(f"[{code}] skipped upcoming fixtures ({e})", file=sys.stderr)
                continue

            for m in upcoming:
                database.upsert_match(conn, m)

            if not upcoming:
                print(f"[{code}] no upcoming fixtures in range")
                continue

            league_model = model.LeagueModel(finished)
            print(
                f"[{code}] league averages: {league_model.league_avg_home_goals:.2f} home / "
                f"{league_model.league_avg_away_goals:.2f} away goals per game "
                f"(from {league_model.sample_size} matches)"
            )

            odds_by_key = {}
            if odds_fetcher.is_configured():
                odds_by_key = odds_fetcher.get_odds_for_league(code)
                print(f"[{code}] fetched odds for {len(odds_by_key)} fixtures")

            for m in upcoming:
                pred = model.predict_fixture(league_model, m["home_team"], m["away_team"])

                odds = odds_fetcher.match_odds(odds_by_key, m["home_team"], m["away_team"])
                value_side, value_edge = model.value_bet(pred, odds) if odds else (None, None)

                database.upsert_prediction(
                    conn,
                    {
                        "match_id": m["id"],
                        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                        "competition_code": code,
                        "home_team": m["home_team"],
                        "away_team": m["away_team"],
                        "utc_date": m["utc_date"],
                        "home_win_prob": pred["home_win_prob"],
                        "draw_prob": pred["draw_prob"],
                        "away_win_prob": pred["away_win_prob"],
                        "expected_home_goals": pred["expected_home_goals"],
                        "expected_away_goals": pred["expected_away_goals"],
                        "best_scoreline": pred["best_scoreline"],
                        "over_2_5_prob": pred["over_2_5_prob"],
                        "btts_prob": pred["btts_prob"],
                        "home_odds": odds.get("home") if odds else None,
                        "draw_odds": odds.get("draw") if odds else None,
                        "away_odds": odds.get("away") if odds else None,
                        "value_side": value_side,
                        "value_edge": value_edge,
                    },
                )
                total_predictions += 1

            print(f"[{code}] {len(upcoming)} predictions generated")

        database.log_update(conn, config.LEAGUES, total_matches_seen, total_predictions)

    snapshot = export_json.write_snapshot()
    print(f"\nExported {len(snapshot['upcoming'])} upcoming and {len(snapshot['history'])} settled fixtures to {config.DATA_JSON_PATH}")
    print(f"Done. {total_matches_seen} matches processed, {total_predictions} predictions generated.")


if __name__ == "__main__":
    run()
