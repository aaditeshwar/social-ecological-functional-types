"""impact-farmpond: the effect of new farm ponds (and headwater ponds) on cropping in their zone of influence.

There is no registry: a pond's first wet year in the CoRE Stack water series is taken as its construction year.
Settings in knowledge/impact/farmponds.json, notes in knowledge/impact/notes.json (fp_waterbody, fp_unit, fp_old),
references in knowledge/impact/references.json. Needs the waterbody layers, cropping intensity and kharif drought
of every tehsil in config/waterbody/locations.json (wb-fetch) and the waterbody atlas bundles (wb-run, for the MWS
context). Writes out/impact/farmpond/ (records.json, summary.json, review.md, web/) and copies the bundles to
web/data/waterbody/ (fp.json, fp_<district>.json).

Steps
1. Panel: every waterbody of every cached tehsil (wb.build), assigned to the tehsil whose boundary holds it
   (wb.run.dedupe); its ZoI and home-MWS cropping per year; MWS drought weeks.
2. New ponds: first wet year 2019-2023, wet in most years since, with a qualifying pre year (see farmponds.json).
3. Outcomes: ZoI cropping intensity, rabi/summer cropping, multi-cropped and cropped shares, footprint-adjusted
   after construction; background = the home MWS without the ZoI cropland of all new waterbodies.
4. Headline: imputation (pond baseline + district-year effect + MWS background + drought weeks fitted on untreated
   cells, Borusyak, Jaravel and Spiess 2024). Robustness: same-district DiD (doubly robust); background change;
   placebo on the last pre year.
5. Lined/unlined class from the water after construction; per-pond verdicts; averages by district, tehsil and MWS;
   heterogeneity (cross-fitted forest, BLP/GATES/CLAN); effectiveness of older structures (site-premium corrected).
"""
import collections, json, math
from pathlib import Path
import warnings
import numpy as np
from ..util import ROOT, load_json, raw_dir, slug, knowledge_dir
from .notes import render as _render, signed, years_text, rules as note_rules

def render(kind, env, R=None):
    """notes.render, with whole numbers written as the page writes them (en-IN grouping, years as they are), so a
    note written here reads the same as the one the atlas page writes from the same rules."""
    from ..intro_notes import fmt
    from ..expr import evaluate
    R = R or note_rules(); spec = R[kind]; ev = {**env, 'true': True, 'false': False}
    show = {k: (fmt(v, k) if isinstance(v, int) and not isinstance(v, bool) else v) for k, v in env.items()}
    class _S(dict):
        def __missing__(self, k): return '{' + k + '}'
    ok = lambda r: bool(_try(lambda: evaluate(r['when'], ev)))
    parts = []
    m = next((r for r in spec['main'] if ok(r)), None)
    if m: parts.append(m['text'].format_map(_S(show)))
    parts += [r['text'].format_map(_S(show)) for r in spec.get('add', []) if ok(r)]
    return ' '.join(parts)

def _try(f):
    try: return f()
    except Exception: return False

OUT = ROOT / 'out' / 'impact' / 'farmpond'
WEB = ROOT / 'web' / 'data' / 'waterbody'
ARCH = ['rainfed_dryland', 'rainfed_rice_subhumid', 'groundwater_irrigated', 'canal_irrigated', 'tank_irrigated', 'forest_fringe',
        'tree_crops', 'pastoral', 'peri_urban']
CROP_KEYS = ['single_cropped_area', 'doubly_cropped_area', 'triply_cropped_area', 'single_non_kharif_cropped_area', 'single_kharif_cropped_area']
OUTS = ['ci', 'nonkharif', 'multi', 'cropped']
CLS = ('lined', 'uncertain', 'unlined')

def settings():
    return load_json(knowledge_dir() / 'impact' / 'farmponds.json')

def references():
    return load_json(knowledge_dir() / 'impact' / 'references.json')

def _arr(xs, n, zero=False):
    xs = list(xs or [])[:n]
    a = np.full(n, 0.0 if zero else np.nan)
    for i, v in enumerate(xs):
        if v is not None: a[i] = float(v)
        elif zero: a[i] = 0.0
    return a

def _r(x, n=3):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else round(float(x), n)

# ------------------------------------------------------------------ the lined / unlined rule (shared with the atlas notes and core_seft)
def lining(k, kr, krz, dweeks, first_year, years, L):
    """Class of a pond from its seasonal water (% of its area) after its first wet year, and the signs behind it.
    k, kr, krz: per-year lists over `years`; dweeks: {year: weeks of moderate or severe kharif drought} of its home MWS."""
    n = len(years); i0 = years.index(first_year) if first_year in years else None
    if i0 is None: return None
    K, KR, KZ = _arr(k, n)[i0:], _arr(kr, n)[i0:], _arr(krz, n)[i0:]
    ok = ~np.isnan(KZ)
    if not ok.any(): return None
    dw = np.array([float((dweeks or {}).get(y, np.nan)) for y in years[i0:]])
    dr = dw >= L.get('drought_weeks', 4); nr = dw < L.get('drought_weeks', 4)
    s = {'summer_area': float(np.nanmean(KZ)), 'summer_years': float(np.mean(KZ[ok] > 0)), 'rabi_area': float(np.nanmean(KR)),
         'kharif_area': float(np.nanmean(K)), 'cv': float(np.nanstd(K) / (np.nanmean(K) + 1e-9)) if np.nanmean(K) > 0 else None,
         'fill_ratio': float(np.nanmean(K[dr]) / (np.nanmean(K[nr]) + 1e-9)) if dr.any() and nr.any() and np.nanmean(K[nr]) > 0 else None,
         'n_years': int(ok.sum())}
    s['sup_drought'] = s['fill_ratio'] is not None and s['fill_ratio'] >= L['drought_fill_ratio']
    s['sup_late'] = max(s['rabi_area'], s['summer_area']) > s['kharif_area']
    s['sup_steady'] = s['cv'] is not None and s['cv'] < L['steady_cv']
    s['n_sup'] = int(s['sup_drought']) + int(s['sup_late']) + int(s['sup_steady'])
    lined = s['summer_years'] >= L['lined_summer_years'] and s['summer_area'] >= L['lined_summer_area'] and s['n_sup'] >= L['min_supporting']
    unlined = s['summer_area'] < L['unlined_summer_area'] and not (s['sup_drought'] or s['sup_late'])
    s['cls'] = 'lined' if lined else ('unlined' if unlined else 'uncertain')
    return s

