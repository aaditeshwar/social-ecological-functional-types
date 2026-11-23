"""Offline end-to-end test of the scripts used for new locations.

Starts a mock CoRE Stack server (API + GeoServer WFS) that serves a synthetic district built on the
watershed geometry of Basantrai tehsil (Godda), copies the repository to a temporary folder, and runs

    seft.cli add  ->  fetch  ->  audit  ->  validate  ->  run --merge

against it. The mock cuts the lulc_vector response short, so the GeoServer back-fill is exercised too.
It checks that the new district lands in web/data next to the eight sample districts.

    python tests/test_offline.py
"""
import json, math, os, random, shutil, subprocess, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from seft.geo import decode   # noqa: E402

STATE, DISTRICT, TEHSIL = 'Teststate', 'Testpur', 'Demo'
YEARS = [str(y) for y in range(2017, 2025)]
rnd = random.Random(1)

def build_world():
    G = json.loads((REPO / 'data' / 'geo' / 'geometry_raw.json').read_text())['godda/basantrai']
    mws = {}
    for uid, enc in G['mws'].items():
        rings = decode(enc)
        if rings and len(rings[0]) >= 4:
            mws['99_' + uid.split('_')[1]] = rings[0]
    vill = [[900000 + i, f'Village {i}', v[2] / 1e4, v[3] / 1e4] for i, v in enumerate(G['vill'])]
    return mws, vill

MWS, VILL = build_world()

def ring_area_ha(r):
    lat = sum(p[1] for p in r) / len(r)
    a = 0.5 * abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1])))
    return a * 111.32 ** 2 * math.cos(math.radians(lat)) * 100

def ser(lo, hi):
    return [round(rnd.uniform(lo, hi), 2) for _ in YEARS]

def annual(uid, cols, meta=None):
    return {'metadata': {'uid': uid, **(meta or {})}, 'annual': {'time': YEARS, **cols}}

def documented(uid, cols, agri_year=True, scalars=None):
    """A row in the documented schema (API metadata, Nov 2026): flat, UID, year-suffixed columns."""
    r = {'UID': uid, **(scalars or {})}
    for c, vals in cols.items():
        for y, v in zip(YEARS, vals):
            r[f'{c}_{y}-{int(y) + 1}' if agri_year else f'{c}_{y}'] = v
    return r

def lulc_cols(a):
    f = lambda lo, hi: [round(a * v, 2) for v in ser(lo, hi)]
    return {'barrenlands_area': f(0, .03), 'built-up_area': f(.02, .06), 'cropland_area': f(0, 0),
            'doubly_cropped_area': f(.2, .4), 'triply_cropped_area': f(0, .02), 'tree_forest_area': f(.1, .3),
            'shrub_scrub_area': f(.02, .1), 'single_kharif_cropped_area': f(.1, .3),
            'single_non_kharif_cropped_area': f(0, .05), 'k_water_area': f(0, .01), 'kr_water_area': f(0, .01),
            'krz_water_area': f(0, .005)}

