"""Intervention registries: one JSON file per source in data/registries/, one record per intervention event.

build   read the CSV lists of GeoServer layers (desilted waterbodies, and optionally their zones of influence),
        fetch each layer (GeoServer port 8443: run where it is reachable), make one record per desilting row,
        drop duplicates across layers, resolve state / district / tehsil names against get_active_locations,
        and add the tehsils to the waterbody and impact locations files.
link    after the tehsils are fetched (wb-fetch), link each record to an atlas waterbody: the record's waterbody
        polygon (its representative point) or desilting point inside an atlas waterbody fragment, else the
        nearest fragment within registry_quality.link_max_m.

Record format (see knowledge/impact/README.md):
  {"id", "type", "year", "volume_m3", "waterbody": {"wb_id", "state", "district", "tehsil", "match": {...}},
   "point", "desilting_point", "location": {"state", "district", "tehsil", "status"}, "source": {...},
   "names": {...}, "implementer", "quality_flags": [...]}
"""
import csv, datetime, difflib, gzip, json, math, re
from collections import defaultdict
from pathlib import Path
from ..util import ROOT, load_json, raw_dir, slug

REG_DIR = ROOT / 'data' / 'registries'
IMPACT_CFG = ROOT / 'config' / 'impact'
YEAR = re.compile(r'(19|20)\d\d')
NA = {'', 'na', 'n/a', 'none', 'null', 'nan', '-'}

def settings():
    from ..util import knowledge_dir
    return load_json(knowledge_dir() / 'impact' / 'settings.json')

