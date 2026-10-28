"""随机森林选参、模型持久化和时间外推边界检查。"""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
spec = importlib.util.spec_from_file_location('step07', ROOT/'src/07_random_forest.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class ForestProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.features = module.load_features()
        cls.metadata = json.loads((ROOT/'results/step07/forest_metadata.json').read_text())

    def test_grid_winner_is_minimum_validation_error(self):
        search = pd.read_csv(ROOT/'results/step07/validation_search.csv')
        for battery, g in search.groupby('battery_id'):
            self.assertEqual(len(g), 6)
            best = g.sort_values(['RMSE_Ah','candidate_order']).iloc[0]
            params = self.metadata[battery]['selected_parameters']
            self.assertEqual(params['min_samples_leaf'], best.min_samples_leaf)
            self.assertEqual(params['max_depth'], None if pd.isna(best.max_depth) else best.max_depth)

    def test_same_test_targets_as_linear_regression(self):
        linear = pd.read_csv(ROOT/'results/step06/predictions.csv')
        forest = pd.read_csv(ROOT/'results/step07/predictions.csv')
        linear = linear[linear.model == 'linear_ols'].sort_values(['battery_id','split','cycle'])
        forest = forest.sort_values(['battery_id','split','cycle'])
        self.assertEqual(linear[['battery_id','split','cycle']].values.tolist(), forest[['battery_id','split','cycle']].values.tolist())
        np.testing.assert_array_equal(linear.actual_Ah.to_numpy(), forest.actual_Ah.to_numpy())

    def test_saved_forests_reproduce_predictions_without_test_labels(self):
        saved = pd.read_csv(ROOT/'results/step07/predictions.csv')
        for battery, g in self.features.groupby('battery_id'):
            test = g[g.split == 'test'].copy(); test['capacity_Ah'] = -999
            estimator = joblib.load(ROOT/f'results/step07/{battery}_forest.joblib')
            predicted = estimator.predict(test[module.FEATURES])
            expected = saved[(saved.battery_id == battery)&(saved.split == 'test')]
            np.testing.assert_allclose(predicted, expected.predicted_Ah, atol=1e-12)
            self.assertLess(self.metadata[battery]['fit_last_target'], test.cycle.min())
            self.assertGreaterEqual(predicted.min()+1e-12, self.metadata[battery]['fit_capacity_min_Ah'])
            self.assertLessEqual(predicted.max()-1e-12, self.metadata[battery]['fit_capacity_max_Ah'])

    def test_candidate_order_and_seed_fixed(self):
        self.assertEqual(len(module.GRID), 6)
        model = module.make_forest(module.GRID[0])
        self.assertEqual(model.random_state, 25121619)
        self.assertEqual(model.n_estimators, 300)
        self.assertEqual(model.n_jobs, 1)


if __name__ == '__main__': unittest.main()
