import importlib.util
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('step05',ROOT/'src/05_multihorizon_models.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class MultiHorizonTests(unittest.TestCase):
    def setUp(self):
        self.raw=pd.read_csv(ROOT/'data/battery.csv')

    def test_known_linear_extrapolation(self):
        for h in m.HORIZONS:
            self.assertAlmostEqual(m.recent_linear(2-.01*np.arange(1,41),h),2-.01*(40+h))

    def test_future_changes_do_not_change_origin_features(self):
        a=m.make_samples(self.raw)
        changed=self.raw.copy();changed.loc[(changed.battery_id=='B0005')&(changed.cycle>134),'capacity_Ah']+=1
        b=m.make_samples(changed)
        mask=(a.battery_id=='B0005')&(a.origin_cycle<=134)
        np.testing.assert_allclose(a.loc[mask,m.FEATURES],b.loc[mask,m.FEATURES])

    def test_origin_has_all_fitted_targets(self):
        data=m.make_samples(self.raw)
        for (_,h),g in data.groupby(['battery_id','horizon']):
            train=g[g.split=='train']; val=g[g.split=='validation']; test=g[g.split=='test']
            self.assertLessEqual(train.target_cycle.max(),val.origin_cycle.min())
            self.assertLessEqual(g[g.target_cycle<=g.validation_end_cycle].target_cycle.max(),test.origin_cycle.min())
            self.assertTrue((g.target_cycle-g.origin_cycle==h).all())
            self.assertTrue((test.target_cycle<=test.observation_end_cycle).all())

    def test_horizons_share_common_test_origins(self):
        _,pred,_=m.experiment(self.raw)
        for battery,g in pred[(pred.split=='test')&pred.common_origin].groupby('battery_id'):
            sets=[set(v.origin_cycle) for _,v in g.groupby(['horizon','model'])]
            self.assertTrue(all(s==sets[0] for s in sets))

    def test_invalid_keys_rejected(self):
        with self.assertRaises(ValueError):m.make_samples(pd.concat([self.raw,self.raw.iloc[:1]]))
        bad=self.raw.copy();bad.loc[0,'capacity_Ah']=np.nan
        with self.assertRaises(ValueError):m.make_samples(bad)

if __name__=='__main__':unittest.main()
