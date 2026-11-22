"""What-if tests of candidate atlas rule changes against the ground truth, without changing the rules.

    python tools/groundtruth_whatif.py            # uses the cache from the last run, or builds it
    python tools/groundtruth_whatif.py --rebuild  # re-score the ground-truth and sample MWS first

Each candidate is an expression over the atlas variables and signals (signal ids are true/false, `<id>_g`
the grade) and the sheet's signals (`sh_<pattern>_<sig>`, 0/1, and `sh_<pattern>` for its trigger), so that
parts of a sheet pattern can be tried inside an atlas-style rule. It is scored on the ground-truth labels and on the share of the 4,598 atlas sample MWS where it
would fire. Results feed config/groundtruth/suggestions.md. Edit CANDIDATES to try other ideas.
"""
import sys, math, pickle, collections, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from seft import groundtruth as gt
from seft.util import load_json
from seft.expr import evaluate, NAN
CACHE = ROOT / 'out' / 'groundtruth' / 'whatif_cache.pkl'

def build():
    from seft.pipeline import run
    from seft.sheet import load_sheet_rules, evaluate_sheet
    SR = load_sheet_rules()
    items = gt.flatten(load_json(gt.GT_DIR / 'final_ground_truth.json'))
    pools = load_json(ROOT / 'web' / 'data' / 'index.json')['pools']
    want = {i['uid'] for i in items}
    G, _, _, _ = run(load_json(gt.GT_DIR / 'locations.json'), log=lambda *a: None, pools=pools, keep=lambda r: r['uid'] in want)
    S, _, _, _ = run(load_json(ROOT / 'config' / 'locations.json'), log=lambda *a: None, pools=pools)
    def slim(r):
        e = {k: v for k, v in r['env'].items() if isinstance(v, (int, float, str)) and not isinstance(v, bool)}
        for k, s in r['signals'].items():
            e[k] = NAN if s['on'] is None else s['on']; e[k + '_g'] = NAN if s['grade'] is None else s['grade']
        for pid, res in evaluate_sheet(r['env'], SR).items():
            e[f'sh_{pid}'] = {'triggered': 1, 'not triggered': 0}.get(res['status'], NAN)
            for sg, v in res['signals'].items(): e[f'sh_{pid}_{sg}'] = NAN if v is None else v
        return {'uid': r['uid'], 'env': e}
    D = {'gt': [slim(r) for r in G], 'sample': [slim(r) for r in S], 'items': items}
    CACHE.parent.mkdir(parents=True, exist_ok=True); pickle.dump(D, open(CACHE, 'wb'))
    return D

CG = {r['id']: r for r in json.load(open(ROOT / 'knowledge' / 'causal_graph.json'))['stresses']}
def cur(*ids, gate=True):
    return ' or '.join(f"(({CG[i]['systems']}) and ({CG[i]['trigger']}))" if gate else f"({CG[i]['trigger']})" for i in ids)

