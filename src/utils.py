import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

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