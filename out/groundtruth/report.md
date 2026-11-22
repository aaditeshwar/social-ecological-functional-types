# Ground-truth check of the atlas and Signal_Verification rules

145 labels on 39 micro-watersheds in 32 tehsils. TP/FP/FN/TN count decided predictions; "unknown" means the rule could not be decided from the data, "no data" that the MWS was not found in the fetched tehsil. Metrics use decided predictions only. Balanced accuracy is the mean of recall and specificity, so it is not inflated by a rule that never (or always) fires; it needs both positive and negative labels. "atlas, no gate" ignores the production-system gate. "Sample" is the share of the 4,598 atlas sample MWS where the rule fires.

| Pathway | Rules | n | TP | FP | FN | TN | Unknown | No data | Accuracy | Balanced accuracy | F1 | Precision | Recall | Sample |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Groundwater | atlas | 23 | 0 | 7 | 1 | 15 | 0 | 0 | 0.65 | 0.34 | 0.00 | 0.00 | 0.00 | 32% |
| Groundwater | atlas,&nbsp;no&nbsp;gate | 23 | 0 | 9 | 1 | 13 | 0 | 0 | 0.56 | 0.29 | 0.00 | 0.00 | 0.00 | 43% |
| Groundwater | sheet | 23 | 1 | 8 | 0 | 14 | 0 | 0 | 0.65 | 0.82 | 0.20 | 0.11 | 1.00 | 43% |
| Drought | atlas | 23 | 5 | 1 | 1 | 16 | 0 | 0 | 0.91 | 0.89 | 0.83 | 0.83 | 0.83 | 27% |
| Drought | atlas,&nbsp;no&nbsp;gate | 23 | 5 | 1 | 1 | 16 | 0 | 0 | 0.91 | 0.89 | 0.83 | 0.83 | 0.83 | 29% |
| Drought | sheet | 23 | 5 | 0 | 1 | 17 | 0 | 0 | 0.96 | 0.92 | 0.91 | 1.00 | 0.83 | 26% |
| Irrigation | atlas | 23 | 6 | 2 | 0 | 15 | 0 | 0 | 0.91 | 0.94 | 0.86 | 0.75 | 1.00 | 28% |
| Irrigation | atlas,&nbsp;no&nbsp;gate | 23 | 6 | 8 | 0 | 9 | 0 | 0 | 0.65 | 0.76 | 0.60 | 0.43 | 1.00 | 45% |
| Irrigation | sheet | 23 | 6 | 3 | 0 | 14 | 0 | 0 | 0.87 | 0.91 | 0.80 | 0.67 | 1.00 | 24% |
| Low&nbsp;yield | atlas | 23 | 5 | 3 | 2 | 13 | 0 | 0 | 0.78 | 0.76 | 0.67 | 0.62 | 0.71 | 33% |
| Low&nbsp;yield | atlas,&nbsp;no&nbsp;gate | 23 | 5 | 3 | 2 | 13 | 0 | 0 | 0.78 | 0.76 | 0.67 | 0.62 | 0.71 | 34% |
| Low&nbsp;yield | sheet | 23 | 7 | 1 | 0 | 15 | 0 | 0 | 0.96 | 0.97 | 0.93 | 0.88 | 1.00 | 35% |
| Soil&nbsp;degradation | atlas | 23 | 4 | 3 | 1 | 15 | 0 | 0 | 0.83 | 0.82 | 0.67 | 0.57 | 0.80 | 29% |
| Soil&nbsp;degradation | atlas,&nbsp;no&nbsp;gate | 23 | 4 | 3 | 1 | 15 | 0 | 0 | 0.83 | 0.82 | 0.67 | 0.57 | 0.80 | 30% |
| Soil&nbsp;degradation | sheet | 23 | 4 | 2 | 1 | 16 | 0 | 0 | 0.87 | 0.84 | 0.73 | 0.67 | 0.80 | 22% |
| Forest&nbsp;degradation | atlas | 12 | 8 | 1 | 0 | 3 | 0 | 0 | 0.92 | 0.88 | 0.94 | 0.89 | 1.00 | 41% |
| Forest&nbsp;degradation | atlas,&nbsp;no&nbsp;gate | 12 | 8 | 1 | 0 | 3 | 0 | 0 | 0.92 | 0.88 | 0.94 | 0.89 | 1.00 | 62% |
| Forest&nbsp;degradation | sheet | 12 | 8 | 1 | 0 | 3 | 0 | 0 | 0.92 | 0.88 | 0.94 | 0.89 | 1.00 | 46% |
| Siltation | atlas | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0.00 | – | 0.00 | – | 0.00 | 4% |
| Siltation | atlas,&nbsp;no&nbsp;gate | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0.00 | – | 0.00 | – | 0.00 | 16% |
| Siltation | sheet | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 1.00 | – | 1.00 | 1.00 | 1.00 | 59% |
| Livestock&nbsp;water | atlas | 6 | 0 | 0 | 1 | 5 | 0 | 0 | 0.83 | 0.50 | 0.00 | – | 0.00 | 0% |
| Livestock&nbsp;water | atlas,&nbsp;no&nbsp;gate | 6 | 0 | 0 | 1 | 5 | 0 | 0 | 0.83 | 0.50 | 0.00 | – | 0.00 | 3% |
| Livestock&nbsp;water | sheet | 6 | 1 | 0 | 0 | 5 | 0 | 0 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 51% |
| Livestock&nbsp;decline&nbsp;(fodder&nbsp;shortage) | atlas | 6 | 3 | 0 | 2 | 1 | 0 | 0 | 0.67 | 0.80 | 0.75 | 1.00 | 0.60 | 27% |
| Livestock&nbsp;decline&nbsp;(fodder&nbsp;shortage) | atlas,&nbsp;no&nbsp;gate | 6 | 5 | 1 | 0 | 0 | 0 | 0 | 0.83 | 0.50 | 0.91 | 0.83 | 1.00 | 81% |
| Livestock&nbsp;decline&nbsp;(fodder&nbsp;shortage) | sheet | 6 | 5 | 0 | 0 | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 36% |
| Multi&#8209;sector&nbsp;vulnerability&nbsp;(caste) | atlas | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0.67 | – | 0.80 | 1.00 | 0.67 | 42% |
| Multi&#8209;sector&nbsp;vulnerability&nbsp;(caste) | atlas,&nbsp;no&nbsp;gate | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0.67 | – | 0.80 | 1.00 | 0.67 | 42% |
| Multi&#8209;sector&nbsp;vulnerability&nbsp;(caste) | sheet | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0.67 | – | 0.80 | 1.00 | 0.67 | 32% |

**Not scored:** livelihood.agroforestry (no labels); livelihood.fishery (no labels); socio-economic.health (no labels)

## Changes made to the atlas rules

Changes made to the atlas rules as a result of the ground-truth check. Each entry gives the date, the pathway and rule, the change, and its effect on this ground truth and on the share of the 4,598 sample MWS where it fires. The sheet rules (`knowledge/sheet_rules.json`) are not changed.

