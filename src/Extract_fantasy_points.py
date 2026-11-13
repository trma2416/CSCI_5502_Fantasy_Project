## Extract weekly fantasy points + ESPN projections from espn API endpoints for one or more seasons,
## generates one csv per season: player_weeks_{SEASON}.csv in ./data
##
## usage in terminal:
##   python3 <directory/to/script/>Extract_fantasy_points.py                  -> seasons listed in SEASONS below
##   python3 <directory/to/script/>Extract_fantasy_points.py 2024 2025 2026   -> seasons given on the command line
## only need to run once per season which will store data in you local repo but it will not be pushed to online version for storage reasons
##
## Weeks kept per season: every week through the latest PLAYED week, plus the single next week
## (projection only, no actuals yet). A finished season keeps all 18 weeks.

import json
import sys
import requests
import pandas as pd
from pathlib import Path

# Seasons to extract (override from the command line: python3 Extract_fantasy_points.py 2025 2026)
SEASONS = [2024, 2025, 2026]
WEEKS = range(1, 19)  # full regular season; later weeks are trimmed below if not yet reached
DATA_DIR = Path("data")

# ESPN's default-league endpoint (no league ID or login needed)
URL = (
    "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}"
    "/segments/0/leaguedefaults/3"
)
POSITIONS = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "D/ST"}

# Ask for up to 2000 players, most-rostered first
headers = {
    "X-Fantasy-Filter": json.dumps(
        {"players": {"limit": 2000, "sortPercOwned": {"sortPriority": 1, "sortAsc": False}}}
    )
}


def out_file(season):
    return DATA_DIR / f"player_weeks_{season}.csv"


def fetch_season(season):
    """Every player-week with an actual and/or projected score, for all weeks in WEEKS."""
    rows = []
    for week in WEEKS:
        resp = requests.get(
            URL.format(season=season),
            params={"view": "kona_player_info", "scoringPeriodId": week},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()

        for entry in resp.json().get("players", []):
            p = entry.get("player", {})
            pts = {}
            for s in p.get("stats", []):
                # statSourceId 0 = actual (1 = projection); statSplitTypeId 1 = single week
                if (
                    s.get("seasonId") == season
                    and s.get("scoringPeriodId") == week
                    and s.get("statSourceId") in (0, 1)
                    and s.get("statSplitTypeId") == 1
                ):
                    pts[s["statSourceId"]] = s.get("appliedTotal")
            if pts:
                rows.append({
                    "player_id": p.get("id"),
                    "player": p.get("fullName"),
                    "position": POSITIONS.get(p.get("defaultPositionId"), p.get("defaultPositionId")),
                    "pro_team_id": p.get("proTeamId"),
                    "week": week,
                    "fantasy_points": pts.get(0),
                    "projected_points": pts.get(1),
                })
    return pd.DataFrame(rows)


def trim_to_next_week(df):
    """Keep weeks through (latest played week + 1).

    A week counts as played when at least one player has a non-zero actual score; future weeks
    can come back with empty or all-zero actuals. A finished season keeps every week.
    """
    if df.empty:
        return df
    played = df.groupby("week")["fantasy_points"].apply(lambda s: s.fillna(0).ne(0).any())
    last_played = int(played[played].index.max()) if played.any() else 0
    return df[df["week"] <= min(last_played + 1, max(WEEKS))]


def run_season(season):
    print(f"\n=== Season {season} ===")
    df = trim_to_next_week(fetch_season(season))

    DATA_DIR.mkdir(exist_ok=True)
    df.to_csv(out_file(season), index=False)
    print(f"Saved {len(df)} player-weeks to {out_file(season)}")

    # sanity check: only the final week should show projections without actuals
    print(df.groupby("week").agg(
        rows=("player_id", "size"),
        with_actual=("fantasy_points", "count"),
        with_projection=("projected_points", "count"),
    ))


def main(seasons):
    for season in seasons:
        run_season(season)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or SEASONS)