# CSCI_5502_Fantasy_Project

## Team Members:
**Tristan Martinez**   
**Nishant Devkota**   
**Tushar Koushik**  

## Project goal:
The main purpose of the project is to help fantasy football players decide which players to start and which players to keep on the bench. NFL games run on a weekly cycle, so fantasy football managers need to make decisions every week on which players to start based on their potential fantasy score. 

## Current research questions:
- What are some specific factors that impact a player's performance?
- What is the most efficient way to scrape news data and turn it into numerical values?
- How does the result differ if we only use historical data, instead of also including new data, to predict a player's performance?
- Which machine learning model would work best for our project?

## Data-source references:
The main source of our data will be ESPN. We will scrape historical box score data as our quantitative data and use their news articles for qualitative data. Some important variables: touchdowns, yards received/rushed, number of successful throws, number of successful catches, and opposing defense team rank. We will use web scraping to collect data from ESPN, subject to ping rate limits. Here are some example links:
- https://www.espn.com/nfl/player/gamelog/_/id/3139477/patrick-mahomes
- https://www.espn.com/nfl/scoreboard
- https://www.pro-football-reference.com/players/M/MahoPa00/gamelog/2023/

As for the qualitative news, we will need to do web scraping. If web scraping with BeautifulSoup doesn't work, then we will try to connect to ESPN’s direct api links. Also, the qualitative news is more of an extra analysis, while the historical quantitative data will be used for the core analysis. We will try to gather as much data from news as possible, but a significant amount is not needed.

## Milestone roadmap:
We will spend one week each on all of these steps:
- We will first start by analyzing what exact features we are looking for.
- After engineering the features we want, we will start grabbing both types of data: box score data and news data.
- We will then use these data to do data analysis so we can connect our features with the data.
- The next step will be to create and execute an algorithm that uses all of the information we gathered to project estimated fantasy scores.
- With these predictive scores, the project will provide us with a decision on whether to start or bench a player.
