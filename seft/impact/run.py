"""impact-run: the effect of every registered intervention, averages by unit, and the atlas bundles.

Needs the registry linked to atlas waterbodies (impact-link, or this command links first) and the waterbody
layers and tehsil data of the tehsils listed in config/impact/locations.json (wb-fetch; wb-run for the MWS
context used in the averages by rainfall regime, aquifer and so on).
Writes out/impact/records.json, averages.json, review.md and web/ bundles, then copies the bundles to
web/data/waterbody/ (impact.json, imp_<district>.json).
"""
import collections, json, random, shutil
from pathlib import Path
import warnings
import numpy as np
warnings.filterwarnings("ignore", category=RuntimeWarning, module=__name__)
from ..util import ROOT, load_json, raw_dir, slug, knowledge_dir
from . import registry as REG
from .pool import Pool, pool_years, mws_years, bundle_ctx, CTX_KEYS
from .estimate import Estimator, OUTCOMES
from .notes import render, signed, years_text, rules as note_rules

OUT = ROOT / 'out' / 'impact'
WEB = ROOT / 'web' / 'data' / 'waterbody'

def type_labels():
    T = load_json(knowledge_dir() / 'waterbody' / 'types.json')
    return {t['id']: t['label'] for t in T['types']}, {t['id'] for t in T['types'] if t['in_scope']}

def build_pool(districts, wcfg=None, log=print):
    """Pool over every cached tehsil of the given (state, district) pairs in the waterbody locations file."""
    from ..wb.build import build_tehsil
    wcfg = wcfg or load_json(ROOT / 'config' / 'waterbody' / 'locations.json')
    types = load_json(knowledge_dir() / 'waterbody' / 'types.json')
    scope = {t['id'] for t in types['types'] if t['in_scope']}
    bodies, ms, ctx, tehs = [], {}, {}, []
    for s, d in districts:
        e = next((x for x in wcfg['districts'] if x['state'] == s and x['district'] == d), None)
        for t in (e or {}).get('tehsils', []):
            if not (raw_dir(s, d, t) / 'swb_layers.json.gz').exists(): continue
            bs, _ = build_tehsil(s, d, t, types, log=lambda *a: None); bodies += bs; ms.update(mws_years(s, d, t)); tehs.append((d, t))
        ctx.update(bundle_ctx(d))
    P = Pool(bodies, pool_years(bodies), scope, ctx, ms)
    log(f'  pool: {len(P.key)} waterbodies in {len(tehs)} cached tehsils of {len(districts)} districts')
    return P, bodies

def treated_map(regs, pool):
    T = collections.defaultdict(list)
    for doc in regs:
        for r in doc['interventions']:
            w = r.get('waterbody') or {}
            if w.get('wb_id') is not None and r.get('year') and str(w['wb_id']) in pool.index: T[str(w['wb_id'])].append(r['year'])
    return T

def conf_flags(rec, S, wtype, area):
    F = S['flags']; out = []
    if area is not None and area < F['small']['max_area_ha']: out.append('small')
    if wtype in F['flow_driven']['types']: out.append('flow_driven')
    if rec.get('verdict') != 'not_assessable' and len(rec.get('post_years') or []) == 1: out.append('one_post_year')
    return out

def assess_waterbody(E, i, interventions, S, labels, screened=True, itype='desilting'):
    """Records (one per window) for pool row i. interventions: [{'year', 'volume_m3', 'ids', 'quality_flags'}]."""
    P = E.P; by = collections.OrderedDict()
    for x in sorted(interventions, key=lambda x: x['year']):
        e = by.setdefault(x['year'], {'year': x['year'], 'volume_m3': None, 'ids': [], 'quality_flags': []})
        if x.get('volume_m3') is not None: e['volume_m3'] = (e['volume_m3'] or 0) + x['volume_m3']
        e['ids'] += x.get('ids') or []; e['quality_flags'] = sorted(set(e['quality_flags']) | set(x.get('quality_flags') or []))
    ys = list(by); out = []
    windows = [('single' if len(ys) == 1 else 'first', ys[0], None, ys[1] if len(ys) > 1 else None)]
    if len(ys) > 1: windows.append(('combined', ys[0], ys[-1], None))
    for kind, y0, ystart, ynext in windows:
        rec = E.assess(i, y0, ystart, ynext)
        used = [by[y] for y in ys if y >= y0 and (ynext is None or y < ynext) and (kind != 'first' or y == y0)]
        rec.update(window=kind, intervention={'type': itype, 'years': [u['year'] for u in used],
                                              'volume_m3': sum(u['volume_m3'] or 0 for u in used) if any(u['volume_m3'] is not None for u in used) else None,
                                              'ids': [i_ for u in used for i_ in u['ids']]},
                   quality_flags=sorted({q for u in used for q in u['quality_flags']}))
        rec['flags'] = conf_flags(rec, S, P.type[i], float(P.area[i])) + ([] if screened else ['unscreened'])
        out.append(rec)
    return out

