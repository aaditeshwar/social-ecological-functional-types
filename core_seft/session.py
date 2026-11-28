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
KINDS = ('district', 'tehsil', 'mws', 'waterbody', 'waterbody-impact')
LAYERS_FILE = 'swb_layers.json.gz'


def configure(data_dir=None, api_key=None, knowledge_dir=None, log=print):
    global _DEFAULT
    _DEFAULT = Session(data_dir=data_dir, api_key=api_key, knowledge_dir=knowledge_dir, log=log)
    return _DEFAULT


def predict_impact(intervention, **kw):
    if _DEFAULT is None:
        configure()
    return _DEFAULT.predict_impact(intervention, **kw)


def site_suitability(values=None, **kw):
    if _DEFAULT is None:
        configure()
    return _DEFAULT.site_suitability(values, **kw)


def analyse(kind, *, state, district, tehsil=None, uid=None, answers=None, fetch=True, include=None, detail='summary',
            intervention=None):
    if _DEFAULT is None:
        configure()
    return _DEFAULT.analyse(kind, state=state, district=district, tehsil=tehsil, uid=uid, intervention=intervention,
                            answers=answers, fetch=fetch, include=include, detail=detail)


class Session:
    """Analyse CoRE Stack entities against a local cache and a knowledge pack."""

    def __init__(self, data_dir=None, api_key=None, knowledge_dir=None, log=print):
        default = os.environ.get('CORE_SEFT_DATA') or str(Path.home() / 'core-seft-data')
        self.data_dir = Path(data_dir or default).expanduser()
        self.api_key = api_key or os.environ.get('CORE_STACK_API_KEY')
        self._knowledge_override = Path(knowledge_dir).expanduser() if knowledge_dir else None
        self.log = log if log is not None else (lambda *a, **k: None)
        self._mws = {}          # (state, district, tehsils_tuple) -> (records, villages, clusters, meta)
        self._wb = {}           # (state, district, tehsils_tuple) -> bodies
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

    def _cached_tehsils(self, state, district):
        """Official tehsil labels that already have lulc_vector.json under data_dir."""
        from seft.util import slug
        d = Path(self.data_dir) / 'raw' / slug(state) / slug(district)
        if not d.is_dir():
            return []
        out = []
        for p in sorted(d.iterdir()):
            f = p / 'lulc_vector.json'
            if not f.exists():
                continue
            try:
                t = load_json(f).get('tehsil')
            except Exception:
                t = None
            out.append(t or p.name)
        return out

    def _tehsil_has_mws(self, state, district, tehsil, uid):
        p = raw_dir(state, district, tehsil) / 'lulc_vector.json'
        if not p.exists():
            return False
        want = str(uid)
        for r in load_json(p).get('rows') or []:
            u = r.get('uid') or r.get('UID') or (r.get('metadata') or {}).get('uid')
            if str(u) == want:
                return True
        return False

    def _tehsil_has_wb(self, state, district, tehsil, uid):
        p = raw_dir(state, district, tehsil) / LAYERS_FILE
        if not p.exists():
            return False
        import gzip, json
        want = str(uid)
        with gzip.open(p, 'rt', encoding='utf-8') as f:
            doc = json.load(f)
        for w in doc.get('waterbodies') or []:
            if want in (str(w.get('wb_id') or ''), str(w.get('UID') or '')):
                return True
        return False

    def _tehsils_for_query(self, kind, state, district, tehsil=None, uid=None, fetch=True):
        """Tehsils to load/fetch for this analyse call. Grain is tehsil except kind=district."""
        if kind == 'district':
            return self._tehsils(state, district)
        if kind == 'tehsil':
            known = self._tehsils(state, district)
            if tehsil not in known:
                raise UnknownEntity(f'tehsil {tehsil!r} is not in {state}/{district}')
            return [tehsil]
        if tehsil:
            return [tehsil]
        hits = []
        for t in self._cached_tehsils(state, district):
            if kind == 'mws' and self._tehsil_has_mws(state, district, t, uid):
                hits.append(t)
            elif kind == 'waterbody' and self._tehsil_has_wb(state, district, t, uid):
                hits.append(t)
        if hits:
            return sorted(hits)
        if not fetch:
            raise CacheMiss(
                f'no cached tehsil in {state}/{district} contains {kind} {uid}. '
                f'Pass fetch=True and tehsil=... to download that tehsil, or fetch_district().'
            )
        raise UnknownEntity(
            f'{kind} {uid} is not in the {state}/{district} cache. '
            f'Pass tehsil= so only that tehsil is downloaded.'
        )

    def fetch_tehsils(self, state, district, tehsils, include=None):
        """Download the named tehsils into data_dir. Waterbody layers when include='waterbody'."""
        self._activate()
        if not self.api_key:
            raise CacheMiss('Set CORE_STACK_API_KEY or pass api_key= to Session before fetching.')
        os.environ['CORE_STACK_API_KEY'] = self.api_key
        tehsils = list(tehsils)
        cfg = self._cfg(state, district, tehsils)
        miss = self._missing(cfg, layers=(include == 'waterbody'))
        if any(m[3] == 'lulc_vector' for m in miss):
            from seft.fetch import fetch_all
            fetch_all(cfg, log=self.log)
        if include == 'waterbody' and self._missing(cfg, layers=True):
            from seft.wb.layers import fetch_all_layers
            fetch_all_layers(cfg, api=False, log=self.log)
        self._write_index(state, district, tehsils)
        self._invalidate(state, district)
        return cfg

    def fetch_district(self, state, district, include=None):
        """Download every tehsil of this district into data_dir. Waterbody layers when include='waterbody'."""
        self._activate()
        return self.fetch_tehsils(state, district, self._tehsils(state, district), include=include)

    def _invalidate(self, state, district):
        self._mws = {k: v for k, v in self._mws.items() if k[:2] != (state, district)}
        self._wb = {k: v for k, v in self._wb.items() if k[:2] != (state, district)}

    def _write_index(self, state, district, tehsils):
        p = Path(self.data_dir) / 'index.json'
        doc = load_json(p) if p.exists() else {'districts': []}
        rest = [d for d in doc.get('districts', []) if not (d.get('state') == state and d.get('district') == district)]
        have = []
        for d in doc.get('districts', []):
            if d.get('state') == state and d.get('district') == district:
                have = list(d.get('tehsils') or [])
                break
        for t in tehsils:
            if t not in have:
                have.append(t)
        rest.append({'state': state, 'district': district, 'tehsils': have, 'roles': ['coverage'],
                     'note': 'cached on demand by core-seft; scored with the published pools'})
        from seft.util import dump_json
        dump_json({'districts': rest}, p, compact=False)

    def _ensure(self, state, district, tehsils, fetch=True, layers=False):
        self._activate()
        cfg = self._cfg(state, district, list(tehsils))
        miss = self._missing(cfg, layers=layers)
        if not miss:
            return cfg
        need_fetch = any(m[3] == 'lulc_vector' for m in miss) or (layers and any(m[3] == 'swb_layers' for m in miss))
        if need_fetch and not fetch:
            bits = ', '.join(f'{d}/{t} ({what})' for _, d, t, what in miss[:8])
            raise CacheMiss(
                f'tehsil cache incomplete for {state}/{district}: {bits}. '
                f'Pass fetch=True (the default) or call fetch_tehsils() / fetch_district().'
            )
        self.fetch_tehsils(state, district, tehsils, include='waterbody' if layers else None)
        still = [m for m in self._missing(cfg, layers=False) if m[3] == 'lulc_vector']
        if still:
            bits = ', '.join(f'{d}/{t}' for _, d, t, _ in still[:8])
            raise CacheMiss(f'lulc_vector still missing after fetch for {state}/{district}: {bits}')
        return cfg

    def _scope_key(self, state, district, tehsils):
        return (state, district, tuple(sorted(tehsils)))

    def _score_mws(self, state, district, tehsils, fetch=True):
        key = self._scope_key(state, district, tehsils)
        if key in self._mws:
            return self._mws[key]
        cfg = self._ensure(state, district, tehsils, fetch=fetch, layers=False)
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

    def _wb_section(self, state, district, tehsils, recs, fetch, include, tehsil=None):
        cfg = self._cfg(state, district, tehsils)
        have = not self._missing(cfg, layers=True)
        if not have and include != 'waterbody':
            return None
        bodies = self._score_wb(state, district, tehsils,
                                fetch=fetch if include == 'waterbody' else False)
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
            'note': self._wb_unit_note(bodies, K, state, district, tehsil=tehsil),
        }

    def _works(self, district):
        """Recorded intervention years by waterbody id (str), from the registries' linked records in this district."""
        from seft.util import slug
        out = {}
        for doc in self._registries():
            for r in doc.get('interventions') or []:
                w = r.get('waterbody') or {}
                if w.get('wb_id') is not None and r.get('year') and slug(w.get('district') or '') == slug(district):
                    out.setdefault(str(w['wb_id']), []).append(r['year'])
        return out

    def _wb_unit_note(self, bodies, K, state, district, tehsil=None, uid=None):
        from seft.intro_notes import render, rules, wb_unit_env
        if uid is not None:
            sel, label = [b for b in bodies if str(b.get('home_mws')) == str(uid)], 'this micro-watershed'
        elif tehsil:
            sel, label = [b for b in bodies if b.get('tehsil') == tehsil], f'{tehsil} tehsil'
        else:
            sel, label = bodies, f'{district} district'
        return render(rules('waterbody').get('unit'), wb_unit_env(sel, label, K, set(self._works(district)))) or None

    def _score_wb(self, state, district, tehsils, fetch=True):
        key = self._scope_key(state, district, tehsils)
        if key in self._wb:
            return self._wb[key]
        cfg = self._ensure(state, district, tehsils, fetch=fetch, layers=True)
        recs, _, _, _ = self._score_mws(state, district, tehsils, fetch=fetch)
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
            row['mws_tehsil'] = r.get('tehsil')
            ctx[r['uid']] = row
        prof, drought = build_profiles(cfg)
        attach(B, ctx, prof)
        from seft.wb.run import dedupe
        B = dedupe(B, log=lambda m: None)
        scope = {t['id'] for t in types['types'] if t['in_scope']}
        ref = year_reference(B, scope)
        from seft.impact.farmpond import note_fields, settings as fp_settings
        try: FS = fp_settings()
        except FileNotFoundError: FS = None          # a knowledge pack older than 0.3.x has no impact/farmponds.json
        for b in B:
            b['vars'] = compute(b, prof, drought, ref)
            if FS:
                dw = {int(y): (FS['drought']['min_weeks'] if v else 0) for y, v in (drought.get(b.get('home_mws')) or {}).items()}
                b['fp_note'] = note_fields(b.get('k'), b.get('kr'), b.get('krz'), b.get('type'), dw, FS)
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
                fetch=True, include=None, detail='summary', intervention=None):
        if kind not in KINDS:
            raise UnknownEntity(f'kind must be one of {KINDS}, not {kind!r}')
        if kind == 'waterbody-impact':
            if not state or not district:
                raise UnknownEntity('analyse requires state= and district=')
            self._activate()
            return self._impact(state, district, tehsil=tehsil, uid=uid, intervention=intervention, fetch=fetch)
        if not state or not district:
            raise UnknownEntity('analyse requires state= and district=')
        if kind == 'tehsil' and not tehsil:
            raise UnknownEntity('kind="tehsil" requires tehsil=')
        if kind in ('mws', 'waterbody') and not uid:
            raise UnknownEntity(f'kind="{kind}" requires uid=')
        self._activate()
        kn = self._knowledge()
        versions = self._versions()
        tehsils = self._tehsils_for_query(kind, state, district, tehsil=tehsil, uid=uid, fetch=fetch)
        if kind in ('district', 'tehsil', 'mws'):
            recs, vill, cl, meta = self._score_mws(state, district, tehsils, fetch=fetch)
        if kind == 'mws':
            r = self._find_mws(recs, uid, state, district)
            mix_before = diff = None
            if answers:
                r, mix_before, diff = self._apply_answers(r, answers, meta.get('pools') or atlas_mws_pools() or {})
            from .present import _villages
            vrows = _villages(r['uid'], vill, cl, district)
            r = dict(r)
            r['n_villages'] = r.get('n_villages') if r.get('n_villages') is not None else len(vrows)
            res = present_mws(r, kn['G'], kn['T'], kn['S'], kn['SC'], kn['Q'], kn['IV'], versions,
                              answers=answers, mix_before=mix_before, diff=diff, detail=detail,
                              A=kn['A'], C=kn['C'], CC=kn.get('CC'), villages=vrows)
            if include == 'waterbody':
                # the waterbodies whose home is this MWS, as in the waterbody atlas's MWS panel
                from seft.wb.score import load_knowledge
                bodies = self._score_wb(state, district, tehsils, fetch=fetch)
                mine = [b for b in bodies if str(b.get('home_mws')) == str(r['uid'])]
                res.waterbodies = {'n_waterbodies': len(mine),
                                   'note': self._wb_unit_note(bodies, load_knowledge(), state, district, uid=r['uid'])}
            return res
        if kind in ('district', 'tehsil'):
            wb = None
            try:
                wb = self._wb_section(state, district, tehsils, recs, fetch, include,
                                      tehsil=tehsil if kind == 'tehsil' else None)
            except CacheMiss:
                wb = None
            return rollup(recs, kn['G'], kn['T'], kn['SC'], kn['IV'], versions,
                          kind, state, district, tehsil=tehsil if kind == 'tehsil' else None,
                          waterbodies=wb, A=kn['A'], C=kn['C'])
        bodies = self._score_wb(state, district, tehsils, fetch=fetch)
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
        recs, _, _, _ = self._score_mws(state, district, tehsils, fetch=fetch)
        home = None
        if b.get('home_mws'):
            try:
                home = self._find_mws(recs, b['home_mws'], state, district)
            except UnknownEntity:
                home = None
        return present_waterbody(b, K, home, versions, answers=answers, detail=detail,
                                 A=kn['A'], C=kn['C'], CC=kn.get('CC'), works=self._works(district).get(str(b.get('wb_id'))))


    # ------------------------------------------------------------------ waterbody impact
    def predict_impact(self, intervention, *, state, district, type=None, waterbody=None, mws=None, lat=None, lon=None,
                       tehsil=None, area_ha=None, zoi_area_ha=None, catchment_ha=None, stream_order=None, lined=None,
                       volume_m3=None, fetch=True, k=10):
        """Predicted impact of a new pond or tank (intervention='new_pond') or of desilting (intervention='desilting').

        new_pond: where (waterbody= an existing one, or mws=, or lat= and lon=), type= (farm_pond, headwater_pond,
        small_onstream_pond, onstream_tank, village_pond; default farm_pond or the waterbody's type),
        area_ha=, and if known zoi_area_ha=, catchment_ha=, stream_order=, lined= (farm ponds: True, False or None).
        desilting: waterbody= and volume_m3=. Returns the predicted effect, the group of assessed structures it falls in
        with their range, the most similar assessed structures and the model's notes (see core_seft/predict.py)."""
        from .predict import Predictor
        return Predictor(self).predict(intervention, state=state, district=district, type=type, waterbody=waterbody, mws=mws,
                                       lat=lat, lon=lon, tehsil=tehsil, area_ha=area_ha, zoi_area_ha=zoi_area_ha,
                                       catchment_ha=catchment_ha, stream_order=stream_order, lined=lined, volume_m3=volume_m3,
                                       fetch=fetch, k=k)

    def site_suitability(self, values=None, *, structures=None, state=None, district=None, waterbody=None, mws=None,
                         lat=None, lon=None, tehsil=None, predict=True, area_ha=None, fetch=True):
        """Which structures suit a site, from the suitability rules in knowledge/interventions.json.

        values: {slope_pct, stream_order, catchment_ha, drainage_distance_m, land_use, soil_group}; with waterbody=
        its stream order and catchment fill the missing ones. With a location (state, district and waterbody=, mws=
        or lat=/lon=) and predict=True, structures the impact model covers (farm ponds, check dams, community and
        percolation ponds) also get predict_impact for that site."""
        from .predict import suitability, Predictor, STRUCTURE_TYPES
        from seft.util import load_json
        self._activate()
        values = dict(values or {})
        if waterbody is not None:
            b, _ = Predictor(self)._wb(state, district, waterbody, tehsil, fetch)
            values.setdefault('stream_order', b.get('stream_order')); values.setdefault('catchment_ha', b.get('catchment_ha'))
        I = load_json(self.knowledge_dir / 'interventions.json')
        res = suitability(I, values, structures)
        if predict and state and district and (waterbody is not None or mws is not None or (lat is not None and lon is not None)):
            for r in res:
                t = STRUCTURE_TYPES.get(r['structure'])
                if not t or r['verdict'] == 'not suitable': continue
                try:
                    r['impact'] = self.predict_impact('new_pond', state=state, district=district, type=t, mws=mws,
                                                      waterbody=None, lat=lat, lon=lon, tehsil=tehsil, area_ha=area_ha,
                                                      catchment_ha=values.get('catchment_ha'), stream_order=values.get('stream_order'),
                                                      fetch=fetch, k=5) if (mws is not None or lat is not None) else \
                                  self.predict_impact('new_pond', state=state, district=district, type=t, waterbody=waterbody,
                                                      tehsil=tehsil, area_ha=area_ha, fetch=fetch, k=5)
                except Exception as e:
                    r['impact'] = {'error': str(e)}
        return res

    def _registries(self):
        """Registries from <data_dir>/registries and the repository's data/registries (same id: data_dir wins)."""
        out = {}
        for d in (ROOT / 'data' / 'registries', Path(self.data_dir) / 'registries'):
            if d.is_dir():
                for p in sorted(d.glob('*.json')):
                    doc = load_json(p); out[doc['registry']['id']] = doc
        return list(out.values())

    def _impact(self, state, district, tehsil=None, uid=None, intervention=None, fetch=True):
        """Impact of an intervention on a waterbody (uid), or averages over the registered works of a district or
        tehsil. Controls come from every cached tehsil of the district (plus the waterbody's own tehsil)."""
        import collections
        from seft.impact import registry as REG
        from seft.impact.pool import Pool, pool_years, mws_years
        from seft.impact.estimate import Estimator
        from seft.impact.run import assess_waterbody, note_env, type_labels, unit_stats, treated_map, pick_group, usable
        from seft.impact.pool import CTX_KEYS
        from seft.impact.notes import render, rules as note_rules
        S = REG.settings(); R = note_rules(); labels, scope = type_labels()
        tehs = set(self._cached_tehsils(state, district))
        if uid is not None:
            tehs |= set(self._tehsils_for_query('waterbody', state, district, uid=uid, fetch=fetch))
        elif tehsil:
            tehs |= {tehsil}
        tehs = sorted(t for t in tehs if (raw_dir(state, district, t) / LAYERS_FILE).exists()) or \
            sorted(self._tehsils_for_query('waterbody' if uid else 'tehsil', state, district, tehsil=tehsil, uid=uid, fetch=fetch))
        key = ('impact', self._scope_key(state, district, tehs))
        if key not in self._wb:
            B = self._score_wb(state, district, tehs, fetch=fetch)
            ms = {}
            for t in tehs: ms.update(mws_years(state, district, t))
            pool = Pool(B, pool_years(B), scope, None, ms)
            regs = self._registries()
            self._wb[key] = (pool, regs, Estimator(pool, S, treated_map(regs, pool)))
        pool, regs, E = self._wb[key]
        reg = collections.defaultdict(list)
        for doc in regs:
            for r in doc['interventions']:
                w = r.get('waterbody') or {}
                if w.get('wb_id') is not None and r.get('year') and str(w['wb_id']) in pool.index:
                    reg[str(w['wb_id'])].append({'year': r['year'], 'volume_m3': r.get('volume_m3'), 'ids': [r['id']],
                                                 'quality_flags': r.get('quality_flags') or []})
        screened = any(any((r.get('location') or {}).get('district') == district for r in d['interventions']) for d in regs)
        versions = self._versions()
        def wb_info(i):
            return {'wb_id': pool.key[i], 'state': pool.state[i], 'district': pool.district[i], 'tehsil': pool.tehsil[i],
                    'mws': pool.mws[i], 'type': pool.type[i], 'area': round(float(pool.area[i]), 2),
                    'xy': [round(float(c), 5) for c in pool.lonlat[i]]}
        def records_for(k, xs, scr):
            i = pool.index[k]; info = wb_info(i)
            ctx = {c: (pool.ctx[i] or {}).get(c) for c in CTX_KEYS}
            return [{**info, 'ctx': ctx, **rec} for rec in assess_waterbody(E, i, xs, S, labels, screened=scr)]
        gkey = ('impact-group', key)
        if gkey not in self._wb:            # every registered work of the district, for group means and unit averages
            self._wb[gkey] = [r for k, xs in sorted(reg.items()) for r in records_for(k, xs, True)]
        allrecs = self._wb[gkey]
        ok = [r for r in allrecs if usable(r)]
        if uid is None:
            sel = [r for r in ok if not tehsil or r['tehsil'] == tehsil]
            unit = f'{tehsil} tehsil' if tehsil else f'{district} district'
            return {'kind': 'waterbody-impact', 'unit': unit, 'state': state, 'district': district, 'tehsil': tehsil,
                    'average': unit_stats(sel, S, unit, R), 'records': [r for r in allrecs if not tehsil or r['tehsil'] == tehsil],
                    'registries': [d['registry']['id'] for d in regs], 'versions': versions}
        k = str(uid)
        if k not in pool.index:
            raise UnknownEntity(f'waterbody {uid} is not in {state}/{district}')
        source, xs, scr = None, None, screened
        if intervention:
            iv = dict(intervention)
            if not iv.get('year'): raise UnknownEntity('intervention needs a year (hydrological year, e.g. 2023 for 2023-24)')
            xs = [{'year': int(iv['year']), 'volume_m3': iv.get('volume_m3'), 'ids': ['supplied'], 'quality_flags': []}]
            source = 'supplied'
            if k in reg:
                same = sorted({x['year'] for x in reg[k]}) == [int(iv['year'])]
                source = 'supplied (matches the registry)' if same else 'supplied (the registry lists other works on this waterbody)'
        elif k in reg:
            xs, source = reg[k], 'registry'
        if not xs:
            return {'kind': 'waterbody-impact', 'waterbody': wb_info(pool.index[k]), 'records': [], 'source': None,
                    'message': 'No intervention is known for this waterbody. Pass intervention={"type": "desilting", "year": 2023, "volume_m3": ...}.',
                    'versions': versions}
        recs = records_for(k, xs, scr)
        cache = {}
        for r in recs:
            g = pick_group(r, ok, S, labels, cache)   # district and type; else rainfall regime and type (works cached here)
            r['note'] = render('waterbody', note_env(r, r, S, labels, g), R)
            r['group'] = g
        return {'kind': 'waterbody-impact', 'waterbody': wb_info(pool.index[k]), 'records': recs, 'source': source,
                'screened': scr, 'registries': [d['registry']['id'] for d in regs], 'versions': versions}
