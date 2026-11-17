# Milestone 3: Modeling, Comparison, and Evaluation

---

## 1. Modeling Plan

### 1.1/1.2 Project questions and the methods that address them

The project goal (Milestone 1) is to help fantasy managers make weekly start/sit decisions. Milestone 2 revised the research questions (RQ). The table maps each method we ran to those questions.

| Method | Notebook | Task type | Research question addressed |
|---|---|---|---|
| ESPN projected points (`next_week_projected`) | `XGBOOST.ipynb`, `XGBoost_cluster.ipynb`, `test*.ipynb`, `analysis.ipynb` | Regression baseline (established domain benchmark) | RQ2: can a model built only on pre-kickoff information beat ESPN's projections? |
| Per-position multiple linear regression (MLR) on game context | `Modeling_data_prep.ipynb` | Regression (exploratory, not a forecaster) | RQ1: which pre-game factors are associated with weekly fantasy points? |
| Hierarchical clustering of positions by cosine similarity of standardized MLR coefficients | `Modeling_data_prep.ipynb` | Clustering (of 5 positions, not of players) | RQ4: does the best model differ by position, and can positions share a model? |
| Global XGBoost regressor (one model for all positions) | `XGBOOST.ipynb`, `test_global.ipynb` | Regression / one-week-ahead forecasting | RQ2, RQ4 |
| Clustered XGBoost regressors (RB; QB+TE; WR+K) | `XGBoost_cluster.ipynb`, `test.ipynb` | Regression / one-week-ahead forecasting | RQ2, RQ4 |
| Side-by-side evaluation of the saved models on the same 2026 player-games | `analysis.ipynb` | Model comparison | RQ2, RQ4 |

**Target:** `target_next_week_fantasy` (both global and clustered). It is the player's fantasy points in their **next game played**, built by `shift(-1)` within each `(player_id, season)` group. Each row combines what was known after week *N* with the scheduled context of game *N+1*.



### 1.3 Why these methods fit the data

- **Data size and shape.** The modeling frame stacks the 2024, 2025 and 2026 seasons: 7,522 + 7,572 + 4,440 player-game rows. After removing rows with no next game, the global model has 10,555 training rows, 3,183 validation rows and 3,250 test rows (`XGBOOST.ipynb`, cell 9). The data are tabular, mix numeric and high-cardinality categorical columns (`player`, `next_week_opponent`, `next_week_stadium`, `team`), and have many structurally missing values (for example, kicking stats are NaN for WRs).
- **Why gradient-boosted trees.** XGBoost (version 3.4.1, per the saved model JSON) takes native categorical splits (`enable_categorical=True`) and learns default directions for NaNs. This avoids one-hot encoding several hundred player levels and avoids imputing stats that do not apply to a position. Trees also capture the nonlinear, position-dependent relationships that the linear models in `Modeling_data_prep.ipynb` failed to find. The RB MLR had an adjusted R² of −0.013.
- **Why MLR plus clustering before modeling.** Positions score on very different scales and from different stats. The question was whether one model can serve all positions or whether position groups need their own models. MLR coefficients were used as a cheap, interpretable signature of how each position responds to game context.
- **Why ESPN as the baseline.** ESPN's projection is what a fantasy manager would otherwise use, so beating it is the practical bar for a start/sit tool (Milestone 2 EDA: ESPN MAE 3.70, r = 0.71 on 2025).



### 1.4 Assumptions, constraints and failure modes in our implementation

1. **Selection on playing.** `shift(-1)` takes the next game the player *appeared in*. Bye weeks, injuries and inactive weeks are skipped, so the target never includes "did not play." A manager who starts an injured player gets 0, but our evaluation never sees that case. Measured errors are therefore optimistic for real start/sit use.
2. **Season-level context columns.** `opp_def_rank`, `team_pass_rank` and `team_rush_rank` have exactly one value per opponent per season in all three data files (checked: max distinct values per opponent = 1). For 2024 and 2025 they are end-of-season values, which leak the outcome of later games. `XGBOOST.ipynb` removes them for this reason (comment in cell 2).
3. **Player identity as a feature.** `player` is a categorical feature in every model and has the largest mean |SHAP| in all four of them (Section 6.2). The models depend on having seen the player before. Rookies and players new in 2026 are unseen categories, and no notebook measures error for them.
4. **Weather is the observed game-day value.** `next_week_temp` and `next_week_wind` come from nflverse game records, not forecasts. In real use only a forecast would be known before kickoff. The SHAP values for these features are small (≤ 0.04), so the effect is likely minor.
5. **Known data issues carried forward from Milestone 2.** International games have the home team's US stadium, roof and surface (2.6% of 2025 rows). About 27% of rows score exactly 0, often players with no offensive role.

