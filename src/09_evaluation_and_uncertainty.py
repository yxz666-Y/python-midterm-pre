"""第九步：误差、阈值预警与寿命外推敏感性。

先运行01、06、07、08。本步骤读取统一预测，不重训或选择两种主要模型。
80%是相对首循环容量的研究阈值，不是设备安全或厂商更换标准。
"""
from pathlib import Path
import hashlib
import json
import platform

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RATIO = .80
# 预先固定观察长度；每次仅用起点及以前的数据拟合，不以外推效果选窗口。
ORIGIN_FRACTIONS = (.30, .50, .70)
# 独立的探索性滚动预警方案：结果产生前固定，不根据本轮回测选参。
ROLLING_START = 30
ROLLING_HORIZON = 5
ROLLING_WINDOW = 20
ROLLING_NAMES = {'persistence': '容量保持基线', 'linear_recent': '最近20次线性趋势'}
NAMES = {'persistence': '上一循环基线', 'linear_ols': '普通线性回归',
         'random_forest': '随机森林回归'}


def first_crossing(cycles, capacities, threshold):
    """首次实测容量<=阈值；未发生时返回NaN，不把记录末尾当寿命。"""
    cycles, capacities = np.asarray(cycles), np.asarray(capacities)
    crossed = cycles[capacities <= threshold]
    return float(crossed[0]) if len(crossed) else np.nan


def confusion(actual, predicted):
    actual, predicted = np.asarray(actual, bool), np.asarray(predicted, bool)
    tp, fp = int((actual & predicted).sum()), int((~actual & predicted).sum())
    fn, tn = int((actual & ~predicted).sum()), int((~actual & ~predicted).sum())
    return {'TP': tp, 'FP': fp, 'FN': fn, 'TN': tn,
            'precision': tp / (tp + fp) if tp + fp else np.nan,
            'recall': tp / (tp + fn) if tp + fn else np.nan,
            'false_positive_rate': fp / (fp + tn) if fp + tn else np.nan}


def validate_inputs(raw, predictions):
    raw_required = {'battery_id', 'cycle', 'capacity_Ah'}
    pred_required = {'battery_id', 'cycle', 'split', 'model', 'actual_Ah', 'predicted_Ah'}
    if not raw_required.issubset(raw.columns) or not pred_required.issubset(predictions.columns):
        raise ValueError('输入缺少必需字段')
    if raw.empty or predictions.empty or raw[list(raw_required)].isna().any().any() or predictions[list(pred_required)].isna().any().any():
        raise ValueError('必需字段为空或输入没有记录')
    if not np.isfinite(raw[['cycle', 'capacity_Ah']]).all().all() or (raw.capacity_Ah <= 0).any():
        raise ValueError('清洗数据容量或循环存在非法值')
    if raw.duplicated(['battery_id', 'cycle']).any():
        raise ValueError('清洗结果存在重复电池循环')
    if predictions.duplicated(['battery_id', 'cycle', 'split', 'model']).any():
        raise ValueError('预测结果存在重复记录')
    if not np.isfinite(predictions[['actual_Ah', 'predicted_Ah']]).all().all():
        raise ValueError('预测结果包含非有限数值')
    if set(predictions.model) != set(NAMES):
        raise ValueError('应有当前建模步骤的三种模型')
    if set(raw.battery_id) != set(predictions.battery_id):
        raise ValueError('原始数据与预测结果电池不一致')
    expected_groups = {(battery, model) for battery in raw.battery_id.unique() for model in NAMES}
    actual_groups = set(predictions[['battery_id', 'model']].itertuples(index=False, name=None))
    if actual_groups != expected_groups:
        raise ValueError('每块电池必须具有全部三种模型的预测')
    if set(predictions.split) != {'validation', 'test'}:
        raise ValueError('预测结果只能包含validation和test区间')
    truth = raw.set_index(['battery_id', 'cycle']).capacity_Ah
    for (battery, model), g in predictions.groupby(['battery_id', 'model']):
        source = raw[raw.battery_id == battery].sort_values('cycle')
        n = len(source)
        if not np.array_equal(source.cycle, np.arange(1, n + 1)):
            raise ValueError('循环必须从1开始连续')
        for split, start, end in [('validation', int(.6*n)+1, int(.8*n)),
                                  ('test', int(.8*n)+1, n)]:
            part = g[g.split == split].sort_values('cycle')
            if not np.array_equal(part.cycle, np.arange(start, end+1)):
                raise ValueError(f'{battery}/{model}/{split}目标循环不完整')
        expected = [truth.loc[(battery, cycle)] for cycle in g.cycle]
        if not np.allclose(g.actual_Ah, expected, rtol=0, atol=1e-10):
            raise ValueError('当前建模步骤实测容量与清洗数据不一致，请重建结果')


