"""Load cached CoRE Stack tehsil data into one record per micro-watershed (MWS).

Each MWS record is a dict of dataset aliases -> Namespace of columns. Annual columns become
numpy series aligned on YEARS; static columns stay scalars/strings. Village-level data are
apportioned to MWS by area of intersection (for MWS indicators) and also assigned by
maximum overlap (for village clusters).
"""
import json
import re
from collections import defaultdict
import numpy as np
from .util import raw_dir, load_json, ROOT
from .expr import Namespace, NAN
from .schema import normalise_row, village_row, live_key

YEARS = [str(y) for y in range(2017, 2025)]

ALIASES = {
    'lulc_vector': 'lulc', 'croppingintensity_annual': 'ci', 'croppingdrought_kharif': 'drought',
    'hydrological_annual': 'hydro', 'surfacewaterbodies_annual': 'swb', 'aquifer_vector': 'aquifer',
    'terrain': 'terrain', 'soge_vector': 'soge', 'restoration_vector': 'rest',
    'change_detection_degradation': 'degr', 'change_detection_tree_cover_decrease': 'tcd',
    'change_detection_tree_cover_increase': 'tci', 'change_detection_urbanization': 'urb',
    'nrega_annual': 'nrega', 'hydrological_seasonal': 'hseas',
}
# documented names of datasets that were renamed (CS-75); either file is read
RENAMED = {'change_detection_deforestation': 'change_detection_tree_cover_decrease',
           'change_detection_afforestation': 'change_detection_tree_cover_increase'}

# Newer flat datasets (one row per MWS or village, plain columns). Keys are lower-cased with spaces
# (and hyphens) replaced by '_'; columns ending in _YYYY or _YYYY-YYYY become series over the years present.
FLAT_MWS = {'soil_health': 'soil', 'forest_fringes': 'fringe', 'forest_fire': 'fire',
            'tree_in_grassland': 'tig', 'ndvi': 'ndvi', 'ndvi_shrub': 'ndvi'}
FLAT_VILLAGE = {'antyodaya': 'anty', 'facilities_proximity': 'fac'}
EXTRA_ALIASES = list(FLAT_MWS.values()) + list(FLAT_VILLAGE.values()) + ['river', 'conn']
_YR = re.compile(r'^(.*?)_((?:19|20)\d\d)(?:[-_]((?:19|20)?\d\d))?$')

def _key(k):
    return re.sub(r'[\s\-]+', '_', str(k).strip()).lower()

def flat_row(r, alias=None):
    """Normalise one flat row: lower-case keys, yearly columns -> numpy series (sorted by year)."""
    out, years = {}, defaultdict(dict)
    for k, v in r.items():
        kk = live_key(alias, _key(k))
        m = _YR.match(kk)
        if m and isinstance(v, (int, float, type(None))) and not isinstance(v, bool):
            years[m.group(1)][int(m.group(2))] = v
        else:
            out[kk] = v
    for base, d in years.items():
        ys = sorted(d)
        out[base] = np.array([NAN if d[y] is None else float(d[y]) for y in ys])
        out[base + '_years'] = ys
    return out

def _uid_of(r):
    for k in ('uid', 'UID', 'mws_uid', 'MWS_UID'):
        if r.get(k): return r[k]
    return (r.get('metadata') or {}).get('uid')

def _vid_of(r):
    for k in ('village_id', 'vill_id', 'censuscode2011', 'pc11_village_id', 'village_code', 'vill_ID', 'Village_ID'):
        v = r.get(k)
        if v not in (None, ''):
            try: return int(float(v))
            except (TypeError, ValueError): pass
    return None

def _count_list(v):
    if v is None: return 0
    if isinstance(v, list): return len(v)
    if isinstance(v, str):
        v = v.strip().strip('[]')
        return len([x for x in re.split(r'[,;\s]+', v) if x and x.lower() not in ('none', 'nan', 'null')])
    return 1

def _series(annual, col):
    t = annual.get('time') or []
    vals = annual.get(col)
    if vals is None: return None
    m = dict(zip([str(x) for x in t], vals))
    if col == 'monsoon_onset':
        return [m.get(y) for y in YEARS]
    return np.array([NAN if m.get(y) is None else float(m.get(y)) for y in YEARS])

def _read(p, name):
    f = p / f'{name}.json'
    if not f.exists(): return None
    return load_json(f)

