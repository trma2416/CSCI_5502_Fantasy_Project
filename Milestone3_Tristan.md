# Model Selection

For this project we opted to use XGBoost to model our data. We read that Gradient Boosting is a good algorithm for capturing the complexity of a large input space with categorical and numerical data. Specifically, XGBoost is a more optimized version of Gradient Boosting. 

For my model, I opted to first study the relationships between different positions, looking at the correlations between just the fantasy scores across all positions using a pearson matrix. I then generated different dataframes for each postion and modified the columns to remove columns that do not contribute to the scoring metrics of that position. Once I obtained each postional dataframe, I one-hot-encoded the categorical data and then performed MLR on each postional dataframe to find the highest contributing attributes for each postion. 

Next, I am going to 