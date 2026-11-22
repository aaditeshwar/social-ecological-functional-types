"""Write knowledge/sheet_rules.json: the Signal_Verification sheet's revised signals, triggers and intensities
(Signal_Verification_1.xlsx, 21 Nov 2026) as expressions over the cached CoRE Stack data.

Reading conventions (agreed 21 Nov 2026):
- each signal is 1 when true, 0 when false; in triggers and intensities `or` is a sum and `and` a product;
  `(sig_03 or sig_04 or sig_05 > 1)` is sig_03 + sig_04 + sig_05 > 1;
- `shrub_slope` is read as the NDVI `shrub_trend` class;
- nitrogen percentiles of exactly 0 are missing data (CS-91), not zero nitrogen.
Run from the repo root: python tools/build_sheet_rules.py
"""
import json
from pathlib import Path

PCT = ['p05', 'p10', 'p20', 'p30', 'p40', 'p50', 'p60', 'p70', 'p80', 'p90', 'p95']
def soil_frac(nut, thr, unit='kg_per_ha'):
    cols = ', '.join(f'soil.{nut}_{p}_in_{unit}' for p in PCT)
    return f'frac_below({thr}, [{cols}])'
def soil_share(nut, thr, unit='kg_per_ha'):
    # nutrient_area[<thr] / area_under_cropping: the soil_health percentiles describe the cropped area
    # (n_p30 is the value below which 30% of the cropped area lies), so the share is read off them directly
    return soil_frac(nut, thr, unit)
def text_is(field, *vals):
    cond = ' or '.join(f"{field} == '{v}'" for v in vals)
    return f'(({cond}) if is_text({field}) else nan)'
def text_not(field, val):
    return f"(({field} != '{val}') if is_text({field}) else nan)"
RK = 'mean(div(swb.rabi_area, swb.kharif_area))'           # mean of the yearly rabi / kharif water-area ratio
P = 'hydro.precipitation'

