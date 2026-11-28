"""Prediction models shipped with core_seft (core_seft/models/*.json.gz), rebuilt by the impact commands.

* New ponds and tanks (impact-farmpond): per waterbody type, a random forest fitted to the assessed structures'
  effects on cropping intensity in their zone of influence (years up to 2022-23), on features that can be known for
  a proposed site: its size, stream order and catchment, its micro-watershed's cropping intensity and kharif
  drought, the lined/unlined class (farm ponds) and the micro-watershed's context and farming-system shares. The
  trees are exported as plain arrays (no pickle, no scikit-learn needed to predict). With it: the cut points of
  the fifths of cross-fitted predictions, the effects observed in each fifth, and a table of the assessed
  structures for nearest-neighbour comparisons.
* Desilting (impact-model): a linear model (OLS, heteroskedasticity-robust covariance) of the headline effect on
  weeks of water, on a few features chosen in advance (size, depth of silt removed, catchment, stream order,
  rainfall zone, type), fitted on the assessable works without record-quality flags; with the works table for
  nearest-neighbour comparisons. Too few works for a forest.

The effects being modelled are causal estimates (imputation for new structures, matched DiD for desilting); the
models describe how they vary with the features, which are associations, not causes.
"""
import collections, gzip, json, math
from pathlib import Path
import numpy as np
from ..util import ROOT, load_json, slug

MODELS = ROOT / 'core_seft' / 'models'
OUT = ROOT / 'out' / 'impact'
CTX_FLAGS = [('ctx_aquifer', ['hard_rock'], 'hard-rock aquifer'), ('ctx_terrain', ['plain'], 'plain terrain'),
             ('ctx_terrain', ['hilly'], 'hilly terrain'), ('ctx_gw_category', ['over_exploited', 'critical'], 'groundwater over-exploited or critical'),
             ('ctx_canal', ['canal_present'], 'canal present'), ('ctx_rainfall', ['semi_arid'], 'semi-arid rainfall')]
SHARES = ['rainfed_dryland', 'rainfed_rice_subhumid', 'groundwater_irrigated', 'canal_irrigated', 'tank_irrigated', 'forest_fringe',
          'tree_crops', 'pastoral', 'peri_urban']
FP_FEATURES = (['log1p area_ha', 'log1p zoi_area_ha', 'stream_order', 'log1p catchment_ha', 'mws_ci_mean', 'mws_drought_weeks',
                'lined', 'unlined'] + [f[2] for f in CTX_FLAGS] + [f'share_{a}' for a in SHARES])

def fp_features(area_ha, zoi_area_ha, stream_order, catchment_ha, mws_ci_mean, mws_drought_weeks, cls, ctx, shares):
    """The feature vector of a (proposed or built) structure; ctx: {ctx_*: value}, shares: {system: share}."""
    ctx = ctx or {}; shares = shares or {}
    return [math.log1p(area_ha or 0), math.log1p(zoi_area_ha or 0), float(stream_order or 0), math.log1p(catchment_ha or 0),
            float(mws_ci_mean if mws_ci_mean is not None else np.nan), float(mws_drought_weeks if mws_drought_weeks is not None else np.nan),
            float(cls == 'lined'), float(cls == 'unlined')] + \
           [float(ctx.get(k) in vs) for k, vs, _ in CTX_FLAGS] + [float(shares.get(a) or 0) for a in SHARES]

def mws_baseline(M, years):
    """Mean cropping intensity ((single + 2 double + 3 triple) / cropable, over all years) and mean kharif drought weeks
    a year of a micro-watershed, from the cached cropping-intensity and drought rows (as at prediction time)."""
    from .farmpond import _arr, _cropable, CROP_KEYS
    n = len(years); ci = dw = None
    if M.get('crop'):
        src = {k: _arr(M['crop'].get(k), n, zero=True) for k in CROP_KEYS}
        c = M.get('cropable') or _cropable(M, src, n)
        if c: ci = float(np.mean((src['single_cropped_area'] + 2 * src['doubly_cropped_area'] + 3 * src['triply_cropped_area']) / c))
    d = M.get('dweeks') or {}
    v = [d[y] for y in years if y in d]
    if v: dw = float(np.mean(v))
    return ci, dw

# ------------------------------------------------------------------ forest export / predict
def export_forest(m):
    trees = []
    for est in m.estimators_:
        t = est.tree_
        trees.append({'f': t.feature.tolist(), 't': [round(float(x), 5) for x in t.threshold], 'l': t.children_left.tolist(),
                      'r': t.children_right.tolist(), 'v': [round(float(x), 5) for x in t.value[:, 0, 0]]})
    return trees

