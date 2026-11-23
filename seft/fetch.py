"""Fetch CoRE Stack data for new locations.

API:       GET {CORE_STACK_API_BASE}/api/{CORE_STACK_API_VERSION}/get_tehsil_data/?state=..&district=..&tehsil=..
           One request per tehsil, without the data= filter: the response holds every dataset, including
           forest_fire, forest_fringes, tree_in_grassland and ndvi, which v2's data= filter rejects although
           it serves them (CS-83). v2 is the default. v1 (CORE_STACK_API_VERSION=v1) also works; it returns the
           flat, unit-suffixed form of the API docs and Excel exports. seft/schema.py reads both forms.
           header X-API-Key: $CORE_STACK_API_KEY   (never hard-code the key)
GeoServer: WFS GetFeature on {CORE_STACK_GEOSERVER} for MWS polygons (crop_intensity:{d}_{t}_intensity)
           and village polygons (panchayat_boundaries:{d}_{t}).

For each tehsil:
1. Geometry is fetched first from GeoServer (MWS polygons, village points, tehsil outline) and stored in
   data/geo/geometry_raw.json. Its MWS count is the expected row count for MWS-level datasets.
2. The tehsil's full response (every dataset the API returns, with presigned links stripped) is kept,
   gzipped, as data/raw/<state>/<district>/<tehsil>/_response.json.gz. It is then split by dataset
   (config/datasets.json) and each dataset is cached on its own in data/raw/<...>/<dataset>.json. A dataset
   added to config/datasets.json later is extracted from the kept response, with no new API call; --force
   downloads the response again. A dataset missing from the response
   (the API leaves out empty ones, CS-52) is stored as empty.
3. A dataset is marked complete=false when the response was cut off, or when an MWS-level dataset that
   should cover every MWS returns fewer rows than the geometry has MWS (CS-59).
4. Incomplete lulc_vector and croppingintensity_annual are back-filled from the GeoServer layers that
   back the API (see backfill_from_geoserver). Anything still incomplete is listed by `seft.cli audit`.

Rerunning skips datasets already cached as complete unless --force.
"""
import datetime, gzip, json, os, re, time
from .util import ROOT, load_json, dump_json, raw_dir, gs_slug, geom_path
from .ingest import parse_response
from .geo import encode_geom

API_BASE = os.environ.get('CORE_STACK_API_BASE', 'https://geoserver.core-stack.org').rstrip('/')
API_VERSION = os.environ.get('CORE_STACK_API_VERSION', 'v2').strip('/')
GEOSERVER = os.environ.get('CORE_STACK_GEOSERVER', 'https://geoserver.core-stack.org:8443/geoserver').rstrip('/')
GEOM_PATH = ROOT / 'data' / 'geo' / 'geometry_raw.json'  # default; fetch_all uses geom_path() so a library data_dir applies

# MWS-level datasets that legitimately have fewer rows than there are MWS
SPARSE = {'surfacewaterbodies_annual', 'canal', 'green_credit', 'croppingdrought_kharif',
          'river', 'forest_fringes', 'forest_fire', 'tree_in_grassland', 'nrega_annual', 'ndvi', 'mining'}

def _requests():
    import requests
    return requests

def _key():
    k = os.environ.get('CORE_STACK_API_KEY')
    if not k:
        raise SystemExit('Set CORE_STACK_API_KEY in the environment (see README).')
    return k

def _get(url, params, headers=None, retries=4, timeout=300):
    rq = _requests()
    for i in range(retries):
        try:
            r = rq.get(url, params=params, headers=headers or {}, timeout=timeout)
        except rq.RequestException as e:
            if i == retries - 1: raise
            time.sleep(5 * (i + 1)); continue
        if r.status_code == 200:
            return r
        if r.status_code in (429, 500, 502, 503, 504) and i < retries - 1:
            time.sleep(5 * (i + 1)); continue
        raise RuntimeError(f'HTTP {r.status_code} for {url} {params}: {r.text[:300]}')

# names the v1 response uses for datasets named differently in config/datasets.json (v2 names)
V1_NAMES = {'change_detection_tree_cover_decrease': 'change_detection_deforestation',
            'change_detection_tree_cover_increase': 'change_detection_afforestation'}