def load_tehsil_bio(state, district, tehsil):
    """Biophysical records for every MWS listed in one tehsil's datasets."""
    p = raw_dir(state, district, tehsil)
    mws = defaultdict(lambda: {a: Namespace() for a in list(ALIASES.values()) + ['canal', 'gc', 'mine', 'vill', 'vtop', 'vmax'] + EXTRA_ALIASES})
    present = {}
    for ds, alias in ALIASES.items():
        d = _read(p, ds)
        if not d:
            alt = next((n for n, o in RENAMED.items() if o == ds), None)
            d = _read(p, alt) if alt else None
        present[alias] = bool(d and d['rows'])
        if not d: continue
        for r in d['rows']:
            uid, scal, ser = normalise_row(alias, r)
            if not uid: continue
            ns = mws[uid][alias]
            ns.update(scal); ns.update(ser)
            ns['n'] = 1
    # NREGA lists only MWS with works: an MWS absent from a returned dataset has no works (zero, not missing)
    if present.get('nrega'):
        for uid in mws:
            ns = mws[uid]['nrega']
            if 'n' not in ns:
                for c in ('soil_and_water_conservation', 'land_restoration', 'plantations', 'irrigation_on_farms',
                          'other_farm_works', 'off_farm_livelihood_assets', 'community_assets'):
                    ns[c] = np.zeros(len(YEARS))
                ns['n'] = 1; ns['imputed_zero'] = True
    # canals and green credit are one row per item
    for alias, ds in (('canal', 'canal'), ('gc', 'green_credit'), ('mine', 'mining')):
        d = _read(p, ds)
        if d is None and alias == 'mine':      # not fetched: unknown, not zero
            for uid in list(mws): mws[uid][alias]['n'] = NAN
            continue
        by = defaultdict(list)
        for r in (d or {}).get('rows', []):
            by[r.get('uid') or r.get('UID')].append({k: v for k, v in r.items() if k != 'kml_url'})   # strip presigned S3 URLs
        for uid in list(mws):
            items = by.get(uid, [])
            mws[uid][alias]['n'] = len(items)
            mws[uid][alias]['items'] = items
            if alias == 'canal':
                mws[uid][alias]['projects'] = sorted({i.get('project_name') for i in items if i.get('project_name')})
    # newer flat MWS datasets
    for ds, alias in FLAT_MWS.items():
        d = _read(p, ds)
        if not d: continue
        for r in d['rows']:
            uid = _uid_of(r)
            if not uid or uid not in mws: continue
            ns = mws[uid][alias]
            ns.update(flat_row({k: v for k, v in r.items() if k not in ('uid', 'UID')}, alias))
            ns['n'] = 1
        if alias == 'fire':      # fire detections are listed only where fires occurred
            for uid in mws:
                if 'fire_count_per_year' not in mws[uid]['fire']:
                    mws[uid]['fire']['fire_count_per_year'] = 0.0
    # rivers: one row per river reach crossing the MWS; connectivity: lists of upstream MWS
    d = _read(p, 'river')
    if d:
        cnt = defaultdict(int)
        for r in d['rows']:
            u = _uid_of(r)
            if u: cnt[u] += 1
        for uid in mws: mws[uid]['river']['n'] = cnt.get(uid, 0)
    d = _read(p, 'mws_connectivity')
    if d:
        for r in d['rows']:
            u = _uid_of(r)
            if u in mws:
                rr = flat_row(r)
                mws[u]['conn'].update(rr)
                mws[u]['conn']['n_upstream'] = _count_list(r.get('upstream_mws'))
                mws[u]['conn']['n_downstream'] = _count_list(r.get('downstream_mws'))
    out = {}
    for uid, rec in mws.items():
        a = rec['lulc'].get('area') or rec['terrain'].get('area') or rec['aquifer'].get('area') or rec['ci'].get('area')
        if a is None:          # listed only in an auxiliary dataset (e.g. water bodies): not part of this tehsil
            continue
        # surface water bodies: an MWS absent from the dataset has no water body (treated as zero)
        if present['swb'] and 'total_area' not in rec['swb']:
            for c in ('total_area', 'kharif_area', 'rabi_area', 'zaid_area'):
                rec['swb'][c] = np.zeros(len(YEARS))
            rec['swb']['total_swb_area'] = 0.0
            rec['swb']['imputed_zero'] = True
        rec['uid'] = uid; rec['area'] = float(a)
        out[uid] = rec
    return out

