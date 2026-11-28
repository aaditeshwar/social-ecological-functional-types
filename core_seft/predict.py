"""predict_impact and site_suitability (Session methods; module-level wrappers in core_seft).

predict_impact uses the models shipped in core_seft/models (built by `impact-farmpond` and `impact-model`, see
seft/impact/model.py): for a new pond or tank, the forest fitted to the effects of the structures the atlas assessed,
with the fifth of structures the prediction falls in, what those structures showed, and the most similar assessed
structures; for desilting, the linear model of the effects of assessed works. Predictions describe how the
measured effects vary with the site: they rest on the causal estimates behind the model, but the site features are
associations, not causes.

site_suitability runs a site's values against the structure suitability rules in knowledge/interventions.json
(site_rules: slope, stream order, catchment, distance to drainage line, land use, hydrologic soil group).
"""
import math, re
import numpy as np

from .errors import UnknownEntity, CoreSeftError

# structure ids in knowledge/interventions.json -> waterbody types of the impact model
STRUCTURE_TYPES = {'farm_pond': 'farm_pond', 'five_percent_model': 'farm_pond', 'model_30_40': 'farm_pond',
                   'check_dam': 'headwater_pond', 'community_pond': 'village_pond', 'percolation_tank': 'small_onstream_pond'}
_MODELS = {}

def model(name):
    if name not in _MODELS:
        from seft.impact.model import load
        try: _MODELS[name] = load(name)
        except FileNotFoundError: raise CoreSeftError(f'the {name} model is not installed: rebuild it with `python -m seft.cli impact-'
                                                      f'{"farmpond" if name == "farmpond" else "model"}`')
    return _MODELS[name]

def _ns(x):
    return dict(vars(x)) if hasattr(x, '__dict__') else dict(x or {})

def _neighbours(table, x, scale, cols, district, k, head):
    """k most similar rows (standardised distance on cols), same district first."""
    x = np.asarray(x, float); sc = np.asarray(scale, float); sc[sc == 0] = 1
    rows = []
    for r in table:
        v = np.asarray(r[head:], float)
        d = float(np.sqrt(np.nansum(((v[cols] - x[cols]) / sc[cols]) ** 2)))
        rows.append((0 if r[0] == district else 1, d, r))
    rows.sort(key=lambda t: (t[0], t[1]))
    return [t[2] for t in rows[:k]]

