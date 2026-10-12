## Data Provenance and Acquisition   
**Source:**   
API URLs:  
1. Historical game data: "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{pid}/gamelog"  
2. Current standings = "https://site.api.espn.com/apis/v2/sports/football/nfl/standings"  
3. Next game schedule = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_abbr_lower}/schedule"
   
**Date accessed:** 10/12/2026; this will change over time because the data gets added after new games in the future  
**License/term:** None  
**Geographic and Time coverage:** No relevant geographic criteria. Time covered is 2024-current regular season data.  
**Approximate size:** Per player: Approximately 26 columns, 34 rows. ~42 KB  
**Unit of observation:** Each row represents one game played by our specific player during the 2026-2026 regular season.  
**Explain why the source is appropriate for the research questions and what important information it does not contain.**  
Historical game data: This is appropriate for the research question because it looks at the underlying historical data of each player and how they have played in the past. We need this data to answer what score they might get in the next game. This information does not contain who they will play for in the next game or how good the next game's team is.  
Current Standings: This is appropriate for the research question because it looks at the current ranks of different teams. This will help us answer how difficult the next game will be for our player. If the opponent's defense rank is high, then our result will be impacted. This source does not contain the future standings.  
Next game schedule: This is appropriate for the research question because it tells us who our player will be against for the next game. We need to analyse the next opponent, for which we need to actually know who the next opponent is. This source will give us this information. This source does not contain any other information except for just the schedule, so we will use our other data sources to cover the needed information.  
**Describe the acquisition method:** API  
  
## Data Dictionary and Structure   
**Define the unit of observation: what one row represents:** The data we scrape from "Historical game data" and "Current standings" will be combined into one data frame. Each row within this table is one game played by our player during the 2024-2026 regular season. The data from "Next game schedule" only gives us one value, which is the next opponent of our specified player.  
**Provide a compact data dictionary for the variables that matter to the project: variable name, meaning, data type, units/categories, and source:**
The importance of these variables differs based on the player picked. Some of these variables might be important for Player A, while Other variables might be important for Player B. It depends on the role of the player that picked.  
  
| Variable name | Meaning | Data type | Unit/Categories | Source |
| --- | --- | --- | --- | --- |
| Receptions | Total number of times our player caught the ball | Integer | Count | Source #1 |
| Receiving Yards | Total number of yards our player caught the ball for | Integer | Yard | Source #1 |
| Receiving Touchdowns | Number of touchdowns scored on catches | Integer | Count | Source #1 |
| Rushing Attempts | Number of times our player ran the ball | Integer | Count | Source #1 |
| Rushing Yards | Total yards gained on rushes | Integer | Yards | Source #1 |
| Rushing Touchdowns | Number of touchdowns scored on rushes | Integer | Count | Source #1 |
| Fumbles Lost | Number of fumbles our player lost to the other team | Integer | Count | Source #1 |
| Completions | Number of completed passes | Integer | Count | Source #1 |
| Passing Attempts | Number of passes thrown | Integer | Count | Source #1 |
| Passing Yards | Total yards gained on passes | Integer | Yards | Source #1 |
| Passing Touchdowns | Number of touchdown passes | Integer | Count | Source #1 |
| Interceptions | Number of passes caught by the defense | Integer | Count | Source #1 |
| Sacks | Number of times our player was sacked | Integer | Count | Source #1 |
| Rushing Yards | Total yards gained on rushes | Integer | Yards | Source #1 |
| Rushing Touchdowns | Number of touchdowns scored on rushes | Integer | Count | Source #1 |
| Opponent | Historic and future game: Team our player faced in that game | String | NFL team abbreviation | Combination of: Source #1 & Source #3 |
| At/Vs | Historic and future game: Whether the game was home or away | String | "vs" = home, "@" = away | Combination of: Source #1 & Source #3 |
| Opponent Defense Rank | Historic and future game: Opponent's defense rank by points allowed in that season | Integer | Rank, 1 (best) to 32 (worst) | Combination of: Source #1, Source #2, and Source #3 |  
  
**Identify target/outcome variables if the project has them, but do not assume every project requires a prediction target:**
**| Variable name | Meaning | Data type | Unit/Categories | Source |**
| Total fantasy points | A predictive value after weighting and aggregating variables above into an algorithm | float | Count | Source: ML algorithm that consumed variables above |  
**If multiple datasets are joined, document keys, join logic, expected matches, unmatched records, and any aggregation:**
Source #1 and Source #2 are joined into one data table. Source #2 uses the "opponent" column and "season" column from Source #1 to join. Source #2 contains each team and how many points they allowed their opponent to score. This is used to rank each team (more scores allowed means a lower rank in defense). This list of teams and their ranks is then combined into Source #1 by matching the season year and our specified opponent name.
