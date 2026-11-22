"""Command line entry point. Run from the repository root.

    python -m seft.cli add --state Maharashtra --district Yavatmal --tehsils "Darwha,Pusad"
                                       # add a district (and tehsils) to config/locations.json
    python -m seft.cli fetch           # API data + GeoServer geometry for every location (needs CORE_STACK_API_KEY)
    python -m seft.cli audit           # which datasets are missing or incomplete
    python -m seft.cli validate        # check the knowledge JSONs after editing
    python -m seft.cli run             # indicators, systems, stresses, schemes -> out/csv, out/web and web/data
    python -m seft.cli all             # fetch, validate and run in one go
    python -m seft.cli groundtruth --truth FILE
                                       # fetch ground-truth tehsils, score atlas and sheet rules, write
                                       # confusion matrices to out/groundtruth/

Common options: --locations FILE (default config/locations.json). For run: --answers FILE (community
answers saved from the atlas), --merge (keep districts already in the atlas that this run does not cover).
"""
import argparse, sys
from pathlib import Path
from .util import ROOT, load_json, dump_json, raw_dir, iter_locations

DEFAULT_LOC = str(ROOT / 'config' / 'locations.json')

def cmd_add(a):
    p = Path(a.locations)
    cfg = load_json(p) if p.exists() else {'districts': []}
    tehsils = [t.strip() for t in (a.tehsils or '').split(',') if t.strip()]
    if not tehsils:
        raise SystemExit('Give the tehsils with --tehsils "A,B,C", spelt exactly as the CoRE Stack API lists them '
                         '(get_active_locations).')
    d = next((x for x in cfg['districts'] if x['district'] == a.district and x['state'] == a.state), None)
    if d is None:
        d = {'state': a.state, 'district': a.district, 'tehsils': []}; cfg['districts'].append(d)
    added = [t for t in tehsils if t not in d['tehsils']]
    d['tehsils'] += added
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(__import__('json').dumps(cfg, indent=1, ensure_ascii=False) + '\n')
    print(f"{a.district}, {a.state}: added {len(added)} tehsil(s) to {p} ({len(d['tehsils'])} in total)")
    if len(d['tehsils']) < 4:
        print('Note: the pilot used districts with at least 4 populated tehsils; fewer tehsils give thinner district summaries.')

def cmd_fetch(a):
    from .fetch import fetch_all
    fetch_all(load_json(a.locations), force=a.force, only=a.only.split(',') if a.only else None)

def cmd_audit(a):
    from .audit import report
    report(load_json(a.locations))

def cmd_validate(a):
    from .validate import validate
    return validate(Path(a.knowledge))

def cmd_run(a):
    cfg = load_json(a.locations); kd = Path(a.knowledge)
    missing = [(s, d, t) for s, d, t in iter_locations(cfg) if not (raw_dir(s, d, t) / 'lulc_vector.json').exists()]
    if missing:
        names = ', '.join(f'{d}/{t}' for _, d, t in missing[:8]) + (' ...' if len(missing) > 8 else '')
        raise SystemExit(f'No cached data for {len(missing)} tehsil(s): {names}\n'
                         f'Run `python -m seft.cli fetch --locations {a.locations}` first.')
    from .pipeline import run
    from .export import write_csv, write_web, _knowledge
    answers = load_json(a.answers) if a.answers else None
    if answers and 'answers' in answers: answers = answers['answers']
    recs, vill, cl, meta = run(cfg, kd, answers=answers)
    for r in recs: r['n_villages'] = len(cl[r['district']].get(r['uid'], []))
    K = _knowledge(kd)
    out = Path(a.out)
    files = write_csv(recs, vill, K, out / 'csv')
    print(f'wrote {len(files)} CSV files to {out / "csv"}')
    if not a.no_web:
        write_web(recs, vill, cl, meta, K, cfg, out / 'web')
        from .webdata import build
        build(out / 'web', ROOT / 'web' / 'data', out / 'csv', merge=a.merge)

def cmd_groundtruth(a):
    from .groundtruth import main as gt
    gt(a.truth, refresh_locations=a.refresh_locations, force=a.force, fetch=not a.no_fetch, pools_from=a.pools,
       sample=not a.no_sample)

def main(argv=None):
    ap = argparse.ArgumentParser(prog='python -m seft.cli', description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    def loc(p): p.add_argument('--locations', default=DEFAULT_LOC, help='locations JSON (default config/locations.json)')
    p = sub.add_parser('add', help='add a district and its tehsils to a locations file'); loc(p)
    p.add_argument('--state', required=True); p.add_argument('--district', required=True); p.add_argument('--tehsils')
    p = sub.add_parser('fetch', help='download API data and geometry'); loc(p)
    p.add_argument('--force', action='store_true', help='re-download datasets already cached')
    p.add_argument('--only', help='comma-separated dataset names to fetch')
    p = sub.add_parser('audit', help='list missing or incomplete datasets'); loc(p)
    p = sub.add_parser('validate', help='check knowledge JSONs'); p.add_argument('--knowledge', default=str(ROOT / 'knowledge'))
    for name in ('run', 'all'):
        p = sub.add_parser(name, help='run the analysis' if name == 'run' else 'fetch + validate + run'); loc(p)
        p.add_argument('--knowledge', default=str(ROOT / 'knowledge')); p.add_argument('--out', default=str(ROOT / 'out'))
        p.add_argument('--answers', help='community answers JSON saved from the atlas')
        p.add_argument('--merge', action='store_true', help='keep atlas districts that this run does not cover')
        p.add_argument('--no-web', action='store_true', help='only write CSV tables')
        if name == 'all':
            p.add_argument('--force', action='store_true'); p.add_argument('--only', help=argparse.SUPPRESS)
    p = sub.add_parser('groundtruth', help='score atlas and sheet rules against ground-truth MWS')
    p.add_argument('--truth', default=str(ROOT / 'config' / 'groundtruth' / 'final_ground_truth.json'))
    p.add_argument('--refresh-locations', action='store_true', help='re-download get_active_locations')
    p.add_argument('--force', action='store_true', help='re-download datasets already cached')
    p.add_argument('--no-fetch', action='store_true', help='use cached data only')
    p.add_argument('--pools', choices=['atlas', 'run'], default='atlas',
                   help="percentile thresholds: the atlas's (default) or pooled over the ground-truth MWS")
    p.add_argument('--no-sample', action='store_true',
                   help='skip firing rates over the atlas sample (computed once per knowledge version, then cached)')
    a = ap.parse_args(argv)
    if a.cmd == 'add': cmd_add(a)
    elif a.cmd == 'fetch': cmd_fetch(a)
    elif a.cmd == 'audit': cmd_audit(a)
    elif a.cmd == 'validate': sys.exit(0 if cmd_validate(a) else 1)
    elif a.cmd == 'run': cmd_run(a)
    elif a.cmd == 'groundtruth': cmd_groundtruth(a)
    elif a.cmd == 'all':
        cmd_fetch(a)
        if not cmd_validate(a): sys.exit(1)
        cmd_run(a)

if __name__ == '__main__':
    main()
