"""Download the GeoServer waterbody layers for each tehsil and keep a compact copy.

For every tehsil in a locations file this reads two WFS layers from CORE_STACK_GEOSERVER:
  swb:surface_waterbodies_{district}_{tehsil}   waterbody polygons, attributes, yearly k / kr / krz / area
  swb:waterbodies_zoi_{district}_{tehsil}       zone-of-influence circles with yearly cropping in the zone
and writes data/raw/<state>/<district>/<tehsil>/swb_layers.json.gz:
  {"fetched": ..., "waterbodies": [...], "zoi": [...], "zoi_has_wb_id": bool}
Waterbodies keep their attributes (census fields only where filled), yearly series as lists, a centroid,
a bounding box and the polygon (simplified to about 5 m, coordinates rounded to 6 decimals).
Zones of influence keep their attributes, yearly cropping as lists, the centre and bounding box; the
circle itself is not kept, since it is fully described by the centre and the radius `zoi` (metres).

GeoServer runs on port 8443. Run this where that port is reachable (it is not from Claude's workspace).
"""
import datetime, gzip, json, re, zipfile
from pathlib import Path
from ..util import ROOT, load_json, raw_dir, gs_slug, iter_locations
from ..fetch import wfs

LAYERS_FILE = 'swb_layers.json.gz'
WB_YEAR = re.compile(r'^(area|k|kr|krz)_(\d\d)-(\d\d)$')          # area_17-18, k_17-18, ...
ZOI_YEAR = re.compile(r'^(.+?(?<!_(?:19|20)\d\d))_((?:19|20)\d\d)$')  # cropping_intensity_2017, not ..._2017_2024

def _rings(g):
    t = g.get('type')
    if t == 'Polygon': return g['coordinates']
    if t == 'MultiPolygon': return [r for p in g['coordinates'] for r in p]
    return []

def _bbox(g):
    xs = [x for r in _rings(g) for x, _ in r]; ys = [y for r in _rings(g) for _, y in r]
    return [round(min(xs), 6), round(min(ys), 6), round(max(xs), 6), round(max(ys), 6)] if xs else None

def _round(o, nd=6):
    if isinstance(o, float): return round(o, nd)
    if isinstance(o, list): return [_round(x, nd) for x in o]
    return o

def _compact_geom(g, tol=0.00005):
    try:
        from shapely.geometry import shape, mapping
        s = shape(g).buffer(0)
        c = s.representative_point()
        s2 = s.simplify(tol, preserve_topology=True)
        if s2.is_empty: s2 = s
        return _round(mapping(s2)['coordinates']), mapping(s2)['type'], [round(c.x, 6), round(c.y, 6)]
    except Exception:                                   # shapely missing or a broken polygon: keep as is
        b = _bbox(g)
        return _round(g.get('coordinates')), g.get('type'), [round((b[0] + b[2]) / 2, 6), round((b[1] + b[3]) / 2, 6)] if b else None

def _series(props, pat, years_from):
    """Split yearly columns into {name: [values in year order]} and return (other props, series, years)."""
    other, ser = {}, {}
    for k, v in props.items():
        m = pat.match(k)
        if m:
            name, yr = m.group(1), years_from(m)
            ser.setdefault(name, {})[yr] = v
        else:
            other[k] = v
    years = sorted({y for s in ser.values() for y in s})
    return other, {n: [s.get(y) for y in years] for n, s in ser.items()}, years

def compact_waterbodies(fc):
    out = []
    for f in fc.get('features', []):
        other, ser, years = _series(f['properties'], WB_YEAR, lambda m: '20' + m.group(2))
        other = {k: v for k, v in other.items() if v not in ('NA', None, '')}
        coords, gtype, centre = _compact_geom(f['geometry']) if f.get('geometry') else (None, None, None)
        out.append({**other, 'years': years, **ser, 'centroid': centre, 'bbox': _bbox(f['geometry']) if f.get('geometry') else None,
                    'geom': {'type': gtype, 'coordinates': coords} if coords else None})
    return out

def compact_zoi(fc):
    out = []
    for f in fc.get('features', []):
        other, ser, years = _series(f['properties'], ZOI_YEAR, lambda m: m.group(2))
        b = _bbox(f['geometry']) if f.get('geometry') else None
        out.append({**other, 'years': years, **ser, 'bbox': b,
                    'centre': [round((b[0] + b[2]) / 2, 6), round((b[1] + b[3]) / 2, 6)] if b else None})
    return out

def fetch_tehsil_layers(state, district, tehsil, force=False, log=print):
    p = raw_dir(state, district, tehsil) / LAYERS_FILE
    if p.exists() and not force:
        log(f'  {district} / {tehsil}: cached'); return p
    ds, ts = gs_slug(district), gs_slug(tehsil)
    wb = wfs(f'swb:surface_waterbodies_{ds}_{ts}')
    zo = wfs(f'swb:waterbodies_zoi_{ds}_{ts}')
    W, Z = compact_waterbodies(wb), compact_zoi(zo)
    doc = {'fetched': datetime.datetime.now().isoformat(timespec='seconds'),
           'layers': [f'swb:surface_waterbodies_{ds}_{ts}', f'swb:waterbodies_zoi_{ds}_{ts}'],
           'zoi_has_wb_id': bool(Z) and all('wb_id' in z for z in Z),
           'waterbodies': W, 'zoi': Z}
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, 'wt', encoding='utf-8') as f:
        json.dump(doc, f, separators=(',', ':'))
    log(f'  {district} / {tehsil}: {len(W)} waterbodies, {len(Z)} zones of influence'
        f'{"" if doc["zoi_has_wb_id"] else " (zones carry no wb_id)"}, {p.stat().st_size // 1024} KB')
    return p

def fetch_all_layers(cfg, force=False, bundle=None, log=print):
    done, failed = [], []
    for state, district, tehsil in iter_locations(cfg):
        try:
            done.append(fetch_tehsil_layers(state, district, tehsil, force=force, log=log))
        except Exception as e:                          # keep going; report at the end
            failed.append((district, tehsil, str(e)[:200])); log(f'  {district} / {tehsil}: FAILED {str(e)[:200]}')
    if bundle:
        bundle = Path(bundle)
        with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_STORED) as z:   # files are already gzipped
            for p in done:
                z.write(p, p.relative_to(ROOT).as_posix())
        log(f'bundle: {bundle} ({bundle.stat().st_size // (1024 * 1024)} MB, {len(done)} tehsils)')
    log(f'{len(done)} tehsils written, {len(failed)} failed')
    return done, failed
