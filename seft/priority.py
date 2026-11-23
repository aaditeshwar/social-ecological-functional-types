"""Must-ask scores (0-100) for community questions: which answers are likely to change what the atlas infers.

The page (web/index.html: Explore, both atlases, and the Commons Connect tab) computes the same scores in the browser,
where they also follow the answers given so far. The rules are in knowledge/commons_connect.json ('priority').

Watershed atlas questions
  stress questions  scored from the rules they inform: can an answer flip the rule across the positive line, how far
                    could it move the probability, how uncertain is it now, how close are the data to the rule's
                    threshold (intensity), and how confident is the rule.
  system questions  scored from the system mix: can an answer take a system across its presence threshold, and how
                    much of the MWS would it move.
Commons Connect questions take the highest of a base score, the scores of the atlas questions they match (weighted by
how closely), and their own conditions (expressions over the watershed variables and the inference).

`python -m seft.cli priority [--district pune]` writes out/priority/<district>.csv: one row per MWS and question, from
the web bundles (data alone, no answers).
"""
import csv, json, math
from pathlib import Path
from .util import ROOT, load_json
from .expr import evaluate
from .archetypes import apply_shift, _num as _share_num

def rnd(x):
    """Round half up, as Math.round in the page (Python's round() rounds half to even)."""
    return int(math.floor(x + 0.5))

def band(score, P):
    if score is None: return None
    for b in P['bands']:
        if score >= b['min']: return b['id']
    return P['bands'][-1]['id']

def _post(p, lr):
    o = p / (1 - p) * lr
    return o / (1 + o)

def rule_score(x, conf, lrs, A, W):
    """x: {'code', 'inten', 'post'}; lrs: the likelihood ratio each option gives this rule (1 when none).
    flip: the chance that the answer moves the rule across the positive line, taken as p when an answer supporting the
    rule would flip it (the rule is below the line) and 1 - p when a refuting answer would (above the line), scaled so
    that 0.5 counts fully."""
    p = x['post']
    if p is None: return None
    pa = A['positive_at']
    outs = [_post(p, lr) for lr in lrs]
    flips = [q for q in outs if (q >= pa) != (p >= pa)]
    flip = min(1.0, (p if p < pa else 1 - p) / 0.5) if flips else 0.0
    move = max([abs(q - p) for q in outs] + [0.0])
    unc = 1 - abs(2 * p - 1)
    I = (x.get('inten') or 0) / 100
    border = (1 - I) if x['code'] == 2 else (I if x['code'] == 1 else 1.0)
    lowc = {'low': 1.0, 'medium': 0.5}.get(conf, 0.0)
    u = W['flip'] * flip + W['move'] * min(1.0, move / W['move_full']) + W['uncertainty'] * unc + \
        W['borderline'] * border + W['low_confidence'] * lowc
    return 100 * u

def stress_q_score(q, st, conf, A, P):
    """Score and the rule behind it, for a question whose options carry 'stress' [{id, lr}]."""
    W = P['stress_weights']
    rs = []
    for rid in dict.fromkeys(e['id'] for o in q['options'] for e in o.get('stress') or []):
        x = st.get(rid)
        if not x or x.get('post') is None: continue
        lrs = []
        for o in q['options']:
            lr = 1.0
            for e in o.get('stress') or []:
                if e['id'] == rid: lr *= e['lr']
            lrs.append(lr)
        s = rule_score(x, conf.get(rid), lrs, A, W)
        if s is not None: rs.append((s, rid))
    if not rs: return 0.0, None
    rs.sort(reverse=True)
    bonus = W['breadth_bonus'] * sum(1 for s, _ in rs[1:] if s >= W['breadth_at'])
    return min(100.0, rs[0][0] + bonus), rs[0][1]

def _present(shares, spec):
    fill = spec.get('normalisation', {}).get('fill', 'other')
    return {a['id'] for a in spec['archetypes'] if a['id'] != fill and shares.get(a['id'], 0) >= a['present_at']}

