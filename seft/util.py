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
    with open(p, 'w', encoding='utf-8') as f:
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
    """The locations entries that carry this role, as a locations document. For the 'pools' and 'groundtruth'
    roles, tehsils listed under 'coverage_tehsils' (added later because another module needed them) are left out,
    so the sample does not change; for 'coverage' those tehsils count too."""
    out = []
    for d in cfg['districts']:
        cov = set(d.get('coverage_tehsils') or [])
        if role in district_roles(d):
            out.append({**d, 'tehsils': [t for t in d['tehsils'] if role == 'coverage' or t not in cov]})
        elif role == 'coverage' and cov:
            out.append({**d, 'tehsils': [t for t in d['tehsils'] if t in cov]})
    return {'districts': out}

def role_tehsils(cfg, role):
    """{(state, district, tehsil)} carrying a role (see with_role)."""
    return {(d['state'], d['district'], t) for d in with_role(cfg, role)['districts'] for t in d['tehsils']}

# ------------------------------------------------------------------ locations of the modules
# Each module lists its locations in its own file. A module also uses the data of the modules it depends on
# (the waterbody atlas draws on the watershed atlas's MWS bundles and context; the impact module on the
# waterbody atlas), so registering a location in a module registers it, as coverage, in its dependencies.
MODULE_LOCATIONS = {'mws': ('config', 'locations.json'), 'waterbody': ('config', 'waterbody', 'locations.json'),
                    'impact': ('config', 'impact', 'locations.json')}
MODULE_DEPENDS = {'mws': [], 'waterbody': ['mws'], 'impact': ['waterbody', 'mws']}

def module_locations_path(module):
    return ROOT.joinpath(*MODULE_LOCATIONS[module])

def _role_order(roles):
    order = ('pools', 'groundtruth', 'reference', 'test', 'coverage')
    rs = set(roles)
    if rs - {'coverage'}: rs.discard('coverage')
    return [r for r in order if r in rs] + sorted(rs - set(order))

def register_locations(module, entries, role='coverage', log=print, cascade=True, dependency=False):
    """Add tehsils to a module's locations file and, as coverage, to the modules it depends on.

    entries: {(state, district): [tehsils]}. In the module itself the district gets `role`. In a dependency, a new
    district gets the role 'coverage'; tehsils added to an existing pools or ground-truth district are recorded
    under 'coverage_tehsils', so its sample is unchanged. dependency=True treats `module` itself that way (used when
    another module's locations are synced into it). Returns {module: number of tehsils added}."""
    added = {}
    for m in [module] + (MODULE_DEPENDS[module] if cascade else []):
        p = module_locations_path(m)
        cfg = load_json(p) if p.exists() else {'districts': []}
        n = 0
        for (s, dn), ts in sorted(entries.items()):
            e = next((x for x in cfg['districts'] if x['state'] == s and x['district'] == dn), None)
            new_district = e is None
            own = m == module and not dependency
            if new_district:
                e = {'state': s, 'district': dn, 'tehsils': [], 'roles': [role if own else 'coverage']}
                cfg['districts'].append(e)
            new = [t for t in ts if t not in e['tehsils']]
            e['tehsils'] += new; n += len(new)
            if own:
                e['roles'] = _role_order((e.get('roles') or []) + [role])
            elif new and not new_district and set(district_roles(e)) - {'coverage'}:
                e['coverage_tehsils'] = sorted(set(e.get('coverage_tehsils') or []) | set(new))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cfg, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
        added[m] = n
        log(f'  {p.relative_to(ROOT)}: {n} tehsil(s) added' + ('' if m == module and not dependency else ' (as coverage, for the modules that use it)'))
    return added

def sync_dependencies(module, log=print):
    """Register every location of a module in the modules it depends on (for files edited by hand or older runs)."""
    p = module_locations_path(module)
    if not p.exists(): return {}
    cfg = load_json(p)
    entries = {(d['state'], d['district']): list(d['tehsils']) for d in cfg['districts']}
    out = {}
    for dep in MODULE_DEPENDS[module]:
        out.update(register_locations(dep, entries, 'coverage', log=log, cascade=False, dependency=True))
    return out

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