_TEHSIL_CACHE = {}
_REFRESHED = set()
RESPONSE_FILE = '_response.json.gz'

def response_path(state, district, tehsil):
    return raw_dir(state, district, tehsil) / RESPONSE_FILE

def get_tehsil_all(state, district, tehsil, refresh=False):
    """Every dataset of one tehsil, keyed by lower-cased name. Read from the kept full response
    (data/raw/<...>/_response.json.gz) when it exists; otherwise, or with refresh, one API request without
    the data= filter, whose response is then kept (secrets stripped) for later extraction."""
    k = (API_VERSION, state, district, tehsil)
    if refresh and k not in _REFRESHED:
        _TEHSIL_CACHE.pop(k, None)
    if k not in _TEHSIL_CACHE:
        _TEHSIL_CACHE.clear()
        p = response_path(state, district, tehsil)
        if p.exists() and not (refresh and k not in _REFRESHED):
            with gzip.open(p, 'rt') as f: body = json.load(f)['tehsil_data']
        else:
            r = _get(f'{API_BASE}/api/{API_VERSION}/get_tehsil_data/',
                     {'state': state, 'district': district, 'tehsil': tehsil}, headers={'X-API-Key': _key()})
            body = r.json()
            if isinstance(body, dict) and isinstance(body.get('data'), dict) and 'tehsil_data' in body['data']:
                body = body['data']['tehsil_data']           # v2 envelope
            body = _strip_secrets(body)
            p.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(p, 'wt') as f:
                json.dump({'state': state, 'district': district, 'tehsil': tehsil, 'api_version': API_VERSION,
                           'fetched': datetime.date.today().isoformat(), 'tehsil_data': body}, f)
            _REFRESHED.add(k)
        _TEHSIL_CACHE[k] = {n.lower(): v for n, v in body.items()}
    return _TEHSIL_CACHE[k]

def get_tehsil(state, district, tehsil, datasets, refresh=False):
    """The named datasets of one tehsil, in the {'data': {'tehsil_data': ...}} shape parse_response reads."""
    allds = get_tehsil_all(state, district, tehsil, refresh=refresh)
    out = {}
    for n in datasets:
        rows = allds.get(n.lower())
        if rows is None and n in V1_NAMES: rows = allds.get(V1_NAMES[n])
        if rows is not None: out[n] = rows if isinstance(rows, list) else [rows]
    return {'data': {'tehsil_data': out}}

def _strip_secrets(obj):
    """green_credit rows carry presigned S3 URLs (CS-62); never store them."""
    if isinstance(obj, dict):
        return {k: _strip_secrets(v) for k, v in obj.items() if k != 'kml_url'}
    if isinstance(obj, list):
        return [_strip_secrets(v) for v in obj]
    return obj

def _row_uid(r):
    return (r.get('uid') or r.get('UID') or (r.get('metadata') or {}).get('uid') or r.get('mws_uid')
            or r.get('MWS_UID'))

def _write(state, district, tehsil, name, rows, units, complete, source='get_tehsil_data', **extra):
    o = {'dataset': name, 'state': state, 'district': district, 'tehsil': tehsil, 'complete': complete,
         'n_rows': len(rows), 'units': units, 'rows': rows, 'fetched': datetime.date.today().isoformat(),
         'source': source}
    o.update(extra)
    dump_json(o, raw_dir(state, district, tehsil) / f'{name}.json')

def fetch_tehsil(state, district, tehsil, datasets, n_mws=None, force=False, log=print):
    d = raw_dir(state, district, tehsil)
    status = {}
    for name in datasets:
        p = d / f'{name}.json'
        if not force and p.exists() and load_json(p).get('complete'):
            status[name] = 'cached'; continue
        try:
            obj = _strip_secrets(get_tehsil(state, district, tehsil, [name], refresh=force))
        except Exception as e:
            status[name] = f'FAILED ({e})'; log(f'    {name}: {e}'); continue
        rows, units, complete = parse_response(obj).get(name, ([], {}, True))
        expected = None
        if n_mws and name not in SPARSE and datasets[name].get('level') == 'mws':
            got = len({_row_uid(r) for r in rows})
            expected = n_mws
            if got < n_mws:
                complete = False
        _write(state, district, tehsil, name, rows, units, complete, expected_mws=expected)
        status[name] = f"{len(rows)} rows" + ('' if complete else ' (INCOMPLETE)')
    return status

