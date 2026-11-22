"""Assign each MWS to one class per context dimension (knowledge/contexts.json)."""
from .expr import evaluate, Namespace
from .util import ROOT, load_json

def load_contexts(path=None):
    return load_json(path or ROOT / 'knowledge' / 'contexts.json')

def assign(env, spec):
    ctx = Namespace()
    for dim in spec['dimensions']:
        ctx[dim['id']] = None
        for c in dim['classes']:
            try:
                if evaluate(c['expr'], env) is True:
                    ctx[dim['id']] = c['id']; break
            except Exception:
                pass
    return ctx

def rain_factors(spec, district_precip_medians):
    """district -> factor so that rain_norm = precip_mean * factor matches the district normal."""
    out = {}
    normals = spec.get('rainfall_normals', {})
    for d, med in district_precip_medians.items():
        n = (normals.get(d) or {}).get('mm')
        out[d] = (n / med) if (n and med) else 1.0
    return out
