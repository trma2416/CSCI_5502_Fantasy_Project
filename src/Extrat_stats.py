## Extract data from espn API endpoints for one or more seasons. For each season it generates
## player_gamelogs_{SEASON}.csv and player_summary_{SEASON}.csv in ./data
##
## usage in terminal:
##   python3 <directory/to/script/>Extrat_stats.py                  -> seasons listed in SEASONS below
##   python3 <directory/to/script/>Extrat_stats.py 2024 2025 2026   -> seasons given on the command line
## only need to run once per season which will store data in you local repo but it will not be pushed to online version for storage reasons
##
## Upcoming week: for a season that is still in progress, ONE extra unplayed week (the next one)
## is appended to the gamelogs so next-week features (opponent, home/away, weather) exist.
## Finished seasons get no upcoming rows. See ADD_UPCOMING_WEEK / UPCOMING_WEEK_OVERRIDE.

import json
import sys
import time
import requests
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Seasons to extract (override from the command line: python3 Extrat_stats.py 2025 2026)
SEASONS = [2024, 2025, 2026]

POSITIONS = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K"}  # D/ST has no player gamelog
MAX_WORKERS = 8  # concurrent gamelog requests
LAST_REG_SEASON_WEEK = 18
DATA_DIR = Path("data")

# --- upcoming-week settings -------------------------------------------------------------
# The next week is detected per season as (latest week with played games) + 1, so a finished
# season (latest week = 18) gets nothing. Only exactly one week is ever added.
ADD_UPCOMING_WEEK = True
# Per-season override for mid-week runs while that week's games are still being played,
# e.g. {2026: 10}. Only the latest played week or the one after it is accepted; anything
# else raises, so a stale value can't add rows to the wrong week or the wrong season.
UPCOMING_WEEK_OVERRIDE = {}

# ESPN API configuration
HEADERS = {"User-Agent": "Mozilla/5.0"}
PLAYERS_URL = (
    "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}"
    "/segments/0/leaguedefaults/3"
)
GAMELOG_URL = (
    "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{pid}/gamelog"
)
STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/football/nfl/standings"
SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

# Gamelog columns that are game metadata rather than stats
META_COLS = [
    "player_id", "player", "position", "team", "season", "season_type", "week",
    "eventId", "date", "opponent", "atVs", "result", "score",
]


def gamelog_file(season):
    return DATA_DIR / f"player_gamelogs_{season}.csv"


def summary_file(season):
    return DATA_DIR / f"player_summary_{season}.csv"


def get_players(season):
    """Return every fantasy-relevant player (QB/RB/WR/TE/K) who recorded stats in the season,
    along with their actual fantasy points for each week."""
    filt = {"players": {"limit": 3000, "sortPercOwned": {"sortPriority": 1, "sortAsc": False}}}
    r = requests.get(
        PLAYERS_URL.format(season=season),
        params={"view": "kona_player_info"},
        headers={**HEADERS, "X-Fantasy-Filter": json.dumps(filt)},
        timeout=60,
    )
    r.raise_for_status()

    players, weekly_points = [], []
    for entry in r.json().get("players", []):
        p = entry.get("player", {})
        pos = POSITIONS.get(p.get("defaultPositionId"))
        if pos is None:
            continue
        played = False
        for s in p.get("stats", []):
            # statSourceId 0 = actual; statSplitTypeId 1 = single week
            if s.get("seasonId") != season or s.get("statSourceId") != 0:
                continue
            played = True
            if s.get("statSplitTypeId") == 1:
                weekly_points.append({
                    "player_id": p["id"],
                    "week": s.get("scoringPeriodId"),
                    "fantasy_points": s.get("appliedTotal"),
                })
        if played:
            players.append({"player_id": p["id"], "player": p.get("fullName"), "position": pos})

    return pd.DataFrame(players), pd.DataFrame(weekly_points)


