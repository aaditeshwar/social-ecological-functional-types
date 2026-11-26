"""Score the atlas rules and the Signal_Verification sheet rules against ground-truth micro-watersheds.

    python -m seft.cli groundtruth --truth config/groundtruth/final_ground_truth.json

Input: a JSON of {section: {pathway: {"positive": [...], "negative": [...]}}}, each entry giving a
block_name (tehsil) and an MWS uid. Steps:

1. Resolve each block name to (state, district, tehsil) using get_active_locations, cached in
   config/groundtruth/active_locations.json (--refresh-locations re-downloads it). Names are matched
   without case, and "Keonjhar (Kendujhar)" also matches "keonjhar" and "kendujhar". A name found in
   several districts is settled by which tehsil's data contain the listed uid.
2. Fetch the tehsils with the normal fetcher (seft/fetch.py), so the data are cached once under
   data/raw/ like every other location; cached datasets are reused unless --force. The resolved
   locations are written to config/groundtruth/locations.json.
3. Run the atlas pipeline on those tehsils with the atlas's own pooled-percentile thresholds (from
   web/data/index.json), so the rules are exactly those the atlas applies (--pools run pools over the
   ground-truth tehsils instead). Run the sheet rules (knowledge/sheet_rules.json, seft/sheet.py) on the
   same indicators.
4. Map each ground-truth pathway to atlas rules and a sheet pattern (config/groundtruth/pathways.json)
   and write confusion matrices and a per-MWS detail table to out/groundtruth/.

An atlas pathway is predicted present when any of its rules is triggered, absent when none is triggered
and at least one is 'not triggered' or 'not applicable' (system gate), and unknown otherwise. The
'atlas, no gate' row ignores the production-system gate. Unknown predictions are counted separately
and left out of accuracy, precision and recall.
"""
import csv, json, math, re
from collections import defaultdict, OrderedDict
from pathlib import Path
from .util import ROOT, load_json, dump_json, raw_dir

GT_DIR = ROOT / 'config' / 'groundtruth'
OUT_DIR = ROOT / 'out' / 'groundtruth'

# ---------------------------------------------------------------- ground truth and locations
def flatten(truth):
    items = []
    for sec, paths in truth.items():
        for path, lab in paths.items():
            for label in ('positive', 'negative'):
                for e in lab.get(label, []) or []:
                    items.append({'pathway': f'{sec}.{path}', 'label': 1 if label == 'positive' else 0,
                                  'block': e['block_name'], 'uid': e['uid']})
    return items

def _names(label):
    s = label.strip().lower()
    out = {s}
    m = re.match(r'^(.*?)\s*\((.*?)\)\s*$', s)
    if m: out |= {m.group(1).strip(), m.group(2).strip()}
    return {re.sub(r'[\s\-_.]+', ' ', x).strip() for x in out}

def active_locations(refresh=False, log=print):
    p = GT_DIR / 'active_locations.json'
    if p.exists() and not refresh: return load_json(p)
    from .fetch import _get, _key, API_BASE
    r = _get(f'{API_BASE}/api/v2/get_active_locations/', {}, headers={'X-API-Key': _key()})
    body = r.json()
    locs = body.get('data', {}).get('locations', body) if isinstance(body, dict) else body
    dump_json(locs, p); log(f'active locations: {sum(len(d["blocks"]) for s in locs for d in s["district"])} blocks saved to {p}')
    return locs

def location_index(locs):
    idx = defaultdict(list)
    for s in locs:
        for d in s['district']:
            for b in d['blocks']:
                for n in _names(b['label']):
                    idx[n].append((s['label'], d['label'], b['label']))
    return {k: sorted(set(v)) for k, v in idx.items()}

def _cfg(triples):
    by = OrderedDict()
    for s, d, t in triples:
        by.setdefault((s, d), [])
        if t not in by[(s, d)]: by[(s, d)].append(t)
    return {'note': 'Ground-truth tehsils from final_ground_truth.json (rebuilt by the groundtruth command).',
            'districts': [{'state': s, 'district': d, 'tehsils': ts, 'roles': ['groundtruth']} for (s, d), ts in by.items()]}

def _uids_in(state, district, tehsil):
    f = raw_dir(state, district, tehsil) / 'lulc_vector.json'
    if not f.exists(): return set()
    out = set()
    for r in load_json(f).get('rows', []):
        u = (r.get('metadata') or {}).get('uid') if isinstance(r.get('metadata'), dict) else None
        u = u or r.get('uid') or r.get('UID')
        if u: out.add(str(u))
    return out

