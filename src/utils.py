import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def write_to_dict(df, name, data_path):
    '''Update dictionary csv files '''
    columns = df.columns.to_numpy()
    dict_ = pd.DataFrame(columns)
    try:
        dict_.to_csv(data_path/f"dicts/{name}_dictionary.csv")
    except Exception as e:
        print(f"failed to write dictionary with exception {e}")

def update_data(df, name, data_path):
    try:
        df.to_csv(data_path/f"{name}_final.csv")
    except Exception as e:
        print(f"failed to updata data: {e}")

def clean(X, y):
    m = y.notna() & np.isfinite(y)
    return X[m], y[m]


def get_data(x, irrelevant, target):
    x_train = x.loc[:, ~x.columns.isin(irrelevant)]
    y_train = x[target]

    x_train , y_train = clean(x_train, y_train)

    return x_train, y_train

# check results
def get_results(df, x_test, y_test, model) -> pd.DataFrame:
    test_results = df.loc[x_test.index].copy()
    test_results["model_prediction"] = model.predict(x_test)
    test_results["fantasy_points"] = y_test
    test_results["espn_projected"] = df["next_week_projected"]

    ## compute error statistics
    test_results["model_error"] = test_results["fantasy_points"] - test_results["model_prediction"]
    test_results["model_error_abs"] = test_results["model_error"].abs()
    test_results["espn_error"] = test_results["fantasy_points"] - test_results["espn_projected"]
    test_results["espn_error_abs"] = test_results["espn_error"].abs()

    cmp = test_results.dropna(subset=['espn_projected']).copy()

    cmp["winner"] = np.select([cmp["model_error_abs"] < cmp["espn_error_abs"],
                                cmp["model_error_abs"] > cmp["espn_error_abs"]],
                                ["Model", "espn"],
                                default="Tie"
    )
    for name, pred in [('Model', cmp['model_prediction']), ('ESPN', cmp['espn_projected'])]:
        print(f"{name}: MAE={mean_absolute_error(cmp['fantasy_points'], pred):.3f}  "
            f"RMSE={np.sqrt(mean_squared_error(cmp['fantasy_points'], pred)):.3f}  "
            f"R2={r2_score(cmp['fantasy_points'], pred):.3f}")
    return cmp


def model_input_features(df):
    df = df.drop(columns=["Unnamed: 0","pro_team_id", "season_type"], errors="ignore")
    #Sort chronologically by player (required before the expanding/rolling features below)
    df = df.sort_values(['player_id', 'season', 'week']).reset_index(drop=True)

    #Create target (Next week's fantasy score) and next week's context via shift(-1)
    #group by player AND season so a season's last game doesn't take next season's week 1 as its target
    g = df.groupby(['player_id', 'season'])
    df['target_next_week_fantasy'] = g['fantasy_points'].shift(-1)
    df['next_week_opponent'] = g['opponent'].shift(-1)
    df['next_week_atVs'] = g['atVs'].shift(-1)
    df['next_week_projected'] = g['projected_points'].shift(-1)   # ESPN's projection for the game being predicted (baseline only)
    for col in ['roof', 'surface', 'temp', 'wind', 'location']:
        df[f'next_week_{col}'] = g[col].shift(-1)
    #Compute cumulative career and season-to-date stats up to current row (Week N)
    stats_to_accumulate = [
        'fantasy_points', 'receptions', 'receivingTargets', 'receivingYards', 
        'receivingTouchdowns', 'rushingAttempts', 'rushingYards', 'rushingTouchdowns',
        'completions', 'passingAttempts', 'passingYards', 'passingTouchdowns', 
        'interceptions', 'fumblesLost'
    ]

    for col in stats_to_accumulate:
        # 1. Career cumulative mean (df is sorted by player_id, so .values lines up with the rows)
        df[f'{col}_cum_career_avg'] = (
            df.groupby('player_id')[col]
            .expanding()
            .mean()
            .values
        )
        
        # 2. Season-to-date cumulative mean
        df[f'{col}_season_avg'] = (
            df.groupby(['player_id', 'season'])[col]
            .expanding()
            .mean()
            .values
        )

    for col in ['fantasy_points', 'receivingTargets', 'rushingAttempts', 'passingAttempts']:
        df[f'{col}_last3'] = (
            df.groupby(['player_id', 'season'])[col]
            .transform(lambda s: s.rolling(3, min_periods=1).mean()))

    ## encode categorical columns (same as the global model; cast on the full frame so every group shares one vocabulary)
    categorical_cols = ['player','position', 'next_week_opponent', 'next_week_atVs', 'next_week_surface',
                        'next_week_roof', 'next_week_location']
    for col in categorical_cols:
        df[col] = df[col].astype('category')

    target = 'target_next_week_fantasy'

    ## same excluded columns as the global model
    irrelevant_columns = [
        'Unnamed: 0', 'player_id', 'team', 'opponent', 'date',
        'eventId', 'game_id', 'gameday', 'gametime', 'stadium', 'result',
        'score', 'fantasy_points', 'target_next_week_fantasy', 'espn',
        '_set', 'season',
        'med_proj_pts',
        'projected_points',
        'atVs', 'roof', 'surface', 'temp', 'wind', 'location',
        'opp_def_rank', 'team_pass_rank', 'team_rush_rank', 'next_week_projected' 
    ]
    relevant_columns = [col for col in df.columns if col not in irrelevant_columns]
    irrelevant = [col for col in df.columns if col not in relevant_columns]

    #remove invalid players that model does not see
    valid_players = df[df["season"] != 2026]["player"].unique().tolist()
    
    df = df.loc[df["player"].isin(valid_players)]

    return df

def split(d):
    train = d[(d['season'] == 2024) | ((d['season'] == 2025) & (d['week'] < 10))]
    val = d[(d['season'] == 2025) & (d['week'].between(10, 18))]
    test = d[(d['season'] == 2026) & (d['week'] < 11)]
    return train, val, test