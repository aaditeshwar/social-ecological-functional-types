"""Map the documented get_tehsil_data schema (API metadata, Nov 2026) onto the internal column names.

The pipeline was built on responses of the form {'metadata': {...}, 'annual': {'time': [...], col: [...]}}
with plain column names (delta_g, total_area, uid). The published metadata describes flat rows with unit
and year suffixes instead: UID, area_in_ha, DeltaG_in_mm_2017-2018, Mild_in_weeks_2017, built-up_area_in_ha,
principle_aq_Granite_percent, 'MWS UID'. normalise_row() accepts either form and returns
(uid, scalars, series), so a refresh works whichever form the live API returns (CS-74).
"""
import re
import numpy as np
from .expr import NAN

YEARS = [str(y) for y in range(2017, 2025)]
# a year suffix: _2017 (calendar year) or _2017-2018 / _2017_2018 (agricultural year, keyed by its first year)
_YR = re.compile(r'^(.*?)_((?:19|20)\d\d)(?:[-_](?:19|20)?\d\d)?$')

# explicit renames after lower-casing (spaces and hyphens -> '_'); applied per dataset alias
RENAME = {
    '*': {'uid': 'uid', 'area_in_ha': 'area'},
    'hydro': {'deltag_in_mm': 'delta_g', 'et_in_mm': 'et', 'g_in_mm': 'g', 'precipitation_in_mm': 'precipitation',
              'runoff_in_mm': 'runoff', 'welldepth_in_m': 'welldepth'},
    'ci': {'cropping_intensity_unit_less': 'cropping_intensity'},
    'drought': {'mild_in_weeks': 'mild', 'moderate_in_weeks': 'moderate', 'severe_in_weeks': 'severe',
                'no_drought_in_weeks': 'no_drought', 'drysp_unit_4_weeks': 'dry_spell',
                'kharif_cropped_sqkm': 'kharif_cropped', 'kharif_cropped_area_percent': 'kharif_cropped_pct'},
    'soge': {'soge_dev_percent': 'soge_dev', 'soge_dev': 'soge_dev'},
    'tcd': {'total_deforestation_area': 'total_tree_cover_decrease_area'},
    'tci': {'total_afforestation_area': 'total_tree_cover_increase_area'},
}
# generic suffixes stripped for these aliases (after the explicit renames)
STRIP = {'lulc': '_in_ha', 'ci': '_in_ha', 'swb': '_in_ha', 'rest': '_in_ha', 'degr': '_in_ha', 'tcd': '_in_ha',
         'tci': '_in_ha', 'urb': '_in_ha', 'terrain': '_percent', 'nrega': '_count'}
# the live API (Nov 2026) drops some unit suffixes that the documented schema keeps; restore them so
# variables can use one name (CS-82)
LIVE_SUFFIX = {'soil': [(r'^(oc|oc_olm)_(mean|p\d\d)$', r'\1_\2_in_percent')],
               'fac': [(r'^(.*_distance)$', r'\1_in_km')],
               # forest_fringes: v2 'tree_tree_cover_decrease_fringe_area' = v1 'tree_deforestation_fringe_area_in_ha' (CS-83)
               'fringe': [(r'^tree_tree_cover_decrease_(fringe|mws)_area$', r'tree_deforestation_\1_area_in_ha'),
                          (r'^(forest_fringe_area|mws_area|tree_degradation_(?:fringe|mws)_area)$', r'\1_in_ha')],
               # tree_in_grassland: v2 drops '_in_ha' from every area column
               'tig': [(r'^(area|\w+_area)$', r'\1_in_ha')]}

def live_key(alias, k):
    for pat, rep in LIVE_SUFFIX.get(alias, []):
        if re.match(pat, k): return re.sub(pat, rep, k)
    return k
VILLAGE_RENAME = {'total_population_count': 'total_population', 'total_sc_population_count': 'total_sc_population',
                  'total_st_population_count': 'total_st_population', 'literacy_rate_percent': 'literacy_rate',
                  'mws_uid': 'mws_uid', 'village_details': 'village_details', 'village_ids': 'village_ids'}

