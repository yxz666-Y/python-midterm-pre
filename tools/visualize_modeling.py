from pathlib import Path
import hashlib
import json
import sys

import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from comparison_common import FEATURES, load_features

OUT = ROOT / 'figures/modeling'
OUT.mkdir(parents=True, exist_ok=True)
BLUE = '#176B87'
ORANGE = '#D3662E'
GREEN = '#647D32'
INK = '#172B3A'
GRAY = '#687783'
LIGHT = '#E9EFF3'
font_file = Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
if font_file.exists():
    font_manager.fontManager.addfont(str(font_file))
available_fonts = {font.name for font in font_manager.fontManager.ttflist}
chinese_font = next((name for name in ['Arial Unicode MS', 'Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC'] if name in available_fonts), None)
if chinese_font is None:
    raise RuntimeError('请先安装可用的中文字体，例如Noto Sans CJK SC。')
plt.rcParams.update({
    'font.family': chinese_font, 'axes.unicode_minus': False,
    'font.size': 15, 'axes.titlesize': 18, 'axes.labelsize': 15,
    'xtick.labelsize': 13, 'ytick.labelsize': 13,
    'axes.spines.top': False, 'axes.spines.right': False,
    'text.color': INK, 'axes.labelcolor': INK, 'figure.facecolor': 'white',
    'savefig.facecolor': 'white',
})


def heading(fig, title, subtitle):
    fig.text(.055, .955, title, ha='left', va='top', fontsize=23, weight='bold')
    fig.text(.055, .895, subtitle, ha='left', va='top', fontsize=13, color=GRAY)


def save(fig, name):
    path = OUT / name
    fig.savefig(path, dpi=220)
    plt.close(fig)
    return str(path.relative_to(ROOT))


def table(ax, rows, headers, bbox, widths=None, size=15):
    result = ax.table(cellText=rows, colLabels=headers, colWidths=widths,
                      cellLoc='center', loc='center', bbox=bbox)
    result.auto_set_font_size(False)
    result.set_fontsize(size)
    for (r, c), cell in result.get_celld().items():
        cell.set_edgecolor('#D7DFE5')
        cell.set_linewidth(.7)
        cell.PAD = .08
        if r == 0:
            cell.set_facecolor(LIGHT)
            cell.set_text_props(weight='bold', color=INK)
        else:
            cell.set_facecolor('white')
    return result


def features_figure(raw, sample):
    fig = plt.figure(figsize=(13, 7.4))
    heading(fig, '四个输入特征从哪里来', '真实示例  B0006电池  用第130至134次容量构造第135次预测的输入')
    ax = fig.add_axes([.08, .20, .47, .58])
    history = raw.query("battery_id == 'B0006' and 130 <= cycle <= 134")
    ax.axvspan(134.5, 135.45, color='#FCF2EB', alpha=.9)
    ax.plot(history.cycle, history.capacity_Ah, '-o', color=BLUE, lw=2, ms=7, label='已知的5次实测容量')
    mean = float(sample.mean5_Ah.iloc[0])
    slope = float(sample.slope5_Ah_per_cycle.iloc[0])
    ax.axhline(mean, color=GREEN, ls='--', lw=1.6, label='前5次均值')
    ax.plot(history.cycle, mean+slope*(history.cycle-132), color=GRAY, ls=':', lw=1.7, label='前5次拟合趋势')
    target = float(sample.capacity_Ah.iloc[0])
    ax.scatter([135], [target], marker='*', s=210, color=ORANGE, zorder=5, label='第135次实测标签')
    for row in history.itertuples():
        ax.annotate(f'{row.capacity_Ah:.4f}', (row.cycle, row.capacity_Ah), xytext=(0, 10), textcoords='offset points', ha='center', fontsize=11)
    ax.annotate(f'{target:.4f}', (135, target), xytext=(0, -20), textcoords='offset points', ha='center', fontsize=11, color=ORANGE)
    ax.set(xlabel='循环次数', ylabel='放电容量（Ah）', xlim=(129.6, 135.45), ylim=(1.305, 1.36), xticks=range(130, 136))
    ax.grid(alpha=.18)
    ax.legend(loc='upper left', fontsize=10)
    panel = fig.add_axes([.60, .19, .36, .60])
    panel.axis('off')
    rows = [
        ['循环次数', '135'],
        ['上一循环容量', f'{sample.lag1_Ah.iloc[0]:.4f} Ah'],
        ['前5次容量均值', f'{mean:.5f} Ah'],
        ['前5次变化斜率', f'{slope:+.5f} Ah/次'],
    ]
    table(panel, rows, ['输入特征', '数值'], [0, .35, 1, .65], [.55, .45], 14)
    panel.text(0, .23, f'待预测容量的真实标签：{target:.4f} Ah', fontsize=14, color=ORANGE)
    panel.text(0, .12, '标签仅用于训练或评价\n不参与该次输入特征的计算', fontsize=13, linespacing=1.5)
    fig.text(.055, .065, '均值表示近期容量水平；斜率来自5点直线拟合。这里的短期正斜率不代表电池整体停止老化。', fontsize=12, color=GRAY)
    return save(fig, '01_feature_extraction.png')


