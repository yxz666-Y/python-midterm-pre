"""第四步的关键约束：删失、阈值、外推未来隔离及误差方向。"""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('step04', ROOT/'src/04_evaluation_and_uncertainty.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class EvaluationTests(unittest.TestCase):
    def test_no_crossing_is_not_end_of_life(self):
        self.assertTrue(np.isnan(m.first_crossing([1, 2, 3], [2., 1.9, 1.8], 1.6)))
        self.assertEqual(m.first_crossing([1, 2, 3], [2., 1.6, 1.7], 1.6), 2)

    def test_undefined_rates_not_filled_with_success(self):
        scores = m.confusion([True, True], [True, False])
        self.assertEqual(scores['FN'], 1)
        self.assertTrue(np.isnan(scores['false_positive_rate']))
        self.assertTrue(np.isnan(m.confusion([False], [False])['recall']))

    def test_known_lifetime_trend(self):
        history = pd.DataFrame({'cycle': np.arange(1, 11),
                                'capacity_Ah': 2.-.01*np.arange(1, 11)})
        fit = m.fit_extrapolation(history, 1.6)
        self.assertAlmostEqual(fit['predicted_cross_cycle_continuous'], 40.)
        self.assertAlmostEqual(fit['predicted_remaining_cycles'], 30.)

    def test_flat_fit_and_already_crossed(self):
        flat = pd.DataFrame({'cycle': [1, 2, 3], 'capacity_Ah': [2., 2., 2.]})
        self.assertEqual(m.fit_extrapolation(flat, 1.6)['fit_status'], 'non_decreasing_fit')
        flat['capacity_Ah'] = [2., 1.5, 1.4]
        self.assertEqual(m.fit_extrapolation(flat, 1.6)['fit_status'], 'threshold_already_observed')

    def test_future_values_do_not_change_prefix_fit(self):
        raw = pd.DataFrame({'battery_id': ['X']*100, 'cycle': np.arange(1, 101),
                            'capacity_Ah': 2.-.005*np.arange(1, 101)})
        before = m.lifetime_sensitivity(raw).iloc[0]
        raw.loc[raw.cycle > 30, 'capacity_Ah'] = 1.0
        after = m.lifetime_sensitivity(raw).iloc[0]
        self.assertEqual(before.predicted_cross_cycle_continuous, after.predicted_cross_cycle_continuous)
        self.assertNotEqual(before.observed_first_cross_cycle, after.observed_first_cross_cycle)

    def test_crossing_before_test_has_no_event_lead(self):
        raw = pd.DataFrame({'battery_id': ['X']*10, 'cycle': np.arange(1, 11),
                            'capacity_Ah': [2., 1.9, 1.8, 1.7, 1.5, 1.4, 1.3, 1.2, 1.1, 1.]})
        pred = pd.DataFrame({'battery_id': ['X', 'X'], 'cycle': [9, 10],
                             'model': ['persistence']*2, 'actual_Ah': [1.1, 1.],
                             'predicted_Ah': [1.2, 1.1]})
        coverage, alerts = m.alert_analysis(raw, pred)
        self.assertEqual(coverage.first_cross_status.iloc[0], 'before_test')
        self.assertTrue(np.isnan(alerts.event_lead_cycles.iloc[0]))

    def test_positive_error_means_overestimate(self):
        pred = pd.DataFrame({'battery_id': ['X'], 'model': ['persistence'],
                             'actual_Ah': [1.5], 'predicted_Ah': [1.6]})
        result = m.error_summary(pred).iloc[0]
        self.assertAlmostEqual(result.bias_Ah, .1)
        self.assertEqual(result.overestimate_fraction, 1.)

    def test_event_lead_is_measured_from_information_time(self):
        raw = pd.DataFrame({'battery_id': ['X']*10, 'cycle': np.arange(1, 11),
                            'capacity_Ah': [2.]*8+[1.7, 1.5]})
        pred = pd.DataFrame({'battery_id': ['X']*2, 'cycle': [9, 10],
                             'model': ['persistence']*2, 'actual_Ah': [1.7, 1.5],
                             'predicted_Ah': [1.5, 1.4]})
        _, alerts = m.alert_analysis(raw, pred)
        # 第9次的预测在第8次测量后产生，首次跨越是第10次，提前量为2。
        self.assertEqual(alerts.event_lead_cycles.iloc[0], 2.)
        self.assertEqual(alerts.FP.iloc[0], 1)

    def test_saved_predictions_match_clean_data(self):
        raw = pd.read_csv(ROOT/'results/step01/battery_clean.csv')
        pred = pd.read_csv(ROOT/'results/step03/predictions.csv')
        m.validate_inputs(raw, pred)
        pred.loc[0, 'actual_Ah'] += .1
        with self.assertRaises(ValueError):
            m.validate_inputs(raw, pred)


if __name__ == '__main__':
    unittest.main()
