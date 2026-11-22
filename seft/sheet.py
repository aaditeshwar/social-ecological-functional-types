"""Evaluate the Signal_Verification sheet's rules (knowledge/sheet_rules.json) for one MWS.

Signals are 1 (true), 0 (false) or unknown (missing data). A trigger is decided only if it comes out the
same for every way of filling in the unknown signals; otherwise it is 'insufficient data'. The intensity
treats unknown signals as 0 and is scaled to 0-100 by the rule's 'out of'. Built by
tools/build_sheet_rules.py; the reading conventions are in that file's docstring.
"""
import itertools, math
from .expr import evaluate, NAN
from .util import ROOT, load_json

def load_sheet_rules(path=None):
    return load_json(path or ROOT / 'knowledge' / 'sheet_rules.json')

def _sig(expr, env):
    try: v = evaluate(expr, env)
    except Exception: return None
    if isinstance(v, float) and math.isnan(v): return None
    if v is None: return None
    try: return 1 if bool(v) else 0
    except Exception: return None

def _num(expr, env):
    try: v = evaluate(expr, env)
    except Exception: return None
    try: v = float(v)
    except Exception: return None
    return None if math.isnan(v) else v

def evaluate_rule(rule, env):
    sig = {k: _sig(s['expr'], env) for k, s in rule['signals'].items()}
    unknown = [k for k, v in sig.items() if v is None]
    outcomes = set()
    for combo in itertools.product((0, 1), repeat=len(unknown)):
        e = {k: (v if v is not None else 0) for k, v in sig.items()}
        e.update(dict(zip(unknown, combo)))
        t = _num(rule['trigger'], e)
        outcomes.add(None if t is None else bool(t))
        if len(outcomes) > 1: break
    trig = outcomes.pop() if len(outcomes) == 1 else None
    known = {k: (v if v is not None else 0) for k, v in sig.items()}
    inten = _num(rule['intensity'], known)
    inten = None if inten is None else round(100 * max(0.0, inten) / rule['out_of'], 1)
    status = 'triggered' if trig is True else ('not triggered' if trig is False else 'insufficient data')
    return {'status': status, 'intensity': inten if trig else (0.0 if trig is False else None),
            'signals': sig, 'unknown': unknown}

def evaluate_sheet(env, rules):
    return {r['id']: evaluate_rule(r, env) for r in rules['rules']}
