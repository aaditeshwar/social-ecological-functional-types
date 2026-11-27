"""The pool of waterbodies that treated waterbodies and their controls are drawn from.

Built from atlas waterbodies (seft.wb.build records: type, area, drainage, catchment, home MWS, centroid and the
yearly k / kr / krz series) plus, per home MWS, the yearly rainfall and kharif drought weeks from the cached
tehsil data and the MWS landscape context (from the waterbody atlas bundles or from records scored in a session).
"""
import json, math
from pathlib import Path
import numpy as np
from ..util import ROOT, raw_dir, slug, load_json

CTX_KEYS = ('ctx_rainfall', 'ctx_aquifer', 'ctx_terrain', 'ctx_gw_category', 'ctx_canal', 'ctx_cropping', 'dominant_system')


class _Ball:
    """query_ball_point like scipy.spatial.cKDTree, using numpy only (App Control blocks scipy DLLs on some Windows)."""
    def __init__(self, xy):
        self.xy = np.asarray(xy, float)

    def query_ball_point(self, pt, r):
        d = self.xy - np.asarray(pt, float)
        return np.flatnonzero((d * d).sum(axis=1) <= r * r).tolist()

def mws_years(state, district, tehsil):
    """{mws uid: {'rain': {year: mm}, 'drought': {year: weeks}}} from hydrological_annual and croppingdrought_kharif."""
    out = {}
    d = raw_dir(state, district, tehsil)
    try:
        for r in load_json(d / 'hydrological_annual.json')['rows']:
            a = r['annual']; u = r['metadata']['uid']
            out.setdefault(u, {})['rain'] = {int(t): v for t, v in zip(a['time'], a['precipitation'])}
    except (FileNotFoundError, KeyError): pass
    try:
        for r in load_json(d / 'croppingdrought_kharif.json')['rows']:
            a = r['annual']; u = r['metadata']['uid']
            out.setdefault(u, {})['drought'] = {int(t): (a['moderate'][i] or 0) + (a['severe'][i] or 0) for i, t in enumerate(a['time'])}
    except (FileNotFoundError, KeyError): pass
    return out

def bundle_ctx(district):
    """MWS context from the waterbody atlas bundle of a district (out/waterbody/web first, then web/data/waterbody)."""
    s = slug(district)
    for p in (ROOT / 'out' / 'waterbody' / 'web' / f'w_{s}.json', ROOT / 'web' / 'data' / 'waterbody' / f'w_{s}.json'):
        if p.exists():
            m = json.loads(p.read_text(encoding='utf-8-sig')).get('mws', {})
            return {u: {k: v.get(k) for k in CTX_KEYS} for u, v in m.items()}
    return {}

def _arr(xs, n):
    xs = list(xs or [])[:n] + [None] * max(0, n - len(xs or []))
    return np.array([np.nan if v is None else float(v) for v in xs], float)

class Pool:
    """Waterbodies with aligned yearly arrays. `years` are hydrological years (int)."""
    def __init__(self, bodies, years, in_scope, ctx_by_mws=None, mws_series=None):
        self.years = list(years); T = len(self.years)
        seen, B = set(), []
        for b in bodies:
            key = str(b['wb_id'])
            if key in seen: continue                       # the same waterbody listed under two tehsils
            seen.add(key); B.append(b)
        self.bodies = B; n = len(B)
        self.key = [str(b['wb_id']) for b in B]
        self.index = {k: i for i, k in enumerate(self.key)}
        yi = {y: j for j, y in enumerate(self.years)}
        def aligned(b, name):
            ys = [int(y) for y in (b.get('years') or [])]; v = b.get(name) or []
            a = np.full(T, np.nan)
            for y, x in zip(ys, v):
                if y in yi and x is not None: a[yi[y]] = float(x)
            return a
        k = np.array([aligned(b, 'k') for b in B]).reshape(n, T)
        kr = np.array([aligned(b, 'kr') for b in B]).reshape(n, T)
        krz = np.array([aligned(b, 'krz') for b in B]).reshape(n, T)
        self.O = {'W': 17.3 * (k + kr + krz) / 100}
        with np.errstate(invalid='ignore', divide='ignore'):
            self.O['RR'] = np.where(k >= 10, kr / k, np.nan); self.O['SR'] = np.where(k >= 10, krz / k, np.nan)
        self.type = [b.get('type') for b in B]
        self.in_scope = np.array([b.get('type') in in_scope for b in B])
        self.area = np.array([b.get('area_ha') or 0.0 for b in B])
        self.catch = np.array([b.get('catchment_ha') or 0.0 for b in B])
        self.so = np.array([b.get('stream_order') or 0 for b in B], float)
        self.mws = [b.get('home_mws') for b in B]
        self.district = [b.get('district') for b in B]; self.state = [b.get('state') for b in B]; self.tehsil = [b.get('tehsil') for b in B]
        xy = np.array([b.get('centroid') or [np.nan, np.nan] for b in B], float).reshape(n, 2)
        self.lonlat = xy
        lat0 = np.nanmean(xy[:, 1]) if n else 20.0
        self.xy_km = np.c_[xy[:, 0] * 111.32 * math.cos(math.radians(lat0)), xy[:, 1] * 110.57]
        ms = mws_series or {}
        self.rain = np.array([[((ms.get(m) or {}).get('rain') or {}).get(y, np.nan) for y in self.years] for m in self.mws], float).reshape(n, T)
        self.drought = np.array([[((ms.get(m) or {}).get('drought') or {}).get(y, np.nan) for y in self.years] for m in self.mws], float).reshape(n, T)
        cb = ctx_by_mws or {}
        self.ctx = [(b.get('mws') if isinstance(b.get('mws'), dict) else None) or cb.get(b.get('home_mws')) or {} for b in B]
        ok = np.isfinite(self.xy_km).all(axis=1)
        self.tree = _Ball(np.where(ok[:, None], self.xy_km, 1e9))

def pool_years(bodies):
    ys = sorted({int(y) for b in bodies for y in (b.get('years') or [])})
    return ys

def load_mws_series(tehsils):
    """Rain and drought by MWS for (state, district, tehsil) triples."""
    out = {}
    for s, d, t in tehsils: out.update(mws_years(s, d, t))
    return out