---

## 2. Required Comparison

| Role | Approach | Evidence |
|---|---|---|
| Baseline / reference | ESPN's projected points for the same game (`next_week_projected`) | Every evaluation notebook |
| Candidate 1 | Global XGBoost, one model for all positions, 97 features | `XGBOOST.ipynb`, `test_global.ipynb` |
| Candidate 2 | Clustered XGBoost, three models (RB; QB+TE; WR+K) routed by position, each on the same 97 features | `XGBoost_cluster.ipynb`, `test.ipynb` |
| Supporting analysis | Per-position MLR and hierarchical clustering, used to choose the groups for Candidate 2 | `Modeling_data_prep.ipynb` |

The ESPN projection counts as an "established domain benchmark" under the assignment. It is a strong baseline because it was built by a professional system with access to information we do not have (injury reports, depth charts, betting lines).



Both candidates use the same modeling frame: the same 97 features, target, row filtering, train/validation/test split and hyperparameters (including `early_stopping_rounds=50`). `XGBoost_cluster.ipynb` builds the frame with the same code as `XGBOOST.ipynb` and then partitions the rows by position group, so the three groups together are exactly the global model's 10,555 / 3,183 / 3,250 rows. The only difference between the candidates is whether one model is fit to all positions or one model per group, so any difference in results can be attributed to the grouping.



---

## 3. Modeling Data Preparation

### 3.1 Features used

**Global model (97 features, `XGBOOST.ipynb`).**
- *Identity and time:* `player`, `position`, `week`.
- *Last-game box-score stats* for all positions: rushing, receiving, passing, kicking, ball security, and defensive columns that are almost always NaN for offensive players.
- *Next-game context:* `next_week_opponent`, `next_week_atVs`, `next_week_roof`, `next_week_surface`, `next_week_temp`, `next_week_wind`, `next_week_location`.
- *Engineered history:* career cumulative mean and season-to-date mean for 14 stats (`fantasy_points`, receptions, targets, yards, touchdowns, attempts, interceptions, fumbles lost), plus a 3-game rolling mean of `fantasy_points`, `receivingTargets`, `rushingAttempts` and `passingAttempts`.

**Clustered models (`XGBoost_cluster.ipynb`).** The same 97 features as the global model. Each of the three models (RB; QB+TE; WR+K) is trained only on the rows for its positions. Stats that do not apply to a position (for example kicking stats for a WR) are NaN, and XGBoost handles them through its learned default split direction.

### 3.1 (continued) Features intentionally excluded

| Excluded | Reason (from notebook code and comments) |
|---|---|
| `fantasy_points` (current week), `result`, `score`, `score_category` | Same-game outcomes. `fantasy_points` would be redundant with the history features and is not the target |
| `projected_points`, `next_week_projected`, `med_proj_pts`, `espn` | ESPN's projection is the baseline, not an input. `med_proj_pts` is a season median and leaks later weeks (Milestone 2) |
| `opp_def_rank`, `team_pass_rank`, `team_rush_rank` (current week) | Season-level values. In both models the next-week versions were also removed ("opp_def_rank is a season-end value, so it leaks future games") |
| `atVs`, `roof`, `surface`, `temp`, `wind`, `location` (current week) | Replaced by their next-week versions. The context that matters is the game being predicted |
| `player_id`, `eventId`, `game_id`, `date`, `gameday`, `season`, `Unnamed: 0` | Identifiers or duplicates. `player` is kept as the identity feature |
| `team`, `stadium`, `gametime` | Excluded from both models (the two notebooks use the same exclusion list) |

### 3.2 Encoding, scaling and transformations

