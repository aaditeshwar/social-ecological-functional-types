"""Turn the compact GeoServer layers (seft.wb.layers) into one record per waterbody.

Steps per tehsil:
1. Merge fragments (WB-01): records that share `area_ored` and the same yearly `area`, `k` and `krz`
   series, and whose bounding boxes lie within MERGE_GAP_DEG (about 30 m) of each other, are one waterbody.
   The merged waterbody takes `area_ored` as its area, the union of the fragments' MWS, the highest stream
   order and catchment, and is on a drainage line if any fragment is. Its id is the `wb_id` of the largest
   fragment; all fragment ids are kept.
2. Size floor: waterbodies below types.json `min_area_ha` are dropped.
3. Zone of influence (WB-02): where the zone layer carries `wb_id`, zones are joined on it. Otherwise a zone is
   matched by location: its centre within max(10 m, 10% of the waterbody's side) of the merged waterbody's
   centroid, and its radius within 25% of the radius expected for the waterbody's area (ZOI_CURVE, fitted on
   96,280 unambiguous pairs). `zoi_match` records 'wb_id', 'location' or 'none'.
4. Type: the first matching rule in knowledge/waterbody/types.json. `on_stream` is on a drainage line, or (for waterbodies of
   0.5 ha or more) a catchment 20 or more times the waterbody's area: channel-fed tanks off the mapped drainage line.
5. Home MWS: the MWS listed most often by the fragments (ties: the largest fragment's first MWS).
"""
import collections, gzip, json, math
from ..util import ROOT, load_json, raw_dir, iter_locations
from ..expr import evaluate
from .layers import LAYERS_FILE

MERGE_GAP_DEG = 0.0003
# (log10 of area in m2, expected radius in m): binned medians over the 73 sample tehsils
ZOI_CURVE = [(2.0, 27), (2.25, 46), (2.5, 63), (2.75, 104), (3.0, 144), (3.25, 210), (3.5, 357), (3.75, 426),
             (4.0, 501), (4.25, 580), (4.5, 658), (4.75, 739), (5.0, 815), (5.25, 901), (5.5, 978),
             (5.75, 1051), (6.0, 1132), (6.25, 1223), (6.5, 1314), (6.75, 1352)]
ZOI_RADIUS_TOL = 0.25

def expected_zoi_radius(area_ha):
    a = math.log10(max(area_ha, 1e-6) * 1e4)
    if a <= ZOI_CURVE[0][0]: return ZOI_CURVE[0][1]
    for (a0, r0), (a1, r1) in zip(ZOI_CURVE, ZOI_CURVE[1:]):
        if a <= a1: return r0 + (r1 - r0) * (a - a0) / (a1 - a0)
    return ZOI_CURVE[-1][1]

def _metres(a, b):
    return math.hypot((a[0] - b[0]) * 111320 * math.cos(math.radians(a[1])), (a[1] - b[1]) * 111320)

def _near(a, b, tol):
    return not (a[2] + tol < b[0] or b[2] + tol < a[0] or a[3] + tol < b[1] or b[3] + tol < a[1])

def merge_fragments(W, gap=MERGE_GAP_DEG):
    """Return lists of indices into W, one per merged waterbody."""
    by_series = collections.defaultdict(list)
    for i, w in enumerate(W):
        by_series[(w.get('area_ored'), tuple(w.get('area') or ()), tuple(w.get('k') or ()), tuple(w.get('krz') or ()))].append(i)
    groups = []
    for idx in by_series.values():
        parent = {i: i for i in idx}
        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]; i = parent[i]
            return i
        if len(idx) > 1:
            for a in range(len(idx)):
                for b in range(a + 1, len(idx)):
                    if _near(W[idx[a]]['bbox'], W[idx[b]]['bbox'], gap):
                        parent[find(idx[a])] = find(idx[b])
        comp = collections.defaultdict(list)
        for i in idx: comp[find(i)].append(i)
        groups.extend(comp.values())
    return groups

def _centroid(ws):
    try:
        from shapely.geometry import shape
        from shapely.ops import unary_union
        u = unary_union([shape(w['geom']) for w in ws if w.get('geom')])
        if not u.is_empty: return [round(u.centroid.x, 6), round(u.centroid.y, 6)]
    except Exception:
        pass
    b = ws[0]['bbox']; return [round((b[0] + b[2]) / 2, 6), round((b[1] + b[3]) / 2, 6)]

def _wid(w):
    return w.get('UID', w.get('wb_id'))