def predict_forest(trees, X):
    X = np.atleast_2d(np.asarray(X, float)); out = np.zeros(len(X))
    for T in trees:
        f, th, l, r, v = T['f'], T['t'], T['l'], T['r'], T['v']
        for i, x in enumerate(X):
            n = 0
            while l[n] != -1:
                n = l[n] if x[f[n]] <= th[n] else r[n]
            out[i] += v[n]
    return out / len(trees)

def _stats(y):
    y = np.asarray(y, float)
    if not len(y): return {'n': 0}
    rng = np.random.default_rng(7); bs = [rng.choice(y, len(y)).mean() for _ in range(300)]
    return {'n': int(len(y)), 'mean': round(float(y.mean()), 4), 'lo': round(float(np.percentile(bs, 2.5)), 4), 'hi': round(float(np.percentile(bs, 97.5)), 4),
            'p10': round(float(np.percentile(y, 10)), 4), 'p50': round(float(np.percentile(y, 50)), 4), 'p90': round(float(np.percentile(y, 90)), 4)}

def build_farmpond_model(types_units, H, version, years, log=print):
    """types_units: {type: [(unit, effect, features)]}. Returns the model dict for core_seft."""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import KFold
    out = {'kind': 'new_structure_forest', 'version': version, 'outcome': 'ci', 'unit': 'cropping intensity, points / 100',
           'features': FP_FEATURES, 'years': [years[0], years[-1]], 'types': {}}
    for typ, rows in types_units.items():
        if len(rows) < H['min_ponds']: log(f'  model: {typ}: {len(rows)} structures, too few for a forest'); continue
        X = np.nan_to_num(np.array([r[2] for r in rows], float)); y = np.array([r[1] for r in rows])
        med = np.nanmedian(np.array([r[2] for r in rows], float), axis=0)
        pred = np.zeros(len(y))
        for tr, te in KFold(H['folds'], shuffle=True, random_state=0).split(X):
            m = RandomForestRegressor(n_estimators=H.get('ship_trees', 100), min_samples_leaf=H['min_leaf'], max_features=0.4, random_state=0, n_jobs=-1).fit(X[tr], y[tr])
            pred[te] = m.predict(X[te])
        m = RandomForestRegressor(n_estimators=H.get('ship_trees', 100), min_samples_leaf=H['min_leaf'], max_features=0.4, random_state=0, n_jobs=-1).fit(X, y)
        q = np.quantile(pred, [0.2, 0.4, 0.6, 0.8]); grp = np.searchsorted(q, pred)
        Z = np.c_[np.ones(len(y)), pred - pred.mean()]; b = np.linalg.lstsq(Z, y, rcond=None)[0]
        e = y - Z @ b; Si = np.linalg.inv(Z.T @ Z); V = Si @ (Z.T * e ** 2) @ Z @ Si
        zr = [r[0].get('zoi_area') / r[0]['area'] for r in rows if r[0].get('zoi_area') and r[0].get('area')]
        out['types'][typ] = {
            'n': len(y), 'trees': export_forest(m), 'fill': [None if not np.isfinite(v) else round(float(v), 4) for v in med],
            'cuts': [round(float(v), 4) for v in q], 'groups': [_stats(y[grp == g]) for g in range(5)], 'all': _stats(y),
            'blp': round(float(b[1]), 3), 'blp_se': round(float(math.sqrt(V[1, 1])), 3), 'zoi_ratio': round(float(np.median(zr)), 2) if zr else None,
            'importance': [round(float(v), 4) for v in m.feature_importances_],
            'scale': [round(float(v), 4) for v in X.std(0)],
            'table': [[r[0]['district'], str(r[0]['id']), r[0]['E'], round(float(r[1]), 4), r[0].get('cls')] + [round(float(v), 3) for v in x] for r, x in zip(rows, X)]}
        log(f'  model: {typ}: forest of {H.get("ship_trees", 100)} trees on {len(y)} structures (BLP {b[1]:.2f})')
    return out

def save(model, name, out_dir=None, log=print):
    for d in ([Path(out_dir)] if out_dir else []) + [MODELS]:
        d.mkdir(parents=True, exist_ok=True)
        p = d / f'{name}.json.gz'
        with gzip.open(p, 'wt', encoding='utf-8') as f: json.dump(model, f, separators=(',', ':'), allow_nan=False)
        log(f'  model written: {p} ({p.stat().st_size / 1e6:.2f} MB)')