# ---------------------------------------------------------------- reading layers
def read_layer_list(path):
    """Rows of a layer list CSV (columns: state, district, id, layer, wfs_geojson_url; an optional `series` column
    is used to keep only waterbodies_atecf rows). Rows whose layer name ends in a dot are skipped."""
    rows = []
    with open(path, newline='', encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            r = {k.strip(): (v or '').strip() for k, v in r.items() if k}
            if not r.get('layer'): continue
            if r.get('series') and r['series'] not in ('waterbodies_atecf', 'waterbodies_zoi_atecf', 'zoi'): continue
            if r['layer'].endswith('.'): continue
            rows.append(r)
    return rows

def _fetch(url_or_path):
    if not re.match(r'^https?://', url_or_path):
        p = Path(url_or_path)
        return json.loads(gzip.open(p, 'rt', encoding='utf-8').read() if p.suffix == '.gz' else p.read_text(encoding='utf-8'))
    from ..fetch import _get
    return _get(url_or_path, {}).json()

def _num(v):
    try:
        x = float(v)
        return None if math.isnan(x) else x
    except (TypeError, ValueError):
        return None

def _txt(v):
    s = str(v).strip() if v is not None else ''
    return None if s.lower() in NA else s

def _rep_point(geom):
    if not geom: return None
    try:
        from shapely.geometry import shape
        g = shape(geom)
        if g.is_empty: return None
        p = g if g.geom_type == 'Point' else g.representative_point()
        return [round(p.x, 6), round(p.y, 6)]
    except Exception:
        return None

def records_from_layer(fc, layer, itype='desilting'):
    out = []
    for n, f in enumerate(fc.get('features', [])):
        p = f.get('properties') or {}
        m = YEAR.search(str(p.get('intervention_year') or ''))
        lat, lon = _num(p.get('desiltingpoint_lat')), _num(p.get('desiltingpoint_lon'))
        dpt = [round(lon, 6), round(lat, 6)] if lat is not None and lon is not None else None
        rid = _txt(p.get('desilt_id'))
        out.append({
            'id': f'{layer}:{rid if rid else n + 1}', 'type': itype,
            'year': int(m.group(0)) if m else None, 'year_text': _txt(p.get('intervention_year')),
            'volume_m3': _num(p.get('slit_excavated') if 'slit_excavated' in p else p.get('silt_excavated')),
            'point': _rep_point(f.get('geometry')) or dpt, 'desilting_point': dpt,
            'source_area_ha': _num(p.get('area_ored')),
            'names': {k: _txt(p.get(c)) for k, c in (('state', 'State'), ('district', 'District'), ('tehsil', 'Taluka'),
                                                       ('village', 'Village'), ('waterbody', 'waterbody_name'))},
            'implementer': _txt(p.get('name_of_ngo')),
            'source': {'layer': layer, 'record': rid, 'uid': _txt(p.get('UID')), 'mws_uid': _txt(p.get('MWS_UID')),
                       'distance_from_desilting_point_m': _num(p.get('distance_from_desilting_point'))},
            'waterbody': None, 'location': None, 'quality_flags': []})
    return out

def dedupe(records):
    """Drop records repeated across layers (old and new runs of a project): same desilting point (4 decimals),
    year and volume. The kept record lists the other layers under source.also_in."""
    seen, out = {}, []
    for r in records:
        pt = r['desilting_point'] or r['point']
        key = (round(pt[0], 4), round(pt[1], 4), r['year'], round(r['volume_m3'] or -1)) if pt else ('id', r['id'])
        if key in seen:
            seen[key]['source'].setdefault('also_in', []).append(r['source']['layer']); continue
        seen[key] = r; out.append(r)
    return out

# ---------------------------------------------------------------- names
def _norm(s):
    return re.sub(r'[\s\-_.()]+', ' ', (s or '').lower()).strip()

def _aliases():
    p = IMPACT_CFG / 'aliases.json'
    return load_json(p) if p.exists() else {'districts': {}, 'tehsils': {}}

def _best(name, labels, cutoff=0.8):
    n = _norm(name); by = {_norm(l): l for l in labels}
    if n in by: return by[n], 'exact'
    for k, l in by.items():                       # Mulshi -> Mulshi-Paud, Ahamadnagar (Ahmednagar) etc.
        if k.startswith(n + ' ') or n.startswith(k + ' '): return l, 'prefix'
    m = difflib.get_close_matches(n, list(by), n=1, cutoff=cutoff)
    return (by[m[0]], 'fuzzy') if m else (None, None)

def resolve(records, refresh_locations=False, log=print):
    """Set record['location'] = {state, district, tehsil, status} using get_active_locations and config/impact/aliases.json."""
    from ..groundtruth import active_locations
    locs = active_locations(refresh_locations, log)
    A = _aliases()
    states = {s['label']: s for s in locs}
    cache, unresolved = {}, defaultdict(int)
    for r in records:
        nm = r['names']; key = (nm.get('state'), nm.get('district'), nm.get('tehsil'))
        if key not in cache:
            st, _ = _best(nm.get('state'), list(states), 0.85)
            res = {'state': st, 'district': None, 'tehsil': None, 'status': 'state not found'}
            if st:
                dists = {d['label']: d for d in states[st]['district']}
                dn = A['districts'].get(f'{st}/{nm.get("district")}', nm.get('district'))
                dl, how = _best(dn, list(dists))
                if dl:
                    res.update(district=dl, status='tehsil not found')
                    blocks = [b['label'] for b in dists[dl]['block']] if 'block' in dists[dl] else [b['label'] for b in dists[dl]['blocks']]
                    tn = A['tehsils'].get(f'{st}/{dl}/{nm.get("tehsil")}', nm.get('tehsil'))
                    tl, how2 = _best(tn, blocks)
                    if tl: res.update(tehsil=tl, status='resolved' if how == how2 == 'exact' else f'resolved ({how}/{how2})')
                else:
                    res['status'] = 'district not found'
            cache[key] = res
        r['location'] = dict(cache[key])
        if not r['location']['tehsil']: unresolved[key] += 1
    for (s, d, t), n in sorted(unresolved.items(), key=lambda x: -x[1]):
        log(f'  unresolved: {s} / {d} / {t} ({n} records): {cache[(s, d, t)]["status"]}')
    return cache

# ---------------------------------------------------------------- zones of influence
def zoi_for(records, fc):
    """Match the zones of influence of a ZoI layer to records: the zone whose centre is nearest the record's point,
    within the zone's radius. Returns {record id: compact zone}."""
    from ..wb.layers import compact_zoi
    Z = compact_zoi(fc); out = {}
    seen = set(); zs = []
    for z in Z:                                    # identical duplicates (one per desilting row) are dropped
        k = (z.get('UID'), tuple(z.get('centre') or ()))
        if k in seen: continue
        seen.add(k); zs.append(z)
    for r in records:
        if not r['point']: continue
        best = None
        for z in zs:
            c = z.get('centre')
            if not c: continue
            d = _metres(r['point'], c)
            if d <= max(30.0, z.get('zoi') or 0) and (best is None or d < best[0]): best = (d, z)
        if best:
            z = best[1]; ndvi = {}
            for y, v in zip(z.get('years') or [], z.get('NDVI') or []):
                try: ndvi[y] = json.loads(v) if isinstance(v, str) else v
                except ValueError: pass
            out[r['id']] = {'uid': z.get('UID'), 'radius_m': z.get('zoi'), 'area_ha': z.get('zoi_area'), 'years': z.get('years'),
                            **{k: z.get(k) for k in ('cropping_intensity', 'single_cropped_area', 'single_kharif_cropped_area',
                                                     'single_non_kharif_cropped_area', 'doubly_cropped_area', 'triply_cropped_area')},
                            'total_cropable_area': z.get('total_cropable_area_ever_hydroyear_2017'), 'ndvi': ndvi,
                            'distance_m': round(best[0], 1)}
    return out

def _metres(a, b):
    k = 111320.0
    return math.hypot((a[0] - b[0]) * k * math.cos(math.radians(a[1])), (a[1] - b[1]) * k)

# ---------------------------------------------------------------- build
def build(reg_id, layers_csv, zoi_csv=None, name=None, itype='desilting', role='coverage', scope='tehsil',
          refresh_locations=False, add_locations=True, log=print):
    S = settings()
    rows = read_layer_list(layers_csv)
    recs, failed = [], []
    for r in rows:
        try:
            fc = _fetch(r['wfs_geojson_url']); rs = records_from_layer(fc, r['layer'], itype); recs.extend(rs)
            log(f'  {r["layer"]}: {len(rs)} records')
        except Exception as e:
            failed.append(r['layer']); log(f'  {r["layer"]}: FAILED {str(e)[:160]}')
    n0 = len(recs); recs = dedupe(recs)
    log(f'{n0} records from {len(rows) - len(failed)} layers; {n0 - len(recs)} duplicates across layers dropped; {len(recs)} kept')
    for r in recs:
        q = r['quality_flags']
        if r['volume_m3'] is None: q.append('volume_missing')
        if r['year'] is None: q.append('year_missing')
    resolve(recs, refresh_locations, log)
    zoi = {}
    if zoi_csv:
        by_layer = defaultdict(list)
        for r in recs: by_layer[r['source']['layer'].replace('waterbodies_atecf_', '')].append(r)
        for z in read_layer_list(zoi_csv):
            k = z['layer'].replace('waterbodies_zoi_atecf_', '')
            try:
                got = zoi_for(by_layer.get(k, []), _fetch(z['wfs_geojson_url'])); zoi.update(got)
                log(f'  {z["layer"]}: {len(got)} of {len(by_layer.get(k, []))} records matched to a zone of influence')
            except Exception as e:
                log(f'  {z["layer"]}: FAILED {str(e)[:160]}')
    doc = {'registry': {'id': reg_id, 'name': name or reg_id, 'source': f'GeoServer layers listed in {Path(layers_csv).name}',
                        'version': str(datetime.date.today()), 'intervention_types': [itype],
                        'year_convention': S['year_convention'], 'layers': [r['layer'] for r in rows], 'failed_layers': failed},
           'interventions': recs}
    REG_DIR.mkdir(parents=True, exist_ok=True)
    out = REG_DIR / f'{reg_id}.json'; save(doc, out)
    if zoi:
        with gzip.open(REG_DIR / f'{reg_id}.zoi.json.gz', 'wt', encoding='utf-8') as f: json.dump(zoi, f, separators=(',', ':'))
    log(f'wrote {out} ({len(recs)} interventions)' + (f' and {reg_id}.zoi.json.gz ({len(zoi)} zones)' if zoi else ''))
    if add_locations: add_to_locations(recs, role, scope, log)
    return doc

def save(doc, path):
    Path(path).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')

def add_to_locations(recs, role='coverage', scope='tehsil', log=print):
    """Add the resolved tehsils (or whole districts) to config/waterbody/locations.json (role coverage, so the atlas
    pools are unaffected) and to config/impact/locations.json (role `role`)."""
    from ..groundtruth import active_locations
    want = defaultdict(set)
    for r in recs:
        L = r.get('location') or {}
        if L.get('tehsil'): want[(L['state'], L['district'])].add(L['tehsil'])
    if scope == 'district':
        locs = {(s['label'], d['label']): [b['label'] for b in d.get('blocks', d.get('block', []))] for s in active_locations() for d in s['district']}
        for k in list(want): want[k] |= set(locs.get(k, []))
    for path, rl in ((ROOT / 'config' / 'waterbody' / 'locations.json', 'coverage'), (IMPACT_CFG / 'locations.json', role)):
        cfg = load_json(path) if path.exists() else {'districts': []}
        added = 0
        for (s, d), ts in sorted(want.items()):
            e = next((x for x in cfg['districts'] if x['state'] == s and x['district'] == d), None)
            if e is None:
                e = {'state': s, 'district': d, 'tehsils': [], 'roles': [rl]}; cfg['districts'].append(e)
            new = [t for t in sorted(ts) if t not in e['tehsils']]; e['tehsils'] += new; added += len(new)
            if rl not in (e.get('roles') or []) and not (rl == 'coverage' and e.get('roles')):
                e['roles'] = (e.get('roles') or []) + [rl]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, indent=1, ensure_ascii=False) + '\n')
        log(f'  {path.relative_to(ROOT)}: {added} tehsils added')

