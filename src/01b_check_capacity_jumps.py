"""补充清洗：检测容量跳变，输出带标记原值和限幅处理对照。
统计离群不等于测量错误，处理版仅供敏感性分析，不覆盖正式清洗数据。
阈值仅用每块电池前60%记录估计，与03的训练边界一致；不是在线早期检测。
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]


def check_jumps(data):
    parts, thresholds = [], []
    for battery, group in data.groupby('battery_id'):
        g = group.sort_values('cycle').copy()
        if g.capacity_Ah.isna().any() or not np.isfinite(g.capacity_Ah).all():
            raise ValueError('请先排查缺失或非有限容量')
        if not np.array_equal(g.cycle, np.arange(1, len(g)+1)):
            raise ValueError('循环必须从1开始且连续')
        delta = g.capacity_Ah.diff()
        end = int(len(g)*.6)
        # 对相邻变化量而非容量本身检测，避免把正常后期低容量当成异常。
        q1, q3 = delta.iloc[1:end].quantile([.25, .75])
        iqr = q3-q1
        if iqr <= 1e-12:
            raise ValueError('训练变化量IQR退化为0，须人工审查，不能自动限幅')
        inner_lo, inner_hi = q1-1.5*iqr, q3+1.5*iqr
        outer_lo, outer_hi = q1-3*iqr, q3+3*iqr
        g['delta_Ah'] = delta
        g['review_flag'] = (delta < inner_lo) | (delta > inner_hi)
        g['extreme_flag'] = (delta < outer_lo) | (delta > outer_hi)
        g['capacity_treated_Ah'] = g.capacity_Ah
        # 极端点的变化量裁剪到3IQR边界，再加回上一循环原始容量。
        # 使用原始前值而不是递归累加，避免一次修正导致所有后续容量平移。
        replacement = g.capacity_Ah.shift(1) + delta.clip(outer_lo, outer_hi)
        g.loc[g.extreme_flag, 'capacity_treated_Ah'] = replacement[g.extreme_flag]
        g['adjustment_Ah'] = g.capacity_treated_Ah-g.capacity_Ah
        parts.append(g)
        thresholds.append({'battery_id': battery, 'threshold_fit_end_cycle': end,
                           'q1_delta_Ah': q1, 'q3_delta_Ah': q3, 'iqr_Ah': iqr,
                           'review_lower_Ah': inner_lo, 'review_upper_Ah': inner_hi,
                           'extreme_lower_Ah': outer_lo, 'extreme_upper_Ah': outer_hi,
                           'review_count': int(g.review_flag.sum()),
                           'extreme_count': int(g.extreme_flag.sum()),
                           'max_abs_adjustment_Ah': float(g.adjustment_Ah.abs().max())})
    return pd.concat(parts, ignore_index=True), pd.DataFrame(thresholds)


def main():
    data = pd.read_csv(ROOT/'results/step01/battery_clean.csv')
    result, summary = check_jumps(data)
    out = ROOT/'results/step01b'
    figdir = ROOT/'figures/step01b'
    out.mkdir(parents=True, exist_ok=True)
    figdir.mkdir(parents=True, exist_ok=True)
    result.to_csv(out/'all_rows_with_flags.csv', index=False, encoding='utf-8-sig')
    result[result.review_flag].to_csv(out/'review_candidates.csv', index=False, encoding='utf-8-sig')
    result[result.extreme_flag].to_csv(out/'treated_points.csv', index=False, encoding='utf-8-sig')
    summary.to_csv(out/'thresholds_and_counts.csv', index=False, encoding='utf-8-sig')
    sensitivity = result[list(data.columns)].copy()
    sensitivity['capacity_Ah'] = result.capacity_treated_Ah
    sensitivity.to_csv(out/'battery_treated_sensitivity_only.csv', index=False, encoding='utf-8-sig')
    trends = []
    for battery, g in result.groupby('battery_id'):
        trends.append({'battery_id': battery,
            'original_first_Ah': g.capacity_Ah.iloc[0],
            'treated_first_Ah': g.capacity_treated_Ah.iloc[0],
            'original_last_Ah': g.capacity_Ah.iloc[-1],
            'treated_last_Ah': g.capacity_treated_Ah.iloc[-1],
            'original_linear_slope': np.polyfit(g.cycle, g.capacity_Ah, 1)[0],
            'treated_linear_slope': np.polyfit(g.cycle, g.capacity_treated_Ah, 1)[0]})
    pd.DataFrame(trends).to_csv(out/'trend_sensitivity.csv', index=False, encoding='utf-8-sig')
    plt.rcParams.update({'font.family': 'Arial Unicode MS', 'axes.unicode_minus': False})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout='constrained')
    for ax, (battery, g) in zip(axes.flat, result.groupby('battery_id')):
        ax.plot(g.cycle, g.capacity_Ah, color='#176B87', label='原始容量', lw=1.5)
        ax.plot(g.cycle, g.capacity_treated_Ah, color='#D3662E', label='极端跳变限幅对照', lw=1, alpha=.8)
        flagged = g[g.extreme_flag]
        ax.scatter(flagged.cycle, flagged.capacity_Ah, s=22, color='#8A4E9C', label='3IQR极端跳变原值', zorder=3)
        ax.set(title=battery, xlabel='循环次数', ylabel='容量（Ah）')
        ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle('统计跳变与限幅对照：标记不代表已证实的测量错误')
    fig.savefig(figdir/'jump_treatment_comparison.png', dpi=180)
    plt.close(fig)
    print(summary.to_string(index=False))
    print(f'缺失值：{int(data.isna().sum().sum())}；待核查：{result.review_flag.sum()}；限幅对照：{result.extreme_flag.sum()}')


if __name__ == '__main__':
    main()