def resolve(items, refresh_locations=False, fetch=True, force=False, log=print):
    idx = location_index(active_locations(refresh_locations, log))
    want = defaultdict(set)
    for it in items: want[it['block']].add(it['uid'])
    cands = {b: idx.get(next(iter(_names(b))), []) for b in want}
    missing = sorted(b for b, c in cands.items() if not c)
    if fetch:
        from .fetch import fetch_all
        fetch_all(_cfg([t for c in cands.values() for t in c]), force=force, log=log)
    res, chosen = {}, []
    for b, cs in sorted(cands.items()):
        uids = sorted(want[b])
        scored = [(len(set(uids) & _uids_in(*c)), c) for c in cs]
        scored.sort(key=lambda x: -x[0])
        if not scored:
            res[b] = {'status': 'not in active locations', 'uids': uids}; continue
        best_n, best = scored[0]
        if len(scored) > 1 and best_n == scored[1][0]:
            status = 'ambiguous' if best_n else 'ambiguous, uid not found'
        else:
            status = 'resolved' if len(cs) == 1 else f'resolved by uid among {len(cs)} candidates'
        if best_n < len(uids): status += f'; {len(uids) - best_n} of {len(uids)} uid(s) not in this tehsil'
        res[b] = {'state': best[0], 'district': best[1], 'tehsil': best[2], 'status': status, 'uids': uids,
                  'uids_found': best_n, 'candidates': [list(c) for c in cs]}
        chosen.append(best)
    cfg = _cfg(chosen)
    dump_json(cfg, GT_DIR / 'locations.json'); dump_json(res, GT_DIR / 'resolution.json')
    for b in missing: log(f'  {b}: not in get_active_locations; skipped')
    return cfg, res

# ---------------------------------------------------------------- scoring
def _atlas_pred(stress, rules, gated=True):
    st = [stress[r]['status'] if gated else stress[r]['would'] for r in rules if r in stress]
    if not st: return None
    if 'triggered' in st: return 1
    if any(s in ('not triggered', 'not applicable') for s in st): return 0
    return None

def _signal_pred(sig, ids):
    on = [sig.get(i, {}).get('on') for i in ids]
    if any(o is True for o in on): return 1
    if all(o is False for o in on): return 0
    return None

def score(items, cfg, pools_from='atlas', log=print):
    from .pipeline import run
    from .sheet import load_sheet_rules, evaluate_sheet
    want = {it['uid'] for it in items}
    pools = None
    if pools_from == 'atlas':
        ip = ROOT / 'web' / 'data' / 'index.json'
        if ip.exists(): pools = load_json(ip).get('pools')
        if not pools: log('  no atlas pools in web/data/index.json; pooling over the ground-truth tehsils')
    recs, _, _, meta = run(cfg, log=log, pools=pools, keep=lambda r: r['uid'] in want)
    SR = load_sheet_rules()
    by = {}
    for r in recs:
        r['sheet'] = evaluate_sheet(r['env'], SR)
        by[r['uid']] = r
    return by, meta

def _cm(pairs):
    c = {'TP': 0, 'FP': 0, 'FN': 0, 'TN': 0, 'unknown': 0, 'no data': 0}
    for y, p in pairs:
        if p == 'no data': c['no data'] += 1
        elif p is None: c['unknown'] += 1
        elif y == 1: c['TP' if p == 1 else 'FN'] += 1
        else: c['FP' if p == 1 else 'TN'] += 1
    n = c['TP'] + c['FP'] + c['FN'] + c['TN']
    c['n'] = n
    c['accuracy'] = round((c['TP'] + c['TN']) / n, 3) if n else None
    c['precision'] = round(c['TP'] / (c['TP'] + c['FP']), 3) if c['TP'] + c['FP'] else None
    c['recall'] = round(c['TP'] / (c['TP'] + c['FN']), 3) if c['TP'] + c['FN'] else None
    c['specificity'] = round(c['TN'] / (c['TN'] + c['FP']), 3) if c['TN'] + c['FP'] else None
    # balanced accuracy needs both classes; F1 is 0 when nothing positive is found
    c['balanced_accuracy'] = round((c['recall'] + c['specificity']) / 2, 3) \
        if c['recall'] is not None and c['specificity'] is not None else None
    p_, r_ = c['precision'] or 0.0, c['recall']
    c['f1'] = None if r_ is None else (round(2 * p_ * r_ / (p_ + r_), 3) if p_ + r_ else 0.0)
    return c

