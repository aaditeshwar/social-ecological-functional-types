"""Command line entry point. Run from the repository root.

    python -m seft.cli add --state Maharashtra --district Yavatmal --tehsils "Darwha,Pusad" [--role coverage]
                                       # add a district (and tehsils) to config/locations.json; --role pools,
                                       # groundtruth or coverage (default) says what it is for
    python -m seft.cli fetch           # API data + GeoServer geometry for every location (needs CORE_STACK_API_KEY)
    python -m seft.cli audit           # which datasets are missing or incomplete
    python -m seft.cli validate        # check the knowledge JSONs after editing
    python -m seft.cli refresh-knowledge   # put edited text-only knowledge (interventions, notes) into web/data
    python -m seft.cli cc-build --forms <folder>   # Commons Connect ODK templates -> knowledge/commons_connect.json
    python -m seft.cli rules-xlsx --v1 FILE.xlsx   # site rules -> suitability-rules workbook in out/
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

Waterbody impact (config/impact/locations.json, registries in data/registries/):
    python -m seft.cli impact-build-registry --id atecf_desilting --layers swb_layers.csv [--zoi zoi_layers.csv]
                                       # GeoServer layers of intervened waterbodies -> data/registries/<id>.json,
                                       # tehsils added to the waterbody and impact locations (--role, --scope)
    python -m seft.cli impact-link     # link registry records to atlas waterbodies (after wb-fetch)
    python -m seft.cli impact-run      # effects, verdicts, averages -> out/impact and web/data/waterbody
    python -m seft.cli impact-validate # check knowledge/impact, config/impact and the registries

Common options: --locations FILE (default config/locations.json). For run and wb-run: --answers FILE
(community answers saved from the atlas), --merge (keep districts already in the atlas that this run does not
cover), --update-pools (recompute the percentile pools over the 'pools' districts; otherwise the published
pools in knowledge/pools.json are used).

Location roles (each district in a locations file has 'roles'):
    pools        the sample for the percentile pools (the eight original districts)
    groundtruth  compared with labels: config/groundtruth/locations.json (final_ground_truth.json) for watersheds,
                 the Water Body Census fields (wb-census) for waterbodies
    coverage     extra districts, fetched for the atlas or cached on demand, scored with the published pools
"""
import argparse, sys
from pathlib import Path
from .util import ROOT, load_json, dump_json, raw_dir, iter_locations

DEFAULT_LOC = str(ROOT / 'config' / 'locations.json')
WB_LOC = str(ROOT / 'config' / 'waterbody' / 'locations.json')

def _roles(a):
    from .util import ROLES
    roles = [r.strip() for r in (a.role or 'coverage').split(',') if r.strip()]
    bad = [r for r in roles if r not in ROLES]
    if bad: raise SystemExit(f"Unknown role(s) {', '.join(bad)}; use {', '.join(ROLES)} (comma-separated for several).")
    return roles

def cmd_impact_build(a):
    from .impact.registry import build
    if a.role not in ('reference', 'test', 'coverage'): raise SystemExit('--role is reference, test or coverage')
    build(a.id, a.layers, a.zoi, name=a.name, role=a.role, scope=a.scope, refresh_locations=a.refresh_locations,
          add_locations=not a.no_locations)

def cmd_impact_link(a):
    from .impact import registry as R
    paths = [R.REG_DIR / f'{x}.json' for x in a.registry.split(',')] if a.registry else None
    for doc in R.load_all(paths):
        R.link(doc); R.save(doc, R.REG_DIR / f"{doc['registry']['id']}.json")

def cmd_impact_run(a):
    from .impact.run import main as imain
    if a.finalize_only:
        from .impact.run import finalize_only
        finalize_only(web=not a.no_web); return
    imain(a.registry.split(',') if a.registry else None, link=not a.no_link, web=not a.no_web)