def error_summary(test):
    rows = []
    for (battery, model), g in test.groupby(['battery_id', 'model']):
        error = (g.predicted_Ah - g.actual_Ah).to_numpy()
        rows.append({'battery_id': battery, 'model': model, 'n': len(g),
                     'MAE_Ah': np.abs(error).mean(), 'RMSE_Ah': np.sqrt((error**2).mean()),
                     'bias_Ah': error.mean(), 'overestimate_fraction': (error > 1e-12).mean(),
                     'max_overestimate_Ah': np.maximum(error, 0).max(),
                     'p90_absolute_error_Ah': np.quantile(np.abs(error), .9)})
    return pd.DataFrame(rows)


def alert_analysis(raw, test, ratio=RATIO):
    coverage, scores = [], []
    for battery, g in raw.groupby('battery_id'):
        g = g.sort_values('cycle')
        threshold = float(g.capacity_Ah.iloc[0]*ratio)
        cross = first_crossing(g.cycle, g.capacity_Ah, threshold)
        start = int(len(g)*.8)+1
        status = ('not_observed' if np.isnan(cross) else
                  'before_test' if cross < start else 'in_test')
        coverage.append({'battery_id': battery, 'threshold_ratio': ratio,
                         'threshold_Ah': threshold, 'observed_first_cross_cycle': cross,
                         'observation_end': int(g.cycle.max()), 'test_start': start,
                         'first_cross_status': status})
        for model, part in test[test.battery_id == battery].groupby('model'):
            part = part.sort_values('cycle')
            row = {'battery_id': battery, 'model': model, 'n': len(part),
                   'threshold_Ah': threshold,
                   **confusion(part.actual_Ah <= threshold, part.predicted_Ah <= threshold)}
            # 单步预测只覆盖下一次。更早循环的误报不能冒充首次跨越预警。
            crossing_row = part[part.cycle == cross] if status == 'in_test' else part.iloc[:0]
            detected = bool(len(crossing_row) and (crossing_row.predicted_Ah <= threshold).iloc[0])
            event = cross if detected else np.nan
            event_status = ('not_applicable' if status != 'in_test' else
                            'not_scored' if crossing_row.empty else
                            'detected' if detected else 'missed')
            row.update({'first_cross_status': status, 'first_event_alert_target_cycle': event,
                        'event_lead_cycles': 1. if detected else np.nan,
                        'event_evaluation_status': event_status})
            scores.append(row)
    return pd.DataFrame(coverage), pd.DataFrame(scores)


def rolling_forecasts(history, horizon=ROLLING_HORIZON, window=ROLLING_WINDOW):
    """只接收截至起点的实测历史；未来容量不能进入此函数。"""
    if horizon < 1 or window < 2 or len(history) < window:
        raise ValueError('预测范围须为正，且历史长度必须覆盖至少两个点的拟合窗口')
    history = history.sort_values('cycle')
    recent = history.tail(window)
    x = recent.cycle.to_numpy(float)
    y = recent.capacity_Ah.to_numpy(float)
    beta = np.linalg.lstsq(np.column_stack([np.ones(len(x)), x]), y, rcond=None)[0]
    targets = np.arange(int(history.cycle.iloc[-1])+1, int(history.cycle.iloc[-1])+horizon+1)
    return {'persistence': np.repeat(history.capacity_Ah.iloc[-1], horizon),
            'linear_recent': np.column_stack([np.ones(horizon), targets]) @ beta}