def note_fields(k, kr, krz, wtype, dweeks, S=None):
    """Fields of the waterbody note (knowledge/waterbody/notes.json fp_*) for one waterbody, as the atlas page reads
    them from fp_<district>.json: the lined/unlined class of a farm or headwater pond that keeps holding water, and
    whether it is a new pond (first wet from first_appearance). dweeks: {year: drought weeks} of its home MWS."""
    S = S or settings(); Y = S['years']['series']; n = len(Y)
    out = {'fp_lining': '', 'fp_summer_area': None, 'fp_summer_years': None, 'fp_new': False, 'fp_year_label': ''}
    if wtype not in S['intervention']['types']: return out
    w = np.nan_to_num(_arr(k, n)) + np.nan_to_num(_arr(kr, n)) + np.nan_to_num(_arr(krz, n)) > 0
    if not w.any(): return out
    i0 = int(np.argmax(w)); E = Y[i0]
    if w[i0:].mean() < S['appearance']['persist_share']: return out
    s = lining(k, kr, krz, dweeks, E, Y, {**S['lining'], 'drought_weeks': S['drought']['min_weeks']})
    if s and wtype in S['lining'].get('types', S['intervention']['types']):
        out.update(fp_lining=s['cls'], fp_summer_area=round(s['summer_area']), fp_summer_years=round(100 * s['summer_years']))
    if E >= S['years']['first_appearance']: out.update(fp_new=True, fp_year_label=years_text([E]))
    return out

# ------------------------------------------------------------------ 1. panel
def _crop(src, cropable, n):
    g = lambda k: _arr(src.get(k), n)
    s, d, t, snk = g('single_cropped_area'), g('doubly_cropped_area'), g('triply_cropped_area'), g('single_non_kharif_cropped_area')
    cropped = s + d + t; c = cropable if cropable else np.nan
    with np.errstate(invalid='ignore', divide='ignore'):
        return {'ci': (s + 2 * d + 3 * t) / c, 'multi': (d + t) / cropped, 'nonkharif': (d + t + snk) / c, 'cropped': cropped / c}

def load_panel(wcfg, years, log=print):
    from ..wb.build import build_tehsil
    from ..wb.run import dedupe
    types = load_json(knowledge_dir() / 'waterbody' / 'types.json')
    keep = ('wb_id', 'area_ha', 'stream_order', 'catchment_ha', 'home_mws', 'k', 'kr', 'krz', 'centroid', 'zoi', 'state', 'district', 'tehsil', 'type')
    B, MWS, nt = [], {}, 0
    for dd in wcfg['districts']:
        for t in dd['tehsils']:
            d = raw_dir(dd['state'], dd['district'], t)
            if not (d / 'swb_layers.json.gz').exists(): continue
            bs, _ = build_tehsil(dd['state'], dd['district'], t, types, log=lambda *a: None); nt += 1
            for b in bs:
                z = b.get('zoi') or {}
                b['zoi'] = {k: z.get(k) for k in CROP_KEYS + ['total_cropable_area_ever_hydroyear_2017_2024', 'zoi_area', 'cropping_intensity']} if z else None
                B.append({k: b.get(k) for k in keep})
            for name in ('croppingintensity_annual.json', 'croppingdrought_kharif.json'):
                p = d / name
                if not p.exists(): continue
                for r in load_json(p)['rows']:
                    u = r['metadata']['uid']; a = r['annual']; M = MWS.setdefault(u, {})
                    if name.startswith('cropping') and 'intensity' in name:
                        if M.get('crop'): continue
                        M.update(district=dd['district'], tehsil=t, cropable=r['metadata'].get('sum_area'), area=r['metadata'].get('area'),
                                 crop={k: a.get(k) for k in CROP_KEYS + ['cropping_intensity']})
                    else:
                        M['dweeks'] = {int(y): (m or 0) + (s or 0) for y, m, s in zip(a['time'], a['moderate'], a['severe'])}
    for b in B: b['mws'] = {}; b['mws']['mws_tehsil'] = (MWS.get(b.get('home_mws')) or {}).get('tehsil')
    B = dedupe(B, log=log)
    log(f'  panel: {len(B)} waterbodies in {nt} cached tehsils, {len(MWS)} micro-watersheds')
    return B, MWS

def mws_context(districts):
    """{mws: {ctx_*: .., share_*: ..}} from the waterbody atlas bundles."""
    out = {}
    for d in districts:
        s = slug(d)
        for p in (ROOT / 'out' / 'waterbody' / 'web' / f'w_{s}.json', ROOT / 'web' / 'data' / 'waterbody' / f'w_{s}.json'):
            if p.exists():
                for u, v in json.loads(p.read_text(encoding='utf-8-sig')).get('mws', {}).items():
                    out[u] = {k: x for k, x in v.items() if k.startswith('ctx_') or k.startswith('share_') or k == 'dominant_system'}
                break
    return out

# ------------------------------------------------------------------ 2-3. units with outcomes
def make_units(B, MWS, S, log=print):
    Y = S['years']['series']; NY = len(Y); yi = {y: i for i, y in enumerate(Y)}; A = S['appearance']; DW = S['drought']['min_weeks']
    def wet(b):
        k, kr, krz = _arr(b.get('k'), NY), _arr(b.get('kr'), NY), _arr(b.get('krz'), NY)
        return np.nan_to_num(k) + np.nan_to_num(kr) + np.nan_to_num(krz) > 0
    W = [wet(b) for b in B]
    est = collections.defaultdict(lambda: collections.defaultdict(list))
    for b, w in zip(B, W):
        if w[0] and b.get('home_mws'): est[b['home_mws']][b['type']].append(w); est[b['home_mws']]['*'].append(w)
    U = []
    for b, w in zip(B, W):
        if not w.any(): continue
        E = Y[int(np.argmax(w))]; persist = float(w[yi[E]:].mean())
        m = b.get('home_mws'); M = MWS.get(m) or {}; dwk = M.get('dweeks') or {}
        nb = est[m][b['type']] if len(est[m][b['type']]) >= A['same_type_min'] else est[m]['*']
        valid = []
        if E > Y[0] and len(nb) >= A['min_neighbours']:
            share = np.mean(np.array(nb), axis=0)
            valid = [y for y in Y[:yi[E]] if share[yi[y]] >= A['neighbour_wet_share'] and not dwk.get(y, 0) >= DW]
        z = b.get('zoi')
        zo = _crop(z, z.get('total_cropable_area_ever_hydroyear_2017_2024'), NY) if z and z.get('cropping_intensity') else None
        U.append({'id': b['wb_id'], 'type': b['type'], 'state': b['state'], 'district': b['district'], 'tehsil': b['tehsil'], 'mws': m,
                  'area': b['area_ha'], 'xy': b.get('centroid'), 'E': E, 'persist': persist, 'valid_pre': valid, 'zoi': zo,
                  'zoi_area': (z or {}).get('zoi_area'), 'so': b.get('stream_order'), 'catch': b.get('catchment_ha'),
                  'cropable': (z or {}).get('total_cropable_area_ever_hydroyear_2017_2024'), 'zraw': z,
                  'k': b.get('k'), 'kr': b.get('kr'), 'krz': b.get('krz'),
                  'dweeks': np.array([float(dwk.get(y, np.nan)) for y in Y])})
    # background: the home MWS's cropping without the ZoI cropland of waterbodies that appeared from first_appearance
    sub = collections.defaultdict(lambda: {**{k: np.zeros(NY) for k in CROP_KEYS}, 'cropable': 0.0})
    for u in U:
        z = u['zraw']
        if not z or not u['mws'] or u['E'] < S['years']['first_appearance'] or not z.get('cropping_intensity'): continue
        for k in CROP_KEYS: sub[u['mws']][k] += _arr(z.get(k), NY, zero=True)
        sub[u['mws']]['cropable'] += z.get('total_cropable_area_ever_hydroyear_2017_2024') or 0
    bg = {}
    for m, M in MWS.items():
        if not M.get('crop'): continue
        src = {k: _arr(M['crop'].get(k), NY, zero=True) for k in CROP_KEYS}; c = M.get('cropable') or _cropable(M, src, NY)
        if m in sub and c > 0:
            # overlapping ZoIs can add up to more than the MWS: never remove more than max_remove of its cropland
            frac = sub[m]['cropable'] / c; f = min(frac, S['background']['max_remove']) / frac if frac > S['background']['max_remove'] else 1.0
            src = {k: np.maximum(src[k] - f * sub[m][k], 0) for k in CROP_KEYS}; c = c - f * sub[m]['cropable']
        bg[m] = _crop({k: list(v) for k, v in src.items()}, c if c > 0 else None, NY) if c > 0 else None
    F = S['footprint']['max_share']
    for u in U:
        u.pop('zraw', None)
        u['bgo'] = bg.get(u['mws'])
        u['ok'] = u['zoi'] is not None and u['bgo'] is not None and not np.isnan(u['zoi']['ci']).all()
        if not u['ok']: continue
        f = min(u['area'] / u['zoi_area'], F) if u.get('zoi_area') else 0.0
        u['y'] = {}
        for oc in OUTS:
            y = u['zoi'][oc].copy()
            if u['E'] > Y[0] and next(o for o in S['outcomes'] if o['id'] == oc).get('footprint'): y[yi[u['E']]:] = y[yi[u['E']]:] / (1 - f)
            u['y'][oc] = y
        u['bg'] = u['bgo']; u['dwk'] = np.nan_to_num(u['dweeks'], nan=0.0); u['drt'] = (u['dwk'] >= DW).astype(float)
    return U

