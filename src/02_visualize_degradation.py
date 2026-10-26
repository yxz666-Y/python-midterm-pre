"""第二步：画退化曲线，在相同观察窗口内比较电池个体差异。
运行：python src/02_visualize_degradation.py
输入来自第一步；不修改原始数据，不拟合预测模型。
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/step02'
FIG = ROOT / 'figures/step02'
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({'font.family': 'Arial Unicode MS', 'axes.unicode_minus': False,
                     'font.size': 12, 'axes.spines.top': False, 'axes.spines.right': False})
COLORS = ['#176B87', '#D3662E', '#647D32', '#8A4E9C']

# 1. 数据录入：读取第一步的清洗结果，按电池和循环排序。
df = pd.read_csv(ROOT / 'results/step01/battery_clean.csv')
df = df.sort_values(['battery_id', 'cycle']).reset_index(drop=True)
assert not df.isna().any().any(), '请先运行第一步并排查缺失值'
assert not df.duplicated(['battery_id', 'cycle']).any(), '存在重复主键'
assert np.isfinite(df[['cycle', 'capacity_Ah', 'ambient_temp_C']]).all().all()
assert (df.capacity_Ah > 0).all()
for _, g in df.groupby('battery_id'):
    assert np.array_equal(g.cycle.to_numpy(), np.arange(1, len(g) + 1))

# 2. 计算相对首循环容量。它消除了初始容量大小的影响，
#    但不是以制造商额定容量定义的 SOH，不直接代表真实剩余寿命。
df['retention_pct'] = df.capacity_Ah / df.groupby('battery_id').capacity_Ah.transform('first') * 100
# 相邻两次容量之差：正值表示局部回升，保留原始测量，不强制单调下降。
df['capacity_change_Ah'] = df.groupby('battery_id').capacity_Ah.diff()
common_end = int(df.groupby('battery_id').cycle.max().min())
common = df[df.cycle <= common_end].copy()

# 3. 全部观测曲线：B0018 只有132次记录，线条在132处结束，不补齐未来。
fig, ax = plt.subplots(figsize=(11, 6), layout='constrained')
for (battery, g), color in zip(df.groupby('battery_id'), COLORS):
    ax.plot(g.cycle, g.capacity_Ah, label=f'{battery}（{len(g)}次）', color=color, lw=1.8)
ax.set(xlabel='放电循环次数', ylabel='放电容量（Ah）', title='全部观测：四块电池的容量退化曲线')
ax.grid(alpha=.2)
ax.legend()
fig.savefig(FIG / '01_capacity_all_cycles.png', dpi=180)
plt.close(fig)

# 4. 公平比较：统一为共同的前132次循环，并比较相对容量保留率。
fig, ax = plt.subplots(figsize=(11, 6), layout='constrained')
for (battery, g), color in zip(common.groupby('battery_id'), COLORS):
    ax.plot(g.cycle, g.retention_pct, label=battery, color=color, lw=1.8)
ax.set(xlabel='放电循环次数', ylabel='相对首循环容量（%）',
       title=f'共同观察窗口：前{common_end}次循环的相对容量')
ax.grid(alpha=.2)
ax.legend()
fig.savefig(FIG / '02_retention_common_window.png', dpi=180)
plt.close(fig)

# 5. 数值差异：首末差是描述性统计，不能当成恒定退化规律向未来外推。
rows = []
for battery, g in common.groupby('battery_id'):
    first, last = g.capacity_Ah.iloc[[0, -1]]
    rows.append({'battery_id': battery, 'comparison_cycle': common_end,
                 'first_capacity_Ah': first, 'end_capacity_Ah': last,
                 'loss_Ah': first-last, 'retention_pct': last/first*100,
                 'loss_pct': (1-last/first)*100,
                 'mean_loss_Ah_per_interval': (first-last)/(common_end-1),
                 'rebound_count': int((g.capacity_change_Ah > 0).sum()),
                 'interval_count': len(g)-1})
summary = pd.DataFrame(rows)
fig, ax = plt.subplots(figsize=(10, 5.5), layout='constrained')
bars = ax.bar(summary.battery_id, summary.loss_pct, color=COLORS, width=.55)
ax.bar_label(bars, fmt='%.2f%%', padding=5)
ax.set(xlabel='电池编号', ylabel='容量下降比例（%）', ylim=(0, summary.loss_pct.max()*1.2),
       title=f'相同窗口比较：第{common_end}次相对第1次的容量下降')
ax.grid(axis='y', alpha=.2)
fig.savefig(FIG / '03_loss_comparison.png', dpi=180)
plt.close(fig)

# 6. 导出可复查的表格和PPT图表数据；所有值均由本次计算得到。
summary.to_csv(OUT / 'common_window_comparison.csv', index=False, encoding='utf-8-sig')
df.to_csv(OUT / 'curve_data.csv', index=False, encoding='utf-8-sig')
payload = {'common_end': common_end, 'rows': len(df), 'summary': summary.round(6).to_dict('records'),
           'batteries': {b: {'cycles': g.cycle.tolist(), 'capacity': g.capacity_Ah.tolist(),
                            'retention': g.retention_pct.round(6).tolist()}
                        for b, g in df.groupby('battery_id')}}
(OUT / 'slides_data.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
print(summary.to_string(index=False))
print(f'已生成3张图。共同窗口：1—{common_end}；保留全部{len(df)}条观测。')