def evaluate(items, by, mapping):
    rows, detail = [], []
    for pw, m in list(mapping['pathways'].items()) + list(mapping.get('extra', {}).items()):
        its = [it for it in items if it['pathway'] == pw]
        if not its:
            continue
        preds = defaultdict(list)
        for it in its:
            r = by.get(it['uid'])
            d = {'pathway': pw, 'block': it['block'], 'uid': it['uid'], 'truth': it['label']}
            for name, fn in _predictors(m):
                p = 'no data' if r is None else fn(r)
                preds[name].append((it['label'], p))
                d[name] = p
            if r is not None:
                d['tehsil'] = f"{r['district']} / {r['tehsil']}"
                for rid in m.get('atlas_rules', []):
                    s = r['stress'].get(rid, {})
                    d[f'atlas:{rid}'] = f"{s.get('status')} ({s.get('intensity')})" if s else ''
                sid = m.get('sheet')
                if sid:
                    s = r['sheet'][sid]
                    d[f'sheet:{sid}'] = f"{s['status']} ({s['intensity']})"
                    d['sheet signals'] = ' '.join(f"{k[-2:]}={'?' if v is None else v}" for k, v in s['signals'].items())
                sig = r['signals']
                used = sorted({x for rid in m.get('atlas_rules', []) for role in ('stress', 'context')
                               for x in _rule(rid)['signals'].get(role, [])}) if m.get('atlas_rules') else m.get('atlas_signals', [])
                d['atlas signals on'] = ' '.join(x for x in used if sig.get(x, {}).get('on') is True)
                d['atlas signals unknown'] = ' '.join(x for x in used if sig.get(x, {}).get('on') is None)
            detail.append(d)
        for name, _ in _predictors(m):
            rows.append({'pathway': pw, 'label': m.get('label', pw), 'rules': name, **_cm(preds[name])})
    return rows, detail

def _p_sheet(r, sid):
    s = r['sheet'][sid]['status']
    return 1 if s == 'triggered' else (0 if s == 'not triggered' else None)

def _or(a, b):
    if a == 1 or b == 1: return 1
    return None if a is None or b is None else 0

def _and(a, b):
    if a == 0 or b == 0: return 0
    return None if a is None or b is None else 1

def combo_predictors(m):
    """Ways of combining the atlas and the sheet for one pathway: either fires (OR), both fire (AND), and
    the sheet confirmed by, or added to, each atlas sub-pathway on its own."""
    R, sid = m.get('atlas_rules') or [], m.get('sheet')
    if not R or not sid: return []
    out = [('atlas OR sheet', lambda r: _or(_atlas_pred(r['stress'], R), _p_sheet(r, sid))),
           ('atlas AND sheet', lambda r: _and(_atlas_pred(r['stress'], R), _p_sheet(r, sid)))]
    if len(R) > 1:
        for c in R:
            out.append((f'sheet AND {c}', lambda r, c=c: _and(_atlas_pred(r['stress'], [c]), _p_sheet(r, sid))))
            out.append((f'sheet OR {c}', lambda r, c=c: _or(_atlas_pred(r['stress'], [c]), _p_sheet(r, sid))))
    return out

def combinations(items, by, mapping):
    rows, tiers = [], []
    for pw, m in mapping['pathways'].items():
        its = [it for it in items if it['pathway'] == pw and it['uid'] in by]
        if not its or not combo_predictors(m): continue
        for name, fn in combo_predictors(m):
            rows.append({'pathway': pw, 'label': m.get('label', pw), 'rules': name,
                         **_cm([(it['label'], fn(by[it['uid']])) for it in its])})
        t = defaultdict(lambda: [0, 0])
        for it in its:
            r = by[it['uid']]
            a, sh = _atlas_pred(r['stress'], m['atlas_rules']), _p_sheet(r, m['sheet'])
            k = ('both' if a == 1 and sh == 1 else 'sheet only' if sh == 1 else 'atlas only' if a == 1
                 else 'neither' if a == 0 and sh == 0 else 'undecided')
            t[k][0] += it['label']; t[k][1] += 1
        tiers.append({'pathway': pw, 'label': m.get('label', pw), **{k: tuple(v) for k, v in t.items()}})
    return rows, tiers