def _cropable(M, src, NY):
    """Cropable area when the API leaves out sum_area: from the published cropping intensity, else the MWS area."""
    ci = _arr((M.get('crop') or {}).get('cropping_intensity'), NY)
    w = src['single_cropped_area'] + 2 * src['doubly_cropped_area'] + 3 * src['triply_cropped_area']
    ok = (ci > 0) & np.isfinite(ci) & (w > 0)
    return float(np.median(w[ok] / ci[ok])) if ok.any() else (M.get('area') or 0)

# ------------------------------------------------------------------ 4. estimators
def fit_imputation(units, oc, NY, hold=False, iters=300):
    """Y_it = a_i + l_(t,district) + g*MWS_it + d*droughtweeks_it on untreated cells (t < E); hold leaves out E-1."""
    yi0 = lambda u: u['Ei']
    rows = []
    for k, u in enumerate(units):
        E = u['Ei']; y = u['y'][oc]; b = u['bg'][oc]
        for t in range(E):
            if hold and t == E - 1 and E >= 3: continue
            if np.isnan(y[t]) or np.isnan(b[t]): continue
            rows.append((k, (t, u['district']), y[t], b[t], u['dwk'][t]))
    if not rows: return None
    K = np.array([r[0] for r in rows]); C = [r[1] for r in rows]
    Yv = np.array([r[2] for r in rows]); X = np.array([[r[3], r[4]] for r in rows])
    ci = {c: j for j, c in enumerate(sorted(set(C)))}; Ci = np.array([ci[c] for c in C]); nu = len(units)
    cntK = np.maximum(np.bincount(K, None, nu), 1); cntC = np.bincount(Ci, None, len(ci))
    beta = np.zeros(2); lam = np.zeros(len(ci)); a = np.zeros(nu)
    Xd = X - np.array([np.bincount(K, X[:, j], nu)[K] / cntK[K] for j in range(2)]).T
    for _ in range(iters):
        r = Yv - X @ beta
        a_new = np.bincount(K, r - lam[Ci], nu) / cntK
        lam_new = np.bincount(Ci, r - a_new[K], len(ci)) / cntC
        e = Yv - a_new[K] - lam_new[Ci]
        beta_new = np.linalg.lstsq(Xd, e - e.mean(), rcond=None)[0] if len(Yv) > 10 else beta
        done = np.abs(beta_new - beta).max() < 1e-7 and np.abs(lam_new - lam).max() < 1e-7
        a, lam, beta = a_new, lam_new, beta_new
        if done: break
    ncell = collections.Counter(C); lamd = {c: lam[j] for c, j in ci.items()}
    pooled = collections.defaultdict(list)
    for c, j in ci.items(): pooled[c[0]].append((lam[j], ncell[c]))
    lamt = {t: (sum(l * n for l, n in v) / sum(n for _, n in v), sum(n for _, n in v)) for t, v in pooled.items()}
    return dict(a=a, lam=lamd, lam_t=lamt, ncell=ncell, beta=beta, has=set(K.tolist()))

def impute_cells(units, oc, M, NY, min_cell, hold=False):
    """[(k, t, tau, drought, support, yhat)] for post cells (or the held-out E-1 cell)."""
    out = []
    if M is None: return out
    for k, u in enumerate(units):
        if k not in M['has']: continue
        E = u['Ei']; y = u['y'][oc]; b = u['bg'][oc]
        for t in (([E - 1] if E >= 3 else []) if hold else range(E, NY)):
            if np.isnan(y[t]) or np.isnan(b[t]): continue
            c = (t, u['district'])
            if M['ncell'].get(c, 0) >= min_cell: l, s = M['lam'][c], 'district'
            elif M['lam_t'].get(t, (0, 0))[1] >= min_cell: l, s = M['lam_t'][t][0], 'pooled'
            else: l, s = 0.0, 'background'
            yhat = M['a'][k] + l + M['beta'][0] * b[t] + M['beta'][1] * u['dwk'][t]
            out.append((k, t, y[t] - yhat, u['drt'][t], s, yhat))
    return out

