"""`python -m seft.cli wb-run`: the waterbody atlas run, mirroring `run` for watersheds.

For every tehsil in the locations file (default config/waterbody/locations.json):
build waterbodies from the cached GeoServer layers (seft.wb.build), take the home MWS's context from the
watershed pipeline (seft.wb.context), score signals, roles and rules (seft.wb.score), and write
  out/waterbody/csv/wb_<district>.csv     one row per waterbody
  out/waterbody/web/index.json            knowledge, districts, counts and firing rates
  out/waterbody/web/w_<district>.json     waterbodies of one district for the frontend
then copy the web bundles and the CSV tables to web/data/waterbody/ (with --merge, districts not in this run
are kept), as `run` does with out/web and out/csv for watersheds.
"""
import collections, csv, json, math, re, shutil
from pathlib import Path
from ..util import ROOT, load_json, slug, iter_locations, raw_dir
from .build import build_all
from .context import mws_context, attach
from .villages import build_profiles
from .indicators import compute, year_reference
from .score import load_knowledge, base_env, pool_thresholds, score, scheme_links, iv_names, iv_env
from ..interventions import suggest

OUT = ROOT / 'out' / 'waterbody'
ARCH = [a['id'] for a in load_json(ROOT / 'knowledge' / 'archetypes.json')['archetypes']]
WEB_VARS = ['years_wet', 'k_fill', 'kr_mean', 'krz_mean', 'rel_slope', 'drought_fill_ratio', 'zoi_ci_mean', 'catchment_ratio']
WEB = ROOT / 'web' / 'data' / 'waterbody'
VAR_OUT = ['years_wet', 'is_new', 'regular', 'k_fill', 'kr_mean', 'krz_mean', 'retention_kr', 'retention_krz', 'k_early',
           'k_late', 'rel_slope', 'rel_late_to_early', 'drought_fill_ratio', 'catchment_ratio', 'zoi_ci_mean',
           'zoi_ci_slope', 'zoi_multi_crop_share', 'fish_village_share', 'surface_irrigation_share']
CTX_OUT = ['ctx_rainfall', 'ctx_aquifer', 'ctx_terrain', 'ctx_gw_category', 'ctx_canal', 'ctx_cropping', 'dominant_system']

STATUS = {'regular': {'code': 'r', 'label': 'Holds water regularly', 'about': 'Wet in 3 or more of the 8 years (2017-2024), and not new.'},
          'rarely_wet': {'code': 'x', 'label': 'Rarely holds water (1-2 of 8 years)', 'about': 'Wet in only 1 or 2 of the 8 years. Rules that need several wet years do not apply; a short-lived pond, a pond that fills only in very wet years, or a misdetection.'},
          'new': {'code': 'n', 'label': 'New (since 2022)', 'about': 'First wet in 2022 or later and wet every year since: mostly farm ponds dug recently. Counted per micro-watershed as recent ponds.'},
          'dry': {'code': 'd', 'label': 'Never wet', 'about': 'No wet year in the series.'}}

def status(b):
    v = b.get('vars') or {}
    if v.get('is_new'): return 'new'
    if v.get('regular'): return 'regular'
    return 'rarely_wet' if v.get('years_wet') else 'dry'

def recent_ponds(bodies, scope):
    """New waterbodies (status 'new', in scope) per home MWS: {uid: [count, area ha]}."""
    out = collections.defaultdict(lambda: [0, 0.0])
    for b in bodies:
        if b['type'] in scope and b.get('status') == 'new' and b['home_mws']:
            out[b['home_mws']][0] += 1; out[b['home_mws']][1] += b['area_ha']
    return {k: [n, round(a, 2)] for k, (n, a) in out.items()}

_NAME = re.compile(r"'[^']*'|\"[^\"]*\"|([A-Za-z_][A-Za-z0-9_]*)")
_FUNCS = {'nz', 'min', 'max', 'ramp', 'clip', 'ifelse', 'div', 'abs', 'isnan', 'known', 'ntrue', 'nknown', 'avg', 'and', 'or', 'not',
          'in', 'if', 'else', 'True', 'False', 'None', 'true', 'false', 'type', 'wb_type'}