- **Categorical encoding.** Columns are cast to pandas `category` and passed to XGBoost with `enable_categorical=True`. There is no one-hot encoding or target encoding. The saved models store the category vocabulary, and `analysis.ipynb` reports zero prediction failures from unseen categories on the 3,163 test rows.
- **Scaling.** None, because tree splits do not depend on feature scale. Standardization (z-scores on features and target) was used only in the MLR step, so that coefficients could be compared across positions.
- **One-hot encoding** (`drop_first=True`) was used only for the exploratory MLR. That step showed that `opp_def_rank` is determined exactly by the `opponent` dummies and `location` by `team`, `opponent` and `atVs`, which produced a rank-deficient design matrix (condition number ≈ 7×10¹⁷).
- **Feature construction.** Next-game context comes from `shift(-1)` within `(player_id, season)`, so a season's last game never takes the next season's week 1 as its target. Expanding means (`expanding().mean()`) and rolling means (`rolling(3, min_periods=1)`) include the current week *N*. This is valid because the target is week *N+1*.
- **Row filtering.** Rows with a NaN target are dropped (`utils.clean`) in both notebooks. This removes each player's last game of a season, including 2026 week 10, which has not been played.

### 3.3/3.4 Leakage controls and remaining leakage

**Methods used to prevent target leakage, evaluation leakage, and to accomodate for time-dependent data:**
- The split is time-ordered (Section 4.2). No random split was used.
- The target and next-week context are shifted within player-season, and the commit "fixed data leak" (`211aac6`) added the season grouping.
- Season-level opponent ranks and the season-median projection were removed from the global model.
- Hyperparameters and early stopping use only the validation set. The 2026 test season is not used for fitting or tuning.



---

## 4. Validation and Evaluation Strategy

### 4.1 Metrics

| Metric | Why it matters for this problem |
|---|---|
| **MAE** (primary) | It is in fantasy points, which is the unit a manager reasons in ("off by 4 points"). It is less dominated by the rare 40-point games than RMSE. |
| **RMSE** | Penalizes large misses. Those are the boom and bust weeks that hurt a lineup most. It is also XGBoost's early-stopping metric. |
| **R²** | Share of the week-to-week variance explained, on the same scale for all three predictors. |
| **Head-to-head win count** (model closer than ESPN for that player-game), by position | Directly answers RQ2 per position and shows where the model adds value even when its average error is worse. |
| **MAE by predicted week** | Checks whether performance is stable through the season or depends on how many weeks of history are available. |


### 4.2 Split strategy

| Split | Data | Global rows (finite target) | Purpose |
|---|---|---|---|
| Train | All of 2024 + 2025 weeks 1–9 | 10,555 | Fit trees |
| Validation | 2025 weeks 10–18 | 3,183 | Early stopping; manual hyperparameter checks |
| Test | 2026 weeks 1–9 (predicting weeks 2–9; week 10 is unplayed) | 3,250 (3,163 with an ESPN projection) | Final, untouched comparison |

The split respects time order. Every validation row comes after every training row, and the test season comes after both. This mirrors real use: train on the past, predict the coming weeks. With only about 2.5 seasons, time-series cross-validation (for example an expanding window over weeks) would give more stable estimates than a single validation window, but it was not used.


### 4.3 Common evaluation protocol

`analysis.ipynb` builds one input frame with the same code as `XGBOOST.ipynb` (Section 3) and uses it for all four saved models. The global model scores every row of it. Each cluster model scores only the rows for its positions, with the same 97 features. Before predicting, the notebook checks that each saved cluster model's feature list equals the global one, and it stops with a message to retrain if it does not. Blocks 10–12 then build a matched test set so that all three predictors are scored on exactly the same rows:
- inner join on `(player_id, predicted week)`;
- assertions that the actual score agrees between the global and cluster rows and that there are no duplicate keys;
- result: **3,163 player-games, 562 players, predicted weeks 2–9** (WR 1,151; TE 750; RB 740; QB 286; K 236).

---

## 5. Tuning and Model Selection

### 5.1 Search strategy

Hyperparameters were tuned **manually**. All four final models use the same configuration:

| Parameter | Value | Role |
|---|---|---|
| `n_estimators` | 10,000 (upper bound) | Actual number of trees set by early stopping |
| `learning_rate` | 0.005 | Small steps, many trees |
| `max_depth` | 5 | Limits how many features can interact in one tree |
| `min_child_weight` | 3 | Minimum leaf weight, guards against very small leaves |
| `subsample` / `colsample_bytree` | 0.7 / 0.7 | Row and column subsampling for regularization |
| `early_stopping_rounds` | 50 | Stops when validation RMSE stops improving |