# status: adopted (now in force), previous (the rule before an adopted change), declined, open (not decided)
CANDIDATES = [
 ('agriculture.drought', 'previous rule (drought weeks or years only)', lambda: "(sys_rainfed_or_tank and (s_drought_weeks or s_drought_years)) or (" + CG['drought.unstable_sowing']['systems'] + " and (" + CG['drought.unstable_sowing']['trigger'] + "))", 'previous'),
 ('agriculture.drought', 'weeks or years or (dry spells and semi-arid)', lambda: "(sys_rainfed_or_tank and (s_drought_weeks or s_drought_years or (s_dry_spells and ctx_semi_arid))) or (" + CG['drought.unstable_sowing']['systems'] + " and (" + CG['drought.unstable_sowing']['trigger'] + "))", 'adopted 21 Nov, revised 22 Nov'),
 ('agriculture.drought', 'as above, and 2 of 3 rainfall-limited contexts', lambda: "(sys_rainfed_or_tank and (s_drought_weeks or s_drought_years or (s_dry_spells and ctx_semi_arid)) and ntrue(ctx_low_kharif_rain, ctx_runoff_loss, ctx_dry_year) >= 2) or (sys_rainfed and (s_kharif_min or s_kharif_cv))", 'adopted 22 Nov, revised 22 Nov'),
 ('agriculture.drought', 'as above, unstable sowing also in the rainfall-limited setting', lambda: "(sys_rainfed_or_tank and (s_drought_weeks or s_drought_years or (s_dry_spells and ctx_semi_arid)) and ntrue(ctx_low_kharif_rain, ctx_runoff_loss, ctx_dry_year) >= 2) or (sys_rainfed and (s_kharif_min or s_kharif_cv) and ntrue(ctx_low_kharif_rain, ctx_runoff_loss, ctx_dry_year) >= 2)", 'adopted 22 Nov, revised 22 Nov'),
 ('agriculture.drought', 'as above, plus the worst-season signal (>= 6 weeks)', lambda: "(sys_rainfed_or_tank and (s_drought_weeks or s_drought_years or s_drought_worst or (s_dry_spells and ctx_semi_arid)) and ntrue(ctx_low_kharif_rain, ctx_runoff_loss, ctx_dry_year) >= 2) or (sys_rainfed and (s_kharif_min or s_kharif_cv) and ntrue(ctx_low_kharif_rain, ctx_runoff_loss, ctx_dry_year) >= 2)", 'adopted 22 Nov, revised 22 Nov'),
 ('agriculture.drought', 'as above, kharif drought gated on cropland >= 10% (sys_cropland)', lambda: cur('drought.kharif_drought', 'drought.unstable_sowing'), 'adopted 22 Nov'),
 ('agriculture.drought', 'drop unstable sowing from the drought group', lambda: "sys_rainfed_or_tank and (s_drought_weeks or s_drought_years or (s_dry_spells and ctx_semi_arid))", 'declined'),
 ('agriculture.drought', 'dry spells also trigger anywhere (gated)', lambda: "sys_rainfed_or_tank and (s_drought_weeks or s_drought_years or s_dry_spells)", 'not adopted'),
 ('agriculture.drought', 'in force, dry spells count in any climate (with the rainfall setting)', lambda: "(sys_cropland and (s_drought_weeks or s_drought_years or s_drought_worst or s_dry_spells) and ntrue(ctx_low_kharif_rain, ctx_runoff_loss, ctx_dry_year) >= 2) or (" + CG['drought.unstable_sowing']['systems'] + " and (" + CG['drought.unstable_sowing']['trigger'] + "))", 'tested 22 Nov'),
 ('agriculture.drought', 'drought or dry spells, semi-arid only (gated)', lambda: "sys_rainfed_or_tank and (s_drought_weeks or s_drought_years or s_dry_spells) and ctx_semi_arid", 'superseded'),
 ('agriculture.low_yield', 'previous rule (both declines, or one severe)', lambda: "(sys_cropland and s_farm_to_scrub) or (sys_cropland and ((s_ci_decline and s_crop_area_decline) or s_ci_decline_g >= 1 or s_crop_area_decline_g >= 1))", 'previous'),
 ('agriculture.low_yield', 'CI decline or cropped-area decline (abandonment counted)', lambda: "(sys_cropland and s_farm_to_scrub) or (sys_cropland and (s_ci_decline or s_crop_area_decline))", 'adopted 21 Nov, revised 22 Nov'),
 ('agriculture.low_yield', 'as above, only in under-sown or single-season regimes', lambda: "sys_cropland and (s_farm_to_scrub or s_ci_decline or s_crop_area_decline) and (ctx_under_sown or ctx_single_season)", 'adopted 22 Nov, revised 22 Nov'),
 ('agriculture.low_yield', 'as above, plus any fall in CI, first two to last two years (s_ci_fell)', lambda: cur('productivity.farmland_abandonment', 'productivity.declining_intensity'), 'adopted 22 Nov'),
 ('agriculture.low_yield', 'CI decline or cropped-area decline (abandonment not counted)', lambda: "sys_cropland and (s_ci_decline or s_crop_area_decline)", 'not adopted'),
 ('agriculture.low_yield', 'in force, abandonment not counted', lambda: "sys_cropland and (s_ci_decline or s_ci_fell or s_crop_area_decline) and (ctx_under_sown or ctx_single_season)", 'tested 22 Nov'),
 ('agriculture.low_yield', 'in force, CI decline at -0.01 a year', lambda: "sys_cropland and (s_farm_to_scrub or ci_slope <= -0.01 or s_ci_fell or s_crop_area_decline) and (ctx_under_sown or ctx_single_season)", 'tested 22 Nov'),
 ('agriculture.low_yield', 'in force, cropped-area decline not counted', lambda: "sys_cropland and (s_farm_to_scrub or s_ci_decline or s_ci_fell) and (ctx_under_sown or ctx_single_season)", 'tested 22 Nov'),
 ('agriculture.low_yield', 'in force, context also SOGE stressed with dry spells (sheet sig_04)', lambda: "sys_cropland and (s_farm_to_scrub or s_ci_decline or s_ci_fell or s_crop_area_decline) and (ctx_under_sown or ctx_single_season or (s_soge_stage and s_dry_spells))", 'tested 22 Nov'),
 ('agriculture.low_yield', 'in force, or little second-season cropping (triple < 2%, kharif-only < 10%) in context (sheet sig_03)', lambda: cur('productivity.farmland_abandonment', 'productivity.declining_intensity') + " or (sys_cropland and div(triple_ha, area) < 0.02 and div(single_kharif_ha, area) < 0.10 and (ctx_under_sown or ctx_single_season))", 'tested 22 Nov'),
 ('agriculture.soil_degradation', 'previous rule (2 of N < 280, P < 10, K < 110, OC < 0.5)', lambda: "(sys_cropland and ntrue(s_n_low, s_p_low, s_k_low, s_oc_low) >= 2) or (" + CG['soil.erosion']['systems'] + " and (" + CG['soil.erosion']['trigger'] + "))", 'previous'),
 ('agriculture.soil_degradation', 'medium-range P and K, very low N (2 of 4)', lambda: "(sys_cropland and ntrue(s_n_very_low, s_p_medium, s_k_medium, soil_oc_low_frac >= 0.5) >= 2) or (" + CG['soil.erosion']['systems'] + " and (" + CG['soil.erosion']['trigger'] + "))", 'adopted 22 Nov, revised 22 Nov'),
 ('agriculture.soil_degradation', 'as above, OC counted over >= 80% of cropland', lambda: cur('soil.nutrient_deficiency', 'soil.erosion'), 'adopted 22 Nov'),
 ('agriculture.soil_degradation', 'old cut-offs, nitrogen not counted (2 of P < 10, K < 110, OC)', lambda: "sys_cropland and (ntrue(s_p_low, s_k_low, s_oc_low) >= 2 or (ctx_sloping and s_runoff_high and s_cultivated))", 'superseded'),
 ('agriculture.soil_degradation', 'in force, erosion without the runoff condition', lambda: "(sys_cropland and (" + CG['soil.nutrient_deficiency']['trigger'] + ")) or (sys_cropland and ctx_sloping and s_cultivated)", 'tested 22 Nov'),
 ('agriculture.soil_degradation', 'in force, at least one deficient nutrient is OC or very-low N', lambda: "(sys_cropland and ntrue(s_n_very_low, s_p_medium, s_k_medium, s_oc_low) >= 2 and (s_oc_low or s_n_very_low)) or (" + CG['soil.erosion']['systems'] + " and (" + CG['soil.erosion']['trigger'] + "))", 'tested 22 Nov'),
 ('agriculture.soil_degradation', 'in force, P and K count only over >= 95% of cropland', lambda: "(sys_cropland and ntrue(s_n_very_low, s_p_medium_g >= 1, s_k_medium_g >= 1, s_oc_low) >= 2) or (" + CG['soil.erosion']['systems'] + " and (" + CG['soil.erosion']['trigger'] + "))", 'tested 22 Nov'),
 ('ntfp.forest_degradation', 'previous rule', lambda: "(sys_trees and (s_net_tree_loss or (s_forest_to_farm and s_net_tree_neg))) or (sys_forest and s_fringe_loss) or (" + CG['forest.fire']['systems'] + " and (" + CG['forest.fire']['trigger'] + "))", 'previous'),
 ('ntfp.forest_degradation', 'add tree-cover gain below 0.7 of loss (forest gate)', lambda: "((sys_trees) and (s_net_tree_loss or (s_forest_to_farm and s_net_tree_neg) or (sys_forest and s_gain_below_loss))) or (sys_forest and s_fringe_loss) or (" + CG['forest.fire']['systems'] + " and (" + CG['forest.fire']['trigger'] + "))", 'adopted 22 Nov'),
 ('ntfp.forest_degradation', 'as above, farmland degradation >= 4% in fringe degradation', lambda: "((sys_trees) and (s_net_tree_loss or (s_forest_to_farm and s_net_tree_neg) or (sys_forest and s_gain_below_loss))) or " + cur('forest.fringe_degradation', 'forest.fire'), 'adopted 22 Nov'),
 ('ntfp.forest_degradation', 'as above, forest to farm >= 6% of forest where forest >= 600 ha', lambda: cur('forest.tree_cover_loss', 'forest.fringe_degradation', 'forest.fire'), 'adopted 22 Nov'),
 ('ntfp.forest_degradation', 'add gross tree-cover loss >= 5% of MWS', lambda: "tcd_frac >= 0.05 or " + cur('forest.tree_cover_loss', 'forest.fringe_degradation', 'forest.fire'), 'tested 22 Nov'),
 ('livelihood.livestock_decline', 'previous rule', lambda: "sys_pastoral and (s_grazing_density or s_grass_tree_loss or s_shrub_ndvi_decline or (s_commons_shrinking and (s_livestock_dense or s_grazing_density)))", 'previous'),
 ('livelihood.livestock_decline', 'commons degradation adds tree loss in shrub > 2 ha and forest-edge loss', lambda: cur('fodder.grazing_pressure', 'fodder.commons_degradation'), 'adopted 22 Nov'),
 ('livelihood.livestock_decline', 'as above, gate pastoral >= 3% and density >= 0.3', lambda: "share_pastoral >= 0.03 and tlu_per_ha >= 0.3 and ((" + CG['fodder.grazing_pressure']['trigger'] + ") or (" + CG['fodder.commons_degradation']['trigger'] + "))", 'declined'),
 ('livelihood.livestock_decline', 'as above, gate pastoral >= 5% or density >= 0.3 (mixed crop-livestock)', lambda: "(share_pastoral >= 0.05 or tlu_per_ha >= 0.3) and ((" + CG['fodder.grazing_pressure']['trigger'] + ") or (" + CG['fodder.commons_degradation']['trigger'] + "))", 'declined'),
 ('livelihood.livestock_water', 'current', lambda: cur('livestock_water_scarcity'), 'in force'),
 ('livelihood.livestock_water', 'no pastoral-land gate', lambda: cur('livestock_water_scarcity', gate=False), 'tested 22 Nov'),
 ('waterbodies.siltation', 'current', lambda: cur('waterbody_shrinkage'), 'in force'),
 ('waterbodies.siltation', 'low persistence or falling rabi water (gated)', lambda: "sys_waterbodies and (s_swb_rabi_persist_low or s_swb_rabi_trend)", 'tested 21 Nov'),
 ('waterbodies.siltation', 'in force, or rabi/kharif water drop (s_rabi_water_drop)', lambda: cur('waterbody_shrinkage') + " or (sys_waterbodies and s_rabi_water_drop)", 'tested 22 Nov'),
 ('waterbodies.siltation', 'in force, or rabi/kharif water drop with shrinking water bodies', lambda: cur('waterbody_shrinkage') + " or (sys_waterbodies and s_rabi_water_drop and (s_swb_shrinking or s_swb_rabi_trend))", 'tested 22 Nov'),
 ('agriculture.irrigation', 'previous rule (tank/canal gate, water bodies drying before rabi)', lambda: "(sys_surface_irrigated and (s_swb_rabi_persist_low or s_swb_rabi_trend) and (s_dbl_falling or s_soge_stage)) or (" + CG['irrigation.waterlogging']['systems'] + " and (" + CG['irrigation.waterlogging']['trigger'] + "))", 'previous'),
 ('agriculture.irrigation', 'double-cropping gate, rabi/kharif water drop + 1 support', lambda: cur('irrigation.rabi_water_shortfall', 'irrigation.waterlogging'), 'adopted 22 Nov'),
 ('agriculture.irrigation', 'in force, plus groundwater evidence alone where there are no water bodies', lambda: cur('irrigation.rabi_water_shortfall', 'irrigation.waterlogging') + " or (sys_irrigated_cropland and nknown(s_rabi_water_drop) == 0 and (s_soge_stage or s_wl_fall) and ctx_no_canal and ctx_no_river)", 'tested 22 Nov'),
 ('agriculture.irrigation', 'previous rule without the tank/canal gate', lambda: "((s_swb_rabi_persist_low or s_swb_rabi_trend) and (s_dbl_falling or s_soge_stage)) or (s_wl_rise and ctx_flat)", 'declined'),
 ('agriculture.irrigation', 'previous trigger, gate on groundwater + canal + tank >= 10%', lambda: "(share_groundwater_irrigated + share_canal_irrigated + share_tank_irrigated >= 0.10) and (((s_swb_rabi_persist_low or s_swb_rabi_trend) and (s_dbl_falling or s_soge_stage)) or (s_wl_rise and ctx_flat))", 'declined'),
 ('agriculture.groundwater', 'current', lambda: cur('groundwater.over_extraction', 'groundwater.irrigation_expansion', 'groundwater.water_balance_deficit'), 'in force'),
 ('socio-economic.caste', 'previous rule (3 of 6)', lambda: "ntrue(s_st_share or s_sc_share, s_low_literacy, s_low_nrega, s_bank_far, s_low_shg, s_kuccha) >= 3", 'previous'),
 ('socio-economic.caste', '2 of 6 dimensions', lambda: cur('multidimensional_vulnerability'), 'adopted 21 Nov'),
]

