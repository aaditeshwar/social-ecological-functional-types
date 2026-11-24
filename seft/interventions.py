"""Interventions (knowledge/interventions.json) for a micro-watershed or a waterbody.

Each intervention has a landscape fit test: 'suits' and 'avoid' expressions over the watershed variables, the system
shares (share_<archetype>) and the context classes (terrain, aquifer, rainfall, gw_category, canal, cropping).
  suited      'suits' holds and 'avoid' does not
  not suited  'avoid' holds
  possible    otherwise (including when a value is missing)
The page (web/index.html) evaluates the same expressions in the browser, so that suggestions follow community answers.
"""
import math
from .expr import evaluate
from .util import knowledge_dir, load_json

DIMS = ('rainfall', 'aquifer', 'terrain', 'gw_category', 'canal', 'cropping')
# variables supplied only by community answers (knowledge/interventions.json fit.community_vars); unknown by default
COMMUNITY_VARS = ('wl_post_monsoon',)
FIT_RANK = {'suited': 2, 'possible': 1, 'not suited': 0}

def load_interventions(path=None):
    return load_json(path or knowledge_dir() / 'interventions.json')

def fit_env(env, ctx=None, shares=None):
    """Variables with None turned into NaN (so a missing value makes a comparison unknown, not an error), plus the
    context classes by dimension name and the system shares."""
    e = {k: (math.nan if v is None else v) for k, v in env.items() if not isinstance(v, (dict, list))}
    for d in DIMS: e[d] = (ctx or {}).get(d) or ''
    for k, v in (shares or {}).items(): e['share_' + k] = math.nan if v is None else v
    for k in COMMUNITY_VARS: e.setdefault(k, math.nan)
    return e

def _true(expr, env):
    if not expr: return False
    try: r = evaluate(expr, env)
    except Exception: return False
    try: return r is True or (not isinstance(r, str) and float(r) == 1.0)
    except (TypeError, ValueError): return False

def fit(iv, env):
    if _true(iv.get('avoid'), env): return 'not suited'
    if _true(iv.get('suits'), env): return 'suited'
    return 'possible'

def suggest(env, positive, IV, key='addresses', wb_type=None):
    """Interventions that respond to the positive stresses (watershed) or rules (waterbody, key='addresses_wb'), with
    their fit, ranked: suited first, then by the number of stresses addressed."""
    out = []
    for iv in IV['interventions']:
        if wb_type is not None and iv.get('wb_types') and wb_type not in iv['wb_types']: continue
        hit = [x for x in iv.get(key) or [] if x in positive]
        if not hit: continue
        f = fit(iv, env)
        out.append({'id': iv['id'], 'fit': f, 'because': hit, 'side': iv['side'], 'rank': FIT_RANK[f] * 10 + len(hit)})
    out.sort(key=lambda x: -x['rank'])
    return out

def scheme_names(K_ws_schemes, K_wb_schemes=None):
    """{id: name} over the watershed and waterbody scheme lists, for display of an intervention's schemes."""
    out = {s['id']: s['name'] for s in K_ws_schemes['schemes']}
    for s in (K_wb_schemes or {}).get('schemes', []):
        out.setdefault(s['id'], s['name'])
        if s.get('watershed_id'): out[s['watershed_id']] = out.get(s['watershed_id'], s['name'])
    return out
