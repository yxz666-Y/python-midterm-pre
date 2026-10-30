"""核对第一步清洗结果：不做新的处理，只检查每一项约束是否真的成立。

读取data/battery.csv与results/step01的产物，逐条复核01_read_and_clean.py
声明的检查，包括字段、类型、缺失、重复、有效性与循环连续性。
"""
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT/'data/battery.csv'
CLEAN = ROOT/'results/step01/battery_clean.csv'
SUMMARY = ROOT/'results/step01/battery_summary.csv'
COLUMNS = ['battery_id', 'cycle', 'capacity_Ah', 'ambient_temp_C']


def load_raw():
    return pd.read_csv(RAW, encoding='utf-8-sig')


def load_clean():
    """统一排序后再检查，使结果与行顺序无关。"""
    return pd.read_csv(CLEAN, encoding='utf-8-sig').sort_values(
        ['battery_id', 'cycle']).reset_index(drop=True)


class CleanedDataTests(unittest.TestCase):
    def test_columns_row_count_and_batteries(self):
        clean = load_clean()
        self.assertEqual(list(clean.columns), COLUMNS)
        self.assertEqual(len(clean), 636)
        self.assertEqual(sorted(clean.battery_id.unique()),
                         ['B0005', 'B0006', 'B0007', 'B0018'])

    def test_no_missing_and_no_duplicate_records(self):
        clean = load_clean()
        self.assertEqual(int(clean.isna().sum().sum()), 0)
        self.assertEqual(int(clean.duplicated().sum()), 0)
        # 同一电池、同一循环不允许存在不同记录。
        self.assertEqual(int(clean.duplicated(['battery_id', 'cycle']).sum()), 0)

    def test_capacity_and_cycle_are_valid(self):
        clean = load_clean()
        values = clean[['cycle', 'capacity_Ah']].to_numpy(float)
        self.assertTrue(np.isfinite(values).all())
        self.assertTrue((clean.capacity_Ah > 0).all())
        self.assertTrue((clean.cycle >= 1).all())
        self.assertTrue((clean.cycle % 1 == 0).all())

    def test_each_battery_has_contiguous_cycles_from_one(self):
        clean = load_clean()
        counts = {}
        for battery, g in clean.groupby('battery_id'):
            cycles = g.sort_values('cycle').cycle.to_numpy()
            np.testing.assert_array_equal(cycles, np.arange(1, len(g)+1))
            counts[battery] = len(g)
        self.assertEqual(counts, {'B0005': 168, 'B0006': 168,
                                  'B0007': 168, 'B0018': 132})

    def test_cleaning_does_not_change_observed_values(self):
        clean = load_clean()
        raw = load_raw().sort_values(['battery_id', 'cycle']).reset_index(drop=True)
        pd.testing.assert_series_equal(clean.battery_id, raw.battery_id, check_dtype=False)
        np.testing.assert_array_equal(clean.cycle.to_numpy(), raw.cycle.to_numpy())
        np.testing.assert_allclose(clean.capacity_Ah, raw.capacity_Ah, rtol=0, atol=1e-12)
        np.testing.assert_allclose(clean.ambient_temp_C, raw.ambient_temp_C, rtol=0, atol=1e-12)

    def test_ambient_temperature_is_constant(self):
        clean = load_clean()
        np.testing.assert_array_equal(sorted(clean.ambient_temp_C.unique()), [24.])

    def test_summary_matches_recomputation_from_cleaned_rows(self):
        clean = load_clean()
        saved = pd.read_csv(SUMMARY, encoding='utf-8-sig').set_index('battery_id')
        loss = (1 - clean.groupby('battery_id').capacity_Ah.last()
                / clean.groupby('battery_id').capacity_Ah.first())*100
        rebound = (clean.groupby('battery_id').capacity_Ah.diff().gt(0)
                   .groupby(clean.battery_id).sum())
        for battery, g in clean.groupby('battery_id'):
            row = saved.loc[battery]
            self.assertEqual(int(row.records), len(g))
            self.assertAlmostEqual(float(row.first_capacity_Ah), float(g.capacity_Ah.iloc[0]))
            self.assertAlmostEqual(float(row.last_capacity_Ah), float(g.capacity_Ah.iloc[-1]))
            self.assertAlmostEqual(float(row.min_capacity_Ah), float(g.capacity_Ah.min()))
            self.assertAlmostEqual(float(row.max_capacity_Ah), float(g.capacity_Ah.max()))
            self.assertAlmostEqual(float(row.capacity_loss_pct), float(loss[battery]))
            self.assertEqual(int(row.rebound_count), int(rebound[battery]))


if __name__ == '__main__':
    unittest.main()
