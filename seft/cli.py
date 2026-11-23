"""Command line entry point. Run from the repository root.

    python -m seft.cli add --state Maharashtra --district Yavatmal --tehsils "Darwha,Pusad"
                                       # add a district (and tehsils) to config/locations.json
    python -m seft.cli fetch           # API data + GeoServer geometry for every location (needs CORE_STACK_API_KEY)
    python -m seft.cli audit           # which datasets are missing or incomplete
    python -m seft.cli validate        # check the knowledge JSONs after editing
    python -m seft.cli refresh-knowledge   # put edited text-only knowledge (interventions, notes) into web/data
    python -m seft.cli cc-build --forms <folder>   # Commons Connect ODK templates -> knowledge/commons_connect.json
    python -m seft.cli priority [--district pune]  # must-ask scores of the community questions -> out/priority
    python -m seft.cli run             # indicators, systems, stresses, schemes -> out/csv, out/web and web/data
    python -m seft.cli all             # fetch, validate and run in one go
    python -m seft.cli groundtruth --truth FILE
                                       # fetch ground-truth tehsils, score atlas and sheet rules, write
                                       # confusion matrices to out/groundtruth/

Waterbody atlas (same operations, on config/waterbody/locations.json):
    python -m seft.cli wb-add --state ... --district ... --tehsils "..."
    python -m seft.cli wb-fetch        # API data (as fetch) + GeoServer waterbody and zone-of-influence layers
    python -m seft.cli wb-audit        # missing layers and datasets
    python -m seft.cli wb-validate     # check knowledge/waterbody/*.json
    python -m seft.cli wb-run          # -> out/waterbody/csv/wb_<district>.csv, out/waterbody/web, web/data/waterbody
    python -m seft.cli wb-all          # wb-fetch, wb-validate and wb-run
    python -m seft.cli wb-census       # compare with the Water Body Census fields -> out/waterbody/census/
    python -m seft.cli wb-assess --answers community_answers.json   # re-assess with answers saved from the page

Common options: --locations FILE (default config/locations.json). For run: --answers FILE (community
answers saved from the atlas), --merge (keep districts already in the atlas that this run does not cover).
"""
import argparse, sys
from pathlib import Path
from .util import ROOT, load_json, dump_json, raw_dir, iter_locations

DEFAULT_LOC = str(ROOT / 'config' / 'locations.json')
WB_LOC = str(ROOT / 'config' / 'waterbody' / 'locations.json')

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

def cmd_wb_fetch(a):
    from .wb.layers import fetch_all_layers
    fetch_all_layers(load_json(a.locations), force=a.force)

def cmd_wb_audit(a):
    from .wb.audit import report
    report(load_json(a.locations))

def cmd_wb_validate(a):
    from .wb.validate import validate
    return validate()

def cmd_wb_run(a):
    from .wb.run import main as wb_run
    wb_run(a.locations, a.out, merge=a.merge, web=not a.no_web)

def cmd_wb_census(a):
    from .wb.census import main as wb_census
    wb_census(a.locations, a.out)

def cmd_refresh_knowledge(a):
    from .webdata import refresh_knowledge
    refresh_knowledge()

def cmd_wb_assess(a):
    from .wb.assess import main as wb_assess
    wb_assess(a.answers, a.locations, a.out)

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
    # waterbody atlas: same operations, on config/waterbody/locations.json
    def wloc(p): p.add_argument('--locations', default=WB_LOC, help='locations JSON (default config/waterbody/locations.json)')
    p = sub.add_parser('wb-add', help='add a district and its tehsils to the waterbody locations'); wloc(p)
    p.add_argument('--state', required=True); p.add_argument('--district', required=True); p.add_argument('--tehsils')
    p = sub.add_parser('wb-fetch', help='download API data and the GeoServer waterbody layers'); wloc(p)
    p.add_argument('--force', action='store_true', help='re-download what is already cached')
    p = sub.add_parser('wb-audit', help='list missing layers and datasets for the waterbody atlas'); wloc(p)
    p = sub.add_parser('wb-validate', help='check the waterbody knowledge JSONs')
    for name in ('wb-run', 'wb-all'):
        p = sub.add_parser(name, help='waterbody atlas: build, score -> out/waterbody and web/data/waterbody' if name == 'wb-run'
                           else 'wb-fetch + wb-validate + wb-run'); wloc(p)
        p.add_argument('--out', default=str(ROOT / 'out' / 'waterbody'))
        p.add_argument('--merge', action='store_true', help='keep atlas districts that this run does not cover')
        p.add_argument('--no-web', action='store_true', help='only write CSV tables and out/waterbody/web')
        if name == 'wb-all': p.add_argument('--force', action='store_true')
    p = sub.add_parser('wb-census', help='compare waterbody patterns with the Water Body Census fields -> out/waterbody/census'); wloc(p)
    p.add_argument('--out', default=str(ROOT / 'out' / 'waterbody' / 'census'))
    p = sub.add_parser('cc-build', help='structured Commons Connect forms from the ODK templates -> knowledge/commons_connect.json')
    p.add_argument('--forms', required=True, help='folder with the Commons Connect .xlsx templates')
    p = sub.add_parser('priority', help='must-ask scores of the atlas and Commons Connect questions, by MWS -> out/priority')
    p.add_argument('--district', action='append', help='district slug (repeatable); default all in web/data')
    sub.add_parser('refresh-knowledge', help='put the current knowledge files (e.g. interventions) into web/data without re-scoring')
    p = sub.add_parser('wb-assess', help='re-assess waterbodies with community answers saved from the page -> out/waterbody/answers'); wloc(p)
    p.add_argument('--answers', required=True, help='community answers JSON saved from the waterbody atlas')
    p.add_argument('--out', default=str(ROOT / 'out' / 'waterbody' / 'answers'))
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
    elif a.cmd == 'wb-add': cmd_add(a)
    elif a.cmd == 'wb-fetch': cmd_wb_fetch(a)
    elif a.cmd == 'wb-audit': cmd_wb_audit(a)
    elif a.cmd == 'wb-validate': sys.exit(0 if cmd_wb_validate(a) else 1)
    elif a.cmd == 'wb-run': cmd_wb_run(a)
    elif a.cmd == 'wb-census': cmd_wb_census(a)
    elif a.cmd == 'wb-assess': cmd_wb_assess(a)
    elif a.cmd == 'refresh-knowledge': cmd_refresh_knowledge(a)
    elif a.cmd == 'cc-build':
        from .commons_connect import build; build(a.forms)
    elif a.cmd == 'priority':
        from .priority import main as pmain; pmain(a.district)
    elif a.cmd == 'wb-all':
        cmd_wb_fetch(a)
        if not cmd_wb_validate(a): sys.exit(1)
        cmd_wb_run(a)
    elif a.cmd == 'all':
        cmd_fetch(a)
        if not cmd_validate(a): sys.exit(1)
        cmd_run(a)

if __name__ == '__main__':
    main()
