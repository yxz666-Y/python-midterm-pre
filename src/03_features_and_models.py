"""第三步：历史特征与下一循环容量预测。
先运行01，再运行本文件。预测cycle=t时只使用t之前已测得的容量。
每块电池分别建模；按原始循环数的60%/20%/20%划分，不随机打乱。
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ALPHAS = [0.01, 0.1, 1.0, 10.0, 100.0]
FEATURES = ['cycle', 'lag1_Ah', 'mean5_Ah', 'slope5_Ah_per_cycle']


def make_features(raw):
    """窗口先shift(1)再rolling，禁止把预测目标放进特征。"""
    frames = []
    for battery, g in raw.groupby('battery_id'):
        g = g.sort_values('cycle').copy()
        n = len(g)
        if not np.array_equal(g.cycle.to_numpy(), np.arange(1, n+1)):
            raise ValueError('循环必须从1开始且连续，请先完成清洗')
        history = g.capacity_Ah.shift(1)
        g['lag1_Ah'] = history
        g['mean5_Ah'] = history.rolling(5).mean()
        # 5个点对[0,1,2,3,4]作最小二乘，其中心化横坐标平方和为10。
        g['slope5_Ah_per_cycle'] = history.rolling(5).apply(
            lambda values: np.dot(values, np.arange(5)-2)/10, raw=True)
        train_end, val_end = int(n*.6), int(n*.8)
        g['split'] = np.where(g.cycle <= train_end, 'train',
                              np.where(g.cycle <= val_end, 'validation', 'test'))
        # 前5次没有完整历史窗口，明确舍弃；不向前填充未来容量。
        frames.append(g.dropna(subset=FEATURES))
    return pd.concat(frames, ignore_index=True)


def score(y, pred):
    error = np.asarray(pred)-np.asarray(y)
    return {'MAE_Ah': float(np.mean(np.abs(error))),
            'RMSE_Ah': float(np.sqrt(np.mean(error**2)))}


def linear_predict(train, target):
    """最小二乘拟合容量=a+b×循环次数。测试阶段仅在前80%重拟合。"""
    x = np.column_stack([np.ones(len(train)), train.cycle])
    beta = np.linalg.lstsq(x, train.capacity_Ah.to_numpy(), rcond=None)[0]
    return np.column_stack([np.ones(len(target)), target.cycle]) @ beta


def fit_ridge(train, alpha):
    """标准化参数仅来自训练数据；最小化SSE+alpha*系数平方和。
    截距不惩罚。保存均值、尺度、系数，便于复查与复用。
    """
    x = train[FEATURES].to_numpy(dtype=float)
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale = np.where(scale == 0, 1., scale)
    design = np.column_stack([np.ones(len(x)), (x-mean)/scale])
    penalty = np.diag([0.] + [alpha]*len(FEATURES))
    beta = np.linalg.solve(design.T @ design + penalty, design.T @ train.capacity_Ah.to_numpy())
    return {'alpha': alpha, 'features': FEATURES, 'mean': mean.tolist(),
            'scale': scale.tolist(), 'coefficients_standardized': beta.tolist()}


def predict_ridge(model, target):
    x = (target[model['features']].to_numpy()-model['mean'])/model['scale']
    return np.column_stack([np.ones(len(x)), x]) @ model['coefficients_standardized']


def select_alpha(g):
    """仅训练段拟合、验证段选参；测试段不会参与此过程。"""
    train, val = g[g.split == 'train'], g[g.split == 'validation']
    scores = [{'alpha': a, **score(val.capacity_Ah, predict_ridge(fit_ridge(train, a), val))}
              for a in ALPHAS]
    best = min(scores, key=lambda row: row['RMSE_Ah'])['alpha']
    return best, scores


def main():
    raw = pd.read_csv(ROOT/'results/step01/battery_clean.csv')
    data = make_features(raw)
    out = ROOT/'results/step03'
    out.mkdir(parents=True, exist_ok=True)
    data.to_csv(out/'features.csv', index=False, encoding='utf-8-sig')
    predictions, metrics, tuning, models, splits = [], [], [], {}, []
    for battery, g in data.groupby('battery_id'):
        alpha, scores = select_alpha(g)
        tuning.extend({'battery_id': battery, **row} for row in scores)
        for name, part in g.groupby('split'):
            splits.append({'battery_id': battery, 'split': name, 'first_cycle': int(part.cycle.min()),
                           'last_cycle': int(part.cycle.max()), 'n': len(part)})
        models[battery] = fit_ridge(g[g.split != 'test'], alpha)
        for split in ['validation', 'test']:
            segment = g[g.split == split]
            train = g[g.split == 'train'] if split == 'validation' else g[g.split != 'test']
            model_predictions = {
                'persistence': segment.lag1_Ah.to_numpy(),
                'linear_cycle': linear_predict(train, segment),
                'ridge_history': predict_ridge(fit_ridge(train, alpha), segment),
            }
            for model, pred in model_predictions.items():
                metrics.append({'battery_id': battery, 'split': split, 'model': model,
                                'n': len(segment), **score(segment.capacity_Ah, pred)})
                predictions.append(pd.DataFrame({'battery_id': battery, 'cycle': segment.cycle,
                    'split': split, 'model': model, 'actual_Ah': segment.capacity_Ah,
                    'predicted_Ah': pred}))
    pd.DataFrame(metrics).to_csv(out/'metrics.csv', index=False, encoding='utf-8-sig')
    pd.concat(predictions).to_csv(out/'predictions.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(tuning).to_csv(out/'ridge_validation_search.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(splits).to_csv(out/'time_splits.csv', index=False, encoding='utf-8-sig')
    (out/'ridge_models.json').write_text(json.dumps(models, ensure_ascii=False, indent=2), encoding='utf-8')
    print(pd.DataFrame(metrics).to_string(index=False))


if __name__ == '__main__':
    main()