def _shares(env, spec, sets=None, shifts=None):
    """System shares as seft.archetypes.mixture computes them, before rounding (the page uses the same unrounded
    shares, so presence at a threshold is decided the same way)."""
    env = dict(env); sets = sets or {}
    for h in spec['helpers']:
        if h['id'] in sets: v = sets[h['id']]
        else:
            try: v = evaluate(h['expr'], env)
            except Exception: v = math.nan
        env[h['id']] = v
    raw = {}
    for a in spec['archetypes']:
        try: raw[a["id"]] = _share_num(evaluate(a["share"], env))
        except Exception: raw[a['id']] = 0.0
    tot = sum(raw.values()); fill = spec.get('normalisation', {}).get('fill', 'other'); sh = dict(raw)
    if 0 < tot < 1: sh[fill] = sh.get(fill, 0.0) + (1 - tot)
    elif tot > 1: sh = {k: v / tot for k, v in sh.items()}
    for x in shifts or []: sh = apply_shift(sh, x)
    return sh

def system_q_score(q, env, spec, P, base_sets=None, base_shifts=None):
    """cross: for each system an answer would take across its presence threshold, how close its share is now to that
    threshold (1 at the threshold, 0 at none or twice the threshold); the largest. shift: the mean share of the MWS the
    answers would move (total variation), scaled so that shift_full counts fully."""
    W = P['system_weights']
    base = _shares(env, spec, base_sets, base_shifts)
    pres = _present(base, spec)
    at = {a['id']: a['present_at'] for a in spec['archetypes']}
    cross, tvs = 0.0, []
    for o in q['options']:
        sets = dict(base_sets or {}); sets.update(o.get('set') or {})
        shifts = list(base_shifts or []) + list(o.get('shift') or [])
        sh = _shares(env, spec, sets, shifts)
        tvs.append(0.5 * sum(abs(sh.get(k, 0) - base.get(k, 0)) for k in set(sh) | set(base)))
        for a in _present(sh, spec) ^ pres:
            cross = max(cross, 1 - min(1.0, abs(base.get(a, 0) - at[a]) / at[a]))
    tv = sum(tvs) / len(tvs) if tvs else 0.0
    return 100 * (W['cross'] * cross + W['shift'] * min(1.0, tv / W['shift_full']))

def _true(expr, env):
    try: r = evaluate(expr, env)
    except Exception: return None
    if r is None or (isinstance(r, float) and math.isnan(r)): return None
    return bool(r)

def _num(expr, env):
    if isinstance(expr, (int, float)): return float(expr)
    try: r = evaluate(expr, env)
    except Exception: return None
    try: r = float(r)
    except (TypeError, ValueError): return None
    return None if math.isnan(r) else r

def key(rid): return rid.replace('.', '__')

def cc_score(q, env, ask, P):
    """Score of a Commons Connect question. ask: {('ws'|'wb', atlas question id): score}. Routing questions are scored
    afterwards (cc_form_scores)."""
    if q.get('role') != 'inform': return None, 'record'
    M = q.get('must_ask') or {}
    s = M.get('base')
    if s is None and not q.get('atlas_match') and not M.get('rules'): s = P['default_base']
    why = M.get('why') or ('base score' if s is not None else '')
    s = s or 0
    for m in q.get('atlas_match') or []:
        v = ask.get((m['atlas'], m['id']))
        if v is None: continue
        v *= P['match_weight'][m['how']]
        if v > s: s, why = v, f"{m['how']} as atlas question {m['id']}"
    for r in M.get('rules') or []:
        if _true(r['if'], env):
            v = _num(r['score'], env)
            if v is None: continue
            if r.get('mode') == 'set': return rnd(v), r['why']
            if v > s: s, why = v, r['why']
    return rnd(min(100.0, s)), why

def cc_form_scores(form, env, ask, P):
    out = {q['name']: cc_score(q, env, ask, P) for q in form['questions']}
    for q in form['questions']:                                    # routing questions: the best of what they lead to
        if q.get('routes'):
            kids = [out[c][0] for c in q['routes'] if c in out and out[c][0] is not None]
            if kids and max(kids) > (out[q['name']][0] or 0): out[q['name']] = (max(kids), 'leads to ' + ', '.join(q['routes']))
    return out

# ---------------------------------------------------------------- from the web bundles
def _ws_state(m, b, K, A):
    """Data-only assessment of one MWS from the bundle, as the page computes it before any answers."""
    from .assess import prior
    conf = {s['id']: s['confidence'] for s in K['causal_graph']['stresses']}
    st = {}
    for sid, x in m['s'].items():
        code, inten = x[0], x[2]
        status = {2: 'triggered', 1: 'not triggered', 0: 'not applicable'}.get(code, 'insufficient data')
        p = prior({'status': status, 'intensity': inten}, conf[sid], A)
        st[sid] = {'code': code, 'inten': inten, 'post': p}
    return st, conf