def key(k):
    return re.sub(r'[\s\-]+', '_', str(k).strip()).lower()

def _rename(alias, k):
    k = key(k)
    k = RENAME['*'].get(k, k)
    k = RENAME.get(alias, {}).get(k, k)
    suf = STRIP.get(alias)
    if suf and k.endswith(suf):
        k = k[:-len(suf)]
        k = RENAME.get(alias, {}).get(k, k)
    return k

def _bad(v):
    return v in (None, '') or (isinstance(v, (int, float)) and v <= -9999)

def _latest_soge(cols, years):
    """SOGE now comes as assessments for several years (2011-2025), with -9999 for missing values: use the
    latest year whose stage of extraction is valid, and report which year it is."""
    dev = cols.get('soge_dev') or cols.get('soge_dev_percent') or []
    ok = [i for i, v in enumerate(dev) if not _bad(v)]
    if not ok: return {}
    i = ok[-1]
    out = {('soge_dev' if c == 'soge_dev_percent' else c): (None if _bad(v[i]) else v[i])
           for c, v in cols.items() if c != 'time' and i < len(v)}
    out['assessment_year'] = int(years[i])
    return out

def normalise_row(alias, r):
    """-> (uid, scalars, series) for one MWS row in either the legacy or the documented form."""
    if 'annual' in r:                                   # legacy form
        md = r.get('metadata', {})
        t = [str(x) for x in (r['annual'].get('time') or [])]
        if alias == 'soge':                             # yearly block assessments -> latest valid year (CS-86)
            return md.get('uid'), {**{k: v for k, v in md.items() if k != 'uid'}, **_latest_soge(r['annual'], t)}, {}
        series = {}
        for col, vals in r['annual'].items():
            if col == 'time': continue
            m = dict(zip(t, vals))
            v8 = [m.get(y) for y in YEARS]
            try:
                series[col.replace('-', '_')] = np.array([NAN if v in (None, '') else float(v) for v in v8])
            except (TypeError, ValueError):            # text per year (monsoon_onset, class names)
                series[col.replace('-', '_')] = v8
        return md.get('uid') or md.get('mws_id'), {k: v for k, v in md.items() if k not in ('uid', 'mws_id')}, series
    uid = r.get('uid') or r.get('UID') or r.get('MWS UID') or r.get('mws_uid') or r.get('mws_id')
    scal, yearly = {}, {}
    for k, v in r.items():
        if k in ('uid', 'UID', 'mws_id', 'aquifer_classes', 'aquifer_percentages'): continue
        kk = key(k)
        m = _YR.match(kk)
        if m and not kk.startswith('principle_aq'):
            yearly.setdefault(_rename(alias, m.group(1)), {})[m.group(2)] = v
            continue
        if kk.startswith('principle_aq_') and kk.endswith('_percent'):
            scal['pa_' + kk[len('principle_aq_'):-len('_percent')]] = v
            continue
        scal[_rename(alias, k)] = v
    if 'aquifer_classes' in r:                          # legacy aquifer form
        for c, pc in zip(r['aquifer_classes'], r['aquifer_percentages']):
            scal['pa_' + key(c)] = pc
    series = {}
    if alias == 'soge':                                  # v1: block assessments by year -> latest valid year
        ys = sorted({y for d in yearly.values() for y in d})
        scal.update(_latest_soge({c: [d.get(y) for y in ys] for c, d in yearly.items()}, ys))
        return uid, scal, series
    for col, d in yearly.items():
        vals = [d.get(y) for y in YEARS]
        try:
            series[col] = np.array([NAN if v in (None, '') else float(v) for v in vals])
        except (TypeError, ValueError):                  # text per year (monsoon_onset, class names)
            series[col] = vals
    return uid, scal, series

def village_row(r):
    """Village-level rows (social_economic_indicator, livestock, mws_intersect_villages) in either form."""
    return {VILLAGE_RENAME.get(key(k), k): v for k, v in r.items()}