# ------------------------------------------------------------------ predict_impact
class Predictor:
    def __init__(self, session):
        self.s = session

    def _wb(self, state, district, uid, tehsil, fetch):
        S = self.s
        teh = S._tehsils_for_query('waterbody', state, district, tehsil=tehsil, uid=uid, fetch=fetch)
        B = S._score_wb(state, district, teh, fetch=fetch)
        return S._find_wb(B, uid, state, district), teh

    def _mws_at(self, state, district, lat, lon):
        """MWS (and tehsil) holding a point, from the cached geometry."""
        from shapely.geometry import Point
        from seft.geo import to_shape
        from seft.util import geom_path, load_json, gs_slug
        p = geom_path()
        if not p.exists(): raise CoreSeftError('no cached geometry: fetch the district first (fetch_district)')
        geo = load_json(p); pt = Point(lon, lat); pre = gs_slug(district) + '/'
        for key, g in geo.items():
            if not key.startswith(pre): continue
            for uid, enc in (g.get('mws') or {}).items():
                shp = to_shape(enc)
                if shp is not None and shp.contains(pt): return uid, key[len(pre):]
        raise UnknownEntity(f'no micro-watershed of {state}/{district} in the cache holds ({lat}, {lon})')

    def _mws(self, state, district, uid, tehsil, fetch):
        S = self.s
        if tehsil:
            ts = [t for t in S._tehsils(state, district) if t.lower().replace(' ', '_') == tehsil.lower().replace(' ', '_')] or [tehsil]
        else:
            ts = S._tehsils_for_query('mws', state, district, uid=uid, fetch=fetch)
        recs, *_ = S._score_mws(state, district, ts, fetch=fetch)
        r = S._find_mws(recs, uid, state, district)
        return r, ts

    def _baseline(self, state, district, tehsils, uid):
        from seft.util import raw_dir, load_json
        from seft.impact.farmpond import settings
        from seft.impact.model import mws_baseline
        Y = settings()['years']['series']; M = {}
        for t in tehsils:
            d = raw_dir(state, district, t)
            for name in ('croppingintensity_annual.json', 'croppingdrought_kharif.json'):
                p = d / name
                if not p.exists(): continue
                for row in load_json(p)['rows']:
                    if str(row['metadata']['uid']) != str(uid): continue
                    a = row['annual']
                    if 'intensity' in name and not M.get('crop'):
                        M.update(cropable=row['metadata'].get('sum_area'), area=row['metadata'].get('area'),
                                 crop={k: a.get(k) for k in ('single_cropped_area', 'doubly_cropped_area', 'triply_cropped_area',
                                                             'single_non_kharif_cropped_area', 'single_kharif_cropped_area', 'cropping_intensity')})
                    elif 'drought' in name:
                        M['dweeks'] = {int(y): (m or 0) + (s or 0) for y, m, s in zip(a['time'], a['moderate'], a['severe'])}
        return mws_baseline(M, Y)

    def predict(self, intervention, *, state, district, type=None, waterbody=None, mws=None, lat=None, lon=None, tehsil=None,
                area_ha=None, zoi_area_ha=None, catchment_ha=None, stream_order=None, lined=None, volume_m3=None, fetch=True, k=10):
        S = self.s; S._activate()
        if intervention in ('desilting',):
            return self._desilting(state, district, waterbody, tehsil, volume_m3, fetch, k)
        if intervention not in ('new_pond', 'new_farmpond', 'farm_pond', 'new_structure'):
            raise UnknownEntity(f'intervention must be "new_pond" or "desilting", not {intervention!r}')
        Mdl = model('farmpond')
        b = None; notes = []
        if waterbody is not None:
            b, ts = self._wb(state, district, waterbody, tehsil, fetch)
            mws = b.get('home_mws'); type = type or b.get('type')
            area_ha = area_ha if area_ha is not None else b.get('area_ha')
            catchment_ha = catchment_ha if catchment_ha is not None else b.get('catchment_ha')
            stream_order = stream_order if stream_order is not None else b.get('stream_order')
            z = b.get('zoi') or {}
            zoi_area_ha = zoi_area_ha if zoi_area_ha is not None else z.get('zoi_area')
            if lined is None and type == 'farm_pond':
                cls = ((b.get('fp_note') or {}).get('fp_lining') or None)
                lined = {'lined': True, 'unlined': False}.get(cls)
        if mws is None and lat is not None and lon is not None:
            mws, tehsil = self._mws_at(state, district, lat, lon)
        if mws is None: raise UnknownEntity('give waterbody=, mws= or lat= and lon=')
        type = type or 'farm_pond'
        T = Mdl['types'].get(type)
        if not T: raise UnknownEntity(f'no model for {type!r}; models exist for {sorted(Mdl["types"])}')
        r, ts = self._mws(state, district, mws, tehsil, fetch)
        ci, dw = self._baseline(state, district, ts, mws)
        ctx = {f'ctx_{k}': v for k, v in _ns(r.get('ctx')).items()}
        shares = (r.get('mix') or {}).get('shares') or {}
        if area_ha is None: area_ha = 0.2 if type == 'farm_pond' else 1.0; notes.append(f'area_ha not given: {area_ha} ha assumed')
        if zoi_area_ha is None and T.get('zoi_ratio'):
            zoi_area_ha = area_ha * T['zoi_ratio']; notes.append(f'zoi_area_ha not given: {T["zoi_ratio"]} x area (median of assessed {type})')
        cls = None if type != 'farm_pond' else ('lined' if lined is True else 'unlined' if lined is False else 'uncertain')
        from seft.impact.model import fp_features, predict_forest
        x = fp_features(area_ha, zoi_area_ha, stream_order, catchment_ha, ci, dw, cls, ctx, shares)
        filled = []
        unknown = {2: stream_order is None, 3: catchment_ha is None}
        for i, v in enumerate(x):
            if (unknown.get(i) or not math.isfinite(v)) and T['fill'][i] is not None:
                x[i] = T['fill'][i]; filled.append(Mdl['features'][i])
        if filled: notes.append('not known, set to the median of assessed structures: ' + ', '.join(filled))
        p = float(predict_forest(T['trees'], [x])[0])
        g = int(np.searchsorted(T['cuts'], p)); G = T['groups'][g]
        nb = _neighbours(T['table'], x, T['scale'], list(range(len(x))), district, k, head=5)
        return {
            'intervention': 'new_pond', 'type': type, 'state': state, 'district': district, 'mws': mws, 'waterbody': waterbody,
            'inputs': {'area_ha': area_ha, 'zoi_area_ha': zoi_area_ha, 'catchment_ha': catchment_ha, 'stream_order': stream_order,
                       'lining': cls, 'mws_ci_mean': ci, 'mws_drought_weeks': dw, 'ctx': ctx, 'shares': shares},
            'outcome': 'cropping intensity in the zone of influence, percentage points, average over the first years after construction',
            'predicted': round(100 * p, 1),
            'group': {'fifth': g + 1, 'of': 5, 'n': G.get('n'), 'mean': _pct(G.get('mean')), 'range95': [_pct(G.get('lo')), _pct(G.get('hi'))],
                      'p10_p90': [_pct(G.get('p10')), _pct(G.get('p90'))]},
            'all_assessed': {'n': T['all']['n'], 'mean': _pct(T['all']['mean']), 'p10_p90': [_pct(T['all']['p10']), _pct(T['all']['p90'])]},
            'similar': [{'district': n[0], 'waterbody': n[1], 'first_wet': n[2], 'effect': _pct(n[3]), 'lining': n[4]} for n in nb],
            'model': {'name': 'farmpond', 'version': Mdl.get('version'), 'n': T['n'], 'blp': T['blp'], 'blp_se': T['blp_se']},
            'notes': notes + ([f'{type} results are exploratory: much of the benefit can lie downstream or in uses other than crops']
                              if type in ('small_onstream_pond', 'onstream_tank', 'village_pond') else []),
            'caution': 'The prediction says how much structures like this one gained on average; one structure varies by about 20 points from year to year, so the range of similar structures (p10_p90) matters more than the point value. Features are associations, not causes.'}

    def _desilting(self, state, district, waterbody, tehsil, volume_m3, fetch, k):
        if waterbody is None: raise UnknownEntity('desilting needs waterbody=')
        if not volume_m3: raise UnknownEntity('desilting needs volume_m3= (silt to be removed)')
        Mdl = model('desilting')
        from seft.impact.model import ds_features
        b, _ = self._wb(state, district, waterbody, tehsil, fetch)
        rain = (b.get('mws') or {}).get('ctx_rainfall')
        x = np.array(ds_features(b.get('area_ha'), volume_m3, b.get('catchment_ha'), b.get('stream_order'), rain, b.get('type'), Mdl['types']))
        x = x[np.array(Mdl['keep'])]
        beta = np.array(Mdl['coef']); V = np.array(Mdl['cov'])
        p = float(x @ beta); se = float(math.sqrt(max(x @ V @ x, 0))); sd = math.sqrt(se ** 2 + Mdl['resid_sd'] ** 2)
        nb = _neighbours(Mdl['table'], x, np.std(np.array([r[5:] for r in Mdl['table']], float), 0), list(range(1, len(x))), district, k, head=5)
        notes = [] if b.get('type') in Mdl['types'] else [f'no desilted {b.get("type")} in the model: predicted as the reference type {Mdl["types"][0]}']
        return {'intervention': 'desilting', 'state': state, 'district': district, 'waterbody': waterbody, 'type': b.get('type'),
                'inputs': {'area_ha': b.get('area_ha'), 'volume_m3': volume_m3, 'depth_m': round(volume_m3 / (b['area_ha'] * 1e4), 2) if b.get('area_ha') else None,
                           'catchment_ha': b.get('catchment_ha'), 'stream_order': b.get('stream_order'), 'rainfall': rain},
                'outcome': 'change in weeks of water a year against similar untreated waterbodies',
                'predicted': round(p, 1), 'range95_mean': [round(p - 1.96 * se, 1), round(p + 1.96 * se, 1)],
                'range95_single': [round(p - 1.96 * sd, 1), round(p + 1.96 * sd, 1)],
                'all_assessed': {'n': Mdl['all']['n'], 'mean': round(Mdl['all']['mean'], 1), 'p10_p90': [round(Mdl['all']['p10'], 1), round(Mdl['all']['p90'], 1)]},
                'similar': [{'district': n[0], 'waterbody': n[1], 'type': n[2], 'year': n[3], 'effect_weeks': n[4]} for n in nb],
                'model': {'name': 'desilting', 'version': Mdl.get('version'), 'n': Mdl['n'], 'r2': Mdl['r2']},
                'notes': notes, 'caution': f'The features explain little of the variation between works (R² {Mdl["r2"]}): the prediction is close to the average of assessed works, and a single work can differ by many weeks (range95_single).'}

