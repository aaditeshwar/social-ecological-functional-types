"""Write CSV/JSON outputs and the per-district bundles used by the web viewer."""
import csv, json, math
from collections import Counter, defaultdict
from pathlib import Path
from shapely.ops import unary_union
from .util import ROOT, load_json, dump_json, slug, gs_slug
from .geo import to_shape, encode_geom

STATUS = {'triggered': 2, 'not triggered': 1, 'not applicable': 0, 'unknown': -1, 'insufficient data': -1}
SEV = {'severe': 2, 'moderate': 1}
KFILES = ('variables', 'contexts', 'archetypes', 'signals', 'taxonomy', 'causal_graph', 'schemes', 'questions', 'sources', 'interventions', 'notes')

def _knowledge(kd):
    return {k: load_json(kd / f'{k}.json') for k in KFILES}

def _scheme_names(K):
    from .interventions import scheme_names
    wb = ROOT / 'knowledge' / 'waterbody' / 'schemes.json'
    return scheme_names(K['schemes'], load_json(wb) if wb.exists() else None)

def _wb_rule_labels():
    p = ROOT / 'knowledge' / 'waterbody' / 'rules.json'
    return {r['id']: r['label'] for r in load_json(p)['rules']} if p.exists() else {}

def _pw_cols(K):
    from .stresses import os_keys
    return [k for k, *_ in os_keys(K['taxonomy'], K['causal_graph'])]

