"""impact-validate: check knowledge/impact, config/impact and the registries in data/registries."""
import collections
from ..util import ROOT, load_json, knowledge_dir
from ..expr import compile_expr
from . import registry as REG

ROLES = ('reference', 'test', 'coverage')

def main(log=print):
    errs, warns = [], []
    S = load_json(knowledge_dir() / 'impact' / 'settings.json')
    for k in ('intervention_types', 'outcomes', 'matching', 'estimators', 'reference', 'verdict', 'flags', 'registry_quality', 'averages'):
        if k not in S: errs.append(f'settings.json: missing "{k}"')
    ids = {e['id'] for e in S.get('estimators', [])}
    if ids != {'did', 'did_rain', 'prepost_rain', 'counterfactual'}: errs.append(f'settings.json: estimators must be the four retained ones, got {sorted(ids)}')
    V = S.get('verdict', {})
    if not (0 < V.get('loss_pct', 0) < V.get('gain_pct', 0) < 100): errs.append('settings.json: verdict needs 0 < loss_pct < gain_pct < 100')
    N = load_json(knowledge_dir() / 'impact' / 'notes.json')
    for kind in ('waterbody', 'unit'):
        for part in ('main', 'add'):
            for i, r in enumerate(N.get(kind, {}).get(part, [])):
                try: compile_expr(r['when'])
                except Exception as e: errs.append(f'notes.json {kind}.{part}[{i}]: {e}')
        if not N.get(kind, {}).get('main') or N[kind]['main'][-1]['when'] != 'true':
            warns.append(f'notes.json {kind}.main: the last rule should be `true` so every result gets a note')
    p = REG.IMPACT_CFG / 'locations.json'
    if p.exists():
        for d in load_json(p)['districts']:
            bad = [r for r in d.get('roles', []) if r not in ROLES]
            if bad: errs.append(f'config/impact/locations.json {d["district"]}: unknown role(s) {bad}; use {ROLES}')
    known = set(S.get('registry_quality', {}).get('labels', {})) | {'year_missing'}
    types = {t['id'] for t in S.get('intervention_types', [])}
    for path in sorted(REG.REG_DIR.glob('*.json')):
        doc = load_json(path); rid = path.stem
        ids = collections.Counter(r['id'] for r in doc.get('interventions', []))
        dup = [k for k, v in ids.items() if v > 1]
        if dup: errs.append(f'{path.name}: duplicate intervention ids {dup[:5]}')
        for r in doc.get('interventions', []):
            if r.get('type') not in types: errs.append(f'{path.name} {r["id"]}: unknown type {r.get("type")}'); break
            if r.get('year') is not None and not isinstance(r['year'], int): errs.append(f'{path.name} {r["id"]}: year must be an integer')
            un = set(r.get('quality_flags') or []) - known
            if un: warns.append(f'{path.name} {r["id"]}: unknown quality flags {sorted(un)}')
        n = len(doc.get('interventions', [])); linked = sum(1 for r in doc['interventions'] if (r.get('waterbody') or {}).get('wb_id') is not None)
        log(f'  {path.name}: {n} interventions, {linked} linked to atlas waterbodies')
    for w in warns: log('  warning: ' + w)
    for e in errs: log('  ERROR: ' + e)
    log('impact knowledge and registries: ' + ('OK' if not errs else f'{len(errs)} error(s)'))
    return not errs
