"""`python -m seft.cli wb-validate`: check knowledge/waterbody/*.json: ids are unique, expressions parse,
rules name only known types, signals, roles and contexts, and every signal or role used exists."""
import re
from ..expr import evaluate, ExprError
from .score import load_knowledge

_ID = re.compile(r'\b((?:s|ctx|role)_[a-z_]+)\b')

def _walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k == 'sources' and isinstance(v, list): yield k, v
            else: yield from _walk(v)
    elif isinstance(o, list):
        for x in o: yield from _walk(x)

def validate(kdir=None, log=print):
    K = load_knowledge(kdir); problems = []
    types = {t['id'] for t in K['types']['types']}
    sig = [s['id'] for s in K['signals']['signals']]; roles = [r['id'] for r in K['roles']['roles']]
    for name, ids in (('signal', sig), ('role', roles), ('rule', [r['id'] for r in K['rules']['rules']]), ('type', [t['id'] for t in K['types']['types']])):
        dup = {i for i in ids if ids.count(i) > 1}
        if dup: problems.append(f'duplicate {name} ids: {sorted(dup)}')
    known = set(sig) | set(roles)
    def check(expr, where):
        for x in _ID.findall(expr):
            if x not in known and not x.startswith('ctx_') : problems.append(f'{where}: unknown name {x}')
            if x.startswith('ctx_') and x not in known and x not in ('ctx_rainfall', 'ctx_aquifer', 'ctx_terrain', 'ctx_gw_category', 'ctx_canal', 'ctx_cropping'):
                problems.append(f'{where}: unknown context {x}')
        try: evaluate(expr, {})
        except ExprError as e:
            if 'not allowed' in str(e) or 'syntax' in str(e).lower(): problems.append(f'{where}: {e}')
        except Exception: pass
    for t in K['types']['types']: check(t['when'], f"type {t['id']}")
    for s in K['signals']['signals']:
        if 'expr' in s: check(s['expr'], f"signal {s['id']}")
        elif not ('pool' in s or ('value' in s and 'severe' in s)): problems.append(f"signal {s['id']}: needs value and severe, or a pool")
    for r in K['roles']['roles']: check(r['expr'], f"role {r['id']}")
    for r in K['rules']['rules']:
        for f in ('trigger', 'intensity', 'gate'):
            if r.get(f): check(r[f], f"rule {r['id']} {f}")
        bad = [t for t in r['applies_to'] if t not in types]
        if bad: problems.append(f"rule {r['id']}: unknown types {bad}")
        for k in ('label', 'rationale', 'public_note'):
            if not r.get(k): problems.append(f"rule {r['id']}: missing {k}")
    sch = [x['id'] for x in K['schemes']['schemes']]; rids = {r['id'] for r in K['rules']['rules']} | {'recent_ponds'}
    if len(set(sch)) != len(sch): problems.append('duplicate scheme ids')
    for key, links in K['schemes']['links'].items():
        if key not in rids: problems.append(f'schemes: links for unknown rule {key}')
        for l in links:
            if l['scheme'] not in sch: problems.append(f"schemes: {key} links unknown scheme {l['scheme']}")
            bad = [t for t in l.get('types', []) if t not in types]
            if bad: problems.append(f"schemes: {key}/{l['scheme']} unknown types {bad}")
    for r in K['rules']['rules']:
        if r['id'] not in K['schemes']['links']: problems.append(f"schemes: no schemes linked to rule {r['id']}")
    # questions
    rids = {r['id'] for r in K['rules']['rules']}; Q = K['questions']
    qids = [q['id'] for q in Q['type_questions'] + Q['stress_questions']]
    if len(set(qids)) != len(qids): problems.append('duplicate question ids')
    setf = {f['id'] for f in K['variables'].get('type_fields', [])}
    for q in Q['type_questions'] + Q['stress_questions']:
        for r in q.get('rules', []):
            if r not in rids: problems.append(f"question {q['id']}: unknown rule {r}")
        for t in q.get('applies_to', []):
            if t not in types: problems.append(f"question {q['id']}: unknown type {t}")
        for o in q['options']:
            for e in o.get('stress', []):
                if e['id'] not in rids: problems.append(f"question {q['id']}/{o['id']}: unknown rule {e['id']}")
                if not e.get('lr', 0) > 0: problems.append(f"question {q['id']}/{o['id']}: lr must be > 0")
            for f in (o.get('set') or {}):
                if f not in setf: problems.append(f"question {q['id']}/{o['id']}: sets unknown field {f}")
    asked = {r for q in Q['stress_questions'] for r in q.get('rules', [])}
    for r in rids - asked: problems.append(f'rule {r}: no community question')
    for r in K['rules']['rules']:
        if r.get('confidence') not in ('high', 'medium', 'low'): problems.append(f"rule {r['id']}: confidence must be high, medium or low")
    # sources
    known_src = {x['id'] for x in K['sources']['sources']}
    for name in ('types', 'variables', 'signals', 'roles', 'rules', 'questions'):
        for k, v in _walk(K[name]):
            if k == 'sources':
                for sid in v:
                    if sid not in known_src: problems.append(f'{name}: unknown source {sid}')
    for x in K['signals']['signals'] + K['roles']['roles'] + K['rules']['rules'] + K['types']['types']:
        if not x.get('sources'): problems.append(f"{x['id']}: no sources")
    from ..notes_check import check_notes
    problems += check_notes(K['notes'], ('waterbody', 'unit'), extra={v['id'] for v in K['variables']['variables']},
                            where='waterbody/notes.json')
    for p in problems: log('  ' + p)
    log(f"{len(problems)} problems; {len(K['types']['types'])} types, {len(sig)} signals, {len(roles)} roles, {len(K['rules']['rules'])} rules, {len(sch)} schemes, {len(qids)} questions, {len(known_src)} sources")
    return not problems