def note_env(rec, wb, S, labels, group=None, itype='desilting'):
    it = next((t for t in S['intervention_types'] if t['id'] == itype), {'label': itype})
    e = (rec.get('effects') or {}).get('W') or {}; did = e.get('did')
    vol = (rec.get('intervention') or {}).get('volume_m3'); area = wb.get('area')
    tl = labels.get(wb.get('type'), wb.get('type') or 'waterbody').lower()
    tlp = ' / '.join(x + 's' for x in tl.split(' / '))
    flags = [S['flags'][f]['label'] for f in rec.get('flags') or [] if f in S['flags']] + \
            [S['registry_quality']['labels'].get(q, q) for q in rec.get('quality_flags') or []]
    ys = (rec.get('intervention') or {}).get('years') or []
    g = group or {}
    return {'verdict': rec.get('verdict'), 'intervention_label_lower': it['label'].lower(),
            'year_label': ' and '.join(years_text([y]) for y in ys) or '–', 'type_label': tl, 'type_label_plural': tlp,
            'effect_signed': signed(did), 'effect_abs': f'{abs(did):.1f}' if did is not None else '–',
            'n_controls': (rec.get('controls') or {}).get('n', 0), 'radius_km': S['matching']['radius_km'],
            'post_text': years_text(rec.get('post_years')), 'reason': rec.get('reason') or '',
            'has_volume': vol is not None, 'volume_text': f'{vol:,.0f}' if vol is not None else '',
            'depth_text': f'{vol / (area * 1e4):.2f}' if vol is not None and area else '–',
            'n_flags': len(flags), 'flags_text': '; '.join(flags),
            'group_n': g.get('n', 0), 'group_unit': g.get('unit', ''), 'group_mean_signed': signed(g.get('mean'))}

def unit_stats(recs, S, label, R=None, rng=None):
    A = S['averages']; rng = rng or np.random.default_rng(7)
    xs = np.array([r['effects']['W']['did'] for r in recs], float)
    out = {'n': len(recs), 'unit_label': label}
    if len(xs):
        bs = [float(np.mean(rng.choice(xs, len(xs)))) for _ in range(A['bootstrap'])] if len(xs) > 1 else [float(xs[0])]
        out.update(mean=round(float(xs.mean()), 2), lo=round(float(np.percentile(bs, 2.5)), 2), hi=round(float(np.percentile(bs, 97.5)), 2),
                   n_gain=sum(r['verdict'] == 'likely_gain' for r in recs), n_loss=sum(r['verdict'] == 'likely_loss' for r in recs),
                   reference_mean=round(float(np.nanmean([r['effects']['W'].get('reference_mean') or np.nan for r in recs])), 2),
                   by_estimator={k: round(float(np.nanmean([r['effects']['W'].get(k) if r['effects']['W'].get(k) is not None else np.nan for r in recs])), 2)
                                 for k in ('did', 'did_rain', 'prepost_rain', 'counterfactual')},
                   RR=round(float(np.nanmean([r['effects']['RR'].get('did') if r['effects']['RR'].get('did') is not None else np.nan for r in recs])), 3),
                   SR=round(float(np.nanmean([r['effects']['SR'].get('did') if r['effects']['SR'].get('did') is not None else np.nan for r in recs])), 3))
    env = {'n': out['n'], 'min_n': A['min_n'], 'unit_label': label, 'intervention_label_lower': 'desilting',
           'mean_signed': signed(out.get('mean')), 'mean_abs': f'{abs(out.get("mean") or 0):.1f}',
           'lo': out.get('lo', 0), 'hi': out.get('hi', 0), 'lo_signed': signed(out.get('lo')), 'hi_signed': signed(out.get('hi')),
           'n_gain': out.get('n_gain', 0), 'n_loss': out.get('n_loss', 0), 'expected_each': f'{0.1 * out["n"]:.1f}'.rstrip('0').rstrip('.')}
    out['note'] = render('unit', env, R)
    return out