def rolling_backtest(raw, min_history=ROLLING_START, horizon=ROLLING_HORIZON,
                     window=ROLLING_WINDOW, ratio=RATIO):
    """预测未来H次内是否首次跨阈值；已有跨越后停止，标签不参与拟合。

    临近记录末端，不足H次且尚未观察到跨越时，标签未知，不当成负样本。
    相邻起点窗口重叠，输出为探索性时间回测，不是独立样本泛化评估。
    """
    if min_history < window or window < 2 or horizon < 1 or not 0 < ratio < 1:
        raise ValueError('滚动回测配置不合法')
    rows, events = [], []
    for battery, source in raw.groupby('battery_id'):
        source = source.sort_values('cycle').reset_index(drop=True)
        threshold = float(source.capacity_Ah.iloc[0]*ratio)
        cross = first_crossing(source.cycle, source.capacity_Ah, threshold)
        battery_rows = []
        for count in range(min_history, len(source)):
            history = source.iloc[:count]
            if (history.capacity_Ah <= threshold).any():
                break  # 此时已知道发生过首次跨越，不再将回升当成新的首次事件。
            origin = int(history.cycle.iloc[-1])
            forecasts = rolling_forecasts(history, horizon, window)
            future = source.iloc[count:count+horizon]
            observed_cross = first_crossing(future.cycle, future.capacity_Ah, threshold)
            known = np.isfinite(observed_cross) or len(future) == horizon
            actual_event = bool(np.isfinite(observed_cross)) if known else np.nan
            for model, values in forecasts.items():
                hit = np.flatnonzero(values <= threshold)
                predicted_cycle = origin+int(hit[0])+1 if len(hit) else np.nan
                battery_rows.append({'battery_id': battery, 'model': model,
                                     'origin_cycle': origin, 'horizon_cycles': horizon,
                                     'threshold_Ah': threshold, 'available_future_cycles': len(future),
                                     'label_status': 'known' if known else 'right_censored',
                                     'actual_event_within_horizon': actual_event,
                                     'predicted_alert': bool(len(hit)),
                                     'predicted_first_cross_cycle': predicted_cycle,
                                     'forecast_min_Ah': float(np.min(values)),
                                     'observed_cross_within_horizon': observed_cross})
        rows.extend(battery_rows)
        for model in ROLLING_NAMES:
            records = [r for r in battery_rows if r['model'] == model]
            # 有效提前量要求真实事件位于该次预先规定的H步预测范围内。
            hits = [r for r in records if r['label_status'] == 'known'
                    and r['actual_event_within_horizon'] and r['predicted_alert']]
            observed = bool(np.isfinite(cross))
            eligible = observed and cross > min_history and bool(records)
            status = ('not_observed' if not observed else 'before_or_at_start' if not eligible
                      else 'detected' if hits else 'missed')
            first = hits[0] if hits else None
            events.append({'battery_id': battery, 'model': model,
                           'observed_first_cross_cycle': cross, 'event_status': status,
                           'first_valid_alert_origin': first['origin_cycle'] if first else np.nan,
                           'event_lead_cycles': cross-first['origin_cycle'] if first else np.nan,
                           'false_alert_origins': sum(r['predicted_alert'] and
                               not r['actual_event_within_horizon'] for r in records
                               if r['label_status'] == 'known')})
    trace = pd.DataFrame(rows, columns=['battery_id', 'model', 'origin_cycle', 'horizon_cycles',
        'threshold_Ah', 'available_future_cycles', 'label_status', 'actual_event_within_horizon',
        'predicted_alert', 'predicted_first_cross_cycle', 'forecast_min_Ah',
        'observed_cross_within_horizon'])
    metrics = []
    for event in events:
        group = trace[(trace.battery_id == event['battery_id']) & (trace.model == event['model'])]
        known = group[group.label_status == 'known']
        metrics.append({'battery_id': event['battery_id'], 'model': event['model'],
                        'n_origins': len(group), 'n_scored': len(known),
                        'n_unknown': len(group)-len(known),
                        **confusion(known.actual_event_within_horizon.to_numpy(bool),
                                    known.predicted_alert.to_numpy(bool))})
    return trace, pd.DataFrame(metrics), pd.DataFrame(events)


def plot_rolling(metrics, dest):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout='constrained')
    for ax, metric, title in zip(axes, ['recall', 'false_positive_rate'],
                               ['未来5次内事件窗口召回率', '未来5次内无事件窗口误报率']):
        metrics.pivot(index='battery_id', columns='model', values=metric)[list(ROLLING_NAMES)].rename(
            columns=ROLLING_NAMES).plot.bar(ax=ax, rot=0, color=['#176B87', '#D3662E'])
        ax.set(title=title, xlabel='电池编号', ylabel='比例', ylim=(0, 1.15))
        ax.legend(fontsize=8)
        ax.grid(axis='y', alpha=.2)
    fig.suptitle('新增滚动回测：第30次起评估，重叠窗口仅作探索性描述')
    fig.savefig(dest/'04_rolling_warning.png', dpi=180)
    plt.close(fig)