def split_figure(raw, features):
    fig = plt.figure(figsize=(13, 7.1))
    heading(fig, '按时间顺序划分数据', '每块电池独立建模  前5次仅提供历史  训练与验证之后保留测试段')
    ax = fig.add_axes([.10, .28, .85, .48])
    colors = {'history': '#DDE3E8', 'train': BLUE, 'validation': ORANGE, 'test': GREEN}
    batteries = sorted(raw.battery_id.unique())
    for y, battery in enumerate(batteries):
        n = len(raw[raw.battery_id == battery])
        a, b = int(n*.6), int(n*.8)
        segments = [(1, 5, 'history'), (6, a, 'train'), (a+1, b, 'validation'), (b+1, n, 'test')]
        for start, end, name in segments:
            ax.barh(y, end-start+1, left=start-.5, height=.62, color=colors[name], edgecolor='white')
            if name != 'history':
                ax.text((start+end)/2, y, f'{start}—{end}\n{end-start+1}条', ha='center', va='center', color='white', fontsize=13)
    ax.set(yticks=range(4), yticklabels=batteries, xlabel='预测目标的循环次数', xlim=(.5, 169))
    ax.invert_yaxis()
    ax.spines[['left', 'bottom']].set_visible(False)
    ax.tick_params(axis='y', length=0, pad=9)
    ax.set_xticks([1, 30, 60, 90, 120, 150, 168])
    ax.grid(axis='x', alpha=.10)
    handles = [plt.Rectangle((0, 0), 1, 1, color=colors[k]) for k in colors]
    fig.legend(handles, ['历史记录', '训练段', '验证段', '测试段'], loc='lower center', bbox_to_anchor=(.5, .15), ncol=4, frameon=False, fontsize=14)
    counts = features.groupby('split').size()
    fig.text(.055, .11, f'建模样本共{len(features)}条：训练{counts["train"]}条，验证{counts["validation"]}条，测试{counts["test"]}条。', fontsize=14)
    fig.text(.055, .047, '验证段用于选择随机森林参数；确定方案后合并训练与验证段重新拟合。测试模型固定，输入随已测得的历史更新。', fontsize=11.5, color=GRAY)
    return save(fig, '02_time_split.png')


