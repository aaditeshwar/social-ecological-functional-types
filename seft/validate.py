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
    for e in errs: print('ERROR', e)
    print(f"{len(errs)} problems; {len(var)} variables, {len(arch)} archetypes, {len(nodes)} graph nodes, "
          f"{len(K['causal_graph']['edges'])} edges, {len(sig)} signals, {len(stresses)} rules under {sum(len(p['observed_stresses']) for p in T['production_systems'])} observed stresses in {len(T['production_systems'])} production systems, {len(K['schemes']['schemes'])} schemes, {len(qids)} questions, {len(src)} sources")
    return not errs
