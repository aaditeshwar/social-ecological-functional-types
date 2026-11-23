"""Decompose each MWS into a mixture of system archetypes (knowledge/archetypes.json).

Helpers are evaluated in order; any helper can be overridden (community answers set helper
values, see knowledge/questions.json), and later helpers are recomputed from the override.
Raw shares are physical fractions of MWS area. If they sum to less than 1 the remainder
(land-cover pixels not classified) is added to the archetype named in 'normalisation.fill';
if they sum to more than 1 all shares are divided by the sum.
"""
import math
from .expr import evaluate, NAN
from .util import knowledge_dir, load_json

def load_archetypes(path=None):
    return load_json(path or knowledge_dir() / 'archetypes.json')

def _num(v):
    return 0.0 if v is None or isinstance(v, str) or (isinstance(v, float) and math.isnan(v)) else max(float(v), 0.0)

def mixture(env, spec, overrides=None, shifts=None):
    env = dict(env)
    overrides = overrides or {}
    helpers = {}
    for h in spec['helpers']:
        if h['id'] in overrides:
            v = overrides[h['id']]
        else:
            try:
                v = evaluate(h['expr'], env)
            except Exception:
                v = NAN
        env[h['id']] = v; helpers[h['id']] = v
    raw = {}
    for a in spec['archetypes']:
        try:
            raw[a['id']] = _num(evaluate(a['share'], env))
        except Exception:
            raw[a['id']] = 0.0
    tot = sum(raw.values())
    norm = spec.get('normalisation', {})
    fill = norm.get('fill', 'other')
    shares = dict(raw)
    if tot < 1 and tot > 0:
        shares[fill] = shares.get(fill, 0.0) + (1 - tot)
    elif tot > 1:
        shares = {k: v / tot for k, v in shares.items()}
    for sh in shifts or []:
        shares = apply_shift(shares, sh)
    return finish(shares, spec, helpers, tot)

def apply_shift(shares, sh):
    """Move `fraction` of each 'from' share to the 'to' archetypes, split in proportion to their
    current shares (or to the first listed when all are zero). The total is unchanged."""
    s = dict(shares)
    moved = sum(s.get(a, 0.0) * sh['fraction'] for a in sh['from'])
    for a in sh['from']:
        s[a] = s.get(a, 0.0) * (1 - sh['fraction'])
    to = sh['to'] if isinstance(sh['to'], list) else [sh['to']]
    base = sum(s.get(a, 0.0) for a in to)
    for a in to:
        s[a] = s.get(a, 0.0) + (moved * s.get(a, 0.0) / base if base > 1e-9 else (moved if a == to[0] else 0.0))
    return s

def finish(shares, spec, helpers=None, raw_total=None):
    present = [a['id'] for a in spec['archetypes'] if shares[a['id']] >= a['present_at']]
    prod = {k: v for k, v in shares.items() if k != spec.get('normalisation', {}).get('fill', 'other')}
    dominant = max(prod, key=prod.get) if any(prod.values()) else None
    return {'shares': {k: round(v, 3) for k, v in shares.items()}, 'present': present, 'dominant': dominant,
            'raw_total': None if raw_total is None else round(raw_total, 3),
            'helpers': {k: (None if v is None or isinstance(v, str) or (isinstance(v, float) and math.isnan(v)) else round(float(v), 4))
                        for k, v in (helpers or {}).items()}}
