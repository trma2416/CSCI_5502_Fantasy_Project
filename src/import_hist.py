## Extract historical fantasy data from espn API endpoints, generates csv file, player_weeks_{SEASON}.csv
## usage in terminal use: python3 <directory/to/script/>import_hist.py
## only need to run once which will store data in you local repo but it will not be pushed to online version for storage reasons

import json
import requests
import pandas as pd
from pathlib import Path

SEASON = 2025
WEEKS = range(1, 19)  # 2025 regular season

OUT_FILE = Path("data") / f"player_weeks_{SEASON}.csv"

# ESPN's default-league endpoint (no league ID or login needed)
URL = (
    f"https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}"
    f"/segments/0/leaguedefaults/3"
)
POSITIONS = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "D/ST"}

# Ask for up to 2000 players, most-rostered first
headers = {
    "X-Fantasy-Filter": json.dumps(
        {"players": {"limit": 2000, "sortPercOwned": {"sortPriority": 1, "sortAsc": False}}}
    )
}

rows = []
for week in WEEKS:
    resp = requests.get(
        URL,
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
                s.get("seasonId") == SEASON
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

df = pd.DataFrame(rows)
df.to_csv(OUT_FILE, index=False)