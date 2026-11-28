"""Checks for the introductory-note rules (knowledge/notes.json, knowledge/waterbody/notes.json).

Each kind has `main` and `add` lists of {when, text}. Every `when` must parse, the last `main` rule should be `true`,
and every placeholder in a text must be a field declared in `_fields.<kind>` (keys may list several names,
comma-separated; '<dimension>_label' expands over the context dimensions) or one of the extra names given
(indicator or variable ids)."""
import re
from .expr import compile_expr

def declared(N, kind, dims=()):
    out = set()
    for k in (N.get('_fields') or {}).get(kind, {}):
        for name in (x.strip() for x in k.split(',')):
            if '<dimension>' in name: out |= {name.replace('<dimension>', d) for d in dims}
            else: out.add(name)
    return out

def check_notes(N, kinds, extra=(), dims=(), where='notes.json'):
    errs = []
    for kind in kinds:
        spec = N.get(kind)
        if not spec: errs.append(f'{where}: missing "{kind}"'); continue
        ok = declared(N, kind, dims) | set(extra)
        for part in ('main', 'add'):
            for i, r in enumerate(spec.get(part, [])):
                try: compile_expr(r['when'])
                except Exception as e: errs.append(f'{where} {kind}.{part}[{i}]: {e}')
                bad = sorted(set(re.findall(r'\{(\w+)\}', r['text'])) - ok)
                if bad: errs.append(f'{where} {kind}.{part}[{i}]: placeholder(s) {bad} not declared in _fields.{kind}')
        if not spec.get('main') or spec['main'][-1]['when'] != 'true':
            errs.append(f'{where} {kind}.main: the last rule should be `true` so every {kind} gets a note')
    return errs
