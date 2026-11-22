"""Per-MWS profiles that the waterbody rules need but the watershed tables do not carry.

From the cached API files of each tehsil (data/raw/...):
- villages intersecting each MWS (mws_intersect_villages), with intersect areas;
- Mission Antyodaya per village: fish community ponds, fish farming, the major irrigation source;
- kharif drought weeks per year (croppingdrought_kharif), to tell drought years from normal years.

Village shares are area-weighted over the villages intersecting the MWS that have Antyodaya data.
"""
import json
from ..util import raw_dir, iter_locations

def _rows(state, district, tehsil, name):
    p = raw_dir(state, district, tehsil) / name
    if not p.exists(): return []
    with open(p, encoding='utf-8') as f: return json.load(f).get('rows', [])

def _flag(v):
    try: return 1.0 if float(v) >= 0.5 else 0.0
    except (TypeError, ValueError): return None

def build_profiles(cfg, drought_weeks=4):
    anty, inter, drought = {}, {}, {}
    for s, d, t in iter_locations(cfg):
        for r in _rows(s, d, t, 'antyodaya.json'):
            vid = str(r.get('village_id'))
            if r.get('data_availability_status', 'matched') != 'matched' and r.get('availability_of_fish_community_ponds') is None: continue
            anty[vid] = {'fish_ponds': _flag(r.get('availability_of_fish_community_ponds')),
                         'fish_farming': _flag(r.get('availability_of_fish_farming')),
                         'irrigation_source': r.get('availability_of_major_source_of_irrigation')}
        for r in _rows(s, d, t, 'mws_intersect_villages.json'):
            det = r.get('village_details') or {}
            keys, vals = det.get('keys') or [], det.get('values') or []
            lst = inter.setdefault(r['mws_uid'], {})
            for k, v in zip(keys, vals): lst[str(k)] = max(lst.get(str(k), 0), (v or {}).get('area_intersect') or 0)
        for r in _rows(s, d, t, 'croppingdrought_kharif.json'):
            uid = (r.get('metadata') or {}).get('uid'); a = r.get('annual') or {}
            if not uid or not a.get('time'): continue
            mod, sev = a.get('moderate') or [], a.get('severe') or []
            drought[uid] = {y: ((m or 0) + (sv or 0)) >= drought_weeks for y, m, sv in zip(a['time'], mod, sev)}
    prof = {}
    for m, vs in inter.items():
        tot = sum(a for v, a in vs.items() if v in anty)
        if not tot: prof[m] = {'n_villages': len(vs), 'anty_area_ha': 0}; continue
        w = lambda f: sum(a * f(anty[v]) for v, a in vs.items() if v in anty) / tot
        prof[m] = {'n_villages': len(vs), 'anty_area_ha': round(tot, 1),
                   'fish_village_share': round(w(lambda x: max(x['fish_ponds'] or 0, x['fish_farming'] or 0)), 3),
                   'surface_irrigation_share': round(w(lambda x: 1.0 if x['irrigation_source'] in ('Surface water', 'Canal') else 0.0), 3),
                   'canal_irrigation_share': round(w(lambda x: 1.0 if x['irrigation_source'] == 'Canal' else 0.0), 3)}
    return prof, drought