def averages(rows, S, R=None):
    """rows: [(record, unit values dict)]; uses single/first windows that are assessable and carry no quality flag."""
    use = [(r, u) for r, u in rows if r['window'] in ('single', 'first') and r['verdict'] != 'not_assessable' and not r['quality_flags']]
    out = {}
    for k in S['averages']['units']:
        g = collections.defaultdict(list)
        for r, u in use:
            if u.get(k) is not None: g[u[k]].append(r)
        out[k] = {str(v): unit_stats(rs, S, _unit_label(k, v), R) for v, rs in g.items()}
    return out

def _unit_label(k, v):
    t = str(v).replace('_', ' ')
    return {'state': t, 'district': f'{t} district', 'tehsil': f'{t.split("/")[-1]} tehsil', 'mws': f'MWS {t}',
            'type': f'{t}s', 'dominant_system': f'{t} areas'}.get(k, f'{t} ({k.replace("ctx_", "").replace("_", " ")})')

def main(registry_ids=None, cfg_path=None, out=None, web=True, link=True, log=print):
    S = REG.settings(); R = note_rules(); labels, scope = type_labels()
    paths = [REG.REG_DIR / f'{r}.json' for r in registry_ids] if registry_ids else None
    regs = REG.load_all(paths)
    if not regs: raise SystemExit('No registry in data/registries/. Build one with impact-build-registry.')
    icfg = load_json(cfg_path or REG.IMPACT_CFG / 'locations.json')
    wcfg = load_json(ROOT / 'config' / 'waterbody' / 'locations.json')
    if link:
        for doc in regs:
            REG.link(doc, wcfg, log=log); REG.save(doc, REG.REG_DIR / f'{doc["registry"]["id"]}.json')
    districts = [(d['state'], d['district']) for d in icfg['districts']]
    pool, _ = build_pool(districts, wcfg, log)
    E = Estimator(pool, S, treated_map(regs, pool))
    by = collections.defaultdict(list)
    for doc in regs:
        for r in doc['interventions']:
            w = r.get('waterbody') or {}
            if w.get('wb_id') is not None and r.get('year') and str(w['wb_id']) in pool.index:
                by[str(w['wb_id'])].append({'year': r['year'], 'volume_m3': r.get('volume_m3'), 'ids': [r['id']], 'quality_flags': r.get('quality_flags') or []})
    log(f'  {sum(len(v) for v in by.values())} interventions on {len(by)} pool waterbodies')
    recs = []
    for n, (k, xs) in enumerate(sorted(by.items())):
        i = pool.index[k]
        wb = {'wb_id': k, 'state': pool.state[i], 'district': pool.district[i], 'tehsil': pool.tehsil[i], 'mws': pool.mws[i],
              'type': pool.type[i], 'area': round(float(pool.area[i]), 2), 'xy': [round(float(c), 5) for c in pool.lonlat[i]]}
        for rec in assess_waterbody(E, i, xs, S, labels):
            recs.append({**wb, **rec})
        if (n + 1) % 100 == 0: log(f'    {n + 1} of {len(by)} waterbodies')
    unit_of = lambda r: {'state': r['state'], 'district': r['district'], 'tehsil': f"{r['district']}/{r['tehsil']}", 'mws': r['mws'], 'type': r['type'],
                         **{c: (pool.ctx[pool.index[r['wb_id']]] or {}).get(c) for c in CTX_KEYS}}
    AV = averages([(r, unit_of(r)) for r in recs], S, R)
    for r in recs:
        g = (AV.get('type') or {}).get(r['type']) if r['type'] else None
        gd = None
        if g is not None:
            same = [x for x in recs if x['district'] == r['district'] and x['type'] == r['type'] and x['window'] in ('single', 'first')
                    and x['verdict'] != 'not_assessable' and not x['quality_flags']]
            if same: gd = {'n': len(same), 'unit': f"{r['district']} district", 'mean': float(np.mean([x['effects']['W']['did'] for x in same]))}
        r['note'] = render('waterbody', note_env(r, r, S, labels, gd), R)
    write(recs, AV, regs, S, out, web, log)
    return recs, AV

