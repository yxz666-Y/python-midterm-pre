"""只读取第六七步保存结果，核对指标并生成两类算法的比较图表。"""
import hashlib
import json
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from comparison_common import ROOT, FEATURES, load_features, score

NAMES = {'persistence': '容量保持基线', 'linear_ols': '普通线性回归', 'random_forest': '随机森林回归'}
COLORS = {'persistence': '#176B87', 'linear_ols': '#D3662E', 'random_forest': '#647D32'}


def main():
    pred = pd.concat([pd.read_csv(ROOT/f'results/{step}/predictions.csv') for step in ['step06','step07']], ignore_index=True)
    metrics = pd.concat([pd.read_csv(ROOT/f'results/{step}/metrics.csv') for step in ['step06','step07']], ignore_index=True)
    for r in metrics.itertuples():
        g = pred[(pred.battery_id == r.battery_id)&(pred.split == r.split)&(pred.model == r.model)]
        assert len(g) == r.n
        for field, value in score(g.actual_Ah,g.predicted_Ah).items():
            np.testing.assert_allclose(value,getattr(r,field),atol=1e-12)
    raw = pd.read_csv(ROOT/'data/battery.csv').set_index(['battery_id','cycle']).capacity_Ah
    for r in pred.itertuples(): np.testing.assert_allclose(r.actual_Ah,raw.loc[r.battery_id,r.cycle],atol=1e-12)
    # 各方法的目标完全一致，禁止通过删除难预测的测试点改善指标。
    expected = pred[pred.model == 'linear_ols'][['battery_id','split','cycle','actual_Ah']].sort_values(['battery_id','split','cycle']).reset_index(drop=True)
    for model in NAMES:
        actual = pred[pred.model == model][expected.columns].sort_values(['battery_id','split','cycle']).reset_index(drop=True)
        pd.testing.assert_frame_equal(actual,expected)
    test = pred[pred.split == 'test'].copy()
    test['error_Ah'] = test.predicted_Ah-test.actual_Ah
    macro = metrics[metrics.split == 'test'].groupby('model')[['MAE_Ah','RMSE_Ah','bias_Ah']].mean().reset_index()
    pooled = pd.DataFrame([{'model': m, 'n': len(g), **score(g.actual_Ah,g.predicted_Ah)} for m,g in test.groupby('model')])
    out = ROOT/'results/step08'; out.mkdir(parents=True,exist_ok=True)
    metrics.to_csv(out/'metrics.csv',index=False,encoding='utf-8-sig')
    pred.to_csv(out/'predictions.csv',index=False,encoding='utf-8-sig')
    macro.to_csv(out/'macro_test.csv',index=False,encoding='utf-8-sig')
    pooled.to_csv(out/'pooled_test.csv',index=False,encoding='utf-8-sig')
    test.loc[test.groupby('model').error_Ah.apply(lambda x: x.abs().idxmax()).values].to_csv(out/'largest_errors.csv',index=False,encoding='utf-8-sig')
    models = json.loads((ROOT/'results/step07/forest_metadata.json').read_text())
    rows = []
    for battery,g in test[test.model == 'random_forest'].groupby('battery_id'):
        minimum = models[battery]['fit_capacity_min_Ah']
        rows.append({'battery_id':battery,'n':len(g),'fit_capacity_min_Ah':minimum,
                     'test_capacity_min_Ah':g.actual_Ah.min(),'test_below_fit_min_n':int((g.actual_Ah<minimum).sum()),
                     'prediction_min_Ah':g.predicted_Ah.min(),'prediction_max_Ah':g.predicted_Ah.max(),
                     'overestimation_n':int((g.error_Ah>0).sum())})
    pd.DataFrame(rows).to_csv(out/'forest_range_diagnostic.csv',index=False,encoding='utf-8-sig')
    sample=load_features().query("battery_id == 'B0006' and cycle == 135")
    forest=joblib.load(ROOT/'results/step07/B0006_forest.joblib')
    tree=forest.estimators_[0]; x=sample[FEATURES].to_numpy()
    path=[]
    for node in tree.decision_path(x).indices:
        feature=tree.tree_.feature[node]
        if feature>=0:
            threshold=float(tree.tree_.threshold[node]); value=float(x[0,feature])
            path.append({'feature':FEATURES[feature],'observed':value,'threshold':threshold,
                         'branch':'<=' if value<=threshold else '>'})
    leaf=int(tree.apply(x)[0]); values=np.array([t.predict(x)[0] for t in forest.estimators_])
    example={'battery_id':'B0006','target_cycle':135,'features':{f:float(sample.iloc[0][f]) for f in FEATURES},
             'actual_Ah':float(sample.iloc[0].capacity_Ah),'first_tree_path':path,
             'first_tree_leaf_value_Ah':float(tree.predict(x)[0]),'first_tree_leaf_unique_training_n':int(tree.tree_.n_node_samples[leaf]),
             'tree_count':len(values),'tree_prediction_min_Ah':float(values.min()),
             'tree_prediction_max_Ah':float(values.max()),'tree_prediction_mean_Ah':float(values.mean()),
             'predictions':{m:float(test[(test.battery_id == 'B0006')&(test.cycle == 135)&(test.model == m)].predicted_Ah.iloc[0]) for m in NAMES}}
    np.testing.assert_allclose(example['tree_prediction_mean_Ah'],example['predictions']['random_forest'],atol=1e-12)
    (out/'worked_example.json').write_text(json.dumps(example,ensure_ascii=False,indent=2),encoding='utf-8')
    dest=ROOT/'figures/step08'; dest.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'Arial Unicode MS','axes.unicode_minus':False,'font.size':11,
                         'axes.spines.top':False,'axes.spines.right':False})
    for battery,g in test.groupby('battery_id'):
        fig,ax = plt.subplots(figsize=(8.5,3.25),layout='constrained')
        actual=g[g.model == 'linear_ols'].sort_values('cycle')
        ax.plot(actual.cycle,actual.actual_Ah,color='#172B3A',lw=2.1,label='实测容量',zorder=5)
        for m,style in zip(NAMES,['--','-.','-']):
            part=g[g.model == m].sort_values('cycle')
            ax.plot(part.cycle,part.predicted_Ah,color=COLORS[m],ls=style,lw=1.5,label=NAMES[m])
        ax.set(title=f'{battery} 相同测试目标的单步容量预测',xlabel='预测目标循环次数',ylabel='放电容量（Ah）')
        ax.grid(alpha=.2);ax.legend(fontsize=8,ncol=2,loc='best')
        fig.savefig(dest/f'{battery}_predictions.png',dpi=200);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(8.5,3.6),layout='constrained')
    palette=['#176B87','#D3662E','#647D32','#8A4E76']
    for ax,m in zip(axes,['linear_ols','random_forest']):
        g=test[test.model == m]
        lo=min(g.actual_Ah.min(),g.predicted_Ah.min())-.02;hi=max(g.actual_Ah.max(),g.predicted_Ah.max())+.02
        ax.plot([lo,hi],[lo,hi],color='gray',ls='--',lw=1)
        for (battery,part),color in zip(g.groupby('battery_id'),palette):
            ax.scatter(part.actual_Ah,part.predicted_Ah,s=15,color=color,alpha=.75,label=battery)
        ax.set(title=NAMES[m],xlabel='实测容量（Ah）',ylabel='预测容量（Ah）',xlim=(lo,hi),ylim=(lo,hi))
        ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.savefig(dest/'actual_vs_predicted.png',dpi=200);plt.close(fig)
    pivot=metrics[metrics.split == 'test'].pivot(index='battery_id',columns='model',values='RMSE_Ah')[list(NAMES)]
    ax=pivot.rename(columns=NAMES).plot.bar(color=list(COLORS.values()),figsize=(8.5,3.8),rot=0)
    ax.set(xlabel='电池编号',ylabel='测试RMSE（Ah）',title='同一目标与特征下的误差比较');ax.grid(axis='y',alpha=.2)
    ax.figure.tight_layout();ax.figure.savefig(dest/'rmse_comparison.png',dpi=200);plt.close(ax.figure)
    sources=['src/06_linear_regression.py','src/07_random_forest.py','src/comparison_common.py',
             'results/step06/predictions.csv','results/step07/predictions.csv',
             'results/step06/linear_models.json','results/step07/forest_metadata.json',
             'results/step07/validation_search.csv','data/battery.csv']
    (out/'verification.json').write_text(json.dumps({'verified_metric_groups':len(metrics),
        'test_targets_per_model':int(len(test)/3),'model_count':3,
        'checks':['all metric fields recomputed','same target keys and actual values for all models','actual values equal original CSV'],
        'sources_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources}},ensure_ascii=False,indent=2),encoding='utf-8')
    print(macro.to_string(index=False));print(pd.DataFrame(rows).to_string(index=False))


if __name__ == '__main__': main()
