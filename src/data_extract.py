import json
import time
import requests
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Season configuration
SEASON = 2025
POSITIONS = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K"}  # D/ST has no player gamelog
MAX_WORKERS = 8  # concurrent gamelog requests

GAMELOG_FILE = Path("data") / f"player_gamelogs_{SEASON}.csv"
SUMMARY_FILE = Path("data") / f"player_summary_{SEASON}.csv"

# ESPN API configuration
HEADERS = {"User-Agent": "Mozilla/5.0"}
PLAYERS_URL = (
    f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}"
    f"/segments/0/leaguedefaults/3"
)
GAMELOG_URL = (
    "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{pid}/gamelog"
)
STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/football/nfl/standings"

# Gamelog columns that are game metadata rather than stats
META_COLS = [
    "player_id", "player", "position", "team", "season", "season_type", "week",
    "eventId", "date", "opponent", "atVs", "result", "score",
]


def get_players(season=SEASON):
    """Return every fantasy-relevant player (QB/RB/WR/TE/K) who recorded stats in the season,
    along with their actual fantasy points for each week."""
    filt = {"players": {"limit": 3000, "sortPercOwned": {"sortPriority": 1, "sortAsc": False}}}
    r = requests.get(
        PLAYERS_URL,
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


def get_gamelog(player_id, season=SEASON, retries=3):
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


def get_defense_ranks(season=SEASON):
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


def get_all_gamelogs(players, season=SEASON):
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


def main():
    players, weekly_points = get_players(SEASON)
    print(f"Found {len(players)} players with {SEASON} stats")

    gamelogs = get_all_gamelogs(players, SEASON)

    ranks = get_defense_ranks(SEASON)
    gamelogs["opp_def_rank"] = gamelogs["opponent"].map(ranks)
    gamelogs = gamelogs.merge(weekly_points, on=["player_id", "week"], how="left")

    summary = summarize_players(gamelogs)

    GAMELOG_FILE.parent.mkdir(exist_ok=True)
    gamelogs.to_csv(GAMELOG_FILE, index=False)
    summary.to_csv(SUMMARY_FILE, index=False)
    print(f"Saved {len(gamelogs)} games to {GAMELOG_FILE}")
    print(f"Saved {len(summary)} player summaries to {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
