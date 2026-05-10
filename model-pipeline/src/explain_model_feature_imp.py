import re
import matplotlib.pyplot as plt
import numpy as np
from sklearn.base import RegressorMixin
from pathlib import Path
from constants import models_dir


def get_importances_and_name(model_tuple, model_name: str) -> tuple[np.ndarray, str, list[str]]:
    regressors = [m for m in model_tuple if isinstance(m, RegressorMixin)]

    feature_names = None
    for component in model_tuple:
        if hasattr(component, 'feature_names_in_'):
            feature_names = list(component.feature_names_in_)
            break

    if feature_names is None:
        raise ValueError("No component with feature_names_in_ found in model tuple.")

    if len(regressors) == 2:
        re_match = re.search(r'rf_weight_(\d+)', model_name)
        if re_match:
            rf_weight = int(re_match.group(1)) / 100.0
        else:
            rf_weight = 0.6
        gbr, rf = regressors
        importances = (1 - rf_weight) * gbr.feature_importances_ + rf_weight * rf.feature_importances_  # type: ignore
        model_name = "Ensemble (GBR + RF)"
    elif len(regressors) == 1:
        reg = regressors[0]
        importances = reg.feature_importances_  # type: ignore
        model_name = reg.__class__.__name__
    else:
        raise ValueError("No regressor found in joblib.")

    return importances, model_name, feature_names


def plot_feature_importances_and_save(importances: np.ndarray, feature_names: list[str], model_name: str, output_dir: Path):
    plt.figure(figsize=(8, 6))
    sorted_idx = np.argsort(importances)
    sorted_features = [feature_names[i] for i in sorted_idx]

    base_colors = ['#d9d9d9'] * len(importances)
    base_colors[-1] = '#377eb8'
    base_colors[-2] = '#4daf4a'

    plt.barh(sorted_features, importances[sorted_idx], color=base_colors)
    plt.xlabel('Importance', fontsize=14)
    plt.grid(axis='x', linestyle=':', alpha=0.7)
    plt.xlim(0, max(importances) * 1.15)
    plt.tight_layout()

    output_path = output_dir / f"{model_name}.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
