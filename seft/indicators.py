"""Compute indicators defined in knowledge/variables.json for every MWS."""
import math
import numpy as np
from .expr import evaluate, names_in, Namespace, NAN, ExprError
from .util import ROOT, load_json

MIN_COVERAGE = 0.2

def load_variables(path=None):
    spec = load_json(path or ROOT / 'knowledge' / 'variables.json')
    return spec['variables']

def _order(vars_):
    ids = {v['id'] for v in vars_}
    done, out, pending = set(), [], list(vars_)
    while pending:
        progressed = False
        for v in list(pending):
            deps = ((names_in(v['expr']) | {v.get('min_coverage')}) & ids) - {v['id']}
            if deps <= done:
                out.append(v); done.add(v['id']); pending.remove(v); progressed = True
        if not progressed:
            raise ExprError('circular variable dependencies: ' + ', '.join(v['id'] for v in pending))
    return out

def _clean(x):
    if isinstance(x, (np.floating, float)):
        return None if math.isnan(x) else round(float(x), 4)
    if isinstance(x, np.ndarray):
        return [None if math.isnan(v) else round(float(v), 4) for v in x]
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    return x

def compute(rec, variables):
    env = {k: v for k, v in rec.items()}
    out = {}
    for v in _order(variables):
        try:
            val = evaluate(v['expr'], env)
        except ExprError:
            raise
        except Exception:
            val = NAN
        cov = v.get('min_coverage')
        if cov and not (isinstance(env.get(cov), float) and env[cov] >= MIN_COVERAGE):
            val = NAN
        env[v['id']] = val
        if not v.get('series'):
            out[v['id']] = _clean(val)
    return out, env
