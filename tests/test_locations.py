"""Locations of the modules: registering in one module registers, as coverage, in the modules it depends on."""
import json, sys, tempfile, unittest
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import seft.util as U


class TestLocations(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()); self.old = U.ROOT; U.ROOT = self.tmp
        (self.tmp / 'config' / 'waterbody').mkdir(parents=True)
        (self.tmp / 'config' / 'locations.json').write_text(json.dumps({'districts': [
            {'state': 'S', 'district': 'P', 'tehsils': ['A', 'B'], 'roles': ['pools']}]}))

    def tearDown(self):
        U.ROOT = self.old

    def cfg(self, m):
        return json.loads(U.module_locations_path(m).read_text())

    def test_impact_cascades_to_waterbody_and_mws(self):
        U.register_locations('impact', {('S', 'P'): ['B', 'C'], ('S', 'Q'): ['X']}, 'test', log=lambda *a: None)
        imp = {d['district']: d for d in self.cfg('impact')['districts']}
        self.assertEqual(imp['P']['roles'], ['test'])
        wb = {d['district']: d for d in self.cfg('waterbody')['districts']}
        self.assertEqual(wb['Q']['roles'], ['coverage'])
        mws = {d['district']: d for d in self.cfg('mws')['districts']}
        self.assertEqual(mws['P']['tehsils'], ['A', 'B', 'C'])
        self.assertEqual(mws['P']['roles'], ['pools'])            # the pools district keeps its role
        self.assertEqual(mws['P']['coverage_tehsils'], ['C'])      # but C stays out of the sample
        self.assertEqual(mws['Q']['roles'], ['coverage'])
        cfg = self.cfg('mws')
        self.assertEqual(U.role_tehsils(cfg, 'pools'), {('S', 'P', 'A'), ('S', 'P', 'B')})
        self.assertIn(('S', 'P', 'C'), U.role_tehsils(cfg, 'coverage'))

    def test_sync_is_idempotent(self):
        U.register_locations('waterbody', {('S', 'Q'): ['X']}, 'coverage', log=lambda *a: None)
        self.assertEqual(U.sync_dependencies('waterbody', log=lambda *a: None), {'mws': 0})


if __name__ == '__main__':
    unittest.main()
