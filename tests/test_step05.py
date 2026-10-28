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
        _,pred,_,_,_=m.experiment(self.raw)
        for (battery,split),g in pred[pred.common_origin].groupby(['battery_id','split']):
            sets=[set(v.origin_cycle) for _,v in g.groupby(['horizon','model'])]
            self.assertTrue(all(s==sets[0] for s in sets))

    def test_no_unavailable_targets_in_model(self):
        _,pred,_,_,models=m.experiment(self.raw)
        self.assertTrue((pred.model_information_cutoff_cycle<=pred.origin_cycle).all())
        for key,model in models.items():
            self.assertEqual(model['latest_fitted_target_cycle'],105 if key.startswith('B0018') else 134)

    def test_test_targets_do_not_select_alpha_or_first_forecast(self):
        _,a,_,search_a,models_a=m.experiment(self.raw)
        changed=self.raw.copy()
        for battery,g in changed.groupby('battery_id'):
            changed.loc[(changed.battery_id==battery)&(changed.cycle>int(len(g)*.8)),'capacity_Ah']+=1
        _,b,_,search_b,models_b=m.experiment(changed)
        pd.testing.assert_frame_equal(search_a,search_b)
        self.assertEqual(models_a,models_b)
        first=a[(a.split=='test')].groupby(['battery_id','horizon','model']).origin_cycle.transform('min')
        mask=(a.split=='test') & (a.origin_cycle==first.reindex(a.index))
        np.testing.assert_allclose(a.loc[mask,'predicted_Ah'],b.loc[mask,'predicted_Ah'])

    def test_ridge_constant_capacity(self):
        data=m.make_samples(self.raw)
        train=data[(data.battery_id=='B0005')&(data.horizon==5)&(data.split=='train')].copy()
        train['actual_Ah']=2.
        model=m.fit_direct_ridge(train,10.)
        np.testing.assert_allclose(m.predict_direct_ridge(model,data[data.horizon==5]),2.,atol=1e-8)

    def test_invalid_keys_rejected(self):
        with self.assertRaises(ValueError):m.make_samples(pd.concat([self.raw,self.raw.iloc[:1]]))
        bad=self.raw.copy();bad.loc[0,'capacity_Ah']=np.nan
        with self.assertRaises(ValueError):m.make_samples(bad)

if __name__=='__main__':unittest.main()