def _pct(v):
    return None if v is None else round(100 * v, 1)

# ------------------------------------------------------------------ site_suitability
LU = {'croplands': r'cropland', 'single kharif': r'single kharif', 'single non-kharif': r'single non-kharif', 'double': r'double',
      'triple': r'triple', 'barren': r'barren', 'shrub/scrub': r'shrub', 'trees/forest': r'trees|forest', 'built-up': r'built', 'water': r'water'}
CROPS = {'croplands', 'single kharif', 'single non-kharif', 'double', 'triple'}
PARAM = {'Slope': 'slope_pct', 'Stream order': 'stream_order', 'Catchment area': 'catchment_ha', 'Distance to drainage line': 'drainage_distance_m',
         'Land use': 'land_use', 'Land use (recharge pits)': 'land_use', 'Hydrologic soil group': 'soil_group'}

def _num_match(v, text):
    """True/False whether number v fits a rule text like '3–20%', '< 1 or > 10%', '1, 2, 3', '≤ 2 ha'; None if unreadable."""
    t = re.sub(r'\([^)]*\)', '', str(text or '')).strip()
    if not t or t in ('—', '-', 'None'): return None
    t = t.replace('%', '').replace('ha', '').replace(' m', '').replace('–', '-').replace('≤', '<=').replace('≥', '>=')
    ok = False; read = False
    for part in re.split(r'\bor\b|,', t):
        part = part.strip().rstrip('m').strip()
        if not part: continue
        m = re.match(r'^(<=|>=|<|>)\s*([\d.]+)$', part)
        if m:
            read = True; op, x = m.group(1), float(m.group(2))
            ok |= {'<': v < x, '<=': v <= x, '>': v > x, '>=': v >= x}[op]; continue
        m = re.match(r'^([\d.]+)\s*-\s*([\d.]+)$', part)
        if m: read = True; ok |= float(m.group(1)) <= v <= float(m.group(2)); continue
        m = re.match(r'^([\d.]+)$', part)
        if m: read = True; ok |= v == float(m.group(1)); continue
    return ok if read else None

