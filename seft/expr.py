"""Safe expression evaluator used by every knowledge JSON.

Experts write formulas and conditions as short Python-like expressions, e.g.

    div(lulc.tree_forest_area, area)            # a series (one value per year)
    mean(div(ci.doubly_cropped_area, crop_area)) # a scalar
    slope(hydro.welldepth) < -0.25 and aquifer_class == 'Hard Rock'

Only arithmetic, comparisons, boolean logic, conditional expressions, attribute
access on dataset aliases, list literals, `in`, and the whitelisted functions
below are allowed. Anything else raises ExprError, so a JSON file cannot run
arbitrary code.

Series are numpy float arrays aligned on the agricultural years 2017..2024 (NaN
where missing). Arithmetic between a series and a scalar or another series is
element-wise.
"""
import ast, math
import numpy as np

class ExprError(Exception):
    pass

NAN = float('nan')

def _arr(x):
    if isinstance(x, np.ndarray):
        return x
    if isinstance(x, (list, tuple)):
        return np.array([NAN if v is None else v for v in x], dtype=float)
    return None

def _isnan(x):
    return x is None or (isinstance(x, float) and math.isnan(x))

def _scalar(x):
    a = _arr(x)
    return a if a is None else a

def _valid(a):
    a = _arr(a)
    return a[~np.isnan(a)] if a is not None else np.array([])

# ---------- aggregation / transform functions ----------

def f_mean(x):
    v = _valid(x) if _arr(x) is not None else np.array([x], float)
    return float(v.mean()) if v.size else NAN

def f_median(x):
    v = _valid(x)
    return float(np.median(v)) if v.size else NAN

def f_sum(x):
    if _arr(x) is None:
        return NAN if _isnan(x) else float(x)
    v = _valid(x)
    return float(v.sum()) if v.size else NAN

def f_min(*xs):
    if len(xs) == 1 and _arr(xs[0]) is not None:
        v = _valid(xs[0]); return float(v.min()) if v.size else NAN
    v = [x for x in xs if not _isnan(x)]
    return min(v) if v else NAN

def f_max(*xs):
    if len(xs) == 1 and _arr(xs[0]) is not None:
        v = _valid(xs[0]); return float(v.max()) if v.size else NAN
    v = [x for x in xs if not _isnan(x)]
    return max(v) if v else NAN

def f_first(x):
    v = _valid(x); return float(v[0]) if v.size else NAN

def f_last(x):
    v = _valid(x); return float(v[-1]) if v.size else NAN

def f_range(x):
    v = _valid(x); return float(v.max() - v.min()) if v.size else NAN

def f_std(x):
    v = _valid(x); return float(v.std(ddof=1)) if v.size > 1 else NAN

def f_cv(x):
    v = _valid(x)
    if v.size < 3: return NAN
    m = v.mean()
    return float(v.std(ddof=1) / abs(m)) if m else NAN

def f_slope(x):
    """Theil-Sen slope per year (robust to one bad year). Needs >= 4 valid years."""
    a = _arr(x)
    if a is None: return NAN
    idx = np.where(~np.isnan(a))[0]
    if idx.size < 4: return NAN
    s = [(a[j] - a[i]) / (j - i) for k, i in enumerate(idx) for j in idx[k + 1:]]
    return float(np.median(s))

def f_mk_p(x):
    """Two-sided Mann-Kendall p-value (normal approximation, no tie correction)."""
    a = _valid(x); n = a.size
    if n < 4: return NAN
    s = sum(np.sign(a[j] - a[i]) for i in range(n) for j in range(i + 1, n))
    var = n * (n - 1) * (2 * n + 5) / 18
    z = 0 if s == 0 else (s - np.sign(s)) / math.sqrt(var)
    return float(math.erfc(abs(z) / math.sqrt(2)))

def f_early(x, k=3):
    a = _arr(x); return f_mean(a[:k]) if a is not None else NAN

def f_late(x, k=3):
    a = _arr(x); return f_mean(a[-k:]) if a is not None else NAN

