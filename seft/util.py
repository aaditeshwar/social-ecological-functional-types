import json, re, os
from contextvars import ContextVar
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_data_root: ContextVar = ContextVar('seft_data_root', default=None)
_knowledge_root: ContextVar = ContextVar('seft_knowledge_root', default=None)

def data_root():
    p = _data_root.get()
    return Path(p) if p is not None else ROOT / 'data'

def knowledge_dir():
    p = _knowledge_root.get()
    return Path(p) if p is not None else ROOT / 'knowledge'

def geom_path():
    return data_root() / 'geo' / 'geometry_raw.json'

def set_data_root(p):
    """Point the raw cache and geometry at a folder (library use). None restores the repo default."""
    return _data_root.set(None if p is None else Path(p))

def set_knowledge_dir(p):
    return _knowledge_root.set(None if p is None else Path(p))

def slug(s):
    """Lowercase, non-alphanumerics to underscore. Used for cache paths."""
    return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')

def gs_slug(s):
    """Slug used in CoRE Stack GeoServer layer names: lowercase, spaces to underscores, hyphens kept."""
    return re.sub(r'[^a-z0-9\-]+', '_', s.lower()).strip('_')

def load_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)

def dump_json(o, p, compact=True):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w') as f:
        json.dump(o, f, separators=(',', ':') if compact else None, indent=None if compact else 1, ensure_ascii=False)

def raw_dir(state, district, tehsil):
    return data_root() / 'raw' / slug(state) / slug(district) / slug(tehsil)

def atlas_mws_pools():
    """Published MWS percentile thresholds (knowledge pack, else the atlas index)."""
    p = knowledge_dir() / 'pools.json'
    if p.exists():
        d = load_json(p)
        return d.get('mws', d)
    ip = ROOT / 'web' / 'data' / 'index.json'
    return load_json(ip).get('pools') if ip.exists() else None

def atlas_wb_pools():
    p = knowledge_dir() / 'pools.json'
    if p.exists():
        d = load_json(p)
        if d.get('waterbody'):
            return d['waterbody']
    ip = ROOT / 'web' / 'data' / 'waterbody' / 'index.json'
    return load_json(ip).get('pools') if ip.exists() else None

ROLES = ('pools', 'groundtruth', 'coverage')

def district_roles(d):
    """Roles of a locations entry. Entries without 'roles' (older files) count as 'pools'."""
    return list(d.get('roles') or ['pools'])

def with_role(cfg, role):
    """The locations entries that carry this role, as a locations document."""
    return {'districts': [d for d in cfg['districts'] if role in district_roles(d)]}

def pools_doc():
    p = knowledge_dir() / 'pools.json'
    return load_json(p) if p.exists() else {}

def write_pools(part, pools, provenance):
    """Replace one part ('mws' or 'waterbody') of knowledge/pools.json, with where it came from."""
    p = knowledge_dir() / 'pools.json'
    d = load_json(p) if p.exists() else {}
    d[part] = pools
    d.setdefault('provenance', {})[part] = provenance
    p.write_text(json.dumps(d, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
    return p

def iter_locations(cfg=None):
    cfg = cfg or load_json(ROOT / 'config' / 'locations.json')
    for d in cfg['districts']:
        for t in d['tehsils']:
            yield d['state'], d['district'], t
