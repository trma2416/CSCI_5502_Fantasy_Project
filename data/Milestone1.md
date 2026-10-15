## Data Provenance and Acquisition   
**Source:**   
API URLs:  
1. Historical game data: "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{pid}/gamelog"  
2. Current standings: "https://site.api.espn.com/apis/v2/sports/football/nfl/standings"  
3. Next game schedule: "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_abbr_lower}/schedule"
4. Historical fantasy data (actual and projected weekly fantasy points): [2025 Fantasy Player Data](https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2025/segments/0/leaguedefaults/3?view=kona_player_info)
5. Game conditions (stadium, roof, surface, weather): nflverse schedules, loaded with the `nflreadpy` Python package (`nfl.load_schedules(seasons=2025)`)
   
**Date accessed:** 10/12/2026 (nflverse schedules: 10/15/2026). These results will change over time because data is added after new games are played.  
**License/term:** No formal license. The ESPN endpoints (Sources #1–#4) are public but undocumented, and ESPN's Terms of Use apply. The nflverse schedule data (Source #5) is openly published by the nflverse project.  
**Geographic and Time coverage:** No relevant geographic criteria. Time covered is the 2025 NFL regular season (weeks 1–18).  
**Approximate size:** The merged dataset has 7,572 rows and 80 columns covering 685 players (QB, RB, WR, TE, K), about 5.6 MB in memory. The underlying game log CSV is about 1.6 MB.  
**Unit of observation:** Each row represents one regular-season game played by one player during the 2025 season (one player-game).  
**Explain why the source is appropriate for the research questions and what important information it does not contain.**  
Historical game data: This is appropriate for the research question because it looks at the underlying historical data of each player and how they have played in the past. We need this data to answer what score they might get in the next game. This information does not contain who they will play in the next game or how good the next game's team is.  
Current Standings: This is appropriate for the research question because it looks at the current ranks of different teams. This will help us answer how difficult the next game will be for our player. If the opponent's defense rank is high, then our result will be impacted. This source does not contain the future standings, and it gives end-of-season totals rather than a team's rank at the time of each game.  
Next game schedule: This is appropriate for the research question because it tells us who our player will be against for the next game. We need to analyse the next opponent, for which we need to actually know who the next opponent is. This source will give us this information. This source does not contain any other information except for just the schedule, so we will use our other data sources to cover the needed information.  
Historical fantasy data: This is appropriate for the research question because it gives the actual fantasy points each player scored each week, which is the outcome we want to predict. It also gives ESPN's projected points for that week, which we can use as a baseline to compare our model against. This source does not contain the underlying game stats, so we join it with Source #1. Some player-weeks have no projection.  
Game conditions: This is appropriate for the research question because weather, roof type and playing surface may affect how a player performs (for example, wind lowers passing and kicking output). This source does not contain player-level information, and temperature and wind are not recorded for games played in domes or under closed roofs.  
**Describe the acquisition method:** API (Sources #1–#4 through `requests` in `src/data_extract.py` and `src/import_hist.py`; Source #5 through the `nflreadpy` package)  
  
## Data Dictionary and Structure   
**Define the unit of observation: what one row represents:** The data from "Historical game data", "Current standings", "Historical fantasy data" and "Game conditions" are combined into one data frame. Each row within this table is one game played by one player during the 2025 regular season. The data from "Next game schedule" only gives us one value, which is the next opponent of our specified player.  
**Provide a compact data dictionary for the variables that matter to the project: variable name, meaning, data type, units/categories, and source:**
The importance of these variables differs based on the player picked. Some of these variables might be important for Player A, while other variables might be important for Player B. It depends on the role of the player that is picked. Stat columns are stored as floats because a stat that does not apply to a player's position (for example, passing yards for a kicker) is missing (NaN) rather than 0.  
  
**Game and player identifiers**

| Variable name | Meaning | Data type | Unit/Categories | Source |
| --- | --- | --- | --- | --- |
| player_id | ESPN player ID | Integer | ID | Source #4 |
| player | Player's full name | String | Name | Source #4 |
| position | Player's fantasy position | String | QB, RB, WR, TE, K | Source #4 |
| team | Team the player played for in that game | String | NFL team abbreviation | Source #1 |
| season | NFL season | Integer | Year (2025) | Source #1 |
| week | Regular-season week of the game | Integer | 1–18 | Source #1 |
| eventId | ESPN game ID | String | ID | Source #1 |
| date | Game start date and time | String | ISO 8601 timestamp, UTC | Source #1 |
| opponent | Team our player faced in that game | String | NFL team abbreviation | Source #1 (next game: Source #3) |
| atVs | Whether the game was home or away | String | "home", "away" (recoded from "vs"/"@") | Source #1 (next game: Source #3) |
| location | City where the game was played | String | "City, ST" | Derived from team, opponent and atVs |
| result | Game result for the player's team | String | W, L, T | Source #1 |
| score | Final score of the game | String | "team-opponent" (e.g. "23-10") | Source #1 |
| opp_def_rank | Opponent's defense rank by points allowed in that season | Integer | Rank, 1 (fewest allowed) to 32 (most allowed) | Source #2 joined to Source #1 |

**Rushing**

| Variable name | Meaning | Data type | Unit/Categories | Source |
| --- | --- | --- | --- | --- |
| rushingAttempts | Number of times our player ran the ball | Float | Count | Source #1 |
| rushingYards | Total yards gained on rushes | Float | Yards | Source #1 |
| yardsPerRushAttempt | Average yards per rush | Float | Yards/attempt | Source #1 |
| rushingTouchdowns | Number of touchdowns scored on rushes | Float | Count | Source #1 |
| longRushing | Longest rush in the game | Float | Yards | Source #1 |

**Receiving**

| Variable name | Meaning | Data type | Unit/Categories | Source |
| --- | --- | --- | --- | --- |
| receptions | Total number of times our player caught the ball | Float | Count | Source #1 |
| receivingTargets | Number of passes thrown to our player | Float | Count | Source #1 |
| receivingYards | Total yards gained on catches | Float | Yards | Source #1 |
| yardsPerReception | Average yards per catch | Float | Yards/reception | Source #1 |
| receivingTouchdowns | Number of touchdowns scored on catches | Float | Count | Source #1 |
| longReception | Longest catch in the game | Float | Yards | Source #1 |

**Passing**

| Variable name | Meaning | Data type | Unit/Categories | Source |
| --- | --- | --- | --- | --- |
| completions | Number of completed passes | Float | Count | Source #1 |
| passingAttempts | Number of passes thrown | Float | Count | Source #1 |
| passingYards | Total yards gained on passes | Float | Yards | Source #1 |
| completionPct | Percentage of passes completed | Float | Percent | Source #1 |
| yardsPerPassAttempt | Average yards per pass thrown | Float | Yards/attempt | Source #1 |
| passingTouchdowns | Number of touchdown passes | Float | Count | Source #1 |
| interceptions | Number of passes caught by the defense | Float | Count | Source #1 |
| longPassing | Longest completed pass in the game | Float | Yards | Source #1 |
| sacks | Number of times our player was sacked | Float | Count | Source #1 |
| QBRating | NFL passer rating | Float | 0–158.3 | Source #1 |
| adjQBR | ESPN adjusted total quarterback rating | Float | 0–100 | Source #1 |

**Fumbles and defensive / special teams plays**

| Variable name | Meaning | Data type | Unit/Categories | Source |
| --- | --- | --- | --- | --- |
| fumbles | Number of times our player fumbled | Float | Count | Source #1 |
| fumblesLost | Number of fumbles our player lost to the other team | Float | Count | Source #1 |
| fumblesForced | Number of fumbles our player forced | Float | Count | Source #1 |
| fumblesRecovered | Number of fumbles our player recovered | Float | Count | Source #1 |
| kicksBlocked | Number of kicks our player blocked | Float | Count | Source #1 |
| totalTackles | Total tackles made | Float | Count | Source #1 |
| soloTackles | Unassisted tackles | Float | Count | Source #1 |
| assistTackles | Assisted tackles | Float | Count | Source #1 |
| stuffs | Tackles of a ball carrier behind the line of scrimmage | Float | Count | Source #1 |
| stuffYards | Yards lost on stuffs | Float | Yards | Source #1 |
| interceptionYards | Return yards on interceptions made by our player | Float | Yards | Source #1 |
| avgInterceptionYards | Average return yards per interception | Float | Yards/interception | Source #1 |
| interceptionTouchdowns | Interceptions returned for a touchdown | Float | Count | Source #1 |
| longInterception | Longest interception return | Float | Yards | Source #1 |
| passesDefended | Passes our player broke up or intercepted | Float | Count | Source #1 |

**Kicking**

| Variable name | Meaning | Data type | Unit/Categories | Source |
| --- | --- | --- | --- | --- |
| fieldGoalsMade | Field goals made | Float | Count | Source #1 |
| fieldGoalAttempts | Field goals attempted | Float | Count | Source #1 |
| fieldGoalPct | Percentage of field goals made | Float | Percent | Source #1 |
| longFieldGoalMade | Longest field goal made | Float | Yards | Source #1 |
| fieldGoalsMadeYardsAverage | Average distance of field goals made | Float | Yards | Source #1 |
| fieldGoalsMade1_19 | Field goals made from 1–19 yards | Float | Count | Source #1 |
| fieldGoalAttempts1_19 | Field goals attempted from 1–19 yards | Float | Count | Source #1 |
| fieldGoalsMade20_29 | Field goals made from 20–29 yards | Float | Count | Source #1 |
| fieldGoalAttempts20_29 | Field goals attempted from 20–29 yards | Float | Count | Source #1 |
| fieldGoalsMade30_39 | Field goals made from 30–39 yards | Float | Count | Source #1 |
| fieldGoalAttempts30_39 | Field goals attempted from 30–39 yards | Float | Count | Source #1 |
| fieldGoalsMade40_49 | Field goals made from 40–49 yards | Float | Count | Source #1 |
| fieldGoalAttempts40_49 | Field goals attempted from 40–49 yards | Float | Count | Source #1 |
| fieldGoalsMade50 | Field goals made from 50+ yards | Float | Count | Source #1 |
| fieldGoalAttempts50 | Field goals attempted from 50+ yards | Float | Count | Source #1 |
| extraPointsMade | Extra points made | Float | Count | Source #1 |
| extraPointAttempts | Extra points attempted | Float | Count | Source #1 |
| totalKickingPoints | Total points scored by kicking (field goals and extra points) | Float | Points | Source #1 |

**Game conditions**

| Variable name | Meaning | Data type | Unit/Categories | Source |
| --- | --- | --- | --- | --- |
| espn | ESPN game ID used to join Source #5 (same as eventId) | String | ID | Source #5 |
| game_id | nflverse game ID | String | "season_week_away_home" (e.g. "2025_18_DET_CHI") | Source #5 |
| gameday | Game date | String | YYYY-MM-DD, US Eastern | Source #5 |
| gametime | Kickoff time | String | HH:MM, US Eastern | Source #5 |
| stadium | Stadium the game was played in | String | Stadium name | Source #5 |
| roof | Roof type | String | outdoors, dome, closed | Source #5 |
| surface | Playing surface | String | grass, fieldturf, matrixturf, sportturf, astroturf, a_turf | Source #5 |
| temp | Temperature at kickoff (missing for dome/closed-roof games) | Float | Degrees Fahrenheit | Source #5 |
| wind | Wind speed at kickoff (missing for dome/closed-roof games) | Float | Miles per hour | Source #5 |
  
**Identify target/outcome variables if the project has them, but do not assume every project requires a prediction target:**  
  
| Variable name | Meaning | Data type | Unit/Categories | Source |
| --- | --- | --- | --- | --- |
| fantasy_points | Actual fantasy points the player scored in that game. This is the value our model predicts. | Float | Fantasy points (ESPN default league scoring) | Source #4 |
| projected_points | ESPN's pre-game projected fantasy points for that week. This is not a target; it is a baseline to compare our model's predictions against. | Float | Fantasy points (ESPN default league scoring) | Source #4 |
  
**If multiple datasets are joined, document keys, join logic, expected matches, unmatched records, and any aggregation:**
1. **Game logs + defense ranks (Source #1 + Source #2):** Source #2 contains each team and how many points it allowed during the season. Teams are ranked by points allowed (fewest allowed = rank 1), and the rank is mapped onto each game log row by its `opponent` (and `season`). All 7,572 rows matched. Because the rank uses end-of-season totals, games early in the season use a rank that includes games played after them.
2. **Game logs + weekly fantasy points (Source #1 + Source #4):** The weekly fantasy data is first filtered to the 685 players that appear in the game logs, then left-joined on `player_id` and `week`. Columns that exist in both tables (`player`, `position`, `fantasy_points`) are kept from the game logs. `season_type` (always "2025 Regular Season") and `pro_team_id` (duplicates `team`) are dropped. Every row has `fantasy_points`; 291 rows have no `projected_points` because ESPN had no projection for that player-week.
3. **Merged data + game conditions (Source #5):** Left-joined on `eventId` = `espn`. All 7,572 rows matched a game. `temp` and `wind` are missing for 2,633 rows, almost all of them dome or closed-roof games, and `surface` is blank for 27 rows.
4. **Derived columns:** `atVs` is recoded from "vs"/"@" to "home"/"away", and `location` is the home team's city (the player's team for home games, the opponent for away games). `location` assumes each game is played at the home team's stadium, so neutral-site and international games get the wrong city; use `stadium` for those games.

No aggregation is applied to the merged table: it stays at one row per player-game. A separate per-player summary (`player_summary_2025.csv`) aggregates the game logs into season totals and per-game averages.

## Data Cleaning and Preprocessing
A summary of the cleaning done so far in `notebooks/historical.ipynb`. Before the notebook, `src/data_extract.py` already keeps only regular-season games, removes duplicate player-games, splits kicking stats stored as "made-attempts" (e.g. "1-2") into two columns, and converts stat columns to numbers (ESPN's "-" becomes NaN).

1. **Loaded three datasets:** weekly fantasy points (`player_weeks_2025.csv`, 13,958 rows, 1,088 players), player season summaries (`player_summary_2025.csv`, 685 players) and player game logs (`player_gamelogs_2025.csv`, 7,572 rows, 685 players). A list of column names for each was saved as a data dictionary CSV.
2. **Matched players across datasets:** We checked that the summary and game log files contain the same 685 players. The weekly fantasy data covers more players (including D/ST), so it was filtered down to those 685 players.
3. **Checked missing fantasy values:** We looked at rows where `fantasy_points` or `projected_points` is missing. No row is missing both. Missing projections are spread across the season (not just week 1), so they were left as NaN rather than filled in.
4. **Merged game logs with weekly fantasy points:** Left join on `player_id` and `week`. Columns found in both tables (`player`, `position`, `fantasy_points`) were dropped from the weekly data so they are not duplicated.
5. **Dropped redundant columns:** `season_type` has a single value ("2025 Regular Season"), and `pro_team_id` repeats the information in `team`, so both were removed.
6. **Recoded home/away:** `atVs` was changed from "vs"/"@" to "home"/"away".
7. **Added a game location:** A new `location` column holds the home team's abbreviation (the player's team for home games, the opponent for away games). It is then mapped to that team's stadium city (e.g. "Detroit, MI").
8. **Added game conditions:** The 2025 nflverse schedule (stadium, roof, surface, temperature, wind, game date and time) was left-joined on `eventId` = `espn`. `eventId` was converted to a string so the keys match.
9. **Saved the merged data dictionary:** The final list of 80 columns was saved to `merged_data_dict.csv`.

**Known issues still to fix:**
- Washington is "WSH" in ESPN data but "WAS" in the city lookup, so `location` is missing for Washington home games.
- `location` gives the wrong city for neutral-site and international games.
- `temp` and `wind` are missing for dome and closed-roof games and still need a fill strategy (or a flag for indoor games).
- `surface` is blank for 27 rows.
- The merged dataset has not been saved to a CSV yet, only its column list.
