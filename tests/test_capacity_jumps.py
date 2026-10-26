import importlib.util
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('jumps',ROOT/'src/01b_check_capacity_jumps.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class JumpTests(unittest.TestCase):
    def setUp(self):
        self.data=pd.read_csv(ROOT/'data/battery.csv')

    def test_preserve_original_and_only_treat_flagged(self):
        result,_=m.check_jumps(self.data)
        original=self.data.sort_values(['battery_id','cycle']).reset_index(drop=True)
        pd.testing.assert_frame_equal(result[original.columns],original)
        np.testing.assert_array_equal(result.loc[~result.extreme_flag,'capacity_treated_Ah'],result.loc[~result.extreme_flag,'capacity_Ah'])
        self.assertTrue((result.capacity_treated_Ah>0).all())
        self.assertTrue((~result.extreme_flag | result.review_flag).all())

    def test_heldout_changes_do_not_change_thresholds(self):
        _,a=m.check_jumps(self.data)
        changed=self.data.copy()
        changed.loc[(changed.battery_id=='B0005') & (changed.cycle>100),'capacity_Ah']+=1
        _,b=m.check_jumps(changed)
        cols=[c for c in a if c.endswith('_Ah') and c!='max_abs_adjustment_Ah']
        np.testing.assert_allclose(a[cols],b[cols])

    def test_known_extreme_and_nonrecursive_adjustment(self):
        df,summary=m.check_jumps(self.data)
        g=df[df.battery_id=='B0006'].set_index('cycle')
        upper=summary.set_index('battery_id').loc['B0006','extreme_upper_Ah']
        self.assertTrue(g.loc[90,'extreme_flag'])
        self.assertAlmostEqual(g.loc[90,'delta_Ah'],.1519)
        self.assertAlmostEqual(g.loc[90,'capacity_treated_Ah'],g.loc[89,'capacity_Ah']+upper)
        self.assertAlmostEqual(g.loc[92,'capacity_treated_Ah'],g.loc[92,'capacity_Ah'])

if __name__=='__main__': unittest.main()