def cmd_add(a):
    roles = _roles(a)
    loc = a.locations
    if roles == ['groundtruth'] and a.cmd == 'add' and loc == DEFAULT_LOC:
        loc = str(ROOT / 'config' / 'groundtruth' / 'locations.json')   # watershed ground-truth tehsils live here
    p = Path(loc)
    cfg = load_json(p) if p.exists() else {'districts': []}
    tehsils = [t.strip() for t in (a.tehsils or '').split(',') if t.strip()]
    if not tehsils:
        raise SystemExit('Give the tehsils with --tehsils "A,B,C", spelt exactly as the CoRE Stack API lists them '
                         '(get_active_locations).')
    d = next((x for x in cfg['districts'] if x['district'] == a.district and x['state'] == a.state), None)
    if d is None:
        d = {'state': a.state, 'district': a.district, 'tehsils': [], 'roles': []}; cfg['districts'].append(d)
    added = [t for t in tehsils if t not in d['tehsils']]
    d['tehsils'] += added
    old = d.get('roles') or []
    new = set(old) | set(roles)
    if new - {'coverage'}: new.discard('coverage')     # a pools or ground-truth district is no longer only coverage
    d['roles'] = [r for r in ('pools', 'groundtruth', 'coverage') if r in new]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(__import__('json').dumps(cfg, indent=1, ensure_ascii=False) + '\n')
    print(f"{a.district}, {a.state}: added {len(added)} tehsil(s) to {p} ({len(d['tehsils'])} in total); roles: {', '.join(d['roles'])}")
    if 'pools' in d['roles'] and 'pools' not in old:
        run = 'wb-run' if a.cmd == 'wb-add' else 'run'
        print(f"This district is now part of the pools sample: after fetching, `python -m seft.cli {run} --update-pools` "
              f"recomputes the percentile pools (thresholds change for every district).")
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
    from .util import with_role, pools_doc, write_pools
    import datetime
    pub = pools_doc().get('mws')
    pool_d = {(d['state'], d['district']) for d in with_role(cfg, 'pools')['districts']}
    if a.update_pools or not pub:
        if not pool_d: raise SystemExit("No district in the locations file has the 'pools' role.")
        print(f"pooling the signal thresholds over the 'pools' districts: {', '.join(d for _, d in sorted(pool_d))}")
        recs, vill, cl, meta = run(cfg, kd, answers=answers, pool_filter=lambda r: (r['state'], r['district']) in pool_d)
        write_pools('mws', meta['pools'], {'districts': [d for _, d in sorted(pool_d)],
                    'n_mws': sum(1 for r in recs if (r['state'], r['district']) in pool_d),
                    'computed': f'{datetime.date.today()}, run --update-pools'})
        print('wrote the MWS pools to knowledge/pools.json (bump knowledge/manifest.json before releasing a pack)')
        if a.merge: print('Note: districts kept from the atlas by --merge were scored with the previous pools; '
                          'run them again (or run every district without --merge) so that all use the new pools.')
    else:
        print('scoring with the published pools (knowledge/pools.json); --update-pools to recompute them')
        recs, vill, cl, meta = run(cfg, kd, answers=answers, pools=pub)
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
    wb_run(a.locations, a.out, merge=a.merge, web=not a.no_web, update_pools=a.update_pools)