def f_frac(cond):
    """Fraction of valid years where a boolean series is true."""
    a = _arr(cond)
    if a is None: return NAN
    v = a[~np.isnan(a)]
    return float(v.mean()) if v.size else NAN

def f_count(cond):
    a = _arr(cond)
    if a is None: return NAN
    return float(np.nansum(a))

def f_div(a, b, default=NAN):
    A, B = _arr(a), _arr(b)
    if A is None and B is None:
        if _isnan(a) or _isnan(b) or b == 0: return default
        return a / b
    with np.errstate(divide='ignore', invalid='ignore'):
        r = np.true_divide(A if A is not None else a, B if B is not None else b)
    if isinstance(r, np.ndarray):
        r = np.where(np.isfinite(r), r, default)
    return r

def f_nz(x, default=0.0):
    A = _arr(x)
    if A is not None: return np.where(np.isnan(A), default, A)
    return default if _isnan(x) else x

def f_clip(x, lo=0.0, hi=1.0):
    A = _arr(x)
    if A is not None: return np.clip(A, lo, hi)
    return NAN if _isnan(x) else min(max(x, lo), hi)

def f_ramp(x, lo, hi):
    """Linear membership: 0 at or below lo, 1 at or above hi (reverse if lo > hi)."""
    if _isnan(x): return NAN
    if lo == hi: return 1.0 if x >= hi else 0.0
    return min(max((x - lo) / (hi - lo), 0.0), 1.0)

def f_ifelse(c, a, b):
    if _isnan(c): return NAN
    return a if c else b

def f_isnan(x):
    return _isnan(x)

def f_is_text(x):
    return isinstance(x, str) and x != ''

def f_known(x):
    return not _isnan(x)

def f_cumsum(x):
    a = _arr(x); return np.nancumsum(a) if a is not None else NAN

def f_runs(cond):
    """Longest run of consecutive true years."""
    a = _arr(cond)
    if a is None: return NAN
    best = cur = 0
    for v in a:
        cur = cur + 1 if v == 1 else 0
        best = max(best, cur)
    return float(best)

def f_abs(x):
    A = _arr(x)
    return np.abs(A) if A is not None else (NAN if _isnan(x) else abs(x))

def f_contains(lst, item):
    return item in (lst or [])

def f_doy(dates):
    """Day of year for a list of 'YYYY-M-D' strings."""
    import datetime as dt
    out = []
    for s in dates or []:
        try:
            y, m, d = (int(p) for p in str(s).split('-')[:3])
            out.append(dt.date(y, m, d).timetuple().tm_yday)
        except Exception:
            out.append(NAN)
    return np.array(out, float)


PCT_LEVELS = [5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95]

def f_frac_below(t, values, levels=None):
    """Share of the MWS (0-1) below t, interpolated from its percentile values (p05, p10, p20 ... p90, p95).
    Below p05 counts as 0 and above p95 as 1."""
    lv = levels or PCT_LEVELS
    if _isnan(t) or values is None: return NAN
    pts = [(l / 100, v) for l, v in zip(lv, values) if not _isnan(v)]
    if len(pts) < 3: return NAN
    if t < pts[0][1]: return 0.0
    if t >= pts[-1][1]: return 1.0
    for (q0, v0), (q1, v1) in zip(pts, pts[1:]):
        if v0 <= t < v1:
            return q0 + (q1 - q0) * ((t - v0) / (v1 - v0) if v1 > v0 else 0)
    return NAN

def f_frac_below_nz(t, values, levels=None):
    """Like frac_below, but percentile values of exactly 0 are read as missing data, not as zero.
    The share of the area with zeros (z) is estimated from the percentiles; the result is the share below t
    of the area that has data, (frac_below(t) - z) / (1 - z). Missing if 90% or more of the area is zero."""
    if values is None: return NAN
    z = f_frac_below(1e-6, values, levels)
    if _isnan(z): return NAN
    if z >= 0.9: return NAN
    f = f_frac_below(t, values, levels)
    if _isnan(f): return NAN
    return max(0.0, (f - z) / (1 - z))