One alternative configuration is left commented out in `XGBOOST.ipynb` (`learning_rate=0.01`, `max_depth=8`, `min_child_weight=5`, `subsample=colsample=0.5`). Its result is not recorded.

Early-stopping results on the validation set (from the saved model metadata):

| Model | Best iteration | Best validation RMSE |
|---|---|---|
| Global | 360 | 5.908 |
| RB | 461 | 6.150 |
| QB+TE | 405 | 5.915 |
| WR+K | 319 | 5.803 |

**Tuning Process:** Our tuning process consisted of a trial and error approach based on the starting points that are the midpoints of each parameters' range, then iteratively modifying the hyperparameters until no meaningful change in the RMSE occured. 

The test set was not used for tuning. Early stopping and all hyperparameter choices relied on 2025 weeks 10–18 only.

### 5.2 Final comparison on the test set

> **Note:** the clustered results below (and the clustered SHAP values in Section 6.2 and player examples in Section 6.3) come from the earlier clustered models, which used a different feature set. `XGBoost_cluster.ipynb` now trains on the global feature set, and `analysis.ipynb` and `test.ipynb` have been updated to give the cluster models the same inputs. These numbers must be updated after re-running `XGBoost_cluster.ipynb` and then `analysis.ipynb` and `test.ipynb`.

**Overall, on the 3,163 matched 2026 player-games (`analysis.ipynb`, block 12):**

| Predictor | MAE | RMSE | R² |
|---|---|---|---|
| **ESPN projection (baseline)** | **3.868** | **5.504** | **0.496** |
| Global XGBoost | 4.376 | 5.947 | 0.412 |
| Clustered XGBoost (combined) | 4.623 | 6.130 | 0.375 |



**By clustered group (`test.ipynb`):**

| Group | Rows | Model MAE | ESPN MAE | Model R² | ESPN R² |
|---|---|---|---|---|---|
| RB | 740 | 4.544 | 3.818 | 0.392 | 0.513 |
| QB+TE | 1,036 | 4.634 | 3.677 | 0.447 | 0.567 |
| WR+K | 1,387 | 4.657 | 4.038 | 0.297 | 0.420 |

**Head-to-head wins against ESPN (share of player-games where the model was closer):**

| Position | Global wins | Clustered wins |
|---|---|---|
| K | 125 / 236 (53.0%) | 124 / 236 (52.5%) |
| RB | 310 / 740 (41.9%) | 298 / 740 (40.3%) |
| WR | 467 / 1,151 (40.6%) | 423 / 1,151 (36.8%) |
| QB | 108 / 286 (37.8%) | 96 / 286 (33.6%) |
| TE | 255 / 750 (34.0%) | 265 / 750 (35.3%) |
| **All** | **1,265 / 3,163 (40.0%)** | **1,206 / 3,163 (38.1%)** |

**MAE by predicted week, 2026:** the global model ranges from 4.21 to 4.66, the clustered models from 4.38 to 4.82, and ESPN from 3.68 to 3.98. ESPN has the lowest MAE in **every** week, and the global model is lower than the clustered models in every week.

### 5.3 Model selection

**Selected learned model: Global XGBoost.** It is better than the clustered approach on every overall metric, in every week, and on head-to-head wins for four of five positions (TE is the exception). It is also simpler to deploy and reproduce: one model and one feature pipeline instead of three plus a routing table. That fits the instruction to prefer the simpler model when performance is similar or better.

**Neither model beats the baseline.** ESPN's projection is still the best predictor. Its MAE is 0.51 points lower than the global model's, and it is closer on 60% of player-games. The answer to RQ2 for this round is therefore **no**. The only position near parity is kicker, where the model wins slightly more than half the time.

---

## 6. Interpretation, Errors, and Limitations

### 6.1 What the models found, in terms of the project questions