def did_district(units, oc, last_main, min_n=10, cov='none', B=200, rng=None):
    """Cohort x year DiD against not-yet-built ponds of the same district, change from the pre-year mean.
    cov: 'none' (simple DiD), 'size' or 'mws' (doubly robust, Sant'Anna and Zhao 2020)."""
    from sklearn.linear_model import LogisticRegression, LinearRegression
    rng = rng or np.random.default_rng(7); res = []
    for d in sorted({u['district'] for u in units}):
        us = [u for u in units if u['district'] == d]
        for G in sorted({u['Ei'] for u in us}):
            for t in range(G, last_main + 1):
                dy = lambda u: u['y'][oc][t] - np.nanmean(u['y'][oc][:G])
                tr = [u for u in us if u['Ei'] == G and not np.isnan(dy(u))]; co = [u for u in us if u['Ei'] > t and not np.isnan(dy(u))]
                if len(tr) < min_n or len(co) < min_n: continue
                D = np.r_[np.ones(len(tr)), np.zeros(len(co))]; Yv = np.array([dy(u) for u in tr + co])
                if cov == 'none': ps = np.full(len(D), D.mean()); m = np.full(len(D), Yv[D == 0].mean())
                else:
                    fx = lambda u: [math.log1p(u['area']), math.log1p(u.get('zoi_area') or 0), u.get('so') or 0, math.log1p(u.get('catch') or 0)] + (
                        [np.nanmean(u['bg'][oc][:G]), u['bg'][oc][t] - np.nanmean(u['bg'][oc][:G]), u['dwk'][t]] if cov == 'mws' else [])
                    X = np.nan_to_num(np.array([fx(u) for u in tr + co])); X = (X - X.mean(0)) / (X.std(0) + 1e-9)
                    ps = LogisticRegression(max_iter=500).fit(X, D).predict_proba(X)[:, 1].clip(0.02, 0.98)
                    m = LinearRegression().fit(X[D == 0], Yv[D == 0]).predict(X)
                w1 = D / D.mean(); w0 = ps * (1 - D) / (1 - ps); w0 = w0 / w0.mean()
                res.append((len(tr), w1 * (Yv - m) - w0 * (Yv - m), D))
    if not res: return None
    tot = sum(n for n, *_ in res); est = sum(n * psi.mean() / D.mean() for n, psi, D in res) / tot
    bs = []
    for _ in range(B):
        v = 0
        for n, psi, D in res:
            i = rng.integers(0, len(psi), len(psi)); v += n * psi[i].mean() / max(D[i].mean(), 1e-9)
        bs.append(v / tot)
    return {'mean': _r(est, 4), 'lo': _r(np.percentile(bs, 2.5), 4), 'hi': _r(np.percentile(bs, 97.5), 4), 'n_cells': len(res)}

def boot(x, B=500, rng=None):
    x = np.asarray([v for v in x if v is not None and np.isfinite(v)], float); rng = rng or np.random.default_rng(7)
    if not len(x): return {'n': 0}
    bs = [float(rng.choice(x, len(x)).mean()) for _ in range(B)] if len(x) > 1 else [float(x[0])]
    return {'n': int(len(x)), 'mean': _r(x.mean(), 4), 'lo': _r(np.percentile(bs, 2.5), 4), 'hi': _r(np.percentile(bs, 97.5), 4)}

# ------------------------------------------------------------------ 5. per-pond records and verdicts
def pond_records(units, OUT_, hold, S, rng):
    V = S['verdict']; last = S['_last_main']; Y = S['years']['series']
    ref = np.array([c[2] for c in hold])
    pl = {c[0]: c[2] for c in hold}
    recs = {}
    for k, u in enumerate(units):
        cells = [c for c in OUT_['ci'] if c[0] == k]
        main = [c for c in cells if c[1] <= last]; early = [c for c in cells if c[1] > last]
        use = main or early
        eff = {}
        for oc in OUTS:
            cs = [c for c in OUT_[oc] if c[0] == k]
            m = [c[2] for c in cs if c[1] <= last]; e = [c[2] for c in cs if c[1] > last]
            eff[oc] = {'main': _r(np.mean(m), 4) if m else None, 'early': _r(np.mean(e), 4) if e else None, 'n_main': len(m), 'n_early': len(e)}
        r = u['y']['ci'] - u['bg']['ci']; pre = np.nanmean(r[:u['Ei']]) if u['Ei'] else np.nan
        bgc = [r[t] - pre for t in range(u['Ei'], len(Y)) if not np.isnan(r[t])] if np.isfinite(pre) else []
        bgm = float(np.mean(bgc)) if bgc else None
        rec = {'E': u['E'], 'cls': u['cls'], 'sig': u['sig'], 'effects': eff, 'background': _r(bgm, 4), 'placebo': _r(pl.get(k), 4),
               'post_years': [Y[c[1]] for c in cells], 'main_years': [Y[c[1]] for c in main],
               'support': dict(collections.Counter(c[4] for c in cells)),
               'drought_main': _r(np.mean([c[2] for c in main if c[3] == 1]), 4) if any(c[3] == 1 for c in main) else None,
               'flags': (['appeared_2019'] if u['E'] == S['years']['first_appearance'] else []) + (['small'] if u['area'] < 0.1 else [])}
        if not use:
            rec.update(verdict='not_assessable', reason='no cropping data for the years after the pond appeared'); recs[k] = rec; continue
        tau = float(np.mean([c[2] for c in use])); n = len(use)
        refm = rng.choice(ref, (2000, n)).mean(1) if len(ref) else np.array([0.0])
        pct = float((refm < tau).mean() * 100)
        p = pl.get(k); ppct = float((ref < p).mean() * 100) if p is not None and len(ref) else None
        base = 'gain' if pct >= V['gain_pct'] else ('loss' if pct <= V['loss_pct'] else 'no_change')
        placebo_ok = p is None or (V['placebo_band'][0] <= ppct <= V['placebo_band'][1] and abs(p) <= abs(tau))
        agree = bgm is None or base == 'no_change' or np.sign(bgm) == np.sign(tau)
        earlyv = not main or n < V['min_post_years_full'] or set(c[4] for c in use) == {'background'}
        if base == 'no_change': verdict = 'no_change'
        elif not (placebo_ok and agree): verdict = 'inconclusive'
        else: verdict = ('early_' if earlyv else 'likely_') + base
        reasons = ([] if placebo_ok else ['the pond\'s area was already gaining or falling behind the year before it appeared']) + \
                  ([] if agree else ['the change against its micro-watershed points the other way'])
        rec.update(verdict=verdict, tau=_r(tau, 4), n=n, pct=_r(pct, 1), placebo_pct=_r(ppct, 1), early=bool(earlyv), reason='; '.join(reasons),
                   series={'zoi': [_r(x) for x in u['y']['ci']], 'mws': [_r(x) for x in u['bg']['ci']],
                           'fit': [None] * u['Ei'] + [_r(next((c[5] for c in cells if c[1] == t), None)) for t in range(u['Ei'], len(Y))]})
        recs[k] = rec
    return recs

