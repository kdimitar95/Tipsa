"""
Statistical prediction model.

Approach: a standard independent-Poisson goals model (the same family used by
most public football analytics write-ups). For each team we derive a home
attack/defence strength and an away attack/defence strength relative to the
league average, then combine two teams' strengths into expected goals for a
specific fixture. Goal counts are then treated as independent Poisson draws,
which gives a full probability distribution over scorelines -- not just a
single predicted result.

This is a solid baseline, not a guarantee: it doesn't yet account for
injuries/suspensions, tactical news, or the slight real-world correlation
between low scorelines (the "Dixon-Coles adjustment"). See the README for
notes on extending it.
"""
from collections import defaultdict

from scipy.stats import poisson

MAX_GOALS = 8          # scoreline grid computed as 0..MAX_GOALS for each side
SHRINKAGE = 4           # pseudo-matches of league-average strength blended in
MIN_MATCHES_FOR_STRENGTH = 4


class LeagueModel:
    """Holds team strengths for one competition, built from finished matches."""

    def __init__(self, finished_matches):
        self.home_goals_for = defaultdict(int)
        self.home_goals_against = defaultdict(int)
        self.home_played = defaultdict(int)
        self.away_goals_for = defaultdict(int)
        self.away_goals_against = defaultdict(int)
        self.away_played = defaultdict(int)

        total_home_goals = total_away_goals = total_matches = 0

        for m in finished_matches:
            if m["home_goals"] is None or m["away_goals"] is None:
                continue
            h, a = m["home_team"], m["away_team"]
            hg, ag = m["home_goals"], m["away_goals"]

            self.home_goals_for[h] += hg
            self.home_goals_against[h] += ag
            self.home_played[h] += 1

            self.away_goals_for[a] += ag
            self.away_goals_against[a] += hg
            self.away_played[a] += 1

            total_home_goals += hg
            total_away_goals += ag
            total_matches += 1

        self.league_avg_home_goals = total_home_goals / total_matches if total_matches else 1.35
        self.league_avg_away_goals = total_away_goals / total_matches if total_matches else 1.15
        self.sample_size = total_matches

    def _rate(self, goals, played, league_avg):
        """Shrinks small samples toward the league average so a team with only
        a couple of games played doesn't produce an extreme, noisy estimate."""
        return (goals + SHRINKAGE * league_avg) / (played + SHRINKAGE)

    def team_strengths(self, team):
        hp = self.home_played.get(team, 0)
        ap = self.away_played.get(team, 0)

        attack_home = self._rate(self.home_goals_for.get(team, 0), hp, self.league_avg_home_goals) / self.league_avg_home_goals
        defence_home = self._rate(self.home_goals_against.get(team, 0), hp, self.league_avg_away_goals) / self.league_avg_away_goals
        attack_away = self._rate(self.away_goals_for.get(team, 0), ap, self.league_avg_away_goals) / self.league_avg_away_goals
        defence_away = self._rate(self.away_goals_against.get(team, 0), ap, self.league_avg_home_goals) / self.league_avg_home_goals

        low_data = (hp + ap) < MIN_MATCHES_FOR_STRENGTH
        return {
            "attack_home": attack_home,
            "defence_home": defence_home,
            "attack_away": attack_away,
            "defence_away": defence_away,
            "low_data": low_data,
        }

    def expected_goals(self, home_team, away_team):
        home = self.team_strengths(home_team)
        away = self.team_strengths(away_team)

        exp_home = home["attack_home"] * away["defence_away"] * self.league_avg_home_goals
        exp_away = away["attack_away"] * home["defence_home"] * self.league_avg_away_goals

        # Keep expected goals in a sane range even for wildly mismatched/noisy inputs.
        exp_home = max(0.15, min(exp_home, 6.0))
        exp_away = max(0.15, min(exp_away, 6.0))

        low_data = home["low_data"] or away["low_data"]
        return exp_home, exp_away, low_data


def score_matrix(exp_home, exp_away, max_goals=MAX_GOALS):
    home_probs = [poisson.pmf(i, exp_home) for i in range(max_goals + 1)]
    away_probs = [poisson.pmf(i, exp_away) for i in range(max_goals + 1)]
    return [[hp * ap for ap in away_probs] for hp in home_probs]


def summarize(matrix):
    home_win = draw = away_win = over_2_5 = btts = 0.0
    best_p, best_score = -1, (0, 0)

    for hg, row in enumerate(matrix):
        for ag, p in enumerate(row):
            if hg > ag:
                home_win += p
            elif hg == ag:
                draw += p
            else:
                away_win += p
            if hg + ag > 2:
                over_2_5 += p
            if hg >= 1 and ag >= 1:
                btts += p
            if p > best_p:
                best_p, best_score = p, (hg, ag)

    # Normalize in case the truncated grid doesn't sum to exactly 1.0
    total = home_win + draw + away_win
    if total > 0:
        home_win, draw, away_win = home_win / total, draw / total, away_win / total

    return {
        "home_win_prob": round(home_win, 4),
        "draw_prob": round(draw, 4),
        "away_win_prob": round(away_win, 4),
        "over_2_5_prob": round(min(over_2_5, 1.0), 4),
        "btts_prob": round(min(btts, 1.0), 4),
        "best_scoreline": f"{best_score[0]}-{best_score[1]}",
    }


def predict_fixture(league_model, home_team, away_team):
    exp_home, exp_away, low_data = league_model.expected_goals(home_team, away_team)
    matrix = score_matrix(exp_home, exp_away)
    result = summarize(matrix)
    result["expected_home_goals"] = round(exp_home, 2)
    result["expected_away_goals"] = round(exp_away, 2)
    result["low_data"] = low_data
    return result


def value_bet(prediction, odds):
    """Compares model probabilities to bookmaker-implied probabilities.
    odds: {"home": x, "draw": y, "away": z} decimal odds.
    Flags the side with the largest positive edge, if any, above a threshold."""
    if not odds:
        return None, None

    sides = {
        "home": (prediction["home_win_prob"], odds.get("home")),
        "draw": (prediction["draw_prob"], odds.get("draw")),
        "away": (prediction["away_win_prob"], odds.get("away")),
    }

    best_side, best_edge = None, 0.0
    for side, (model_p, price) in sides.items():
        if not price or price <= 1.0:
            continue
        implied_p = 1.0 / price
        edge = model_p - implied_p
        if edge > best_edge:
            best_side, best_edge = side, edge

    EDGE_THRESHOLD = 0.05  # require model to see >5pp more chance than the market implies
    if best_side and best_edge > EDGE_THRESHOLD:
        return best_side, round(best_edge, 4)
    return None, None