- **RQ1 (pre-game factors).** Game context alone explains almost none of the week-to-week variation. In `Modeling_data_prep.ipynb`, every numeric pre-game feature had |r| ≤ 0.08 with RB fantasy points. The RB MLR had train R² = 0.066, adjusted R² = −0.013 and F-test p = 0.868, with a test RMSE of 8.22 on the last ~25% of weeks. Standardized MLR coefficients were below 0.10 for most features and at most about 0.33 across positions. The tree models agree (Section 6.2): the player's own history dominates, and context features rank lower.
- **RQ2 (beat ESPN).** No, overall or by position, except a slight edge for kickers on win count.
- **RQ4 (does the best model differ by position).** Clustering positions by their context coefficients did not help. Pooling all positions worked better. With both candidates now trained on the same features (Section 2), this comparison isolates the effect of grouping once the clustered results are re-run.

**Position clusters found (`Modeling_data_prep.ipynb`).** Hierarchical clustering with average linkage, using distance = 1 − cosine similarity:

| Group | Positions | Cosine similarity | Spearman rank agreement |
|---|---|---|---|
| 1 | QB, TE | 0.87 | 0.79 |
| 2 | WR, K | 0.67 | 0.43 (WR–QB is almost as high at 0.40) |
| 3 | RB | ≤ 0.20 with every other position | −0.15 to 0.22 |

These clusters should be read with caution:
- They compare very weak, noisy coefficients.
- The QB–TE similarity is driven mostly by `surface_*` dummies, which may stand in for specific stadiums or teams.
- WR–K has no football explanation.
- The cluster stability was never tested, for example on 2024 data or by bootstrapping players.

The cross-position R² heatmap gives a different and more intuitive picture: QB–WR R² = 0.35 and QB–TE = 0.11, with every other pair ≤ 0.02. **⚠ Gap:** `Milestone3_Tristan.md` says the MLR heatmap "captures more correlations" than the R² heatmap and that "the spearman ranks agree." The notebook's own interpretation says the WR–K grouping is weaker under Spearman. "Captures more correlations" is not a measured property, so the write-up should be reworded to match the notebook.

### 6.2 Feature importance (TreeSHAP, mean |SHAP| on 2026 rows)

SHAP values come from XGBoost's built-in TreeSHAP (`pred_contribs=True`). They are in fantasy points, and each row's values add up to its prediction.

| Rank | Global | RB | QB+TE | WR+K |
|---|---|---|---|---|
| 1 | `player` (1.76) | `player` (2.65) | `player` (3.12) | `player` (2.37) |
| 2 | `fantasy_points_season_avg` (1.46) | `rushingAttempts` (0.88) | `passingAttempts` (0.47) | `receivingTargets` (0.53) |
| 3 | `fantasy_points_cum_career_avg` (0.49) | `next_week_opponent` (0.51) | `next_week_opponent` (0.41) | `next_week_stadium` (0.28) |
| 4 | `fantasy_points_last3` (0.38) | `next_week_stadium` (0.41) | `receivingTargets` (0.38) | `receptions` (0.25) |
| 5 | `next_week_opponent` (0.21) | `rushingYards` (0.31) | `passingYards` (0.32) | `next_week_opponent` (0.23) |

**Interpretation:**
- **Player identity and usage dominate.** All four models rely mostly on *who* the player is. After that, the clustered models use usage volume (rushing attempts, targets, pass attempts), and the global model uses the engineered averages of past points. Those averages are a smoother summary of the same information. That is the likely reason the global model does better, since the clustered models only see one noisy game of raw stats.
- **Context matters, but second.** Opponent and stadium are the main context features. Weather, roof and surface are near the bottom.
- **These are associations, not causes.** SHAP explains what the model uses, not what drives scoring. Large SHAP values for `player` and `next_week_stadium` are high-cardinality categorical features, and tree models can over-split on those. Part of their importance may come from memorizing player-level and venue-level averages.



### 6.3 Errors and difficult cases