def _lu_terms(text):
    t = str(text or '').lower()
    return {k for k, rx in LU.items() if re.search(rx, t)}

def _cat_match(param, v, text):
    if str(text or '').strip() in ('', '—', 'None'): return None
    if param == 'soil_group':
        allowed = set(re.findall(r'\b([ABCD])\b', re.sub(r'\([^)]*\)', '', str(text))))
        return str(v).strip().upper() in allowed if allowed else None
    vals = v if isinstance(v, (list, tuple, set)) else [v]
    want = set().union(*[_lu_terms(x) for x in vals]) or {str(x).lower() for x in vals}
    have = _lu_terms(text)
    if not have: return None
    if want & have: return True
    return bool(('croplands' in want and have & CROPS) or (want & CROPS and 'croplands' in have))

def evaluate_rule(rule, value):
    key = PARAM.get(rule['parameter'])
    def m(text):
        if key in ('land_use', 'soil_group'): return _cat_match(key, value, text)
        try: return _num_match(float(value), text)
        except (TypeError, ValueError): return None
    for res, field in (('accepted', 'accepted'), ('partial', 'partial'), ('not_accepted', 'not_accepted')):
        if m(rule.get(field)): return res
    return 'not_accepted' if m(rule.get('accepted')) is False else 'unknown'

def suitability(I, values, structures=None):
    """Run values against every structure with site rules. values: {slope_pct, stream_order, catchment_ha,
    drainage_distance_m, land_use, soil_group}; missing ones are reported as unknown."""
    out = []
    for iv in I['interventions']:
        if not iv.get('site_rules') or (structures and iv['id'] not in structures): continue
        rows = []
        for r in iv['site_rules']:
            key = PARAM.get(r['parameter']); v = (values or {}).get(key)
            res = 'unknown' if v is None or v == '' else evaluate_rule(r, v)
            rows.append({'parameter': r['parameter'], 'input': key, 'value': v, 'result': res, 'accepted': r.get('accepted'),
                         'partial': r.get('partial'), 'not_accepted': r.get('not_accepted'), 'basis': r.get('basis'), 'sources': r.get('sources', []),
                         'note': r.get('note')})
        res = [x['result'] for x in rows]
        verdict = ('not suitable' if 'not_accepted' in res else 'partly suitable' if 'partial' in res else
                   'unknown' if all(x == 'unknown' for x in res) else 'suitable' if 'unknown' not in res else 'suitable on the values given')
        out.append({'structure': iv['id'], 'name': iv['name'], 'category': iv.get('category'), 'verdict': verdict,
                    'missing': sorted({x['input'] for x in rows if x['result'] == 'unknown' and x['value'] is None}), 'rules': rows,
                    'where': iv.get('where'), 'site_spec': iv.get('site_spec')})
    order = {'suitable': 0, 'suitable on the values given': 1, 'partly suitable': 2, 'unknown': 3, 'not suitable': 4}
    out.sort(key=lambda r: (order[r['verdict']], r['structure']))
    return out