def merged_record(ws):
    big = max(ws, key=lambda w: w.get('total_area') or 0)
    mws = collections.Counter(m for w in ws for m in str(w.get('mws_uid_list') or '').split('|') if m)
    first = str(big.get('mws_uid_list') or '').split('|')[0]
    home = max(mws, key=lambda m: (mws[m], m == first)) if mws else None
    bb = [min(w['bbox'][0] for w in ws), min(w['bbox'][1] for w in ws), max(w['bbox'][2] for w in ws), max(w['bbox'][3] for w in ws)]
    return {
        'wb_id': _wid(big), 'fragment_ids': [_wid(w) for w in ws], 'n_fragments': len(ws),
        'area_ha': big.get('area_ored') or 0.0, 'fragments_area_ha': round(sum(w.get('total_area') or 0 for w in ws), 4),
        'wb_type': big.get('waterbody_type'), 'wb_name': big.get('waterbody_type_name'),
        'canal_project': big.get('project_name'),
        'has_drainage_fields': 'on_drainage_line' in big,
        'on_drainage': any(bool(w.get('on_drainage_line')) for w in ws),
        'stream_order': max((w.get('max_stream_order') or 0) for w in ws),
        'catchment_ha': max((w.get('max_catchment_area') or 0) for w in ws),
        'mws_uids': sorted(mws), 'n_mws': len(mws), 'home_mws': home,
        'villages': sorted({v.strip() for w in ws for v in str(w.get('covering_village_names') or '').split(',') if v.strip()}),
        'years': big.get('years'), 'water_area': big.get('area'), 'k': big.get('k'), 'kr': big.get('kr'), 'krz': big.get('krz'),
        'centroid': _centroid(ws), 'bbox': bb,
        'census_id': big.get('census_id'),
    }

def match_zoi(bodies, Z, has_wb_id):
    """Attach a zone of influence to each body in place. Returns counts."""
    stats = collections.Counter()
    if has_wb_id:
        zid = {str(z.get('wb_id')): z for z in Z}
        for b in bodies:
            z = next((zid[str(i)] for i in b['fragment_ids'] if str(i) in zid), None)
            b['zoi'] = z; b['zoi_match'] = 'wb_id' if z else 'none'; stats[b['zoi_match']] += 1
        return stats
    grid = collections.defaultdict(list)
    for bi, b in enumerate(bodies):
        grid[(round(b['centroid'][0], 2), round(b['centroid'][1], 2))].append(bi)
    got = {}
    for z in Z:
        zc = z.get('centre')
        if not zc: continue
        best = None
        for dx in (-0.02, -0.01, 0, 0.01, 0.02):
            for dy in (-0.02, -0.01, 0, 0.01, 0.02):
                for bi in grid.get((round(zc[0] + dx, 2), round(zc[1] + dy, 2)), ()):
                    b = bodies[bi]
                    if b['area_ha'] <= 0: continue
                    d = _metres(b['centroid'], zc); r = expected_zoi_radius(b['area_ha'])
                    if (abs((z.get('zoi') or 0) - r) <= ZOI_RADIUS_TOL * r and d <= max(10, 0.1 * math.sqrt(b['area_ha'] * 1e4))
                            and (best is None or d < best[0])):
                        best = (d, bi)
        if best and (best[1] not in got or best[0] < got[best[1]][0]):
            got[best[1]] = (best[0], z)
    for bi, b in enumerate(bodies):
        z = got.get(bi)
        b['zoi'] = z[1] if z else None; b['zoi_match'] = 'location' if z else 'none'; stats[b['zoi_match']] += 1
    return stats

def assign_type(b, types):
    env = {k: b[k] for k in ('area_ha', 'wb_type', 'on_drainage', 'stream_order', 'n_mws', 'has_drainage_fields')}
    env['catchment_ratio'] = (b['catchment_ha'] / b['area_ha']) if b['area_ha'] else 0
    env['on_stream'] = bool(b['on_drainage'] or (env['catchment_ratio'] >= 20 and b['area_ha'] >= 0.5))
    b['on_stream'] = env['on_stream']
    env['true'] = True
    for t in types['types']:
        if evaluate(t['when'], env): return t['id']
    return None

def build_tehsil(state, district, tehsil, types, log=print):
    p = raw_dir(state, district, tehsil) / LAYERS_FILE
    if not p.exists():
        log(f'  {district} / {tehsil}: no {LAYERS_FILE}; run wb-fetch first'); return [], {}
    with gzip.open(p, 'rt', encoding='utf-8') as f: doc = json.load(f)
    W = [w for w in doc['waterbodies'] if w.get('bbox')]
    bodies = [merged_record([W[i] for i in g]) for g in merge_fragments(W)]
    n_all = len(bodies)
    bodies = [b for b in bodies if b['area_ha'] >= types['min_area_ha']]
    zs = match_zoi(bodies, doc['zoi'], doc.get('zoi_has_wb_id'))
    for b in bodies:
        b.update(state=state, district=district, tehsil=tehsil, type=assign_type(b, types))
    stats = {'records': len(W), 'waterbodies': n_all, 'kept': len(bodies), **{f'zoi_{k}': v for k, v in zs.items()}}
    log(f'  {district} / {tehsil}: {len(W)} records -> {n_all} waterbodies, {len(bodies)} >= {types["min_area_ha"]} ha; '
        f'ZoI by wb_id {zs["wb_id"]}, by location {zs["location"]}, none {zs["none"]}')
    return bodies, stats

def build_all(cfg=None, kdir=None, log=print):
    cfg = cfg or load_json(ROOT / 'config' / 'waterbody' / 'locations.json')
    types = load_json((kdir or ROOT / 'knowledge' / 'waterbody') / 'types.json')
    out, stats = [], {}
    for s, d, t in iter_locations(cfg):
        b, st = build_tehsil(s, d, t, types, log=log); out.extend(b); stats[f'{d}/{t}'] = st
    return out, stats, types