def env_names(K):
    """Names the signals, roles and rules read, split into waterbody variables and home-MWS values, so the page can
    score a waterbody again (after a type answer) exactly as seft/wb/score.py does."""
    exprs = []
    for x in K['signals']['signals']: exprs += [x.get('expr'), x.get('gate'), x.get('var')]
    exprs += [r['expr'] for r in K['roles']['roles']]
    for r in K['rules']['rules']: exprs += [r.get('gate'), r.get('trigger'), r.get('intensity')]
    skip = _FUNCS | {x['id'] for x in K['signals']['signals']} | {r['id'] for r in K['roles']['roles']}
    names = {m.group(1) for e in exprs if e for m in _NAME.finditer(e) if m.group(1)} - skip
    mws = sorted(set(n for n in names if n.startswith(('mws_', 'share_', 'ctx_'))) | set(iv_names(K)))
    wb = [v['id'] for v in K['variables']['variables']]
    wb += sorted(n for n in names - set(mws) if n not in wb)
    return wb, mws

def _num(x, n=6):
    if isinstance(x, bool): return int(x)
    if isinstance(x, float):
        if math.isnan(x) or math.isinf(x): return None
        return float(f'{x:.{n}g}')
    return x

def _r(x, n=3):
    return round(x, n) if isinstance(x, float) else x

def _mean(xs):
    xs = [x for x in xs or [] if isinstance(x, (int, float))]
    return round(sum(xs) / len(xs), 2) if xs else None

def dedupe(B, log=print):
    """CoRE Stack tehsil layers overlap at tehsil borders, so a waterbody can come in with two or more tehsils.
    Keep one record per wb_id: the one in its home micro-watershed's tehsil, else the largest, else the first."""
    groups = collections.defaultdict(list)
    for i, b in enumerate(B): groups[b['wb_id']].append(i)
    keep = set()
    for ids in groups.values():
        if len(ids) == 1: keep.add(ids[0]); continue
        home = [i for i in ids if B[i]['tehsil'] == (B[i].get('mws') or {}).get('mws_tehsil')]
        keep.add(home[0] if home else max(ids, key=lambda i: (B[i]['area_ha'], -i)))
    n = len(B) - len(keep)
    if n: log(f'  {n} duplicate records of {sum(len(v) > 1 for v in groups.values())} waterbodies listed in more than one tehsil layer removed')
    return [b for i, b in enumerate(B) if i in keep]

def score_all(cfg, log=print, pools=None, pool_districts=None, pool_tehsils=None):
    """Build and score every waterbody of the locations. Returns (bodies, stats, types, K, pools)."""
    K = load_knowledge()
    B, stats, types = build_all(cfg, log=log)
    scope = {t['id'] for t in types['types'] if t['in_scope']}
    log('  landscape context: running the watershed pipeline for these tehsils')
    ctx = mws_context(cfg, log=log)
    prof, drought = build_profiles(cfg)
    attach(B, ctx, prof)
    B = dedupe(B, log=log)
    ref = year_reference(B, scope)
    for b in B: b['vars'] = compute(b, prof, drought, ref)
    if pools is None:
        pools = pool_thresholds([base_env(b, b['vars']) for b in B if b['type'] in scope
                                 and (pool_districts is None or b['district'] in pool_districts)
                                 and (pool_tehsils is None or (b['district'], b['tehsil']) in pool_tehsils)], K)
    for b in B:
        if b['type'] in scope: b['signals'], b['roles'], b['rules'] = score(b, b['vars'], K, pools)
        else: b['signals'], b['roles'], b['rules'] = {}, {}, {}
        b['status'] = status(b)
    return B, stats, types, K, pools

def _rule_cell(r):
    return r['intensity'] if r['status'] == 'triggered' else ('' if r['status'] == 'not applicable' else (0 if r['status'] == 'not triggered' else 'NA'))