- **Predictions are compressed toward the mean.** The player examples in `analysis.ipynb` show the models predicting in a narrow band. Patrick Mahomes's predictions (both models) were 15.0–18.6 against actuals of 6.0–29.0. Brandon Aubrey's were 6.7–10.8 against 1.0–17.0. Big weeks are missed by the most. Jahmyr Gibbs scored 41.4 in week 3 and 37.7 in week 5, and the global model predicted 18.3 and 16.5 (errors of 23.1 and 21.2). ESPN also missed those weeks, but by less (16.1 and 10.7). This is the expected behavior of a squared-error model on a noisy, right-skewed target. It also means the model is weakest exactly on the boom weeks that matter most for start/sit decisions (RQ5).
- **Where the model beats ESPN.** Justin Jefferson: the clustered model MAE was 5.51 and ESPN's 7.70, because ESPN kept projecting about 18 points while his actual output fell. The model adapts faster to a player's recent drop. Kickers are the only position with a win rate above 50%, which is consistent with kicking being hard for anyone to project.
- **ESPN projections of 0.** The week-10 lookup shows ESPN projecting 0.00 for Lamar Jackson, Jaxson Dart and Sam Darnold while the models predicted 16–20 points. A projection of 0 usually means ESPN expects the player to be out. Our models have no injury or availability information, so they cannot make that call.
- **Single-player results are anecdotes.** `analysis.ipynb` notes that the per-player comparisons (5 players, 6–8 games each) cannot rank the models. The aggregate test results in Section 5.2 are the evidence.

### 6.4 Subgroup performance and fairness

The subjects are professional athletes, and the output is advice for a recreational game, so there are no protected-attribute fairness concerns. The relevant subgroup analysis is by position. It is reported in Section 5.2: the model is weakest for TE and QB on win rate and closest to ESPN for K and RB. **⚠ Gap:** per-position MAE for the global model was never computed (only win counts). Error for rookies or low-history players, and for low-usage players who score near 0, was not examined. These are the groups where a player-identity feature is least reliable.

### 6.5 What the evaluation does not show

- **It does not show causation.** Features with high SHAP values (opponent, stadium) are associated with predictions. They do not cause scoring changes.
- **It does not show the model is useful for start/sit decisions.** MAE was evaluated, but ranking within position and week was not, and players who did not play are excluded.
- **It does not generalize beyond these seasons.** There is one test window (2026 weeks 2–9), one model per approach (one random seed, `random_state=12`), and no confidence intervals. The MAE gap between global and clustered (0.25 points) and between global and ESPN (0.51 points) has no reported uncertainty. A paired bootstrap over players would show whether the global–clustered gap is reliable.

---

## 7. Summary of Evidence Gaps and Required Fixes

| # | Area | Issue | Suggested fix |
|---|---|---|---|
| 1 | Plan | RQ3 (history vs. history + context) and RQ5 (boom/bust) have no model or results | Train a history-only global model, and add a boom/bust classifier or threshold evaluation |
| 2 | Plan | XGBoost chosen without a simpler learned competitor | Add a ridge regression or random forest on the global features |
| 3 | Comparison | No naive baseline | Score `fantasy_points_season_avg` and `fantasy_points_last3` as predictors on the same 3,163 rows |
| 4 | Comparison | QB+WR+TE / RB / K grouping proposed but code commented out | Run it or remove the section |
| 5 | Leakage | Position clustering used 2025 weeks 10–18 (the validation set) | Re-run the clustering on training weeks only |
| 6 | Baseline | Some ESPN projections are season-median imputations or 0 | Flag imputed rows and report ESPN metrics with and without them |
| 7 | Documentation | `Milestone3_Tristan.md` states the wrong split (val = 2025 weeks 7–9, test = rest of 2025) | Correct it to train 2024 + 2025 weeks 1–9, val 2025 weeks 10–18, test 2026 |
| 8 | Documentation | `Milestone3_Tristan.md` overstates agreement between the MLR, R² and Spearman results | Use the notebook's own caveats |
| 9 | Tuning | Manual tuning with no record of the configurations tried | Log each configuration and its validation RMSE, or run a small randomized search on the validation set |
| 10 | Reproducibility | `analysis.ipynb` used a 450-round global model, while the committed model (from `XGBOOST.ipynb`) has 411 rounds, giving different metrics (MAE 4.376 vs 4.410) | Fix one model version and re-run every evaluation notebook |
| 11 | Reproducibility | `figures/shap_top_features.png` is overwritten by two notebooks | Save to model-specific file names |
| 12 | Evaluation | No ranking metric, no per-position MAE for the global model, no confidence intervals, single seed | Add Spearman within position-week, per-position MAE, and a bootstrap CI on the MAE differences |
| 13 | Evaluation | Rows where the player did not play next are excluded by construction | State this in the results, or model availability separately |
