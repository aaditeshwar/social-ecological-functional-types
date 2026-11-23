"""Offline tests for core_seft (no network)."""
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core_seft.present import present_interventions, present_mws, mws_diff, jsonable
from core_seft.types import AnalyseResult
from seft.interventions import load_interventions
from seft.stresses import load_graph, load_taxonomy
from seft.signals import load_signals
from seft.schemes import load_schemes
from seft.assess import load_questions


def sample_record():
    return {
        'uid': '12_313813', 'state': 'Jharkhand', 'district': 'Godda', 'tehsil': 'Basantrai',
        'tehsils': ['Basantrai', 'Mahagama'], 'area': 1324.47, 'n_villages': 8,
        'ctx': {'rainfall': 'humid', 'aquifer': 'alluvium', 'terrain': 'plain',
                'gw_category': 'semi_critical', 'canal': 'no_canal', 'cropping': 'intensive'},
        'env': {'f_crop': 0.5, 'rain_norm': 1200, 'rain_factor': 1.0, 'share_groundwater_irrigated': 0.5},
        'ind': {'f_crop': 0.5, 'precip_mean': 1100, 'rain_norm': 1200, 'n_canals': 0, 'swb_frac': 0.01,
                'f_forest': 0.1, 'f_commons': 0.05},
        'mix': {'shares': {'groundwater_irrigated': 0.5, 'rainfed_dryland': 0.2, 'forest_fringe': 0.3,
                           'rainfed_rice_subhumid': 0, 'canal_irrigated': 0, 'tank_irrigated': 0,
                           'tree_crops': 0, 'pastoral': 0, 'peri_urban': 0},
                'present': ['groundwater_irrigated', 'rainfed_dryland', 'forest_fringe'],
                'dominant': 'groundwater_irrigated', 'raw_total': 1.0},
        'mix0': {'shares': {'groundwater_irrigated': 0.5}, 'present': ['groundwater_irrigated'],
                 'dominant': 'groundwater_irrigated', 'raw_total': 1.0},
        'stress': {
            'groundwater.over_extraction': {
                'status': 'triggered', 'intensity': 72, 'severity': 'moderate', 'positive': True,
                'posterior': 0.81, 'band': 'confirmed', 'signals_on': ['s_soge_stage'], 'signals_unknown': [],
            },
            'soil.erosion': {
                'status': 'not applicable', 'intensity': None, 'positive': False,
                'signals_on': [], 'signals_unknown': [],
            },
        },
        'pathways': {
            'agriculture.water_security': {
                'status': 'triggered', 'intensity': 72, 'severity': 'moderate',
                'positive': ['groundwater.over_extraction'], 'posterior': 0.81, 'band': 'confirmed',
            }
        },
        'signals': {
            's_soge_stage': {'kind': 'stress', 'on': True, 'grade': 0.7, 'threshold': 0.7, 'basis': 'absolute'},
        },
        'schemes': [{'id': 'mgnrega_nrm', 'because': ['groundwater.over_extraction'], 'archetypes': ['groundwater_irrigated']}],
        'interventions': [
            {'id': 'loose_boulder_check', 'fit': 'possible', 'because': ['groundwater.recharge_opportunity'], 'side': 'supply'},
            {'id': 'farm_pond', 'fit': 'not suited', 'because': ['drought.kharif_drought'], 'side': 'supply'},
        ],
        'answers': {},
    }


class PresentTests(unittest.TestCase):
    def test_jsonable_nan(self):
        import math
        self.assertIsNone(jsonable(float('nan')))
        self.assertEqual(jsonable({'a': 1}), {'a': 1})

    def test_interventions_omit_not_suited(self):
        IV = load_interventions()
        rows = [
            {'id': 'loose_boulder_check', 'fit': 'suited', 'because': ['soil.erosion'], 'side': 'supply'},
            {'id': 'farm_pond', 'fit': 'not suited', 'because': ['drought.kharif_drought'], 'side': 'supply'},
        ]
        out = present_interventions(rows, IV)
        self.assertEqual([x['fit'] for x in out], ['suited'])
        self.assertTrue(out[0]['name'])
        self.assertIn('what', out[0])
        full = present_interventions(rows, IV, detail='full')
        self.assertEqual({x['fit'] for x in full}, {'suited', 'not suited'})

    def test_mws_envelope(self):
        r = sample_record()
        out = present_mws(
            r, load_graph(), load_taxonomy(), load_signals(), load_schemes(),
            load_questions(), load_interventions(),
            {'library': '0.1.0', 'knowledge': '0.1.0'},
        )
        self.assertIsInstance(out, AnalyseResult)
        d = out.to_dict()
        self.assertEqual(d['kind'], 'mws')
        self.assertEqual(d['uid'], '12_313813')
        self.assertEqual(d['mix']['dominant'], 'groundwater_irrigated')
        self.assertTrue(d['context']['rainfall'])
        self.assertTrue(d['schemes'])
        self.assertTrue(d['interventions'])
        self.assertNotIn('not suited', {i['fit'] for i in d['interventions']})
        self.assertTrue(d['notes'])
        self.assertTrue(d['questions'])
        self.assertIn('must_ask', d['questions'][0])
        self.assertIn(d['questions'][0]['must_ask']['band'], ('must', 'useful', 'skip'))
        scores = [q['must_ask']['score'] for q in d['questions'] if q.get('must_ask')]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(d['commons_connect'])
        self.assertTrue(any(q['form'] == 'landscape' for q in d['commons_connect']))
        self.assertIn('must_ask', d['commons_connect'][0])
        self.assertIn('labels', d['mix'])
        self.assertTrue(d['mix'].get('dominant_label'))
        self.assertIn('labels', d['context'])
        self.assertEqual(d['library_version'], '0.1.0')
        self.assertEqual(d['knowledge_version'], '0.1.0')

    def test_diff_detects_scheme_change(self):
        b = sample_record()
        a = sample_record()
        a['schemes'] = []
        a['interventions'] = [{'id': 'loose_boulder_check', 'fit': 'suited', 'because': [], 'side': 'supply'}]
        d = mws_diff(b, a)
        self.assertEqual(d['schemes_removed'], ['mgnrega_nrm'])
        self.assertIn('loose_boulder_check', d['interventions'])


