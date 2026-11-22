"""Report dataset coverage per tehsil in the raw cache."""
from .util import ROOT, load_json, raw_dir, iter_locations

def audit(cfg=None):
    cfg_ds = load_json(ROOT / 'config' / 'datasets.json')['datasets']
    req = [k for k, v in cfg_ds.items() if not v.get('optional')]
    out = []
    for s, d, t in iter_locations(cfg):
        rd = raw_dir(s, d, t)
        st = {}
        for ds in req:
            p = rd / (ds + '.json')
            if not p.exists():
                st[ds] = 'missing'
            else:
                o = load_json(p)
                st[ds] = ('ok' if o.get('complete') else 'incomplete') + f":{o['n_rows']}" + \
                         (f"/{o['expected_mws']}" if o.get('expected_mws') and not o.get('complete') else '')
        out.append((s, d, t, st))
    return out

def report(cfg=None, log=print):
    rows = audit(cfg)
    n_ok = 0
    for s, d, t, st in rows:
        bad = {k: v for k, v in st.items() if not v.startswith('ok')}
        if not bad:
            n_ok += 1; continue
        if all(v == 'missing' for v in st.values()):
            log(f'{d} / {t}: not fetched'); continue
        log(f'{d} / {t}: ' + ', '.join(f'{k} {v}' for k, v in bad.items()))
    log(f'{n_ok} of {len(rows)} tehsils complete.')
    return rows

if __name__ == '__main__':
    report()
