"""New farm ponds: the lined/unlined rule, the waterbody-note fields and the public notes (seft/impact/farmpond.py)."""
import unittest
from seft.impact import farmpond as F
from seft.impact.notes import rules
render = F.render

Y = list(range(2017, 2025))
DW = {y: 0 for y in Y}; DW[2018] = 6; DW[2022] = 5          # two drought years

class Lining(unittest.TestCase):
    def setUp(self):
        self.S = F.settings(); self.L = {**self.S['lining'], 'drought_weeks': self.S['drought']['min_weeks']}

    def test_lined(self):
        k = [0, 0, 0, 90, 92, 91, 90, 93]; s = F.lining(k, k, [0, 0, 0, 70, 75, 72, 70, 74], DW, 2020, Y, self.L)
        self.assertEqual(s['cls'], 'lined'); self.assertGreaterEqual(s['fill_ratio'], 0.9)

    def test_unlined(self):
        k = [0, 0, 60, 70, 65, 15, 60, 55]; s = F.lining(k, [0, 0, 40, 50, 40, 5, 40, 30], [0] * 8, DW, 2019, Y, self.L)
        self.assertEqual(s['cls'], 'unlined')

    def test_uncertain(self):
        k = [0, 0, 0, 80, 40, 85, 30, 80]; s = F.lining(k, k, [0, 0, 0, 30, 0, 25, 0, 20], DW, 2020, Y, self.L)
        self.assertEqual(s['cls'], 'uncertain')

    def test_note_fields(self):
        k = [0, 0, 0, 90, 92, 91, 90, 93]
        f = F.note_fields(k, k, [0, 0, 0, 70, 75, 72, 70, 74], 'farm_pond', DW, self.S)
        self.assertEqual((f['fp_lining'], f['fp_new'], f['fp_year_label']), ('lined', True, '2020-21'))
        self.assertFalse(F.note_fields(k, k, k, 'village_pond', DW, self.S)['fp_lining'])
        hw = F.note_fields(k, k, [0, 0, 0, 70, 75, 72, 70, 74], 'headwater_pond', DW, self.S)
        self.assertEqual((hw['fp_lining'], hw['fp_new']), ('', True))       # one category: no lined/unlined split
        old = F.note_fields([80, 20, 80, 80, 80, 20, 80, 80], [60] * 8, [0] * 8, 'farm_pond', DW, self.S)
        self.assertFalse(old['fp_new']); self.assertEqual(old['fp_lining'], 'unlined')

class Notes(unittest.TestCase):
    def test_pond_note(self):
        S = F.settings(); S['_last_main_year'] = S['years']['last_main']
        rec = {'type': 'farm_pond', 'verdict': 'likely_gain', 'E': 2020, 'tau': 0.05, 'n': 3, 'cls': 'lined',
               'sig': {'summer_area': 70.0, 'summer_years': 1.0, 'fill_ratio': 1.0}, 'main_years': [2020, 2021, 2022],
               'post_years': [2020, 2021, 2022, 2023, 2024], 'drought_main': None, 'flags': [],
               'effects': {o: {'main': 0.02, 'early': 0.03} for o in F.OUTS}}
        t = render('fp_waterbody', F.wb_env(rec, S, {'farm_pond': 'Farm pond'}, {'n': 40, 'unit': 'Jalna district', 'mean': 0.02, 'label': 'new farm ponds'}), rules())
        self.assertIn('first held water in 2020-21', t); self.assertIn('5.0 points', t); self.assertIn('lined pond', t)
        self.assertIn('Across 40 new farm ponds assessed in Jalna district', t); self.assertNotIn('{', t)

    def test_unit_and_old_notes(self):
        S = F.settings()
        st = {'n': 30, 'mean': 0.02, 'lo': 0.01, 'hi': 0.03, 'n_gain': 5, 'n_loss': 2, 'label': 'new farm ponds',
              'by_class': {'lined': {'n': 8, 'mean': 0.04}, 'unlined': {'n': 9, 'mean': -0.01}}, 'nk_mean': 0.01, 'n_early': 0}
        t = render('fp_unit', F.unit_env(st, 'Jalna district', S), rules())
        self.assertTrue(t.startswith('30 new farm ponds in Jalna district raised cropping intensity')); self.assertNotIn('{', t)
        o = render('fp_old', F.old_env({'gap': -0.05, 'premium': -0.09, 'corrected': 0.04}, 'farm_pond', {'farm_pond': 'Farm pond'}), rules())
        self.assertIn('+4.0 points may be due to the structure', o)

if __name__ == '__main__':
    unittest.main()

class Models(unittest.TestCase):
    def test_shipped_models(self):
        from seft.impact.model import load, predict_forest, FP_FEATURES
        m = load('farmpond')
        self.assertEqual(m['features'], FP_FEATURES)
        T = m['types']['farm_pond']; row = T['table'][0]
        p = predict_forest(T['trees'], [row[5:]])[0]
        self.assertTrue(-1 < p < 1); self.assertEqual(len(T['cuts']), 4); self.assertEqual(len(T['groups']), 5)
        d = load('desilting'); self.assertEqual(len(d['coef']), len(d['features'])); self.assertGreater(d['n'], 30)

class Suitability(unittest.TestCase):
    def test_rules(self):
        import json
        from core_seft.predict import suitability, _num_match
        from seft.util import knowledge_dir
        self.assertTrue(_num_match(25, '< 2 or > 20%')); self.assertFalse(_num_match(4, '1 or > 4')); self.assertTrue(_num_match(30, '≤ 30 m (on a drainage line)'))
        I = json.load(open(knowledge_dir() / 'interventions.json'))
        r = {x['structure']: x for x in suitability(I, {'slope_pct': 2, 'stream_order': 3, 'catchment_ha': 3, 'drainage_distance_m': 100,
                                                          'land_use': 'single kharif', 'soil_group': 'C'})}
        self.assertEqual(r['farm_pond']['verdict'], 'suitable')
        self.assertEqual(r['check_dam']['verdict'], 'not suitable')       # catchment 3 ha is too small for a check dam
        self.assertEqual(suitability(I, {}, ['farm_pond'])[0]['verdict'], 'unknown')
