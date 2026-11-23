"""Evaluate the signal library (knowledge/signals.json).

Three kinds of signal: 'system' (a yes/no condition on the system mix: where a rule is checked),
'stress' (evidence of a problem) and 'context' (a setting a rule may require, or an amplifier).
A threshold signal compares one indicator with a threshold in its bad direction and has a grade:
0 below the threshold, 0.5 at it, rising linearly to 1 at the severe threshold. It is 'on' at
grade >= 0.5. Expression signals are yes/no and grade 0 or 1. Missing data -> unknown (None).
"""
import math
import numpy as np
from .expr import evaluate, NAN
from .util import knowledge_dir, load_json

def load_signals(path=None):
    return load_json(path or knowledge_dir() / 'signals.json')

def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and not math.isnan(x)

def pooled_percentiles(S, envs):
    """Percentile thresholds for every threshold signal with a percentile_fallback, pooled over all MWS."""
    pools = {}
    for s in S['signals']:
        fb = s.get('percentile_fallback')
        if not fb or 'var' not in s: continue
        vals = np.array([e.get(s['var']) for e in envs if _num(e.get(s['var']))], float)
        if not vals.size: continue
        if np.percentile(vals, fb['pct']) == np.percentile(vals, fb['severe_pct']) == np.percentile(vals, 50):
            continue        # degenerate: the threshold is the typical value (e.g. most values tied at 0), so a
                            # percentile cannot separate MWS; leave the signal unknown rather than on everywhere
        pools[s['id']] = {'value': float(np.percentile(vals, fb['pct'])), 'severe': float(np.percentile(vals, fb['severe_pct'])),
                          'pct': fb['pct'], 'severe_pct': fb['severe_pct'], 'n': int(vals.size)}
    return pools

def grade(v, thr, sev, direction):
    """0 if the threshold is not crossed, else 0.5 + 0.5 * position between threshold and severe (capped at 1)."""
    hi = direction == 'high'
    if (v < thr) if hi else (v > thr): return 0.0
    if sev == thr: return 1.0
    f = (v - thr) / (sev - thr)
    return round(0.5 + 0.5 * max(0.0, min(1.0, f)), 4)

def eval_signal(s, env, pools):
    out = {'kind': s['kind']}
    if 'expr' in s:
        try: v = evaluate(s['expr'], env)
        except Exception: v = NAN
        if isinstance(v, (bool, np.bool_)):
            out.update(on=bool(v), grade=1.0 if v else 0.0)
        elif _num(v):
            out.update(on=bool(v), grade=1.0 if v else 0.0)
        else:
            out.update(on=None, grade=None)
        return out
    v = env.get(s['var'])
    out['value'] = round(float(v), 4) if _num(v) else None
    thr = None
    if s.get('use_absolute', True):
        for i, t in enumerate(s.get('thresholds', [])):
            try:
                if evaluate(t['when'], env) is True:
                    thr = (t['value'], t['severe'], 'absolute', i); break
            except Exception:
                continue
    if thr is None and s['id'] in pools:
        p = pools[s['id']]; thr = (p['value'], p['severe'], f"pooled p{p['pct']}/p{p['severe_pct']}", len(s.get('thresholds', [])))
    out['tix'] = thr[3] if thr else None
    if thr is None or not _num(v):
        out.update(on=None, grade=None, basis=thr[2] if thr else None)
        return out
    g = grade(float(v), thr[0], thr[1], s['direction'])
    out.update(on=g >= 0.5, grade=g, threshold=round(thr[0], 4), severe_threshold=round(thr[1], 4),
               basis=thr[2], direction=s['direction'])
    return out

def evaluate_signals(env, S, pools, kinds=None):
    return {s['id']: eval_signal(s, env, pools) for s in S['signals'] if kinds is None or s['kind'] in kinds}

def threshold_table(S, pools):
    """Per threshold signal, the candidate thresholds [value, severe, basis, when] in the order 'tix' indexes them."""
    out = {}
    for s in S['signals']:
        if 'var' not in s: continue
        c = [[t['value'], t['severe'], 'absolute', t['when']] for t in s.get('thresholds', [])]
        p = pools.get(s['id'])
        c.append([round(p['value'], 4), round(p['severe'], 4), f"pooled p{p['pct']}/p{p['severe_pct']}", None] if p else None)
        out[s['id']] = c
    return out
