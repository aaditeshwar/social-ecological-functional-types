"""impact-validate: check knowledge/impact, config/impact and the registries in data/registries."""
import collections
from ..util import ROOT, load_json, knowledge_dir
from ..expr import compile_expr
from . import registry as REG

ROLES = ('reference', 'test', 'coverage')

def panel_errors(N, page=None, key='panel', fn='impT'):
    """notes.json `panel` (page function impT) and `fp_panel` (fpT): every key the atlas page uses exists, and each
    text uses only its declared placeholders."""
    import re
    P = N.get(key); errs = []
    if not isinstance(P, dict): return [f'notes.json: missing "{key}" (fixed text of the impact panels)']
    decl = {k: {x.strip() for x in v.split(',')} for k, v in P.get('_placeholders', {}).items()}
    for k, t in P.items():
        if k.startswith('_'): continue
        used = set(re.findall(r'\{(\w+)\}', t))
        if used - decl.get(k, set()): errs.append(f'notes.json {key}.{k}: placeholder(s) {sorted(used - decl.get(k, set()))} not listed in {key}._placeholders')
    page = page or ROOT / 'web' / 'index.html'
    if page.exists():
        text = page.read_text(encoding='utf-8')
        used = set(re.findall(fn + r'\("(\w+)"', text))
        if fn == 'fpT': used |= {'flag_' + f for f in ('appeared_2019', 'small')}      # built as fpT("flag_"+f)
        for k in sorted(x for x in used - set(P) if not x.endswith('_')):
            errs.append(f'notes.json {key}: key "{k}" is used by web/index.html but not defined')
    return errs

def farmpond_errors(N, warns):
    """knowledge/impact/farmponds.json, references.json and the fp_* note rules."""
    errs = []
    fp = knowledge_dir() / 'impact' / 'farmponds.json'
    if not fp.exists(): return ['knowledge/impact/farmponds.json is missing']
    F = load_json(fp)
    for k in ('intervention', 'years', 'appearance', 'drought', 'outcomes', 'footprint', 'background', 'estimators', 'lining', 'verdict', 'averages', 'heterogeneity', 'effectiveness'):
        if k not in F: errs.append(f'farmponds.json: missing "{k}"')
    Y = F.get('years', {})
    if not (Y.get('series') and Y['series'][0] < Y.get('first_appearance', 0) <= Y.get('last_main', 0) <= Y.get('last_appearance', 0) <= Y['series'][-1]):
        errs.append('farmponds.json years: need series[0] < first_appearance <= last_main <= last_appearance <= series[-1]')
    if [o['id'] for o in F.get('outcomes', [])] != ['ci', 'nonkharif', 'multi', 'cropped']: errs.append('farmponds.json outcomes: expected ci, nonkharif, multi, cropped')
    if {e['id'] for e in F.get('estimators', [])} != {'imputation', 'did_district', 'background', 'placebo'}: errs.append('farmponds.json estimators: expected imputation, did_district, background, placebo')
    L = F.get('lining', {})
    if not (0 <= L.get('unlined_summer_area', 0) < L.get('lined_summer_area', 0) <= 100): errs.append('farmponds.json lining: need unlined_summer_area < lined_summer_area')
    V = F.get('verdict', {})
    if not (0 < V.get('loss_pct', 0) < V.get('gain_pct', 0) < 100): errs.append('farmponds.json: verdict needs 0 < loss_pct < gain_pct < 100')
    rp = knowledge_dir() / 'impact' / 'references.json'
    refs = {r['id'] for r in load_json(rp)['references']} if rp.exists() else set()
    if not rp.exists(): errs.append('knowledge/impact/references.json is missing')
    S = load_json(knowledge_dir() / 'impact' / 'settings.json')
    cited = list(F['intervention'].get('references', [])) + [x for e in F.get('estimators', []) for x in e.get('references', [])] + \
            list(F.get('heterogeneity', {}).get('references', [])) + [x for t in S.get('intervention_types', []) for x in t.get('references', [])]
    for c in cited:
        if c not in refs: errs.append(f'impact reference "{c}" is cited but not in references.json')
    T = {t['id'] for t in load_json(knowledge_dir() / 'waterbody' / 'types.json')['types']}
    for t in list(F.get('intervention', {}).get('types', [])) + list(F.get('not_assessed', {})) + list(F.get('lining', {}).get('types', [])):
        if t not in T: errs.append(f'farmponds.json: type "{t}" is not in knowledge/waterbody/types.json')
    for kind in ('fp_waterbody', 'fp_unit', 'fp_old', 'fp_none'):
        for part in ('main', 'add'):
            for i, r in enumerate(N.get(kind, {}).get(part, [])):
                try: compile_expr(r['when'])
                except Exception as e: errs.append(f'notes.json {kind}.{part}[{i}]: {e}')
        if not N.get(kind, {}).get('main') or N[kind]['main'][-1]['when'] != 'true':
            warns.append(f'notes.json {kind}.main: the last rule should be `true` so every result gets a note')
    errs += panel_errors(N, key='fp_panel', fn='fpT')
    return errs

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
    errs += panel_errors(N)
    errs += farmpond_errors(N, warns)
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