def heterogeneity(units, recs, H, ctx):
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import KFold
    ks = [k for k, r in recs.items() if r['effects']['ci']['main'] is not None]
    if len(ks) < H['min_ponds']: return None
    y = np.array([recs[k]['effects']['ci']['main'] for k in ks])
    names = ['pond area', 'zone of influence area', 'stream order', 'catchment area', 'MWS cropping intensity before the pond', 'kharif drought weeks after it appeared',
             'first wet year', 'water looks lined', 'water looks unlined', 'hard-rock aquifer', 'plain terrain', 'hilly terrain',
             'groundwater over-exploited or critical', 'canal present', 'semi-arid rainfall'] + [f'{a.replace("_", " ")} share of MWS' for a in ARCH]
    def X_of(u):
        c = ctx.get(u['mws'], {}); E = u['Ei']
        return [math.log1p(u['area']), math.log1p(u.get('zoi_area') or 0), u.get('so') or 0, math.log1p(u.get('catch') or 0),
                np.nanmean(u['bg']['ci'][:E]), u['dwk'][E:].mean(), u['E'], float(u['cls'] == 'lined'), float(u['cls'] == 'unlined'),
                float(c.get('ctx_aquifer') == 'hard_rock'), float(c.get('ctx_terrain') == 'plain'), float(c.get('ctx_terrain') == 'hilly'),
                float(c.get('ctx_gw_category') in ('over_exploited', 'critical')), float(c.get('ctx_canal') == 'canal_present'),
                float(c.get('ctx_rainfall') == 'semi_arid')] + [c.get('share_' + a) or 0 for a in ARCH]
    X = np.nan_to_num(np.array([X_of(units[k]) for k in ks], float)); pred = np.zeros(len(y)); imp = np.zeros(X.shape[1])
    for tr, te in KFold(H['folds'], shuffle=True, random_state=0).split(X):
        m = RandomForestRegressor(n_estimators=H['trees'], min_samples_leaf=H['min_leaf'], max_features=0.4, random_state=0, n_jobs=-1).fit(X[tr], y[tr])
        pred[te] = m.predict(X[te]); imp += m.feature_importances_ / H['folds']
    Z = np.c_[np.ones(len(y)), pred - pred.mean()]; b = np.linalg.lstsq(Z, y, rcond=None)[0]
    e = y - Z @ b; Si = np.linalg.inv(Z.T @ Z); Vc = Si @ (Z.T * e ** 2) @ Z @ Si
    q = np.quantile(pred, [0.2, 0.4, 0.6, 0.8]); grp = np.searchsorted(q, pred)
    gates = [boot(y[grp == g]) for g in range(5)]
    # CLAN in readable units: the forest sees log sizes, the table shows sizes in ha (medians, as they are skewed),
    # cropping intensity in %, yes/no features and system shares as % of ponds or of MWS area
    D = np.nan_to_num(np.array([[units[k]['area'], units[k].get('zoi_area') or 0, units[k].get('so') or 0, units[k].get('catch') or 0] for k in ks], float))
    units_ = ['ha', 'ha', '', 'ha', '%', 'weeks a year', '', '% of ponds', '% of ponds'] + ['% of ponds'] * 6 + ['% of MWS area'] * len(ARCH)
    def disp(j, sel):
        if j < 4 and j != 2: return float(np.median(D[sel, j]))
        v = float(X[sel, j].mean()); return v * 100 if units_[j].startswith('%') or j == 4 else v
    clan = [{'feature': names[j], 'unit': units_[j], 'importance': _r(imp[j]), 'low': _r(disp(j, grp == 0), 2), 'high': _r(disp(j, grp == 4), 2),
             'stat': 'median' if j in (0, 1, 3) else 'mean'} for j in np.argsort(-imp)[:8]]
    return {'n': len(y), 'blp': _r(b[1]), 'blp_se': _r(math.sqrt(Vc[1, 1])), 'gates': gates, 'clan': clan}

def effectiveness(U, S, in_scope, log=print):
    """Older structures (wet since 2017, persistent): ZoI minus MWS cropping intensity, minus the site premium."""
    Y0 = S['years']['series'][0]; P = S['appearance']['persist_share']; mn = S['effectiveness']['min_new_for_premium']
    prem = collections.defaultdict(list)
    for u in U:
        if u['ok'] and S['years']['first_appearance'] <= u['E'] <= S['years']['last_appearance'] and u['persist'] >= P and u['valid_pre']:
            g = np.nanmean(u['zoi']['ci'][:u['Ei']] - u['bg']['ci'][:u['Ei']])
            if np.isfinite(g): prem[(u['district'], u['type'])].append(g)
    premium = {k: float(np.mean(v)) for k, v in prem.items() if len(v) >= mn}
    per, summ = {}, collections.defaultdict(lambda: {'gap': [], 'corr': [], 'prem': [], 'districts': set(), 'n': 0})
    for u in U:
        if not (u['ok'] and u['E'] == Y0 and u['persist'] >= P and u['type'] in in_scope): continue
        g = np.nanmean(u['zoi']['ci'] - u['bg']['ci'])
        if not np.isfinite(g): continue
        s = summ[u['type']]; s['n'] += 1; s['gap'].append(g)
        p = premium.get((u['district'], u['type']))
        per[u['id']] = {'type': u['type'], 'gap': _r(g, 4), 'premium': _r(p, 4), 'corrected': _r(g - p, 4) if p is not None else None}
        if p is not None: s['corr'].append(g - p); s['prem'].append(p); s['districts'].add(u['district'])
    out = []
    for t, s in sorted(summ.items(), key=lambda kv: -kv[1]['n']):
        out.append({'type': t, 'n': s['n'], 'gap': _r(np.mean(s['gap']), 4), 'premium': _r(np.mean(s['prem']), 4) if s['prem'] else None,
                    'corrected': boot(s['corr']) if s['corr'] else {'n': 0}, 'n_districts': len(s['districts'])})
    return per, out, {f'{d}|{t}': _r(v, 4) for (d, t), v in premium.items()}

# ------------------------------------------------------------------ notes
def _pl(label):
    from ..intro_notes import plain_label
    return plain_label(label)

def plural(label):
    """'headwater pond / check dam' -> 'headwater ponds / check dams' (as impPlural in the page)."""
    import re
    return ' / '.join(x + ('es' if re.search(r'(ch|sh|s|x)$', x) else 's') for x in label.split(' / '))

def pts(x, n=1):
    return signed(None if x is None else x * 100, n)

def wb_env(rec, S, labels, group=None):
    L = S['lining']['labels']; e = rec['effects']; sig = rec.get('sig') or {}; g = group or {}
    tl = _pl(labels.get(rec['type'], rec['type'])).lower()
    return {'verdict': rec['verdict'], 'type_label': tl, 'year_label': years_text([rec['E']]), 'year': rec['E'],
            'effect_signed': pts(rec.get('tau')), 'effect_abs': f"{abs((rec.get('tau') or 0) * 100):.1f}",
            'nk_signed': pts(e['nonkharif']['main'] if e['nonkharif']['main'] is not None else e['nonkharif']['early']),
            'has_nk': (e['nonkharif']['main'] if e['nonkharif']['main'] is not None else e['nonkharif']['early']) is not None,
            'post_text': years_text(rec.get('main_years') or rec.get('post_years')), 'n_years': rec.get('n') or 0,
            'early_text': years_text([y for y in rec.get('post_years', []) if y > S['_last_main_year']]),
            'early_signed': pts(e['ci']['early']), 'has_early': e['ci']['early'] is not None and bool(rec.get('main_years')),
            'reason': rec.get('reason') or '', 'cls': rec.get('cls') or '', 'cls_label': L.get(rec.get('cls'), ''),
            'summer_area': f"{sig.get('summer_area', 0):.0f}", 'summer_years': f"{100 * sig.get('summer_years', 0):.0f}",
            'fill_ratio': f"{sig['fill_ratio']:.2f}" if sig.get('fill_ratio') is not None else '–',
            'appeared_2019': 'appeared_2019' in rec.get('flags', []), 'drought_signed': pts(rec.get('drought_main')), 'has_drought': rec.get('drought_main') is not None,
            'group_n': g.get('n', 0), 'group_unit': g.get('unit', ''), 'group_mean_signed': pts(g.get('mean')), 'group_label': g.get('label', 'new ' + plural(tl)),
            'group_cls_n': g.get('cls_n', 0), 'group_cls_mean_signed': pts(g.get('cls_mean'))}