def get_gamelog(player_id, season, retries=3):
    """Fetch one season of game logs (regular season + postseason) as a DataFrame."""
    for attempt in range(retries):
        r = requests.get(
            GAMELOG_URL.format(pid=player_id),
            headers=HEADERS,
            params={"season": season},
            timeout=30,
        )
        # ESPN sometimes answers 202 with an empty body when hit too fast
        if r.status_code == 200 and r.content:
            break
        time.sleep(2 ** attempt)
    else:
        return pd.DataFrame()
    data = r.json()

    names = data.get("names", [])        # unique stat keys (labels repeat YDS/AVG/TD/LNG)
    events_info = data.get("events", {})  # game details keyed by eventId
    rows = []

    for st in data.get("seasonTypes", []):
        for cat in st.get("categories", []):
            for ev in cat.get("events", []):
                info = events_info.get(ev["eventId"], {})
                row = dict(zip(names, ev["stats"]))
                row["player_id"] = player_id
                row["team"] = info.get("team", {}).get("abbreviation")
                row["season"] = season
                row["season_type"] = st.get("displayName")
                row["week"] = info.get("week")
                row["eventId"] = ev["eventId"]
                row["date"] = info.get("gameDate")
                row["opponent"] = info.get("opponent", {}).get("abbreviation")
                row["atVs"] = info.get("atVs")
                row["result"] = info.get("gameResult")
                row["score"] = info.get("score")
                rows.append(row)

    return pd.DataFrame(rows)


def get_defense_ranks(season):
    """Rank teams by points allowed for a season (1 = fewest allowed)."""
    r = requests.get(STANDINGS_URL, headers=HEADERS, params={"season": season})
    r.raise_for_status()
    pa = {}
    for conf in r.json()["children"]:
        for e in conf["standings"]["entries"]:
            for s in e["stats"]:
                if s.get("name") == "pointsAgainst":
                    pa[e["team"]["abbreviation"]] = s.get("value")
    return pd.Series(pa).rank(method="min").astype(int)


