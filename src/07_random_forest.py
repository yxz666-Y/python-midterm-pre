"""建模B：相同输入与单步目标的随机森林回归，仅验证段选参。"""
from pathlib import Path
import hashlib
import json
import joblib
import sklearn
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from comparison_common import ROOT, FEATURES, load_features, prediction_frame, score, write_outputs

SEED = 25121619
GRID = [{'max_depth': depth, 'min_samples_leaf': leaf}
        for depth in [2, 4, None] for leaf in [3, 8]]


def make_forest(params):
    return RandomForestRegressor(n_estimators=300, bootstrap=True, max_features=1.0,
                                 random_state=SEED, n_jobs=1, **params)


def select_parameters(train, validation):
    rows = []
    for order, params in enumerate(GRID):
        model = make_forest(params).fit(train[FEATURES], train.capacity_Ah)
        predicted = model.predict(validation[FEATURES])
        rows.append({'candidate_order': order, **params,
                     **score(validation.capacity_Ah, predicted)})
    best = min(range(len(rows)), key=lambda i: (rows[i]['RMSE_Ah'], i))
    return GRID[best].copy(), rows


def main():
    data = load_features()
    out = ROOT/'results/step07'; out.mkdir(parents=True, exist_ok=True)
    predictions, searches, metadata, importance = [], [], {}, []
    for battery, g in data.groupby('battery_id'):
        train, validation = g[g.split == 'train'], g[g.split == 'validation']
        params, search = select_parameters(train, validation)
        searches.extend({'battery_id': battery, **row} for row in search)
        fitted = make_forest(params).fit(g[g.split != 'test'][FEATURES], g[g.split != 'test'].capacity_Ah)
        joblib.dump(fitted, out/f'{battery}_forest.joblib', compress=3)
        fit = g[g.split != 'test']
        metadata[battery] = {'selected_parameters': params,
                             'fit_first_target': int(fit.cycle.min()),
                             'fit_last_target': int(fit.cycle.max()), 'fit_n': len(fit),
                             'fit_capacity_min_Ah': float(fit.capacity_Ah.min()),
                             'fit_capacity_max_Ah': float(fit.capacity_Ah.max()),
                             'observed_max_tree_depth': max(t.get_depth() for t in fitted.estimators_)}
        importance.extend({'battery_id': battery, 'feature': name, 'impurity_importance': float(value)}
                          for name, value in zip(FEATURES, fitted.feature_importances_))
        for split in ['validation', 'test']:
            part = g[g.split == split]
            estimator = make_forest(params).fit(train[FEATURES], train.capacity_Ah) if split == 'validation' else fitted
            predictions.append(prediction_frame(part, 'random_forest', estimator.predict(part[FEATURES])))
    pd.DataFrame(searches).to_csv(out/'validation_search.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(importance).to_csv(out/'feature_importance.csv', index=False, encoding='utf-8-sig')
    (out/'forest_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    metrics = write_outputs('step07', predictions, {
        'algorithm': 'RandomForestRegressor predicting absolute capacity',
        'candidate_grid': GRID, 'selection': 'per-battery validation RMSE minimum; first candidate breaks exact ties',
        'n_estimators': 300, 'random_state': SEED, 'bootstrap': True, 'max_features': 1.0, 'n_jobs': 1,
        'sklearn_version': sklearn.__version__, 'joblib_version': joblib.__version__,
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    print(metrics.to_string(index=False))


if __name__ == '__main__': main()
