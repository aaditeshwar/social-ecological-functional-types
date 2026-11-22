"""End-to-end run: load cached data -> indicators -> contexts -> archetype mixtures -> stresses -> schemes."""
import math
from collections import defaultdict
import numpy as np
from .util import ROOT, load_json
from .load import load_district
from .indicators import load_variables, compute
from .context import load_contexts, assign, rain_factors
from .archetypes import load_archetypes, mixture
from .stresses import load_graph, load_taxonomy, evaluate_stresses, hierarchy
from .signals import load_signals, pooled_percentiles, threshold_table
from .schemes import load_schemes, match, eligible
from .assess import load_questions, system_overrides, reassess

def run(locations=None, knowledge_dir=None, log=print, answers=None, pools=None, keep=None):
    """answers: optional {mws_uid: {question_id: option_id}} from community meetings.
    pools: fixed pooled-percentile thresholds (e.g. the atlas's, from web/data/index.json) instead of
    pooling over this run; used to score new locations with the same thresholds as the atlas.
    keep: optional callable(record) -> bool; records it rejects are dropped before scoring."""
    answers = answers or {}
    kd = knowledge_dir or ROOT / 'knowledge'
    cfg = locations or load_json(ROOT / 'config' / 'locations.json')
    V = load_variables(kd / 'variables.json'); C = load_contexts(kd / 'contexts.json')
    A = load_archetypes(kd / 'archetypes.json'); G = load_graph(kd / 'causal_graph.json'); SC = load_schemes(kd / 'schemes.json')
    Q = load_questions(kd / 'questions.json')
    S = load_signals(kd / 'signals.json'); T = load_taxonomy(kd / 'taxonomy.json')
    records, villages, clusters = [], {}, {}
    # pass 1: indicators
    for d in cfg['districts']:
        mws, vill, cl = load_district(d['state'], d['district'], d['tehsils'])
        log(f"{d['district']}: {len(mws)} MWS, {len(vill)} villages")
        for uid, rec in mws.items():
            rec['rain_factor'] = 1.0
            out, env = compute(rec, V)
            records.append({'uid': uid, 'state': d['state'], 'district': d['district'], 'tehsil': rec['tehsil'],
                            'tehsils': rec['tehsils'], 'area': rec['area'], 'ind': out, 'env': env,
                            'canals': rec['canal'].get('projects', []), 'gc': rec['gc'].get('items', [])})
        villages[d['district']] = vill; clusters[d['district']] = cl
    # rainfall rescaling to district normals
    med = defaultdict(list)
    for r in records:
        if r['ind'].get('precip_mean') is not None: med[r['district']].append(r['ind']['precip_mean'])
    factors = rain_factors(C, {k: float(np.median(v)) for k, v in med.items()})
    for r in records:
        f = factors.get(r['district'], 1.0); p = r['ind'].get('precip_mean')
        rn = p * f if p is not None else math.nan
        r['env']['rain_factor'] = f; r['env']['rain_norm'] = rn
        r['ind']['rain_norm'] = None if math.isnan(rn) else round(rn, 1)
    # pass 2: contexts and archetypes
    for r in records:
        env = r['env']; env['state'] = r['state']; env['district'] = r['district']
        r['ctx'] = assign(env, C); env['ctx'] = r['ctx']
        r['mix0'] = mixture(env, A)
        sets, shifts = system_overrides(Q, answers.get(r['uid']))
        r['mix'] = mixture(env, A, sets, shifts) if (sets or shifts) else r['mix0']
        r['answers'] = answers.get(r['uid'], {})
        for k, v in r['mix']['shares'].items(): env['share_' + k] = v
    # pass 3: signals (pooled percentiles over the whole run), rules, pathways, schemes
    if keep: records = [r for r in records if keep(r)]
    if pools is None: pools = pooled_percentiles(S, [r['env'] for r in records])
    for r in records:
        score(r, G, Q, S, T, SC, pools)
    meta = {'rain_factors': factors, 'pools': pools, 'signal_thresholds': threshold_table(S, pools)}
    return records, villages, clusters, meta

def score(r, G, Q, S, T, SC, pools):
    """Signals, rules, community re-assessment, pathways and schemes for one record (env, mix, answers)."""
    res, sig = evaluate_stresses(r['env'], G, pools, S)
    r['signals'] = sig
    r['stress'] = reassess(res, G, Q, r.get('answers'))
    r['pathways'] = hierarchy(r['stress'], sig, G, T)
    r['schemes'] = match(r['env'], r['stress'], r['mix'], SC, r['state'])
    r['eligible'] = eligible(r['env'], SC, r['state'])
    return r