def get_upcoming_games(week, season):
    """One row per team for every game scheduled in `week` (home and away views).

    Uses ESPN's scoreboard. `dates=<season>` is required: without it the `week` parameter
    silently returns the previous season's schedule.
    """
    r = requests.get(
        SCOREBOARD_URL,
        headers=HEADERS,
        params={"dates": season, "seasontype": 2, "week": week, "limit": 1000},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()

    # guard against ESPN answering with a different season/week than we asked for
    got_year = (data.get("season") or {}).get("year")
    got_week = (data.get("week") or {}).get("number")
    if (got_year is not None and got_year != season) or (got_week is not None and got_week != week):
        print(f"WARNING: scoreboard returned season={got_year} week={got_week}, "
              f"expected season={season} week={week}; skipping upcoming rows")
        return pd.DataFrame()

    rows = []
    for ev in data.get("events", []):
        comps = ev.get("competitions", [{}])[0].get("competitors", [])
        sides = {c["homeAway"]: c["team"]["abbreviation"] for c in comps}
        if "home" not in sides or "away" not in sides:
            continue
        # atVs uses the same "vs" (home) / "@" (away) values as the gamelog endpoint
        for side, other, at_vs in (("home", "away", "vs"), ("away", "home", "@")):
            rows.append({
                "team": sides[side],
                "opponent": sides[other],
                "atVs": at_vs,
                "eventId": ev["id"],
                "date": ev.get("date"),
                "week": week,
            })
    return pd.DataFrame(rows)


def pick_upcoming_week(gamelogs, season):
    """The single week to add as unplayed rows for this season, or None for no rows."""
    last_played = int(gamelogs["week"].max())

    if season in UPCOMING_WEEK_OVERRIDE:
        week = UPCOMING_WEEK_OVERRIDE[season]
        if week not in (last_played, last_played + 1):
            raise ValueError(
                f"UPCOMING_WEEK_OVERRIDE[{season}]={week} but the latest played week is "
                f"{last_played}; only {last_played} or {last_played + 1} is allowed. "
                f"Remove the override for finished seasons."
            )
        return week

    week = last_played + 1
    return week if week <= LAST_REG_SEASON_WEEK else None  # finished season -> None


def build_upcoming_rows(gamelogs, week, season):
    """Unplayed rows (player x upcoming game) in the same schema as the gamelogs.

    Stat columns are left empty (they get filled with NaN on concat). Each player is
    attached to the team of their most recent game. Teams on a bye get no row, and a player
    who already has a played row for `week` never gets a second one.
    """
    games = get_upcoming_games(week, season)
    if games.empty:
        return pd.DataFrame()

    roster = (
        gamelogs.sort_values("date")
        .groupby("player_id")
        .tail(1)[["player_id", "player", "position", "team"]]
    )
    upcoming = roster.merge(games, on="team", how="inner")

    # never duplicate a (player, week) that was actually played
    played = gamelogs.dropna(subset=["week"])
    played_keys = set(zip(played["player_id"], played["week"].astype(int)))
    already = [(pid, wk) in played_keys for pid, wk in zip(upcoming["player_id"], upcoming["week"])]
    upcoming = upcoming[[not a for a in already]]

    upcoming = upcoming.assign(season=season, season_type="Regular Season")

    byes = sorted(set(roster["team"]) - set(games["team"]))
    print(f"Upcoming week {week}: {len(upcoming)} player rows across "
          f"{upcoming['team'].nunique()} teams (bye: {byes})")
    return upcoming


def get_all_gamelogs(players, season):
    """Fetch regular-season gamelogs for every player and stack them into one DataFrame."""
    with ThreadPoolExecutor(MAX_WORKERS) as ex:
        frames = list(ex.map(lambda pid: get_gamelog(pid, season), players["player_id"]))

    df = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    df = df[df["season_type"].str.contains("Regular", na=False)]
    df = df.drop_duplicates(["player_id", "eventId"])
    df = df.merge(players, on="player_id", how="left")

    # Kicking stats come as "made-attempts" (e.g. "1-2"); split them into two columns
    paired = [c for c in df.columns if c not in META_COLS and "-" in c]
    splits = []
    for col in paired:
        split = df[col].str.split("-", expand=True).reindex(columns=[0, 1])
        split.columns = col.split("-")
        splits.append(split)
    df = pd.concat([df.drop(columns=paired)] + splits, axis=1)

    stat_cols = [c for c in df.columns if c not in META_COLS]
    stats = df[stat_cols].apply(pd.to_numeric, errors="coerce")  # "-" -> NaN
    return pd.concat([df[META_COLS], stats], axis=1)


def summarize_players(gamelogs):
    """One row per player: games played, season totals, per-game averages and fantasy points."""
    stat_cols = [c for c in gamelogs.columns if c not in META_COLS + ["opp_def_rank"]]
    long_cols = [c for c in stat_cols if c.startswith("long")]
    rate_cols = [
        c for c in stat_cols
        if any(k in c for k in ("Pct", "Per", "per", "Rating", "QBR", "Average", "avg", "fantasy_points"))
    ]
    count_cols = [c for c in stat_cols if c not in long_cols + rate_cols]

    g = gamelogs.groupby(["player_id", "player", "position"])
    summary = g.agg(
        team=("team", "last"),
        games=("eventId", "nunique"),
        avg_opp_def_rank=("opp_def_rank", "mean"),
    )
    totals = g[count_cols].sum(min_count=1).add_prefix("total_")
    per_game = g[count_cols].mean().add_prefix("avg_")
    rates = g[rate_cols].mean().add_prefix("avg_")
    longs = g[long_cols].max()

    fantasy = g["fantasy_points"].sum(min_count=1).rename("total_fantasy_points")

    summary = pd.concat([summary, totals, per_game, rates, longs, fantasy], axis=1)
    summary = summary.dropna(axis=1, how="all").reset_index()
    return summary.sort_values("total_fantasy_points", ascending=False, ignore_index=True)


def run_season(season):
    print(f"\n=== Season {season} ===")
    players, weekly_points = get_players(season)
    print(f"Found {len(players)} players with {season} stats")

    gamelogs = get_all_gamelogs(players, season)

    ranks = get_defense_ranks(season)
    gamelogs["opp_def_rank"] = gamelogs["opponent"].map(ranks)
    gamelogs = gamelogs.merge(weekly_points, on=["player_id", "week"], how="left")

    # summarize BEFORE adding upcoming rows so unplayed games don't count toward games/averages
    summary = summarize_players(gamelogs)
    n_played = len(gamelogs)

    # add the next week's unplayed rows (opponent, home/away, eventId, date; stats stay NaN)
    if ADD_UPCOMING_WEEK:
        upcoming_week = pick_upcoming_week(gamelogs, season)
        if upcoming_week is None:
            print(f"Season {season} is complete (latest played week "
                  f"{int(gamelogs['week'].max())}); no upcoming rows")
        else:
            upcoming = build_upcoming_rows(gamelogs, upcoming_week, season)
            if not upcoming.empty:
                upcoming["opp_def_rank"] = upcoming["opponent"].map(ranks)
                gamelogs = pd.concat([gamelogs, upcoming], ignore_index=True)

    DATA_DIR.mkdir(exist_ok=True)
    gamelogs.to_csv(gamelog_file(season), index=False)
    summary.to_csv(summary_file(season), index=False)
    print(f"Saved {n_played} played games + {len(gamelogs) - n_played} upcoming rows "
          f"to {gamelog_file(season)}")
    print(f"Saved {len(summary)} player summaries to {summary_file(season)}")


def main(seasons):
    for season in seasons:
        run_season(season)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or SEASONS)