def sample_rates(mapping, log=print):
    """Share of the atlas sample MWS (the pools districts of config/locations.json) where each rule set and combination fires.
    Cached in out/groundtruth/sample_rates.json, keyed by a hash of the knowledge files."""
    import hashlib
    h = hashlib.sha1()
    for f in sorted((ROOT / 'knowledge').glob('*.json')) + [GT_DIR / 'pathways.json']:
        h.update(f.read_bytes())
    key = h.hexdigest()
    cache = OUT_DIR / 'sample_rates.json'
    if cache.exists():
        c = load_json(cache)
        if c.get('key') == key: return c['rates']
    from .pipeline import run
    from .sheet import load_sheet_rules, evaluate_sheet
    pools = load_json(ROOT / 'web' / 'data' / 'index.json').get('pools')
    log('  scoring the atlas sample for firing rates (cached afterwards) ...')
    from .util import with_role
    recs, _, _, _ = run(with_role(load_json(ROOT / 'config' / 'locations.json'), 'pools'), log=lambda *a: None, pools=pools)
    SR = load_sheet_rules()
    for r in recs: r['sheet'] = evaluate_sheet(r['env'], SR)
    rates = {}
    for pw, m in mapping['pathways'].items():
        preds = _predictors(m) + combo_predictors(m)
        if not preds: continue
        rates[pw] = {name: round(sum(1 for r in recs if fn(r) == 1) / len(recs), 3) for name, fn in preds}
    dump_json({'key': key, 'n': len(recs), 'rates': rates}, cache)
    return rates

_GRAPH = None
def _rule(rid):
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = {r['id']: r for r in load_json(ROOT / 'knowledge' / 'causal_graph.json')['stresses']}
    return _GRAPH[rid]

def _predictors(m):
    out = []
    if m.get('atlas_rules'):
        out.append(('atlas', lambda r, R=m['atlas_rules']: _atlas_pred(r['stress'], R, True)))
        out.append(('atlas, no gate', lambda r, R=m['atlas_rules']: _atlas_pred(r['stress'], R, False)))
    if m.get('atlas_signals'):
        out.append(('atlas', lambda r, S=m['atlas_signals']: _signal_pred(r['signals'], S)))
    if m.get('sheet'):
        def f(r, sid=m['sheet']):
            s = r['sheet'][sid]['status']
            return 1 if s == 'triggered' else (0 if s == 'not triggered' else None)
        out.append(('sheet', f))
    if m.get('sheet_signal'):
        def g(r, ss=m['sheet_signal']):
            rid, sig = ss.split(':'); return r['sheet'][rid]['signals'].get(sig)
        out.append(('sheet', g))
    return out

# ---------------------------------------------------------------- report
def _nb(text):
    """Non-breaking spaces, so that a table cell stays on one line."""
    return str(text).replace(' ', '&nbsp;').replace('-', '&#8209;')

def _table(rows, rates=None):
    L = ['| Pathway | Rules | n | TP | FP | FN | TN | Unknown | No data | Accuracy | Balanced accuracy | F1 | Precision | Recall |'
         + (' Sample |' if rates else ''),
         '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|' + ('---|' if rates else '')]
    for r in rows:
        sr = (rates or {}).get(r['pathway'], {}).get(r['rules'])
        L.append(f"| {_nb(r['label'])} | {_nb(r['rules'])} | {r['n']} | {r['TP']} | {r['FP']} | {r['FN']} | {r['TN']} | "
                 f"{r['unknown']} | {r['no data']} | {_fmt(r['accuracy'])} | {_fmt(r['balanced_accuracy'])} | {_fmt(r['f1'])} | "
                 f"{_fmt(r['precision'])} | {_fmt(r['recall'])} |" + ((f" {round(100 * sr)}% |" if sr is not None else ' – |') if rates else ''))
    return L

def _fmt(v):
    return '–' if v is None else (f'{v:.2f}' if isinstance(v, float) else str(v))