STRUCTURE = [   # sheet structure (system / context / trigger parts) carried into atlas-style rules
 # drought: the sheet requires 2 of 3 rainfall contexts (sig_03 rainfall-limited incl. kharif share, sig_04 runoff, sig_05 min rain)
 ('agriculture.drought', 'rule in force (for reference)', lambda: cur('drought.kharif_drought', 'drought.unstable_sowing'), 'adopted 22 Nov'),
 ('agriculture.drought', 'atlas pattern + sheet rainfall-limited context (sig_03)', lambda: "sys_rainfed_or_tank and (s_drought_weeks or s_drought_years or s_dry_spells) and sh_high_drought_risk_sig_03", 'test'),
 ('agriculture.drought', 'atlas pattern + 2 of the sheet\'s 3 rainfall contexts', lambda: "sys_rainfed_or_tank and (s_drought_weeks or s_drought_years or s_dry_spells) and (sh_high_drought_risk_sig_03 + sh_high_drought_risk_sig_04 + sh_high_drought_risk_sig_05 >= 2)", 'test'),
 ('agriculture.drought', 'atlas pattern + 2 of atlas contexts (semi-arid, runoff >= 0.25, rain CV >= 0.25)', lambda: "sys_rainfed_or_tank and (s_drought_weeks or s_drought_years or s_dry_spells) and ntrue(ctx_semi_arid, s_runoff_high, precip_cv >= 0.25) >= 2", 'test'),
 ('agriculture.drought', 'atlas pattern + sheet sig_03, rainfed/tank gate lowered to 5%', lambda: "(share_rainfed_dryland + share_rainfed_rice_subhumid + share_tank_irrigated >= 0.05) and (s_drought_weeks or s_drought_years or s_dry_spells) and sh_high_drought_risk_sig_03", 'test'),
 # irrigation: sheet sig_01 (rabi water below kharif water) acts as the system/stress entry; then 2 of 4 supporting conditions
 ('agriculture.irrigation', 'sheet sig_01 + 2 of atlas supports (water shrinking, SOGE/wl fall, no canal and river, few NREGA water works)', lambda: "sh_high_irrigation_difficulties_sig_01 and ntrue(s_swb_shrinking or s_swb_rabi_trend, s_soge_stage or s_wl_fall, ctx_no_canal and ctx_no_river, ctx_low_nrega_water) >= 2", 'test'),
 ('agriculture.irrigation', 'gate double-cropped share >= 0.5 + 2 of atlas supports', lambda: "double_share >= 0.5 and ntrue(s_swb_shrinking or s_swb_rabi_trend, s_soge_stage or s_wl_fall, ctx_no_canal and ctx_no_river, ctx_low_nrega_water) >= 2", 'test'),
 ('agriculture.irrigation', 'gate double-cropped share >= 0.5 + sheet sig_01 + 1 atlas support (adopted as s_rabi_water_drop)', lambda: "double_share >= 0.5 and sh_high_irrigation_difficulties_sig_01 and ntrue(s_swb_shrinking or s_swb_rabi_trend, s_soge_stage or s_wl_fall, ctx_no_canal and ctx_no_river, ctx_low_nrega_water) >= 1", 'test'),
 # soil: the sheet's P (< 25) and K (< 210) cut-offs sit in the Soil Health Card medium class; atlas P/K (< 10, < 110) never fire here
 ('agriculture.soil_degradation', '2 of (sheet P < 25, sheet K < 210, atlas OC low)', lambda: "ntrue(sh_soil_health_sig_02, sh_soil_health_sig_03, s_oc_low) >= 2", 'test'),
 ('agriculture.soil_degradation', '2 of (sheet P, sheet K, atlas OC severe)', lambda: "ntrue(sh_soil_health_sig_02, sh_soil_health_sig_03, s_oc_low_g >= 1) >= 2", 'test'),
 ('agriculture.soil_degradation', 'sheet P or K, and atlas OC low', lambda: "(sh_soil_health_sig_02 or sh_soil_health_sig_03) and s_oc_low", 'test'),
 # low yield: the sheet requires a context (sig_04 SOGE + long dry spells, or sig_05 kharif cropped < 85%)
 ('agriculture.low_yield', 'rule in force (for reference)', lambda: cur('productivity.farmland_abandonment', 'productivity.declining_intensity'), 'adopted 22 Nov'),
 ('agriculture.low_yield', 'adopted rule and sheet context (sig_04 or sig_05)', lambda: "(" + cur('productivity.farmland_abandonment', 'productivity.declining_intensity') + ") and (sh_decreasing_productivity_sig_04 or sh_decreasing_productivity_sig_05)", 'test'),
 ('agriculture.low_yield', 'adopted rule or (sheet small-cropping sig_03 and kharif context sig_05)', lambda: "(" + cur('productivity.farmland_abandonment', 'productivity.declining_intensity') + ") or (sh_decreasing_productivity_sig_03 and sh_decreasing_productivity_sig_05)", 'test'),
 # forest: the sheet gates on absolute forest area and uses relative net loss
 ('ntfp.forest_degradation', 'forest gate + relative net loss (gain < loss) or forest-to-farm >= 5% of forest', lambda: "sys_forest and (tci_frac < tcd_frac or div(forest_to_farm_frac, f_forest) >= 0.05)", 'test'),
 ('ntfp.forest_degradation', 'current or (forest gate and gain < 0.7 x loss)', lambda: cur('forest.tree_cover_loss', 'forest.fringe_degradation', 'forest.fire') + " or (sys_forest and tci_frac < 0.7 * tcd_frac)", 'test'),
 ('ntfp.forest_degradation', 'forest area >= 300 ha gate + relative net loss or forest-to-farm', lambda: "f_forest * area >= 300 and (tci_frac < tcd_frac or div(forest_to_farm_frac, f_forest) >= 0.05)", 'test'),
 # fodder / livestock water: the sheet gates on livestock (village head count), the atlas on pastoral land share
 ('livelihood.livestock_decline', 'gate on livestock density >= 0.3 TLU/ha or pastoral >= 5%', lambda: "(tlu_per_ha >= 0.3 or share_pastoral >= 0.05) and ((" + CG['fodder.grazing_pressure']['trigger'] + ") or (" + CG['fodder.commons_degradation']['trigger'] + "))", 'test'),
 ('livelihood.livestock_decline', 'livestock gate + fringe loss as a trigger', lambda: "(tlu_per_ha >= 0.3 or share_pastoral >= 0.05) and ((" + CG['fodder.grazing_pressure']['trigger'] + ") or (" + CG['fodder.commons_degradation']['trigger'] + ") or s_fringe_loss)", 'test'),
 ('livelihood.livestock_water', 'gate on livestock density >= 0.3 TLU/ha or pastoral >= 5%', lambda: "(tlu_per_ha >= 0.3 or share_pastoral >= 0.05) and (" + CG['livestock_water_scarcity']['trigger'] + ")", 'test'),
]

