"""第五步：固定预测起点，分别预测后1、5、10次循环容量。
逐电池按时间划分；每个起点只用当时已知容量，不读取中间未来观测。
运行前先运行01。输出只写入step05，不覆盖此前结果。
"""
from pathlib import Path
import json
import hashlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
HORIZONS=(1,5,10)
ALPHAS=(0.01,0.1,1.,10.,100.)
FEATURES=['target_cycle','origin_capacity_Ah','mean5_Ah','slope5_Ah_per_cycle']


def make_samples(raw):
    required={'battery_id','cycle','capacity_Ah','ambient_temp_C'}
    if not required.issubset(raw.columns) or raw[list(required)].isna().any().any():
        raise ValueError('输入字段不完整或包含缺失')
    if not np.isfinite(raw[['cycle','capacity_Ah','ambient_temp_C']]).all().all():
        raise ValueError('输入含非有限数值')
    if (raw.capacity_Ah<=0).any() or raw.duplicated(['battery_id','cycle']).any():
        raise ValueError('存在非正容量或重复主键')
    rows=[]
    for battery,g in raw.groupby('battery_id'):
        g=g.sort_values('cycle'); n=len(g)
        if not np.array_equal(g.cycle.to_numpy(),np.arange(1,n+1)):
            raise ValueError('循环须从1开始连续')
        values=g.capacity_Ah.to_numpy()
        train_end,val_end=int(n*.6),int(n*.8)
        for h in HORIZONS:
            for origin in range(5,n-h+1):
                target=origin+h
                history=values[:origin]
                split=('train' if target<=train_end else
                       'validation' if origin>=train_end and target<=val_end else
                       'test' if origin>=val_end else 'boundary_gap')
                recent=history[-5:]
                rows.append({'battery_id':battery,'horizon':h,'origin_cycle':origin,
                    'target_cycle':target,'origin_capacity_Ah':history[-1],
                    'mean5_Ah':recent.mean(),'slope5_Ah_per_cycle':np.dot(recent,np.arange(5)-2)/10,
                    'actual_Ah':values[target-1],'split':split,
                    'train_end_cycle':train_end,'validation_end_cycle':val_end,
                    'observation_end_cycle':n})
    return pd.DataFrame(rows)


def recent_linear(history,horizon):
    """最近20次实测容量拟合直线，在当前起点一次外推h步。"""
    y=np.asarray(history,dtype=float)[-20:]
    x=np.arange(len(y),dtype=float)
    design=np.column_stack([np.ones(len(y)),x])
    beta=np.linalg.lstsq(design,y,rcond=None)[0]
    return float(np.array([1.,len(y)-1+horizon])@beta)


def score(actual,predicted):
    error=np.asarray(predicted)-np.asarray(actual)
    return {'MAE_Ah':float(np.mean(abs(error))), 'RMSE_Ah':float(np.sqrt(np.mean(error**2))),
            'bias_Ah':float(np.mean(error))}


def fit_direct_ridge(train,alpha):
    """每个horizon独立拟合Q(origin+h)，仅用已知目标。"""
    x=train[FEATURES].to_numpy(dtype=float)
    mean,scale=x.mean(axis=0),x.std(axis=0)
    scale=np.where(scale==0,1.,scale)
    design=np.column_stack([np.ones(len(x)),(x-mean)/scale])
    beta=np.linalg.solve(design.T@design+np.diag([0.]+[alpha]*len(FEATURES)),
                         design.T@train.actual_Ah.to_numpy())
    return {'alpha':float(alpha),'features':FEATURES,'mean':mean.tolist(),'scale':scale.tolist(),
            'coefficients_standardized':beta.tolist(),
            'latest_fitted_target_cycle':int(train.target_cycle.max())}


def predict_direct_ridge(model,target):
    x=(target[FEATURES].to_numpy()-model['mean'])/model['scale']
    return np.column_stack([np.ones(len(x)),x])@model['coefficients_standardized']


def choose_alpha(g):
    train=g[g.split=='train'];val=g[g.split=='validation']
    search=[{'alpha':a,**score(val.actual_Ah,predict_direct_ridge(fit_direct_ridge(train,a),val))}
            for a in ALPHAS]
    return min(search,key=lambda r:r['RMSE_Ah'])['alpha'],search