def write_report(rows, detail, res, mapping, items, by, combos=None, tiers=None, rates=None, out=OUT_DIR):
    out.mkdir(parents=True, exist_ok=True)
    keys = ['pathway', 'label', 'rules', 'n', 'TP', 'FP', 'FN', 'TN', 'unknown', 'no data',
            'accuracy', 'balanced_accuracy', 'f1', 'precision', 'recall', 'specificity']
    with open(out / 'confusion.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, keys, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    dk = []
    for d in detail:
        for k in d:
            if k not in dk: dk.append(k)
    with open(out / 'detail.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, dk); w.writeheader(); w.writerows(detail)
    if combos:
        with open(out / 'combinations.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, keys, extrasaction='ignore'); w.writeheader(); w.writerows(combos)
    dump_json({'confusion': rows, 'combinations': combos or [], 'confidence_tiers': tiers or [],
               'sample_rates': rates or {}, 'detail': detail, 'resolution': res}, out / 'results.json')
    L = ['# Ground-truth check of the atlas and Signal_Verification rules', '',
         f'{len(items)} labels on {len({i["uid"] for i in items})} micro-watersheds in {len(res)} tehsils. '
         'TP/FP/FN/TN count decided predictions; "unknown" means the rule could not be decided from the data, '
         '"no data" that the MWS was not found in the fetched tehsil. Metrics use decided predictions only. '
         'Balanced accuracy is the mean of recall and specificity, so it is not inflated by a rule that never '
         '(or always) fires; it needs both positive and negative labels. "atlas, no gate" ignores the '
         'production-system gate. "Sample" is the share of the 4,598 atlas sample MWS where the rule fires.', '']
    L += _table(rows, rates)
    skipped = [(pw, m) for pw, m in mapping['pathways'].items() if not m.get('atlas_rules') and not m.get('sheet')
               and not m.get('atlas_signals') and not m.get('sheet_signal')]
    empty = sorted({f'{s}.{p}' for s, ps in load_json(GT_DIR / 'final_ground_truth.json').items()
                    for p, v in ps.items() if not (v.get('positive') or v.get('negative'))}) \
        if (GT_DIR / 'final_ground_truth.json').exists() else []
    if skipped or empty:
        L += ['', '**Not scored:** ' + '; '.join([f"{pw} ({m.get('note', 'no rule')})" for pw, m in skipped] +
                                                  [f'{p} (no labels)' for p in empty])]
    for title, f in (('Changes made to the atlas rules', 'changes.md'), ('Pathway by pathway: original rule, changes made, options tested', 'suggestions.md')):
        p = GT_DIR / f
        if p.exists():
            L += ['', f'## {title}', '', p.read_text().strip()]
            if f == 'suggestions.md' and combos:
                L += ['', '### Combining the atlas and the sheet (computed on this run)', '',
                      '"atlas OR sheet" fires when either fires; "atlas AND sheet" when both do. "sheet AND <rule>" '
                      'asks the sheet to be confirmed by one atlas sub-pathway; "sheet OR <rule>" adds one atlas '
                      'sub-pathway to the sheet.', '']
                L += _table(combos, rates)
                if tiers:
                    L += ['', '### Agreement as a confidence measure', '',
                          'Each cell gives labelled positives / labels in that tier. If agreement carries information, '
                          '"both" should be mostly positive and "neither" mostly negative, with the single-rule tiers in '
                          'between.', '', '| Pathway | Both fire | Sheet only | Atlas only | Neither |', '|---|---|---|---|---|']
                    tot = defaultdict(lambda: [0, 0])
                    for t in tiers:
                        cells = []
                        for k in ('both', 'sheet only', 'atlas only', 'neither'):
                            v = t.get(k)
                            cells.append('–' if not v else f'{v[0]} / {v[1]}')
                            if v: tot[k][0] += v[0]; tot[k][1] += v[1]
                        L.append(f"| {_nb(t['label'])} | " + ' | '.join(cells) + ' |')
                    L.append('| **All pathways** | ' + ' | '.join(
                        f"**{tot[k][0]} / {tot[k][1]}**" if tot[k][1] else '–' for k in ('both', 'sheet only', 'atlas only', 'neither')) + ' |')
    L += ['', '## Locations', '', '| Block | State / District / Tehsil | Status |', '|---|---|---|']
    for b, v in sorted(res.items()):
        L.append(f"| {b} | {v.get('state', '')} / {v.get('district', '')} / {v.get('tehsil', '')} | {v['status']} |")
    (out / 'report.md').write_text('\n'.join(L) + '\n')
    return out / 'report.md'

def main(truth_path, refresh_locations=False, force=False, fetch=True, pools_from='atlas', sample=True, log=print):
    truth_path = Path(truth_path)
    truth = load_json(truth_path)
    GT_DIR.mkdir(parents=True, exist_ok=True)
    if truth_path.resolve() != (GT_DIR / 'final_ground_truth.json').resolve():
        dump_json(truth, GT_DIR / 'final_ground_truth.json')
    items = flatten(truth)
    mapping = load_json(GT_DIR / 'pathways.json')
    log(f'{len(items)} labels, {len({i["block"] for i in items})} blocks, {len({i["uid"] for i in items})} MWS')
    cfg, res = resolve(items, refresh_locations, fetch, force, log)
    by, meta = score(items, cfg, pools_from, log)
    rows, detail = evaluate(items, by, mapping)
    combos, tiers = combinations(items, by, mapping)
    rates = sample_rates(mapping, log) if sample else None
    p = write_report(rows, detail, res, mapping, items, by, combos, tiers, rates)
    log(f'wrote {p}, confusion.csv, detail.csv and results.json to {p.parent}')
    return rows
