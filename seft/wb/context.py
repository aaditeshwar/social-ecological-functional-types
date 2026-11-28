"""Landscape context for waterbodies, from the watershed atlas pipeline.

`mws_context(cfg)` runs the watershed pipeline (seft.pipeline.run) for the same tehsils, with the atlas's
pooled-percentile thresholds from web/data/index.json when present (as the ground-truth check does), so the MWS
context is exactly what the watershed atlas would show. Each waterbody then takes the context of its home MWS:
the context dimensions (ctx_*), the archetype shares (share_*) and the MWS variables (mws_*).
Villages are reached through the MWS (seft/wb/villages.py).
"""
from ..util import ROOT, load_json, atlas_mws_pools

def mws_context(cfg, log=print):
    from ..pipeline import run
    pools = atlas_mws_pools()
    if not pools: log('  no published MWS pools; pooled percentiles come from these tehsils')
    recs, _, _, _ = run(cfg, log=lambda m: None, pools=pools)
    out = {}
    for r in recs:
        row = {f'ctx_{k}': v for k, v in (r.get('ctx') or {}).items()}
        row.update({f'share_{k}': v for k, v in (r.get('mix') or {}).get('shares', {}).items()})
        row.update({f'mws_{k}': v for k, v in (r.get('ind') or {}).items()})
        row['mws_area_ha'] = r.get('area')
        row['dominant_system'] = (r.get('mix') or {}).get('dominant')
        row['mws_tehsil'] = r.get('tehsil')
        out[r['uid']] = row
    return out

def attach(bodies, ctx, prof):
    for b in bodies:
        m = ctx.get(b.get('home_mws'))
        b['mws_in_atlas'] = m is not None
        b['mws'] = dict(m) if m else {}
        b['n_mws_villages'] = (prof.get(b.get('home_mws')) or {}).get('n_villages', 0)
    return bodies
