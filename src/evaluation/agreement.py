import pandas as pd
import numpy as np
from scipy import stats
from sklearn.metrics import cohen_kappa_score

# Read the data
data = pd.read_csv('Beaverton_mitigation_policy/evaluation.csv')

# Create a mapping for ordinal values
ordinal_map = {'No': 0, 'Could be better': 0.5, 'Yes': 1, 'Not Applicable': np.nan}

# Convert human_score and input_score to numeric
data['human_score_num'] = data['human_score'].map(ordinal_map)
data['input_score_num'] = data['input_score'].map(ordinal_map)

# Remove rows with NaN values
data_clean = data.dropna(subset=['human_score_num', 'input_score_num'])

def spearman_correlation(data):
    return stats.spearmanr(data['human_score_num'], data['input_score_num'])

spearman_corr, p_value = spearman_correlation(data_clean)
print(f"Spearman's correlation: {spearman_corr}, p-value: {p_value}")

def kendall_tau(data):
    return stats.kendalltau(data['human_score_num'], data['input_score_num'])

kendall_tau_val, p_value = kendall_tau(data_clean)
print(f"Kendall's tau: {kendall_tau_val}, p-value: {p_value}")

def weighted_cohens_kappa(data):
    human_scores = data['human_score_num'].astype(int)
    input_scores = data['input_score_num'].astype(int)
    
    # Use 'quadratic' weights, which is equivalent to the method we tried before
    return cohen_kappa_score(human_scores, input_scores, weights='quadratic')

kappa = weighted_cohens_kappa(data_clean)
print(f"Weighted Cohen's kappa: {kappa}")


aspects = data_clean['aspect'].unique()
for aspect in aspects:
    aspect_data = data_clean[data_clean['aspect'] == aspect]
    if len(aspect_data) > 2:
        print(f"\nResults for aspect: {aspect}")
        spearman_corr, spearman_p = spearman_correlation(aspect_data)
        print(f"Spearman's correlation: {spearman_corr:.4f}, p-value: {spearman_p:.4f}")
        
        kendall_tau_val, kendall_p = kendall_tau(aspect_data)
        print(f"Kendall's tau: {kendall_tau_val:.4f}, p-value: {kendall_p:.4f}")
        
        kappa = weighted_cohens_kappa(aspect_data)
        print(f"Weighted Cohen's kappa: {kappa:.4f}")