def write_csv(records, villages, K, outdir):
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    var_ids = [v['id'] for v in K['variables']['variables'] if not v.get('series')] + ['rain_norm']
    var_ids = list(dict.fromkeys(var_ids))
    dims = [d['id'] for d in K['contexts']['dimensions']]
    arch = [a['id'] for a in K['archetypes']['archetypes']]
    sids = [s['id'] for s in K['causal_graph']['stresses']]
    pw = _pw_cols(K)
    by = defaultdict(list)
    for r in records: by[r['district']].append(r)
    files = []
    head = (['uid', 'state', 'district', 'home_tehsil', 'all_tehsils', 'area_ha'] + var_ids + ['ctx_' + d for d in dims] +
            ['share_' + a for a in arch] + ['dominant_system', 'systems_present'] +
            [f'{k}_{x}' for k in pw for x in ('status', 'intensity')] +
            [f'{s}_status' for s in sids] + [f'{s}_intensity' for s in sids] + [f'{s}_severity' for s in sids] + [f'{s}_posterior' for s in sids] +
            ['mix_raw_total', 'n_answers', 'schemes', 'interventions_suited', 'interventions_possible', 'canal_projects', 'n_villages'])
    for d, recs in list(by.items()) + [('all', records)]:
        p = outdir / f'mws_{slug(d)}.csv'
        with open(p, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f); w.writerow(head)
            for r in recs:
                w.writerow([r['uid'], r['state'], r['district'], r['tehsil'], ';'.join(r['tehsils']), round(r['area'], 2)] +
                           [r['ind'].get(v) for v in var_ids] + [r['ctx'].get(x) for x in dims] +
                           [r['mix']['shares'][a] for a in arch] + [r['mix']['dominant'], ';'.join(r['mix']['present'])] +
                           [x for k in pw for x in (r['pathways'][k]['status'], r['pathways'][k]['intensity'])] +
                           [r['stress'][s]['status'] for s in sids] + [r['stress'][s].get('intensity') for s in sids] +
                           [r['stress'][s].get('severity') or '' for s in sids] +
                           [r['stress'][s].get('posterior') for s in sids] + [r['mix'].get('raw_total'), len(r.get('answers') or {})] +
                           [';'.join(x['id'] for x in r['schemes']),
                            ';'.join(x['id'] for x in r.get('interventions', []) if x['fit'] == 'suited'),
                            ';'.join(x['id'] for x in r.get('interventions', []) if x['fit'] == 'possible'),
                            ';'.join(r['canals']), r.get('n_villages', '')])
        files.append(p)
    if villages is None:
        return files
    head_v = ['village_id', 'name', 'district', 'tehsil', 'mws_uid', 'overlap_share', 'area_in_district_mws_ha', 'population',
              'sc_population', 'st_population', 'literacy_rate', 'livestock_total', 'cattle', 'buffalo', 'sheep', 'goat', 'pig']
    allv = []
    for d, vs in villages.items():
        rows = []
        for v in vs.values():
            L = v.get('livestock') or {}
            rows.append([v['village_id'], v['name'], d, v['tehsil'], v.get('mws'), v.get('overlap_share'), v.get('area_ha'), v['pop'], v['sc'], v['st'],
                         v['literacy'], L.get('all_livestock_total'), L.get('cattle_total'), L.get('buffalo_total'), L.get('sheep_total'),
                         L.get('goat_total'), L.get('pig_total')])
        allv += rows
        p = outdir / f'villages_{slug(d)}.csv'
        with open(p, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f); w.writerow(head_v); w.writerows(rows)
        files.append(p)
    with open(outdir / 'villages_all.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(head_v); w.writerows(allv)
    files.append(outdir / 'villages_all.csv')
    return files

def _r(x, n=3):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else (round(x, n) if isinstance(x, float) else x)

def write_web(records, villages, clusters, meta, K, cfg, outdir, geom_path=None):
    """index.json (knowledge, India map, district summaries) and one bundle per district."""
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    geo = load_json(geom_path or ROOT / 'data' / 'geo' / 'geometry_raw.json')
    states = load_json(ROOT / 'data' / 'geo' / 'india_states.json')
    var_ids = [v['id'] for v in K['variables']['variables'] if not v.get('series')] + ['rain_norm']
    var_ids = list(dict.fromkeys(var_ids))
    arch = [a['id'] for a in K['archetypes']['archetypes']]
    sids = [s['id'] for s in K['causal_graph']['stresses']]
    dims = [d['id'] for d in K['contexts']['dimensions']]
    sig_ids = [x['id'] for x in K['signals']['signals']]
    pw = _pw_cols(K)
    by = defaultdict(list)
    for r in records: by[r['district']].append(r)
    districts = []
    for dcfg in cfg['districts']:
        d = dcfg['district']; recs = by[d]
        teh, mwsgeom, vill_xy = [], {}, {}
        shapes = []
        for t in dcfg['tehsils']:
            g = geo.get(f"{gs_slug(d)}/{gs_slug(t)}")
            if not g: continue
            teh.append({'name': t, 'geom': g['teh'], 'n_mws': sum(1 for r in recs if t in r['tehsils'])})
            s = to_shape(g['teh'])
            if s is not None: shapes.append(s)
            for uid, e in g['mws'].items():
                mwsgeom.setdefault(uid, e)
            for v in g['vill']:
                vill_xy[int(v[0])] = (v[2], v[3])
        dshape = unary_union([s.buffer(0.002) for s in shapes]).buffer(-0.002) if shapes else None
        outline = encode_geom(dshape, 0.003) if dshape is not None else ''
        bounds = dshape.bounds if dshape is not None else None
        mws_out = []
        for r in recs:
            st = {}
            WC = {'triggered': 2, 'not triggered': 1, 'insufficient data': -1}
            for s in sids:
                x = r['stress'][s]
                st[s] = [STATUS[x['status']], SEV.get(x.get('severity'), 0), _r(x.get('intensity'), 1),
                         WC.get(x['would'], -1), SEV.get(x.get('would_severity'), 0)]
            sg = [_r(r['signals'][k]['grade'], 3) for k in sig_ids]
            sb = [r['signals'][k].get('tix') for k in sig_ids]
            hids = [h['id'] for h in K['archetypes']['helpers']]
            mx0 = r.get('mix0', r['mix'])
            mws_out.append({'u': r['uid'], 't': r['tehsil'], 'ts': r['tehsils'], 'a': round(r['area'], 1),
                            'g': mwsgeom.get(r['uid'], ''), 'i': [_r(r['ind'].get(v), 4) for v in var_ids],
                            'c': [r['ctx'].get(x) for x in dims], 'm': [r['mix']['shares'][a] for a in arch],
                            'dom': r['mix']['dominant'], 's': st, 'sg': sg, 'sb': sb, 'h': [mx0['helpers'].get(h) for h in hids] + [mx0.get('raw_total')], 'el': r.get('eligible', []), 'sc': [[x['id'], x['because']] for x in r['schemes']],
                            'cp': r['canals'], 'v': clusters[d].get(r['uid'], [])})
        vout = []
        for v in villages[d].values():
            L = v.get('livestock') or {}
            xy = vill_xy.get(v['village_id'])
            vout.append([v['village_id'], v['name'], v['tehsil'], v.get('mws'), v.get('overlap_share'), v['pop'], v['sc'], v['st'],
                         v['literacy'], L.get('all_livestock_total'), L.get('cattle_total'), L.get('buffalo_total'),
                         L.get('sheep_total'), L.get('goat_total'), L.get('pig_total'), xy[0] if xy else None, xy[1] if xy else None])
        bundle = {'district': d, 'state': dcfg['state'], 'tehsils': teh, 'outline': outline, 'var_ids': var_ids, 'dims': dims,
                  'arch': arch, 'stress_ids': sids, 'signal_ids': sig_ids, 'mws': mws_out,
                  'village_cols': ['id', 'name', 'tehsil', 'mws', 'overlap', 'pop', 'sc', 'st', 'literacy', 'livestock', 'cattle',
                                   'buffalo', 'sheep', 'goat', 'pig', 'lon', 'lat'], 'villages': vout}
        dump_json(bundle, outdir / f'd_{slug(d)}.json')
        # summary
        tot = sum(r['area'] for r in recs) or 1
        mix = {a: round(sum(r['area'] * r['mix']['shares'][a] for r in recs) / tot, 3) for a in arch}
        n = max(len(recs), 1)
        sc = {s: round(sum(1 for r in recs if r['stress'][s]['status'] == 'triggered') / n, 3) for s in sids}
        for k in pw:
            sc[k] = round(sum(1 for r in recs if r['pathways'][k]['status'] == 'triggered') / n, 3)
        scheme_ct = Counter(x['id'] for r in recs for x in r['schemes'])
        iv_ct = Counter(x['id'] for r in recs for x in r.get('interventions', []) if x['fit'] == 'suited')
        districts.append({'district': d, 'state': dcfg['state'], 'slug': slug(d), 'n_mws': len(recs),
                          'n_villages': len(villages[d]), 'tehsils': [t['name'] for t in teh], 'outline': outline,
                          'bounds': bounds, 'mix': mix, 'stress_rate': sc, 'top_schemes': scheme_ct.most_common(12), 'top_interventions': iv_ct.most_common(12),
                          'rain_factor': round(meta['rain_factors'].get(d, 1.0), 3)})
    index = {'districts': districts, 'states': states, 'knowledge': K, 'pools': meta['pools'], 'var_ids': var_ids,
             'signal_ids': sig_ids, 'signal_thresholds': meta.get('signal_thresholds', {}),
             'scheme_names': _scheme_names(K), 'wb_rule_labels': _wb_rule_labels()}
    dump_json(index, outdir / 'index.json')
    return outdir