def ev(expr, e):
    try: v = evaluate(expr, e)
    except Exception: return None
    if isinstance(v, float) and math.isnan(v): return None
    return bool(v)

def main():
    D = build() if '--rebuild' in sys.argv or not CACHE.exists() else pickle.load(open(CACHE, 'rb'))
    GT = {r['uid']: r for r in D['gt']}
    sets = {'main': CANDIDATES, 'structure': STRUCTURE}
    which = sys.argv[sys.argv.index('--set') + 1] if '--set' in sys.argv else 'main'
    print('| Pathway | Candidate | Status | TP | FP | FN | TN | Balanced accuracy | F1 | Sample |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for row in sets[which]:
        pw, name, f = row[:3]; status = row[3] if len(row) > 3 else ''
        expr = f(); pairs = []
        for it in D['items']:
            if it['pathway'] != pw or it['uid'] not in GT: continue
            p = ev(expr, GT[it['uid']]['env']); pairs.append((it['label'], None if p is None else int(p)))
        c = gt._cm(pairs)
        vals = [ev(expr, r['env']) for r in D['sample']]
        fire = sum(1 for v in vals if v) / len(vals); und = sum(1 for v in vals if v is None) / len(vals)
        samp = f"{round(100 * fire)}%" + (f" ({round(100 * und)}% undecided)" if und >= 0.05 else '')
        print(f"| {gt._nb(pw.split('.')[1].replace('_', ' '))} | {gt._nb(name)} | {status} | {c['TP']} | {c['FP']} | {c['FN']} | {c['TN']} | "
              f"{gt._fmt(c['balanced_accuracy'])} | {gt._fmt(c['f1'])} | {samp} |")

if __name__ == '__main__':
    main()