def _flat(args):
    out = []
    for a in args:
        if isinstance(a, (list, tuple)): out += list(a)
        else: out.append(a)
    return out

def f_ntrue(*args):
    """Number of arguments that are true (unknown ones are not counted)."""
    return float(sum(1 for a in _flat(args) if not _isnan(a) and bool(a)))

def f_nknown(*args):
    """Number of arguments that are known (not missing)."""
    return float(sum(1 for a in _flat(args) if not _isnan(a)))

def f_avg(*args):
    """Mean of the known arguments (missing ones are skipped)."""
    v = [float(a) for a in _flat(args) if not _isnan(a)]
    return sum(v) / len(v) if v else NAN

def f_nfalls(x):
    """Number of year-on-year falls in a series (consecutive valid years only)."""
    a = _arr(x)
    if a is None: return NAN
    d = a[1:] - a[:-1]
    d = d[~np.isnan(d)]
    return float((d < 0).sum()) if d.size else NAN

def f_nvalid(x):
    """Number of valid (non-missing) values in a series."""
    a = _arr(x)
    if a is None: return NAN
    return float((~np.isnan(a)).sum())

FUNCS = {
    'mean': f_mean, 'median': f_median, 'sum': f_sum, 'min': f_min, 'max': f_max,
    'first': f_first, 'last': f_last, 'range': f_range, 'std': f_std, 'cv': f_cv,
    'slope': f_slope, 'mk_p': f_mk_p, 'early': f_early, 'late': f_late,
    'frac': f_frac, 'count': f_count, 'div': f_div, 'nz': f_nz, 'clip': f_clip,
    'ramp': f_ramp, 'ifelse': f_ifelse, 'isnan': f_isnan, 'known': f_known,
    'cumsum': f_cumsum, 'runs': f_runs, 'abs': f_abs, 'contains': f_contains,
    'doy': f_doy, 'frac_below': f_frac_below, 'frac_below_nz': f_frac_below_nz, 'is_text': f_is_text, 'ntrue': f_ntrue, 'nknown': f_nknown, 'avg': f_avg, 'nfalls': f_nfalls, 'nvalid': f_nvalid, 'len': lambda x: len(x) if x is not None else 0,
}

_BIN = {
    ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: f_div(a, b),
    ast.Pow: lambda a, b: a ** b, ast.Mod: lambda a, b: a % b,
}

def _cmp(op, a, b):
    A, B = _arr(a), _arr(b)
    if A is not None or B is not None:
        x = A if A is not None else a
        y = B if B is not None else b
        with np.errstate(invalid='ignore'):
            r = {ast.Lt: np.less, ast.LtE: np.less_equal, ast.Gt: np.greater,
                 ast.GtE: np.greater_equal, ast.Eq: np.equal, ast.NotEq: np.not_equal}[type(op)](x, y).astype(float)
        nanmask = np.isnan(x) if isinstance(x, np.ndarray) else np.zeros_like(r, bool)
        if isinstance(y, np.ndarray): nanmask = nanmask | np.isnan(y)
        r[nanmask] = NAN
        return r
    if isinstance(op, ast.In): return a in (b or [])
    if isinstance(op, ast.NotIn): return a not in (b or [])
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and (_isnan(a) or _isnan(b)):
        return NAN
    return {ast.Lt: lambda: a < b, ast.LtE: lambda: a <= b, ast.Gt: lambda: a > b,
            ast.GtE: lambda: a >= b, ast.Eq: lambda: a == b, ast.NotEq: lambda: a != b}[type(op)]()

class Namespace(dict):
    """Attribute-access dict used for dataset aliases (lulc.tree_forest_area)."""
    def __getattr__(self, k):
        try: return self[k]
        except KeyError: return NAN

_cache = {}

def compile_expr(src):
    if src not in _cache:
        try:
            _cache[src] = ast.parse(src, mode='eval').body
        except SyntaxError as e:
            raise ExprError(f'syntax error in {src!r}: {e}')
    return _cache[src]

def evaluate(src, env):
    """Evaluate an expression string. `env` maps names to scalars, strings, series or Namespaces.
    Boolean logic is three-valued: NaN (unknown) propagates unless the other operand decides."""
    return _ev(compile_expr(src), env, src)

