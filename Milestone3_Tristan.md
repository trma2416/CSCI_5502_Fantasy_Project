# Model Selection

For this project we opted to use XGBoost to model our data. We read that Gradient Boosting is a good algorithm for capturing the complexity of a large input space with categorical and numerical data. Specifically, XGBoost is a more optimized version of Gradient Boosting. 

For my model, I opted to first study the relationships between different positions. Looking first, at the correlations between the fantasy scores across all positions using a pearson matrix. I then generated different dataframes for each postion and modified the columns to remove columns that do not contribute to the scoring metrics of that position. Once I obtained each postional dataframe, I one-hot-encoded the categorical data and then performed MLR on each postional dataframe.

Once finding the coefficient vectors for each contributing attribute, I standardized the coefficient vectors by sorting them in a descending order based on their contributing coefficient value. I then calculated the cosine simularity between each vector based on position and then plotted a heatmap of the values of the cosine similarity based on position. 

Comparing the two heatmaps, The R-squared heatmap of fantasy points of each position vs the cosine simularity of the MLR coefficients of each postion, we can see that the MLR coefficients heatmap captures more correlations that the standard R-squared correlation. 

Using the standardizex MLR coefficients position similarity, I opted to use these values of cosine similarity to determine the clusters of postions using dendrogram clustering. We compared the spearman rank correlation against the standardized coefficients to ensure that the spearman ranks agree with the correlations found.

The clustering resulted in 3 groups:
|Group 1|Group 2|Group 3|
|-------|-------|-------|
|   RB  |QB, TE | WR, K |


Once the clusters were generated, I moved into the XGBoost_cluster.ipynb to begin to implement the models. I obtained 2024 and 2025 data and following the EDA portion where I generated the contributing attributes, I followed this schema. I then had to perform a shift of specific attributes by a week such that our model is using old scoring data and current contextual data to train on because we are wanting to use the historical data combined with the current weather data to predict a future score. Once that task was completed I had to label our categorical data as a "category" dtype for the input of XGBoost. Finally, I generated our training, validation, and testing splits. We opted to use all of 2024 and half of 2025 as training, weeks 7-9 in 2025 as validation, and the rest of the weeks in 2025 as testing. 