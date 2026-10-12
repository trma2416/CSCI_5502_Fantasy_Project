## Data Provenance and Acquisition   
**Source:**   
API URLs:  
Historical game data: "https://site.web.api.espn.com/apis/common/v3/sports/football/nfl/athletes/{pid}/gamelog"  
Current standings = "https://site.api.espn.com/apis/v2/sports/football/nfl/standings"  
Next game schedule = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_abbr_lower}/schedule"  
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
Identify target/outcome variables if the project has them, but do not assume every project requires a prediction target.
If multiple datasets are joined, document keys, join logic, expected matches, unmatched records, and any aggregation.
