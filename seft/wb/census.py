"""`python -m seft.cli wb-census`: compare waterbody patterns with the Water Body Census fields, as
`groundtruth` compares the watershed rules with labels.

CoRE Stack matched census points to its waterbodies by proximity and by capacity against area, so the fields
may not be accurate, and they describe the census reference year (2017-18). They are never inputs to the
atlas; this check only shows whether the atlas's patterns lean the way the census does.

Writes out/waterbody/census/:
  report.md       the comparisons as tables, with the caveats
  detail.csv      one row per waterbody with census fields: atlas type, roles, rule statuses and census fields
  comparison.json the same numbers as the report, for scripts
"""
import collections, csv, gzip, json, statistics as st
from pathlib import Path
from ..util import ROOT, load_json, raw_dir, iter_locations
from .run import score_all

OUT = ROOT / 'out' / 'waterbody' / 'census'
CENSUS_FIELDS = ['ref_water_body_type_id_name', 'water_body_nature_name', 'water_body_ownership_name',
                 'ref_water_body_in_use_id_name', 'ref_reason_water_body_in_use_id1_name', 'reason_water_body_in_use_name2',
                 'reason_water_body_in_use_name3', 'scheme_status_reason_name', 'filled_up_storage_name',
                 'filled_up_storage_space_name', 'storage_capacity_water_body_original', 'storage_capacity_water_body_present',
                 'ref_water_body_under_repair_renovation_restoration_id_name', 'ref_selection_id_water_body_encroached_name',
                 'ref_selection_id_wua_exists_name', 'renovation_year', 'construcion_year']
USES = ('ref_reason_water_body_in_use_id1_name', 'reason_water_body_in_use_name2', 'reason_water_body_in_use_name3')

def _tf(x): return {'True': True, '1.0': True, 'False': False, '0.0': False}.get(x)
def _num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

def census_fields(cfg):
    C = {}
    for s, d, t in iter_locations(cfg):
        p = raw_dir(s, d, t) / 'swb_layers.json.gz'
        if not p.exists(): continue
        with gzip.open(p, 'rt', encoding='utf-8') as f:
            for w in json.load(f)['waterbodies']:
                if w.get('census_id') not in (None, 'NA'): C[str(w.get('UID', w.get('wb_id')))] = w
    return C

def _uses(c): return {c.get(u) for u in USES} - {None}

def _rate(rows, rid):
    a = [b for b, _ in rows if b['rules'].get(rid, {}).get('status') in ('triggered', 'not triggered')]
    return [len(a), round(100 * sum(b['rules'][rid]['status'] == 'triggered' for b in a) / len(a)) if a else None]