def dataset(name):
    rows = []
    for uid, ring in MWS.items():
        a = round(ring_area_ha(ring), 2)
        if name == 'lulc_vector':
            rows.append(annual(uid, lulc_cols(a), {'area': a}))
        elif name == 'croppingintensity_annual':
            rows.append(annual(uid, {'cropping_intensity': ser(.9, 1.6), 'doubly_cropped_area': ser(50, 200),
                                     'single_cropped_area': ser(50, 200), 'single_kharif_cropped_area': ser(40, 180),
                                     'single_non_kharif_cropped_area': ser(0, 20), 'triply_cropped_area': ser(0, 5)},
                               {'area': a, 'sum_area': a * .7}))
        elif name == 'croppingdrought_kharif':      # documented schema
            rows.append(documented(uid, {'Mild_in_weeks': ser(0, 4), 'Moderate_in_weeks': ser(0, 3), 'Severe_in_weeks': ser(0, 2),
                                         'drysp_unit_4_weeks': ser(0, 4), 'kharif_cropped_sqkm': ser(0.6, 1.0),
                                         'monsoon_onset': [f'{y}-6-{rnd.randint(5, 25)}' for y in YEARS]}, agri_year=False))
        elif name == 'hydrological_annual':         # documented schema
            rows.append(documented(uid, {'Precipitation_in_mm': ser(900, 1600), 'ET_in_mm': ser(600, 1000), 'RunOff_in_mm': ser(100, 400),
                                         'DeltaG_in_mm': ser(-150, 120), 'WellDepth_in_m': ser(-5, 4), 'G_in_mm': ser(-100, 100)}))
        elif name == 'surfacewaterbodies_annual':
            if rnd.random() < .6:
                rows.append(annual(uid, {'total_area': ser(2, 10), 'kharif_area': ser(2, 10), 'rabi_area': ser(1, 6),
                                         'zaid_area': ser(0, 2)}, {'total_swb_area': 5}))
        elif name == 'aquifer_vector':
            rows.append({'UID': uid, 'area_in_ha': a, 'aquifer_class': 'Hard Rock', 'principle_aq_Granite_percent': 70,
                         'principle_aq_Basalt_percent': 30})
        elif name == 'terrain':
            rows.append({'UID': uid, 'area_in_ha': a, 'terrain_description': 'Mostly Plains', 'plain_area_percent': 70,
                         'slopy_area_percent': 15, 'hill_slope_area_percent': 10, 'ridge_area_percent': 5})
        elif name == 'soge_vector':
            rows.append({'UID': uid, 'class_name': 'Safe', 'soge_dev_percent': 35.0})
        elif name == 'restoration_vector':
            rows.append({'uid': uid, 'wide_scale_restoration_area': a * .1, 'mosaic_restoration_area': a * .3, 'protection_area': 0})
        elif name == 'change_detection_degradation':
            rows.append({'uid': uid, 'total_degradation_area': a * .02, 'farm_to_barren_area': a * .01, 'farm_to_scrub_land_area': a * .01})
        elif name in ('change_detection_deforestation', 'change_detection_tree_cover_decrease'):   # documented columns
            rows.append({'UID': uid, 'total_deforestation_area_in_ha': a * .03, 'forest_to_farm_area_in_ha': a * .02})
        elif name in ('change_detection_afforestation', 'change_detection_tree_cover_increase'):
            rows.append({'UID': uid, 'total_afforestation_area_in_ha': a * .02})
        elif name == 'change_detection_urbanization':
            rows.append({'uid': uid, 'total_urbanization_area': a * .01, 'tree_farm_to_built_up_area': a * .01})
        elif name == 'soil_health':
            r = {'UID': uid, 'area_in_ha': a}
            for nut, lo, hi, unit in (('N', 150, 400, 'kg_per_ha'), ('P', 5, 30, 'kg_per_ha'), ('K', 80, 300, 'kg_per_ha'), ('OC', .2, .9, 'percent')):
                base = rnd.uniform(lo, hi)
                for i, q in enumerate((5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95)):
                    r[f'{nut}_p{q:02d}_in_{unit}'] = round(base * (0.6 + 0.08 * i), 3)
            rows.append(r)
        elif name == 'nrega_annual':
            r = {'UID': uid}
            for y in range(2018, 2024):
                for c in ('Community assets', 'Soil and water conservation', 'Irrigation on farms', 'Plantations'):
                    r[f'{c}_count_{y}'] = rnd.randint(0, 12)
            rows.append(r)
        elif name == 'river' and rnd.random() < .4:
            rows.append({'UID': uid, 'river_name': 'Test river'})
        elif name == 'mws_connectivity':
            others = [u for u in MWS if u != uid]
            rows.append({'UID': uid, 'direction': 1, 'downstream_mws': others[0], 'upstream_mws': ','.join(rnd.sample(others, rnd.randint(0, 2)))})
        elif name == 'forest_fringes' and rnd.random() < .5:
            rows.append({'UID': uid, 'forest_fringe_area_in_ha': 20.0, 'tree_deforestation_fringe_area_in_ha': rnd.uniform(0, 2),
                         'tree_degradation_fringe_area_in_ha': rnd.uniform(0, 2), 'mws_area_in_ha': a})
        elif name == 'forest_fire' and rnd.random() < .5:
            rows.append({'UID': uid, 'fire_count_per_year': rnd.randint(0, 6), 'fire_frp_mean_in_MW': 10.0})
        elif name == 'tree_in_grassland' and rnd.random() < .7:
            rows.append({'UID': uid, 'shrubs_trees_area_in_ha': 30.0, 'tree_loss_in_tree_in_shrub_area_in_ha': rnd.uniform(0, 5)})
        elif name == 'ndvi':
            rows.append({'UID': uid, 'shrub_mean': .3, 'shrub_slope': rnd.uniform(-.01, .01), 'crop_slope': 0.0})
        elif name == 'mws_intersect_villages':
            cx = sum(p[0] for p in ring) / len(ring); cy = sum(p[1] for p in ring) / len(ring)
            near = sorted(VILL, key=lambda v: (v[2] - cx) ** 2 + (v[3] - cy) ** 2)[:3]
            rows.append({'mws_uid': uid, 'area': a, 'village_details': {'keys': [str(v[0]) for v in near],
                         'values': [{'area_intersect': a * w, 'percentage_of_area': w * 100} for w in (.5, .3, .2)]}})
    if name == 'social_economic_indicator':
        rows = [{'village_id': v[0], 'village_name': v[1], 'total_population_count': rnd.randint(300, 4000),
                 'total_SC_population_count': rnd.randint(0, 300), 'total_ST_population_count': rnd.randint(0, 900),
                 'literacy_rate_percent': round(rnd.uniform(40, 70), 2)} for v in VILL]
    if name == 'livestock':
        rows = [{'village_id': v[0], 'village_name': v[1], 'data_availability_status': 'matched',
                 'all_livestock_total': 0, 'cattle_total': rnd.randint(50, 600), 'buffalo_total': rnd.randint(0, 100),
                 'sheep_total': rnd.randint(0, 200), 'goat_total': rnd.randint(0, 400), 'pig_total': rnd.randint(0, 50)} for v in VILL]
    if name == 'antyodaya':
        rows = []
        for v in VILL:
            h = rnd.randint(80, 900)
            rows.append({'village_id': v[0], 'village_name': v[1], 'total_hhd': h, 'total_hhd_mobilized_into_shg': int(h * rnd.uniform(.05, .7)),
                         'total_hhd_having_piped_water_connection': int(h * rnd.uniform(0, .9)),
                         'total_hhd_with_kuccha_wall_kuccha_roof': int(h * rnd.uniform(0, .6)),
                         'total_hhd_source_of_minor_forest_production': int(h * rnd.uniform(0, .4))})
    if name == 'facilities_proximity':
        rows = [{'village_id': v[0], 'village_name': v[1], 'bank_branch_distance_in_km': round(rnd.uniform(.5, 14), 2),
                 'financial_inclusion_cat_distance_in_km': round(rnd.uniform(.2, 8), 2)} for v in VILL]
    if name == 'green_credit':
        rows = [{'uid': next(iter(MWS)), 'project_name': 'Test plantation', 'kml_url': 'https://example.invalid/secret?X-Amz-Signature=abc'}]
    return rows