def fit_extrapolation(history, threshold):
    """固定起点线性外推；只有history参与拟合，斜率非负时不强造寿命。"""
    x = history.cycle.to_numpy(float)
    y = history.capacity_Ah.to_numpy(float)
    intercept, slope = np.linalg.lstsq(np.column_stack([np.ones(len(x)), x]), y, rcond=None)[0]
    origin = int(x[-1])
    if np.any(y <= threshold):
        status, crossing = 'threshold_already_observed', np.nan
    elif slope >= -1e-12:
        status, crossing = 'non_decreasing_fit', np.nan
    else:
        crossing = float((threshold-intercept)/slope)
        status = 'future_crossing' if crossing > origin else 'fit_crossing_not_future'
        if status != 'future_crossing':
            crossing = np.nan
    return {'intercept_Ah': float(intercept), 'slope_Ah_per_cycle': float(slope),
            'fit_status': status, 'predicted_cross_cycle_continuous': crossing,
            'predicted_remaining_cycles': crossing-origin if np.isfinite(crossing) else np.nan}


def lifetime_sensitivity(raw):
    rows = []
    for battery, g in raw.groupby('battery_id'):
        g = g.sort_values('cycle')
        threshold = float(g.capacity_Ah.iloc[0]*RATIO)
        # 后续实测只用于回顾评价，不送入历史拟合。
        observed = first_crossing(g.cycle, g.capacity_Ah, threshold)
        for fraction in ORIGIN_FRACTIONS:
            count = int(len(g)*fraction)
            history = g.iloc[:count]
            fit = fit_extrapolation(history, threshold)
            predicted = fit['predicted_cross_cycle_continuous']
            comparable = np.isfinite(observed) and observed > count and np.isfinite(predicted)
            rows.append({'battery_id': battery, 'history_fraction': fraction, 'origin_cycle': count,
                         'threshold_Ah': threshold, **fit,
                         'observed_first_cross_cycle': observed,
                         'observed_event_after_origin': bool(np.isfinite(observed) and observed > count),
                         'right_censored': bool(np.isnan(observed)),
                         'crossing_error_cycles': predicted-observed if comparable else np.nan,
                         'beyond_observation_end': bool(np.isfinite(predicted) and predicted > len(g))})
    return pd.DataFrame(rows)


def configure_font():
    available = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((f for f in ['Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC',
                              'Arial Unicode MS'] if f in available), 'DejaVu Sans')
    plt.rcParams.update({'font.family': chosen, 'axes.unicode_minus': False, 'font.size': 10})
    return chosen