def compare(J, K):
    R = {}
    def contrast(name, field, test, rules):
        groups = {}
        for lab, fn in test:
            rows = [(b, c) for b, c in J if fn(c)]
            groups[lab] = {'n': len(rows), **{rid: _rate(rows, rid) for rid in rules}}
        R[name] = {'field': field, 'groups': groups}
    contrast('how_full', 'filled_up_storage_name',
             [(k, (lambda k: lambda c: c.get('filled_up_storage_name') == k)(k)) for k in ('Full', 'Upto 3/4', 'Upto 1/2', 'Upto 1/4', 'Nil/Negligible filled up')],
             ['wb.inflow_shortfall'])
    for lab in ('Full', 'Upto 3/4', 'Upto 1/2', 'Upto 1/4', 'Nil/Negligible filled up'):
        kf = [b['vars']['k_fill'] for b, c in J if c.get('filled_up_storage_name') == lab and isinstance(b['vars'].get('k_fill'), (int, float))]
        R['how_full']['groups'][lab]['median_fill'] = round(st.median(kf)) if kf else None
    contrast('fill_frequency', 'filled_up_storage_space_name',
             [(k, (lambda k: lambda c: c.get('filled_up_storage_space_name') == k)(k)) for k in ('Filled up every year', 'Usually filled up', 'Rarely filled up', 'Never filled up')],
             ['wb.inflow_shortfall', 'wb.drought_failure'])
    contrast('in_use', 'ref_water_body_in_use_id_name',
             [('in use', lambda c: _tf(c.get('ref_water_body_in_use_id_name')) is True), ('not in use', lambda c: _tf(c.get('ref_water_body_in_use_id_name')) is False)],
             ['wb.siltation', 'wb.inflow_shortfall', 'wb.sudden_loss'])
    contrast('encroached', 'ref_selection_id_water_body_encroached_name',
             [('encroached', lambda c: _tf(c.get('ref_selection_id_water_body_encroached_name')) is True), ('not encroached', lambda c: _tf(c.get('ref_selection_id_water_body_encroached_name')) is False)],
             ['wb.siltation'])
    contrast('under_repair', 'ref_water_body_under_repair_renovation_restoration_id_name',
             [('under repair', lambda c: _tf(c.get('ref_water_body_under_repair_renovation_restoration_id_name')) is True), ('not under repair', lambda c: _tf(c.get('ref_water_body_under_repair_renovation_restoration_id_name')) is False)],
             ['wb.sudden_loss'])
    def ratio(c):
        o, p = _num(c.get('storage_capacity_water_body_original')), _num(c.get('storage_capacity_water_body_present'))
        return p / o if (o and p is not None and o > 0 and p <= 1.5 * o) else None
    contrast('storage_loss', 'storage present / original',
             [('below 80%', lambda c: ratio(c) is not None and ratio(c) < 0.8), ('80% or more', lambda c: ratio(c) is not None and ratio(c) >= 0.8)],
             ['wb.inflow_shortfall', 'wb.siltation'])
    contrast('wua', 'ref_selection_id_wua_exists_name',
             [(k, (lambda k: lambda c: c.get('ref_selection_id_wua_exists_name') == k)(k)) for k in ('Yes', 'No', 'Not Known')],
             ['wb.irrigation_underuse'])
    contrast('pisciculture', 'use: Pisciculture',
             [('pisciculture', lambda c: 'Pisciculture' in _uses(c)), ('other uses', lambda c: 'Pisciculture' not in _uses(c))],
             ['wb.fishery_opportunity'])
    roles = [r['id'] for r in K['roles']['roles']]
    R['use_vs_roles'] = {}
    for u in ('Irrigation', 'Pisciculture', 'Ground water recharge', 'Domestic/Drinking'):
        yes = [b for b, c in J if u in _uses(c)]; no = [b for b, c in J if u not in _uses(c)]
        R['use_vs_roles'][u] = {'n': len(yes), **{r: [round(st.mean(b['roles'][r] for b in yes), 2) if yes else None,
                                                         round(st.mean(b['roles'][r] for b in no), 2) if no else None] for r in roles}}
    ct = collections.defaultdict(collections.Counter)
    for b, c in J: ct[c.get('ref_water_body_type_id_name') or 'unknown'][b['type']] += 1
    R['type'] = {k: dict(v.most_common()) for k, v in ct.items()}
    return R