def square(x, y, d=0.004):
    return {'type': 'Polygon', 'coordinates': [[[x - d, y - d], [x + d, y - d], [x + d, y + d], [x - d, y + d], [x - d, y - d]]]}

CALLS = []

ALL_DATASETS = [d['name'] if isinstance(d, dict) else d for d in
                (lambda c: c.get('datasets', c))(json.loads((REPO / 'config' / 'datasets.json').read_text()))]

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, obj, status=200):
        b = json.dumps(obj).encode(); self.send_response(status)
        self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        CALLS.append(u.path)
        if u.path.startswith('/api/v2/get_tehsil_data'):
            if self.headers.get('X-API-Key') != 'test-key':
                return self._send({'detail': 'bad key'}, 401)
            if (q.get('district'), q.get('tehsil')) != (DISTRICT, TEHSIL):
                return self._send({'detail': 'not found'}, 404)
            # the client asks once per tehsil without a data filter (CS-83); a filter is still honoured
            names = q['data'].split(',') if 'data' in q else ALL_DATASETS
            td = {}
            for name in names:
                rows = dataset(name)
                if name == 'lulc_vector':
                    rows = rows[: len(rows) // 2]      # simulate a truncated dataset (CS-59)
                if rows: td[name] = rows               # empty datasets are left out, as the API does
            return self._send({'status': 'ok', 'data': {'tehsil_data': td,
                                                        'tehsil_units': {n: {} for n in td}}})
        if u.path.endswith('/wfs'):
            layer = q.get('typeName', '')
            if layer.startswith('crop_intensity:'):
                feats = []
                for r in dataset('croppingintensity_annual'):
                    uid = r['metadata']['uid']; P = {'uid': uid, 'sum': r['metadata']['sum_area'] * 1e4}
                    for c, vals in r['annual'].items():
                        if c != 'time':
                            for y, v in zip(YEARS, vals): P[f'{c}_{y}'] = v
                    feats.append({'type': 'Feature', 'properties': P,
                                  'geometry': {'type': 'Polygon', 'coordinates': [MWS[uid] + [MWS[uid][0]]]}})
                return self._send({'type': 'FeatureCollection', 'features': feats})
            if layer.startswith('panchayat_boundaries:'):
                return self._send({'type': 'FeatureCollection', 'features': [
                    {'type': 'Feature', 'properties': {'vill_ID': v[0], 'vill_name': v[1], 'TOT_P': 1000, 'P_SC': 100, 'P_ST': 50},
                     'geometry': square(v[2], v[3])} for v in VILL]})
            if layer.startswith('lulc_vector:'):
                feats = []
                for r in dataset('lulc_vector'):
                    uid = r['metadata']['uid']; P = {'uid': uid}
                    for c, vals in r['annual'].items():
                        if c != 'time':
                            for y, v in zip(YEARS, vals): P[f'{c}_{y}'] = v
                    feats.append({'type': 'Feature', 'properties': P,
                                  'geometry': {'type': 'Polygon', 'coordinates': [MWS[uid] + [MWS[uid][0]]]}})
                return self._send({'type': 'FeatureCollection', 'features': feats})
        self._send({'detail': 'unknown'}, 404)

def main():
    srv = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{srv.server_address[1]}'
    tmp = Path(tempfile.mkdtemp(prefix='seft_test_'))
    work = tmp / 'seft'
    shutil.copytree(REPO, work, ignore=shutil.ignore_patterns('__pycache__', 'raw', 'responses', 'tests'))
    env = dict(os.environ, CORE_STACK_API_KEY='test-key', CORE_STACK_API_BASE=base,
               CORE_STACK_GEOSERVER=base + '/geoserver', PYTHONPATH=str(work), NO_PROXY='127.0.0.1,localhost',
               no_proxy='127.0.0.1,localhost')
    loc = 'config/test_locations.json'
    def run(*args):
        print('$ python -m seft.cli', ' '.join(args))
        r = subprocess.run([sys.executable, '-m', 'seft.cli', *args], cwd=work, env=env, capture_output=True, text=True)
        print('  ' + (r.stdout + r.stderr).strip().replace('\n', '\n  '))
        if r.returncode: raise SystemExit(f'FAILED: {args}')
        return r.stdout
    try:
        run('add', '--locations', loc, '--state', STATE, '--district', DISTRICT, '--tehsils', TEHSIL)
        run('fetch', '--locations', loc)
        out = run('audit', '--locations', loc)
        assert '1 of 1 tehsils complete' in out, 'audit should report the back-filled tehsil as complete'
        run('validate')
        before = len(json.loads((work / 'web' / 'data' / 'index.json').read_text())['districts'])
        run('run', '--locations', loc, '--merge')
        idx = json.loads((work / 'web' / 'data' / 'index.json').read_text())
        names = [d['district'] for d in idx['districts']]
        assert DISTRICT in names and len(names) == before + 1, names
        b = json.loads((work / 'web' / 'data' / 'd_testpur.json').read_text())
        assert len(b['mws']) == len(MWS) and (work / 'web' / 'data' / 'd_testpur.js').exists()
        raw = work / 'data' / 'raw' / 'teststate' / 'testpur' / 'demo'
        lulc = json.loads((raw / 'lulc_vector.json').read_text())
        assert lulc['source'] == 'geoserver_backfill' and lulc['n_rows'] == len(MWS), 'lulc back-fill'
        assert 'kml_url' not in (raw / 'green_credit.json').read_text(), 'presigned URL must be stripped'
        vi = b['var_ids']; m0 = b['mws'][0]
        for v in ('dg_neg_frac', 'dr_modsev_mean', 'dry_spell_mean', 'kharif_cv', 'f_hill', 'soge_stage', 'forest_to_farm_frac',
                  'literacy', 'st_share', 'soil_n_low_frac', 'nrega_works_per_1000ha', 'shg_coverage', 'bank_distance_km', 'n_upstream'):
            assert any(m['i'][vi.index(v)] is not None for m in b['mws']), f'{v} is empty: schema mapping failed'
        print(f'\nOK: {len(MWS)} MWS fetched, lulc back-filled, atlas now has {len(names)} districts: {", ".join(names)}')
        print(f'Test copy kept at {work} (open web/index.html there to see the synthetic district).')
    finally:
        srv.shutdown()

if __name__ == '__main__':
    main()