def load_tehsil_villages(state, district, tehsil):
    p = raw_dir(state, district, tehsil)
    inter = _read(p, 'mws_intersect_villages')
    soc = _read(p, 'social_economic_indicator')
    lv = _read(p, 'livestock')
    for D in (inter, soc, lv):
        if D: D['rows'] = [village_row(r) for r in D['rows']]
    socd = {int(r['village_id']): r for r in (soc or {}).get('rows', []) if r.get('village_id') is not None}
    lvd = {int(r['village_id']): r for r in (lv or {}).get('rows', [])
           if r.get('village_id') is not None and r.get('data_availability_status') == 'matched'}
    pairs = []   # (mws, village, area_ha)
    for r in (inter or {}).get('rows', []):
        vd = r.get('village_details') or {}
        if isinstance(vd, str):                      # v1: "{580399: {'area_intersect': 56.9, ...}, ...}"
            import ast
            try: vd = ast.literal_eval(vd)
            except (ValueError, SyntaxError): vd = {}
        if isinstance(vd, dict) and 'keys' not in vd:
            vd = {'keys': [str(k) for k in vd], 'values': list(vd.values())}
        for k, v in zip(vd.get('keys', []), vd.get('values', [])):
            pairs.append((r['mws_uid'], int(k), float(v.get('area_intersect') or 0)))
    flat = {}
    for ds, alias in FLAT_VILLAGE.items():
        d = _read(p, ds)
        flat[alias] = {}
        for r in (d or {}).get('rows', []):
            vid = _vid_of(r)
            if vid is None: continue
            row = flat_row(r, alias)
            if alias == 'anty':
                # FPO / PACS availability is text; turn it into counts that apportion like households.
                # A blank answer in a village that answered the survey is read as "neither" (7,493 of the
                # 9,340 surveyed sample villages are blank; see 'To verify' in the API issues log).
                fp = r.get('availability_of_fpos_pacs')
                if isinstance(fp, str) and fp.strip():
                    row['fpo_known'] = 1.0
                    row['fpo_available'] = 1.0 if fp.strip().lower() in ('fpo', 'both') else 0.0
                    row['fpo_text'] = fp.strip()
                elif r.get('total_hhd') not in (None, 0):
                    row['fpo_known'] = 1.0; row['fpo_available'] = 0.0
            flat[alias][vid] = row
    villages = {}
    for v in {v for _, v, _ in pairs}:
        s, l = socd.get(v, {}), lvd.get(v)
        villages[v] = {
            'village_id': v, 'name': s.get('village_name') or (l or {}).get('village_name'), 'tehsil': tehsil,
            'pop': s.get('total_population'), 'sc': s.get('total_sc_population'),
            'st': s.get('total_st_population'), 'literacy': s.get('literacy_rate'),
            'livestock': None if l is None else {k: l.get(k) for k in (
                'all_livestock_total', 'cattle_total', 'buffalo_total', 'sheep_total', 'goat_total', 'pig_total',
                'large_animals_total', 'small_animals_total')},
            'anty': flat['anty'].get(v), 'fac': flat['fac'].get(v),
        }
    return pairs, villages

def load_district(state, district, tehsils):
    """Merge tehsils. An MWS that straddles tehsils appears in each tehsil's API response, sometimes
    with different values (CS-63); the copy from its 'home' tehsil (largest village overlap) is used
    and the others are recorded in rec['tehsils']."""
    copies = defaultdict(dict)
    pairs, villages = [], {}
    for t in tehsils:
        for uid, rec in load_tehsil_bio(state, district, t).items():
            copies[uid][t] = rec
        pr, vl = load_tehsil_villages(state, district, t)
        pairs += pr; villages.update(vl)
    pairs = list({(m, v): (m, v, a) for m, v, a in pairs}.values())
    teh_area = defaultdict(lambda: defaultdict(float))
    for m, v, a in pairs:
        teh_area[m][villages[v]['tehsil']] += a
    mws = {}
    for uid, cp in copies.items():
        ta = teh_area.get(uid, {})
        home = max(cp, key=lambda t: (ta.get(t, 0), t == next(iter(cp))))
        rec = cp[home]
        rec['tehsil'] = home; rec['tehsils'] = sorted(cp)
        rec['state'], rec['district'] = state, district
        rec['vill'] = Namespace()
        mws[uid] = rec
    clusters = _apportion(mws, pairs, villages)
    return mws, villages, clusters

