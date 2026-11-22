import json, re, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def slug(s):
    """Lowercase, non-alphanumerics to underscore. Used for cache paths."""
    return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')

def gs_slug(s):
    """Slug used in CoRE Stack GeoServer layer names: lowercase, spaces to underscores, hyphens kept."""
    return re.sub(r'[^a-z0-9\-]+', '_', s.lower()).strip('_')

def load_json(p):
    with open(p) as f:
        return json.load(f)

def dump_json(o, p, compact=True):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, 'w') as f:
        json.dump(o, f, separators=(',', ':') if compact else None, indent=None if compact else 1, ensure_ascii=False)

def raw_dir(state, district, tehsil):
    return ROOT / 'data' / 'raw' / slug(state) / slug(district) / slug(tehsil)

def iter_locations(cfg=None):
    cfg = cfg or load_json(ROOT / 'config' / 'locations.json')
    for d in cfg['districts']:
        for t in d['tehsils']:
            yield d['state'], d['district'], t