RULES = [
 {'id': 'groundwater_stress', 'section': 'Agriculture / Water', 'signals': {
   'sig_01': (f"mean({P}) < 800 and {text_not('soge.class_name', 'Safe')}",
              "Average(Precipitation_in_mm_)<800 and soge_class_name not in ['Safe']"),
   'sig_02': ('mean(hydro.delta_g) < -70', 'mean(DeltaG_in_mm_) < -70mm'),
   'sig_03': ('conn.n_upstream == 0', 'len(upstream_mws) == 0'),
   'sig_04': ('river.n == 0 and canal.n == 0', 'river is None and canal is None'),
   'sig_05': ('mean(ci.cropping_intensity) > 1.6', 'cropping_intensity_unit_less_ > 1.6')},
  'trigger': '(sig_01 + sig_02) * (sig_03 + sig_04 + sig_05) > 0',
  'sheet_trigger': '(sig_01 or sig_02) and (sig_03 or sig_04 or sig_05)',
  'intensity': '(sig_01 + sig_02) * (sig_03 + sig_04 + sig_05)', 'out_of': 6},
 {'id': 'high_drought_risk', 'section': 'Agriculture / Water', 'signals': {
   'sig_01': ('mean(drought.severe) + mean(drought.moderate) > 1 and max(drought.severe) + max(drought.moderate) > 6',
              '((mean(Severe_in_weeks_) + mean(Moderate_in_weeks_)) > 1) and (max(Severe_in_weeks_) + max(Moderate_in_weeks_)) > 6'),
   'sig_02': ('max(drought.dry_spell) > 4 and mean(drought.dry_spell) > 2.5',
              'max(drysp_unit_4_weeks_) > 4 and mean(drysp_unit_4_weeks_) > 2.5'),
   'sig_03': (f'(mean({P}) < 600 or div(mean(hseas.precipitation_kharif), mean({P})) < 0.66) and max({P}) < 1500',
              '(mean(Precipitation_in_mm_)<600 or mean(precipitation_kharif_in_mm_) / mean(Precipitation_in_mm_) < 0.66) and max(Precipitation_in_mm_) < 1500'),
   'sig_04': (f'div(mean(hydro.runoff), mean({P})) > 0.2', 'mean(RunOff_in_mm) / mean(Precipitation_in_mm_) > 0.2'),
   'sig_05': (f'min({P}) < 400', 'min(Precipitation_in_mm_) < 400')},
  'trigger': '(sig_01 + sig_02 > 0) * (sig_03 + sig_04 + sig_05 > 1) > 0',
  'sheet_trigger': '(sig_01 or sig_02) and (sig_03 or sig_04 or sig_05 > 1)',
  'intensity': '(sig_01 + sig_02) * (sig_03 + sig_04 + sig_05)', 'out_of': 6},
 {'id': 'high_irrigation_difficulties', 'section': 'Agriculture / Water', 'signals': {
   'sig_01': (f'{RK} < 0.995', 'mean(rabi_area_in_ha_ / kharif_area_in_ha_) < 0.995'),
   'sig_02': ('last(swb.total_area) - first(swb.total_area) < 0 and nfalls(swb.total_area) >= 0.5 * nvalid(swb.total_area)',
              '(total_area_in_ha_[-1] - total_area_in_ha_[0]) < 0 AND number of years with a year-on-year fall >= 0.5*(total number of years)'),
   'sig_03': (f"({text_is('soge.class_name', 'Semi-Critical', 'Semi Critical', 'Critical')} or mean(hydro.delta_g) < -120) and conn.n_upstream <= 2",
              "(soge_class_name in ['Semi-Critical', 'Critical'] or mean(DeltaG_in_mm_) < -120mm) and (len(upstream_mws)<=2)"),
   'sig_04': ('river.n == 0 and canal.n == 0 and div(mean(swb.rabi_area), area) < 0.4',
              'canal is None AND river is None AND average(rabi_area_in_ha_ / mws area) < 0.4'),
   'sig_05': ('sum(nz(nrega.irrigation_on_farms)) < 15 and div(mean(ci.doubly_cropped_area), area) > 0.1',
              "sum_nrega_annual['Irrigation on farms'] < 15 AND average(doubly_cropped_area_in_ha_ / mws area) > 0.1")},
  'trigger': 'sig_01 * (sig_02 + sig_03 + sig_04 + sig_05 >= 2) > 0',
  'sheet_trigger': 'sig_01 and (sig_02 + sig_03 + sig_04 + sig_05 >= 2)',
  'intensity': 'sig_01 * (sig_02 + sig_03 + sig_04 + sig_05)', 'out_of': 4},
 {'id': 'soil_health', 'section': 'Agriculture / Soil', 'signals': {
   'sig_01': (f"{soil_share('n', 120).replace('frac_below(', 'frac_below_nz(', 1)} >= 0.95", 'nitrogen_area[<120] / area_under_cropping_in_ha >= 0.95'),
   'sig_02': (f"{soil_share('p', 25)} > 0.8", 'phosphorus_area[<25] / area_under_cropping_in_ha > 0.8'),
   'sig_03': (f"{soil_share('k', 210)} > 0.4", 'potassium_area[<210] / area_under_cropping_in_ha > 0.4'),
   'sig_04': (f"{soil_share('oc', 0.5, 'percent')} >= 0.4", 'organic_carbon_area[<0.5] / area_under_cropping_in_ha >= 0.4')},
  'trigger': 'sig_01 + sig_02 + sig_03 + sig_04 >= 2', 'sheet_trigger': 'sig_01 + sig_02 + sig_03 + sig_04 >= 2',
  'intensity': 'sig_01 + sig_02 + sig_03 + sig_04', 'out_of': 4},
 {'id': 'decreasing_productivity', 'section': 'Agriculture / Yield', 'signals': {
   'sig_01': ('div(degr.farm_to_scrub_land_area, ci.sum_area) > 0.08 and 0 < ci.sum_area < 500',
              'farm_to_scrub_land_area_in_ha/sum_area_in_ha (cropping) > 8% AND 0 < sum_area_in_ha (cropping) < 500'),
   'sig_02': ('late(ci.cropping_intensity, 2) - early(ci.cropping_intensity, 2) < 0',
              'mean(last two cropping_intensity values) - mean(first two cropping_intensity values) < 0'),
   'sig_03': ('mean(ci.triply_cropped_area) < 15 and mean(ci.single_kharif_cropped_area) < 140',
              'Average(triply_cropped_area_in_ha_) < 15 AND Average(single_kharif_cropped_area_in_ha) < 140'),
   'sig_04': (f"{text_not('soge.class_name', 'Safe')} and mean(drought.dry_spell) > 6",
              'soge_class_name != Safe AND mean(drysp_unit_4_weeks_)>6'),
   'sig_05': ('mean(drought.kharif_cropped_area) < 85', 'mean(kharif_cropped_area_percent_) < 85')},
  'trigger': '(sig_01 + sig_02 + sig_03) * (sig_04 + sig_05) > 0',
  'sheet_trigger': '(sig_01 or sig_02 or sig_03) AND (sig_04 or sig_05)',
  'intensity': '(sig_01 + sig_02 + sig_03) * (sig_04 + sig_05)', 'out_of': 6},
 {'id': 'siltation', 'section': 'Agriculture / Water -> Waterbodies', 'signals': {
   'sig_01': (f'{RK} < 0.95', 'mean(rabi_area_in_ha_ / kharif_area_in_ha_) < 95%'),
   'sig_02': ('slope(swb.total_area) < 0', "sen's slope(total_area_in_ha_) < 0")},
  'trigger': 'sig_01 + sig_02 > 0', 'sheet_trigger': 'sig_01 or sig_02',
  'intensity': 'sig_01 + sig_02', 'out_of': 2},
 {'id': 'water_scarcity', 'section': 'Livelihood / Livestock', 'signals': {
   'sig_01': (f'{RK} < 0.3', 'mean(rabi_area_in_ha_ / kharif_area_in_ha_) < 30%'),
   'sig_02': ('slope(swb.total_area) < 0.7', "sen's slope(total_area_in_ha_) < 0.7"),
   'sig_03': ('vmax.livestock_units_sheet > 2500', 'max(village large_animals_total * 3 + small_animals_total) > 2500'),
   'sig_04': ('sum(nz(nrega.soil_and_water_conservation)) < 20', 'sum_nrega_annual[Soil and water conservation_count] < 20'),
   'sig_05': ('river.n == 0', 'river is None')},
  'trigger': 'sig_03 * (sig_01 + sig_02 * (sig_04 + sig_05)) > 0',
  'sheet_trigger': 'sig_03 and (sig_01 or (sig_02 and (sig_04 or sig_05)))',
  'intensity': '(sig_03 * sig_01 + sig_03 * sig_02) * (sig_04 + sig_03) * (sig_02 * sig_05)', 'out_of': 4,
  'note': "Sheet intensity read literally: '(sig_03 and sig_01) + (sig_03 and sig_02) and (sig_04 + sig_03) and (sig_02 and sig_05)'. It has no 'out of'; 4 is its largest value."},
 {'id': 'fodder_risk', 'section': 'Livelihood / Livestock', 'signals': {
   'sig_01': ('tig.tree_loss_in_tree_in_shrub_area_in_ha > 2', 'tree_loss_in_tree_in_shrub_area_in_ha > 2ha'),
   'sig_02': ('fringe.tree_deforestation_fringe_area_in_ha > 25 and fringe.tree_degradation_fringe_area_in_ha > 25',
              'tree_deforestation_fringe_area_in_ha > 25ha and tree_degradation_fringe_area_in_ha > 25ha'),
   'sig_03': (text_is('ndvi.shrub_trend', 'Decreasing'), 'shrub_slope [from ndvi sheet] < 0, read as shrub_trend == decreasing'),
   'sig_04': ('vmax.livestock_units_sheet > 2000', 'max(village large_animals_total * 3 + small_animals_total) > 2000')},
  'trigger': 'sig_04 * (sig_01 + sig_02 + sig_03) > 0', 'sheet_trigger': 'sig_04 and (sig_01 or sig_02 or sig_03)',
  'intensity': 'sig_04 * sig_01 + sig_04 * sig_02 + sig_04 * sig_03', 'out_of': 3},
 {'id': 'good_water_potential', 'section': 'Livelihood / Fishery', 'type': 'opportunity', 'signals': {
   'sig_01': (f'{RK} >= 0.8', 'mean(rabi_area_in_ha_ / kharif_area_in_ha_) >= 80%'),
   'sig_02': ('slope(swb.total_area) >= 0.3', "sen's slope(total_area_in_ha_) >= 0.3"),
   'sig_03': ('sum(nz(nrega.soil_and_water_conservation)) >= 20', 'sum_nrega_annual[Soil and water conservation_count] >= 20'),
   'sig_04': ('mean(ci.cropping_intensity) < 1', 'average(cropping_intensity_unit_less) < 1'),
   'sig_05': ('div(vtop.shg_hhd, vtop.total_hhd) > 0.5', 'total_hhd_mobilized_into_shg/total_hhd > 0.5 [largest village]')},
  'trigger': 'sig_01 * (sig_02 + sig_03 + sig_04 + sig_05) > 0', 'sheet_trigger': 'sig_01 and (sig_02 or sig_03 or sig_04 or sig_05)',
  'intensity': 'sig_01 * (sig_02 + sig_03 + sig_04 + sig_05)', 'out_of': 4},
 {'id': 'transition_from_crops_to_agroforestry', 'section': 'Livelihood / Agroforestry', 'type': 'opportunity', 'signals': {
   'sig_01': ('100 * div(degr.farm_to_scrub_land_area, degr.total_degradation_area) > 60',
              '100*farm_to_scrub_land_area_in_ha / total_degradation_area_in_ha > 60%'),
   'sig_02': ('slope(ci.cropping_intensity) < 0', 'sen slope(cropping_intensity_unit_less) < 0'),
   'sig_03': ('sum(nz(nrega.plantations)) >= 5', 'sum nrega_count[Plantations_count_] >= 5'),
   'sig_04': ('div(vtop.shg_hhd, vtop.total_hhd) > 0.5', 'total_hhd_mobilized_into_shg/total_hhd > 0.5 [largest village]'),
   'sig_05': ("(vtop.fpo_text == 'FPO' or vtop.fpo_text == 'Both') and vtop.coop_km < 5",
              '(availability_of_fpos_pacs in ["FPO", "BOTH"]) and (cooperative_cat_distance_in_km < 5km) [largest village]')},
  'trigger': 'sig_01 + sig_02 > 0', 'sheet_trigger': 'sig_01 or sig_02',
  'intensity': '(sig_01 + sig_02) * (1 + sig_03 + sig_04 + sig_05)', 'out_of': 8},
 {'id': 'forest_degradation', 'section': 'Forest Biodiversity / Forests', 'signals': {
   'sig_01': ('100 * div(tcd.total_tree_cover_decrease_area, area) > 7 or 100 * div(degr.total_degradation_area, area) > 4',
              '%total_deforestation_area_in_ha (over mws) > 7 OR % total_degradation_area_in_ha (over mws) > 4'),
   'sig_02': ('mean(lulc.tree_forest_area) > 320 and tci.total_tree_cover_increase_area < 0.7 * tcd.total_tree_cover_decrease_area',
              'average(tree_forest_area_in_ha_) > 320ha AND total_afforestation_area_in_ha < total_deforestation_area_in_ha * 0.7'),
   'sig_03': ('100 * div(tcd.forest_to_farm_area, mean(lulc.tree_forest_area)) > 6 and mean(lulc.tree_forest_area) > 600',
              '% forest_to_farm_area_in_ha (over average(tree_forest_area_in_ha_)) > 6 AND average(tree_forest_area_in_ha_) > 600')},
  'trigger': 'sig_01 + sig_02 + sig_03 > 0', 'sheet_trigger': 'sig_01 or sig_02 or sig_03',
  'intensity': 'sig_01 + sig_02 + sig_03', 'out_of': 3,
  'note': 'total_degradation_area is read from change_detection_degradation (farmland degradation), as the column name in the sheet says.'},
 {'id': 'multi_sector_vulnerability', 'section': 'Socio-economic', 'signals': {
   'sig_01': ('vtop.st_pct + vtop.sc_pct > 60', 'ST_percent + SC_percent > 60% [largest village]'),
   'sig_02': ('nrega_works < 50', 'sum(all nrega_annual columns) < 50'),
   'sig_03': ('vtop.bank_km > 5', 'bank_branch_distance_in_km > 5km [largest village]'),
   'sig_04': ('vtop.literacy < 55', 'literacy_rate_percent < 55% [largest village]'),
   'sig_05': ('div(vtop.shg_hhd, vtop.total_hhd) > 0.4', 'total_hhd_mobilized_into_shg/total_hhd > 0.4 [largest village]')},
  'trigger': 'sig_01 + sig_02 + sig_03 + sig_04 + sig_05 >= 3', 'sheet_trigger': 'sig_01 + sig_02 + sig_03 + sig_04 + sig_05 >= 3',
  'intensity': 'sig_01 + sig_02 + sig_03 + sig_04 + sig_05', 'out_of': 5},
 {'id': 'water_security_safety_domestic_use', 'section': 'Socio-economic / Health', 'signals': {
   'sig_01': ('mine.n >= 1', 'mining == 1'),
   'sig_02': ("((terrain.terrain_cluster_id != 1) if not is_text(terrain.terrain_cluster_id) else (terrain.terrain_cluster_id != '1')) and tcd.total_tree_cover_decrease_area > 20 and mean(ci.cropping_intensity) < 1.5",
              "terrain_cluster_id != '1' and total_deforestation_area_in_ha > 20ha and average(cropping_intensity_unit_less_) < 1.5"),
   'sig_03': (f'{RK} < 0.95', 'mean(rabi_area_in_ha_ / kharif_area_in_ha_) < 95%'),
   'sig_04': (f"{text_not('soge.class_name', 'Safe')} + (mean(hydro.delta_g) <= 0) * ((conn.n_upstream == 0) + {text_is('aquifer.aquifer_class', 'Hard Rock', 'Hard rock')}) > 0",
              "soge_class_name (of latest year) not in ['Safe'] or mean(DeltaG_in_mm_) <= 0mm and ((len(upstream_mws) == 0 or aquifer_class == 'Hard rock'))"),
   'sig_05': ('slope(swb.total_area) < 0.5 and sum(nz(nrega.soil_and_water_conservation)) < 10',
              "sen's slope(total_area_in_ha_) < 0.5 and sum_nrega_annual[Soil and water conservation_count] < 10")},
  'trigger': 'sig_01 + sig_03 * (sig_02 + sig_04 + sig_05) > 0', 'sheet_trigger': 'sig_01 or (sig_03 and (sig_02 or sig_04 or sig_05))',
  'intensity': 'sig_01 + sig_03 * (sig_02 + sig_04 + sig_05)', 'out_of': 4,
  'note': 'sig_04 has no brackets around or/and in the sheet; read as arithmetic it is soge_not_safe + (DeltaG <= 0) * (headwater + hard rock).'},
]

def main():
    out = {'_about': __doc__.strip(), 'source': 'Signal_Verification_1.xlsx (Revised Patterns), 21 Nov 2026',
           'rules': []}
    for r in RULES:
        r = dict(r)
        r['signals'] = {k: {'expr': e, 'sheet': t} for k, (e, t) in r['signals'].items()}
        r.setdefault('type', 'stress')
        out['rules'].append(r)
    p = Path(__file__).resolve().parents[1] / 'knowledge' / 'sheet_rules.json'
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    print(f'wrote {len(out["rules"])} sheet rules to {p}')

if __name__ == '__main__':
    main()
