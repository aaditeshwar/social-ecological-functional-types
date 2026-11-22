"""Re-score the atlas from the indicator values stored in its bundles, without raw API data.

    python -m seft.rescore            # web/data -> out/web, out/csv (MWS tables) -> web/data

Use this after editing signals.json, causal_graph.json, taxonomy.json, questions.json or schemes.json
when the raw tehsil data are not cached. Indicators, contexts and the system mix are taken from the
bundles as they are (variables added since the bundles were built are missing until the data are
fetched again and `seft.cli run` is used). Village tables are kept from the previous run.
"""
import argparse, math
from pathlib import Path
from .util import ROOT, load_json
from .expr import Namespace, NAN
from .stresses import load_graph, load_taxonomy
from .signals import load_signals, pooled_percentiles, threshold_table
from .schemes import load_schemes
from .assess import load_questions
from .archetypes import load_archetypes, finish
from .pipeline import score

def _f(x):
    return NAN if x is None else x

def derive(ind, env, V):
    """Variables missing from an older bundle that depend only on stored indicators (e.g. f_sloping)."""
    from .expr import evaluate, names_in, FUNCS
    for v in V:
        if v['id'] in ind or v.get('series'): continue
        names = names_in(v['expr']) - set(FUNCS) - {'nan', 'True', 'False', 'None'}
        if names and names <= set(env):
            try: val = evaluate(v['expr'], env)
            except Exception: continue
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                env[v['id']] = val; ind[v['id']] = None if math.isnan(val) else round(float(val), 4)

def records_from_bundles(src, A, V):
    index = load_json(src / 'index.json')
    hids = [h['id'] for h in A['helpers']]
    recs, villages, clusters = [], {}, {}
    for d in index['districts']:
        b = load_json(src / f"d_{d['slug']}.json")
        vids = b['var_ids']; arch = b['arch']
        vill = {}
        for row in b['villages']:
            v = dict(zip(b['village_cols'], row))
            vill[v['id']] = {'village_id': v['id'], 'name': v['name'], 'tehsil': v['tehsil'], 'mws': v['mws'],
                             'overlap_share': v['overlap'], 'pop': v['pop'], 'sc': v['sc'], 'st': v['st'], 'literacy': v['literacy'],
                             'livestock': {'all_livestock_total': v['livestock'], 'cattle_total': v['cattle'], 'buffalo_total': v['buffalo'],
                                           'sheep_total': v['sheep'], 'goat_total': v['goat'], 'pig_total': v['pig']}}
        villages[d['district']] = vill
        clusters[d['district']] = {m['u']: m.get('v', []) for m in b['mws']}
        for m in b['mws']:
            ind = dict(zip(vids, m['i']))
            env = {k: _f(v) for k, v in ind.items()}
            derive(ind, env, V)
            ctx = Namespace(zip(b['dims'], m['c']))
            env.update(ctx=ctx, state=d['state'], district=d['district'])
            shares = dict(zip(arch, m['m']))
            for k, v in shares.items(): env['share_' + k] = v
            h = m.get('h') or []
            helpers = dict(zip(hids, h[:len(hids)]))
            mix = finish(shares, A, helpers, h[len(hids)] if len(h) > len(hids) else None)
            recs.append({'uid': m['u'], 'state': d['state'], 'district': d['district'], 'tehsil': m['t'], 'tehsils': m['ts'],
                         'area': m['a'], 'ind': ind, 'env': env, 'ctx': ctx, 'mix': mix, 'mix0': mix, 'answers': {},
                         'canals': m.get('cp', []), 'gc': [], 'n_villages': len(m.get('v', []))})
    return index, recs, villages, clusters

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--src', default=str(ROOT / 'web' / 'data'))
    ap.add_argument('--knowledge', default=str(ROOT / 'knowledge'))
    ap.add_argument('--out', default=str(ROOT / 'out'))
    ap.add_argument('--no-web', action='store_true')
    a = ap.parse_args(argv)
    kd = Path(a.knowledge); src = Path(a.src); out = Path(a.out)
    A = load_archetypes(kd / 'archetypes.json')
    G = load_graph(kd / 'causal_graph.json'); S = load_signals(kd / 'signals.json'); T = load_taxonomy(kd / 'taxonomy.json')
    Q = load_questions(kd / 'questions.json'); SC = load_schemes(kd / 'schemes.json')
    from .indicators import load_variables, _order
    V = _order(load_variables(kd / 'variables.json'))
    index, recs, villages, clusters = records_from_bundles(src, A, V)
    pools = pooled_percentiles(S, [r['env'] for r in recs])
    for r in recs: score(r, G, Q, S, T, SC, pools)
    from .export import write_csv, write_web, _knowledge
    K = _knowledge(kd)
    files = write_csv(recs, None, K, out / 'csv')
    print(f'rescored {len(recs)} MWS; wrote {len(files)} MWS tables to {out / "csv"}')
    if a.no_web: return recs
    cfg = {'districts': [{'state': d['state'], 'district': d['district'], 'tehsils': d['tehsils']} for d in index['districts']]}
    rf = {d['district']: d.get('rain_factor', 1.0) for d in index['districts']}
    meta = {'rain_factors': rf, 'pools': pools, 'signal_thresholds': threshold_table(S, pools)}
    write_web(recs, villages, clusters, meta, K, cfg, out / 'web')
    # keep the previous village tables next to the new MWS tables
    import shutil
    for f in (src / 'csv').glob('villages_*.csv'):
        if not (out / 'csv' / f.name).exists(): shutil.copy(f, out / 'csv' / f.name)
    from .webdata import build
    build(out / 'web', src, out / 'csv')
    return recs

if __name__ == '__main__':
    main()