def plots(test, errors, lifetime, dest):
    colors = ['#176B87', '#D3662E', '#647D32']
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout='constrained')
    for ax, value, title in zip(axes, ['bias_Ah', 'max_overestimate_Ah'],
                                ['平均误差（预测−实测）', '最大容量高估误差']):
        errors.pivot(index='battery_id', columns='model', values=value)[list(NAMES)].rename(
            columns=NAMES).plot.bar(ax=ax, rot=0, color=colors)
        ax.axhline(0, color='black', lw=.8)
        ax.set(title=title, xlabel='电池编号', ylabel='误差（Ah）')
        ax.legend(fontsize=8)
    fig.suptitle('测试误差的方向与高估风险（描述性分析）')
    fig.savefig(dest/'01_error_risk.png', dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    for ax, (battery, g) in zip(axes.flat, test.groupby('battery_id')):
        for (model, name), color in zip(NAMES.items(), colors):
            part = g[g.model == model].sort_values('cycle')
            ax.plot(part.cycle, part.predicted_Ah-part.actual_Ah, label=name, color=color)
        ax.axhline(0, color='black', lw=.8)
        ax.set(title=battery, xlabel='目标循环次数', ylabel='预测−实测（Ah）')
        ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('单步预测误差随循环变化；正值表示容量高估')
    fig.savefig(dest/'02_error_by_cycle.png', dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    for ax, (battery, g) in zip(axes.flat, lifetime.groupby('battery_id')):
        valid = g[g.fit_status == 'future_crossing']
        ax.plot(valid.origin_cycle, valid.predicted_cross_cycle_continuous, 'o-',
                label='线性趋势估计到达循环', color=colors[0])
        observed = g.observed_first_cross_cycle.iloc[0]
        if np.isfinite(observed):
            ax.axhline(observed, color=colors[1], ls='--', label='首次实测低于阈值')
        ax.set(title=battery, xlabel='预测起点（仅使用此前数据）', ylabel='阈值到达循环')
        ax.set_xticks(g.origin_cycle)
        excluded = g[g.fit_status == 'threshold_already_observed'].origin_cycle.tolist()
        if excluded:
            ax.set_title(f'{battery}\n起点{excluded}已跨阈值，不再外推', fontsize=10)
        ax.grid(alpha=.2)
        ax.legend(fontsize=8)
    fig.suptitle('80%研究阈值：历史长度敏感性（不是置信区间）')
    fig.savefig(dest/'03_lifetime_sensitivity.png', dpi=180)
    plt.close(fig)


def main():
    inputs = {'clean': ROOT/'results/step01/battery_clean.csv',
              'predictions': ROOT/'results/step08/predictions.csv'}
    raw, pred = (pd.read_csv(inputs[key]) for key in ['clean', 'predictions'])
    validate_inputs(raw, pred)
    test = pred[pred.split == 'test'].copy()
    test['error_Ah'] = test.predicted_Ah-test.actual_Ah
    errors = error_summary(test)
    coverage, alerts = alert_analysis(raw, test)
    lifetime = lifetime_sensitivity(raw)
    rolling_trace, rolling_metrics, rolling_events = rolling_backtest(raw)
    out, fig = ROOT/'results/step09', ROOT/'figures/step09'
    out.mkdir(parents=True, exist_ok=True)
    fig.mkdir(parents=True, exist_ok=True)
    for name, table in {'error_summary': errors, 'test_errors': test, 'threshold_coverage': coverage,
                        'alert_metrics': alerts, 'lifetime_sensitivity': lifetime,
                        'rolling_alerts': rolling_trace, 'rolling_metrics': rolling_metrics,
                        'rolling_events': rolling_events}.items():
        table.to_csv(out/f'{name}.csv', index=False, encoding='utf-8-sig')
    font = configure_font()
    plots(test, errors, lifetime, fig)
    plot_rolling(rolling_metrics, fig)
    metadata = {'threshold_ratio': RATIO, 'threshold_reference': 'first observed capacity per battery',
                'origins': list(ORIGIN_FRACTIONS), 'origin_rule': 'floor(fraction * observed length)',
                'event_definition': 'first measured capacity <= threshold, no sustained-crossing rule',
                'alert_mode': 'one-step; only correctly predicted first-crossing target gives lead=1',
                'rolling_warning': {'start_cycle': ROLLING_START, 'horizon_cycles': ROLLING_HORIZON,
                                    'fit_window': ROLLING_WINDOW, 'models': list(ROLLING_NAMES),
                                    'stopping': 'after first observed crossing',
                                    'unknown_label': 'incomplete horizon without observed crossing',
                                    'event_matching': 'actual first crossing within fixed forecast horizon',
                                    'parameters': 'fixed before running this exploratory backtest'},
                'extrapolation_mode': 'linear capacity trend fitted on prefix only; frozen at origin',
                'limitations': ['retrospective origins depend on available record lengths',
                                'sensitivity spread is not a confidence or prediction interval',
                                'no new battery or variable-temperature validation',
                                'test results are descriptive, not further model selection',
                                'rolling windows overlap and share the same four already examined batteries',
                                'rolling event detection is horizon-based, not accurate crossing-date prediction'],
                'inputs_sha256': {key: hashlib.sha256(path.read_bytes()).hexdigest()
                                  for key, path in inputs.items()},
                'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'versions': {'python': platform.python_version(), 'numpy': np.__version__,
                             'pandas': pd.__version__, 'matplotlib': matplotlib.__version__},
                'plot_font': font}
    (out/'experiment.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Threshold coverage:')
    print(coverage.to_string(index=False))
    print('\nLifetime sensitivity:')
    print(lifetime[['battery_id', 'origin_cycle', 'fit_status',
                    'predicted_cross_cycle_continuous', 'observed_first_cross_cycle',
                    'crossing_error_cycles']].round(3).to_string(index=False))
    print('\nRolling warning events:')
    print(rolling_events.to_string(index=False))


if __name__ == '__main__':
    main()