def linear_figure(sample, models, example):
    model = models['B0006']
    values = sample[FEATURES].iloc[0].to_numpy(float)
    coefficients = np.array(model['coefficients_raw'])
    contributions = values*coefficients
    prediction = float(model['intercept_Ah']+contributions.sum())
    np.testing.assert_allclose(prediction, example['predictions']['linear_ols'], atol=1e-12)
    fig = plt.figure(figsize=(13, 7.2))
    heading(fig, '线性回归怎样算出一次预测', 'B0006第135次  使用最终模型的原始尺度系数  系数由最小二乘法拟合得到')
    fig.text(.08, .80, '预测容量 = 截距 + 循环项 + 上次容量项 + 近期均值项 + 近期趋势项', fontsize=19)
    ax = fig.add_axes([.08, .25, .84, .47])
    ax.axis('off')
    names = ['循环次数', '上一循环容量', '前5次容量均值', '前5次变化斜率']
    rows = [[name, f'{value:.5f}', f'{coef:+.8f}', f'{term:+.6f}'] for name, value, coef, term in zip(names, values, coefficients, contributions)]
    rows.append(['截距', '—', '—', f'{model["intercept_Ah"]:+.6f}'])
    table(ax, rows, ['项目', '输入值', '拟合系数', '对预测值的贡献（Ah）'], [0, 0, 1, 1], [.25, .20, .25, .30], 15)
    actual = float(sample.capacity_Ah.iloc[0])
    fig.text(.08, .16, f'各项相加得到预测容量  {prediction:.6f} Ah', fontsize=21, weight='bold', color=BLUE)
    fig.text(.08, .10, f'真实容量  {actual:.6f} Ah       本次绝对误差  {abs(prediction-actual):.6f} Ah', fontsize=15)
    fig.text(.08, .035, '表中数值已四舍五入。模型实际用标准化输入求解，这里将系数还原为原始尺度；系数不代表因果作用。', fontsize=11, color=GRAY)
    return save(fig, '03_linear_prediction.png')


def forest_figure(sample, example):
    forest = joblib.load(ROOT / 'results/step07/B0006_forest.joblib')
    x = sample[FEATURES].to_numpy(float)
    outputs = np.array([tree.predict(x)[0] for tree in forest.estimators_])
    np.testing.assert_allclose(outputs.mean(), example['predictions']['random_forest'], atol=1e-12)
    fig = plt.figure(figsize=(13, 7.6))
    heading(fig, '随机森林怎样完成同一次预测', 'B0006第135次  展示已训练森林的真实路径与300棵树输出  没有重新训练模型')
    left = fig.add_axes([.05, .22, .43, .56])
    left.axis('off')
    labels = {'lag1_Ah': '上一循环容量', 'cycle': '循环次数'}
    rows = []
    for i, node in enumerate(example['first_tree_path'], 1):
        value = f'{node["observed"]:g}'
        threshold = f'{node["threshold"]:.5f}'.rstrip('0').rstrip('.')
        sign = '≤' if node['branch'] == '<=' else '>'
        rows.append([str(i), f'{labels[node["feature"]]}  {value} {sign} {threshold}'])
    left.text(0, 1.06, '第1棵树的实际判断路径', fontsize=16, weight='bold')
    table(left, rows, ['顺序', '样本沿着这些条件进入叶节点'], [0, .20, 1, .80], [.14, .86], 12.5)
    left.text(0, .055, f'到达叶节点  →  输出 {outputs[0]:.6f} Ah', fontsize=15, color=BLUE)
    ax = fig.add_axes([.57, .28, .38, .48])
    ax.scatter(np.arange(1, len(outputs)+1), outputs, s=13, alpha=.55, color=BLUE, label='每棵树的预测')
    ax.axhline(outputs.mean(), color=ORANGE, lw=2, label='300棵树的平均值')
    ax.set(xlabel='树的编号', ylabel='预测容量（Ah）', xlim=(-4, 305))
    ax.grid(alpha=.15)
    ax.legend(fontsize=10, loc='upper right')
    fig.text(.55, .80, '300棵树分别预测，再取平均', fontsize=16, weight='bold')
    fig.text(.055, .12, f'森林最终预测  {outputs.mean():.6f} Ah       实测容量  {example["actual_Ah"]:.6f} Ah', fontsize=20, weight='bold')
    fig.text(.055, .05, '各树有放回抽样，每次分组考虑全部4个特征；叶节点容量均值按抽样次数加权。这里只展示第1棵树的路径。', fontsize=11, color=GRAY)
    return save(fig, '04_random_forest_prediction.png'), outputs