def ws_env(m, b, K):
    e = {v: (math.nan if x is None else x) for v, x in zip(b['var_ids'], m['i'])}
    dims = [d['id'] for d in K['contexts']['dimensions']]
    e['ctx'] = dict(zip(dims, m['c']))
    for d, c in zip(dims, m['c']): e[d] = c or ''
    for a, s in zip([a['id'] for a in K['archetypes']['archetypes']], m['m']): e['share_' + a] = s
    e['district'] = b['district']; e['state'] = b['state']
    sg = dict(zip(b['signal_ids'], m.get('sg') or []))
    for ps in K['taxonomy']['production_systems']:            # ps_<production system>: 1 present, 0 absent
        g = sg.get(ps['signal'])
        e['ps_' + ps['id']] = math.nan if g is None else (1 if g >= 0.5 else 0)
    return e

def ws_scores(m, b, K, CC):
    """{question id: (score, why)} for the watershed atlas questions, plus the Commons Connect env."""
    A = K['questions']['assessment']; P = CC['priority']
    st, conf = _ws_state(m, b, K, A)
    env = ws_env(m, b, K)
    out = {}
    for q in K['questions']['system_questions']:
        if q.get('show_if') and _true(q['show_if'], env) is not True: out[q['id']] = (0, 'not asked here (show_if)'); continue
        s1 = system_q_score(q, env, K['archetypes'], P)
        s2, rid = stress_q_score(q, st, conf, A, P)
        out[q['id']] = (rnd(max(s1, s2)), 'changes the system mix' if s1 >= s2 else f'informs {rid}')
    for q in K['questions']['stress_questions']:
        s, rid = stress_q_score(q, st, conf, A, P)
        out[q['id']] = (rnd(s), f'informs {rid}' if rid else 'its stresses do not apply here')
    for sid, x in st.items():
        k = key(sid)
        env['p_' + k] = math.nan if x['post'] is None else x['post']
        env['pos_' + k] = math.nan if x['post'] is None else (1 if x['post'] >= A['positive_at'] else 0)
        env['urg_' + k] = math.nan if x['post'] is None else rule_score(x, conf[sid], P['urgency_lrs'], A, P['stress_weights'])
    for qid, (s, _) in out.items(): env['ask_' + qid] = s
    return out, env

# ---------------------------------------------------------------- from a live pipeline / waterbody record (core_seft.analyse)
STATUS_CODE = {
    'triggered': 2, 'not triggered': 1, 'not applicable': 0,
    'unknown': -1, 'insufficient data': -1,
}


def _scalar_env(env):
    """Copy scalars (and context classes) off a pipeline env, dropping Namespace / nested values."""
    out = {}
    for k, v in dict(env or {}).items():
        if k == 'ctx' or isinstance(v, (dict, list)):
            continue
        out[k] = v
    ctx = (env or {}).get('ctx')
    if ctx is not None and hasattr(ctx, 'items'):
        for d, c in dict(ctx).items():
            out[d] = c or ''
    return out


def st_from_stress(stress, G, A):
    """{rule id: {code, inten, post}} from pipeline.score / reassess."""
    from .assess import prior as mws_prior
    conf = {s['id']: s.get('confidence', 'medium') for s in G['stresses']}
    st = {}
    for sid, res in (stress or {}).items():
        post = res.get('posterior')
        if post is None and res.get('status') != 'not applicable':
            post = mws_prior(res, conf.get(sid), A)
        st[sid] = {
            'code': STATUS_CODE.get(res.get('status'), -1),
            'inten': res.get('intensity'),
            'post': post,
        }
    return st, conf


def st_from_wb_rules(rules, K, A):
    """Same shape as st_from_stress, from seft.wb.score / assess."""
    from .wb.assess import prior as wb_prior
    conf = {r['id']: r.get('confidence', 'medium') for r in K['rules']['rules']}
    st = {}
    for rid, res in (rules or {}).items():
        post = res.get('post') if res.get('post') is not None else res.get('posterior')
        if post is None and res.get('status') != 'not applicable':
            post = wb_prior(res.get('status'), res.get('intensity'), conf.get(rid), A)
        st[rid] = {
            'code': STATUS_CODE.get(res.get('status'), -1),
            'inten': res.get('intensity'),
            'post': post,
        }
    return st, conf


