"""普通线性回归与随机森林的独立特征提取及统一评估口径。"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ['cycle', 'lag1_Ah', 'mean5_Ah', 'slope5_Ah_per_cycle']
INPUT = ROOT/'results/step01/battery_clean.csv'


def make_features(raw):
    """预测t时容量窗口最多到t−1，前5次仅作历史，不填充未来值。"""
    frames = []
    for battery, g in raw.groupby('battery_id'):
        g = g.sort_values('cycle').copy()
        n = len(g)
        if not np.array_equal(g.cycle.to_numpy(), np.arange(1, n+1)):
            raise ValueError('循环必须从1开始且连续，请先完成清洗')
        history = g.capacity_Ah.shift(1)
        g['lag1_Ah'] = history
        g['mean5_Ah'] = history.rolling(5).mean()
        g['slope5_Ah_per_cycle'] = history.rolling(5).apply(
            lambda values: np.dot(values, np.arange(5)-2)/10, raw=True)
        train_end, val_end = int(n*.6), int(n*.8)
        g['split'] = np.where(g.cycle <= train_end, 'train',
                              np.where(g.cycle <= val_end, 'validation', 'test'))
        frames.append(g.dropna(subset=FEATURES))
    return pd.concat(frames, ignore_index=True)


def load_features():
    return make_features(pd.read_csv(INPUT))


def score(actual, predicted):
    error = np.asarray(predicted)-np.asarray(actual)
    return {'MAE_Ah': float(np.mean(abs(error))),
            'RMSE_Ah': float(np.sqrt(np.mean(error**2))),
            'bias_Ah': float(np.mean(error)),
            'max_abs_error_Ah': float(np.max(abs(error)))}


def prediction_frame(part, model, predicted):
    return pd.DataFrame({'battery_id': part.battery_id, 'cycle': part.cycle,
                         'split': part.split, 'model': model,
                         'actual_Ah': part.capacity_Ah, 'predicted_Ah': predicted})


def write_outputs(stage, predictions, metadata):
    out = ROOT/f'results/{stage}'
    out.mkdir(parents=True, exist_ok=True)
    predictions = pd.concat(predictions, ignore_index=True)
    rows = []
    for (battery, split, model), g in predictions.groupby(['battery_id', 'split', 'model']):
        rows.append({'battery_id': battery, 'split': split, 'model': model, 'n': len(g),
                     **score(g.actual_Ah, g.predicted_Ah)})
    metrics = pd.DataFrame(rows)
    predictions.to_csv(out/'predictions.csv', index=False, encoding='utf-8-sig')
    metrics.to_csv(out/'metrics.csv', index=False, encoding='utf-8-sig')
    metadata.update({'target': 'capacity_Ah at cycle t using history through t-1',
                     'features': FEATURES, 'history_window': 5,
                     'split': 'per battery floor(0.6*n), floor(0.8*n), rest test',
                     'final_fit': 'train+validation; fixed estimator throughout test',
                     'test_mode': 'rolling one-step; actual preceding history available',
                     'input_sha256': hashlib.sha256(INPUT.read_bytes()).hexdigest(),
                     'feature_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                     'numpy_version': np.__version__, 'pandas_version': pd.__version__})
    (out/'experiment.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    return metrics