def unit_env(st, label, S):
    c = st.get('by_class') or {}
    f = lambda k, x: (c.get(k) or {}).get(x)
    return {'n': st.get('n', 0), 'min_n': S['averages']['min_n'], 'unit_label': label, 'type_label_plural': st.get('label', 'new farm ponds'),
            'type_label': st.get('label_one', 'new farm pond'),
            'mean_signed': pts(st.get('mean')), 'mean_abs': f"{abs((st.get('mean') or 0) * 100):.1f}", 'lo_signed': pts(st.get('lo')), 'hi_signed': pts(st.get('hi')),
            'lo': st.get('lo') or 0, 'hi': st.get('hi') or 0, 'n_gain': st.get('n_gain', 0), 'n_loss': st.get('n_loss', 0),
            'expected_each': f"{0.1 * st.get('n', 0):.0f}", 'nk_signed': pts(st.get('nk_mean')), 'has_nk': st.get('nk_mean') is not None,
            'n_lined': f('lined', 'n') or 0, 'lined_signed': pts(f('lined', 'mean')), 'n_unlined': f('unlined', 'n') or 0, 'unlined_signed': pts(f('unlined', 'mean')),
            'lined_nk_signed': pts(f('lined', 'nk')), 'unlined_nk_signed': pts(f('unlined', 'nk')),
            'n_early': st.get('n_early', 0), 'early_signed': pts(st.get('early_mean')), 'n_new': st.get('n_new', 0)}

def old_env(o, wtype, labels):
    tl = _pl(labels.get(wtype, wtype)).lower(); g = o.get('gap'); p = o.get('premium'); c = o.get('corrected')
    return {'type_label': tl, 'type_label_plural': plural(tl), 'gap_abs': f"{abs((g or 0) * 100):.1f}", 'gap_dir': 'above' if (g or 0) >= 0 else 'below',
            'premium_abs': f"{abs((p or 0) * 100):.1f}", 'premium_dir': 'below' if (p or 0) < 0 else 'above', 'has_premium': p is not None,
            'corrected_signed': pts(c), 'corrected': c if c is not None else 0}

def unit_stats(ks, recs, units, S, label, rng, classes=CLS):
    sel = [k for k in ks if recs[k]['verdict'] != 'not_assessable']
    main = [recs[k]['effects']['ci']['main'] for k in sel if recs[k]['effects']['ci']['main'] is not None]
    st = {'n_new': len(ks), **boot(main, S['averages']['bootstrap'], rng), 'label': label}
    st['n_gain'] = sum(recs[k]['verdict'] in ('likely_gain', 'early_gain') for k in sel)
    st['n_loss'] = sum(recs[k]['verdict'] in ('likely_loss', 'early_loss') for k in sel)
    nk = [recs[k]['effects']['nonkharif']['main'] for k in sel if recs[k]['effects']['nonkharif']['main'] is not None]
    st['nk_mean'] = _r(np.mean(nk), 4) if nk else None
    ea = [recs[k]['effects']['ci']['early'] for k in sel if recs[k]['effects']['ci']['early'] is not None]
    st['n_early'] = len(ea); st['early_mean'] = _r(np.mean(ea), 4) if ea else None
    st['by_class'] = {}
    for c in classes:
        v = [recs[k]['effects']['ci']['main'] for k in sel if recs[k]['cls'] == c and recs[k]['effects']['ci']['main'] is not None]
        w = [recs[k]['effects']['nonkharif']['main'] for k in sel if recs[k]['cls'] == c and recs[k]['effects']['nonkharif']['main'] is not None]
        st['by_class'][c] = {'n': len(v), 'mean': _r(np.mean(v), 4) if v else None, 'nk': _r(np.mean(w), 4) if w else None}
    st['verdicts'] = dict(collections.Counter(recs[k]['verdict'] for k in ks))
    return st

def _unit_label(kind, v):
    return {'district': f'{v} district', 'tehsil': f'{v.split("/")[-1]} tehsil', 'mws': f'micro-watershed {v}'}[kind]

# ------------------------------------------------------------------ main
def main(wcfg_path=None, out=None, web=True, log=print, seed=7):
    S = settings()
    wcfg = load_json(wcfg_path or ROOT / 'config' / 'waterbody' / 'locations.json')
    import os, pickle
    cache = os.environ.get('SEFT_FP_CACHE')       # optional: reuse the loaded panel between runs (a pickle path)
    if cache and Path(cache).exists():
        B, MWS = pickle.load(open(cache, 'rb')); log(f'  panel from {cache}')
    else:
        B, MWS = load_panel(wcfg, S['years']['series'], log)
        if cache: pickle.dump((B, MWS), open(cache, 'wb'))
    return run_panel(B, MWS, S, out, web, log, seed)

