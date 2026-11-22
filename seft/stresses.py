"""Evaluate stress and opportunity rules (knowledge/causal_graph.json) over signals, and roll them up
into observed stresses within production systems (knowledge/taxonomy.json).

A rule has a 'systems' expression over system signals (where it is checked), a 'trigger' over signal
booleans ('<id>_g' gives a grade) and an 'intensity' expression over grades, scaled 0-100. In the
intensity, an unknown stress signal is skipped by max/min/avg; an unknown context or system signal
counts as 0 (no amplification). A triggered rule is severe at intensity >= severe_at.
"""
import math
from .expr import evaluate, NAN
from .util import ROOT, load_json
from .signals import pooled_percentiles, evaluate_signals   # noqa: F401  (re-exported)

def load_graph(path=None):
    return load_json(path or ROOT / 'knowledge' / 'causal_graph.json')

def load_taxonomy(path=None):
    return load_json(path or ROOT / 'knowledge' / 'taxonomy.json')

def _ok(x):
    return x is not None and not (isinstance(x, float) and math.isnan(x))

def _bool_env(sig):
    e = {}
    for k, r in sig.items():
        e[k] = NAN if r['on'] is None else r['on']
        e[k + '_g'] = NAN if r['grade'] is None else r['grade']
    return e

def _grade_env(sig, rule):
    soft = set(rule['signals'].get('context', [])) | set(rule['signals'].get('system', []))
    e = {}
    for k, r in sig.items():
        g = r['grade']
        e[k] = (0.0 if k in soft else NAN) if g is None else g
        e[k + '_g'] = e[k]
    return e

def _applies(rule, sig):
    try: a = evaluate(rule['systems'], _bool_env(sig))
    except Exception: a = NAN
    return a if isinstance(a, bool) else None

def evaluate_rule(rule, sig):
    be = _bool_env(sig)
    try: trig = evaluate(rule['trigger'], be)
    except Exception: trig = NAN
    try: inten = evaluate(rule['intensity'], _grade_env(sig, rule))
    except Exception: inten = NAN
    inten = None if not _ok(inten) or isinstance(inten, bool) else round(max(0.0, min(100.0, float(inten))), 1)
    would = 'triggered' if trig is True else ('not triggered' if trig is False else 'insufficient data')
    if would == 'triggered' and inten is None: inten = 50.0
    sev = (('severe' if inten >= rule.get('severe_at', 70) else 'moderate') if would == 'triggered' else None)
    used = [x for role in ('stress', 'context') for x in rule['signals'].get(role, [])]
    return {'would': would, 'would_severity': sev, 'intensity': inten,
            'signals_on': [x for x in used if sig.get(x, {}).get('on') is True],
            'signals_unknown': [x for x in used if sig.get(x, {}).get('on') is None]}

def _set_status(r, applies):
    if applies is True:
        r['status'], r['severity'] = r['would'], r['would_severity']
    else:
        r['status'], r['severity'] = ('not applicable' if applies is False else 'unknown'), None
    r['applies'] = applies

def evaluate_stresses(env, graph, pools, S):
    """Signals and rules for one MWS. Rules are evaluated whether or not they apply, so that a
    change in the system mix (community answers) can switch applicability without recomputing."""
    sig = evaluate_signals(env, S, pools)
    res = {}
    for rule in graph['stresses']:
        r = evaluate_rule(rule, sig)
        _set_status(r, _applies(rule, sig))
        res[rule['id']] = r
    return res, sig

def reapply(res, sig, graph, env, S):
    """Re-evaluate system signals after the system mix changed, then applicability."""
    sys_ = evaluate_signals(env, S, {}, kinds={'system'})
    sig = {**sig, **sys_}
    for rule in graph['stresses']:
        _set_status(res[rule['id']], _applies(rule, sig))
    return res, sig

ORDER = ['triggered', 'not triggered', 'insufficient data', 'unknown', 'not applicable']

def os_rules(T):
    """{(production system, observed stress): [rule ids]} with groups expanded."""
    groups = {g['id']: g['children'] for g in T['groups']}
    return {(p['id'], o['id']): [c for x in o['pathways'] for c in groups.get(x, [x])]
            for p in T['production_systems'] for o in p['observed_stresses']}

def os_keys(T, graph):
    """Column keys: '<system>.<observed stress>' for rules of its own type, plus
    '<system>.<observed stress>:<other type>' when it also holds rules of another type."""
    types = {r['id']: r['type'] for r in graph['stresses']}
    out = []
    for p in T['production_systems']:
        for o in p['observed_stresses']:
            ts = {types[c] for c in os_rules(T)[(p['id'], o['id'])]}
            out.append((f"{p['id']}.{o['id']}", p['id'], o['id'], o['type']))
            for t in sorted(ts - {o['type']}):
                out.append((f"{p['id']}.{o['id']}:{t}", p['id'], o['id'], t))
    return out

def hierarchy(res, sig, graph, T):
    """Roll rules up to observed stresses within production systems. An observed stress is 'not
    applicable' where its production system is absent; otherwise triggered if any of its rules of the
    key's type is; intensity = max over applicable rules; severe if any triggered rule is severe.
    'positive' and 'posterior' use the community-assessed result."""
    types = {r['id']: r['type'] for r in graph['stresses']}
    rules = os_rules(T)
    ps_sig = {p['id']: p['signal'] for p in T['production_systems']}
    out = {}
    for key, ps, os_, t in os_keys(T, graph):
        present = sig.get(ps_sig[ps], {}).get('on')
        ch = [c for c in rules[(ps, os_)] if types[c] == t]
        if present is not True:
            out[key] = {'status': 'not applicable' if present is False else 'unknown', 'intensity': None, 'severity': None,
                        'triggered': [], 'positive': [], 'posterior': None, 'rules': ch}
            continue
        rs = [res[c] for c in ch]
        st = min((r['status'] for r in rs), key=ORDER.index)
        its = [r['intensity'] for r in rs if r['status'] != 'not applicable' and r['intensity'] is not None]
        trig = [c for c in ch if res[c]['status'] == 'triggered']
        out[key] = {'status': st, 'intensity': max(its) if its else None,
                    'severity': ('severe' if any(res[c]['severity'] == 'severe' for c in trig) else 'moderate') if trig else None,
                    'triggered': trig, 'positive': [c for c in ch if res[c].get('positive')],
                    'posterior': max([res[c]['posterior'] for c in ch if res[c].get('posterior') is not None], default=None),
                    'rules': ch}
    return out
