"""Static checks on the knowledge JSONs: every expression parses, every id reference resolves."""
from .util import ROOT, load_json
from .expr import compile_expr, names_in, FUNCS

def validate(kd=None):
    kd = kd or ROOT / 'knowledge'
    K = {k: load_json(kd / f'{k}.json') for k in ('variables', 'contexts', 'archetypes', 'signals', 'taxonomy', 'causal_graph', 'schemes', 'questions', 'sources')}
    errs = []
    src = {s['id'] for s in K['sources']['sources']}
    var = {v['id'] for v in K['variables']['variables']} | {'rain_factor', 'rain_norm', 'area'}
    helpers = {h['id'] for h in K['archetypes']['helpers']}
    arch = {a['id'] for a in K['archetypes']['archetypes']}
    stresses = {s['id'] for s in K['causal_graph']['stresses']}
    nodes = {n['id'] for n in K['causal_graph']['nodes']} | stresses
    aliases = {'lulc', 'ci', 'drought', 'hydro', 'swb', 'aquifer', 'terrain', 'soge', 'rest', 'degr', 'tcd', 'tci', 'urb', 'canal', 'gc', 'mine', 'vill', 'vtop', 'vmax', 'hseas',
               'soil', 'nrega', 'anty', 'fac', 'river', 'conn', 'fringe', 'fire', 'tig', 'ndvi'}
    known = var | helpers | aliases | {'share_' + a for a in arch} | {'ctx', 'state', 'district', 'True', 'False', 'None', 'nan'} | set(FUNCS)
    def chk(e, where, extra=set()):
        try:
            bad = names_in(e) - known - extra
            if bad: errs.append(f'{where}: unknown names {sorted(bad)} in {e!r}')
        except Exception as x:
            errs.append(f'{where}: {x}')
    for v in K['variables']['variables']: chk(v['expr'], f"variable {v['id']}")
    for d in K['contexts']['dimensions']:
        for c in d['classes']: chk(c['expr'], f"context {d['id']}.{c['id']}")
    for h in K['archetypes']['helpers']: chk(h['expr'], f"helper {h['id']}")
    for a in K['archetypes']['archetypes']:
        chk(a['share'], f"archetype {a['id']}")
        for s in a.get('sources', []):
            if s not in src: errs.append(f"archetype {a['id']}: unknown source {s}")
    for e in K['causal_graph']['edges']:
        if e['from'] not in nodes or e['to'] not in nodes: errs.append(f"edge {e['from']}->{e['to']}: unknown node")
        for s in e['sources']:
            if s not in src: errs.append(f"edge {e['from']}->{e['to']}: unknown source {s}")
    sig = {x['id']: x for x in K['signals']['signals']}
    for x in K['signals']['signals']:
        if x['kind'] not in ('system', 'stress', 'context'): errs.append(f"signal {x['id']}: unknown kind {x['kind']}")
        if 'expr' in x: chk(x['expr'], f"signal {x['id']}")
        else:
            if x['var'] not in var: errs.append(f"signal {x['id']}: unknown variable {x['var']}")
            if x['direction'] not in ('high', 'low'): errs.append(f"signal {x['id']}: direction must be high or low")
            for t in x.get('thresholds', []):
                chk(t['when'], f"signal {x['id']} when")
                bad = (t['severe'] < t['value']) if x['direction'] == 'high' else (t['severe'] > t['value'])
                if bad: errs.append(f"signal {x['id']}: severe threshold on the wrong side")
                for y in t.get('sources', []):
                    if y not in src: errs.append(f"signal {x['id']}: unknown source {y}")
            if not x.get('thresholds') and not x.get('percentile_fallback'):
                errs.append(f"signal {x['id']}: no threshold")
        for y in x.get('sources', []):
            if y not in src: errs.append(f"signal {x['id']}: unknown source {y}")
    sn = set(sig) | {k + '_g' for k in sig}
    for s in K['causal_graph']['stresses']:
        roles = s['signals']
        for role, ids in roles.items():
            for i in ids:
                if i not in sig: errs.append(f"rule {s['id']}: unknown signal {i}")
                elif role == 'system' and sig[i]['kind'] != 'system': errs.append(f"rule {s['id']}: {i} is not a system signal")
        for key in ('systems', 'trigger', 'intensity'):
            used = names_in(s[key]) - set(FUNCS) - {'True', 'False', 'None', 'nan'}
            bad = used - sn
            if bad: errs.append(f"rule {s['id']} {key}: unknown names {sorted(bad)}")
            listed = {i for ids in roles.values() for i in ids}
            extra = {u[:-2] if u.endswith('_g') else u for u in used} - listed
            if extra: errs.append(f"rule {s['id']} {key}: signals not listed in its roles {sorted(extra)}")
        if s.get('group') != (s['id'].split('.')[0] if '.' in s['id'] else None): errs.append(f"rule {s['id']}: group does not match id")
        if s['type'] not in ('stress', 'opportunity'): errs.append(f"rule {s['id']}: unknown type")
        for x in s['sources']:
            if x not in src: errs.append(f"rule {s['id']}: unknown source {x}")
        if not s.get('public_note'): errs.append(f"rule {s['id']}: no public note")
    T = K['taxonomy']; seen = []
    groups = {g['id']: g for g in T['groups']}
    for g in T['groups']:
        for c in g['children']:
            if c not in stresses: errs.append(f"group {g['id']}: unknown rule {c}")
            elif not c.startswith(g['id'] + '.'): errs.append(f"group {g['id']}: rule {c} is not named '{g['id']}.<rule>'")
    for s_ in stresses:
        if '.' in s_ and s_.split('.')[0] not in groups: errs.append(f"rule {s_}: group {s_.split('.')[0]} not in taxonomy groups")
    covered = set()
    for p in T['production_systems']:
        if p['signal'] not in sig or sig[p['signal']]['kind'] != 'system': errs.append(f"production system {p['id']}: unknown system signal {p['signal']}")
        for a in p['archetypes']:
            if a not in arch: errs.append(f"production system {p['id']}: unknown archetype {a}")
        covered |= set(p['archetypes'])
        for o in p['observed_stresses']:
            if o['type'] not in ('stress', 'opportunity'): errs.append(f"observed stress {p['id']}.{o['id']}: unknown type")
            for x in o['pathways']:
                if x in groups: seen += groups[x]['children']
                elif x in stresses: seen.append(x)
                else: errs.append(f"observed stress {p['id']}.{o['id']}: unknown pathway {x}")
    for x in sorted(arch - covered - {K['archetypes']['normalisation']['fill']}): errs.append(f"archetype {x}: in no production system")
    for x in stresses - set(seen): errs.append(f"rule {x}: not under any observed stress")
    for a in K['archetypes'].get('cross_cutting', []):
        for x in a.get('key_stresses', []):
            if x not in stresses: errs.append(f"cross-cutting {a['id']}: unknown stress {x}")
    for a in K['archetypes']['archetypes']:
        for x in a.get('key_stresses', []):
            if x not in stresses: errs.append(f"archetype {a['id']}: unknown stress {x}")
    for s in K['schemes']['schemes']:
        for x in s['addresses']:
            if x not in stresses: errs.append(f"scheme {s['id']}: unknown stress {x}")
        for x in s['archetypes']:
            if x not in arch: errs.append(f"scheme {s['id']}: unknown archetype {x}")
        if s.get('condition'): chk(s['condition'], f"scheme {s['id']} condition")
    Q = K['questions']
    qids = set()
    for q in Q['system_questions'] + Q['stress_questions']:
        if q['id'] in qids: errs.append(f"question {q['id']}: duplicate id")
        qids.add(q['id'])
        if q.get('show_if'): chk(q['show_if'], f"question {q['id']} show_if")
        for s_ in q.get('stresses', []):
            if s_ not in stresses: errs.append(f"question {q['id']}: unknown stress {s_}")
        for o in q['options']:
            for e in o['stress']:
                if e['id'] not in stresses: errs.append(f"question {q['id']}.{o['id']}: unknown stress {e['id']}")
                if not e['lr'] > 0: errs.append(f"question {q['id']}.{o['id']}: lr must be > 0")
            for h in o.get('set', {}):
                if h not in helpers: errs.append(f"question {q['id']}.{o['id']}: unknown helper {h}")
            for sh in o.get('shift', []):
                for a in sh['from'] + (sh['to'] if isinstance(sh['to'], list) else [sh['to']]):
                    if a not in arch: errs.append(f"question {q['id']}.{o['id']}: unknown archetype {a}")
    # interventions (shared with the waterbody atlas)
    ivp = kd / 'interventions.json'
    n_iv = 0
    if ivp.exists():
        IV = load_json(ivp); wbk = kd / 'waterbody'
        wb_rules = {r['id'] for r in load_json(wbk / 'rules.json')['rules']} if (wbk / 'rules.json').exists() else set()
        wb_types = {t['id'] for t in load_json(wbk / 'types.json')['types']} if (wbk / 'types.json').exists() else set()
        sch = {x['id'] for x in K['schemes']['schemes']}
        if (wbk / 'schemes.json').exists(): sch |= {x['id'] for x in load_json(wbk / 'schemes.json')['schemes']}
        dims = {'rainfall', 'aquifer', 'terrain', 'gw_category', 'canal', 'cropping'}
        seen_iv = set()
        for x in IV['interventions']:
            w = f"intervention {x['id']}"; n_iv += 1
            if x['id'] in seen_iv: errs.append(f'{w}: duplicate id')
            seen_iv.add(x['id'])
            if x['side'] not in IV['sides']: errs.append(f"{w}: unknown side {x['side']}")
            if x['category'] not in IV['categories']: errs.append(f"{w}: unknown category {x['category']}")
            for k in ('suits', 'avoid'):
                if x.get(k): chk(x[k], f'{w} {k}', dims)
            for a in x.get('archetypes', []):
                if a not in arch: errs.append(f'{w}: unknown archetype {a}')
            for a in x.get('addresses', []):
                if a not in stresses: errs.append(f'{w}: unknown stress {a}')
            for a in x.get('addresses_wb', []):
                if a not in wb_rules: errs.append(f'{w}: unknown waterbody rule {a}')
            for a in x.get('wb_types') or []:
                if a not in wb_types: errs.append(f'{w}: unknown waterbody type {a}')
            for a in x.get('schemes', []):
                if a not in sch: errs.append(f'{w}: unknown scheme {a}')
            for a in x.get('sources', []):
                if a not in src: errs.append(f'{w}: unknown source {a}')
            if not x.get('addresses') and not x.get('addresses_wb'): errs.append(f'{w}: addresses nothing')
        covered = {a for x in IV['interventions'] for a in x.get('addresses', [])}
        for st in sorted(stresses - covered): errs.append(f'rule {st}: no intervention addresses it')
        cov_wb = {a for x in IV['interventions'] for a in x.get('addresses_wb', [])}
        for st in sorted(wb_rules - cov_wb): errs.append(f'waterbody rule {st}: no intervention addresses it')
    n_cc = _validate_cc(kd, K, errs)
    for e in errs: print('ERROR', e)
    print(f"{len(errs)} problems; {len(var)} variables, {len(arch)} archetypes, {len(nodes)} graph nodes, "
          f"{len(K['causal_graph']['edges'])} edges, {len(sig)} signals, {len(stresses)} rules under {sum(len(p['observed_stresses']) for p in T['production_systems'])} observed stresses in {len(T['production_systems'])} production systems, {len(K['schemes']['schemes'])} schemes, {len(qids)} questions, {n_iv} interventions, {len(src)} sources, {n_cc} Commons Connect questions")
    return not errs