def run_panel(B, MWS, S=None, out=None, web=True, log=print, seed=7):
    """Everything after loading: units, estimates, records, averages, notes and bundles (used by main and tests)."""
    warnings.filterwarnings('ignore')
    S = S or settings(); R = note_rules(); rng = np.random.default_rng(seed)
    Y = S['years']['series']; yi = {y: i for i, y in enumerate(Y)}; NY = len(Y)
    S['_last_main'] = yi[S['years']['last_main']]; S['_last_main_year'] = S['years']['last_main']
    from .run import type_labels
    labels, in_scope = type_labels()
    ctx = mws_context(sorted({b['district'] for b in B}))
    U = make_units(B, MWS, S, log)
    for u in U: u['Ei'] = yi[u['E']]
    I = S['intervention']; A = S['appearance']; L = {**S['lining'], 'drought_weeks': S['drought']['min_weeks']}
    est = next(e for e in S['estimators'] if e['id'] == 'imputation'); dd = next(e for e in S['estimators'] if e['id'] == 'did_district')
    first, lastA = S['years']['first_appearance'], S['years']['last_appearance']
    # lining for every pond of the assessed types (shown in the waterbody note)
    lin = {}
    for u in U:
        if u['type'] in S['lining'].get('types', I['types']) and u['persist'] >= A['persist_share']:
            s = lining(u['k'], u['kr'], u['krz'], {y: v for y, v in zip(Y, u['dweeks']) if np.isfinite(v)}, u['E'], Y, L)
            if s: u['sig'] = {k: (_r(v, 3) if isinstance(v, float) else v) for k, v in s.items()}; u['cls'] = s['cls']; lin[u['id']] = u
    records, summary, by_unit = {}, {'types': {}}, {}
    for typ in I['types']:
        cand = [u for u in U if u['type'] == typ and first <= u['E'] <= max(lastA, Y[-1]) and u['persist'] >= A['persist_share']]
        units = [u for u in cand if u['E'] <= lastA and u['valid_pre'] and u['ok']]
        classed = typ in S['lining'].get('types', I['types'])          # lined/unlined split for farm ponds only
        CL = CLS if classed else ()
        for u in units:
            if classed: u.setdefault('cls', 'uncertain')
            else: u['cls'] = None
            u.setdefault('sig', None)
        log(f'  {typ}: {len(cand)} new since {first}, {len(units)} assessable (first wet {first}-{lastA}, qualifying pre year, ZoI cropping)')
        OUT_, Ms = {}, {}
        for oc in OUTS:
            Ms[oc] = fit_imputation(units, oc, NY); OUT_[oc] = impute_cells(units, oc, Ms[oc], NY, est['min_cell'])
        Mh = fit_imputation(units, 'ci', NY, hold=True); hold = impute_cells(units, 'ci', Mh, NY, est['min_cell'], hold=True)
        recs = pond_records(units, OUT_, hold, S, rng)
        # summary: outcomes by class and period; same-district DiD; placebo
        T = {'n_candidates': len(cand), 'n_assessed': len(units), 'n_districts': len({u['district'] for u in units}),
             'classes': dict(collections.Counter(u['cls'] for u in units)) if classed else None, 'gamma': _r(Ms['ci']['beta'][0]) if Ms['ci'] else None,
             'delta': _r(Ms['ci']['beta'][1], 5) if Ms['ci'] else None, 'support': dict(collections.Counter(c[4] for c in OUT_['ci'])),
             'placebo': boot([c[2] for c in hold], 500, rng), 'placebo_sd': _r(np.std([c[2] for c in hold]), 4) if hold else None, 'outcomes': {}, 'did': {}, 'by_appearance': {}, 'event': {}}
        for oc in OUTS:
            T['outcomes'][oc] = {}
            for c in ('all',) + CL:
                inc = lambda k: c == 'all' or units[k]['cls'] == c
                main = [recs[k]['effects'][oc]['main'] for k in recs if inc(k) and recs[k]['effects'][oc]['main'] is not None]
                early = [recs[k]['effects'][oc]['early'] for k in recs if inc(k) and recs[k]['effects'][oc]['early'] is not None]
                cm = [x for x in OUT_[oc] if inc(x[0]) and x[1] <= S['_last_main']]
                T['outcomes'][oc][c] = {'main': boot(main, 500, rng), 'early': boot(early, 500, rng),
                                        'normal': _r(np.mean([x[2] for x in cm if x[3] == 0]), 4) if any(x[3] == 0 for x in cm) else None,
                                        'drought': _r(np.mean([x[2] for x in cm if x[3] == 1]), 4) if any(x[3] == 1 for x in cm) else None,
                                        'n_drought_cells': sum(1 for x in cm if x[3] == 1)}
        for oc in ('ci', 'nonkharif'):
            T['did'][oc] = {}
            for c in ('all',) + CL:
                sub = units if c == 'all' else [u for u in units if u['cls'] == c]
                T['did'][oc][c] = {cov: did_district(sub, oc, S['_last_main'], dd['min_n'], cov, rng=rng) for cov in ('none', 'size', 'mws')}
        for g in range(first, lastA + 1):
            v = [x[2] for x in OUT_['ci'] if units[x[0]]['E'] == g]
            if v: T['by_appearance'][g] = {'mean': _r(np.mean(v), 4), 'n_cells': len(v)}
        ev = collections.defaultdict(list)
        for x in OUT_['ci']: ev[x[1] - units[x[0]]['Ei']].append(x[2])
        T['event'] = {e: {'mean': _r(np.mean(v), 4), 'n_cells': len(v)} for e, v in sorted(ev.items())}
        T['heterogeneity'] = heterogeneity(units, recs, S['heterogeneity'], ctx)
        bd = collections.defaultdict(list)
        for k, r in recs.items():
            if r['effects']['ci']['main'] is not None: bd[units[k]['district']].append(r['effects']['ci']['main'])
        T['by_district'] = {d: boot(v, 300, rng) for d, v in sorted(bd.items())}
        summary['types'][typ] = T
        # averages by unit, then the notes
        tl = _pl(labels.get(typ, typ)).lower(); tlp = 'new ' + plural(tl)
        groups = {kind: collections.defaultdict(list) for kind in S['averages']['units']}
        for k, u in enumerate(units):
            groups['district'][u['district']].append(k); groups['tehsil'][f"{u['district']}/{u['tehsil']}"].append(k)
            if u['mws']: groups['mws'][u['mws']].append(k)
        for kind, G in groups.items():
            for v, ks in G.items():
                st = unit_stats(ks, recs, units, S, tlp, rng, CL); st['label_one'] = 'new ' + tl
                st['note'] = render('fp_unit', unit_env(st, _unit_label(kind, v), S), R)
                by_unit.setdefault(kind, {}).setdefault(v, {})[typ] = st
        for k, rec in recs.items():
            u = units[k]; dst = by_unit['district'][u['district']][typ]
            cs = dst['by_class'].get(u['cls']) or {}
            g = {'n': dst['n'], 'unit': f"{u['district']} district", 'mean': dst.get('mean'), 'label': tlp,
                 'cls_n': cs.get('n', 0) if u['cls'] in ('lined', 'unlined') else 0, 'cls_mean': cs.get('mean')}
            rec.update(type=typ, id=u['id'], district=u['district'], tehsil=u['tehsil'], mws=u['mws'], area=_r(u['area'], 2), group=g)
            rec['note'] = render('fp_waterbody', wb_env(rec, S, labels, g), R)
            records[str(u['id'])] = rec
        for u in cand:
            if str(u['id']) in records: continue
            reason = ('there is no year of cropping data after it yet' if u['E'] > lastA else
                      'it has no zone of influence with cropping data' if not u['ok'] else
                      'none of the years before it appeared was a normal year in which most waterbodies of its micro-watershed held water, so it may have existed but been dry')
            rec = {'type': typ, 'id': u['id'], 'district': u['district'], 'tehsil': u['tehsil'], 'mws': u['mws'], 'area': _r(u['area'], 2), 'E': u['E'],
                   'cls': u.get('cls'), 'sig': u.get('sig'), 'verdict': 'not_assessable', 'reason': reason, 'effects': None, 'flags': []}
            rec['note'] = render('fp_waterbody', {**wb_env({**rec, 'effects': {o: {'main': None, 'early': None} for o in OUTS}}, S, labels), 'reason': reason}, R)
            records[str(u['id'])] = rec
    per_old, eff, premium = effectiveness(U, S, in_scope, log)
    for wid, o in per_old.items():
        o['note'] = render('fp_old', old_env(o, o['type'], labels), R) if o.get('corrected') is not None else ''
    summary['effectiveness'] = eff; summary['premium'] = premium
    write(records, by_unit, summary, per_old, lin, U, S, out, web, log)
    return records, summary

