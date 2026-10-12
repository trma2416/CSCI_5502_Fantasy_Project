## test pulling data 
from pathlib import Path
import nflreadpy as nfl
from nflreadpy.config import update_config

## take us to root of project
PROJ_ROOT=Path(__file__).resolve.parent.parent

## cache data so we dont have to redownload memeory upon each upload
update_config(cache_mode="filesystem", cache_dir = PROJ_ROOT / "cache")

#download play by play data

def load_data(year):
    pbp = nfl.load_pbp(2025)

    ## weekly player stats
    weekly = nfl.load_player_stats(2025)

    schedules = nfl.load_schedules(2025)

    players = nfl.load_players()

    df = pbp.to_pandas()
    return df