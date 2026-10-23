"""独立重算关键指标与时间边界，防止结果文件和建模输出错位。"""
from pathlib import Path
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parents[1]
d=pd.read_csv(R/'data/battery.csv');p=pd.read_csv(R/'results/predictions.csv');m=pd.read_csv(R/'results/metrics.csv');r=pd.read_csv(R/'results/rul.csv')
assert len(d)==636 and len(p)==129*3
for (b,model),g in p.groupby(['battery_id','model']):
 raw=d[d.battery_id==b].set_index('cycle');n=len(raw)
 assert g.cycle.min()==int(.8*n)+1
 assert np.allclose(g.actual,raw.loc[g.cycle,'capacity_Ah'])
 rmse=np.sqrt(np.mean((g.predicted-g.actual)**2))
 assert np.isclose(rmse,m[(m.battery_id==b)&(m.model==model)].RMSE.iloc[0])
 if model=='上一循环基线': assert np.allclose(g.predicted,raw.loc[g.cycle-1,'capacity_Ah'])
for row in r.itertuples():
 g=d[d.battery_id==row.battery_id];hit=g[g.capacity_Ah<=g.capacity_Ah.iloc[0]*.8].cycle.iloc[0]
 assert row.observed_crossing==hit and row.origin<hit
 assert row.actual_RUL==hit-row.origin
print('PASS: 387 predictions, all RMSE values, lag baseline and RUL origin/labels verified')