SIG = ('summer_area', 'summer_years', 'rabi_area', 'kharif_area', 'fill_ratio')

def bundle_record(r):
    """A pond's record as shipped to the atlas (fp_<district>.json): without the note, which the page writes from
    the same rules (fp.json notes) so the bundles stay small; signs as [summer area %, share of years with summer
    water, rabi %, kharif %, drought/normal fill]."""
    o = {k: v for k, v in r.items() if k not in ('district', 'id', 'group', 'support', 'placebo_pct', 'note')}
    if o.get('sig'): o['sig'] = [o['sig'].get(k) for k in SIG]
    for e in (o.get('effects') or {}).values(): e.pop('n_main', None); e.pop('n_early', None)
    return o

def bundle_old(o):
    """An older structure's effectiveness as shipped: [gap, premium, corrected] (the page writes the note)."""
    return [o.get('gap'), o.get('premium'), o.get('corrected')]

def write(records, by_unit, summary, per_old, lin, U, S, out=None, web=True, log=print):
    from .run import _finite
    out = Path(out or OUT); (out / 'web').mkdir(parents=True, exist_ok=True)
    dist_of = {u['id']: u['district'] for u in U}
    by = collections.defaultdict(lambda: {'waterbodies': {}, 'lining': {}, 'old': {}, 'units': {'tehsil': {}, 'mws': {}}})
    for wid, r in records.items(): by[r['district']]['waterbodies'][wid] = bundle_record(r)
    for wid, u in lin.items():
        s = u['sig']; by[u['district']]['lining'][str(wid)] = [{'lined': 'L', 'unlined': 'U', 'uncertain': '?'}[s['cls']], _r(s['summer_area'], 0), _r(100 * s['summer_years'], 0),
                                                              _r(s['fill_ratio'], 2) if s.get('fill_ratio') is not None else None, u['E']]
    for wid, o in per_old.items():
        if dist_of.get(wid): by[dist_of[wid]]['old'][str(wid)] = bundle_old(o)
    mws_d = {r['mws']: r['district'] for r in records.values() if r.get('mws')}
    for kind in ('tehsil', 'mws'):
        for v, st in (by_unit.get(kind) or {}).items():
            d = v.split('/')[0] if kind == 'tehsil' else mws_d.get(v)
            if d: by[d]['units'][kind][v.split('/')[-1] if kind == 'tehsil' else v] = st
    refs = references()
    Sx = {k: v for k, v in S.items() if not k.startswith('_')}
    idx = {'settings': Sx, 'references': refs['references'], 'summary': summary,
           'districts': [{'district': d, 'slug': slug(d), 'n_records': len(v['waterbodies']), 'n_lining': len(v['lining']), 'n_old': len(v['old'])} for d, v in sorted(by.items())],
           'averages': {'district': by_unit.get('district', {})}, 'panel': note_rules().get('fp_panel', {}),
           'notes': {k: note_rules()[k] for k in ('fp_waterbody', 'fp_old')}}
    (out / 'records.json').write_text(json.dumps(_finite(records), indent=1, ensure_ascii=False), encoding='utf-8')
    (out / 'summary.json').write_text(json.dumps(_finite(summary), indent=1, ensure_ascii=False), encoding='utf-8')
    (out / 'review.md').write_text(review(summary, S), encoding='utf-8')
    files = {'fp': idx, **{f'fp_{slug(d)}': {'district': d, **v} for d, v in by.items()}}
    for n, o in files.items():
        (out / 'web' / f'{n}.json').write_text(json.dumps(_finite(o), separators=(',', ':'), ensure_ascii=False, allow_nan=False), encoding='utf-8')
    log(f'  wrote {out}/records.json ({len(records)} ponds), summary.json, review.md, web/ ({len(files)} bundles)')
    if web:
        from ..webdata import write_js
        WEB.mkdir(parents=True, exist_ok=True)
        for f in list(WEB.glob('fp_*.json')) + list(WEB.glob('wb_fp_*.js')): f.unlink()
        for n in files:
            text = (out / 'web' / f'{n}.json').read_text(encoding='utf-8')
            (WEB / f'{n}.json').write_text(text, encoding='utf-8'); write_js(f'wb_{n}', text, WEB)
        log(f'  copied to {WEB.relative_to(ROOT)}')

def review(summary, S):
    L = ['# New farm ponds: impact review', '']
    f = lambda b: '–' if not b or not b.get('n') else f"{100 * b['mean']:+.1f} ({100 * b['lo']:+.1f}, {100 * b['hi']:+.1f}) n={b['n']}"
    p1 = lambda v: '–' if v is None else f'{100 * v:+.1f}'
    for typ, T in summary['types'].items():
        L += [f'## {typ}', '', f"{T['n_candidates']} new since {S['years']['first_appearance']}; {T['n_assessed']} assessed in {T['n_districts']} districts; classes {T['classes']}.",
              f"Placebo (year before): {f(T['placebo'])} points. Model: background coefficient {T['gamma']}, drought weeks {T['delta']}; support {T['support']}.", '',
              '| Outcome | Class | Up to ' + str(S['years']['last_main']) + ' (points) | Normal years | Drought years | Later years (early) |', '| --- | --- | --- | --- | --- | --- |']
        for oc, D in T['outcomes'].items():
            for c, x in D.items():
                L.append(f"| {oc} | {c} | {f(x['main'])} | {p1(x['normal'])} | {p1(x['drought'])} | {f(x['early'])} |")
        L += ['', '| Same-district DiD | Class | No covariates | Size | Size + MWS |', '| --- | --- | --- | --- | --- |']
        for oc, D in T['did'].items():
            for c, x in D.items():
                g = lambda v: '–' if not v else f"{100 * v['mean']:+.1f} ({100 * v['lo']:+.1f}, {100 * v['hi']:+.1f})"
                L.append(f"| {oc} | {c} | {g(x['none'])} | {g(x['size'])} | {g(x['mws'])} |")
        H = T.get('heterogeneity')
        if H:
            L += ['', f"Heterogeneity: BLP {H['blp']} (SE {H['blp_se']}); GATES " + '; '.join(f(g) for g in H['gates'])]
            L += [f"- {c['feature']}: importance {c['importance']}, lowest group {c['low']}, highest {c['high']}" for c in H['clan']]
        L.append('')
    L += ['## Older structures (site-premium corrected)', '', '| Type | n | Gap | Premium | Corrected |', '| --- | --- | --- | --- | --- |']
    for e in summary['effectiveness']:
        L.append(f"| {e['type']} | {e['n']} | {p1(e['gap'])} | {p1(e['premium'])} | {f(e['corrected'])} |")
    return '\n'.join(L) + '\n'
