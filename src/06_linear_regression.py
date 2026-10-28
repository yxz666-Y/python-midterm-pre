"""建模A：四个相同历史特征的普通最小二乘线性回归，无正则化。"""
import hashlib
import json
import numpy as np
from comparison_common import ROOT, FEATURES, load_features, prediction_frame, write_outputs


def fit_linear(train):
    x = train[FEATURES].to_numpy(dtype=float)
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale = np.where(scale == 0, 1., scale)
    design = np.column_stack([np.ones(len(x)), (x-mean)/scale])
    beta, _, rank, singular = np.linalg.lstsq(design, train.capacity_Ah.to_numpy(), rcond=None)
    raw_beta = beta[1:]/scale
    return {'features': FEATURES, 'mean': mean.tolist(), 'scale': scale.tolist(),
            'coefficients_standardized': beta.tolist(),
            'intercept_Ah': float(beta[0]-mean@raw_beta),
            'coefficients_raw': raw_beta.tolist(), 'design_rank': int(rank),
            'condition_number_standardized': float(singular.max()/singular.min()),
            'fit_first_target': int(train.cycle.min()),
            'fit_last_target': int(train.cycle.max()), 'fit_n': len(train)}


def predict_linear(model, target):
    x = (target[model['features']].to_numpy(dtype=float)-model['mean'])/model['scale']
    return np.column_stack([np.ones(len(x)), x])@np.array(model['coefficients_standardized'])


def main():
    data = load_features()
    out = ROOT/'results/step06'; out.mkdir(parents=True, exist_ok=True)
    data.to_csv(out/'features.csv', index=False, encoding='utf-8-sig')
    predictions, models = [], {}
    for battery, g in data.groupby('battery_id'):
        models[battery] = fit_linear(g[g.split != 'test'])
        for split in ['validation', 'test']:
            part = g[g.split == split]
            train = g[g.split == 'train'] if split == 'validation' else g[g.split != 'test']
            predictions.append(prediction_frame(part, 'linear_ols', predict_linear(fit_linear(train), part)))
            predictions.append(prediction_frame(part, 'persistence', part.lag1_Ah.to_numpy()))
    (out/'linear_models.json').write_text(json.dumps(models, ensure_ascii=False, indent=2), encoding='utf-8')
    metrics = write_outputs('step06', predictions, {
        'algorithm': 'ordinary least squares with intercept, four inputs, no regularization',
        'selection': 'no hyperparameters; no test-based tuning',
        'script_sha256': hashlib.sha256(__import__('pathlib').Path(__file__).read_bytes()).hexdigest()})
    print(metrics.to_string(index=False))


if __name__ == '__main__': main()