class SessionOfflineTests(unittest.TestCase):
    def test_unknown_kind(self):
        from core_seft import Session, UnknownEntity
        s = Session(data_dir=str(REPO / 'data'), log=lambda *a, **k: None)
        with self.assertRaises(UnknownEntity):
            s.analyse('village', state='Jharkhand', district='Godda')

    def test_cache_miss(self):
        import tempfile
        from core_seft import Session, CacheMiss
        tmp = tempfile.mkdtemp()
        s = Session(data_dir=tmp, knowledge_dir=str(REPO / 'knowledge'), log=lambda *a, **k: None)
        with self.assertRaises(CacheMiss):
            s.analyse('district', state='Jharkhand', district='Godda', fetch=False)

    def test_analyse_cached_godda_mws(self):
        from seft.util import raw_dir, set_data_root, ROOT
        set_data_root(REPO / 'data')
        if not (raw_dir('Jharkhand', 'Godda', 'Basantrai') / 'lulc_vector.json').exists():
            self.skipTest('Godda cache not present')
        from core_seft import Session
        s = Session(data_dir=str(REPO / 'data'), knowledge_dir=str(REPO / 'knowledge'),
                    log=lambda *a, **k: None)
        r = s.analyse('mws', state='Jharkhand', district='Godda', uid='12_313813', fetch=False)
        self.assertEqual(r.kind, 'mws')
        self.assertEqual(r.uid, '12_313813')
        self.assertTrue(r.mix['dominant'])
        self.assertTrue(r.context)
        self.assertIsInstance(r.interventions, list)
        self.assertIsInstance(r.schemes, list)
        self.assertTrue(r.questions)
        self.assertIn('must_ask', r.questions[0])
        self.assertGreaterEqual(r.questions[0]['must_ask']['score'], r.questions[-1]['must_ask']['score'])
        self.assertTrue(r.commons_connect)
        self.assertTrue(any(q.get('form') == 'landscape' for q in r.commons_connect))
        self.assertTrue(any((q.get('must_ask') or {}).get('score') is not None for q in r.commons_connect))
        self.assertTrue(r.must_ask_summary.get('atlas'))
        r2 = s.analyse('mws', state='Jharkhand', district='Godda', uid='12_313813',
                       answers={'sys_irrigated_share': 'low'}, fetch=False)
        self.assertEqual(r2.answers_applied.get('sys_irrigated_share'), 'low')
        self.assertIsNotNone(r2.diff)

    def test_analyse_cached_godda_waterbody(self):
        from seft.util import raw_dir, set_data_root, ROOT
        set_data_root(REPO / 'data')
        if not (raw_dir('Jharkhand', 'Godda', 'Basantrai') / 'swb_layers.json.gz').exists():
            self.skipTest('Godda waterbody layers not present')
        from core_seft import Session
        s = Session(data_dir=str(REPO / 'data'), knowledge_dir=str(REPO / 'knowledge'),
                    log=lambda *a, **k: None)
        r = s.analyse('waterbody', state='Jharkhand', district='Godda', uid='9628377', fetch=False)
        self.assertEqual(r.kind, 'waterbody')
        self.assertTrue(r.questions)
        self.assertIn('must_ask', r.questions[0])
        self.assertTrue(any(q.get('form') == 'waterbody' for q in r.commons_connect))
        self.assertTrue(r.identity.get('type_label'))


if __name__ == '__main__':
    unittest.main()
