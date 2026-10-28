"""核对新回归的时间约束、重建公式及预测口径。"""
import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np

SRC = Path(__file__).resolve().parents[1]/'src'
sys.path.insert(0, str(SRC))
spec = importlib.util.spec_from_file_location('step06', SRC/'06_linear_regression.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class LinearProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data = module.load_features()

    def test_features_identical_to_saved_current_experiment(self):
        import pandas as pd
        saved = pd.read_csv(SRC.parent/'results/step06/features.csv')
        np.testing.assert_allclose(self.data[module.FEATURES], saved[module.FEATURES], atol=1e-12)

    def test_current_and_future_capacity_do_not_change_current_features(self):
        import pandas as pd
        from comparison_common import make_features
        raw = pd.read_csv(SRC.parent/'results/step01/battery_clean.csv')
        changed = raw.copy()
        changed.loc[(changed.battery_id == 'B0005')&(changed.cycle >= 135),'capacity_Ah'] = 999.
        transformed = make_features(changed)
        a = self.data[(self.data.battery_id == 'B0005')&(self.data.cycle <= 135)]
        b = transformed[(transformed.battery_id == 'B0005')&(transformed.cycle <= 135)]
        np.testing.assert_array_equal(a[module.FEATURES].to_numpy(), b[module.FEATURES].to_numpy())

    def test_feature_window_ends_before_target(self):
        import pandas as pd
        raw = pd.read_csv(SRC.parent/'results/step01/battery_clean.csv')
        for _, r in self.data.iterrows():
            history = raw[(raw.battery_id == r.battery_id)&(raw.cycle.between(r.cycle-5,r.cycle-1))]
            self.assertEqual(len(history), 5)
            self.assertAlmostEqual(r.lag1_Ah, history.iloc[-1].capacity_Ah)
            self.assertAlmostEqual(r.mean5_Ah, history.capacity_Ah.mean())
            self.assertAlmostEqual(r.slope5_Ah_per_cycle, np.polyfit(history.cycle,history.capacity_Ah,1)[0])

    def test_raw_coefficient_formula_matches_standardized_prediction(self):
        g = self.data[self.data.battery_id == 'B0005']
        train, test = g[g.split != 'test'], g[g.split == 'test']
        model = module.fit_linear(train)
        predicted = model['intercept_Ah']+test[module.FEATURES].to_numpy()@model['coefficients_raw']
        np.testing.assert_allclose(predicted, module.predict_linear(model, test), atol=1e-12)
        self.assertEqual(model['fit_last_target'], 134)

    def test_estimators_fit_only_before_test_and_test_labels_do_not_affect_predictions(self):
        for _, g in self.data.groupby('battery_id'):
            train, test = g[g.split != 'test'], g[g.split == 'test']
            self.assertLess(train.cycle.max(), test.cycle.min())
            model = module.fit_linear(train)
            changed = test.copy(); changed['capacity_Ah'] = -999.
            np.testing.assert_array_equal(module.predict_linear(model,test),module.predict_linear(model,changed))


if __name__ == '__main__': unittest.main()
