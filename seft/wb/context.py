"""Landscape context for waterbodies, taken from the watershed atlas.

Each waterbody gets the context of its home MWS from the watershed atlas table (out/csv/mws_all.csv, written by
`python -m seft.cli run`): the context dimensions (rainfall, aquifer, terrain, groundwater category, canal,
cropping), the archetype shares and a few variables used by the waterbody rules. Villages are reached the same
way, through the MWS (villages intersecting the home MWS, from out/csv/villages_all.csv).
"""
import csv
from ..util import ROOT

CTX_COLS = ['ctx_rainfall', 'ctx_aquifer', 'ctx_terrain', 'ctx_gw_category', 'ctx_canal', 'ctx_cropping']
SHARE_COLS = ['share_rainfed_dryland', 'share_rainfed_rice_subhumid', 'share_groundwater_irrigated',
              'share_canal_irrigated', 'share_tank_irrigated', 'share_forest_fringe', 'share_tree_crops',
              'share_pastoral', 'share_peri_urban']
VAR_COLS = ['area_ha', 'rain_norm', 'aquifer_class', 'soge_stage', 'f_crop', 'f_commons', 'ci_mean', 'double_share',
            'irr_share', 'tlu_per_ha', 'pop_density', 'piped_water_coverage', 'dr_years_modsev4', 'dry_spell_years3',
            'runoff_ratio', 'f_sloping', 'river_present', 'n_upstream']

def _num(v):
    try: return float(v)
    except (TypeError, ValueError): return v if v not in ('', None) else None

def load_mws(path=None):
    path = path or ROOT / 'out' / 'csv' / 'mws_all.csv'
    with open(path, newline='', encoding='utf-8') as f:
        return {r['uid']: r for r in csv.DictReader(f)}

def load_mws_villages(path=None):
    path = path or ROOT / 'out' / 'csv' / 'villages_all.csv'
    out = {}
    with open(path, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            out.setdefault(r['mws_uid'], []).append(r)
    return out

def attach(bodies, mws=None, vill=None):
    mws = mws if mws is not None else load_mws()
    vill = vill if vill is not None else load_mws_villages()
    for b in bodies:
        m = mws.get(b.get('home_mws'))
        b['mws_in_atlas'] = m is not None
        ctx = {}
        if m:
            for c in CTX_COLS: ctx[c] = m.get(c) or None
            for c in SHARE_COLS + VAR_COLS: ctx['mws_' + c if c in VAR_COLS else c] = _num(m.get(c))
            shares = {c: ctx[c] or 0 for c in SHARE_COLS}
            ctx['main_system'] = max(shares, key=shares.get).replace('share_', '') if any(shares.values()) else None
        b['mws'] = ctx
        b['mws_villages'] = [v['village_id'] for v in vill.get(b.get('home_mws'), [])]
    return bodies