def csv_row(b, K, rp=None):
    z = b.get('zoi') or {}; m = b['mws']; v = b.get('vars', {})
    row = {'wb_id': b['wb_id'], 'state': b['state'], 'district': b['district'], 'tehsil': b['tehsil'], 'type': b['type'], 'status': b['status'],
           'area_ha': b['area_ha'], 'n_fragments': b['n_fragments'], 'fragment_ids': ';'.join(map(str, b['fragment_ids'])),
           'wb_type': b['wb_type'], 'wb_name': b['wb_name'], 'on_drainage': b['on_drainage'], 'on_stream': b.get('on_stream'),
           'stream_order': b['stream_order'], 'catchment_ha': b['catchment_ha'], 'home_mws': b['home_mws'], 'mws_uids': ';'.join(b['mws_uids']),
           'lon': b['centroid'][0], 'lat': b['centroid'][1],
           'k_mean': _mean(b.get('k')), 'zoi_match': b['zoi_match'], 'zoi_radius_m': _r(z.get('zoi'), 1),
           'zoi_area_ha': z.get('zoi_area'), 'mws_in_atlas': b['mws_in_atlas'], 'n_mws_villages': b['n_mws_villages']}
    row.update({c: m.get(c) for c in CTX_OUT})
    row['mws_recent_ponds'] = (rp or {}).get(b['home_mws'], [0])[0] if b['home_mws'] else ''
    row.update({f'share_{a}': _r(m.get(f'share_{a}')) for a in ARCH})
    row.update({c: _r(v.get(c)) for c in VAR_OUT})
    row.update({r['id']: b['roles'].get(r['id'], '') for r in K['roles']['roles']})
    row.update({r['id']: _rule_cell(b['rules'][r['id']]) if r['id'] in b['rules'] else '' for r in K['rules']['rules']})
    row['schemes'] = ';'.join(sorted({s for rid, r in b['rules'].items() if r['status'] == 'triggered' for s in scheme_links(rid, b, K)}))
    pos = {rid for rid, r in b['rules'].items() if r['status'] == 'triggered'}
    ivs = suggest(iv_env(b['mws']), pos, K['interventions'], key='addresses_wb', wb_type=b['type']) if pos else []
    row['interventions_suited'] = ';'.join(x['id'] for x in ivs if x['fit'] == 'suited')
    row['interventions_possible'] = ';'.join(x['id'] for x in ivs if x['fit'] == 'possible')
    return row

def _i(xs):
    return [None if not isinstance(x, (int, float)) else round(x) for x in (xs or [])]

def web_record(b, K, env_ids=None):
    """Compact record for the frontend. Keys: id, t (type), teh, mws (home MWS; its context is in the bundle's
    'mws' table), a (area ha), xy (lon, lat), n (name), so (stream order), st (status code, see index 'status'), z (ZoI match: w=wb_id, l=location,
    -=none), k/kr/krz (yearly %, rounded), tf (type fields, index 'type_fields'), e (variables, index 'env_ids'),
    ro (roles in index order),
    ru ([rule index, status s/n/i (triggered, not triggered, insufficient), intensity] for applicable rules)."""
    rids = [r['id'] for r in K['rules']['rules']]; roles = [r['id'] for r in K['roles']['roles']]
    rec = {'id': b['wb_id'], 't': b['type'], 'teh': b['tehsil'], 'mws': b['home_mws'], 'a': round(b['area_ha'], 2),
           'xy': [round(b['centroid'][0], 5), round(b['centroid'][1], 5)], 'so': b['stream_order'],
           'st': STATUS[b['status']]['code'], 'z': {'wb_id': 'w', 'location': 'l'}.get(b['zoi_match'], '-'), 'k': _i(b.get('k')), 'kr': _i(b.get('kr')), 'krz': _i(b.get('krz'))}
    if b.get('wb_name'): rec['n'] = b['wb_name']
    rec['tf'] = [b.get('wb_type'), int(bool(b.get('on_drainage'))), b.get('n_mws'), int(bool(b.get('has_drainage_fields'))),
                 _num((b['catchment_ha'] / b['area_ha']) if b.get('area_ha') and b.get('catchment_ha') is not None else 0)]
    rec['e'] = [_num((b.get('vars') or {}).get(c)) for c in (env_ids or [])]
    if b.get('roles'):
        rec['ro'] = [round(b['roles'].get(r, 0), 2) for r in roles]
        rec['ru'] = [[i, {'triggered': 's', 'not triggered': 'n', 'insufficient data': 'i'}[b['rules'][rid]['status']], b['rules'][rid]['intensity']]
                     for i, rid in enumerate(rids) if b['rules'][rid]['status'] != 'not applicable']
    return rec

