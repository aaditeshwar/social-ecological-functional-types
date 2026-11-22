"""`python -m seft.cli wb-validate`: check knowledge/waterbody/*.json: ids are unique, expressions parse,
rules name only known types, signals, roles and contexts, and every signal or role used exists."""
import re
from ..expr import evaluate, ExprError
from .score import load_knowledge

_ID = re.compile(r'\b((?:s|ctx|role)_[a-z_]+)\b')

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
    for p in problems: log('  ' + p)
    log(f"{len(problems)} problems; {len(K['types']['types'])} types, {len(sig)} signals, {len(roles)} roles, {len(K['rules']['rules'])} rules")
    return not problems
