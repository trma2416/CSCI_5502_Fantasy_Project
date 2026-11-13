# CSCI 5502 Fantasy Football Prediction

This README covers how to set up the project and build the cleaned datasets: raw extraction from ESPN, then cleaning and feature building, ending at `data/df_{SEASON}_final.csv`.

> **A note on commands:** The examples below use `python3`, which works on macOS and Linux. **On Windows, use `python` or `py`.** Where other parts of a command differ by operating system, each version is shown separately. Forward slashes in paths (for example `src/Extrat_stats.py`) work in Windows PowerShell and Command Prompt too.

## 1. Environment setup

The project was developed with Python 3.14. From the repository root, create and activate a virtual environment.

**macOS / Linux (bash, zsh)**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> If PowerShell blocks the activation script, first run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

**Windows (Command Prompt)**

```bat
py -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
```

After the environment is activated, `python` points to the venv's interpreter on every OS.

Packages the data steps rely on: `requests`, `pandas`, `numpy`, and `nflreadpy` (weather and stadium data).

## 2. Extract raw data from ESPN

Two scripts in `src/` pull data from ESPN's public API endpoints. No login or league ID is needed. **Run both from the repository root**, because they write to `./data` relative to the current directory.

### 2a. Weekly fantasy points and ESPN projections

**macOS / Linux**

```bash
python3 src/Extract_fantasy_points.py
```

**Windows (PowerShell or Command Prompt)**

```powershell
python src/Extract_fantasy_points.py
```

Output: `data/player_weeks_{SEASON}.csv`

### 2b. Player game logs, season summaries, and opponent defense rank

**macOS / Linux**

```bash
python3 src/Extrat_stats.py
```

**Windows (PowerShell or Command Prompt)**

```powershell
python src/Extrat_stats.py
```

Output: `data/player_gamelogs_{SEASON}.csv` and `data/player_summary_{SEASON}.csv`

### Choosing seasons

With no arguments, both scripts extract the seasons in their `SEASONS` list (`2024, 2025, 2026`). Both accept the same options; the arguments are identical on every OS, only `python3` vs `python` changes:

| Command (macOS / Linux) | Command (Windows) | Seasons extracted |
|---|---|---|
| `python3 src/<script>.py` | `python src/<script>.py` | Default `SEASONS` list |
| `python3 src/<script>.py 2024 2026` | `python src/<script>.py 2024 2026` | The listed seasons |
| `python3 src/<script>.py --season 2025` | `python src/<script>.py --season 2025` | One season (flag can repeat) |
| `python3 src/<script>.py --start 2020 --end 2023` | `python src/<script>.py --start 2020 --end 2023` | Inclusive range |
| `python3 src/<script>.py -h` | `python src/<script>.py -h` | Show help |

Run both scripts for the same seasons, because the cleaning step needs all three files for each season.

### Notes on in-progress seasons

- **Weeks kept:** for a season still being played, the scripts keep every played week plus the **next** unplayed week. That week has opponent, home/away, and projection data but no actual stats yet. A finished season keeps weeks 1–18.
- **Running mid-week:** if you run `Extrat_stats.py` while a week's games are still in progress, set `UPCOMING_WEEK_OVERRIDE` at the top of the script (for example `{2026: 10}`) to choose which week counts as upcoming. Turn off upcoming rows entirely with `ADD_UPCOMING_WEEK = False`.
- **Runtime:** `Extrat_stats.py` makes one request per player (8 concurrent workers, with retries), so it takes a few minutes per season.
- Each season only needs to be extracted once. Re-run the scripts to refresh the current season.

## 3. Clean the data and build features

Cleaning is done by `clean_data()` in `src/data_pipeline.py`. For each season it reads the three raw files from step 2 and:

1. Filters weekly projections to players in the summary, and fills missing projected points with the player's median projection.
2. Merges game logs with weekly fantasy points and projections.
3. Joins game weather and stadium info from `nflreadpy` schedules (on the ESPN event ID):
   - domes and closed roofs are set to 70°F with no wind
   - missing outdoor wind is filled with the mean outdoor wind
4. Maps `@`/`vs` to `away`/`home` and adds the stadium's city as `location`.
5. Adds `team_pass_rank` and `team_rush_rank`. These use **prior weeks only**, so there is no leakage.

### Run it

**Option A: notebook (any OS).** Open `notebooks/Data_cleaning_function.ipynb` in Jupyter or VS Code and run all cells. The main call is:

```python
cleaned = clean_data([2024, 2025, 2026])
```

**Option B: command line.** Run this from the repository root.

macOS / Linux:

```bash
cd src
python3 -c "from data_pipeline import clean_data; clean_data([2024, 2025, 2026])"
cd ..
```

Windows (PowerShell or Command Prompt):

```powershell
cd src
python -c "from data_pipeline import clean_data; clean_data([2024, 2025, 2026])"
cd ..
```

By default `clean_data` looks for data in `../data` relative to the current directory, so it must be run from a folder one level below the repository root, such as `notebooks/` or `src/`. To run from anywhere else, pass the path yourself: `clean_data([2024], data_dir="path/to/data")`.

### Arguments

| Argument | Meaning |
|---|---|
| `seasons` | An int or a list of ints, e.g. `2025` or `[2024, 2025, 2026]` |
| `data_dir` | Folder holding the raw files (default `../data`) |
| `write` | `True` (default) writes the CSVs below; `False` only returns the DataFrames |

The function returns `{season: DataFrame}`.

## 4. Output: cleaned data

After step 3, `data/` contains:

```
data/
├── player_weeks_{SEASON}.csv       # raw (step 2a)
├── player_gamelogs_{SEASON}.csv    # raw (step 2b)
├── player_summary_{SEASON}.csv     # raw (step 2b)
├── df_{SEASON}_final.csv           # cleaned, one row per player per game
└── dicts/
    ├── df_{SEASON}_dictionary.csv           # column list of the cleaned data
    ├── player_logs_{SEASON}_dictionary.csv  # column list of the raw game logs
    └── player_sum_{SEASON}_dictionary.csv   # column list of the raw summaries
```

`df_{SEASON}_final.csv` is the cleaned dataset used by the analysis and modeling notebooks.

## Quick start

Run these from the repository root.

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 src/Extract_fantasy_points.py
python3 src/Extrat_stats.py
cd src
python3 -c "from data_pipeline import clean_data; clean_data([2024, 2025, 2026])"
cd ..
```

**Windows (PowerShell)**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src/Extract_fantasy_points.py
python src/Extrat_stats.py
cd src
python -c "from data_pipeline import clean_data; clean_data([2024, 2025, 2026])"
cd ..
```

**Windows (Command Prompt)**

```bat
py -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python src/Extract_fantasy_points.py
python src/Extrat_stats.py
cd src
python -c "from data_pipeline import clean_data; clean_data([2024, 2025, 2026])"
cd ..
```
