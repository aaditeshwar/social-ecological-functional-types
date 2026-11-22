"""Variables of one waterbody, computed from its own yearly series, its zone of influence, its home MWS
profile and the MWS drought years. All percentages (k, kr, krz) are of the waterbody's full extent.
"""
import math

def _vals(xs):
    return [x for x in (xs or []) if isinstance(x, (int, float)) and not (isinstance(x, float) and math.isnan(x))]

def _mean(xs):
    v = _vals(xs); return sum(v) / len(v) if v else None

def theil_sen(ys):
    pts = [(i, y) for i, y in enumerate(ys or []) if isinstance(y, (int, float))]
    s = sorted((y2 - y1) / (x2 - x1) for k, (x1, y1) in enumerate(pts) for (x2, y2) in pts[k + 1:])
    if not s: return None
    n = len(s); return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

def _ratio(a, b):
    return a / b if (a is not None and b) else None

def year_reference(bodies, scope_types):
    """Median kharif fill per (tehsil, year) over the tehsil's in-scope waterbodies that hold water in 3 or more years.
    Dividing by it removes the year's rainfall, so trends and recent losses compare a waterbody with its neighbours."""
    acc = {}
    for b in bodies:
        if b['type'] not in scope_types: continue
        k = b.get('k') or []
        if sum(1 for x in k if isinstance(x, (int, float)) and x > 0) < 3: continue
        for y, x in zip(b.get('years') or [], k):
            if isinstance(x, (int, float)): acc.setdefault((b['district'], b['tehsil'], y), []).append(x)
    ref = {}
    for key, xs in acc.items():
        xs = sorted(xs); n = len(xs)
        ref[key] = xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2
    return ref

def compute(b, prof, drought, ref=None):
    years = b.get('years') or []
    k, kr, krz, wa = b.get('k') or [], b.get('kr') or [], b.get('krz') or [], b.get('water_area') or []
    dmap = drought.get(b.get('home_mws')) or {}
    kd = [x for y, x in zip(years, k) if dmap.get(y) is True]
    kn = [x for y, x in zip(years, k) if dmap.get(y) is False]
    z = b.get('zoi') or {}
    tot = z.get('total_cropable_area_ever_hydroyear') or z.get('sum') and z['sum'] / 1e4
    dbl = [(_vals([d])[0] if _vals([d]) else 0) + (_vals([t])[0] if _vals([t]) else 0)
           for d, t in zip(z.get('doubly_cropped_area') or [], z.get('triply_cropped_area') or [])]
    p = prof.get(b.get('home_mws')) or {}
    v = {
        'area_ha': b['area_ha'],
        'k_mean': _mean(k), 'kr_mean': _mean(kr), 'krz_mean': _mean(krz),
        'k_early': _mean(k[:3]), 'k_late': _mean(k[-2:]),
        'k_slope': theil_sen(k),                                  # percentage points per year
        'k_normal': _mean(kn), 'k_drought': _mean(kd), 'n_drought_years': len(kd), 'n_normal_years': len(kn),
        'catchment_ratio': _ratio(b.get('catchment_ha'), b['area_ha']),
        'zoi_matched': b.get('zoi_match') in ('wb_id', 'location'),
        'zoi_ci_mean': _mean(z.get('cropping_intensity')), 'zoi_ci_slope': theil_sen(z.get('cropping_intensity')),
        'zoi_multi_crop_share': (_mean(dbl) / tot) if (dbl and tot) else None,
        'fish_village_share': p.get('fish_village_share'), 'surface_irrigation_share': p.get('surface_irrigation_share'),
    }
    wet = [y for y, x in zip(years, k) if isinstance(x, (int, float)) and x > 0]
    v['years_wet'] = len(wet)
    v['first_wet_year'] = int(wet[0]) if wet else None
    since = [x for y, x in zip(years, k) if wet and y >= wet[0]]
    v['is_new'] = bool(wet) and int(wet[0]) >= 2022 and all(isinstance(x, (int, float)) and x > 0 for x in since)
    v['regular'] = v['years_wet'] >= 3 and not v['is_new']
    v['krz_slope'] = theil_sen(krz)
    rel = [(x / ref[(b['district'], b['tehsil'], y)]) if (ref and isinstance(x, (int, float)) and ref.get((b['district'], b['tehsil'], y))) else None
           for y, x in zip(years, k)]
    v['rel_fill_mean'] = _mean(rel)
    v['rel_early'], v['rel_late'] = _mean(rel[:3]), _mean(rel[-2:])
    v['rel_late_to_early'] = _ratio(v['rel_late'], v['rel_early'])
    v['rel_slope'] = theil_sen(rel)
    v['k_fill'] = v['k_normal'] if v['k_normal'] is not None else v['k_mean']
    v['retention_kr'] = _ratio(v['kr_mean'], v['k_mean'])
    v['retention_krz'] = _ratio(v['krz_mean'], v['k_mean'])
    v['late_to_early'] = _ratio(v['k_late'], v['k_early'])
    v['drought_fill_ratio'] = _ratio(v['k_drought'], v['k_normal']) if (len(kd) >= 1 and len(kn) >= 2) else None
    return v