def _truth(v):
    if _isnan(v): return None
    if isinstance(v, np.ndarray): raise ExprError('series used where a single value is needed; wrap it in mean(), last(), frac() ...')
    return bool(v)

def _ev(n, env, src):
    if isinstance(n, ast.Constant):
        return n.value
    if isinstance(n, ast.Name):
        if n.id in env: return env[n.id]
        if n.id in ('True', 'False', 'None'): return {'True': True, 'False': False, 'None': None}[n.id]
        if n.id == 'nan': return NAN
        raise ExprError(f'unknown name {n.id!r} in {src!r}')
    if isinstance(n, ast.Attribute):
        base = _ev(n.value, env, src)
        if isinstance(base, dict): return base.get(n.attr, NAN)
        raise ExprError(f'attribute access on non-dataset in {src!r}')
    if isinstance(n, ast.List) or isinstance(n, ast.Tuple):
        return [_ev(e, env, src) for e in n.elts]
    if isinstance(n, ast.UnaryOp):
        v = _ev(n.operand, env, src)
        if isinstance(n.op, ast.USub): return -v if not _isnan(v) else NAN
        if isinstance(n.op, ast.UAdd): return v
        if isinstance(n.op, ast.Not):
            A = _arr(v)
            if A is not None: return np.where(np.isnan(A), NAN, 1.0 - (A > 0))
            t = _truth(v); return NAN if t is None else (not t)
    if isinstance(n, ast.BinOp):
        f = _BIN.get(type(n.op))
        if not f: raise ExprError(f'operator not allowed in {src!r}')
        a, b = _ev(n.left, env, src), _ev(n.right, env, src)
        if a is None or b is None: return NAN
        if isinstance(a, list): a = _arr(a)
        if isinstance(b, list): b = _arr(b)
        return f(a, b)
    if isinstance(n, ast.BoolOp):
        vals = [_ev(v, env, src) for v in n.values]
        if any(isinstance(v, np.ndarray) for v in vals):
            arrs = [(_arr(v) if isinstance(v, np.ndarray) else np.full(8, NAN if _isnan(v) else float(bool(v)))) for v in vals]
            out = arrs[0]
            for a in arrs[1:]:
                if isinstance(n.op, ast.And):
                    out = np.where((out == 0) | (a == 0), 0.0, np.where(np.isnan(out) | np.isnan(a), NAN, 1.0))
                else:
                    out = np.where((out == 1) | (a == 1), 1.0, np.where(np.isnan(out) | np.isnan(a), NAN, 0.0))
            return out
        ts = [_truth(v) for v in vals]
        if isinstance(n.op, ast.And):
            if any(t is False for t in ts): return False
            return NAN if any(t is None for t in ts) else True
        if any(t is True for t in ts): return True
        return NAN if any(t is None for t in ts) else False
    if isinstance(n, ast.Compare):
        left = _ev(n.left, env, src); result = True
        for op, c in zip(n.ops, n.comparators):
            right = _ev(c, env, src)
            r = _cmp(op, left, right)
            if isinstance(r, np.ndarray): return r
            if _isnan(r): return NAN
            if not r: return False
            left = right
        return result
    if isinstance(n, ast.IfExp):
        t = _truth(_ev(n.test, env, src))
        if t is None: return NAN
        return _ev(n.body if t else n.orelse, env, src)
    if isinstance(n, ast.Call):
        if not isinstance(n.func, ast.Name) or n.func.id not in FUNCS:
            raise ExprError(f'function not allowed in {src!r}')
        args = [_ev(a, env, src) for a in n.args]
        kw = {k.arg: _ev(k.value, env, src) for k in n.keywords}
        return FUNCS[n.func.id](*args, **kw)
    raise ExprError(f'construct {type(n).__name__} not allowed in {src!r}')

def names_in(src):
    """Bare names referenced by an expression (used to order variable evaluation)."""
    return {x.id for x in ast.walk(compile_expr(src)) if isinstance(x, ast.Name)}