# ---------------------------------------------------------------- loading and linking
def load_all(paths=None):
    paths = paths or sorted(p for p in REG_DIR.glob('*.json'))
    return [load_json(p) for p in paths if not p.name.endswith('.zoi.json')]

def _fragments(state, district, tehsils):
    from shapely.geometry import shape
    out = []
    for t in tehsils:
        p = raw_dir(state, district, t) / 'swb_layers.json.gz'
        if not p.exists(): continue
        with gzip.open(p, 'rt', encoding='utf-8') as f: doc = json.load(f)
        for w in doc['waterbodies']:
            if w.get('geom'):
                try: out.append((str(w.get('UID', w.get('wb_id'))), t, shape(w['geom'])))
                except Exception: pass
    return out

def link(doc, cfg=None, bodies=None, log=print):
    """Fill record['waterbody'] for records in cached tehsils. bodies: seft.wb.build records of those districts
    (to map a fragment to its merged atlas waterbody, its type and whether it passed the size floor)."""
    from shapely.geometry import Point
    from shapely.strtree import STRtree
    from ..wb.build import build_tehsil
    from ..util import knowledge_dir
    S = settings(); Q = S['registry_quality']
    types = load_json(knowledge_dir() / 'waterbody' / 'types.json'); scope = {t['id'] for t in types['types'] if t['in_scope']}
    cfg = cfg or load_json(ROOT / 'config' / 'waterbody' / 'locations.json')
    by = defaultdict(list)
    for r in doc['interventions']:
        L = r.get('location') or {}
        if L.get('district'): by[(L['state'], L['district'])].append(r)
    stats = defaultdict(int)
    for (s, d), rs in by.items():
        ent = next((x for x in cfg['districts'] if x['state'] == s and x['district'] == d), None)
        tehs = [t for t in (ent or {}).get('tehsils', []) if (raw_dir(s, d, t) / 'swb_layers.json.gz').exists()]
        if not tehs:
            stats['district not cached'] += len(rs); continue
        frags = _fragments(s, d, tehs)
        if not frags: continue
        tree = STRtree([g for _, _, g in frags])
        fmap = {}
        Bs = [b for b in (bodies or []) if b.get('district') == d] or [b for t in tehs for b in build_tehsil(s, d, t, types, log=lambda *a: None)[0]]
        for b in Bs:
            for fid in b.get('fragment_ids') or []: fmap.setdefault(str(fid), b)
        for r in rs:
            for k in ('match_far', 'type_out_of_scope', 'below_min_area', 'unlinked'):
                if k in r['quality_flags']: r['quality_flags'].remove(k)
            pts = [p for p in (r['point'], r['desilting_point']) if p]
            hit = None
            for pt in pts:
                P = Point(*pt); idx = [i for i in tree.query(P) if frags[i][2].contains(P)]
                if idx: hit = (idx[0], 0.0, 'point_in_polygon'); break
            if not hit and pts:
                P = Point(*pts[0]); i = int(tree.nearest(P)); dm = frags[i][2].distance(P) * 111000
                if dm <= Q['link_max_m']: hit = (i, dm, 'nearest')
            if not hit:
                r['waterbody'] = None; r['quality_flags'].append('unlinked'); stats['unlinked'] += 1; continue
            fid, teh, _ = frags[hit[0]]; b = fmap.get(fid)
            r['waterbody'] = {'wb_id': b['wb_id'] if b else None, 'fragment_id': fid, 'state': s, 'district': d, 'tehsil': b['tehsil'] if b else teh,
                              'type': b.get('type') if b else None, 'area_ha': b.get('area_ha') if b else None,
                              'match': {'method': hit[2], 'distance_m': round(hit[1], 1)}}
            if hit[1] > Q['match_far_m']: r['quality_flags'].append('match_far')
            if not b: r['quality_flags'].append('below_min_area'); stats['below min area'] += 1; continue
            if b.get('type') not in scope: r['quality_flags'].append('type_out_of_scope')
            if r['volume_m3'] and b.get('area_ha') and r['volume_m3'] / (b['area_ha'] * 1e4) > Q['max_depth_m'] and 'volume_implausible' not in r['quality_flags']:
                r['quality_flags'].append('volume_implausible')
            stats['linked'] += 1
    nolo = sum(1 for r in doc['interventions'] if not (r.get('location') or {}).get('district'))
    if nolo: stats['location unresolved'] = nolo
    log('  linking: ' + ', '.join(f'{k} {v}' for k, v in stats.items()))
    return stats
