"""第三步：历史特征与下一循环容量预测。
先运行01，再运行本文件。预测cycle=t时只使用t之前已测得的容量。
每块电池分别建模；按原始循环数的60%/20%/20%划分，不随机打乱。
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
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


def main():
    raw = pd.read_csv(ROOT/'results/step01/battery_clean.csv')
    data = make_features(raw)
    out = ROOT/'results/step03'
    out.mkdir(parents=True, exist_ok=True)
    data.to_csv(out/'features.csv', index=False, encoding='utf-8-sig')
    predictions, metrics = [], []
    for battery, g in data.groupby('battery_id'):
        for split in ['validation', 'test']:
            segment = g[g.split == split]
            train = g[g.split == 'train'] if split == 'validation' else g[g.split != 'test']
            model_predictions = {
                'persistence': segment.lag1_Ah.to_numpy(),
                'linear_cycle': linear_predict(train, segment),
            }
            for model, pred in model_predictions.items():
                metrics.append({'battery_id': battery, 'split': split, 'model': model,
                                'n': len(segment), **score(segment.capacity_Ah, pred)})
                predictions.append(pd.DataFrame({'battery_id': battery, 'cycle': segment.cycle,
                    'split': split, 'model': model, 'actual_Ah': segment.capacity_Ah,
                    'predicted_Ah': pred}))
    pd.DataFrame(metrics).to_csv(out/'metrics.csv', index=False, encoding='utf-8-sig')
    pd.concat(predictions).to_csv(out/'predictions.csv', index=False, encoding='utf-8-sig')
    print(pd.DataFrame(metrics).to_string(index=False))


if __name__ == '__main__':
    main()