def _report(R, n, K):
    lab = {r['id']: r['label'] for r in K['rules']['rules']}
    L = ['# Waterbody patterns against the Water Body Census', '',
         f'{n} in-scope waterbodies have census fields matched by CoRE Stack. The match is by proximity and by '
         'capacity against area, so it may be wrong for some waterbodies (WB-07 in docs/core_stack_waterbody_api_issues.md), '
         'and the census describes 2017-18: it can check the state at the start of the series and the uses, not '
         'changes after 2019. Census fields are not inputs to the atlas.', '',
         'Cells give the share of waterbodies where the rule fires, among those it applies to (n in brackets).', '']
    titles = {'how_full': 'How full it gets', 'fill_frequency': 'How often it fills', 'in_use': 'In use',
              'encroached': 'Encroached', 'under_repair': 'Under repair', 'storage_loss': 'Present storage against original',
              'wua': 'Water user association', 'pisciculture': 'Used for pisciculture'}
    for key, title in titles.items():
        g = R[key]['groups']; rules = [k for k in next(iter(g.values())) if k.startswith('wb.')]
        extra = ['median_fill'] if key == 'how_full' else []
        L += [f'## {title} (`{R[key]["field"]}`)', '',
              '| Census | n | ' + ' | '.join(['Median kharif fill'] * bool(extra) + [lab[r] for r in rules]) + ' |',
              '|---|---|' + '---|' * (len(rules) + len(extra))]
        for k, v in g.items():
            cells = ([f"{v['median_fill']}%" if v.get('median_fill') is not None else '–'] if extra else []) + \
                    [f"{v[r][1]}% ({v[r][0]})" if v[r][1] is not None else '–' for r in rules]
            L.append(f"| {k} | {v['n']} | " + ' | '.join(cells) + ' |')
        L.append('')
    roles = [r['id'] for r in K['roles']['roles']]; rl = {r['id']: r['label'] for r in K['roles']['roles']}
    L += ['## Census uses against atlas roles', '', 'Mean role weight where the census lists the use, against where it does not.', '',
          '| Use | n | ' + ' | '.join(rl[r] for r in roles) + ' |', '|---|---|' + '---|' * len(roles)]
    for u, v in R['use_vs_roles'].items():
        L.append(f"| {u} | {v['n']} | " + ' | '.join(f"{v[r][0]} vs {v[r][1]}" for r in roles) + ' |')
    types = [t['id'] for t in K['types']['types'] if t['in_scope']]
    L += ['', '## Census type against atlas type', '', '| Census type | ' + ' | '.join(types) + ' |', '|---|' + '---|' * len(types)]
    for k, v in sorted(R['type'].items(), key=lambda x: -sum(x[1].values())):
        n = sum(v.values()); L.append(f'| {k} ({n}) | ' + ' | '.join(f"{round(100 * v.get(t, 0) / n)}%" for t in types) + ' |')
    L += ['', 'Tuning decisions taken from this check are listed in docs/waterbody_census_comparison.md.', '']
    return '\n'.join(L)

def main(cfg_path=None, out=None, all_districts=False, log=print):
    """Compares the 'groundtruth' districts of the waterbody locations file (all districts with all_districts),
    scored with the published waterbody pools."""
    from ..util import with_role, pools_doc
    cfg = load_json(cfg_path or ROOT / 'config' / 'waterbody' / 'locations.json')
    if not all_districts:
        cfg = with_role(cfg, 'groundtruth')
        if not cfg['districts']: raise SystemExit("No district has the 'groundtruth' role; use --all or wb-add --role groundtruth.")
    log('  census comparison over: ' + ', '.join(d['district'] for d in cfg['districts']))
    pub = pools_doc().get('waterbody')
    B, stats, types, K, pools = score_all(cfg, log=log, pools={k: {t: tuple(x) for t, x in v.items()} for k, v in pub.items()} if pub else None)
    K['types'] = types
    scope = {t['id'] for t in types['types'] if t['in_scope']}
    C = census_fields(cfg)
    J = []
    for b in B:
        if b['type'] not in scope: continue
        cs = [C[str(i)] for i in b['fragment_ids'] if str(i) in C]
        if cs: J.append((b, cs[0]))
    R = compare(J, K)
    out = Path(out or OUT); out.mkdir(parents=True, exist_ok=True)
    (out / 'comparison.json').write_text(json.dumps({'n': len(J), **R}, indent=1))
    (out / 'report.md').write_text(_report(R, len(J), K), encoding='utf-8')
    with open(out / 'detail.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        rids = [r['id'] for r in K['rules']['rules']]; roles = [r['id'] for r in K['roles']['roles']]
        w.writerow(['wb_id', 'district', 'tehsil', 'type', 'area_ha'] + roles + rids + CENSUS_FIELDS)
        for b, c in J:
            w.writerow([b['wb_id'], b['district'], b['tehsil'], b['type'], b['area_ha']] + [b['roles'].get(r) for r in roles] +
                       [b['rules'][r]['status'] for r in rids] + [c.get(k) for k in CENSUS_FIELDS])
    log(f'{len(J)} waterbodies with census fields; wrote {out / "report.md"}, detail.csv, comparison.json')
