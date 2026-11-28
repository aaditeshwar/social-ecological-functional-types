"""Offline tests for the waterbody-impact module (synthetic waterbodies; no cache or network needed)."""
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from seft.impact import registry as REG
from seft.impact.pool import Pool
from seft.impact.estimate import Estimator
from seft.impact.run import assess_waterbody, note_env, type_labels
from seft.impact.notes import render

YEARS = list(range(2017, 2025))


def synthetic(n=400, treated=(), gain=0.0, seed=1):
    """n onstream tanks around one point. Every waterbody follows a shared year shock (2023 a drought) plus noise;
    the treated ones gain `gain` points of kharif, rabi and summer share from 2023."""
    rng = random.Random(seed)
    shock = {2017: 60, 2018: 20, 2019: 70, 2020: 85, 2021: 50, 2022: 75, 2023: 15, 2024: 80}
    B = []
    for i in range(n):
        base = rng.uniform(-10, 10)
        k, kr, krz = [], [], []
        for y in YEARS:
            g = gain if (i in treated and y >= 2023) else 0
            v = max(0, min(100, shock[y] + base + rng.gauss(0, 6)))
            k.append(round(v)); kr.append(round(max(0, min(v, v * 0.6 + g + rng.gauss(0, 4))))); krz.append(round(max(0, min(v, v * 0.2 + g / 2))))
        B.append({'wb_id': 1000 + i, 'type': 'onstream_tank', 'area_ha': rng.uniform(1, 20), 'catchment_ha': rng.uniform(50, 500),
                  'stream_order': rng.choice([2, 3, 4]), 'home_mws': f'm{i % 40}', 'centroid': [74.0 + rng.uniform(0, 0.15), 18.5 + rng.uniform(0, 0.15)],
                  'years': [str(y) for y in YEARS], 'k': k, 'kr': kr, 'krz': krz, 'state': 'S', 'district': 'D', 'tehsil': 'T'})
    ms = {f'm{j}': {'rain': {y: 700 + 30 * (j % 5) for y in YEARS}, 'drought': {y: 1 for y in YEARS}} for j in range(40)}
    return Pool(B, YEARS, {'onstream_tank'}, None, ms)


class TestImpact(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.S = REG.settings()
        cls.S['reference']['sample'] = 60

    def run_one(self, gain):
        P = synthetic(treated={0}, gain=gain)
        E = Estimator(P, self.S, {'1000': [2023]})
        return assess_waterbody(E, P.index['1000'], [{'year': 2023, 'volume_m3': 10000, 'ids': ['x'], 'quality_flags': []}],
                                self.S, type_labels()[0])[0]

    def test_detects_a_large_gain(self):
        r = self.run_one(gain=40)
        self.assertEqual(r['window'], 'single')
        self.assertEqual(r['post_years'], [2023, 2024])
        self.assertGreater(r['effects']['W']['did'], 5)
        self.assertEqual(r['verdict'], 'likely_gain')
        self.assertEqual(r['controls']['n'], self.S['matching']['n_controls'])

    def test_no_gain_is_not_a_gain(self):
        r = self.run_one(gain=0)
        self.assertIn(r['verdict'], ('no_change', 'inconclusive', 'likely_loss'))
        self.assertLess(abs(r['effects']['W']['did']), 6)

    def test_post_minus_pre_carries_the_drought(self):
        # 2023 is a drought year shared by all: the raw change is negative, the DiD is not
        r = self.run_one(gain=0)
        self.assertLess(r['effects']['W']['prepost_rain'] or -1, r['effects']['W']['did'] + 3)

    def test_not_assessable_without_post_years(self):
        P = synthetic(treated={0})
        E = Estimator(P, self.S, {'1000': [2025]})
        r = assess_waterbody(E, 0, [{'year': 2025, 'volume_m3': None, 'ids': ['x'], 'quality_flags': []}], self.S, {})[0]
        self.assertEqual(r['verdict'], 'not_assessable')

    def test_two_works_give_first_and_combined_windows(self):
        P = synthetic(treated={0}, gain=20)
        E = Estimator(P, self.S, {'1000': [2021, 2023]})
        recs = assess_waterbody(E, 0, [{'year': 2021, 'volume_m3': 1, 'ids': ['a'], 'quality_flags': []},
                                       {'year': 2023, 'volume_m3': 2, 'ids': ['b'], 'quality_flags': []}], self.S, {})
        self.assertEqual([r['window'] for r in recs], ['first', 'combined'])
        self.assertEqual(recs[0]['post_years'], [2021, 2022])
        self.assertEqual(recs[1]['pre_years'], [2017, 2018, 2019, 2020])
        self.assertEqual(recs[1]['post_years'], [2023, 2024])

    def test_controls_exclude_treated_in_window(self):
        P = synthetic(treated={0, 1})
        E = Estimator(P, self.S, {'1000': [2023], '1001': [2023]})
        C, _ = E.controls(0, list(range(6)), [6, 7])
        self.assertNotIn(P.index['1001'], C)
        E2 = Estimator(P, self.S, {'1000': [2023], '1001': [2025]})   # treated later: a valid control
        self.assertNotIn(P.index['1001'], E2._near_treated(2017, 2024))

    def test_note_renders(self):
        r = self.run_one(gain=40)
        wb = {'type': 'onstream_tank', 'area': 5.0}
        txt = render('waterbody', note_env(r, wb, self.S, type_labels()[0], {'n': 4, 'unit': 'D district', 'mean': 1.2}))
        self.assertIn('2023-24', txt); self.assertNotIn('{', txt)

    def test_registry_records_and_dedupe(self):
        fc = {'features': [
            {'geometry': {'type': 'Point', 'coordinates': [74.1, 18.6]}, 'properties': {'desilt_id': '7', 'intervention_year': '2023-24',
             'slit_excavated': '11400.0', 'desiltingpoint_lat': '18.6', 'desiltingpoint_lon': '74.1', 'State': 'Maharashtra',
             'District': 'Pune', 'Taluka': 'Maval', 'name_of_ngo': 'N/A'}}]}
        a = REG.records_from_layer(fc, 'waterbodies_atecf_mh_pune_189')
        b = REG.records_from_layer(fc, 'waterbodies_atecf_mh_pune_old')
        self.assertEqual(a[0]['year'], 2023); self.assertEqual(a[0]['volume_m3'], 11400.0); self.assertIsNone(a[0]['implementer'])
        kept = REG.dedupe(a + b)
        self.assertEqual(len(kept), 1); self.assertEqual(kept[0]['source']['also_in'], ['waterbodies_atecf_mh_pune_old'])

    def test_name_matching(self):
        self.assertEqual(REG._best('Maval', ['Mawal', 'Mulshi-Paud'])[0], 'Mawal')
        self.assertEqual(REG._best('Mulshi', ['Mawal', 'Mulshi-Paud'])[0], 'Mulshi-Paud')
        self.assertIsNone(REG._best('Purandar', ['Mawal', 'Mulshi-Paud'])[0])


if __name__ == '__main__':
    unittest.main()


def test_notes_panel_covers_page():
    from seft.impact.validate import panel_errors
    from seft.util import load_json, knowledge_dir
    assert panel_errors(load_json(knowledge_dir() / 'impact' / 'notes.json')) == []
