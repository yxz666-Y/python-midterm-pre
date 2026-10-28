"""新一轮线性回归与随机森林实验的共同口径，不改动此前模型。"""
from pathlib import Path
import hashlib
import importlib.util
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('step03_features', ROOT/'src/03_features_and_models.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
FEATURES = list(previous.FEATURES)
INPUT = ROOT/'results/step01/battery_clean.csv'


def load_features():
    return previous.make_features(pd.read_csv(INPUT))


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
                     'numpy_version': np.__version__, 'pandas_version': pd.__version__})
    (out/'experiment.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    return metrics