def _validate_cc(kd, K, errs):
    """knowledge/commons_connect.json: atlas matches, mappings, rules, prefills, routes and work types."""
    import ast
    f = kd / 'commons_connect.json'
    if not f.exists(): return 0
    CC = load_json(f)
    WQ = load_json(kd / 'waterbody' / 'questions.json')
    aq = {('ws', q['id']): q for q in K['questions']['system_questions'] + K['questions']['stress_questions']}
    aq.update({('wb', q['id']): q for q in WQ['type_questions'] + WQ['stress_questions']})
    IV = load_json(kd / 'interventions.json') if (kd / 'interventions.json').exists() else {'interventions': []}
    ivs = {x['id'] for x in IV['interventions']}
    def expr_ok(e, w):
        if isinstance(e, (int, float)): return
        try: ast.parse(e, mode='eval')
        except SyntaxError: errs.append(f'{w}: bad expression {e!r}')
    n = 0
    for F in CC['forms']:
        names = {q['name'] for q in F['questions']}
        for q in F['questions']:
            n += 1; w = f"commons_connect {F['id']}.{q['name']}"; opts = {o['id'] for o in q.get('options') or []}
            if q.get('role') not in ('inform', 'record'): errs.append(f'{w}: role must be inform or record')
            for m in q.get('atlas_match') or []:
                a = aq.get((m['atlas'], m['id']))
                if not a: errs.append(f"{w}: unknown atlas question {m['atlas']}:{m['id']}"); continue
                if m['how'] not in CC['priority']['match_weight']: errs.append(f"{w}: unknown match {m['how']}")
                aopts = {o['id'] for o in a['options']}
                for k, v in (m.get('map') or {}).items():
                    if opts and k not in opts: errs.append(f'{w}: map key {k!r} is not an option')
                    if v not in aopts: errs.append(f"{w}: map value {v!r} is not an option of {m['id']}")
                for up, v in m.get('bins') or []:
                    if v not in aopts: errs.append(f"{w}: band value {v!r} is not an option of {m['id']}")
                if m.get('value'): expr_ok(m['value'], w)
            M = q.get('must_ask') or {}
            for r in M.get('rules') or []: expr_ok(r['if'], w); expr_ok(r['score'], w)
            for r in q.get('prefill') or []:
                expr_ok(r['if'], w)
                for v in ([r['value']] if 'value' in r else r.get('values', [])):
                    if v not in opts: errs.append(f'{w}: prefill {v!r} is not an option')
            for c in q.get('routes') or []:
                if c not in names: errs.append(f'{w}: routes to unknown question {c}')
            for e in (q.get('relevant_expr'), q.get('relevant') if q.get('origin') != 'odk' else None):
                if e: expr_ok(e, w)
            for k, v in (q.get('work_map') or {}).items():
                for i in v:
                    if i not in ivs: errs.append(f'{w}: work type {k!r} -> unknown intervention {i}')
            for i in q.get('demand_iv') or []:
                if i not in ivs: errs.append(f'{w}: unknown intervention {i}')
    asked = {(m['atlas'], m['id']) for F in CC['forms'] for q in F['questions'] for m in q.get('atlas_match') or [] if m['how'] != 'overlap'}
    for k in sorted(set(aq) - asked): errs.append(f'commons_connect: atlas question {k[0]}:{k[1]} is not asked in any form (same or derived)')
    return n