def comparison_figure(metrics, macro):
    names = {'persistence': '容量保持基线', 'linear_ols': '普通线性回归', 'random_forest': '随机森林'}
    colors = [BLUE, ORANGE, GREEN]
    test = metrics[metrics.split == 'test']
    fig = plt.figure(figsize=(13, 7.2))
    heading(fig, '测试集预测误差比较', '相同测试目标的RMSE比较  每种方法均预测129个目标  数值越小越好')
    ax = fig.add_axes([.08, .29, .58, .48])
    batteries = sorted(test.battery_id.unique())
    x = np.arange(4)
    for i, (key, label) in enumerate(names.items()):
        part = test[test.model == key].set_index('battery_id').loc[batteries]
        bars = ax.bar(x+(i-1)*.24, part.RMSE_Ah, width=.22, color=colors[i], label=label)
        ax.bar_label(bars, labels=[f'{value:.4f}' for value in part.RMSE_Ah], padding=3, fontsize=9)
    ax.set(xticks=x, xticklabels=batteries, xlabel='电池编号', ylabel='测试RMSE（Ah）', ylim=(0, .12))
    ax.grid(axis='y', alpha=.15)
    ax.legend(frameon=False, fontsize=10, loc='upper right')
    panel = fig.add_axes([.71, .33, .25, .40])
    panel.axis('off')
    macro = macro.set_index('model')
    rows = [[label, f'{macro.loc[key, "RMSE_Ah"]:.4f}'] for key, label in names.items()]
    panel.text(0, 1.12, '四块电池等权平均', fontsize=16, weight='bold')
    table(panel, rows, ['方法', 'RMSE（Ah）'], [0, 0, 1, 1], [.62, .38], 13)
    fig.text(.055, .14, '这套数据中，容量保持基线整体误差最低；随机森林在B0006后期明显高估容量。', fontsize=16)
    fig.text(.055, .06, '右表取每块电池RMSE的平均值，区别于合并129个样本后重新计算RMSE。该结果对应当前特征与时间划分。', fontsize=11.5, color=GRAY)
    return save(fig, '05_test_rmse_comparison.png')


def main():
    raw = pd.read_csv(ROOT / 'results/step01/battery_clean.csv')
    features = load_features()
    sample = features.query("battery_id == 'B0006' and cycle == 135")
    example = json.loads((ROOT / 'results/step08/worked_example.json').read_text())
    models = json.loads((ROOT / 'results/step06/linear_models.json').read_text())
    metrics = pd.read_csv(ROOT / 'results/step08/metrics.csv')
    macro = pd.read_csv(ROOT / 'results/step08/macro_test.csv')
    assert len(features) == 616 and len(features[features.split == 'test']) == 129
    assert len(sample) == 1
    np.testing.assert_allclose(sample[FEATURES].iloc[0].to_numpy(float), [example['features'][name] for name in FEATURES], atol=1e-12)
    files = [features_figure(raw, sample), split_figure(raw, features), linear_figure(sample, models, example)]
    forest_path, outputs = forest_figure(sample, example)
    files.extend([forest_path, comparison_figure(metrics, macro)])
    sources = ['src/comparison_common.py', 'results/step01/battery_clean.csv', 'results/step06/linear_models.json', 'results/step07/B0006_forest.joblib', 'results/step08/worked_example.json', 'results/step08/metrics.csv', 'results/step08/macro_test.csv']
    payload = {
        'purpose': 'report illustrations of existing models; no model refitting or tuning',
        'figures': files, 'example_battery': 'B0006', 'example_target_cycle': 135,
        'feature_values': example['features'], 'linear_prediction_Ah': example['predictions']['linear_ols'],
        'forest_tree_count': len(outputs), 'forest_mean_Ah': float(outputs.mean()),
        'sources_sha256': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources},
    }
    (OUT / 'figure_sources.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    for file in files:
        print(file)


if __name__ == '__main__':
    main()
