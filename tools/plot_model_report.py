"""仅从已保存的预测表绘制报告图，独立重算指标，不训练或调参。"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
BATTERIES=['B0005','B0006','B0007','B0018']


def verify(pred,metrics,stage):
    checks=0
    for _,r in metrics.iterrows():
        g=pred[(pred.battery_id==r.battery_id)&(pred.split==r['split'])&(pred.model==r.model)]
        if stage==5:
            g=g[g.horizon==r.horizon]
            if r.scope=='common_origins':g=g[g.common_origin]
        if len(g)!=r.n:raise ValueError('预测点数不匹配')
        err=g.predicted_Ah-g.actual_Ah
        for key,value in [('MAE_Ah',abs(err).mean()),('RMSE_Ah',np.sqrt(np.mean(err**2)))]:
            if not np.isclose(value,r[key],rtol=1e-9,atol=1e-10):raise ValueError('指标与逐点预测不一致')
        checks+=1
    return checks


def main():
    inputs=['results/step03/predictions.csv','results/step03/metrics.csv',
            'results/step05/predictions.csv','results/step05/metrics.csv']
    old,met_old,new,met_new=[pd.read_csv(ROOT/p) for p in inputs]
    counts={'step03_metric_groups':verify(old,met_old,3),'step05_metric_groups':verify(new,met_new,5)}
    raw=pd.read_csv(ROOT/'data/battery.csv').set_index(['battery_id','cycle']).capacity_Ah
    for frame,cycle_key in [(old,'cycle'),(new,'target_cycle')]:
        observed=np.array([raw.loc[(r.battery_id,int(getattr(r,cycle_key)))] for r in frame.itertuples()])
        np.testing.assert_allclose(frame.actual_Ah,observed,atol=1e-12)
    for step,keys in [('step03',['battery_id']),('step05',['battery_id','horizon'])]:
        models=json.loads((ROOT/f'results/{step}/ridge_models.json').read_text())
        search=pd.read_csv(ROOT/f'results/{step}/ridge_validation_search.csv')
        for key,g in search.groupby(keys):
            values=key if isinstance(key,tuple) else (key,)
            model_key=values[0] if step=='step03' else f'{values[0]}_h{values[1]}'
            assert models[model_key]['alpha']==g.loc[g.RMSE_Ah.idxmin(),'alpha']
    macro=pd.read_csv(ROOT/'results/step05/macro_common_origins.csv')
    expected=met_new[(met_new.split=='test')&(met_new.scope=='common_origins')].groupby(['horizon','model'])[['MAE_Ah','RMSE_Ah','bias_Ah']].mean()
    for r in macro.itertuples():
        np.testing.assert_allclose([r.MAE_Ah,r.RMSE_Ah,r.bias_Ah],expected.loc[(r.horizon,r.model)],atol=1e-12)
    names_old={'persistence':'上一循环基线','linear_cycle':'全训练段线性回归','ridge_history':'历史特征岭回归'}
    names_new={'persistence':'容量保持基线','linear_recent20':'最近20次线性趋势','ridge_direct':'直接多步岭回归'}
    colors=['#176B87','#D3662E','#647D32'];styles=['--','-.','-']
    dest=ROOT/'figures/model_report';dest.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'Arial Unicode MS','axes.unicode_minus':False,'font.size':11,
                         'axes.spines.top':False,'axes.spines.right':False})
    for stage,pred,names in [(3,old,names_old),(5,new,names_new)]:
        for battery in BATTERIES:
            g=pred[(pred.battery_id==battery)&(pred.split=='test')]
            if stage==5:g=g[(g.horizon==10)&g.common_origin]
            xkey='cycle' if stage==3 else 'target_cycle'
            actual=g[g.model==next(iter(names))].sort_values(xkey)
            fig,ax=plt.subplots(figsize=(8.5,3.25),layout='constrained')
            ax.plot(actual[xkey],actual.actual_Ah,color='#172B3A',lw=2.1,label='实测容量',zorder=5)
            for (model,label),color,style in zip(names.items(),colors,styles):
                s=g[g.model==model].sort_values(xkey)
                ax.plot(s[xkey],s.predicted_Ah,color=color,linestyle=style,lw=1.5,label=label)
            title=f'{battery} 单步容量预测（{len(actual)}个测试目标）' if stage==3 else f'{battery} 提前10次预测（{len(actual)}个共同测试起点）'
            ax.set(title=title,xlabel='预测目标循环次数',ylabel='放电容量（Ah）')
            ax.grid(alpha=.2);ax.legend(fontsize=8,loc='best',ncol=2)
            fig.savefig(dest/f'step{stage:02}_{battery}.png',dpi=200)
            plt.close(fig)
    sources=inputs+['data/battery.csv','results/step03/ridge_models.json','results/step03/ridge_validation_search.csv',
                    'results/step05/ridge_models.json','results/step05/ridge_validation_search.csv',
                    'results/step05/macro_common_origins.csv']
    audit={'source_snapshot':'6ef0b58','verified_groups':counts,
           'additional_checks':['all actual values match original CSV','all 16 selected alphas minimize validation RMSE','macro averages match per-battery metrics'],
           'sources_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources},
           'report_figures':'step03 full test; step05 horizon10 common origins; x axis target cycle'}
    out=ROOT/'results/model_report';out.mkdir(parents=True,exist_ok=True)
    (out/'source_verification.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(counts,ensure_ascii=False))

if __name__=='__main__':main()
