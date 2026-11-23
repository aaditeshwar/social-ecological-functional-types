"""Session: cache root, fetch-on-miss, analyse for district / tehsil / mws / waterbody."""
import copy
import os
from pathlib import Path

from seft.util import (
    ROOT, set_data_root, set_knowledge_dir,
    raw_dir, load_json, iter_locations, atlas_mws_pools, atlas_wb_pools,
)
from seft.pipeline import run, score as score_mws
from seft.archetypes import mixture
from seft.assess import system_overrides
from seft.interventions import load_interventions

from . import __version__
from .errors import CacheMiss, UnknownEntity, KnowledgeError
from .knowledge import bundled_knowledge, pack_version, min_library, parse_ver, refresh as refresh_pack
from .present import present_mws, present_waterbody, rollup, mws_diff

_DEFAULT = None
KINDS = ('district', 'tehsil', 'mws', 'waterbody')
LAYERS_FILE = 'swb_layers.json.gz'


def configure(data_dir=None, api_key=None, knowledge_dir=None, log=print):
    global _DEFAULT
    _DEFAULT = Session(data_dir=data_dir, api_key=api_key, knowledge_dir=knowledge_dir, log=log)
    return _DEFAULT


def analyse(kind, *, state, district, tehsil=None, uid=None, answers=None, fetch=True, include=None, detail='summary'):
    if _DEFAULT is None:
        configure()
    return _DEFAULT.analyse(kind, state=state, district=district, tehsil=tehsil, uid=uid,
                            answers=answers, fetch=fetch, include=include, detail=detail)