def _apportion(mws, pairs, villages):
    vtot = defaultdict(float)
    for m, v, a in pairs: vtot[v] += a
    for v in villages: villages[v]['area_ha'] = round(vtot.get(v, 0), 2)
    best = {}
    for m, v, a in pairs:
        if m in mws and (v not in best or a > best[v][1]): best[v] = (m, a)
    clusters = defaultdict(list)
    for v, (m, a) in best.items():
        villages[v]['mws'] = m
        villages[v]['overlap_share'] = round(a / vtot[v], 3) if vtot[v] else None
        clusters[m].append(v)
    agg = defaultdict(lambda: defaultdict(float))
    flat_agg = defaultdict(lambda: {'anty': {}, 'fac': {}})
    for m, v, a in pairs:
        if not vtot[v] or m not in mws: continue
        w = a / vtot[v]; V = villages[v]; g = agg[m]
        g['area_villages'] += a
        if V['pop'] is not None:
            g['area_social'] += a
            g['pop'] += w * V['pop']; g['sc'] += w * (V['sc'] or 0); g['st'] += w * (V['st'] or 0)
            if V['literacy'] is not None:
                g['lit_x_pop'] += w * V['pop'] * V['literacy']; g['pop_lit'] += w * V['pop']
        if V['livestock'] is not None:
            g['area_livestock'] += a
            for k in ('cattle_total', 'buffalo_total', 'sheep_total', 'goat_total', 'pig_total', 'all_livestock_total'):
                g[k] += w * (V['livestock'].get(k) or 0)
        # Mission Antyodaya: household counts apportioned by area; facilities: area-weighted mean distance
        for alias in ('anty', 'fac'):
            row = V.get(alias)
            if not row: continue
            fa = flat_agg[m][alias]
            fa['area_covered'] = fa.get('area_covered', 0.0) + a
            for k, x in row.items():
                if isinstance(x, bool) or not isinstance(x, (int, float)) or x != x: continue
                if alias == 'anty':
                    fa[k] = fa.get(k, 0.0) + w * x
                else:
                    fa[k] = fa.get(k, 0.0) + a * x
                    fa['_w_' + k] = fa.get('_w_' + k, 0.0) + a
    for m, rec in mws.items():
        for alias in ('anty', 'fac'):
            fa = flat_agg.get(m, {}).get(alias, {})
            ns = rec[alias] if alias in rec else rec.setdefault(alias, Namespace())
            ns['area_covered'] = fa.get('area_covered', 0.0)
            for k, x in fa.items():
                if k.startswith('_w_') or k == 'area_covered': continue
                if alias == 'fac':
                    w = fa.get('_w_' + k, 0.0)
                    ns[k] = x / w if w > 0 else NAN
                else:
                    ns[k] = x
        g = agg.get(m, {}); ns = rec['vill']
        cov_s = g.get('area_social', 0.0); cov_l = g.get('area_livestock', 0.0)
        ns['area_villages'] = g.get('area_villages', 0.0)
        ns['area_social'] = cov_s; ns['area_livestock'] = cov_l
        for k in ('pop', 'sc', 'st'): ns[k] = g.get(k, 0.0) if cov_s else NAN
        ns['literacy'] = g['lit_x_pop'] / g['pop_lit'] if g.get('pop_lit') else NAN
        for k in ('cattle_total', 'buffalo_total', 'sheep_total', 'goat_total', 'pig_total', 'all_livestock_total'):
            ns[k.replace('_total', '')] = g.get(k, 0.0) if cov_l else NAN
        ns['n_villages'] = len(clusters.get(m, []))
    _village_extremes(mws, pairs, villages)
    return dict(clusters)

def _village_extremes(mws, pairs, villages):
    """Per MWS, the village with the largest intersecting area ('vtop') and the largest livestock count
    over all intersecting villages ('vmax'). The Signal_Verification sheet reads village data this way
    (seft/sheet.py); the atlas itself apportions villages by area."""
    best, lmax = {}, defaultdict(lambda: NAN)
    for m, v, a in pairs:
        if m not in mws: continue
        if m not in best or a > best[m][1]: best[m] = (v, a)
        L = villages[v].get('livestock')
        if L:
            lg, sm = L.get('large_animals_total'), L.get('small_animals_total')
            if lg is None and sm is None:
                lg = (L.get('cattle_total') or 0) + (L.get('buffalo_total') or 0)
                sm = (L.get('sheep_total') or 0) + (L.get('goat_total') or 0) + (L.get('pig_total') or 0)
            score = 3 * (lg or 0) + (sm or 0)
            cur = lmax[m]
            lmax[m] = score if cur != cur else max(cur, score)
    for m, rec in mws.items():
        top = rec.setdefault('vtop', Namespace()); mx = rec.setdefault('vmax', Namespace())
        mx['livestock_units_sheet'] = lmax[m]
        if m not in best: continue
        v, a = best[m]; V = villages[v]
        top['village_id'] = v; top['area_intersect'] = a
        pop = V.get('pop')
        try: pop = float(pop)
        except (TypeError, ValueError): pop = NAN
        for k in ('st', 'sc'):
            try: top[k + '_pct'] = 100 * float(V.get(k)) / pop if pop and pop == pop else NAN
            except (TypeError, ValueError): top[k + '_pct'] = NAN
        try: top['literacy'] = float(V.get('literacy'))
        except (TypeError, ValueError): top['literacy'] = NAN
        an = V.get('anty') or {}; fa = V.get('fac') or {}
        def num(x):
            try: return float(x)
            except (TypeError, ValueError): return NAN
        top['total_hhd'] = num(an.get('total_hhd')); top['shg_hhd'] = num(an.get('total_hhd_mobilized_into_shg'))
        top['fpo_text'] = an.get('fpo_text') or ''
        top['bank_km'] = num(fa.get('bank_branch_distance_in_km')); top['coop_km'] = num(fa.get('cooperative_cat_distance_in_km'))
