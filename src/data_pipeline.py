import numpy as np
import pandas as pd
from pathlib import Path
import nflreadpy as nfl

def clean_data(seasons, data_dir=None, write=True):
    """Clean and feature-build one or more seasons. Returns {season: final DataFrame}.

    seasons : int or list of ints, e.g. [2024, 2025, 2026]
    data_dir: folder holding the extract files (default: ../data relative to the notebook)
    write   : True -> also writes data/df_{season}_final.csv and the column dictionaries

    Per season it reads  player_weeks_{season}.csv, player_summary_{season}.csv,
    player_gamelogs_{season}.csv  from the data folder.
    """

    data_path = Path(data_dir) if data_dir else Path.cwd().parent / "data"

    # ESPN gives "@" (away) / "vs" (home)
    home_away = {"@": "away", "vs": "home"}

    # stadium name (as used by nflreadpy) -> city, used for the location feature
    stadium_locations = {
        'Soldier Field': 'Chicago,IL',
        'U.S. Bank Stadium': 'Minneapolis,MN',
        'Ford Field': 'Detroit,MI',
        'SoFi Stadium': 'Inglewood,CA',
        'Lincoln Financial Field': 'Philadelphia,PA',
        'FedExField': 'Landover,MD',
        'GEHA Field at Arrowhead Stadium': 'Kansas City,MO',
        'Paycor Stadium': 'Cincinnati,OH',
        'M&T Bank Stadium': 'Baltimore,MD',
        'Lambeau Field': 'Green Bay,WI',
        "Levi's Stadium": 'Santa Clara,CA',
        'Lucas Oil Stadium': 'Indianapolis,IN',
        'FirstEnergy Stadium': 'Cleveland,OH',
        'State Farm Stadium': 'Glendale,AZ',
        'MetLife Stadium': 'East Rutherford,NJ',
        'NRG Stadium': 'Houston,TX',
        'Raymond James Stadium': 'Tampa,FL',
        'Mercedes-Benz Superdome': 'New Orleans,LA',
        'Lumen Field': 'Seattle,WA',
        'Hard Rock Stadium': 'Miami Gardens,FL',
        'New Era Field': 'Orchard Park,NY',
        'Acrisure Stadium': 'Pittsburgh,PA',
        'Empower Field at Mile High': 'Denver,CO',
        'Mercedes-Benz Stadium': 'Atlanta,GA',
        'Bank of America Stadium': 'Charlotte,NC',
        'Nissan Stadium': 'Nashville,TN',
        'Gillette Stadium': 'Foxborough,MA',
        'AT&T Stadium': 'Arlington,TX',
        'Allegiant Stadium': 'Paradise,NV',
        'TIAA Bank Stadium': 'Jacksonville,FL',
        # newer names for the same venues (these used to give NaN locations)
        'Highmark Stadium': 'Orchard Park,NY',
        'Reliant Stadium': 'Houston,TX',
        'Caesars Superdome': 'New Orleans,LA',
        'EverBank Stadium': 'Jacksonville,FL',
        'Northwest Stadium': 'Landover,MD',
        'Huntington Bank Field': 'Cleveland,OH',
    }

    if isinstance(seasons, int):
        seasons = [seasons]
    if write:
        (data_path / "dicts").mkdir(parents=True, exist_ok=True)

    cleaned = {}
    for season in seasons:
        print(f"--- cleaning {season} ---")

        # ---------------- load ----------------
        weekly_df = pd.read_csv(data_path / f"player_weeks_{season}.csv")
        player_sum = pd.read_csv(data_path / f"player_summary_{season}.csv")
        player_logs = pd.read_csv(data_path / f"player_gamelogs_{season}.csv")
        if write:
            pd.DataFrame(player_sum.columns.to_numpy()).to_csv(
                data_path / f"dicts/player_sum_{season}_dictionary.csv")
            pd.DataFrame(player_logs.columns.to_numpy()).to_csv(
                data_path / f"dicts/player_logs_{season}_dictionary.csv")

        # ---------------- keep only players present in the summary / logs ----------------
        players_set = set(player_sum["player_id"].unique())
        assert players_set == set(player_logs["player_id"].unique()), "not same players"
        weekly_df = weekly_df[weekly_df["player_id"].isin(players_set)].copy()

        # ---------------- impute missing projected points with the player's median ----------------
        weekly_df["med_proj_pts"] = weekly_df.groupby("player_id")["projected_points"].transform("median")
        weekly_df["projected_points"] = np.where(
            weekly_df["projected_points"].isna(),
            weekly_df["med_proj_pts"],
            weekly_df["projected_points"],
        )

        # ---------------- merge logs with weekly projections ----------------
        key_cols = {"player_id", "week"}
        overlapping_cols = (set(player_logs.columns) & set(weekly_df.columns)) - key_cols
        merged_df = pd.merge(
            player_logs,
            weekly_df.drop(columns=list(overlapping_cols)),
            on=list(key_cols),
            how="left",
        )
        # season_type is constant when only the regular season is kept; we also have team name
        if merged_df["season_type"].nunique() == 1:
            merged_df = merged_df.drop(columns=["pro_team_id", "season_type"])

        # ---------------- weather (nflreadpy schedule, joined on ESPN event id) ----------------
        sched = nfl.load_schedules(seasons=season)
        weather = sched.select([
            "espn", "game_id", "gameday", "gametime",
            "stadium", "roof", "surface", "temp", "wind",
        ]).to_pandas()
        merged_df["eventId"] = merged_df["eventId"].astype(str)
        df = merged_df.merge(weather, left_on="eventId", right_on="espn", how="left")

        # Define known dome/indoor stadiums (including international series venues)
        dome_stadiums = {
            'AT&T Stadium', 'Mercedes-Benz Stadium', 'Lucas Oil Stadium', 
            'State Farm Stadium', 'Ford Field', 'U.S. Bank Stadium', 
            'SoFi Stadium', 'Allegiant Stadium', 'NRG Stadium', 
            'Caesars Superdome', 'Mercedes-Benz Superdome', 'Reliant Stadium',
            'FC Bayern Munich Stadium', 'Tottenham Hotspur Stadium', 'Wembley Stadium'
        }

        # Force roof to 'dome' if stadium is in our dome list
        df.loc[df["stadium"].isin(dome_stadiums), "roof"] = "dome"

        # closed roofs count as domes
        df["roof"] = np.where(df["roof"] == "closed", "dome", df["roof"])

        # domes: average indoor temperature (~70F) and no wind
        df["temp"] = np.where(df["roof"] == "dome", 70, df["temp"])
        df["wind"] = np.where((df["wind"].isna()) & (df["roof"] == "dome"), 0.0, df["wind"])

        # outdoor stadiums: impute missing wind with the mean outdoor wind
        mean_wind = df[df["roof"] == "outdoors"]["wind"].mean()
        df["wind"] = np.where((df["wind"].isna()) & (df["roof"] == "outdoors"), mean_wind, df["wind"])

        # fix missing surface
        df.loc[df["stadium"] == "SoFi Stadium", "surface"] = "matrixturf"

        # ---------------- home/away + stadium location ----------------
        df["atVs"] = df["atVs"].map(home_away)
        df["location"] = df["stadium"].map(stadium_locations)

        # game date as a timestamp
        df["date"] = pd.to_datetime(df["date"], format="ISO8601", utc=True)

        # ---------------- team pass/rush rank (uses PRIOR games only, no leakage) ----------------
        # 1. team totals per week (summed over that team's players)
        team_week = (
            df.groupby(["season", "team", "week"], as_index=False)
              .agg(pass_yds=("passingYards", "sum"), rush_yds=("rushingYards", "sum"))
        )
        team_week["played"] = 1

        # 2. full season x team x week grid, so bye weeks show up as 0 yards / 0 games
        keys = ["season", "team"]
        grid_idx = pd.MultiIndex.from_product(
            [team_week["season"].unique(), team_week["team"].unique(), range(1, int(df["week"].max()) + 1)],
            names=["season", "team", "week"],
        )
        grid = team_week.set_index(["season", "team", "week"]).reindex(grid_idx).fillna(0)

        # 3. cumulative totals, shifted one week so each row only sees PRIOR games
        cum = grid.groupby(level=keys).cumsum()
        prior = cum.groupby(level=keys).shift(1)

        # 4. yards per game played (fair across bye weeks), then rank all teams within each week
        games = prior["played"].where(prior["played"] > 0)
        prior["pass_ypg"] = prior["pass_yds"] / games
        prior["rush_ypg"] = prior["rush_yds"] / games

        by_week = prior.groupby(level=["season", "week"])
        prior["team_pass_rank"] = by_week["pass_ypg"].rank(ascending=False, method="min")
        prior["team_rush_rank"] = by_week["rush_ypg"].rank(ascending=False, method="min")

        # 5. attach to the player rows
        ranks = prior[["team_pass_rank", "team_rush_rank"]]
        row_keys = pd.MultiIndex.from_frame(df[["season", "team", "week"]])
        df["team_pass_rank"] = ranks["team_pass_rank"].reindex(row_keys).to_numpy()
        df["team_rush_rank"] = ranks["team_rush_rank"].reindex(row_keys).to_numpy()

        # ---------------- save ----------------
        if write:
            pd.DataFrame(df.columns.to_numpy()).to_csv(
                data_path / f"dicts/df_{season}_dictionary.csv")
            df.to_csv(data_path / f"df_{season}_final.csv")

        last_wk = int(df["week"].max())
        print(f"{season}: {len(df)} rows, weeks {int(df['week'].min())}-{last_wk}, "
              f"{(df['week'] == last_wk).sum()} rows in week {last_wk}")
        cleaned[season] = df

    return cleaned