# ---------------- GeoServer ----------------

def wfs(layer, props=None):
    p = {'service': 'WFS', 'version': '1.0.0', 'request': 'GetFeature', 'typeName': layer, 'outputFormat': 'application/json'}
    if props: p['propertyName'] = props
    return _get(f'{GEOSERVER}/wfs', p).json()

def fetch_geometry(district, tehsil, tol=0.0008):
    """MWS polygons, village points/attributes and a tehsil outline in the compact encoding (seft.geo).
    Also returns the raw crop_intensity features, reused by the back-fill."""
    from shapely.geometry import shape
    from shapely.ops import unary_union
    ds, ts = gs_slug(district), gs_slug(tehsil)
    mws = wfs(f'crop_intensity:{ds}_{ts}_intensity')
    vill = wfs(f'panchayat_boundaries:{ds}_{ts}')
    out = {'mws': {}, 'vill': []}
    vshapes = []
    for f in mws['features']:
        out['mws'][f['properties']['uid']] = encode_geom(shape(f['geometry']).buffer(0), tol)
    for f in vill['features']:
        g = shape(f['geometry']).buffer(0); vshapes.append(g.buffer(0.0005))
        c = g.representative_point(); P = f['properties']
        out['vill'].append([P.get('vill_ID'), P.get('vill_name'), round(c.x * 1e4), round(c.y * 1e4),
                            P.get('TOT_P'), P.get('P_SC'), P.get('P_ST')])
    out['teh'] = encode_geom(unary_union(vshapes), 0.001) if vshapes else ''
    return out, mws['features']

YEAR_COL = re.compile(r'^(?P<col>.+?)_(?P<y>(?:19|20)\d\d)(?:_(?:19|20)?\d\d)?$')

def _annualise(props, cols_wanted):
    """GeoServer stores annual values as <column>_<year> (or <column>_<year>_<year>) properties.
    Regroup them into the API's {'time': [...], column: [...]} shape."""
    series = {}
    for k, v in props.items():
        m = YEAR_COL.match(k)
        if m and m.group('col') in cols_wanted:
            series.setdefault(m.group('col'), {})[m.group('y')] = v
    years = sorted({y for s in series.values() for y in s})
    return {'time': years, **{c: [s.get(y) for y in years] for c, s in series.items()}}

LULC_COLS = {'barrenlands_area', 'built-up_area', 'built_up_area', 'cropland_area', 'doubly_cropped_area',
             'triply_cropped_area', 'tree_forest_area', 'shrub_scrub_area', 'single_kharif_cropped_area',
             'single_non_kharif_cropped_area', 'k_water_area', 'kr_water_area', 'krz_water_area'}
CI_COLS = {'cropping_intensity', 'doubly_cropped_area', 'single_cropped_area', 'single_kharif_cropped_area',
           'single_non_kharif_cropped_area', 'triply_cropped_area'}

