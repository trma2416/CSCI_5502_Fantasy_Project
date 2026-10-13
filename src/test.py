## test pulling data 
from pathlib import Path
import nflreadpy as nfl
from nflreadpy.config import update_config

## take us to root of project
PROJ_ROOT=Path(__file__).resolve().parent.parent

## cache data so we dont have to redownload memeory upon each upload
update_config(cache_mode="filesystem", cache_dir = PROJ_ROOT / "cache")

#download play by play data

def load_pbp(year):
    pbp = nfl.load_pbp(year)

    df = pbp.to_pandas()
    return df

def load_weekly(year):
    weekly = nfl.load_player_stats(year)
    return weekly.to_pandas()

def load_sched(year):
    schedules = nfl.load_schedules(year)
    return schedules.to_pandas()


def load_players():
    players = nfl.load_players()
    return players.to_pandas()