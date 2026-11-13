## Extract weekly fantasy points + ESPN projections from espn API endpoints for one or more seasons,
## generates one csv per season: player_weeks_{SEASON}.csv in ./data
##
## usage in terminal:
##   python3 <directory/to/script/>Extract_fantasy_points.py                        -> seasons listed in SEASONS below
##   python3 <directory/to/script/>Extract_fantasy_points.py 2024 2026              -> specific seasons
##   python3 <directory/to/script/>Extract_fantasy_points.py --season 2025          -> one season (flag can repeat)
##   python3 <directory/to/script/>Extract_fantasy_points.py --start 2020 --end 2023 -> inclusive range of seasons
##   python3 <directory/to/script/>Extract_fantasy_points.py -h                     -> show help
## only need to run once per season which will store data in you local repo but it will not be pushed to online version for storage reasons
##
## Weeks kept per season: every week through the latest PLAYED week, plus the single next week
## (projection only, no actuals yet). A finished season keeps all 18 weeks.

import argparse
import json
import requests
import pandas as pd
from pathlib import Path

# Default seasons to extract when none are given on the command line
SEASONS = [2024, 2025, 2026]
WEEKS = range(1, 19)  # full regular season; later weeks are trimmed below if not yet reached
DATA_DIR = Path("data")

# ESPN's default-league endpoint (no league ID or login needed)
URL = (
    "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}"
    "/segments/0/leaguedefaults/3"
)
POSITIONS = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K"}

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


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Extract weekly ESPN fantasy points and projections into data/player_weeks_{SEASON}.csv."
    )
    parser.add_argument("seasons", nargs="*", type=int, metavar="SEASON",
                        help="season year(s) to extract, e.g. 2024 2025")
    parser.add_argument("-s", "--season", dest="extra_seasons", action="append", type=int, default=[],
                        metavar="SEASON", help="season to extract (can be repeated)")
    parser.add_argument("--start", type=int, help="first season of an inclusive range (requires --end)")
    parser.add_argument("--end", type=int, help="last season of an inclusive range (requires --start)")
    args = parser.parse_args(argv)

    if (args.start is None) != (args.end is None):
        parser.error("--start and --end must be used together")
    if args.start is not None and args.start > args.end:
        parser.error("--start must be less than or equal to --end")

    seasons = list(args.seasons) + args.extra_seasons
    if args.start is not None:
        seasons += range(args.start, args.end + 1)
    return sorted(set(seasons)) or SEASONS


def main(seasons):
    print(f"Extracting seasons: {', '.join(map(str, seasons))}")
    for season in seasons:
        run_season(season)


if __name__ == "__main__":
    main(parse_args())