def backfill_from_geoserver(state, district, tehsil, crop_features=None, log=print):
    """Replace incomplete lulc_vector / croppingintensity_annual with GeoServer values (identical to the
    API where both exist; CS-59). Accepted only when most of the expected columns and >= 6 years are found."""
    from shapely.geometry import shape
    d = raw_dir(state, district, tehsil)
    ds, ts = gs_slug(district), gs_slug(tehsil)
    jobs = [('lulc_vector', f'lulc_vector:lulc_vector_{ds}_{ts}', LULC_COLS, 8),
            ('croppingintensity_annual', None, CI_COLS, 4)]
    for name, layer, cols, min_cols in jobs:
        p = d / f'{name}.json'
        cur = load_json(p) if p.exists() else None
        if cur and cur.get('complete'):
            continue
        try:
            feats = crop_features if layer is None and crop_features is not None else \
                wfs(layer or f'crop_intensity:{ds}_{ts}_intensity')['features']
        except Exception as e:
            log(f'    back-fill {name}: GeoServer failed ({e})'); continue
        rows = []
        for f in feats:
            P = f['properties']; a = _annualise(P, cols)
            if len([c for c in a if c != 'time']) < min_cols or len(a['time']) < 6:
                continue
            if 'built_up_area' in a and 'built-up_area' not in a:
                a['built-up_area'] = a.pop('built_up_area')
            if name == 'croppingintensity_annual':
                meta = {'uid': P.get('uid'), 'sum_area': round(P['sum'] / 1e4, 2) if P.get('sum') else None}   # m2 -> ha
            else:
                meta = {'uid': P.get('uid')}
            try:   # area in ha from the polygon (equirectangular approximation); replaced by the API area below when known
                import math
                g = shape(f['geometry']); lat = g.centroid.y
                meta['area'] = round(g.area * (111.32 ** 2) * math.cos(math.radians(lat)) * 100, 2)
            except Exception:
                pass
            rows.append({'metadata': meta, 'annual': a})
        if not rows or (cur and len(rows) <= cur.get('n_rows', 0)):
            log(f'    back-fill {name}: GeoServer layer did not have the expected <column>_<year> fields; left as is')
            continue
        # keep the API's MWS area where the API returned the row
        api_area = {(r.get('metadata') or {}).get('uid'): (r.get('metadata') or {}).get('area') for r in (cur or {}).get('rows', [])}
        for r in rows:
            if api_area.get(r['metadata']['uid']) is not None:
                r['metadata']['area'] = api_area[r['metadata']['uid']]
        _write(state, district, tehsil, name, rows, (cur or {}).get('units', {}), True, source='geoserver_backfill',
               replaced=None if not cur else {'n_rows': cur['n_rows'], 'complete': cur.get('complete')})
        log(f'    back-fill {name}: {len(rows)} rows from GeoServer')

# ---------------- driver ----------------

def fetch_all(cfg, force=False, only=None, log=print):
    ds_cfg = load_json(ROOT / 'config' / 'datasets.json')['datasets']
    if only:
        ds_cfg = {k: v for k, v in ds_cfg.items() if k in only}
    gpath = geom_path()
    geo = load_json(gpath) if gpath.exists() else {}
    for dist in cfg['districts']:
        for t in dist['tehsils']:
            log(f"{dist['state']} / {dist['district']} / {t}")
            key = f"{gs_slug(dist['district'])}/{gs_slug(t)}"
            crop_feats = None
            if force or key not in geo:
                try:
                    geo[key], crop_feats = fetch_geometry(dist['district'], t)
                    dump_json(geo, gpath)
                    log(f"    geometry: {len(geo[key]['mws'])} MWS, {len(geo[key]['vill'])} villages")
                except Exception as e:
                    log(f'    geometry: GeoServer failed ({e}); MWS counts cannot be checked')
            n_mws = len(geo[key]['mws']) if key in geo else None
            st = fetch_tehsil(dist['state'], dist['district'], t, ds_cfg, n_mws=n_mws, force=force, log=log)
            bad = {k: v for k, v in st.items() if 'INCOMPLETE' in v or 'FAILED' in v}
            log(f"    datasets: {sum(1 for v in st.values() if v == 'cached')} cached, "
                f"{len(st) - len(bad) - sum(1 for v in st.values() if v == 'cached')} fetched, {len(bad)} with problems")
            if any(k in bad for k in ('lulc_vector', 'croppingintensity_annual')) and not os.environ.get('SEFT_NO_GEOSERVER'):
                backfill_from_geoserver(dist['state'], dist['district'], t, crop_feats, log=log)
    from .backfill import apply      # stored GeoServer rows for the test districts (hydrology, livestock, ...)
    for d, t, ds, n, prev in apply(cfg=cfg):
        log(f'    {d} / {t}: {ds} back-filled from data/geo/geoserver_backfill.json ({n} rows, API gave {prev})')
    log('Done. Run `python -m seft.cli audit` to list datasets that are still missing or incomplete.')
