"""Controls, the four estimators, placebos, the untreated reference and the verdict (knowledge/impact/settings.json).

Notation: T = the treated waterbody, C = its matched controls, P = pre years, Q = post years.
  did             [mean_Q W_T - mean_P W_T] - mean over C of [mean_Q W_c - mean_P W_c]
  did_rain        per post year q, the pre year p* minimising |dR_T| + w |dR_T - dR_C| (dR = R(q) - R(p));
                  [W_T(q) - W_T(p*)] - mean_C [W_c(q) - W_c(p*)], averaged over q
  prepost_rain    per post year q, the pre year with the closest rainfall at T; W_T(q) - W_T(p*), averaged (no controls)
  counterfactual  fit W_T(t) = a + b mean_C W_c(t) over P; mean over Q of W_T(q) - a - b mean_C W_c(q)
"""
import random
import warnings
import numpy as np
warnings.filterwarnings("ignore", category=RuntimeWarning, module=__name__)

OUTCOMES = ('W', 'RR', 'SR')

def _nm(a):
    a = np.asarray(a, float)
    return float(np.nanmean(a)) if np.isfinite(a).any() else np.nan

class Estimator:
    def __init__(self, pool, settings, treated=None):
        """treated: {pool key: [intervention years]} for every registered intervention in the pool (may be empty)."""
        self.P, self.S = pool, settings
        self.M = settings['matching']
        self.treated = {k: sorted(set(v)) for k, v in (treated or {}).items() if k in pool.index}
        self._vi, self._near, self._ref = {}, {}, {}
        self.yi = {y: j for j, y in enumerate(pool.years)}

    # ---------------------------------------------------------------- matching
    def _feats(self, pre, district=None):
        """Feature matrix for a pre-period and the inverse covariance over the in-scope waterbodies of the district
        (so a run over many districts and a single-district analyse call choose the same controls)."""
        key = (tuple(pre), district)
        if key in self._vi: return self._vi[key]
        P = self.P; W = P.O['W'][:, pre]; RR = P.O['RR'][:, pre]
        with np.errstate(invalid='ignore'):
            cols = [np.log1p(P.area), np.log1p(P.catch), P.so,
                    np.nanmean(P.rain[:, pre], axis=1) if len(pre) else np.zeros(len(P.area)),
                    np.nanmean(P.drought[:, pre], axis=1) if len(pre) else np.zeros(len(P.area)),
                    np.nanmean(RR, axis=1) if len(pre) else np.zeros(len(P.area))] + [W[:, j] for j in range(len(pre))]
        X = np.column_stack(cols).astype(float)
        sc = P.in_scope & np.isfinite(X).any(axis=1)
        if district is not None: sc = sc & (np.array(P.district) == district)
        med = np.nanmedian(X[sc], axis=0) if sc.any() else np.zeros(X.shape[1])
        med = np.where(np.isfinite(med), med, 0)
        X = np.where(np.isnan(X), med, X)
        V = np.cov(X[sc].T) if sc.sum() > X.shape[1] else np.eye(X.shape[1])
        VI = np.linalg.pinv(np.atleast_2d(V))
        self._vi[key] = (X, VI); return X, VI

    def _near_treated(self, lo, hi):
        """Pool rows within exclude_near_treated_m of a waterbody treated in [lo, hi]."""
        key = (lo, hi)
        if key in self._near: return self._near[key]
        P = self.P; r = self.M.get('exclude_near_treated_m', 200) / 1000
        bad = set()
        for k, ys in self.treated.items():
            if any(lo <= y <= hi for y in ys):
                i = P.index[k]; bad.add(i)
                if r > 0: bad.update(P.tree.query_ball_point(P.xy_km[i], r))
        self._near[key] = bad; return bad

    def controls(self, i, pre, post, exclude=()):
        """Indices of the matched controls of pool row i for a window, and a dict describing the search."""
        P = self.P; years = [P.years[j] for j in list(pre) + list(post)]
        bad = self._near_treated(min(years), max(years)) | set(exclude) | {i}
        cand = [j for j in P.tree.query_ball_point(P.xy_km[i], self.M['radius_km'])
                if j not in bad and P.in_scope[j] and P.type[j] == P.type[i]
                and not (self.M.get('exclude_own_mws', True) and P.mws[i] and P.mws[j] == P.mws[i])]
        if not cand: return [], {'candidates': 0, 'radius_km': self.M['radius_km']}
        X, VI = self._feats(pre, P.district[i])
        d = X[cand] - X[i]; m = np.sqrt(np.maximum(np.einsum('ij,jk,ik->i', d, VI, d), 0))
        o = np.argsort(m)[:self.M['n_controls']]
        return [cand[j] for j in o], {'candidates': len(cand), 'radius_km': self.M['radius_km'],
                                      'median_distance': round(float(np.median(m[o])), 2)}

    # ---------------------------------------------------------------- estimators
    def _did(self, i, C, oc, pre, post):
        y = self.P.O[oc]; dt = _nm(y[i, post]) - _nm(y[i, pre])
        dc = [_nm(y[j, post]) - _nm(y[j, pre]) for j in C]; dc = [v for v in dc if np.isfinite(v)]
        return dt - float(np.mean(dc)) if dc and np.isfinite(dt) else np.nan

    def _rain_pairs(self, i, C, pre, post, controls=True):
        R = self.P.rain; Rt = R[i]; Rc = np.nanmean(R[C], axis=0) if C else np.full(len(Rt), np.nan)
        w = next((e.get('rain_weight', 3) for e in self.S['estimators'] if e['id'] == 'did_rain'), 3)
        out = []
        for q in post:
            def cost(p):
                a = abs(Rt[q] - Rt[p]); b = abs((Rt[q] - Rt[p]) - (Rc[q] - Rc[p])) if controls else 0
                return (a + w * b) if np.isfinite(a) and np.isfinite(b) else np.inf
            p = min(pre, key=cost)
            if np.isfinite(cost(p)): out.append((q, p))
        return out

    def _did_rain(self, i, C, oc, pre, post):
        y = self.P.O[oc]; vals = []
        for q, p in self._rain_pairs(i, C, pre, post):
            dc = [y[j, q] - y[j, p] for j in C]; dc = [v for v in dc if np.isfinite(v)]
            dt = y[i, q] - y[i, p]
            if np.isfinite(dt) and dc: vals.append(dt - np.mean(dc))
        return float(np.mean(vals)) if vals else np.nan

    def _prepost(self, i, C, oc, pre, post):
        y = self.P.O[oc]
        vals = [y[i, q] - y[i, p] for q, p in self._rain_pairs(i, C, pre, post, controls=False)]
        vals = [v for v in vals if np.isfinite(v)]
        return float(np.mean(vals)) if vals else np.nan

    def _cf(self, i, C, oc, pre, post):
        y = self.P.O[oc]; yt = y[i]
        if not C: return np.nan
        with np.errstate(invalid='ignore'): yc = np.nanmean(y[C], axis=0)
        ok = [t for t in pre if np.isfinite(yt[t]) and np.isfinite(yc[t])]
        need = next((e.get('min_pre_years', 4) for e in self.S['estimators'] if e['id'] == 'counterfactual'), 4)
        if len(ok) < need or np.nanstd(yc[ok]) == 0: return np.nan
        b, a = np.polyfit(yc[ok], yt[ok], 1)
        res = [yt[t] - (a + b * yc[t]) for t in post if np.isfinite(yt[t]) and np.isfinite(yc[t])]
        return float(np.mean(res)) if res else np.nan

    def effects(self, i, C, pre, post, placebos=True):
        out = {}
        for oc in OUTCOMES:
            e = {'did': self._did(i, C, oc, pre, post), 'did_rain': self._did_rain(i, C, oc, pre, post),
                 'prepost_rain': self._prepost(i, C, oc, pre, post), 'counterfactual': self._cf(i, C, oc, pre, post)}
            if placebos:
                pl = {}
                y0 = self.P.years[post[0]]
                for off in self.S.get('placebo_offsets', [2, 3]):
                    fake = y0 - off
                    pre_f = [t for t in pre if self.P.years[t] < fake]; post_f = [t for t in pre if self.P.years[t] >= fake]
                    if len(pre_f) >= 3 and post_f: pl[str(fake)] = self._did(i, C, oc, pre_f, post_f)
                e['placebo'] = pl
            out[oc] = e
        return out

    # ---------------------------------------------------------------- reference
    def reference(self, district, wtype, pre, post):
        """DiD of untreated waterbodies of this district and type (all in-scope types if too few), as if treated."""
        key = (district, wtype, tuple(pre), tuple(post))
        if key in self._ref: return self._ref[key]
        P, R = self.P, self.S['reference']
        years = [P.years[j] for j in list(pre) + list(post)]
        bad = self._near_treated(min(years), max(years))
        base = [j for j in range(len(P.key)) if P.district[j] == district and P.in_scope[j] and j not in bad and P.key[j] not in self.treated]
        same = [j for j in base if P.type[j] == wtype]
        rows, scope = (same, 'type') if len(same) >= R['min_n'] else (base, 'district')
        rows = sorted(rows, key=lambda j: P.key[j])          # same sample whatever the pool's order
        rng = random.Random(R.get('seed', 7)); rows = rng.sample(rows, min(R['sample'], len(rows)))
        vals = {oc: [] for oc in OUTCOMES}
        for j in rows:
            C, _ = self.controls(j, pre, post)
            if len(C) < self.M['min_controls']: continue
            e = self.effects(j, C, pre, post, placebos=False)
            for oc in OUTCOMES:
                if np.isfinite(e[oc]['did']): vals[oc].append(e[oc]['did'])
        ref = {'scope': scope, 'n': len(vals['W']), **{oc: np.array(v) for oc, v in vals.items()}}
        self._ref[key] = ref; return ref

    # ---------------------------------------------------------------- one intervention window
    def assess(self, i, y_first, y_last_post=None, next_year=None):
        """Effect for pool row i of an intervention (or interventions) starting in y_first. Post years run from
        y_first (or y_last_post's start for a combined window) up to next_year - 1 or the last year with data."""
        P, S = self.P, self.S
        pre = [j for j, y in enumerate(P.years) if y < y_first]
        start = y_last_post if y_last_post is not None else y_first
        post = [j for j, y in enumerate(P.years) if y >= start and (next_year is None or y < next_year)]
        rec = {'pre_years': [P.years[j] for j in pre], 'post_years': [P.years[j] for j in post]}
        reasons = []
        if not P.in_scope[i]: reasons.append('its type is out of the atlas scope')
        if not post: reasons.append('no year of water data after the work yet')
        if len(pre) < S.get('min_pre_years', 4): reasons.append(f'fewer than {S.get("min_pre_years", 4)} years of data before the work')
        if reasons:
            return {**rec, 'verdict': 'not_assessable', 'reason': '; '.join(reasons)}
        C, info = self.controls(i, pre, post)
        rec['controls'] = {**info, 'n': len(C), 'ids': [P.key[j] for j in C]}
        if len(C) < self.M['min_controls']:
            return {**rec, 'verdict': 'not_assessable',
                    'reason': f'only {len(C)} similar untreated waterbodies within {self.M["radius_km"]} km (at least {self.M["min_controls"]} needed)'}
        eff = self.effects(i, C, pre, post)
        ref = self.reference(P.district[i], P.type[i], pre, post)
        rec['reference'] = {'scope': ref['scope'], 'n': ref['n']}
        for oc in OUTCOMES:
            r = ref[oc]; v = eff[oc]['did']
            eff[oc]['percentile'] = round(float((r < v).mean() * 100)) if len(r) and np.isfinite(v) else None
            eff[oc]['reference_mean'] = round(float(r.mean()), 3) if len(r) else None
        rec['effects'] = _round(eff)
        rec['verdict'], rec['reason'] = self.verdict(eff['W'], ref['W'])
        return rec

    def verdict(self, e, ref):
        V = self.S['verdict']; pct = e.get('percentile')
        if pct is None or not np.isfinite(e['did']): return 'not_assessable', 'the estimate could not be computed'
        if V['loss_pct'] < pct < V['gain_pct']: return 'no_change', ''
        why = []
        lo, hi = (np.percentile(ref, V['placebo_band'][0]), np.percentile(ref, V['placebo_band'][1])) if len(ref) else (-np.inf, np.inf)
        pl = [x for x in (e.get('placebo') or {}).values() if np.isfinite(x)]
        if any(x < lo or x > hi for x in pl) or any(abs(x) > abs(e['did']) for x in pl):
            why.append('the waterbody already moved apart from its controls before the work (placebo check)')
        cf = e.get('counterfactual')
        if cf is not None and np.isfinite(cf) and np.sign(cf) != np.sign(e['did']):
            why.append('the counterfactual model points the other way')
        if why: return 'inconclusive', ' and '.join(why)
        return ('likely_gain' if pct >= V['gain_pct'] else 'likely_loss'), ''

def _round(o, n=3):
    if isinstance(o, dict): return {k: _round(v, n) for k, v in o.items()}
    if isinstance(o, (float, np.floating)): return None if not np.isfinite(o) else round(float(o), n)
    return o
