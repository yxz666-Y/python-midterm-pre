"""验证关键科学约束：历史窗口与时间划分，而非复刻模型实现。"""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('step03', ROOT/'src/03_features_and_models.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.raw = pd.read_csv(ROOT/'data/battery.csv')

    def test_no_future_leakage(self):
        before = m.make_features(self.raw)
        changed = self.raw.copy()
        changed.loc[(changed.battery_id == 'B0005') & (changed.cycle >= 90), 'capacity_Ah'] += 10
        after = m.make_features(changed)
        mask = (before.battery_id == 'B0005') & (before.cycle <= 90)
        np.testing.assert_allclose(before.loc[mask, m.FEATURES], after.loc[mask, m.FEATURES])

    def test_known_history(self):
        raw = pd.DataFrame({'battery_id': ['X']*20, 'cycle': np.arange(1,21),
                            'capacity_Ah': 3-.01*np.arange(1,21)})
        row = m.make_features(raw).iloc[0]
        self.assertEqual(row.cycle, 6)
        self.assertAlmostEqual(row.lag1_Ah, 2.95)
        self.assertAlmostEqual(row.mean5_Ah, 2.97)
        self.assertAlmostEqual(row.slope5_Ah_per_cycle, -.01)

    def test_linear_known_trend(self):
        train = pd.DataFrame({'cycle': np.arange(1,21), 'capacity_Ah': 3-.01*np.arange(1,21)})
        target = pd.DataFrame({'cycle': [21,22]})
        np.testing.assert_allclose(m.linear_predict(train, target), [2.79,2.78])

    def test_test_values_do_not_change_tuning(self):
        data = m.make_features(self.raw)
        g = data[data.battery_id == 'B0005'].copy()
        best, scores = m.select_alpha(g)
        g.loc[g.split == 'test', m.FEATURES + ['capacity_Ah']] = 999.
        self.assertEqual((best, scores), m.select_alpha(g))

    def test_ridge_intercept_and_training_scale(self):
        g = m.make_features(self.raw)
        train = g[(g.battery_id == 'B0005') & (g.split == 'train')].copy()
        train['capacity_Ah'] = 2.
        model = m.fit_ridge(train, 10.)
        np.testing.assert_allclose(model['mean'], train[m.FEATURES].mean())
        np.testing.assert_allclose(m.predict_ridge(model, g), 2., atol=1e-9)

    def test_splits_and_rows(self):
        df = m.make_features(self.raw)
        self.assertEqual(len(df), 616)
        for _, g in df.groupby('battery_id'):
            self.assertLess(g[g.split=='train'].cycle.max(), g[g.split=='validation'].cycle.min())
            self.assertLess(g[g.split=='validation'].cycle.max(), g[g.split=='test'].cycle.min())
            self.assertEqual(g.cycle.min(), 6)

if __name__ == '__main__':
    unittest.main()
