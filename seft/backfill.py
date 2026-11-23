"""Fill datasets that the API truncated, using the GeoServer layers that back
the same API (values verified identical on overlapping rows). Only used when
the API copy in the cache is missing or incomplete."""
import json, datetime
from pathlib import Path
from collections import defaultdict
from .util import ROOT, load_json, dump_json, raw_dir, gs_slug, iter_locations, data_root

def apply(path=None, cfg=None):
    path = Path(path or data_root() / 'geo' / 'geoserver_backfill.json')
    if not path.exists():
        return []
    B = load_json(path)
    names = {gs_slug(d) + '_' + gs_slug(t): (s, d, t) for s, d, t in iter_locations(cfg)}
    log = []
    for ds, per in B.items():
        for key, rows in per.items():
            if key not in names or key == 'amaravati_achalpur': continue  # achalpur rows were fetched only to verify equivalence
            s, d, t = names[key]
            p = raw_dir(s, d, t) / (ds + '.json')
            cur = load_json(p) if p.exists() else None
            if cur and cur.get('complete') and cur['n_rows'] >= len(rows):
                continue
            if ds == 'croppingintensity_annual':
                for r in rows:
                    if r['metadata'].get('sum_area') is not None:
                        r['metadata']['sum_area'] = round(r['metadata']['sum_area'] / 1e4, 2)  # m2 -> ha
            if ds == 'social_economic_indicator':
                agg = defaultdict(lambda: {'total_population': 0, 'total_sc_population': 0, 'total_st_population': 0, 'lit': 0})
                nm = {}
                for r in rows:
                    a = agg[r['village_id']]; nm[r['village_id']] = r['village_name']
                    for k in ('total_population', 'total_sc_population', 'total_st_population'):
                        a[k] += r[k] or 0
                    a['lit'] += (r['literacy_rate'] or 0) * (r['total_population'] or 0) / 100
                rows = [{'village_id': v, 'village_name': nm[v], 'total_population': a['total_population'],
                         'total_sc_population': a['total_sc_population'], 'total_st_population': a['total_st_population'],
                         'literacy_rate': round(a['lit'] / a['total_population'] * 100, 2) if a['total_population'] else 0}
                        for v, a in agg.items() if v]
            dump_json({'dataset': ds, 'state': s, 'district': d, 'tehsil': t, 'complete': True, 'n_rows': len(rows),
                       'units': (cur or {}).get('units', {}), 'rows': rows, 'fetched': datetime.date.today().isoformat(),
                       'source': 'geoserver_backfill', 'replaced': None if not cur else {'n_rows': cur['n_rows'], 'complete': cur.get('complete')}}, p)
            log.append((d, t, ds, len(rows), None if not cur else cur['n_rows']))
    return log

if __name__ == '__main__':
    for l in apply(): print(l)