| Date | Rule | Change | Effect&nbsp;on&nbsp;the&nbsp;ground&nbsp;truth&nbsp;and&nbsp;the&nbsp;sample&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; |
|---|---|---|---|
| 21&nbsp;Nov | Vulnerability:<br>multidimensional vulnerability | Trigger lowered from 3 of 6 dimensions (2 of 3 where only three had data) to 2 of 6. | Recall 0 → 2 of 3. All three labelled positives had exactly two dimensions on. There are no negative labels, so false alarms cannot be measured. Fires in 42% of the atlas sample MWS (was 23%). |
| 21&nbsp;Nov | Drought:<br>kharif drought | Trigger `s_drought_weeks or s_drought_years` became `s_drought_weeks or s_drought_years or (s_dry_spells and ctx_semi_arid)`: frequent dry spells now trigger it in semi-arid areas (rain_norm < 900 mm). Intensity takes `min(s_dry_spells, ctx_semi_arid)` as a third term, so a dry-spell-only trigger has a non-zero intensity. Unstable sowing stays in the drought group. | Drought pathway: hits 1 → 3 of 6, false alarms 4 → 6 of 17, balanced accuracy 0.47 → 0.57. Kharif drought fires in 53% of applicable sample MWS (was 11%), and in 922 of 1,238 Pune MWS. |
| 21&nbsp;Nov | Low yield:<br>declining intensity | Trigger `(s_ci_decline and s_crop_area_decline) or either at its severe level` became `s_ci_decline or s_crop_area_decline`. Intensity unchanged (the average of the two grades, so one decline gives about half the intensity of both). Farmland abandonment still counts towards low yield. | Low-yield pathway: hits 2 → 5 of 7, false alarms 3 → 7 of 16, balanced accuracy 0.55 → 0.64. Declining intensity fires in 30% of applicable sample MWS (was 14%), and in 568 of 1,238 Pune MWS. |
| 22&nbsp;Nov | Drought:<br>kharif drought | Trigger now also requires a rainfall-limited setting: `... and ntrue(ctx_low_kharif_rain, ctx_runoff_loss, ctx_dry_year) >= 2`. New context signals: `ctx_low_kharif_rain` (`rain_norm < 600 or kharif_rain_share < 0.66`; `kharif_rain_share` from `hydrological_seasonal`), `ctx_runoff_loss` (`runoff_ratio > 0.2`), `ctx_dry_year` (`precip_min < 400`). | Drought pathway: hits 3 of 6 (unchanged), false alarms 6 → 3, balanced accuracy 0.57 → 0.66. Kharif drought fires in 27% of applicable sample MWS (was 53%); Pune 681 of 1,238 (was 922). |
| 22&nbsp;Nov | Irrigation:<br>rabi water shortfall | Gate `sys_surface_irrigated` (tank + canal ≥ 10%) replaced by `sys_irrigated_cropland` (`double_share >= 0.5`; a gate on the irrigated slice of cropland, not a new archetype). Trigger `s_rabi_water_drop and ntrue(s_swb_shrinking or s_swb_rabi_trend, s_soge_stage or s_wl_fall, ctx_no_canal and ctx_no_river, ctx_low_nrega_water) >= 1`, with new variable `rabi_kharif_water = mean(div(swb.rabi_area, swb.kharif_area))` and signal `s_rabi_water_drop` (< 0.995, severe 0.5). Waterlogging unchanged. | Irrigation pathway: hits 0 → 6 of 6, false alarms 1 → 2, balanced accuracy 0.47 → 0.94. Rabi shortfall fires in 39% of applicable sample MWS (was 0.3%). Found while looking at these labels, so it needs confirming on new ones. |
| 22&nbsp;Nov | Low yield:<br>farmland abandonment,<br>declining intensity | Both now also require `ctx_under_sown or ctx_single_season`, from a new cropping-regime context dimension (intensive CI ≥ 1.5; under-sown CI < 1.5 and kharif sown < 85%; single-season CI < 1.2 and kharif fully sown; moderate). New variable `kharif_sown_mean = mean(drought.kharif_cropped_area)`. | Low yield: hits 5 → 4 of 7, false alarms 7 → 3, balanced accuracy 0.64 → 0.69. Declining intensity fires in 23% of applicable sample MWS (was 30%); abandonment 16% (unchanged share, fewer MWS). |
| 22&nbsp;Nov | Soil:<br>nutrient deficiency | Trigger `ntrue(s_n_low, s_p_low, s_k_low, s_oc_low) >= 2` became `ntrue(s_n_very_low, s_p_medium, s_k_medium, s_oc_low) >= 2`. New: P below 25 and K below 280 (Soil Health Card medium/high boundaries) over ≥ 80% of cropland (severe 95%); N below 140 over ≥ 80% (severe 95%). OC unchanged. | Soil: hits 2 → 4 of 5, false alarms 11 → 4, balanced accuracy 0.40 → 0.79. Fires in 31% of applicable sample MWS (was 53%). |
| 22&nbsp;Nov | Forest:<br>tree cover loss | Added `or (sys_forest and s_gain_below_loss)`, with new variable `tree_gain_loss_ratio = div(tci.total_tree_cover_increase_area, tcd.total_tree_cover_decrease_area)` and signal `s_gain_below_loss` (≤ 0.7, severe 0.3). | Forest: hits 4 → 5 of 8, false alarms 1 (unchanged), balanced accuracy 0.62 → 0.69. |
| 22&nbsp;Nov | Context classes<br>(bug fix) | The saline aquifer and groundwater-category classes now match the API's spellings ("Salinity", "Semi Critical", "Over Exploited") as well as CGWB's. | `s_saline` can now fire: drinking-water salinity is flagged in 49 Amaravati MWS (was none). |
| 22&nbsp;Nov | Drought:<br>unstable sowing | Trigger `s_kharif_min or s_kharif_cv` became `(s_kharif_min or s_kharif_cv) and ntrue(ctx_low_kharif_rain, ctx_runoff_loss, ctx_dry_year) >= 2`, the same rainfall-limited setting as kharif drought. Gate `sys_rainfed` unchanged. | Drought: false alarms 3 → 1, balanced accuracy 0.66 → 0.72. |
| 22&nbsp;Nov | Drought:<br>kharif drought | New signal `s_drought_worst` (variable `dr_modsev_max`, the worst season's moderate+severe drought weeks; ≥ 6, severe 10) added to the trigger and intensity. Gate `sys_rainfed_or_tank` (rainfed + tank ≥ 15%) replaced by `sys_cropland` (cropland archetypes ≥ 10%). | Worst season: hits 3 → 4 (Kalamnuri), balanced accuracy 0.72 → 0.80. Cropland gate: hits 4 → 5 (Jatara), balanced accuracy 0.80 → 0.89. Drought pathway fires in 27% of the sample (was 22%). |
| 22&nbsp;Nov | Low yield:<br>declining intensity | New variable `ci_endpoint_change = late(ci.cropping_intensity, 2) - early(ci.cropping_intensity, 2)` and signal `s_ci_fell` (< −0.001, severe −0.2), following the sheet's sig_02. Trigger `(s_ci_decline or s_ci_fell or s_crop_area_decline) and (ctx_under_sown or ctx_single_season)`; intensity uses `max(s_ci_decline, s_ci_fell)`. | Low yield: hits 4 → 5 (Kurupam), false alarms 3, balanced accuracy 0.69 → 0.76. Pathway sample 29% → 33%. |
| 22&nbsp;Nov | Soil:<br>nutrient deficiency (s_oc_low) | Organic carbon counts over ≥ 80% of cropland, severe 95% (was 50% / 80%), the same shares as N, P and K. | Soil: false alarms 4 → 3 (Sihora), balanced accuracy 0.79 → 0.82. Pathway sample 33% → 29%. |
| 22&nbsp;Nov | Forest:<br>fringe degradation | New signal `s_farm_degradation` (`degr_frac` ≥ 0.04, severe 0.08), following the sheet's sig_01. Trigger `s_fringe_loss or s_farm_degradation`; intensity `100 * max(s_fringe_loss, s_farm_degradation) * (0.8 + 0.2 * max(ctx_mfp_dependent, s_livestock_dense))`. | Forest: hits 5 → 6 of 8 (Niwas), false alarms 1, balanced accuracy 0.69 → 0.75. Fringe degradation fires in 14% of the sample (was 8%). |
| 22&nbsp;Nov | Fodder:<br>commons degradation | Trigger adds `s_shrub_tree_loss_ha` (new variable `grass_tree_loss_ha`, trees lost in shrub-tree commons > 2 ha, severe 10 ha; sheet sig_01) and `s_fringe_loss` (forest-edge loss; sheet sig_02), with both in the intensity. Gate `sys_pastoral` (pastoral ≥ 5%) unchanged. | Fodder (livestock decline): hits 1 → 3 of 5 (Karera, Begun, Mudgal), false alarms 0, balanced accuracy 0.60 → 0.80. Pathway sample 8% → 27%. |
| 22&nbsp;Nov | Forest:<br>tree cover loss | Trigger adds `or (s_forest_to_farm_rel and ctx_large_forest)`: forest converted to farm ≥ 6% of the forest area (severe 12%; new variables `forest_to_farm_rel`, `forest_area_ha`) where the MWS has ≥ 600 ha of forest; sheet sig_03. | Forest: hits 6 → 8 of 8 (Nandapur, Gogunda), false alarms 1, balanced accuracy 0.75 → 0.88. Pathway sample 34% → 41%. |
| 22&nbsp;Nov | Archetypes:<br>pastoral, peri-urban | Presence thresholds lowered to match the gates: pastoral 10% → 5% (`sys_pastoral`), peri-urban 8% → 3% (`ps_peri_urban`). The cropland gate stays a summed 10% (`sys_cropland`), not per-archetype presence; documented on the signal. | No rule result changes. Pastoral is listed as present in 29% of sample MWS (was 13%), peri-urban in 23% (was 6%). |

Data handling changes that affect both rule sets: nitrogen percentiles of 0 are read as missing (CS-91, 21 Nov 2026). From 22 Nov 2026 the fetcher keeps each tehsil's full API response, so new datasets are extracted locally.

## Pathway by pathway: original rule, changes made, options tested

Pathway by pathway: the atlas rule as it was before the ground-truth check, the changes made, the result now compared with the sheet, and the options tested but not adopted. Options listed under "Tested, not adopted" were scored and left out; untested ideas have been removed. Figures are for the 22 Nov 2026 run.
- **Balanced accuracy** ("BA") is the mean of recall and specificity.
- **"Sample"** is the share of the 4,598 atlas sample MWS where a rule fires. A rule that wins on these labels but fires in most of the sample is not a real gain.
- **Testing options:** `python tools/groundtruth_whatif.py` scores further candidates without changing any rule.

The options were chosen while looking at the same few labels they are scored on, so the gains are optimistic. Prefer options with a clear mechanism, and confirm them on new labels.

### Drought (6 positives, 17 negatives)

**Original rule.**
- `kharif_drought`: `s_drought_weeks or s_drought_years`.
- `unstable_sowing`: `s_kharif_min or s_kharif_cv`.
- Both apply where rainfed or tank farming covers ≥ 15% of the MWS.

BA 0.47, sample 12%.

**Changes made.**
- **21 Nov:** frequent dry spells also trigger kharif drought in semi-arid areas: `... or (s_dry_spells and ctx_semi_arid)`.
- **22 Nov:** kharif drought fires only in a rainfall-limited setting, at least two of:
  - `ctx_low_kharif_rain`: rain_norm < 600, or under 66% of rain in kharif;
  - `ctx_runoff_loss`: runoff > 20%;
  - `ctx_dry_year`: a year below 400 mm.

  `kharif_rain_share` comes from `hydrological_seasonal`, fetched for all sample and ground-truth tehsils on 22 Nov.
- **22 Nov (adopted):** unstable sowing also needs the rainfall-limited setting: `(s_kharif_min or s_kharif_cv) and ntrue(ctx_low_kharif_rain, ctx_runoff_loss, ctx_dry_year) >= 2`. Gate `sys_rainfed` unchanged.
- **22 Nov (adopted):** new worst-season signal `s_drought_worst` (`dr_modsev_max`, the worst season's moderate+severe drought weeks, ≥ 6, severe 10) as a fourth drought pattern in kharif drought, and in its intensity.
- **22 Nov (adopted):** kharif drought is gated on `sys_cropland` (cropland archetypes ≥ 10%) instead of `sys_rainfed_or_tank` (rainfed + tank ≥ 15%). Drought hits the kharif crop on all cropland, including farms classed as irrigated by their rabi crop; the rainfall-limited setting now does the filtering.

**Now.** Atlas BA 0.89 (5 hits, 1 false alarm), sample 27%. Sheet BA 0.92 (5 hits, 0 false alarms), sample 26%.

| Step | Hits / false alarms | BA | Sample |
|---|---|---|---|
| Before the 22 Nov changes | 3 / 3 | 0.66 | 22% |
| + unstable sowing in the rainfall-limited setting | 3 / 1 | 0.72 | 19% |
| + worst-season signal | 4 / 1 | 0.80 | 20% |
| + cropland gate | 5 / 1 | 0.89 | 27% |

**Remaining errors.**
- **False alarm:** *Aruppukkottai* (both kharif drought and unstable sowing fire; the sheet does not flag it).
- **Miss:** *Ghatanji* has frequent dry spells but is classed sub-humid on raw CoRE rainfall, because its district has no rainfall normal. The sheet misses it too.

**Tested, not adopted.**

| Option | Type | Hits / false alarms | BA | Sample |
|---|---|---|---|---|
| Dry spells count in any climate, with the rainfall setting | threshold | 5 / 3 | 0.83 | 38% |

- **Merging with the sheet:** atlas OR sheet BA 0.89 (equals the atlas); AND 0.92 (equals the sheet), sample 20%.
- **Rainfall normals** for the ground-truth districts (would likely bring in Ghatanji) cannot be tested until the normals are added; see "Still open".

### Irrigation (6 positives, 17 negatives)

**Original rule.**
- `rabi_water_shortfall`: `(s_swb_rabi_persist_low or s_swb_rabi_trend) and (s_dbl_falling or s_soge_stage)`, where tank + canal irrigation ≥ 10%.
- `waterlogging`: `s_wl_rise and ctx_flat`, where canal ≥ 10%.

BA 0.47, sample 5%.

**Changes made, 22 Nov.**
- **Gate:** rabi water shortfall is gated on `sys_irrigated_cropland` (double or triple cropping on ≥ 50% of cropland). This is the irrigated slice of cropland before it is split into the groundwater, canal and tank archetypes, not a new archetype.
- **Trigger:** `s_rabi_water_drop` (mean rabi/kharif water-area ratio < 0.995) plus at least one support:
  - water bodies shrinking;
  - SOGE stressed or water level falling;
  - no canal and no river;
  - few NREGA water works.
- **Waterlogging:** unchanged.

**Now.** Atlas BA 0.94 (6 hits, 2 false alarms), sample 28%. Sheet BA 0.91 (6 hits, 3 false alarms), sample 24%.

**Tested, not adopted.**

| Option | Type | Hits / false alarms | BA | Sample |
|---|---|---|---|---|
| Where an MWS has no water bodies (no rabi/kharif ratio), groundwater evidence alone (SOGE stressed or water level falling) with no canal and no river | structural | 6 / 2 (unchanged) | 0.94 | 29% (undecided 5% → 0%) |

- **Merging with the sheet:** atlas AND sheet BA 0.97 (6 hits, 1 false alarm), sample 15%. Requiring both beats either alone here.
- **Caution:** the rule in force was found by looking at these labels, so confirm it on new ones before relying on it. The groundwater-only option changes no label, so it can only be judged on new labels or in the field.

### Low yield (7 positives, 16 negatives)

**Original rule.**
- `farmland_abandonment`: `s_farm_to_scrub`.
- `declining_intensity`: `(s_ci_decline and s_crop_area_decline)`, or either at its severe level.
- Both apply where cropland ≥ 10%.

BA 0.55, sample 25%.

**Changes made.**
- **21 Nov:** declining intensity fires on either decline: `s_ci_decline or s_crop_area_decline`.
- **22 Nov:** both rules fire only in an under-sown or single-season cropping regime, from a new cropping-regime context dimension with four classes:
  - intensive: CI ≥ 1.5, the same cut-off as `ctx_high_ci`;
  - under-sown: kharif sown < 85%, from `kharif_sown_mean`;
  - single-season: CI < 1.2;
  - moderate.
- **22 Nov (adopted):** any fall in cropping intensity between the first two and last two years also counts, as in the sheet's sig_02: new variable `ci_endpoint_change = late(ci.cropping_intensity, 2) - early(ci.cropping_intensity, 2)` and signal `s_ci_fell` (< −0.001, severe −0.2). Trigger `(s_ci_decline or s_ci_fell or s_crop_area_decline) and (ctx_under_sown or ctx_single_season)`; intensity `100 * avg(max(s_ci_decline, s_ci_fell), s_crop_area_decline) * (0.7 + 0.3 * max(s_soge_stage, s_drought_years, s_farm_to_scrub))`.

**Now.** Atlas BA 0.76 (5 hits, 3 false alarms), sample 33%. Sheet BA 0.97 (7 hits, 1 false alarm), sample 35%.

**Remaining errors.**
- **Misses:**
  - *Kadana* fails the 10% cropland gate.
  - *Bijawar* is intensive (CI 1.73), so the cropping-regime context excludes it.
- **False alarms:**
  - *Parner*: abandonment.
  - *Aruppukkottai*: declining intensity.
  - *Maddur*: declining intensity (the sheet flags it too).

**Tested, not adopted.**

| Option | Type | Hits / false alarms | BA | Sample |
|---|---|---|---|---|
| Cropped-area decline not counted | structural | 5 / 2 | 0.79 | 30% |
| CI decline at −0.01 a year instead of −0.02 | threshold | 5 / 3 | 0.76 | 34% |
| Abandonment not counted towards low yield | structural | 3 / 2 | 0.65 | 26% |
| Context also groundwater-stressed with dry spells (sheet sig_04) | structural | 6 / 6 | 0.74 | 36% |
| Or little second-season cropping (triple < 2%, kharif-only < 10% of the MWS) in the cropping-regime context (sheet sig_03) | new trigger | 5 / 4 | 0.73 | 37% |

- **Merging with the sheet:** atlas OR sheet BA 0.91 (7 hits, 3 false alarms); AND 0.83 (5 hits, 1 false alarm).
- **Cropped-area decline not counted** is the only gain, by removing one false alarm (Aruppukkottai), and it drops a mechanism the atlas uses elsewhere. It needs new labels before adoption.
- **Why the sheet does better:** it has no cropland gate (Kadana has 9% cropland; the 10% cropland gate is kept, see "System gates and archetype presence"), and its abandonment signal is limited to small MWS, which leaves out Parner. Its sig_03 and sig_04 pieces do not help in the atlas: sig_03 fires only where the atlas already fires or is gated out, and sig_04 brings in Bijawar with three false alarms.

### Soil degradation (5 positives, 18 negatives)

**Original rule.**
- `nutrient_deficiency`: `ntrue(s_n_low, s_p_low, s_k_low, s_oc_low) >= 2`, using Soil Health Card "low" limits (N < 280, P < 10, K < 110, OC < 0.5%) over ≥ 50% of cropland.
- `erosion`: `ctx_sloping and s_runoff_high and s_cultivated`.

BA 0.40, sample 52%. P and K never fired and N fired almost everywhere.

**Changes made, 22 Nov.** `ntrue(s_n_very_low, s_p_medium, s_k_medium, s_oc_low) >= 2`:
- P < 25 and K < 280 (the Card's medium/high boundaries) over ≥ 80% of cropland;
- N < 140 over ≥ 80%;
- OC < 0.5% over ≥ 80% (**adopted 22 Nov**; was ≥ 50%), severe 95%, the same shares as the other nutrients.

Nitrogen zeros are read as missing (CS-91).

**Now.** Atlas BA 0.82 (4 hits, 3 false alarms), sample 29%. Sheet BA 0.84 (4 hits, 2 false alarms), sample 22%.

**Remaining errors.**
- **Miss:** *Kadana* fails the 10% cropland gate, and has no deficient nutrient on any measure; only half its cropland has very low N.
- **False alarms:**
  - *Bankura* and *Bichhiya*: P and K medium only, with no organic-carbon or nitrogen deficiency.
  - *Mau*: flagged by the sheet as well.

**Tested, not adopted.**

| Option | Type | Hits / false alarms | BA | Sample |
|---|---|---|---|---|
| P and K count only over ≥ 95% of cropland | threshold | 3 / 1 | 0.77 | 23% |
| Two deficient nutrients, at least one of them OC or very-low N (organic matter as an anchor) | structural | 2 / 1 | 0.67 | 20% |
| Erosion without the runoff condition | threshold | 4 / 4 | 0.79 | 37% |

- **Merging with the sheet:** atlas AND sheet BA 0.87 (4 hits, 1 false alarm), sample 18%; OR 0.79.

### Forest degradation (8 positives, 4 negatives)

**Original rule.**
- `tree_cover_loss`: `s_net_tree_loss or (s_forest_to_farm and s_net_tree_neg)`, where tree cover ≥ 15%. Net loss ≥ 2% of the MWS; forest to farm ≥ 5% of the MWS.
- `fringe_degradation`: pooled percentiles (changed 21 Nov from a fixed 5% that fired almost everywhere).
- `fire`.

BA 0.62, sample 29%.

**Changes made, 22 Nov.**
- Added `or (sys_forest and s_gain_below_loss)` to tree-cover loss. This counts tree-cover gain ≤ 0.7 of loss (`tree_gain_loss_ratio`) where forest ≥ 10%, so loss is judged against regrowth.
- **Adopted:** farmland degradation in fringe degradation, as in the sheet's sig_01: new signal `s_farm_degradation` (`degr_frac`, farmland turned to barren, scrub or built-up ≥ 4% of the MWS, severe 8%). Trigger `s_fringe_loss or s_farm_degradation`; intensity `100 * max(s_fringe_loss, s_farm_degradation) * (0.8 + 0.2 * max(ctx_mfp_dependent, s_livestock_dense))`. Gate `sys_forest` unchanged.
- **Adopted:** forest converted to farm relative to the forest, where the forest is large, as in the sheet's sig_03: new variables `forest_to_farm_rel = div(forest_to_farm_frac, f_forest)` and `forest_area_ha = f_forest * area`; signal `s_forest_to_farm_rel` (≥ 0.06, severe 0.12) and context `ctx_large_forest` (`forest_area_ha >= 600`). Tree-cover loss adds `or (s_forest_to_farm_rel and ctx_large_forest)`, with `min(s_forest_to_farm_rel, ctx_large_forest)` in its intensity.

**Now.** Atlas BA 0.88 (8 hits, 1 false alarm), sample 41%. Sheet BA 0.88 (8 hits, 1 false alarm), sample 46%.

| Step | Hits / false alarms | BA | Sample |
|---|---|---|---|
| Original rule | 4 / 1 | 0.62 | 29% |
| + tree-cover gain below 0.7 of loss | 5 / 1 | 0.69 | 30% |
| + farmland degradation in fringe degradation | 6 / 1 | 0.75 | 34% |
| + forest to farm ≥ 6% of the forest, forest ≥ 600 ha | 8 / 1 | 0.88 | 41% |

**Remaining error.** *Kasdol*, a negative label with a real net loss (the sheet flags it too).

**Caution on the 600 ha condition.** It is an absolute area: only 27% of sample MWS have 600 ha of forest, so forest-to-farm conversion relative to the forest cannot trigger in smaller forested MWS. On these labels the cut-off is what separates Nandapur (696 ha) from a negative Bichhiya MWS (520 ha, 10% converted): at 500 ha BA is 0.75, at 300 ha 0.62.

**Tested, not adopted.**

| Option | Type | Hits / false alarms | BA | Sample |
|---|---|---|---|---|
| Gross tree-cover loss ≥ 5% of the MWS | measure | 8 / 3 | 0.62 | 58% |
| Forest to farm ≥ 6% of the forest, with the 10% forest gate instead of 600 ha | measure | 8 / 3 | 0.62 | 50% |

- **Merging with the sheet:** atlas AND sheet and atlas OR sheet both BA 0.88, the same as either alone.
- **Few negatives:** with only 4 negative labels, false-alarm rates here are unreliable.

### Groundwater (1 positive, 22 negatives)

**Original rule.** Over-extraction on SOGE stage ≥ 70% (with local support since 21 Nov), irrigation expansion, and a water-balance deficit. BA 0.34; no ground-truth change made.

**Now.** The atlas misses Jawhar (gated out) and flags 7 negatives in SOGE-stressed blocks. The sheet BA 0.82 rests on its single hit, with 8 false alarms.

With one positive, neither rule set can be tuned meaningfully; more positive labels are needed (see "Still open"). No options were tested.

### Livestock decline, read as fodder shortage (5 positives, 1 negative)

**Original rule.** `grazing_pressure` (livestock units per ha of open commons ≥ 5) and `commons_degradation` (`s_grass_tree_loss or s_shrub_ndvi_decline or (s_commons_shrinking and (s_livestock_dense or s_grazing_density))`), where pastoral land ≥ 5%. BA 0.60.

**Changes made, 22 Nov.**
- **Commons degradation trigger (adopted):** two more grazing-land losses count, following the sheet's fodder signals: `s_shrub_tree_loss_ha` (trees lost in shrub-tree commons > 2 ha, severe 10 ha; sheet sig_01) and `s_fringe_loss` (forest-edge loss; sheet sig_02). Trigger `s_grass_tree_loss or s_shrub_tree_loss_ha or s_shrub_ndvi_decline or s_fringe_loss or (s_commons_shrinking and (s_livestock_dense or s_grazing_density))`. Grazing pressure is unchanged.
- **Pastoral presence (adopted):** the pastoral archetype is listed as present at 5% of the MWS (was 10%), the same share as the livestock gate. Rule results do not change.

**Now.** Atlas BA 0.80 (3 hits, 0 false alarms), sample 27% (was 8%). Sheet BA 1.00 (5 hits, 0 false alarms), sample 36%.

**Remaining errors.** *Bankura* and *Asnawar* have under 1.5% pastoral land, so the gate excludes them. Both are livestock-dense farming MWS (1.49 and 0.40 livestock units per ha), not commons-based pastoral systems.

**Tested, not adopted.**

| Option | Type | Hits / false alarms | BA | Sample |
|---|---|---|---|---|
| Gate pastoral ≥ 3% AND livestock density ≥ 0.3 | system gate | 2 / 0 | 0.70 | 22% (8% undecided) |
| Gate pastoral ≥ 5% OR livestock density ≥ 0.3 (mixed crop-livestock as livestock systems) | system gate | 5 / 1 | 0.50 | 64% (18% undecided) |
| Livestock density alone as the trigger (≥ 0.3, ≥ 0.5 or ≥ 1 unit per ha) | trigger | 4 / 1 at best | 0.40 at best | 33–56% (23% undecided) |

- **Declined:** mixed crop-livestock MWS are not treated as livestock systems (22 Nov), so the OR gate is not used.
- **Density as a trigger:** density does not separate the labels; the one negative (Maddur, 0.71) is denser than four of the five positives.
- **Merging with the sheet:** atlas OR sheet BA 1.0 (equals the sheet); AND 0.80.

### Livestock water (1 positive, 5 negatives)

**Original rule.** Livestock density with little summer water, where pastoral land ≥ 5%. No change made.

**Now.** The only positive (Maddur, 2% pastoral land) is gated out. The sheet finds it. The atlas rule fires in under 1% of the sample.

**Tested, not adopted.**

| Option | Type | Hits / false alarms | BA | Sample |
|---|---|---|---|---|
| No pastoral-land gate | system gate | 0 / 0 | 0.50 | 3% (8% undecided) |

- **Merging:** atlas OR sheet equals the sheet. One positive is too few to tune on.

### Siltation (3 positives, no negatives)

**Original rule.** Rabi water falling together with low rabi retention, where water bodies ≥ 0.5%. No change made.

**Now.** The atlas finds none; the sheet finds all three. The sheet fires in 59% of the sample.

**Tested, not adopted.**

| Option | Type | Hits / false alarms | BA | Sample |
|---|---|---|---|---|
| Also trigger on a rabi/kharif water drop (`s_rabi_water_drop`), where water bodies ≥ 0.5% | new trigger | 2 / 0 | – | 23% |
| The same, only with shrinking water bodies | new trigger | 0 / 0 | – | 8% |

- **Labels:** with no negative labels, false alarms cannot be measured, so neither option can be judged yet.

### Multi-sector vulnerability, read from "caste" (3 positives, no negatives)

**Original rule.** 3 of 6 dimensions, 0 hits.

**Changes made, 21 Nov.** 2 of 6, which gives 2 hits, the same as the sheet, at a 42% sample rate.

- **Merging:** atlas OR sheet finds all 3.
- **Labels:** with no negatives, false alarms cannot be measured. No options were tested.

### System gates and archetype presence (decided 22 Nov)

A system gate decides where a rule is checked; an archetype's presence threshold decides whether it is listed as describing the MWS. Three gaps between them were reviewed:
- **Cropland:** gates test the cropland total (`sys_cropland`, all cropland archetypes summed ≥ 10%), not whether any one archetype is present (15%; tank 10%). Kept as it is (option A). A per-archetype gate would skip 12% of the sample that has ≥ 15% cropland split across archetypes; on the labels it lowered low yield to 0.55 and soil to 0.74. A summed 15% gate lowered low yield to 0.69 and soil to 0.72 (losing Kurupam, 12% cropland).
- **Pastoral:** presence lowered from 10% to 5% to match the gate (option B). Raising the gate to 10% instead would have checked 13% of the sample rather than 29%, with no ground-truth gain.
- **Peri-urban:** presence lowered from 8% to 3% to match the production-system threshold (option B). Raising the urban-encroachment gate to 8% changed its sample rate only from 10% to 9%, because most MWS reach it through the cropland ≥ 20% condition.

### Using both rule sets together

The per-pathway merge figures above come from the tables below, which are recomputed on each run.

Across all pathways, the label was positive in:
- 32 of 41 cases where both fire (78%);
- 10 of 16 where only the sheet fires (63%);
- 1 of 9 where only the atlas fires (11%);
- 2 of 79 where neither fires (3%).

So "neither" is a reliable negative and "both" is now slightly more reliable than the sheet alone. The atlas firing alone is still mostly a false alarm.

### Where things stand and what comes next

Rule tuning on these labels is done. Every remaining option either scores worse or wins by flipping a single labelled MWS. With about 23 labels per pathway, adopting such options would fit the rules to these labels rather than improve them.

| Pathway | Atlas BA | Sheet BA | Remaining gap |
|---|---|---|---|
| Drought | 0.89 | 0.92 | Ghatanji, which needs a rainfall normal (below) |
| Irrigation | 0.94 | 0.91 | – |
| Soil degradation | 0.82 | 0.84 | one false alarm |
| Forest degradation | 0.88 | 0.88 | – |
| Livestock decline (fodder) | 0.80 | 1.00 | Bankura, Asnawar |
| Low yield | 0.76 | 0.97 | Kadana, Bijawar, plus false alarms |

The two large gaps are mostly deliberate:
- **Kadana** (low yield) has 9% cropland, below the 10% cropland gate, which is kept.
- **Bankura and Asnawar** (fodder) are mixed crop-livestock MWS. These are not treated as livestock systems (decided 22 Nov).
- **Bijawar** (low yield) is intensively cropped. It can only be reached by adding three false alarms.

Further gains are expected from data and from how the two rule sets are used, not from more threshold changes:
1. **More labels.** This matters most. Add negatives for siltation, forest, fodder, livestock water and vulnerability, and positives for groundwater and livestock water. New labels also show whether today's gains hold, since the rules were tuned on these labels.
2. **Rainfall normals for the ground-truth districts** (explained below). This would likely bring in Ghatanji for drought. On hold.
3. **Using the two rule sets together.** Either show "both", "atlas only" or "sheet only" as a confidence level, or require both rule sets for irrigation and soil, where that beats either alone. Not decided.
4. **Pune review.** Kharif drought fires in 55% of Pune MWS and declining intensity in 30%. Check these rates with people who know Pune on the ground.

### Rainfall normals (on hold)

**What they are.** A district's rainfall normal is its long-term average annual rainfall, the official figure (typically from IMD) averaged over several decades.

**Why the atlas needs them.** CoRE Stack precipitation for 2017–24 is spatially over-smoothed and often departs from what a district receives (CS-68). For example, Srikakulam comes out at 1,742 mm against a normal of 1,162 mm, and Godda at 1,008 mm against about 1,530 mm. Several rules depend on the rainfall level:
- the semi-arid class (below 900 mm), which decides whether dry spells count as drought and which drought-week threshold applies;
- the low-rainfall context `ctx_low_kharif_rain` (below 600 mm);
- the very-dry-year context `ctx_dry_year` (a year below 400 mm).

**How the correction works.** For each district the pipeline computes

`rain_norm = CoRE rainfall of the MWS × (district normal ÷ district median of CoRE rainfall)`

This keeps the pattern across MWS within the district but anchors its level to the official normal. The normals are kept in `knowledge/contexts.json` under `rainfall_normals`.

**The gap.**
- **Atlas districts:** six of the eight have normals. Pune is deliberately left unscaled, because its rainfall ranges from about 450 mm to over 2,000 mm across the district, so a single district figure would mislead.
- **Ground-truth districts:** no normals have been added for the 20-odd districts the labels come from, so for them `rain_norm` is simply the raw CoRE rainfall.

**Example.** Ghatanji's raw CoRE rainfall is 1,184 mm, so it is classed sub-humid. Its frequent dry spells therefore do not count as drought, because dry spells count only in semi-arid areas. If Yavatmal's normal is well below what CoRE reports for the district, the rescaled value could fall below 900 mm. Ghatanji would then become semi-arid and be caught. This is expected, not tested.

**What adding them involves.**
1. Look up the normal for each ground-truth district from IMD.
2. Add the values to `contexts.json`.
3. Rerun the ground-truth check.

It is a data correction, not a rule change. But it shifts every rainfall-based context in those districts, so it can change other drought results in either direction, not only Ghatanji's. It also makes the ground-truth check treat its districts the same way the atlas treats its own.

### Still open
- **Rainfall normals** for the ground-truth districts: on hold (see above).
- **Pune:** kharif drought fires in 55% of Pune MWS and declining intensity in 30%. Review these against Pune field knowledge.
- **MWS without water bodies:** 232 sample MWS have no rabi/kharif water ratio, so rabi water shortfall cannot be decided there. Groundwater evidence alone was tested; it changes no label, so it needs new labels or field checks.
- **More labels:** add negative labels for siltation, forest, fodder, livestock water and vulnerability, and positive labels for groundwater and livestock water.
- **Using both rule sets:** a confidence level, or requiring both for irrigation and soil. Not decided.

### Combining the atlas and the sheet (computed on this run)

"atlas OR sheet" fires when either fires; "atlas AND sheet" when both do. "sheet AND <rule>" asks the sheet to be confirmed by one atlas sub-pathway; "sheet OR <rule>" adds one atlas sub-pathway to the sheet.

| Pathway | Rules | n | TP | FP | FN | TN | Unknown | No data | Accuracy | Balanced accuracy | F1 | Precision | Recall | Sample |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Groundwater | atlas&nbsp;OR&nbsp;sheet | 23 | 1 | 10 | 0 | 12 | 0 | 0 | 0.56 | 0.77 | 0.17 | 0.09 | 1.00 | 54% |
| Groundwater | atlas&nbsp;AND&nbsp;sheet | 23 | 0 | 5 | 1 | 17 | 0 | 0 | 0.74 | 0.39 | 0.00 | 0.00 | 0.00 | 22% |
| Groundwater | sheet&nbsp;AND&nbsp;groundwater.over_extraction | 23 | 0 | 5 | 1 | 17 | 0 | 0 | 0.74 | 0.39 | 0.00 | 0.00 | 0.00 | 19% |
| Groundwater | sheet&nbsp;OR&nbsp;groundwater.over_extraction | 23 | 1 | 10 | 0 | 12 | 0 | 0 | 0.56 | 0.77 | 0.17 | 0.09 | 1.00 | 53% |
| Groundwater | sheet&nbsp;AND&nbsp;groundwater.irrigation_expansion | 23 | 0 | 0 | 1 | 22 | 0 | 0 | 0.96 | 0.50 | 0.00 | – | 0.00 | 3% |
| Groundwater | sheet&nbsp;OR&nbsp;groundwater.irrigation_expansion | 23 | 1 | 8 | 0 | 14 | 0 | 0 | 0.65 | 0.82 | 0.20 | 0.11 | 1.00 | 44% |
| Groundwater | sheet&nbsp;AND&nbsp;groundwater.water_balance_deficit | 23 | 0 | 1 | 1 | 21 | 0 | 0 | 0.91 | 0.48 | 0.00 | 0.00 | 0.00 | 8% |
| Groundwater | sheet&nbsp;OR&nbsp;groundwater.water_balance_deficit | 23 | 1 | 8 | 0 | 14 | 0 | 0 | 0.65 | 0.82 | 0.20 | 0.11 | 1.00 | 46% |
| Drought | atlas&nbsp;OR&nbsp;sheet | 23 | 5 | 1 | 1 | 16 | 0 | 0 | 0.91 | 0.89 | 0.83 | 0.83 | 0.83 | 34% |
| Drought | atlas&nbsp;AND&nbsp;sheet | 23 | 5 | 0 | 1 | 17 | 0 | 0 | 0.96 | 0.92 | 0.91 | 1.00 | 0.83 | 20% |
| Drought | sheet&nbsp;AND&nbsp;drought.kharif_drought | 23 | 5 | 0 | 1 | 17 | 0 | 0 | 0.96 | 0.92 | 0.91 | 1.00 | 0.83 | 19% |
| Drought | sheet&nbsp;OR&nbsp;drought.kharif_drought | 23 | 5 | 1 | 1 | 16 | 0 | 0 | 0.91 | 0.89 | 0.83 | 0.83 | 0.83 | 34% |
| Drought | sheet&nbsp;AND&nbsp;drought.unstable_sowing | 23 | 1 | 0 | 5 | 17 | 0 | 0 | 0.78 | 0.58 | 0.29 | 1.00 | 0.17 | 4% |
| Drought | sheet&nbsp;OR&nbsp;drought.unstable_sowing | 23 | 5 | 1 | 1 | 16 | 0 | 0 | 0.91 | 0.89 | 0.83 | 0.83 | 0.83 | 27% |
| Irrigation | atlas&nbsp;OR&nbsp;sheet | 23 | 6 | 4 | 0 | 13 | 0 | 0 | 0.83 | 0.88 | 0.75 | 0.60 | 1.00 | 37% |
| Irrigation | atlas&nbsp;AND&nbsp;sheet | 23 | 6 | 1 | 0 | 16 | 0 | 0 | 0.96 | 0.97 | 0.92 | 0.86 | 1.00 | 15% |
| Irrigation | sheet&nbsp;AND&nbsp;irrigation.rabi_water_shortfall | 23 | 6 | 1 | 0 | 16 | 0 | 0 | 0.96 | 0.97 | 0.92 | 0.86 | 1.00 | 15% |
| Irrigation | sheet&nbsp;OR&nbsp;irrigation.rabi_water_shortfall | 23 | 6 | 4 | 0 | 13 | 0 | 0 | 0.83 | 0.88 | 0.75 | 0.60 | 1.00 | 35% |
| Irrigation | sheet&nbsp;AND&nbsp;irrigation.waterlogging | 23 | 0 | 0 | 6 | 17 | 0 | 0 | 0.74 | 0.50 | 0.00 | – | 0.00 | 0% |
| Irrigation | sheet&nbsp;OR&nbsp;irrigation.waterlogging | 23 | 6 | 3 | 0 | 14 | 0 | 0 | 0.87 | 0.91 | 0.80 | 0.67 | 1.00 | 26% |
| Low&nbsp;yield | atlas&nbsp;OR&nbsp;sheet | 23 | 7 | 3 | 0 | 13 | 0 | 0 | 0.87 | 0.91 | 0.82 | 0.70 | 1.00 | 45% |
| Low&nbsp;yield | atlas&nbsp;AND&nbsp;sheet | 23 | 5 | 1 | 2 | 15 | 0 | 0 | 0.87 | 0.83 | 0.77 | 0.83 | 0.71 | 23% |
| Low&nbsp;yield | sheet&nbsp;AND&nbsp;productivity.farmland_abandonment | 23 | 2 | 0 | 5 | 16 | 0 | 0 | 0.78 | 0.64 | 0.45 | 1.00 | 0.29 | 8% |
| Low&nbsp;yield | sheet&nbsp;OR&nbsp;productivity.farmland_abandonment | 23 | 7 | 2 | 0 | 14 | 0 | 0 | 0.91 | 0.94 | 0.88 | 0.78 | 1.00 | 42% |
| Low&nbsp;yield | sheet&nbsp;AND&nbsp;productivity.declining_intensity | 23 | 3 | 1 | 4 | 15 | 0 | 0 | 0.78 | 0.68 | 0.55 | 0.75 | 0.43 | 22% |
| Low&nbsp;yield | sheet&nbsp;OR&nbsp;productivity.declining_intensity | 23 | 7 | 2 | 0 | 14 | 0 | 0 | 0.91 | 0.94 | 0.88 | 0.78 | 1.00 | 40% |
| Soil&nbsp;degradation | atlas&nbsp;OR&nbsp;sheet | 23 | 4 | 4 | 1 | 14 | 0 | 0 | 0.78 | 0.79 | 0.61 | 0.50 | 0.80 | 34% |
| Soil&nbsp;degradation | atlas&nbsp;AND&nbsp;sheet | 23 | 4 | 1 | 1 | 17 | 0 | 0 | 0.91 | 0.87 | 0.80 | 0.80 | 0.80 | 18% |
| Soil&nbsp;degradation | sheet&nbsp;AND&nbsp;soil.nutrient_deficiency | 23 | 4 | 1 | 1 | 17 | 0 | 0 | 0.91 | 0.87 | 0.80 | 0.80 | 0.80 | 17% |
| Soil&nbsp;degradation | sheet&nbsp;OR&nbsp;soil.nutrient_deficiency | 23 | 4 | 4 | 1 | 14 | 0 | 0 | 0.78 | 0.79 | 0.61 | 0.50 | 0.80 | 31% |
| Soil&nbsp;degradation | sheet&nbsp;AND&nbsp;soil.erosion | 23 | 0 | 0 | 5 | 18 | 0 | 0 | 0.78 | 0.50 | 0.00 | – | 0.00 | 1% |
| Soil&nbsp;degradation | sheet&nbsp;OR&nbsp;soil.erosion | 23 | 4 | 2 | 1 | 16 | 0 | 0 | 0.87 | 0.84 | 0.73 | 0.67 | 0.80 | 25% |
| Forest&nbsp;degradation | atlas&nbsp;OR&nbsp;sheet | 12 | 8 | 1 | 0 | 3 | 0 | 0 | 0.92 | 0.88 | 0.94 | 0.89 | 1.00 | 54% |
| Forest&nbsp;degradation | atlas&nbsp;AND&nbsp;sheet | 12 | 8 | 1 | 0 | 3 | 0 | 0 | 0.92 | 0.88 | 0.94 | 0.89 | 1.00 | 33% |
| Forest&nbsp;degradation | sheet&nbsp;AND&nbsp;forest.tree_cover_loss | 12 | 8 | 1 | 0 | 3 | 0 | 0 | 0.92 | 0.88 | 0.94 | 0.89 | 1.00 | 26% |
| Forest&nbsp;degradation | sheet&nbsp;OR&nbsp;forest.tree_cover_loss | 12 | 8 | 1 | 0 | 3 | 0 | 0 | 0.92 | 0.88 | 0.94 | 0.89 | 1.00 | 47% |
| Forest&nbsp;degradation | sheet&nbsp;AND&nbsp;forest.fringe_degradation | 12 | 2 | 0 | 6 | 4 | 0 | 0 | 0.50 | 0.62 | 0.40 | 1.00 | 0.25 | 11% |
| Forest&nbsp;degradation | sheet&nbsp;OR&nbsp;forest.fringe_degradation | 12 | 8 | 1 | 0 | 3 | 0 | 0 | 0.92 | 0.88 | 0.94 | 0.89 | 1.00 | 48% |
| Forest&nbsp;degradation | sheet&nbsp;AND&nbsp;forest.fire | 12 | 0 | 0 | 8 | 4 | 0 | 0 | 0.33 | 0.50 | 0.00 | – | 0.00 | 5% |
| Forest&nbsp;degradation | sheet&nbsp;OR&nbsp;forest.fire | 12 | 8 | 1 | 0 | 3 | 0 | 0 | 0.92 | 0.88 | 0.94 | 0.89 | 1.00 | 49% |
| Siltation | atlas&nbsp;OR&nbsp;sheet | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 1.00 | – | 1.00 | 1.00 | 1.00 | 59% |
| Siltation | atlas&nbsp;AND&nbsp;sheet | 3 | 0 | 0 | 3 | 0 | 0 | 0 | 0.00 | – | 0.00 | – | 0.00 | 4% |
| Livestock&nbsp;water | atlas&nbsp;OR&nbsp;sheet | 6 | 1 | 0 | 0 | 5 | 0 | 0 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 51% |
| Livestock&nbsp;water | atlas&nbsp;AND&nbsp;sheet | 6 | 0 | 0 | 1 | 5 | 0 | 0 | 0.83 | 0.50 | 0.00 | – | 0.00 | 0% |
| Livestock&nbsp;decline&nbsp;(fodder&nbsp;shortage) | atlas&nbsp;OR&nbsp;sheet | 6 | 5 | 0 | 0 | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 44% |
| Livestock&nbsp;decline&nbsp;(fodder&nbsp;shortage) | atlas&nbsp;AND&nbsp;sheet | 6 | 3 | 0 | 2 | 1 | 0 | 0 | 0.67 | 0.80 | 0.75 | 1.00 | 0.60 | 19% |
| Livestock&nbsp;decline&nbsp;(fodder&nbsp;shortage) | sheet&nbsp;AND&nbsp;fodder.grazing_pressure | 6 | 0 | 0 | 5 | 1 | 0 | 0 | 0.17 | 0.50 | 0.00 | – | 0.00 | 2% |
| Livestock&nbsp;decline&nbsp;(fodder&nbsp;shortage) | sheet&nbsp;OR&nbsp;fodder.grazing_pressure | 6 | 5 | 0 | 0 | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 37% |
| Livestock&nbsp;decline&nbsp;(fodder&nbsp;shortage) | sheet&nbsp;AND&nbsp;fodder.commons_degradation | 6 | 3 | 0 | 2 | 1 | 0 | 0 | 0.67 | 0.80 | 0.75 | 1.00 | 0.60 | 19% |
| Livestock&nbsp;decline&nbsp;(fodder&nbsp;shortage) | sheet&nbsp;OR&nbsp;fodder.commons_degradation | 6 | 5 | 0 | 0 | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 44% |
| Multi&#8209;sector&nbsp;vulnerability&nbsp;(caste) | atlas&nbsp;OR&nbsp;sheet | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 1.00 | – | 1.00 | 1.00 | 1.00 | 54% |
| Multi&#8209;sector&nbsp;vulnerability&nbsp;(caste) | atlas&nbsp;AND&nbsp;sheet | 3 | 1 | 0 | 2 | 0 | 0 | 0 | 0.33 | – | 0.50 | 1.00 | 0.33 | 20% |

### Agreement as a confidence measure

Each cell gives labelled positives / labels in that tier. If agreement carries information, "both" should be mostly positive and "neither" mostly negative, with the single-rule tiers in between.

| Pathway | Both fire | Sheet only | Atlas only | Neither |
|---|---|---|---|---|
| Groundwater | 0 / 5 | 1 / 4 | 0 / 2 | 0 / 12 |
| Drought | 5 / 5 | – | 0 / 1 | 1 / 17 |
| Irrigation | 6 / 7 | 0 / 2 | 0 / 1 | 0 / 13 |
| Low&nbsp;yield | 5 / 6 | 2 / 2 | 0 / 2 | 0 / 13 |
| Soil&nbsp;degradation | 4 / 5 | 0 / 1 | 0 / 2 | 1 / 15 |
| Forest&nbsp;degradation | 8 / 9 | – | – | 0 / 3 |
| Siltation | – | 3 / 3 | – | – |
| Livestock&nbsp;water | – | 1 / 1 | – | 0 / 5 |
| Livestock&nbsp;decline&nbsp;(fodder&nbsp;shortage) | 3 / 3 | 2 / 2 | – | 0 / 1 |
| Multi&#8209;sector&nbsp;vulnerability&nbsp;(caste) | 1 / 1 | 1 / 1 | 1 / 1 | – |
| **All pathways** | **32 / 41** | **10 / 16** | **1 / 9** | **2 / 79** |

## Locations

| Block | State / District / Tehsil | Status |
|---|---|---|
| aruppukkottai | Tamil Nadu / Virudhunagar / Aruppukkottai | resolved |
| ashti | Maharashtra / Bid / Ashti | resolved |
| asnawar | Rajasthan / Jhalawar / Asnawar | resolved |
| bankura | West Bengal / Bankura / Bankura | resolved |
| begun | Rajasthan / Chittaurgarh / Begun | resolved |
| bero | Jharkhand / Ranchi / Bero | resolved |
| bichhiya | Madhya Pradesh / Mandla / Bichhiya | resolved |
| bijawar | Madhya Pradesh / Chhatarpur / Bijawar | resolved |
| chainpur | Jharkhand / Gumla / Chainpur | resolved |
| ghatanji | Maharashtra / Yavatmal / Ghatanji | resolved |
| girwa | Rajasthan / Udaipur / Girwa | resolved |
| gogunda | Rajasthan / Udaipur / Gogunda | resolved |
| jatara | Madhya Pradesh / Tikamgarh / Jatara | resolved |
| jawhar | Maharashtra / Palghar / Jawhar | resolved |
| kadana | Gujarat / Mahisagar / Kadana | resolved |
| kalamnuri | Maharashtra / Hingoli / Kalamnuri | resolved |
| karauli | Rajasthan / Karauli / Karauli | resolved |
| karera | Rajasthan / Bhilwara / Karera | resolved by uid among 2 candidates |
| kasdol | Chhattisgarh / Baloda Bazar / Kasdol | resolved |
| keonjhar | Odisha / Keonjhar (Kendujhar) / Keonjhar (Kendujhar) | resolved |
| kurupam | Andhra Pradesh / Vizianagaram / Kurupam | resolved |
| maddur | Karnataka / Mandya / Maddur | resolved |
| mau | Uttar Pradesh / Chitrakoot / Mau | resolved by uid among 2 candidates |
| mudgal | Karnataka / Raichur / Mudgal | resolved |
| mulbagal | Karnataka / Kolar / Mulbagal | resolved |
| nandapur | Odisha / Koraput / Nandapur | resolved |
| niwas | Madhya Pradesh / Mandla / Niwas | resolved |
| parner | Maharashtra / Ahamadnagar / Parner | resolved |
| pikmal | Odisha / Baragarh / Pikmal | resolved |
| sapotra | Rajasthan / Karauli / Sapotra | resolved |
| sihora | Madhya Pradesh / Jabalpur / Sihora | resolved |
| vilattikulam | Tamil Nadu / Tuticorin / Vilattikulam | resolved |