def load(name, path=None):
    p = Path(path) if path else MODELS / f'{name}.json.gz'
    with gzip.open(p, 'rt', encoding='utf-8') as f: return json.load(f)

# ------------------------------------------------------------------ desilting
DS_RAIN = ['arid', 'semi_arid', 'dry_subhumid', 'moist_subhumid', 'humid']

def ds_features(area_ha, volume_m3, catchment_ha, stream_order, rainfall, wtype, types):
    depth = (volume_m3 or 0) / ((area_ha or 0) * 1e4) if area_ha else 0
    return [1.0, math.log1p(area_ha or 0), min(depth, 3.0), math.log1p(catchment_ha or 0), float(stream_order or 0)] + \
           [float(rainfall == r) for r in DS_RAIN[1:]] + [float(wtype == t) for t in types[1:]]

def build_desilting_model(web=None, version='', log=print):
    """From the published desilting bundles (web/data/waterbody imp_*.json and w_*.json)."""
    web = Path(web or ROOT / 'web' / 'data' / 'waterbody')
    idx = json.loads((web / 'index.json').read_text(encoding='utf-8-sig')); E = idx['env_ids']
    ia, ic = E.index('area_ha'), E.index('catchment_ratio')
    rows = []
    for p in sorted(web.glob('imp_*.json')):
        b = json.loads(p.read_text(encoding='utf-8')); s = p.stem[4:]
        wp = web / f'w_{s}.json'
        W = {str(w['id']): w for w in json.loads(wp.read_text(encoding='utf-8-sig'))['waterbodies']} if wp.exists() else {}
        for wid, recs in b['waterbodies'].items():
            for r in recs:
                if r.get('verdict') == 'not_assessable' or r.get('quality_flags') or r.get('window') not in ('single', 'first'): continue
                d = ((r.get('effects') or {}).get('W') or {}).get('did')
                if d is None: continue
                w = W.get(wid) or {}; e = w.get('e') or []
                area = r.get('area') or (e[ia] if len(e) > ia else None)
                catch = (e[ic] * area) if len(e) > ic and e[ic] is not None and area else None
                rows.append({'district': b.get('district') or s, 'id': wid, 'type': r['type'], 'area': area, 'catch': catch, 'so': w.get('so'),
                             'vol': (r.get('intervention') or {}).get('volume_m3'), 'rain': (r.get('ctx') or {}).get('ctx_rainfall'),
                             'year': ((r.get('intervention') or {}).get('years') or [None])[0], 'y': d})
    if len(rows) < 30: log(f'  desilting model: only {len(rows)} works'); return None
    types = [t for t, _ in collections.Counter(r['type'] for r in rows).most_common() if sum(x['type'] == t for x in rows) >= 15]
    rows = [r for r in rows if r['type'] in types]
    X = np.array([ds_features(r['area'], r['vol'], r['catch'], r['so'], r['rain'], r['type'], types) for r in rows]); y = np.array([r['y'] for r in rows])
    keep = X.std(0) > 0; keep[0] = True
    X = X[:, keep]
    b, *_ = np.linalg.lstsq(X, y, rcond=None); e = y - X @ b; n, k = X.shape
    XtXi = np.linalg.pinv(X.T @ X); V = XtXi @ (X.T * e ** 2) @ X @ XtXi * n / max(n - k, 1)
    names = (['intercept', 'log1p area_ha', 'depth_m', 'log1p catchment_ha', 'stream_order'] + [f'rain_{r}' for r in DS_RAIN[1:]] + [f'type_{t}' for t in types[1:]])
    names = [nm for nm, kp in zip(names, keep) if kp]
    model = {'kind': 'desilting_ols', 'version': version, 'outcome': 'weeks of water a year (headline DiD)', 'n': n,
             'types': types, 'rain': DS_RAIN, 'keep': keep.tolist(), 'features': names, 'coef': [round(float(v), 5) for v in b],
             'cov': [[round(float(v), 7) for v in row] for row in V], 'resid_sd': round(float(e.std()), 4), 'all': _stats(y),
             'r2': round(float(1 - e.var() / y.var()), 3),
             'table': [[r['district'], r['id'], r['type'], r['year'], round(float(r['y']), 3)] + [round(float(v), 3) for v in x] for r, x in zip(rows, X)]}
    log(f'  desilting model: OLS on {n} works, {k} terms, R² {model["r2"]}')
    return model
