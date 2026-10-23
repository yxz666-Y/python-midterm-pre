"""按电池时间顺序验证容量预测，所有特征仅使用当前预测点之前的观测。"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
for folder in ['results','figures']: (ROOT/folder).mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'Arial Unicode MS','axes.unicode_minus':False,'figure.dpi':150})
df=pd.read_csv(ROOT/'data/battery.csv').sort_values(['battery_id','cycle'])
assert list(df)==['battery_id','cycle','capacity_Ah','ambient_temp_C']
assert not df.isna().any().any() and not df.duplicated(['battery_id','cycle']).any()
assert (df.capacity_Ah>0).all()
def metrics(y,p):
 e=np.asarray(p)-y
 return {'MAE':float(np.mean(abs(e))),'RMSE':float(np.sqrt(np.mean(e**2))),'Bias':float(np.mean(e))}
def fit(x,y,a=0):
 mu=x.mean(0);sd=x.std(0);sd[sd==0]=1
 z=np.column_stack([np.ones(len(x)),(x-mu)/sd]);pen=np.eye(z.shape[1])*a;pen[0,0]=0
 w=np.linalg.pinv(z.T@z+pen)@z.T@y
 return lambda v:np.column_stack([np.ones(len(v)),(v-mu)/sd])@w
rows=[];preds=[];summary=[];rul=[];intervals=[]
fig,axs=plt.subplots(2,2,figsize=(10,7))
for ax,(bid,g) in zip(axs.flat,df.groupby('battery_id')):
 q=g.capacity_Ah.to_numpy();c=g.cycle.to_numpy();n=len(q);t1=int(n*.6);t2=int(n*.8)
 summary.append(dict(battery_id=bid,n=n,initial=q[0],last=q[-1],loss_pct=100*(1-q[-1]/q[0]),rebounds=int((np.diff(q)>0).sum())))
 # index i predicts q[i]; rolling mean and slope end at i-1
 idx=np.arange(5,n);x=np.array([[c[i],q[i-1],q[i-2],q[i-5:i].mean(),(q[i-1]-q[i-5])/4] for i in idx]);y=q[idx]
 tr=idx<t1;va=(idx>=t1)&(idx<t2);te=idx>=t2
 alpha=min([0.01,.1,1,10,100],key=lambda a:metrics(y[va],fit(x[tr],y[tr],a)(x[va]))['RMSE'])
 methods={'上一循环基线':(q[idx[va]-1],q[idx[te]-1]),'循环线性回归':(fit(c[:t1,None],q[:t1])(c[idx[va],None]),fit(c[:t2,None],q[:t2])(c[idx[te],None])),'历史特征岭回归':(fit(x[tr],y[tr],alpha)(x[va]),fit(x[tr|va],y[tr|va],alpha)(x[te]))}
 ax.plot(c,q,color='#374151',label='实测容量')
 for name,(pv,pt) in methods.items():
  m=metrics(y[te],pt);rows.append(dict(battery_id=bid,model=name,alpha=alpha if name=='历史特征岭回归' else None,train_end=t1,validation_end=t2,**m))
  # validation-calibrated empirical absolute-residual band; no exchangeability guarantee
  width=float(np.quantile(abs(y[va]-pv),.9,method='higher'))
  intervals.append(dict(battery_id=bid,model=name,half_width=width,coverage=float(np.mean(abs(y[te]-pt)<=width))))
  for ci,yi,pi in zip(c[te.nonzero()[0]+5],y[te],pt):preds.append(dict(battery_id=bid,cycle=int(ci),model=name,actual=yi,predicted=pi))
  ax.plot(c[idx[te]],pt,label=name,linewidth=1.2)
 ax.axvline(t2,color='gray',linestyle='--');ax.set(title=bid,xlabel='循环次数',ylabel='容量 / Ah');ax.legend(fontsize=7)
 # fixed-origin extrapolation, using first 30%; terminal threshold is 80% of first observation
 cut=int(n*.3);future=np.arange(cut+1,501);threshold=.8*q[0]
 hits=c[q<=threshold];actual=int(hits[0]) if len(hits) else None
 for degree in [1,2]:
  coef=np.polyfit(c[:cut],q[:cut],degree);pq=np.polyval(coef,future);h=future[pq<=threshold];event=int(h[0]) if len(h) else None
  rul.append(dict(battery_id=bid,degree=degree,origin=cut,threshold=threshold,observed_crossing=actual,predicted_crossing=event,actual_RUL=max(0,actual-cut) if actual else None,predicted_RUL=event-cut if event else None,**metrics(q[cut:],np.polyval(coef,c[cut:]))))
fig.tight_layout();fig.savefig(ROOT/'figures/predictions.png');plt.close(fig)
res=pd.DataFrame(rows);res.to_csv(ROOT/'results/metrics.csv',index=False);pd.DataFrame(preds).to_csv(ROOT/'results/predictions.csv',index=False);pd.DataFrame(intervals).to_csv(ROOT/'results/intervals.csv',index=False);pd.DataFrame(rul).to_csv(ROOT/'results/rul.csv',index=False);pd.DataFrame(summary).to_csv(ROOT/'results/summary.csv',index=False)
fig,ax=plt.subplots(figsize=(9,4.7))
for bid,g in df.groupby('battery_id'):ax.plot(g.cycle,g.capacity_Ah,label=bid)
ax.set(xlabel='循环次数',ylabel='放电容量 / Ah',title='四块电池的容量退化与局部回升');ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(ROOT/'figures/degradation.png');plt.close(fig)
fig,ax=plt.subplots(figsize=(9,4.7));res.pivot(index='battery_id',columns='model',values='RMSE').plot.bar(ax=ax);ax.set(ylabel='测试集 RMSE / Ah',xlabel='电池');ax.tick_params(axis='x',rotation=0);fig.tight_layout();fig.savefig(ROOT/'figures/comparison.png');plt.close(fig)
fig,ax=plt.subplots(figsize=(9,4.7))
for bid,g in df.groupby('battery_id'):ax.plot(g.cycle,g.capacity_Ah/g.capacity_Ah.iloc[0]*100,label=bid)
ax.axhline(80,color='red',linestyle='--',label='研究阈值 80%');ax.set(xlabel='循环次数',ylabel='相对首循环容量 / %',title='健康状态与假设寿命阈值');ax.legend();fig.tight_layout();fig.savefig(ROOT/'figures/soh.png');plt.close(fig)
audit={'rows':len(df),'missing':df.isna().sum().to_dict(),'duplicates':int(df.duplicated().sum()),'temperature_values':df.ambient_temp_C.unique().tolist(),'capacity_range':[df.capacity_Ah.min(),df.capacity_Ah.max()],'seed':'deterministic, no random split'}
(ROOT/'results/audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
print(res.to_string(index=False));print(pd.DataFrame(rul).to_string(index=False));print(pd.DataFrame(intervals).to_string(index=False))