def cmd_wb_census(a):
    from .wb.census import main as wb_census
    wb_census(a.locations, a.out, all_districts=a.all)

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
    ROLE_HELP = ("what the district is for: pools (sample for the percentile pools), groundtruth (compared with labels: "
                 "final_ground_truth.json for watersheds, the Water Body Census for waterbodies), coverage (extra districts, "
                 "scored with the published pools; the default). Comma-separated for several.")
    p = sub.add_parser('add', help='add a district and its tehsils to a locations file'); loc(p)
    p.add_argument('--state', required=True); p.add_argument('--district', required=True); p.add_argument('--tehsils')
    p.add_argument('--role', help=ROLE_HELP + ' --role groundtruth alone writes to config/groundtruth/locations.json.')
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
        p.add_argument('--update-pools', action='store_true',
                       help="recompute the percentile pools over the 'pools' districts (all must be in this run) and write "
                            "knowledge/pools.json; without it the published pools are used")
        p.add_argument('--no-web', action='store_true', help='only write CSV tables')
        if name == 'all':
            p.add_argument('--force', action='store_true'); p.add_argument('--only', help=argparse.SUPPRESS)
    # waterbody atlas: same operations, on config/waterbody/locations.json
    def wloc(p): p.add_argument('--locations', default=WB_LOC, help='locations JSON (default config/waterbody/locations.json)')
    p = sub.add_parser('wb-add', help='add a district and its tehsils to the waterbody locations'); wloc(p)
    p.add_argument('--state', required=True); p.add_argument('--district', required=True); p.add_argument('--tehsils')
    p.add_argument('--role', help=ROLE_HELP)
    p = sub.add_parser('wb-fetch', help='download API data and the GeoServer waterbody layers'); wloc(p)
    p.add_argument('--force', action='store_true', help='re-download what is already cached')
    p = sub.add_parser('wb-audit', help='list missing layers and datasets for the waterbody atlas'); wloc(p)
    p = sub.add_parser('wb-validate', help='check the waterbody knowledge JSONs')
    for name in ('wb-run', 'wb-all'):
        p = sub.add_parser(name, help='waterbody atlas: build, score -> out/waterbody and web/data/waterbody' if name == 'wb-run'
                           else 'wb-fetch + wb-validate + wb-run'); wloc(p)
        p.add_argument('--out', default=str(ROOT / 'out' / 'waterbody'))
        p.add_argument('--merge', action='store_true', help='keep atlas districts that this run does not cover')
        p.add_argument('--update-pools', action='store_true',
                       help="recompute the waterbody pools over the 'pools' districts and write knowledge/pools.json")
        p.add_argument('--no-web', action='store_true', help='only write CSV tables and out/waterbody/web')
        if name == 'wb-all': p.add_argument('--force', action='store_true')
    p = sub.add_parser('wb-census', help='compare waterbody patterns with the Water Body Census fields -> out/waterbody/census'); wloc(p)
    p.add_argument('--out', default=str(ROOT / 'out' / 'waterbody' / 'census'))
    p.add_argument('--all', action='store_true', help="compare every district of the locations file, not only the 'groundtruth' ones")
    p = sub.add_parser('cc-build', help='structured Commons Connect forms from the ODK templates -> knowledge/commons_connect.json')
    p.add_argument('--forms', required=True, help='folder with the Commons Connect .xlsx templates')
    p = sub.add_parser('rules-xlsx', help='site rules of the interventions -> the suitability-rules workbook layout')
    p.add_argument('--v1', required=True, help='a WaterStructure_Suitability_Rules.xlsx giving the structures, parameters and layout')
    p.add_argument('--out', default=str(ROOT / 'out' / 'WaterStructure_Suitability_Rules_v2.xlsx'))
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
    p = sub.add_parser('impact-build-registry', help='intervention registry from GeoServer layer lists -> data/registries/<id>.json')
    p.add_argument('--id', required=True, help='registry id, e.g. atecf_desilting')
    p.add_argument('--layers', required=True, help='CSV of the intervened-waterbody layers (columns layer, wfs_geojson_url)')
    p.add_argument('--zoi', help='CSV of their zone-of-influence layers (same columns)')
    p.add_argument('--name', help='display name of the registry')
    p.add_argument('--role', default='coverage', help='role of the new districts in config/impact/locations.json: reference, test or coverage')
    p.add_argument('--scope', choices=['tehsil', 'district'], default='tehsil', help='add the tehsils with records (default) or whole districts')
    p.add_argument('--refresh-locations', action='store_true', help='re-download get_active_locations before resolving names')
    p.add_argument('--no-locations', action='store_true', help='do not add tehsils to the locations files')
    p = sub.add_parser('impact-link', help='link registry records to atlas waterbodies (after wb-fetch)')
    p.add_argument('--registry', help='comma-separated registry ids (default: all in data/registries)')
    p = sub.add_parser('impact-run', help='impact of every registered intervention -> out/impact, web/data/waterbody')
    p.add_argument('--registry', help='comma-separated registry ids (default: all in data/registries)')
    p.add_argument('--no-link', action='store_true', help='use the links already in the registries')
    p.add_argument('--no-web', action='store_true', help='do not copy bundles to web/data/waterbody')
    p.add_argument('--finalize-only', action='store_true', help='rebuild verdicts, notes and averages from out/impact/records.json without re-estimating')
    sub.add_parser('impact-validate', help='check knowledge/impact, config/impact and the registries')
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
    elif a.cmd == 'impact-build-registry': cmd_impact_build(a)
    elif a.cmd == 'impact-link': cmd_impact_link(a)
    elif a.cmd == 'impact-run': cmd_impact_run(a)
    elif a.cmd == 'impact-validate':
        from .impact.validate import main as iv; sys.exit(0 if iv() else 1)
    elif a.cmd == 'cc-build':
        from .commons_connect import build; build(a.forms)
    elif a.cmd == 'rules-xlsx':
        from .rules_xlsx import main as rx; rx(a.v1, a.out)
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
