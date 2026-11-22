"""`python -m seft.cli wb-run`: build waterbodies, attach landscape context, write tables.

Writes out/waterbody/waterbodies.csv (one row per merged waterbody of at least types.json min_area_ha),
out/waterbody/summary.json (counts by tehsil, type, ZoI match and landscape setting).
"""
import collections, csv, json
from pathlib import Path
from ..util import ROOT, load_json
from .build import build_all
from .context import attach, CTX_COLS, SHARE_COLS

def _mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(sum(xs) / len(xs), 2) if xs else None

def row(b):
    z = b.get('zoi') or {}
    m = b['mws']
    return {
        'wb_id': b['wb_id'], 'state': b['state'], 'district': b['district'], 'tehsil': b['tehsil'], 'type': b['type'],
        'area_ha': b['area_ha'], 'n_fragments': b['n_fragments'], 'wb_type': b['wb_type'], 'wb_name': b['wb_name'],
        'on_drainage': b['on_drainage'], 'stream_order': b['stream_order'], 'catchment_ha': b['catchment_ha'],
        'home_mws': b['home_mws'], 'n_mws': b['n_mws'], 'lon': b['centroid'][0], 'lat': b['centroid'][1],
        'k_mean': _mean(b.get('k') or []), 'kr_mean': _mean(b.get('kr') or []), 'krz_mean': _mean(b.get('krz') or []),
        'zoi_match': b['zoi_match'], 'zoi_radius_m': z.get('zoi'), 'zoi_area_ha': z.get('zoi_area'),
        'zoi_ci_mean': _mean(z.get('cropping_intensity') or []),
        'mws_in_atlas': b['mws_in_atlas'], 'n_mws_villages': len(b['mws_villages']),
        **{c: m.get(c) for c in CTX_COLS}, 'main_system': m.get('main_system'),
        **{c: m.get(c) for c in SHARE_COLS},
    }

def main(cfg_path=None, out=None, log=print):
    cfg = load_json(cfg_path) if cfg_path else None
    B, stats, types = build_all(cfg, log=log)
    attach(B)
    out = Path(out or ROOT / 'out' / 'waterbody'); out.mkdir(parents=True, exist_ok=True)
    rows = [row(b) for b in B]
    with open(out / 'waterbodies.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    inscope = {t['id'] for t in types['types'] if t['in_scope']}
    cnt = lambda key: dict(collections.Counter(key(b) for b in B).most_common())
    summary = {
        'min_area_ha': types['min_area_ha'], 'tehsils': stats,
        'by_type': cnt(lambda b: b['type']),
        'by_type_zoi_match': cnt(lambda b: f"{b['type']}|{b['zoi_match']}"),
        'in_scope_by_setting': cnt(lambda b: f"{b['type']}|{b['mws'].get('ctx_rainfall')}|{b['mws'].get('ctx_aquifer')}" if b['type'] in inscope else None),
        'in_scope_by_main_system': cnt(lambda b: f"{b['type']}|{b['mws'].get('main_system')}" if b['type'] in inscope else None),
    }
    (out / 'summary.json').write_text(json.dumps(summary, indent=1))
    log(f'{len(B)} waterbodies written to {out / "waterbodies.csv"}')
    return B, summary
