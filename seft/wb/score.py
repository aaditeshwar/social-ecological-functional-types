"""Score waterbodies: signals, roles and rules from knowledge/waterbody/{signals,roles,rules}.json.

Rule status for each waterbody: 'not applicable' (type not in applies_to, or gate false), 'triggered',
'not triggered', or 'insufficient data' (not triggered, but a signal in the trigger had no value).
"""
import math, re
from ..util import ROOT, load_json
from ..expr import evaluate
from ..signals import grade

KDIR = ROOT / 'knowledge' / 'waterbody'

def load_knowledge(kdir=None):
    kdir = kdir or KDIR
    K = {n: load_json(kdir / f'{n}.json') for n in ('types', 'signals', 'roles', 'rules')}
    opt = {'schemes': {'schemes': [], 'links': {}}, 'variables': {'variables': [], 'type_fields': []},
           'questions': {'type_questions': [], 'stress_questions': []}, 'sources': {'sources': []}}
    for n, empty in opt.items():
        K[n] = load_json(kdir / f'{n}.json') if (kdir / f'{n}.json').exists() else empty
    # interventions: the catalogue shared with the watershed atlas (knowledge/interventions.json)
    K['interventions'] = load_json(ROOT / 'knowledge' / 'interventions.json')
    # sources: the waterbody bibliography plus the watershed entries it cites (knowledge/sources.json)
    own = {x['id'] for x in K['sources']['sources']}
    cited = set(_cited(K))
    ws = load_json(ROOT / 'knowledge' / 'sources.json')['sources']
    K['sources'] = dict(K['sources'], sources=K['sources']['sources'] + [x for x in ws if x['id'] in cited and x['id'] not in own])
    return K

def _cited(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'sources' and isinstance(v, list) and all(isinstance(x, str) for x in v): yield from v
            else: yield from _cited(v)
    elif isinstance(o, list):
        for x in o: yield from _cited(x)

DIMS = ('rainfall', 'aquifer', 'terrain', 'gw_category', 'canal', 'cropping')

def iv_names(K):
    """Watershed names the intervention fit tests read, as they appear in a waterbody's home-MWS table:
    variable x -> mws_x, a context dimension d -> ctx_d, share_<system> unchanged."""
    import re
    out = set()
    for iv in K['interventions']['interventions']:
        for e in (iv.get('suits'), iv.get('avoid')):
            for m in re.finditer(r"'[^']*'|([A-Za-z_][A-Za-z0-9_]*)", e or ''):
                n = m.group(1)
                if not n or n in ('nz', 'min', 'max', 'and', 'or', 'not', 'in', 'True', 'False'): continue
                out.add('ctx_' + n if n in DIMS else n if n.startswith('share_') else 'mws_' + n)
    return sorted(out)

def iv_env(mws):
    """Fit-test environment for a waterbody from its home-MWS values (inverse of iv_names)."""
    import math
    e = {}
    for k, v in (mws or {}).items():
        if isinstance(v, (dict, list)): continue
        v = math.nan if v is None else v
        if k.startswith('mws_'): e[k[4:]] = v
        elif k.startswith('share_'): e[k] = v
        elif k.startswith('ctx_') and k[4:] in DIMS: e[k[4:]] = v or ''
    for d in DIMS: e.setdefault(d, '')
    return e

def scheme_links(key, b, K):
    """Schemes linked to a rule id (or 'recent_ponds') that apply to this waterbody's state and type."""
    S = {s['id']: s for s in K['schemes']['schemes']}
    out = []
    for l in K['schemes']['links'].get(key, []):
        s = S.get(l['scheme'])
        if not s or (s.get('states') and b.get('state') not in s['states']): continue
        if l.get('types') and b.get('type') not in l['types']: continue
        out.append(l['scheme'])
    return out

def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and not math.isnan(x)

def _ev(expr, env):
    try: return evaluate(expr, env)
    except Exception: return None

def base_env(b, v):
    env = dict(v)
    env.update({k: val for k, val in (b.get('mws') or {}).items()})
    env.update(type=b['type'], wb_type=b.get('wb_type'), true=True, false=False)
    return env

def _pct(xs, p):
    xs = sorted(xs)
    if not xs: return None
    i = (len(xs) - 1) * p / 100; lo = int(i); hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)

def pool_thresholds(envs, K):
    """For signals with a 'pool', thresholds are percentiles of the variable over waterbodies of the same type
    (restricted to those where the 'over' variable is true). Returns {signal_id: {type: (value, severe)}}."""
    out = {}
    for s in K['signals']['signals']:
        P = s.get('pool')
        if not P: continue
        by = {}
        for e in envs:
            if P.get('over') and not e.get(P['over']): continue
            x = e.get(s['var'])
            if _num(x): by.setdefault(e[P['by']], []).append(x)
        lo = s['direction'] == 'low'
        out[s['id']] = {t: (_pct(xs, P['pct'] if lo else 100 - P['pct']), _pct(xs, P['severe_pct'] if lo else 100 - P['severe_pct']))
                        for t, xs in by.items() if len(xs) >= 30}
    return out

def eval_signals(env, K, pools=None):
    out = {}
    for s in K['signals']['signals']:
        if 'expr' in s:
            r = _ev(s['expr'], env)
            out[s['id']] = None if r is None or (isinstance(r, float) and math.isnan(r)) else (1.0 if r else 0.0)
            continue
        if s.get('gate') and not _ev(s['gate'], env):
            out[s['id']] = 0.0; continue
        x = env.get(s['var'])
        if s.get('pool'):
            th = (pools or {}).get(s['id'], {}).get(env.get(s['pool']['by']))
            out[s['id']] = grade(x, th[0], th[1], s['direction']) if (_num(x) and th) else None
        else:
            out[s['id']] = grade(x, s['value'], s['severe'], s['direction']) if _num(x) else None
    return out

def eval_roles(env, K):
    out = {}
    for r in K['roles']['roles']:
        x = _ev(r['expr'], env)
        out[r['id']] = round(float(x), 3) if _num(x) else 0.0
    return out

_ID = re.compile(r'\b(s_[a-z_]+|ctx_[a-z_]+)\b')

def eval_rules(env, sig, K):
    out = {}
    for r in K['rules']['rules']:
        if env['type'] not in r['applies_to'] or (r.get('gate') and not _ev(r['gate'], env)):
            out[r['id']] = {'status': 'not applicable', 'intensity': None}; continue
        used = set(_ID.findall(r['trigger']))
        unknown = [u for u in used if sig.get(u) is None]
        e = dict(env); e.update({k: (val if val is not None else 0.0) for k, val in sig.items()})
        t = _ev(r['trigger'], e)
        if t:
            i = _ev(r['intensity'], e)
            out[r['id']] = {'status': 'triggered', 'intensity': round(max(0.0, min(100.0, float(i))), 1) if _num(i) else None}
        else:
            out[r['id']] = {'status': 'insufficient data' if unknown else 'not triggered', 'intensity': 0.0 if not unknown else None}
    return out

def score(b, v, K, pools=None):
    env = base_env(b, v)
    sig = eval_signals(env, K, pools)
    env.update(sig)
    roles = eval_roles(env, K)
    env.update(roles)
    rules = eval_rules(env, sig, K)
    return sig, roles, rules