def experiment(raw):
    samples=make_samples(raw)
    predictions=[]; tuning=[]; models={}
    histories={b:g.sort_values('cycle').capacity_Ah.to_numpy() for b,g in raw.groupby('battery_id')}
    for (battery,h),g in samples.groupby(['battery_id','horizon']):
        alpha,search=choose_alpha(g)
        tuning.extend({'battery_id':battery,'horizon':int(h),**r} for r in search)
        final_model=fit_direct_ridge(g[g.target_cycle<=g.validation_end_cycle],alpha)
        models[f'{battery}_h{h}']=final_model
        for split in ['validation','test']:
            target=g[g.split==split]
            cutoff=int(g.train_end_cycle.iloc[0] if split=='validation' else g.validation_end_cycle.iloc[0])
            assert (target.origin_cycle>=cutoff).all()
            outputs={'persistence':target.origin_capacity_Ah.to_numpy(),
                'linear_recent20':np.array([recent_linear(histories[battery][:int(o)],h) for o in target.origin_cycle]),
                'ridge_direct':predict_direct_ridge(fit_direct_ridge(g[g.split=='train'],alpha) if split=='validation' else final_model,target)}
            for model,values in outputs.items():
                part=target[['battery_id','horizon','origin_cycle','target_cycle','actual_Ah','split','observation_end_cycle']].copy()
                part['model']=model; part['predicted_Ah']=values
                part['model_information_cutoff_cycle']=(target.origin_cycle.to_numpy() if model!='ridge_direct' else cutoff)
                evaluation_end=int(target.validation_end_cycle.iloc[0] if split=='validation' else target.observation_end_cycle.iloc[0])
                part['common_origin']=(part.origin_cycle<=evaluation_end-max(HORIZONS))
                predictions.append(part)
    predictions=pd.concat(predictions,ignore_index=True)
    metrics=[]
    for (battery,h,split,model),g in predictions.groupby(['battery_id','horizon','split','model']):
        for scope,part in [('all_available',g),('common_origins',g[g.common_origin])]:
            metrics.append({'battery_id':battery,'horizon':h,'split':split,'model':model,
                            'scope':scope,'n':len(part),**score(part.actual_Ah,part.predicted_Ah)})
    return samples,predictions,pd.DataFrame(metrics),pd.DataFrame(tuning),models


def plot_and_summarize(metrics,predictions,out):
    common=metrics[(metrics.split=='test')&(metrics.scope=='common_origins')]
    macro=common.groupby(['horizon','model'],as_index=False)[['MAE_Ah','RMSE_Ah','bias_Ah']].mean()
    macro['aggregation']='unweighted mean of four per-battery metrics'
    macro.to_csv(out/'macro_common_origins.csv',index=False,encoding='utf-8-sig')
    dest=ROOT/'figures/step05';dest.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'Arial Unicode MS','axes.unicode_minus':False})
    names={'persistence':'容量保持基线','linear_recent20':'最近20次线性趋势','ridge_direct':'直接多步岭回归'}
    fig,axes=plt.subplots(1,3,figsize=(14,4.5),layout='constrained',sharey=True)
    for ax,h in zip(axes,HORIZONS):
        table=common[common.horizon==h].pivot(index='battery_id',columns='model',values='RMSE_Ah')
        table[list(names)].rename(columns=names).plot.bar(ax=ax,rot=0,legend=False)
        ax.set(title=f'提前{h}次',xlabel='电池编号',ylabel='RMSE（Ah）')
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='outside lower center',ncol=3)
    fig.suptitle('共同预测起点的测试误差：前三块各25个起点，B0018为18个')
    fig.savefig(dest/'multihorizon_comparison.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
    for model,name in names.items():
        part=macro[macro.model==model]
        ax.plot(part.horizon,part.RMSE_Ah,marker='o',label=name)
    ax.set(xlabel='提前预测的循环数',ylabel='四块电池RMSE的算术平均（Ah）',xticks=HORIZONS,
           title='预测距离与误差：各电池等权汇总，使用共同起点')
    ax.grid(alpha=.2);ax.legend()
    fig.savefig(dest/'macro_error_by_horizon.png',dpi=180);plt.close(fig)
    return macro


def main():
    raw=pd.read_csv(ROOT/'results/step01/battery_clean.csv')
    samples,predictions,metrics,tuning,models=experiment(raw)
    out=ROOT/'results/step05';out.mkdir(parents=True,exist_ok=True)
    for name,df in [('features',samples),('predictions',predictions),('metrics',metrics),('ridge_validation_search',tuning)]:
        df.to_csv(out/(name+'.csv'),index=False,encoding='utf-8-sig')
    (out/'ridge_models.json').write_text(json.dumps(models,ensure_ascii=False,indent=2),encoding='utf-8')
    macro=plot_and_summarize(metrics,predictions,out)
    config={'versions':{'numpy':np.__version__,'pandas':pd.__version__,'matplotlib':matplotlib.__version__},
            'ridge_alpha_candidates':ALPHAS,'parameter_selection':'validation RMSE only',
            'horizons':HORIZONS,'features':FEATURES,'recent_linear_window':20,
            'split_rule':'fit targets <= cutoff; validation/test origins >= fitted-label cutoff',
            'forecast_mode':'at each origin forecast directly h cycles ahead, using history through origin only',
            'common_test_origins':'from floor(0.8*n) through n-max(horizons), same origins for all horizons',
            'limitations':'same four previously inspected batteries; exploratory comparison, not new independent validation',
            'input_sha256':hashlib.sha256((ROOT/'results/step01/battery_clean.csv').read_bytes()).hexdigest(),
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (out/'experiment.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    print(macro.to_string(index=False))


if __name__=='__main__':main()