def _fill_inference_env(env, st, conf, A, P, scores):
    for sid, x in st.items():
        k = key(sid)
        env['p_' + k] = math.nan if x['post'] is None else x['post']
        env['pos_' + k] = math.nan if x['post'] is None else (1 if x['post'] >= A['positive_at'] else 0)
        env['urg_' + k] = math.nan if x['post'] is None else rule_score(
            x, conf.get(sid), P['urgency_lrs'], A, P['stress_weights'])
    for qid, (s, _) in scores.items():
        env['ask_' + qid] = s
    return env


def cc_env_from_mws(r, T, st, conf, A, P, scores):
    """Commons Connect landscape / planning environment for one scored MWS."""
    env = _scalar_env(r.get('env'))
    for k, v in (r.get('ind') or {}).items():
        if k not in env and not isinstance(v, (dict, list)):
            env[k] = v
    env['district'] = r.get('district'); env['state'] = r.get('state')
    ctx = r.get('ctx') or {}
    if hasattr(ctx, 'items'):
        for d, c in dict(ctx).items():
            env[d] = c or ''
    for k, v in ((r.get('mix') or {}).get('shares') or {}).items():
        env['share_' + k] = v
    sig = r.get('signals') or {}
    for ps in (T or {}).get('production_systems') or []:
        g = sig.get(ps['signal'])
        on = None if not g else g.get('on')
        env['ps_' + ps['id']] = math.nan if on is None else (1 if on else 0)
    return _fill_inference_env(env, st, conf, A, P, scores)


def atlas_scores_from_mws(r, Q, spec, G, P, answers=None):
    """{question id: (score, why)} for watershed atlas questions, from a live record (not a web bundle)."""
    from .assess import system_overrides
    A = Q['assessment']
    st, conf = st_from_stress(r.get('stress'), G, A)
    env = _scalar_env(r.get('env'))
    env['district'] = r.get('district'); env['state'] = r.get('state')
    ctx = r.get('ctx') or {}
    if hasattr(ctx, 'items'):
        for d, c in dict(ctx).items():
            env[d] = c or ''
    for k, v in ((r.get('mix') or {}).get('shares') or {}).items():
        env['share_' + k] = v
    sets, shifts = system_overrides(Q, answers if answers is not None else r.get('answers'))
    out = {}
    for q in Q.get('system_questions', []):
        if q.get('show_if') and _true(q['show_if'], env) is not True:
            out[q['id']] = (0, 'not asked here (show_if)'); continue
        s1 = system_q_score(q, env, spec, P, sets, shifts)
        s2, rid = stress_q_score(q, st, conf, A, P)
        out[q['id']] = (rnd(max(s1, s2)), 'changes the system mix' if s1 >= s2 else f'informs {rid}')
    for q in Q.get('stress_questions', []):
        s, rid = stress_q_score(q, st, conf, A, P)
        out[q['id']] = (rnd(s), f'informs {rid}' if rid else 'its stresses do not apply here')
    return out, st, conf


def type_q_score(q, b, types, P, current, type_data, extra_sets=None):
    """Must-ask score of a waterbody type question (same formula as the page's wAskWb)."""
    applies = q.get('applies_to')
    if applies and current not in applies and type_data not in applies:
        return 0, 'does not apply to this type'
    from .wb.build import assign_type
    ts = []
    for o in q.get('options') or []:
        sset = dict(extra_sets or {})
        sset.update(o.get('set') or {})
        ts.append(assign_type(b, types, sset or None))
    n = sum(1 for t in ts if t != current)
    Wt = P['type_weights']
    s = rnd(100 * ((Wt['any'] if n else 0) + Wt['share'] * (n / len(ts) if ts else 0)))
    why = f'{n} of {len(ts)} answers would change the type' if n else 'no answer changes the type'
    return s, why


def atlas_scores_from_wb(b, K, P, answers=None):
    """{question id: (score, why)} for waterbody type and stress questions."""
    from .wb.assess import collect
    A = K['questions']['assessment']
    st, conf = st_from_wb_rules(b.get('rules'), K, A)
    sets, _, _, _ = collect(answers or {}, K)
    current = b.get('type'); type_data = b.get('type_data') or current
    out = {}
    for q in K['questions'].get('type_questions', []):
        out[q['id']] = type_q_score(q, b, K['types'], P, current, type_data, sets)
    for q in K['questions'].get('stress_questions', []):
        s, rid = stress_q_score(q, st, conf, A, P)
        out[q['id']] = (rnd(s), f'informs {rid}' if rid else 'its rules do not apply here')
    return out, st, conf