class Session:
    """Analyse CoRE Stack entities against a local cache and a knowledge pack."""

    def __init__(self, data_dir=None, api_key=None, knowledge_dir=None, log=print):
        default = os.environ.get('CORE_SEFT_DATA') or str(Path.home() / 'core-seft-data')
        self.data_dir = Path(data_dir or default).expanduser()
        self.api_key = api_key or os.environ.get('CORE_STACK_API_KEY')
        self._knowledge_override = Path(knowledge_dir).expanduser() if knowledge_dir else None
        self.log = log if log is not None else (lambda *a, **k: None)
        self._mws = {}          # (state, district) -> (records, villages, clusters, meta)
        self._wb = {}           # (state, district) -> bodies
        self._kn = None         # loaded knowledge objects
        self._tokens = []

    @property
    def library_version(self):
        return __version__

    @property
    def knowledge_dir(self):
        if self._knowledge_override:
            return Path(self._knowledge_override)
        packed = Path(self.data_dir) / 'knowledge'
        if (packed / 'variables.json').exists():
            return packed
        return bundled_knowledge()

    @property
    def knowledge_version(self):
        return pack_version(self.knowledge_dir)

    def refresh_knowledge(self, version='latest'):
        dest = Path(self.data_dir) / 'knowledge'
        refresh_pack(dest, version=version, src=bundled_knowledge())
        self._knowledge_override = dest
        self._kn = None
        return dest

    def _activate(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        set_data_root(self.data_dir)
        set_knowledge_dir(self.knowledge_dir)
        need = min_library(self.knowledge_dir)
        if parse_ver(need) > parse_ver(self.library_version):
            raise KnowledgeError(
                f'knowledge pack {self.knowledge_version} needs core-seft>={need}; this library is {self.library_version}'
            )
        if self.api_key:
            os.environ['CORE_STACK_API_KEY'] = self.api_key
        import seft.pipeline as P
        P._IV = None

    def _versions(self):
        return {'library': self.library_version, 'knowledge': self.knowledge_version}

    def _knowledge(self):
        if self._kn is None:
            kd = self.knowledge_dir
            from seft.indicators import load_variables
            from seft.context import load_contexts
            from seft.archetypes import load_archetypes
            from seft.stresses import load_graph, load_taxonomy
            from seft.signals import load_signals
            from seft.schemes import load_schemes
            from seft.assess import load_questions
            from seft.util import load_json
            cc_path = kd / 'commons_connect.json'
            self._kn = {
                'V': load_variables(kd / 'variables.json'),
                'C': load_contexts(kd / 'contexts.json'),
                'A': load_archetypes(kd / 'archetypes.json'),
                'G': load_graph(kd / 'causal_graph.json'),
                'T': load_taxonomy(kd / 'taxonomy.json'),
                'S': load_signals(kd / 'signals.json'),
                'SC': load_schemes(kd / 'schemes.json'),
                'Q': load_questions(kd / 'questions.json'),
                'IV': load_interventions(kd / 'interventions.json'),
                'CC': load_json(cc_path) if cc_path.exists() else None,
            }
        return self._kn

    def _tehsils(self, state, district):
        for cfg_path in (ROOT / 'config' / 'locations.json', ROOT / 'config' / 'waterbody' / 'locations.json'):
            if cfg_path.exists():
                for d in load_json(cfg_path).get('districts', []):
                    if d.get('state') == state and d.get('district') == district:
                        return list(d['tehsils'])
        idx = Path(self.data_dir) / 'index.json'
        if idx.exists():
            for d in load_json(idx).get('districts', []):
                if d.get('state') == state and d.get('district') == district:
                    return list(d.get('tehsils') or [])
        from seft.groundtruth import active_locations
        locs = active_locations(False, log=self.log)
        for s in locs:
            if s.get('label') != state:
                continue
            for d in s.get('district') or []:
                if d.get('label') == district:
                    return [b['label'] for b in d.get('blocks') or []]
        raise UnknownEntity(
            f'{state} / {district} is not in get_active_locations. Names must match the CoRE Stack list exactly.'
        )

    def _cfg(self, state, district, tehsils=None):
        return {'districts': [{'state': state, 'district': district, 'tehsils': tehsils or self._tehsils(state, district)}]}

    def _missing(self, cfg, layers=False):
        out = []
        for s, d, t in iter_locations(cfg):
            if not (raw_dir(s, d, t) / 'lulc_vector.json').exists():
                out.append((s, d, t, 'lulc_vector'))
            elif layers and not (raw_dir(s, d, t) / LAYERS_FILE).exists():
                out.append((s, d, t, 'swb_layers'))
        return out

    def fetch_district(self, state, district, include=None):
        """Download every tehsil of this district into data_dir. Waterbody layers when include='waterbody'."""
        self._activate()
        if not self.api_key:
            raise CacheMiss('Set CORE_STACK_API_KEY or pass api_key= to Session before fetching.')
        os.environ['CORE_STACK_API_KEY'] = self.api_key
        cfg = self._cfg(state, district)
        from seft.fetch import fetch_all
        fetch_all(cfg, log=self.log)
        if include == 'waterbody':
            from seft.wb.layers import fetch_all_layers
            fetch_all_layers(cfg, api=False, log=self.log)
        self._write_index(state, district, cfg['districts'][0]['tehsils'])
        self._mws.pop((state, district), None)
        self._wb.pop((state, district), None)
        return cfg

    def _write_index(self, state, district, tehsils):
        p = Path(self.data_dir) / 'index.json'
        doc = load_json(p) if p.exists() else {'districts': []}
        rest = [d for d in doc.get('districts', []) if not (d.get('state') == state and d.get('district') == district)]
        rest.append({'state': state, 'district': district, 'tehsils': tehsils})
        from seft.util import dump_json
        dump_json({'districts': rest}, p, compact=False)

    def _ensure(self, state, district, fetch=True, layers=False):
        self._activate()
        cfg = self._cfg(state, district)
        miss = self._missing(cfg, layers=layers)
        if not miss:
            return cfg
        need_fetch = any(m[3] == 'lulc_vector' for m in miss) or (layers and any(m[3] == 'swb_layers' for m in miss))
        if need_fetch and not fetch:
            bits = ', '.join(f'{d}/{t} ({what})' for _, d, t, what in miss[:8])
            raise CacheMiss(
                f'district cache incomplete for {state}/{district}: {bits}. '
                f'Pass fetch=True (the default) or call fetch_district().'
            )
        if any(m[3] == 'lulc_vector' for m in miss):
            self.fetch_district(state, district, include='waterbody' if layers else None)
        elif layers:
            self.fetch_district(state, district, include='waterbody')
        still = [m for m in self._missing(cfg, layers=False) if m[3] == 'lulc_vector']
        if still:
            bits = ', '.join(f'{d}/{t}' for _, d, t, _ in still[:8])
            raise CacheMiss(f'lulc_vector still missing after fetch for {state}/{district}: {bits}')
        return cfg

    def _score_mws(self, state, district, fetch=True):
        key = (state, district)
        if key in self._mws:
            return self._mws[key]
        cfg = self._ensure(state, district, fetch=fetch, layers=False)
        pools = atlas_mws_pools()
        recs, vill, cl, meta = run(cfg, knowledge_dir=self.knowledge_dir, log=self.log, pools=pools)
        for r in recs:
            r['n_villages'] = len((cl.get(r['district']) or {}).get(r['uid'], []))
        self._mws[key] = (recs, vill, cl, meta)
        return self._mws[key]

    def _find_mws(self, recs, uid, state, district):
        want = str(uid)
        for r in recs:
            if str(r['uid']) == want:
                return r
        raise UnknownEntity(f'MWS {uid} is not in {state}/{district}')

    def _apply_answers(self, r, answers, pools):
        kn = self._knowledge()
        before = copy.deepcopy({'stress': r['stress'], 'schemes': r['schemes'],
                                'interventions': r.get('interventions'), 'mix': r['mix']})
        r = copy.copy(r)
        r['env'] = dict(r['env'])
        r['answers'] = dict(answers or {})
        sets, shifts = system_overrides(kn['Q'], r['answers'])
        mix0 = r.get('mix0') or r['mix']
        r['mix'] = mixture(r['env'], kn['A'], sets, shifts) if (sets or shifts) else mix0
        for k, v in r['mix']['shares'].items():
            r['env']['share_' + k] = v
        score_mws(r, kn['G'], kn['Q'], kn['S'], kn['T'], kn['SC'], pools)
        mix_before = before['mix'] if before['mix'] != r['mix'] else None
        return r, mix_before, mws_diff(before, r)

    def _wb_section(self, state, district, recs, fetch, include):
        cfg = self._cfg(state, district)
        have = not self._missing(cfg, layers=True)
        if not have and include != 'waterbody':
            return None
        bodies = self._score_wb(state, district, fetch=fetch if include == 'waterbody' else False)
        if not bodies:
            return None
        from collections import Counter
        from seft.wb.run import recent_ponds, rates
        from seft.wb.score import load_knowledge
        K = load_knowledge()
        scope = {t['id'] for t in K['types']['types'] if t['in_scope']}
        in_scope = [b for b in bodies if b.get('type') in scope]
        rp = recent_ponds(bodies, scope)
        return {
            'n_waterbodies': len(bodies),
            'by_type': dict(Counter(b.get('type') for b in bodies)),
            'by_status': dict(Counter(b.get('status') for b in in_scope)),
            'recent_ponds': sum(n for n, _ in rp.values()),
            'rules': rates(bodies, K, scope),
        }

    def _score_wb(self, state, district, fetch=True):
        key = (state, district)
        if key in self._wb:
            return self._wb[key]
        cfg = self._ensure(state, district, fetch=fetch, layers=True)
        recs, _, _, _ = self._score_mws(state, district, fetch=fetch)
        from seft.wb.build import build_all
        from seft.wb.context import attach
        from seft.wb.villages import build_profiles
        from seft.wb.indicators import compute, year_reference
        from seft.wb.score import load_knowledge, score, base_env
        from seft.wb.run import status as wb_status
        K = load_knowledge()
        B, stats, types = build_all(cfg, kdir=self.knowledge_dir / 'waterbody', log=self.log)
        ctx = {}
        for r in recs:
            row = {f'ctx_{k}': v for k, v in (r.get('ctx') or {}).items()}
            row.update({f'share_{k}': v for k, v in (r.get('mix') or {}).get('shares', {}).items()})
            row.update({f'mws_{k}': v for k, v in (r.get('ind') or {}).items()})
            row['mws_area_ha'] = r.get('area')
            row['dominant_system'] = (r.get('mix') or {}).get('dominant')
            ctx[r['uid']] = row
        prof, drought = build_profiles(cfg)
        attach(B, ctx, prof)
        scope = {t['id'] for t in types['types'] if t['in_scope']}
        ref = year_reference(B, scope)
        for b in B:
            b['vars'] = compute(b, prof, drought, ref)
        pools = atlas_wb_pools()
        if not pools:
            from seft.wb.score import pool_thresholds
            pools = pool_thresholds([base_env(b, b['vars']) for b in B if b['type'] in scope], K)
        for b in B:
            if b['type'] in scope:
                b['signals'], b['roles'], b['rules'] = score(b, b['vars'], K, pools)
            else:
                b['signals'], b['roles'], b['rules'] = {}, {}, {}
            b['status'] = wb_status(b)
        self._wb[key] = B
        return B

    def _find_wb(self, bodies, uid, state, district):
        want = str(uid)
        hits = [b for b in bodies if str(b.get('wb_id')) == want]
        if not hits:
            raise UnknownEntity(f'waterbody {uid} is not in {state}/{district}')
        hits.sort(key=lambda b: (0 if b.get('zoi_match') in ('wb_id', 'location') else 1, -(b.get('area_ha') or 0)))
        return hits[0]

    def analyse(self, kind, *, state, district, tehsil=None, uid=None, answers=None,
                fetch=True, include=None, detail='summary'):
        if kind not in KINDS:
            raise UnknownEntity(f'kind must be one of {KINDS}, not {kind!r}')
        if not state or not district:
            raise UnknownEntity('analyse requires state= and district=')
        if kind == 'tehsil' and not tehsil:
            raise UnknownEntity('kind="tehsil" requires tehsil=')
        if kind in ('mws', 'waterbody') and not uid:
            raise UnknownEntity(f'kind="{kind}" requires uid=')
        self._activate()
        kn = self._knowledge()
        versions = self._versions()
        if kind in ('district', 'tehsil', 'mws'):
            recs, vill, cl, meta = self._score_mws(state, district, fetch=fetch)
        if kind == 'mws':
            r = self._find_mws(recs, uid, state, district)
            mix_before = diff = None
            if answers:
                r, mix_before, diff = self._apply_answers(r, answers, meta.get('pools') or atlas_mws_pools() or {})
            from .present import _villages
            vrows = _villages(r['uid'], vill, cl, district)
            r = dict(r)
            r['n_villages'] = r.get('n_villages') if r.get('n_villages') is not None else len(vrows)
            return present_mws(r, kn['G'], kn['T'], kn['S'], kn['SC'], kn['Q'], kn['IV'], versions,
                               answers=answers, mix_before=mix_before, diff=diff, detail=detail,
                               A=kn['A'], C=kn['C'], CC=kn.get('CC'), villages=vrows)
        if kind in ('district', 'tehsil'):
            if kind == 'tehsil' and tehsil not in self._tehsils(state, district):
                raise UnknownEntity(f'tehsil {tehsil!r} is not in {state}/{district}')
            wb = None
            try:
                wb = self._wb_section(state, district, recs, fetch, include)
            except CacheMiss:
                wb = None
            return rollup(recs, kn['G'], kn['T'], kn['SC'], kn['IV'], versions,
                          kind, state, district, tehsil=tehsil if kind == 'tehsil' else None,
                          waterbodies=wb)
        bodies = self._score_wb(state, district, fetch=fetch)
        b = self._find_wb(bodies, uid, state, district)
        from seft.wb.assess import assess
        from seft.wb.score import load_knowledge
        K = load_knowledge()
        pools = atlas_wb_pools() or {}
        R = assess(b, answers or {}, K, pools, K['types'])
        b = dict(b)
        b['type'] = R['type']
        b['type_data'] = R['type_data']
        b['rules'] = R['rules']
        recs, _, _, _ = self._score_mws(state, district, fetch=fetch)
        home = None
        if b.get('home_mws'):
            try:
                home = self._find_mws(recs, b['home_mws'], state, district)
            except UnknownEntity:
                home = None
        return present_waterbody(b, K, home, versions, answers=answers, detail=detail,
                                 A=kn['A'], C=kn['C'], CC=kn.get('CC'))
