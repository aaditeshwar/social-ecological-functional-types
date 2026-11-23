"""Copy the atlas bundles into web/data so that web/index.html can be opened directly.

    python -m seft.cli run            # writes out/csv, out/web and (through this module) web/data
    python -m seft.webdata            # re-copy out/web to web/data by hand, if needed

Each bundle is written twice: <name>.json (used when the page is served over http) and <name>.js
(used when the page is opened from disk with file://, where browsers block fetch). The .js file
just assigns the same JSON to window.SEFT_DATA[<name>]. CSV tables go to web/data/csv/.

To add districts: `python -m seft.cli add ...`, `fetch`, then `run`. The page reads the district list from index.json, so nothing else changes.
Pass --merge to keep district bundles already in web/data that the new run did not produce
(their entries are carried over into the new index).
"""
import argparse, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def write_js(name, text, dest):
    (dest / f'{name}.js').write_text(
        'window.SEFT_DATA=window.SEFT_DATA||{};window.SEFT_DATA[' + json.dumps(name) + ']=' + text + ';\n',
        encoding='utf-8')

def _combine_csv(folder, slugs, merge):
    """mws_all.csv / villages_all.csv = the per-district tables of every district in the atlas."""
    if not folder.exists():
        return
    if not merge:
        for f in folder.glob('*.csv'):
            stem = f.stem.split('_', 1)
            if len(stem) == 2 and stem[1] != 'all' and stem[1] not in slugs:
                f.unlink()
    for kind in ('mws', 'villages'):
        parts = [folder / f'{kind}_{s}.csv' for s in slugs if (folder / f'{kind}_{s}.csv').exists()]
        if not parts:
            continue
        with open(folder / f'{kind}_all.csv', 'w', encoding='utf-8', newline='') as out:
            for i, p in enumerate(parts):
                with open(p, encoding='utf-8', newline='') as fh:
                    lines = fh.readlines()
                out.writelines(lines if i == 0 else lines[1:])

def build(src=None, dest=None, csv_src=None, merge=False):
    src = Path(src or ROOT / 'out' / 'web')
    dest = Path(dest or ROOT / 'web' / 'data')
    csv_src = Path(csv_src or src.parent / 'csv')
    if not (src / 'index.json').exists():
        raise SystemExit(f'{src / "index.json"} not found. Run `python -m seft.cli run` first.')
    dest.mkdir(parents=True, exist_ok=True)
    index = json.loads((src / 'index.json').read_text(encoding='utf-8'))
    if merge and (dest / 'index.json').exists():
        old = json.loads((dest / 'index.json').read_text(encoding='utf-8'))
        have = {d['district'] for d in index['districts']}
        kept = [d for d in old['districts'] if d['district'] not in have and (dest / f"d_{d['slug']}.json").exists()]
        index['districts'] += kept
        if kept:
            print('kept from earlier runs:', ', '.join(d['district'] for d in kept),
                  '(pooled percentiles and knowledge come from the new run)')
    names = ['index'] + [f"d_{d['slug']}" for d in index['districts']]
    for n in names:
        if n == 'index':
            text = json.dumps(index, separators=(',', ':'), ensure_ascii=False)
        else:
            f = src / f'{n}.json'
            if not f.exists():
                continue                     # kept bundle already in dest
            text = f.read_text(encoding='utf-8')
        (dest / f'{n}.json').write_text(text, encoding='utf-8')
        write_js(n, text, dest)
    if not merge:   # remove bundles of districts no longer in the index
        keep = set(names)
        for f in list(dest.glob('d_*.json')) + list(dest.glob('d_*.js')):
            if f.stem not in keep:
                f.unlink()
    if csv_src.exists() and csv_src.resolve() != (dest / 'csv').resolve():
        (dest / 'csv').mkdir(exist_ok=True)
        for f in csv_src.glob('*.csv'):
            if not f.name.endswith('_all.csv'):
                shutil.copy2(f, dest / 'csv' / f.name)
    _combine_csv(dest / 'csv', [d['slug'] for d in index['districts']], merge)
    print(f'wrote {len(names)} bundles to {dest}: {", ".join(d["district"] for d in index["districts"])}')
    print(f'open {dest.parent / "index.html"} in a browser, or: python -m http.server -d {dest.parent} 8000')

def refresh_knowledge(dest=None, kd=None):
    """Replace the knowledge embedded in web/data/index.json and web/data/waterbody/index.json with the current
    knowledge files, keeping every result. For changes that do not alter scoring (interventions, notes, sources,
    scheme text); after changing signals, rules, questions or types, run `run` / `wb-run` instead."""
    from .export import _knowledge, _scheme_names, _wb_rule_labels
    dest = Path(dest or ROOT / 'web' / 'data'); kd = Path(kd or ROOT / 'knowledge')
    done = []
    if (dest / 'index.json').exists():
        index = json.loads((dest / 'index.json').read_text(encoding='utf-8'))
        K = _knowledge(kd); index['knowledge'] = K; index['scheme_names'] = _scheme_names(K); index['wb_rule_labels'] = _wb_rule_labels()
        text = json.dumps(index, separators=(',', ':'), ensure_ascii=False)
        (dest / 'index.json').write_text(text, encoding='utf-8'); write_js('index', text, dest); done.append('watershed')
    wd = dest / 'waterbody'
    if (wd / 'index.json').exists():
        from .wb.score import load_knowledge
        index = json.loads((wd / 'index.json').read_text(encoding='utf-8'))
        K = load_knowledge(); index['knowledge'] = K
        from .export import _scheme_names as _sn
        index['scheme_names'] = _sn(_knowledge(kd))
        text = json.dumps(index, separators=(',', ':'), ensure_ascii=False)
        (wd / 'index.json').write_text(text, encoding='utf-8'); write_js('wb_index', text, wd); done.append('waterbody')
    print('knowledge refreshed in', ', '.join(done) or 'nothing (no index.json found)')

def main(argv=None):
    ap = argparse.ArgumentParser(prog='seft.webdata', description=__doc__.split('\n')[0])
    ap.add_argument('--src', help='folder with index.json and d_*.json (default out/web)')
    ap.add_argument('--dest', help='default web/data')
    ap.add_argument('--csv', help='folder with CSV tables (default out/csv)')
    ap.add_argument('--merge', action='store_true', help='keep districts already in web/data')
    a = ap.parse_args(argv)
    build(a.src, a.dest, a.csv, a.merge)

if __name__ == '__main__':
    main()