def cc_env_from_wb(b, K, st, conf, A, P, scores, mws_env=None):
    env = dict(mws_env or {})
    for k, v in (b.get('vars') or {}).items():
        if not isinstance(v, (dict, list)):
            env[k] = v
    env['wtype'] = b.get('type')
    env['area_ha'] = b.get('area_ha')
    for rid, x in st.items():
        k = key(rid)
        env['wp_' + k] = math.nan if x['post'] is None else x['post']
        env['wpos_' + k] = math.nan if x['post'] is None else (1 if x['post'] >= A['positive_at'] else 0)
    for qid, (s, _) in scores.items():
        env['wask_' + qid] = s
    return env


def plan_iv_score(iv, env, pos, pos_wb, P):
    """Commons Connect planning score for one intervention (page ccPlanHtml)."""
    from .interventions import fit
    f = fit(iv, env)
    hit = [s for s in (iv.get('addresses') or []) if s in pos]
    hit += [s for s in (iv.get('addresses_wb') or []) if s in (pos_wb or ())]
    PS = P['planning_scores']
    if f == 'suited':
        return PS['suited_stress'] if hit else PS['suited']
    if f == 'possible':
        return PS['possible_stress'] if hit else PS['possible']
    return PS['not_suited']


def plan_question(q, IV, env, pos, pos_wb, P):
    """Copy a Commons Connect question with must_ask.base from work_map / demand_iv when present."""
    q = dict(q)
    M = dict(q.get('must_ask') or {})
    spec = {x['id']: x for x in (IV or {}).get('interventions') or []}
    if q.get('work_map'):
        best = 0
        for o in q.get('options') or []:
            for iid in (q['work_map'] or {}).get(o['id']) or []:
                iv = spec.get(iid)
                if iv:
                    best = max(best, plan_iv_score(iv, env, pos, pos_wb, P))
        M['base'] = best
        M.setdefault('why', 'the best-suited work type here')
        q['must_ask'] = M
    elif q.get('demand_iv'):
        best = 0
        for iid in q['demand_iv']:
            iv = spec.get(iid)
            if iv:
                best = max(best, plan_iv_score(iv, env, pos, pos_wb, P))
        M['base'] = best
        M.setdefault('why', 'how well the mapped interventions suit this landscape')
        q['must_ask'] = M
    return q


def load_k():
    kd = ROOT / 'knowledge'
    return {k: load_json(kd / f'{k}.json') for k in ('questions', 'causal_graph', 'archetypes', 'contexts', 'taxonomy')}

def main(districts=None, log=print):
    K = load_k(); CC = load_json(ROOT / 'knowledge' / 'commons_connect.json'); P = CC['priority']
    idx = load_json(ROOT / 'web' / 'data' / 'index.json')
    slugs = districts or [d['slug'] for d in idx['districts']]
    land = next(f for f in CC['forms'] if f['id'] == 'landscape')
    out = Path(ROOT / 'out' / 'priority'); out.mkdir(parents=True, exist_ok=True)
    for slug in slugs:
        b = load_json(ROOT / 'web' / 'data' / f'd_{slug}.json')
        rows = []
        for m in b['mws']:
            ws, env = ws_scores(m, b, K, CC)
            for qid, (s, why) in ws.items():
                rows.append({'mws': m['u'], 'atlas': 'watershed', 'question': qid, 'score': s, 'band': band(s, P), 'why': why})
            ask = {('ws', k): v[0] for k, v in ws.items()}
            for name, (s, why) in cc_form_scores(land, env, ask, P).items():
                rows.append({'mws': m['u'], 'atlas': 'commons_connect:landscape', 'question': name, 'score': s, 'band': band(s, P), 'why': why})
        with open(out / f'{slug}.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        mu = [r for r in rows if r['atlas'] == 'watershed']
        log(f"  {slug}: {len(b['mws'])} MWS; watershed questions must/useful/skip = "
            f"{sum(r['band'] == 'must' for r in mu)}/{sum(r['band'] == 'useful' for r in mu)}/{sum(r['band'] == 'skip' for r in mu)} -> {out / (slug + '.csv')}")