def write(recs, AV, regs, S, out=None, web=True, log=print):
    out = Path(out or OUT); (out / 'web').mkdir(parents=True, exist_ok=True)
    (out / 'records.json').write_text(json.dumps(recs, indent=1, ensure_ascii=False), encoding='utf-8')
    (out / 'averages.json').write_text(json.dumps(AV, indent=1, ensure_ascii=False), encoding='utf-8')
    (out / 'review.md').write_text(review(recs, AV, S), encoding='utf-8')
    by = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in recs: by[r['district']][r['wb_id']].append({k: v for k, v in r.items() if k not in ('state', 'district', 'wb_id', 'xy')})
    idx = {'settings': {k: S[k] for k in ('intervention_types', 'outcomes', 'matching', 'estimators', 'verdict', 'flags', 'year_convention')},
           'quality_labels': S['registry_quality']['labels'],
           'registries': [{**d['registry'], 'n': len(d['interventions']),
                           'linked': sum(1 for r in d['interventions'] if (r.get('waterbody') or {}).get('wb_id') is not None)} for d in regs],
           'districts': [{'district': d, 'slug': slug(d), 'n_waterbodies': len(v), 'n_records': sum(len(x) for x in v.values())} for d, v in sorted(by.items())],
           'averages': AV}
    files = {'impact': idx, **{f'imp_{slug(d)}': {'district': d, 'waterbodies': v} for d, v in by.items()}}
    for n, o in files.items():
        (out / 'web' / f'{n}.json').write_text(json.dumps(o, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
    log(f'  wrote {out}/records.json ({len(recs)} records), averages.json, review.md, web/ ({len(files)} bundles)')
    if web:
        from ..webdata import write_js
        WEB.mkdir(parents=True, exist_ok=True)
        for f in WEB.glob('imp_*.json'): f.unlink()
        for f in WEB.glob('wb_imp_*.js'): f.unlink()
        for n in files:
            text = (out / 'web' / f'{n}.json').read_text(encoding='utf-8')
            (WEB / f'{n}.json').write_text(text, encoding='utf-8'); write_js(f'wb_{n}', text, WEB)
        log(f'  copied to {WEB.relative_to(ROOT)}')

def review(recs, AV, S):
    """A short Markdown summary for deciding on pooling, estimators and thresholds."""
    L = ['# Impact review', '']
    ok = [r for r in recs if r['window'] in ('single', 'first') and r['verdict'] != 'not_assessable']
    L.append(f'{len(recs)} records; {len(ok)} assessable single or first windows; '
             f'{sum(1 for r in ok if r["quality_flags"])} of them carry quality flags and are left out of averages.')
    L += ['', '| Verdict | n |', '| --- | --- |'] + [f'| {k} | {v} |' for k, v in collections.Counter(r['verdict'] for r in recs).most_common()]
    reasons = collections.Counter(r.get('reason', '').split(';')[0] for r in recs if r['verdict'] == 'not_assessable')
    L += ['', '## Not assessable', '', '| Reason | n |', '| --- | --- |'] + [f'| {k} | {v} |' for k, v in reasons.most_common()]
    W = [r['effects']['W'] for r in ok if not r['quality_flags']]
    if W:
        def agree(k):
            xs = [np.sign(w['did']) == np.sign(w[k]) for w in W if w.get(k) is not None and w.get('did') is not None]
            return f'{100 * np.mean(xs):.0f}%' if xs else '–'
        def mean(k):
            xs = [w[k] for w in W if w.get(k) is not None]
            return f'{np.mean(xs):+.2f}' if xs else '–'
        L += ['', '## Estimators (weeks of water, unflagged records)', '', '| Estimator | Mean | Same sign as DiD |', '| --- | --- | --- |']
        L += [f'| {k} | {mean(k)} | {agree(k) if k != "did" else "—"} |' for k in ('did', 'did_rain', 'prepost_rain', 'counterfactual')]
        pl = [v for w in W for v in (w.get('placebo') or {}).values() if v is not None]
        if pl: L.append(f'\nPlacebo DiD: mean {np.mean(pl):+.2f}, spread {np.std(pl):.2f} weeks over {len(pl)} placebo windows.')
    for k in ('district', 'type', 'ctx_rainfall', 'ctx_aquifer', 'dominant_system'):
        rows = sorted((AV.get(k) or {}).items(), key=lambda kv: -kv[1]['n'])
        if not rows: continue
        L += ['', f'## By {k}', '', '| Unit | n | Mean DiD (95% range) | Likely gain / loss | Reference mean |', '| --- | --- | --- | --- | --- |']
        L += [f"| {v} | {s['n']} | {s.get('mean', 0):+.2f} ({s.get('lo', 0):+.2f}, {s.get('hi', 0):+.2f}) | {s.get('n_gain', 0)} / {s.get('n_loss', 0)} | {s.get('reference_mean', 0):+.2f} |" for v, s in rows]
    return '\n'.join(L) + '\n'