def rates(bodies, K, scope):
    out = {}
    for r in K['rules']['rules']:
        st = collections.Counter(b['rules'][r['id']]['status'] for b in bodies if b['type'] in scope)
        app = sum(v for k, v in st.items() if k != 'not applicable')
        out[r['id']] = {'label': r['label'], 'applicable': app, 'triggered': st['triggered'], 'insufficient': st['insufficient data']}
    return out

def write_outputs(B, stats, types, K, pools, cfg, out=None, log=print):
    out = Path(out or OUT); (out / 'csv').mkdir(parents=True, exist_ok=True); (out / 'web').mkdir(parents=True, exist_ok=True)
    scope = {t['id'] for t in types['types'] if t['in_scope']}
    by = collections.defaultdict(list)
    for b in B: by[b['district']].append(b)
    districts = []; env_ids, mws_ids = env_names(K)
    for d in cfg['districts']:
        bs = by.get(d['district'], []); s = slug(d['district'])
        if not bs: continue
        rp = recent_ponds(bs, scope)
        rows = [csv_row(b, K, rp) for b in bs]
        with open(out / 'csv' / f'wb_{s}.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        mws = {b['home_mws']: {c: _num(b['mws'].get(c)) for c in CTX_OUT + mws_ids} for b in bs if b['mws']}
        for u, (n, a) in rp.items():
            if u in mws: mws[u]['recent_ponds'] = n; mws[u]['recent_ponds_ha'] = a
        (out / 'web' / f'w_{s}.json').write_text(json.dumps({'district': d['district'], 'state': d['state'], 'mws': mws,
            'waterbodies': [web_record(b, K, env_ids) for b in bs]}, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
        districts.append({'district': d['district'], 'state': d['state'], 'slug': s, 'tehsils': d['tehsils'], 'n': len(bs),
                          'by_type': dict(collections.Counter(b['type'] for b in bs)),
                          'by_status': dict(collections.Counter(b['status'] for b in bs if b['type'] in scope)),
                          'recent_ponds': sum(n for n, _ in rp.values()), 'recent_pond_mws': len(rp),
                          'rules': rates(bs, K, scope)})
        log(f"  {d['district']}: {len(bs)} waterbodies -> csv/wb_{s}.csv, web/w_{s}.json")
    index = {'knowledge': K, 'types': types, 'web_vars': WEB_VARS, 'env_ids': env_ids, 'mws_ids': mws_ids,
             'type_fields': ['wb_type', 'on_drainage', 'n_mws', 'has_drainage_fields', 'catchment_ratio'], 'status': STATUS, 'districts': districts, 'tehsil_stats': stats,
             'pools': {k: {t: [_num(a), _num(c)] for t, (a, c) in v.items()} for k, v in pools.items()},
             'rules': rates(B, K, scope)}
    (out / 'web' / 'index.json').write_text(json.dumps(index, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
    return index

def build_web(src=None, dest=None, merge=False, log=print):
    """Copy out/waterbody/web to web/data/waterbody, as seft.webdata.build does for watersheds."""
    from ..webdata import write_js
    src = Path(src or OUT / 'web'); dest = Path(dest or WEB); dest.mkdir(parents=True, exist_ok=True)
    index = json.loads((src / 'index.json').read_text(encoding='utf-8'))
    if merge and (dest / 'index.json').exists():
        old = json.loads((dest / 'index.json').read_text(encoding='utf-8'))
        have = {d['district'] for d in index['districts']}
        kept = [d for d in old['districts'] if d['district'] not in have and (dest / f"w_{d['slug']}.json").exists()]
        index['districts'] += kept
        if kept: log('  kept from earlier runs: ' + ', '.join(d['district'] for d in kept))
    names = ['index'] + [f"w_{d['slug']}" for d in index['districts']]
    for n in names:
        if n == 'index': text = json.dumps(index, separators=(',', ':'), ensure_ascii=False)
        else:
            f = src / f'{n}.json'
            if not f.exists(): continue
            text = f.read_text(encoding='utf-8')
        (dest / f'{n}.json').write_text(text, encoding='utf-8')
        write_js(f'wb_{n}', text, dest)
    if not merge:
        for f in list(dest.glob('w_*.json')) + list(dest.glob('wb_w_*.js')):
            stem = f.stem[3:] if f.stem.startswith('wb_') else f.stem
            if stem not in names: f.unlink()
    csv_src = src.parent / 'csv'
    if csv_src.exists():                  # per-district tables for download, as web/data/csv for watersheds
        (dest / 'csv').mkdir(exist_ok=True)
        keep = {f"wb_{d['slug']}.csv" for d in index['districts']}
        for f in csv_src.glob('wb_*.csv'): shutil.copy2(f, dest / 'csv' / f.name)
        if not merge:
            for f in (dest / 'csv').glob('wb_*.csv'):
                if f.name not in keep: f.unlink()
    log(f'  wrote {len(names)} bundles to {dest}: {", ".join(d["district"] for d in index["districts"])}')

def main(cfg_path=None, out=None, merge=False, web=True, update_pools=False, log=print):
    """update_pools: recompute the waterbody pools over the 'pools' districts of the locations file (all must be
    in this run) and write them to knowledge/pools.json; otherwise score with the published pools."""
    from ..util import with_role, pools_doc, write_pools, district_roles
    import datetime
    cfg = load_json(cfg_path or ROOT / 'config' / 'waterbody' / 'locations.json')
    missing = [(d, t) for s, d, t in iter_locations(cfg) if not (raw_dir(s, d, t) / 'swb_layers.json.gz').exists()]
    if missing:
        names = ', '.join(f'{d}/{t}' for d, t in missing[:8]) + (' ...' if len(missing) > 8 else '')
        raise SystemExit(f'No waterbody layers for {len(missing)} tehsil(s): {names}\nRun `python -m seft.cli wb-fetch` first.')
    pub = pools_doc().get('waterbody')
    pool_d = [d['district'] for d in with_role(cfg, 'pools')['districts']]
    if update_pools or not pub:
        if not pool_d: raise SystemExit("No district in the locations file has the 'pools' role.")
        log(f"  pooling waterbody thresholds over the 'pools' districts: {', '.join(pool_d)}")
        from ..util import role_tehsils
        pool_t = {(d, t) for _, d, t in role_tehsils(cfg, 'pools')}
        B, stats, types, K, pools = score_all(cfg, log=log, pool_districts=set(pool_d), pool_tehsils=pool_t)
        write_pools('waterbody', {k: {t: [_num(a), _num(c)] for t, (a, c) in v.items()} for k, v in pools.items()},
                    {'districts': pool_d, 'computed': f'{datetime.date.today()}, wb-run --update-pools',
                     'n_waterbodies': sum(1 for b in B if (b['district'], b['tehsil']) in pool_t)})
        log('  wrote the waterbody pools to knowledge/pools.json (bump knowledge/manifest.json before releasing a pack)')
    else:
        log('  scoring with the published waterbody pools (knowledge/pools.json); --update-pools to recompute')
        B, stats, types, K, pools = score_all(cfg, log=log, pools={k: {t: tuple(x) for t, x in v.items()} for k, v in pub.items()})
    write_outputs(B, stats, types, K, pools, cfg, out, log=log)
    if web: build_web(Path(out or OUT) / 'web', merge=merge, log=log)
    return B
