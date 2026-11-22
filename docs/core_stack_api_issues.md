# CoRE Stack public API: issues log for developers

Issues found while using the CoRE Stack public API through the MCP server (`lcl-core-stack-public-api`), organised by the user query that exposed them so each can be reproduced.

- Session dates: 10 October to 16 November 2026
- Bug IDs: `CS-01` to `CS-88`, numbered in order of first appearance. Each ID is one unique issue.
- Each issue is described in full once, under the query where it first appeared. Later queries list it under "Also seen" with only the new evidence.
- All calls went through the MCP tool `call_public_api(api_id, params)`. From Query 9 the same server was reached through the linked computer; behaviour was the same except where noted. The API key was sent as a header and is not shown.

Severity:
- **High**: led or could lead to a wrong conclusion, or blocked the task.
- **Medium**: forced a workaround or left a result ambiguous.
- **Low**: cosmetic or minor.

## Bug index

| ID | Severity | Title | Route | Queries |
|---|---|---|---|---|
| CS-01 | Low | Place-name casing inconsistent within and across routes | Several | 1, 3 |
| CS-02 | Low | Field hints in lookup routes restate field names | `get_mwsid_by_latlon`, `get_admin_details_by_latlon` | 1, 3 |
| CS-03 | High | Coded indicators have no legend | `get_mws_kyl_indicators` | 2, 3, 4 |
| CS-04 | High | Cropped-area fields labelled "ha" but behave like percentages | `get_mws_kyl_indicators` | 2, 3, 4, 9 |
| CS-05 | High | No time period on averages, trends or change figures | `get_mws_kyl_indicators`, `get_tehsil_data` | 2, 3, 4, 9 |
| CS-06 | Medium | `avg_wsr_ratio_*` undefined | `get_mws_kyl_indicators` | 2, 3 |
| CS-07 | Medium | `lulc_plain_category` conflicts with `lulc_crop` and repeats across micro-watersheds | `get_mws_kyl_indicators` | 2, 4 |
| CS-08 | Medium | `describe_public_api` adds nothing beyond the route list | MCP server | 2, 3, 4 |
| CS-09 | Medium | Unit given as "value" for about 20 fields | `get_mws_kyl_indicators` | 2, 3 |
| CS-10 | Medium | Zero cannot be told apart from "no data" | `get_mws_kyl_indicators` | 2, 3 |
| CS-11 | Low | `-9999` sentinel in a text field | `get_mws_kyl_indicators` | 2, 3, 4 |
| CS-12 | Low | Waterbody list bloats the response, little usable content | `get_mws_kyl_indicators` | 2, 3, 4 |
| CS-13 | Low | Mixed data types for the same kind of value | Several | 2, 3 |
| CS-14 | Low | Misspelt field name and unexplained acronyms | `get_mws_kyl_indicators` | 2 |
| CS-15 | High | Large responses cut off, no pagination or filter | `get_village_geometries`, `get_mws_geometries`, `get_tehsil_data` | 3, 4, 9, 14 |
| CS-16 | High | `degradation_cropping_intensity` labelled "ratio", values in the hundreds | `get_mws_kyl_indicators` | 3, 4 |
| CS-17 | Medium | No route from a village to its micro-watersheds | All | 3, 4 |
| CS-18 | Medium | `vill_ID` is "0" for many villages | `get_village_geometries` | 3 |
| CS-19 | Medium | Duplicate village features | `get_village_geometries` | 3 |
| CS-20 | Medium | Micro-watersheds crossing tehsil boundaries attributed inconsistently | `get_mwsid_by_latlon`, `get_tehsil_data` | 3, 4 |
| CS-21 | Medium | Land cover percentages sum to more than 100 | `get_mws_kyl_indicators` | 3, 4 |
| CS-22 | Medium | Several fields constant across very different landscapes | `get_mws_kyl_indicators` | 3 |
| CS-23 | Low | `body` returned as an escaped JSON string | `get_village_geometries`, `get_mws_geometries` | 3, 9 |
| CS-24 | Low | Stale and redundant fields in active locations | `get_active_locations` | 3 |
| CS-25 | Medium | Dataset names undocumented; unknown names handled inconsistently | `get_tehsil_data` | 4, 9 |
| CS-26 | Medium | `fields` filter ignored | `get_mws_kyl_indicators`, `get_mws_data` | 4, 7 |
| CS-27 | Medium | "Forest" used for what is measured as tree cover | `get_tehsil_data`, `get_mws_kyl_indicators` | 4 |
| CS-28 | Low | Village codes outside the range of their neighbours | `get_mws_kyl_indicators` | 2, 4 |
| CS-29 | High | Time series route returns 404 `DistrictSOI matching query does not exist` for Chintamani | `get_mws_data` | 7, 10 |
| CS-30 | Medium | Report route returns 404 `Mws Layer not found` for a micro-watershed that other routes serve | `get_mws_report` | 7 |
| CS-31 | Medium | Tehsil data call for `hydrological_seasonal` hung with no response for 4 minutes | `get_tehsil_data` | 7 |
| CS-32 | Medium | Last record of the fortnightly series is all zeros | `get_mws_data` | 7 |
| CS-33 | Low | `time_step` says "15_days" but dates are 14 days apart | `get_mws_data` | 7 |
| CS-34 | Low | ET values repeat in consecutive pairs | `get_mws_data` | 7 |
| CS-35 | Low | Error responses leak internal exception text and vary in shape | `get_mws_data`, `get_mws_report` | 7 |
| CS-36 | High | Layer URL for the micro-watershed boundaries is broken ("Feature type unknown") | `get_generated_layer_urls` | 9 |
| CS-37 | Medium | `cropping_intensity` denominator and `sum_area` undefined | `get_tehsil_data` | 9 |
| CS-38 | Medium | Micro-watershed count differs between datasets of the same tehsil (114 vs 116) | `get_tehsil_data` | 9 |
| CS-39 | Low | Drainage density layer URL has an empty workspace | `get_generated_layer_urls` | 9 |
| CS-40 | Low | Layer list metadata: empty `style_url`, a raster-named layer typed as vector, no year or period fields | `get_generated_layer_urls` | 9 |
| CS-41 | Medium | `welldepth` and `g` undefined; `welldepth` is labelled "m" but is a scaled copy of `delta_g` | `get_tehsil_data` | 10 |
| CS-42 | Low | Metadata differs between datasets of the same tehsil (no `area` in the hydrology dataset) | `get_tehsil_data` | 10 |
| CS-43 | High | Kharif and rabi surface water areas are near-identical; seasonal fields appear nested and are undefined | `get_tehsil_data` | 11 |
| CS-44 | Medium | Three undefined "total" water areas that disagree (`total_area`, `total_swb_area`, kharif) | `get_tehsil_data` | 11 |
| CS-45 | High | Yearly tree and shrub areas swing by a factor of two and mirror each other | `get_tehsil_data` | 12, 15, 16 |
| CS-46 | Medium | Land cover classes sum to about 94.5% of area; water class names undefined | `get_tehsil_data` | 12 |
| CS-47 | Low | `cropland_area` is zero in every row | `get_tehsil_data` | 12 |
| CS-48 | High | Waterbody routes return 502 `Merged dataset not available for given area` for Chintamani | `get_waterbodies_data_by_admin`, `get_waterbody_data` | 13, 14 |
| CS-49 | Medium | Waterbody layer: a third of features lie outside the tehsil; duplicate and empty attribute columns | GeoServer `swb` layer | 13 |
| CS-50 | Low | Data-entry errors in village names and attribute names | GeoServer layers | 13 |
| CS-51 | Medium | Micro-watershed-to-village mapping is incomplete in three ways | `get_tehsil_data` | 14 |
| CS-52 | Medium | `drought` and `green_credit` datasets return an empty object with status 200 | `get_tehsil_data` | 15, 16 |
| CS-53 | Medium | Groundwater extraction class disagrees between routes; block-level values presented per micro-watershed | `get_tehsil_data`, `get_mws_kyl_indicators` | 15 |
| CS-54 | Low | Inconsistent ID key and partial coverage in `nrega_annual` and `livestock` | `get_tehsil_data` | 15 |
| CS-55 | High | Tree-change datasets disagree: `overall_tree_change` reports about 2.5× the gain and 1.8× the loss of the change-detection datasets | `get_tehsil_data` | 16 |
| CS-56 | Medium | Canopy density and height series: whole-tehsil canopy area swings two-fold; 2020 missing but flagged inconsistently between the two datasets | `get_tehsil_data` | 16 |
| CS-57 | Medium | `croppingdrought_kharif`: "mild" drought covers almost every week of every year; dry-spell definition and `kharif_cropped_area` baseline undocumented | `get_tehsil_data` | 16 |
| CS-58 | Medium | `drought_causality` uses undefined codes, changes keys between years, and has no units | `get_tehsil_data` | 16 |
| CS-59 | Unrated | Truncated responses with no pagination (caused by the MCP server, see CS-84) | MCP `call_public_api` | 17 |
| CS-60 | Unrated | District name with a parenthetical alias fails | `get_tehsil_data` | 17 |
| CS-61 | Unrated | `filtered_mws` layer URL is "unknown" | `get_tehsil_data` | 17 |
| CS-62 | Unrated | `green_credit` exposes presigned S3 URLs | `get_tehsil_data` | 17 |
| CS-63 | Unrated | Same MWS returns different values from different tehsils | `get_tehsil_data` | 17 |
| CS-64 | Unrated | `mws_intersect_villages` lists only villages inside the requested tehsil | `get_tehsil_data` | 17 |
| CS-65 | Unrated | `surfacewaterbodies_annual` omits MWS with no water body and can exceed MWS area | `get_tehsil_data` | 17 |
| CS-66 | Unrated | Livestock and social rows do not match village polygons | `get_tehsil_data` | 17 |
| CS-67 | Unrated | Modelled groundwater change is biased negative | `get_tehsil_data` | 17 |
| CS-68 | Unrated | Precipitation is spatially over-smoothed and departs from district normals | `get_tehsil_data` | 17 |
| CS-69 | Unrated | `literacy_rate` uses total population as the denominator | `get_tehsil_data` | 17 |
| CS-70 | Unrated | Cropping intensity is relative to cultivable area and double cropping is over-detected in sub-humid areas | `get_tehsil_data` | 17 |
| CS-71 | Unrated | District naming differs from current boundaries | `get_tehsil_data` | 17 |
| CS-72 | Unrated | Small responses are returned inline by the client | MCP client | 17 |
| CS-73 | Unrated | Land-cover classes cover only 80–90% of some MWS; `cropland_area` is always zero | `get_tehsil_data` | 17 |
| CS-74 | High | Documented `get_tehsil_data` schema differs from the responses ingested in October: flat rows with unit- and year-suffixed columns | `get_tehsil_data` | 18 |
| CS-75 | Medium | `change_detection_tree_cover_decrease` / `_increase` are no longer listed; `change_detection_deforestation` / `_afforestation` appear with different column names | `get_tehsil_data` | 18 |
| CS-76 | Low | `green_credit` is no longer in the documented dataset list | `get_tehsil_data` | 18 |
| CS-78 | Medium | `hydrological_annual`: field descriptions contradict the layer description (G as "groundwater storage change" vs cumulative water balance); DeltaG undefined | `get_tehsil_data` | 18 |
| CS-79 | Low | Year suffixes mix calendar years (`_2017`) and agricultural years (`_2017-2018`) across annual datasets | `get_tehsil_data` | 18 |
| CS-80 | Low | Dataset ids mix camelCase and snake_case (`croppingIntensity_annual`, `village_GP`, `Canopy_height`) | `get_tehsil_data` | 18 |
| CS-81 | Medium | Metadata gaps in the newer datasets: periods, units and formats of NDVI slopes, fire counts, NREGA counts, upstream lists, Antyodaya status | `get_tehsil_data` | 18 |
| CS-82 | High | Live responses differ from both the documented schema and the Excel export: October-style `metadata`/`annual` blocks for annual datasets, lower-case keys, unit suffixes dropped from some fields | `get_tehsil_data` | 19 |
| CS-83 | Medium | v2's `data=` filter rejects `forest_fire`, `forest_fringes`, `tree_in_grassland` and `ndvi`, though `data=all` returns them; its `ndvi_shrub` is empty; column names differ from v1 | `get_tehsil_data` | 19 |
| CS-84 | High | The MCP server cuts responses at 180,000 characters with no flag; the API itself returns complete data (also the cause of CS-59) | MCP `call_public_api` | 19 |
| CS-85 | High | `delta_g` is P − ET − runoff only and `welldepth` is `delta_g` / specific yield: implies water-table rises of over 20 m a year in wet hard-rock MWS | `get_tehsil_data` (`hydrological_annual`) | 19 |
| CS-86 | Medium | `soge_vector` changed from one assessment to yearly assessments 2011–2025, with `-9999` for missing values; the 2025 assessment shifts many blocks | `get_tehsil_data` | 20 |
| CS-87 | Medium | `ndvi` / `ndvi_shrub` slopes are rounded to two decimals, so 96% are exactly 0 | `get_tehsil_data` | 20 |
| CS-88 | Medium | Coverage gaps after a complete fetch: village links missing for 418 MWS, soil for 90, SOGE for 88, connectivity for 73 | `get_tehsil_data` | 20 |
| CS-89 | Medium | `social_economic_indicator` changed between 15 and 21 Nov without notice: 206 Srikakulam and Ananthapur villages that `mws_intersect_villages` still lists lost their Census rows; duplicated rows elsewhere were halved and renamed | `get_tehsil_data` | 21 |
| CS-90 | Medium | `facilities_proximity.cooperative_cat_distance` puts 76% of sample villages more than 50 km from a cooperative (median 78 km), while every bank branch is within 50 km: cooperative coverage looks incomplete | `get_tehsil_data` | 22 |
| CS-91 | High | `soil_health` nitrogen is zero across most of Udaipur (median MWS 0.16 kg/ha; p05–p50 all 0 in most rows) while P, K and OC look normal; other districts have 69–589 kg/ha | `get_tehsil_data` | 23 |
Totals: 15 High, 36 Medium, 21 Low, 15 not yet rated (87 issues; CS-59 to CS-73 were logged in Query 17 without a severity; CS-77 was withdrawn).

---

## Query 1

> Using the core stack MCP config I have just added, tell me which tehsil and micro-watershed fall on lat/long 18.52, 73.85

### API calls

| # | Call | Parameters | Result |
|---|---|---|---|
| 1.1 | `list_public_apis` | none | 12 routes |
| 1.2 | `get_mwsid_by_latlon` | `latitude: 18.52, longitude: 73.85` | `uid: 18_50168`, State `MAHARASHTRA`, District `PUNE`, Tehsil `Haveli` |
| 1.3 | `get_admin_details_by_latlon` | `latitude: 18.52, longitude: 73.85` | State `MAHARASHTRA`, District `PUNE`, Tehsil `Haveli` |

### Issues

**High:** none. **Medium:** none.

**Low**

**CS-01. Place-name casing inconsistent within and across routes**
- Observed (calls 1.2, 1.3): state and district in upper case, tehsil in title case, in the same response.
- Across routes (see Query 3): `get_active_locations` returns "Karnataka", "Chik Ballapur", "Chintamani"; the lookups return "KARNATAKA", "CHIK BALLAPUR", "CHINTAMANI"; `get_village_geometries` returns "karnataka", "chik_ballapur", "chintamani".
- Calls succeeded with either upper or title case, so matching appears case-insensitive, but this is not documented.
- Suggested fix: one canonical form everywhere; document the matching rule.

**CS-02. Field hints in lookup routes restate field names**
- Observed (calls 1.2, 1.3): `mws_field_hints` and `admin_field_hints` map `State` to `state_name`, `uid` to `mws_identifier`, and so on. They add no information.
- Suggested fix: drop them, or use the block for definitions (for example, which tehsil is reported when a micro-watershed spans several; see CS-20).

---

## Query 2

> Show some key KYL indicators which can help explain any social-ecological stresses in this micro-watershed, such as groundwater stress, risk for rainfed agriculture, irrigation concerns, encroachment into forest areas, degradation of forests, livestock fodder issues, multi-dimensional vulnerability for the local populations, etc.

### API calls

| # | Call | Parameters | Result |
|---|---|---|---|
| 2.1 | `get_mws_kyl_indicators` | `state: MAHARASHTRA, district: PUNE, tehsil: Haveli, mws_id: 18_50168` | 60 indicators plus `indicator_units` |
| 2.2 | `describe_public_api` | `api_id: get_mws_kyl_indicators` | Same path, description and parameter names as `list_public_apis` |

### Issues

**High**

**CS-03. Coded indicators have no legend**
- Observed (call 2.1): these come back as bare codes, with the unit given only as "code", "category", "class" or "flag":
  - `trend_g: "1"`, `trend_swb: "0"`, `cropping_intensity_trend: "0"`
  - `drought_category: 0`, `soge_class: 0`, `aquifer_class: 0`
  - `terraincluster_id: 1`, `soil_drainage: 3`, `soil_texture: 1`
- Values seen across the session: trends "-1", "0", "1"; `drought_category` 0, 1, 2; `soge_class` 0, 3; `terraincluster_id` 1, 3; `soil_texture` 1, 2.
- Impact: the groundwater stress reading for Chintamani (Query 3) rests on assuming -1 means "declining" and a higher `soge_class` is worse.
- Suggested fix: return an `indicator_legends` block alongside `indicator_units` mapping each code to a label, or return the label next to the code.

**CS-04. Cropped-area fields labelled "ha" but behave like percentages**
- Fields: `avg_single_cropped`, `avg_double_cropped`, `avg_triple_cropped`, unit "ha".
- Observed (call 2.1): 21.19, 11.49, 8.53.
- Evidence from Queries 3 and 4, using `area` from `get_tehsil_data`:

  | Micro-watershed | Area (ha) | `lulc_crop` | Implied cropland (ha) | Single + double + triple |
  |---|---|---|---|---|
  | 2_29751 | 5,690.55 | 73.47% | about 4,180 | 57.97 |
  | 2_29834 | 4,043.47 | 77.49% | about 3,130 | 63.14 |
  | 2_31566 | 671.60 | 83.65% | about 560 | 79.41 |

- The sum stays between 40 and 80 whatever the size of the micro-watershed, which fits a percentage, not an area.
- Impact: reading these as hectares gave "about 41 ha of cropland" for 18_50168, which is probably wrong.
- Suggested fix: correct the unit, state the denominator, and add absolute hectares as separate fields if wanted. Also verify the "ha" label on `urbanization_area` and `degradation_land_area`.

**CS-05. No time period on averages, trends or change figures**
- Observed (call 2.1): no years given for `avg_precipitation`, `avg_runoff`, `avg_number_dry_spell`, the trend codes, `increase_in_tree_cover`, `decrease_in_tree_cover`, `urbanization_area`, `degradation_land_area`.
- Also applies to the whole `change_detection_tree_cover_decrease` dataset (Query 4).
- Impact: change figures cannot be read as rates or compared with outside sources.
- Suggested fix: add `period_start` and `period_end` per indicator or per dataset.

**Medium**

**CS-06. `avg_wsr_ratio_*` undefined**
- Observed (call 2.1): kharif 1.52, rabi 1.94, zaid 5.62. Across the session the range is 0.0 to 5.62.
- The name does not say what is divided by what, so the field could not be used.
- Suggested fix: expand the acronym and state numerator and denominator.

**CS-07. `lulc_plain_category` conflicts with `lulc_crop` and repeats across micro-watersheds**
- Observed (call 2.1): `lulc_plain_category` is "Mix of Double Cropped(~18%), Single Cropped(~30%) and Tree/Forests(~33%)" while `lulc_crop` is 7.31 and `lulc_forest` is 26.66.
- More evidence in Query 4: four micro-watersheds return the identical string.
- This looks like a label for a cluster of micro-watersheds, not for the one requested.
- Suggested fix: state whether it is a cluster-level typology; if so, rename it and return the cluster ID.

**CS-08. `describe_public_api` adds nothing beyond the route list**
- Observed (call 2.2, and again in calls 3.2 and 4.1): returns only `id`, `path`, the one-line description and parameter names.
- Suggested fix: include parameter formats and allowed values, which are required, an example call, and response fields with definitions, units and code legends.

**CS-09. Unit given as "value" for about 20 fields**
- Observed (call 2.1, `indicator_units`): `relief`, `mean_elevation`, `relative_mean_elevation`, `drainage_density`, `nitrogen_levels`, `phosphoros_levels`, `potassium_levels`, `organic_carbon`, `soil_ph`, `soil_drainage`, `soil_texture`, `reduction_canopy_density_height`, `increase_canopy_density_height`, `reduction_in_shrubland_cover`, `organic_carbon_tree_cover`, `mws_intersect_swb`. The booleans `canal_available` and `river_available` are also labelled "value".
- Impact: soil nutrients were readable only by assuming kg/ha; canopy and shrubland change could be hectares, percentages or an index.
- Suggested fix: give real units (m, km/km², kg/ha, %, ha) and "boolean" for true/false fields.

**CS-10. Zero cannot be told apart from "no data"**
- Observed (call 2.1): `total_nrega_assets: 0`, `area_protection: 0`, `area_wide_scale_restoration: 0.0`.
- Query 3 adds `avg_wsr_ratio_*: 0.0` and `avg_number_dry_spell: 0.0` for 2_31675.
- Suggested fix: use `null` for missing values.

**Low**

**CS-11. `-9999` sentinel in a text field**
- Observed (call 2.1): `lulc_slope_category: -9999` (integer). In Query 4, 3_6404 returns a string for the same field ("~15% Tree/Forests").
- Suggested fix: use `null`; keep the field one type.

**CS-12. Waterbody list bloats the response, little usable content**
- Observed (call 2.1): `mws_intersect_swb` has 25 entries, all with empty `swbName`. Coordinates are rounded to two decimals (about 1 km), so most entries share one of a few points.
- Query 4 responses carry up to about 100 entries; the few names present are generic ("KERE", "POND", "HALLI").
- Suggested fix: return a count by default and the list on request; give coordinates to at least four decimals.

**CS-13. Mixed data types for the same kind of value**
- Observed (call 2.1): trend codes are strings (`"1"`, `"0"`), other codes are integers.
- Query 3 adds: `vill_ID` is a string in `get_village_geometries` and an integer in `mws_intersect_villages`.
- Suggested fix: one type per kind of value.

**CS-14. Misspelt field name and unexplained acronyms**
- Observed (call 2.1): `phosphoros_levels`. Acronyms `soge`, `lcw`, `swb`, `wsr`, `kyl` and the flags `factory_csr`, `green_credit` are not expanded anywhere.
- Suggested fix: correct the spelling (keeping the old name as an alias for a while) and add a glossary.

**Also seen:** CS-28 (village code 802813 in `mws_intersect_villages`; described under Query 4).

---

## Query 3

> Shift over to Chintamani tehsil in Chik Ballapur district in Karnataka. Look at the micro-watershed which contains the Ammanallur village.

### API calls

| # | Call | Parameters | Result |
|---|---|---|---|
| 3.1 | `get_active_locations` | `state: Karnataka, district: Chik Ballapur` | One block, Chintamani, `block_id` and `tehsil_id` both 1144 |
| 3.2 | `describe_public_api` | `api_id: get_village_geometries` | No extra detail |
| 3.3 | `get_village_geometries` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani` | 186,873 characters, ends with `"truncated": true`. Ammanallur found as `vill_ID` 621738 and 621739 |
| 3.4 | `get_mwsid_by_latlon` | `latitude: 13.297, longitude: 77.982` (village centre) | `2_31566`, CHIK BALLAPUR / CHINTAMANI |
| 3.5 | `get_mwsid_by_latlon` | `latitude: 13.306, longitude: 77.983` (north) | `2_31675`, CHIK BALLAPUR / CHINTAMANI |
| 3.6 | `get_mwsid_by_latlon` | `latitude: 13.289, longitude: 77.98` (south-west) | `2_31468`, CHIK BALLAPUR / CHINTAMANI |
| 3.7 | `get_mwsid_by_latlon` | `latitude: 13.291, longitude: 77.987` (south-east) | `2_32051`, KOLAR / KOLAR |
| 3.8 | `get_mws_kyl_indicators` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani, mws_id: 2_31566` | Full indicator set |
| 3.9 | `get_mws_kyl_indicators` | same, `mws_id: 2_31675` | Full indicator set |
| 3.10 | `get_mws_kyl_indicators` | same, `mws_id: 2_31468` | Full indicator set |

The four points in calls 3.4 to 3.7 were picked by hand inside the Ammanallur polygon from call 3.3, because there is no village-to-micro-watershed route (CS-17).

### Issues

**High**

**CS-15. Village geometry response cut off, no pagination or filter**
- Observed (call 3.3): the response body is 186,873 characters and ends mid-coordinate, followed by `"truncated": true`. The last complete village is `vill_ID` 624443 (Moogalamari). I could not tell whether the API or the MCP wrapper applies the cut.
- Villages with higher codes never arrive. `mws_intersect_villages` shows these exist (624494 to 624706, and 803231).
- Impact: Ammanallur happened to fall inside the returned part. In Query 4 it blocked name lookup for most villages.
- Suggested fix:
  - add pagination (`limit`, `offset`) or filters (`vill_id`, `vill_name`, bounding box);
  - add an attributes-only option (code and name, no geometry);
  - return village names with the codes in `mws_intersect_villages`.

**CS-16. `degradation_cropping_intensity` labelled "ratio", values in the hundreds**
- Observed: 174.56 (call 3.8), 258.68 (call 3.9), 488.44 (call 3.10). In Query 2 it was 3.62; in Query 4 it reaches 673.71.
- Values scale with micro-watershed size, so they look like hectares.
- Suggested fix: correct the unit and define "degradation" (area where intensity fell, between which periods).

**Medium**

**CS-17. No route from a village to its micro-watersheds**
- There is no search by village name or code. Finding the micro-watersheds for one village needed calls 3.3 to 3.7: download every village polygon in the tehsil, read coordinates, and test points one at a time.
- That found four micro-watersheds but cannot guarantee all were found, and gives no area shares.
- Suggested fix: add `get_mws_by_village` (name or code in; micro-watershed IDs and overlap share out) and a village name search.

**CS-18. `vill_ID` is "0" for many villages**
- Observed (call 3.3): the first 68 or so features have `vill_ID: "0"` (first is Silaridinne, last is Nachagadde). They cannot be matched to the codes in `mws_intersect_villages`.
- Several names in this group repeat with nothing to tell them apart: Kambampalli (3), Nallaguttahalli (2), Pottepalli (2).
- Suggested fix: fill in the codes, or state why these have none (hamlets, uninhabited, unmatched to census).

**CS-19. Duplicate village features**
- Observed (call 3.3):
  - Ammanallur appears as 621738 and 621739 with identical polygons. Both codes are listed in `mws_intersect_villages` for 2_31566, 2_31675 and 2_31468.
  - The same code sits on two separate features with different polygons: 624403 (Yerrapalli), 624422 (Mudalagollahalli), 624435 (Pathakote).
- Suggested fix: merge true duplicates; store multi-part villages as one MultiPolygon feature.

**CS-20. Micro-watersheds crossing tehsil boundaries attributed inconsistently**
- Observed (call 3.7): a point inside the Chintamani village polygon for Ammanallur returns `2_32051` with District KOLAR, Tehsil KOLAR.
- In Query 4, `2_32051` also appears as a row in the Chintamani tehsil dataset, and waterbody IDs such as `2_29101_2_28565_3_3486_3238` span several micro-watersheds.
- Impact: unclear which tehsil to pass to per-micro-watershed routes, and whether tehsil-file values cover the whole micro-watershed or only the part inside the tehsil.
- Suggested fix: return every tehsil a micro-watershed intersects with area shares; state whether tehsil-file values are whole-unit or clipped.

**CS-21. Land cover percentages sum to more than 100**
- Observed:

  | Call | Micro-watershed | `lulc_crop` | `lulc_forest` | `lulc_shrub` | Sum |
  |---|---|---|---|---|---|
  | 3.8 | 2_31566 | 83.65 | 16.65 | 5.92 | 106.2 |
  | 3.9 | 2_31675 | 80.08 | 20.24 | 9.30 | 109.6 |
  | 3.10 | 2_31468 | 83.24 | 15.81 | 7.48 | 106.5 |

- Built-up, water and barren are not reported.
- Suggested fix: document the denominator and year for each; return a full breakdown that sums to 100.

**CS-22. Several fields constant across very different landscapes**
- Observed (calls 2.1, 3.8 to 3.10, and all of Query 4):
  - `aquifer_class` is 0 for central Pune and for every Chintamani micro-watershed.
  - `organic_carbon_tree_cover` is 1.0 everywhere.
  - `soil_drainage` is 3 everywhere; `soil_ph` is 6.4 for most Chintamani units.
- Suggested fix: confirm these are populated; for soil fields, state the source and its resolution.

**Low**

**CS-23. `body` returned as an escaped JSON string**
- Observed (call 3.3): `body` is a string containing escaped JSON. Every other route returns `body` as a JSON object.
- Suggested fix: return an object.

**CS-24. Stale and redundant fields in active locations**
- Observed (call 3.1): `location_field_hints` describes a `value` field that is not in the response; `block_id` and `tehsil_id` are identical.
- Suggested fix: remove the stale hint; keep one ID or explain the difference.

**Also seen**
- CS-01: three different casings for the same place across calls 3.1, 3.3 and 3.4.
- CS-02: hints in calls 3.4 to 3.7.
- CS-03: `trend_g: "-1"`, `soge_class: 3`, `drought_category: 2` and 1.
- CS-04: values 28.65, 36.78, 13.98 for 2_31566.
- CS-05, CS-06, CS-09, CS-10, CS-11, CS-12: same fields, calls 3.8 to 3.10.
- CS-08: call 3.2.
- CS-13: `vill_ID` string in call 3.3, integer in calls 3.8 to 3.10.

---

## Query 4

> In this tehsil, show me top-10 micro-watersheds which have the heaviest loss of tree cover. Also list their villages and categorize the type of tree cover loss, E.g. due to conversion to built-up, or conversion to farms, etc.

### API calls

| # | Call | Parameters | Result |
|---|---|---|---|
| 4.1 | `describe_public_api` | `api_id: get_tehsil_data` | No list of dataset names |
| 4.2 | `get_tehsil_data` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani, data: change_detection_deforestation` | Returned dataset `change_detection_tree_cover_decrease`, 116 rows |
| 4.3 to 4.12 | `get_mws_kyl_indicators` (10 calls) | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani, fields: mws_intersect_villages`, with `mws_id` in turn: `2_29834`, `2_29751`, `2_28565`, `2_31373`, `3_6404`, `3_5386`, `3_3486`, `2_30416`, `3_3784`, `2_28284` | Full indicator set every time |
| 4.13 | `get_village_geometries` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani` | Same truncated response as call 3.3 |

The `data` value in call 4.2 was a guess, because valid names are not listed anywhere (CS-25).

### Issues

**High:** no new issues. See "Also seen" for CS-15, which blocked part of this query.

**Medium**

**CS-25. Dataset names undocumented; unknown name silently returns another dataset**
- Observed (call 4.2): requested `change_detection_deforestation`, received `change_detection_tree_cover_decrease`, with no message that the name was matched or substituted.
- The route description gives only `drought` and `stream_order` as examples.
- Impact: a caller cannot tell whether they received what they asked for.
- Suggested fix: list valid names (a `list_datasets` route, or in `describe_public_api`); reject unknown names with the valid list, or echo `requested` and `matched`.

**CS-26. `fields` filter ignored**
- Observed (calls 4.3 to 4.12): `fields: mws_intersect_villages` was passed; all ten responses contained every indicator and the full waterbody list.
- The filter may be dropped by the API or by the MCP wrapper; I could not tell which.
- Suggested fix: make it work, document the format, and return an error for unknown field names.

**CS-27. "Forest" used for what is measured as tree cover**
- Observed (call 4.2): the dataset is named `..._tree_cover_decrease` but its columns are `forest_to_farm_area`, `forest_to_built_up_area`, `forest_to_scrub_land_area`, `forest_to_barren_area`. The column `forest_to_forest_area` (unchanged cover) sits in a "decrease" dataset without explanation.
- It is not stated whether plantations and orchards count, so "forest to farm" may be plantation clearing.
- Suggested fix: one term throughout; state what the class includes; separate natural forest from plantation if the source allows.

**Low**

**CS-28. Village codes outside the range of their neighbours**
- Observed: `803231` in `mws_intersect_villages` for 3_3486 (call 4.9), where all other codes are 6245xx to 6246xx. Also `802813` as the only village for 18_50168 (call 2.1).
- These may come from a different coding scheme, such as town codes.
- Suggested fix: state the code system used (Census 2011 village code, LGD code) and flag urban units.

**Also seen**
- CS-15 (High): village names could be resolved for only 4 of the 10 micro-watersheds (2_31373 in part, 3_6404, 3_5386, 3_3784). The other villages, with codes from 624494 upward, are beyond the cut-off in call 4.13.
- CS-07: `lulc_plain_category` is exactly "Mostly Trees/Forests(~48%)" for 2_29834, 2_29751, 2_28565 and 2_28284, whose `lulc_forest` values are 32.78, 40.71, 30.45 and 33.69.
- CS-21: sums of 116.6 (2_29834), 120.6 (2_29751) and 125.1 (3_3784).
- CS-16: values up to 673.71 (2_28565).
- CS-04: used with `area` from call 4.2 to build the evidence table under Query 2.
- CS-05: no period for the tree cover change dataset.
- CS-20: `2_32051` present in the Chintamani dataset from call 4.2.
- CS-17: no way to list villages by name for a micro-watershed.
- CS-03, CS-08, CS-11, CS-12: same behaviour as before.

---

## Queries 5 and 6

Requests to create and then reorganise this log. No API calls.

---

## Query 7

> Draw a nice waterbalance graph showing fortnightly rainfall time-series bars falling from the top to bottom, runoff and evapotranspiration stacked on top of each other, and a linespoints plot of the water balance as rainfall - ET - runoff. Show this for an MWS 3_5386

Outcome: the series for 3_5386 could not be retrieved (CS-29). The chart was drawn with 18_50168, the only micro-watershed for which the route returned data.

### API calls

| # | Call | Parameters | Result |
|---|---|---|---|
| 7.1 | `get_mws_data` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani, mws_id: 3_5386` | 404, `DistrictSOI matching query does not exist.` |
| 7.2 | `get_mws_data` | `state: KARNATAKA, district: CHIK BALLAPUR, tehsil: CHINTAMANI, mws_id: 3_5386` | 404, same message |
| 7.3 | `get_mws_data` | `state: karnataka, district: chik_ballapur, tehsil: chintamani, mws_id: 3_5386` | 404, same message |
| 7.4 | `describe_public_api` | `api_id: get_mws_data` | No extra detail |
| 7.5 to 7.9 | `get_mws_data` (5 calls) | `state: Karnataka, tehsil: Chintamani, mws_id: 3_5386`, with `district` in turn: `Chikkaballapura`, `Chikballapur`, `Chikkaballapur`, `Chikballapura`, `Chik_Ballapur` | 404, same message every time |
| 7.10 | `get_mws_data` | `state: Maharashtra, district: Pune, tehsil: Haveli, mws_id: 18_50168, fields: precipitation` | 200. 208 fortnights, 2017-07-01 to 2025-06-21, with `et`, `runoff` and `precipitation` all returned |
| 7.11 | `get_mws_report` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani, mws_id: 3_5386` | 404, `Mws Layer not found for the given location.` |
| 7.12 | `get_tehsil_data` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani, data: hydrological_seasonal` | No response after 4 minutes |

Calls 7.11 and 7.12 were attempts to find another route to the same data. The `data` value in 7.12 was a guess; it later proved to be a valid name (see CS-31).

### Issues

**High**

**CS-29. Time series route returns 404 `DistrictSOI matching query does not exist` for Chintamani**
- Observed (calls 7.1 to 7.3, 7.5 to 7.9): eight spellings and casings of the district all fail with the same message.
- The exact names from call 7.1 work on `get_mws_kyl_indicators`, `get_tehsil_data` and `get_village_geometries` (Queries 3 and 4), and `get_active_locations` lists Chintamani as an active location.
- The same route works for Pune (call 7.10), so the route itself is up.
- Likely cause, from the message: this route resolves the district against a different table (`DistrictSOI`) from the other routes, and that table has no matching entry for this district.
- Impact: no fortnightly water balance for any Chintamani micro-watershed; the user's request could not be met.
- Suggested fix: use the same district lookup as the other routes; return the accepted spellings in the error.

**Medium**

**CS-30. Report route returns 404 `Mws Layer not found` for a micro-watershed that other routes serve**
- Observed (call 7.11): 3_5386 has KYL indicators (call 4.8) and a row in the tehsil dataset (call 4.2), but no report.
- May share a root cause with CS-29.
- Suggested fix: say in the error which layer is missing and whether the report is ungenerated or the lookup failed.

**CS-31. Tehsil data call for `hydrological_seasonal` hung with no response for 4 minutes**
- Observed (call 7.12): no response before the client gave up.
- Correction (Query 9): `hydrological_seasonal` is a valid dataset name (it is in the list returned by call 9.1), so this was a hang on a valid request, not on an unknown name. Not retried.
- I could not tell whether the API, the MCP wrapper or the client connection stalled, so this needs reproducing.
- Suggested fix: set a server-side timeout that returns an error; if the dataset is large, paginate it.

**CS-32. Last record of the fortnightly series is all zeros**
- Observed (call 7.10): the final entry, 2025-06-21, has `et: 0.0`, `runoff: 0.0`, `precipitation: 0.0`, straight after fortnights of 215.4, 80.51 and 137.11 mm of rain in the monsoon onset.
- This looks like an unfilled placeholder, not a measurement. It pulls any total or average that includes it.
- Suggested fix: drop incomplete periods, or return `null` (see CS-10).

**Low**

**CS-33. `time_step` says "15_days" but dates are 14 days apart**
- Observed (call 7.10): `fortnight_units.time_step` is "15_days"; every consecutive pair of dates in `time` is 14 days apart (2017-07-01, 2017-07-15, 2017-07-29, ...).
- With 26 steps of 14 days the series also drifts one day a year against the calendar, and it is not stated whether `time` is the start or end of each period.
- Suggested fix: correct the label; state whether dates mark the start or end.

**CS-34. ET values repeat in consecutive pairs**
- Observed (call 7.10): many adjacent fortnights have identical `et` (8.68, 8.68; 2.91, 2.91; 9.04, 9.04; 7.1, 7.1; 4.28, 4.28; 1.47, 1.47), while rainfall and runoff never repeat this way.
- This suggests ET comes from a coarser source (monthly, perhaps) split across fortnights. Fortnightly balances then carry less information than they appear to.
- Suggested fix: document the source and native time step of each variable.

**CS-35. Error responses leak internal exception text and vary in shape**
- Observed: call 7.1 returns `error_message` and `error` with the same raw exception string (`DistrictSOI matching query does not exist.`); call 7.11 returns those two plus a `details` object repeating it a third time.
- Neither says which parameter failed or what values are valid.
- Suggested fix: one error shape; name the failing parameter; keep internal model names out of messages.

**Also seen**
- CS-26: `fields: precipitation` in call 7.10 was ignored; all three variables came back. The filter is now known to be ignored on two routes.
- CS-08: call 7.4.
- CS-05: `metadata` in call 7.10 holds only `mws_id`; no data source or processing date.
- CS-25: no list of dataset names, which led to the guess in call 7.12.

---

## Query 8

> Draw the graph again, it is not loading

No API calls. The chart was redrawn from the data returned by call 7.10.

---

## Query 9

> Create a map showing cropping intensity across all microwatersheds in Chintamani tehsil

Outcome: map delivered for all 114 micro-watersheds. Values came from the API. Boundaries could not be obtained through the API (CS-15) or through the boundary layer URL it lists (CS-36); they were taken from the GeoServer cropping intensity layer instead, fetched in a browser.

### API calls

| # | Call | Parameters | Result |
|---|---|---|---|
| 9.1 | `get_tehsil_data` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani, data: cropping_intensity` | 400, `Unknown data filter value(s): cropping_intensity`, followed by the list of 46 valid names |
| 9.2 | `get_generated_layer_urls` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani` | 200, 84 layers |
| 9.3 | `get_tehsil_data` | same, `data: croppingintensity_annual` | 200, 114 rows, years 2017 to 2024 |
| 9.4 | `get_mws_geometries` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani` | 200, `body` is a string of exactly 180,000 characters with `truncated: true`; 12 features started, 11 complete |

Direct GeoServer requests (URLs taken from call 9.2, fetched from a browser on the user's computer):

| # | Layer | Result |
|---|---|---|
| 9.5 | `mws_centroid:chik_ballapur_chintamani_mws_centroid` | 200, GeoJSON, `totalFeatures: 114` |
| 9.6 | `filtered_mws:mws_chik_ballapur_chintamani` (dataset "MWS") | 200 with an XML `ServiceExceptionReport`: `Feature type filtered_mws:mws_chik_ballapur_chintamani unknown` |
| 9.7 | `crop_intensity:chik_ballapur_chintamani_intensity` | 200, GeoJSON, 114 features, 1.74 MB |

### Issues

**High**

**CS-36. Layer URL for the micro-watershed boundaries is broken**
- Observed (calls 9.2, 9.6): the `layer_url` listed for dataset "MWS" (`layer_name: mws_chik_ballapur_chintamani`, workspace `filtered_mws`) returns `Feature type ... unknown`. The same layer name is also unknown in workspace `mws_layers`.
- GeoServer returns the error with HTTP 200 and an XML body, although JSON was requested, so a client that only checks the status code fails later on parsing.
- Impact: together with CS-15 this leaves no working way to get the tehsil's micro-watershed boundaries by themselves. The map was only possible because another layer (9.7) happens to carry the same polygons.
- Suggested fix: publish the layer or correct the workspace in the listing; check listed URLs when the listing is generated.

**Medium**

**CS-37. `cropping_intensity` denominator and `sum_area` undefined**
- Observed (call 9.3): each row has `metadata.area` and `metadata.sum_area`, both "ha", with no definition of `sum_area`.
- `cropping_intensity` is labelled "ratio" with no formula. It does not equal crops per cropped hectare. For all 912 unit-years it equals `(single + 2 x double + 3 x triple) / sum_area` to within rounding.
- Example, 2_28284 in 2017: single 287.38, double 540.71, triple 274.30, `sum_area` 1,736.5. Reported 1.26. Dividing by the area cropped that year (1,102.4 ha) would give 1.99.
- The GeoServer layer (9.7) names the same quantity `total_cropable_area_ever_hydroyear_2017_2024`, which explains it: the denominator is land cropped in any year of the period, so fallow land in a given year pulls the ratio below 1 (minimum seen 0.29).
- Impact: values below 1 look like errors unless the denominator is known, and the figure is not comparable with the usual gross-to-net cropped area definition.
- Suggested fix: state the formula; rename `sum_area` to match the GeoServer name.

**CS-38. Micro-watershed count differs between datasets of the same tehsil**
- Observed: `croppingintensity_annual` (call 9.3), the centroid layer (9.5) and the intensity layer (9.7) have 114 micro-watersheds. `change_detection_tree_cover_decrease` (call 4.2) had 116 rows. The two extra IDs were not identified.
- Suggested fix: explain which units are filtered from which datasets (see also CS-20).

**Low**

**CS-39. Drainage density layer URL has an empty workspace**
- Observed (call 9.2): `https://geoserver.core-stack.org:8443/geoserver//wcs?...&CoverageId=:drainage_density_chik_ballapur_chintamani...`. The workspace is missing in both places. Not fetched.

**CS-40. Layer list metadata gaps**
- Observed (call 9.2):
  - `style_url` is an empty string for all 84 layers.
  - `stream_order_chik_ballapur_chintamani_raster` is listed with `layer_type: vector` and a WFS URL.
  - The block that describes the fields is called `layer_field_units` but holds descriptions, not units.
  - Year and period appear only inside layer names and asset paths (`LULC_21_22_...`, `..._Deforestation_2017_2024`), not as fields.
  - `dataset_name` values do not match the `data` names used by `get_tehsil_data` ("Cropping Intensity" vs `croppingintensity_annual`).
- Suggested fix: add `year` or `period` fields and the matching `get_tehsil_data` name; fix the type; drop or fill `style_url`.

**Also seen**
- CS-15 (High): `get_mws_geometries` (call 9.4) is cut at exactly 180,000 characters, mid-coordinate, with 11 of 114 polygons complete. The cut-off for `get_village_geometries` earlier in the session was 186,873 characters through a different connection to the same server, which points to the MCP wrapper as the layer applying the limit. Polygons follow raster cell edges (about 490 vertices per micro-watershed), so a simplified-geometry option would help as much as pagination.
- CS-23: `body` in call 9.4 is an escaped JSON string.
- CS-25: behaviour differs from call 4.2. There, an unknown name returned another dataset without comment; in call 9.1 an unknown name returned a 400 with the full list of valid names, which is the behaviour suggested. The list is still not available from `describe_public_api`, and close misses are not matched (`cropping_intensity` vs `croppingintensity_annual`).
- CS-04: the tehsil dataset gives true hectares. For 3_5386, single-cropped area is 297 to 415 ha a year on 2,100 ha of cropland, against `avg_single_cropped: 19.3` "ha" in the KYL route. The KYL values fit a percentage of cropland.
- CS-05: partly answered outside the API. Asset paths in call 9.2 end `_2017_2024` for the change detection layers, and the GeoServer attribute names carry years. The API responses themselves still give no period.
- CS-13: `time` values in call 9.3 are strings ("2017"); the GeoServer layer uses per-year column names with full-precision values while the API rounds to two decimals.

---

## Query 10

> Is there a relationship between the annual water balances of micro-watersheds and their cropping intensities? Report the strength and significance of the relationship.

Outcome: answered with `hydrological_annual` joined to `croppingintensity_annual` from call 9.3 (114 micro-watersheds, 8 years, all IDs matched, no missing values).

### API calls

| # | Call | Parameters | Result |
|---|---|---|---|
| 10.1 | `get_tehsil_data` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani, data: hydrological_annual` | 200, 114 rows, years 2017 to 2024, fields `precipitation`, `et`, `runoff`, `delta_g`, `g`, `welldepth` |

### Issues

**High:** none new.

**Medium**

**CS-41. `welldepth` and `g` undefined; `welldepth` is labelled "m" but is a scaled copy of `delta_g`**
- Observed (call 10.1): for 2_28284, `delta_g` is 43.22, -71.59, -193.82 mm and `welldepth` is 2.16, -3.58, -9.69 "m". The ratio is 20 in every case checked, so `welldepth` is `delta_g` x 0.05, which looks like a fixed specific yield applied to the balance.
- It is therefore a modelled change in water level for the year, not a depth to water, and positive means a rise. The name and unit suggest a measured depth.
- `g` is the running sum of `delta_g` from 2017 (43.22, -28.37, -222.19, ...). Neither the baseline year nor the meaning is stated.
- `delta_g` equals `precipitation - et - runoff` to within 0.01 mm for all 912 unit-years. This is not documented either, though here it is what a user would expect.
- Suggested fix: rename (for example `delta_water_level`), state the specific yield used and the sign convention, and state the baseline for `g`.

**Low**

**CS-42. Metadata differs between datasets of the same tehsil**
- Observed: `hydrological_annual` rows carry only `uid` in `metadata`; `croppingintensity_annual` rows carry `uid`, `area` and `sum_area`. Area is needed to turn mm into volumes or to weight averages, so a second call is required.
- Suggested fix: a common metadata block (`uid`, `area`) on every dataset.

**Also seen**
- CS-29: the annual series for Chintamani is available through this route, while the fortnightly route `get_mws_data` still fails for the same tehsil. The data exists; only the lookup in that route is broken.
- CS-38: this dataset has 114 rows, matching the cropping intensity dataset.
- CS-05: years are labelled "agricultural_year" with no statement of which months that covers.

---

## Query 11

> Compare surface water availability between the kharif and rabi seasons over the past decade for microwatersheds in Chintamani. Show this on a map.

Outcome: map delivered for 114 micro-watersheds. Only eight years (2017 to 2024) are available, not a decade.

### API calls

| # | Call | Parameters | Result |
|---|---|---|---|
| 11.1 | `get_tehsil_data` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani, data: surfacewaterbodies_annual` | 200, 114 rows, years 2017 to 2024, fields `kharif_area`, `rabi_area`, `zaid_area`, `total_area` (ha), with `total_swb_area` in metadata |

Micro-watershed areas were taken from call 9.3 and boundaries from call 9.7.

### Issues

**High**

**CS-43. Kharif and rabi surface water areas are near-identical; seasonal fields appear nested and are undefined**
- Observed (call 11.1):
  - `rabi_area` equals `kharif_area` to two decimals in 604 of 912 unit-years.
  - Summed over the tehsil, rabi is 99.3% of kharif (98.4% to 99.9% by year). Zaid is 78% of kharif.
  - `rabi_area` never exceeds `kharif_area`, and `zaid_area` never exceeds `rabi_area`, in any unit-year.
- The strict ordering suggests the fields are nested: rabi is water that was present in kharif and is still present in rabi, and zaid is the subset still present in summer. Under that reading, water that first appears in rabi (north-east monsoon rain in October to December, which matters in this region) cannot be counted.
- A loss of under 1% of water area between the monsoon and winter seasons, in small tanks in a semi-arid tehsil, is implausible as a physical result. It may reflect how seasons are classified (for example, a pixel counted as rabi water if wet at any time in a window that overlaps kharif).
- Impact: a kharif-versus-rabi comparison, which is what the user asked for, shows almost no difference anywhere. Without a definition the user cannot tell whether that is real.
- The KYL route shows the same pattern (`avg_kharif_surface_water_mws` 38.81 and `avg_rabi_surface_water_mws` 38.81 for 18_50168, call 2.1).
- Suggested fix: document how each season's water area is derived (dates, threshold of wet observations, whether nested); if nested, rename to say so and add independent per-season areas.

**Medium**

**CS-44. Three undefined "total" water areas that disagree**
- Observed (call 11.1), 2_28284 in 2017: `kharif_area` 23.34, `total_area` 36.20, `metadata.total_swb_area` 85.58, all "ha".
- Over the tehsil, kharif is 41% to 93% of `total_area` depending on the year, and `total_area` never reaches `total_swb_area`.
- Likely meanings: `total_area` is anything detected as water at any time in the year, and `total_swb_area` is the mapped footprint of the waterbodies. Neither is stated.
- Impact: "share of tank area holding water" could be computed against either, with very different answers.
- Suggested fix: define both; rename `total_area` (for example `any_water_area`) and `total_swb_area` (for example `waterbody_footprint_area`).

**Also seen**
- CS-09 (new evidence, unit now identified): the KYL fields `avg_kharif_surface_water_mws`, `avg_rabi_surface_water_mws` and `avg_zaid_surface_water_mws` are labelled "mm" but are percentages. For all four units checked they equal this dataset's 2017 to 2024 mean seasonal area divided by `total_swb_area`, times 100, to two decimals: 3_5386 gives 21.06, 20.83, 17.44 (means 18.20, 18.00, 15.07 ha on a footprint of 86.44 ha); 2_31566 gives 22.73, 22.60, 9.02; 3_3784 gives 47.61, 47.56, 44.38; 2_29834 gives 27.06, 26.77, 21.82. Suggested fix: change the unit to "% of waterbody footprint" and say so in the field name.
- CS-05: the series starts in 2017; nothing in the API says what period is covered, so a request for "the past decade" cannot be checked against coverage without downloading the data.
- CS-10: 130 unit-years have `kharif_area: 0`. Zero here is plausible (dry tanks in 2018 and 2019), but it is not distinguishable from missing.
- CS-42: metadata here is `uid` and `total_swb_area`, with no micro-watershed `area`; a third metadata shape across three datasets.

---

## Query 12

> Do microwatersheds with more forest cover show better groundwater recharge? Has this relationship changed over the years?

Outcome: answered with `lulc_vector` (tree cover) joined to `hydrological_annual` from call 10.1 (`delta_g`), 114 micro-watersheds, 8 years.

### API calls

| # | Call | Parameters | Result |
|---|---|---|---|
| 12.1 | `get_tehsil_data` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani, data: lulc_vector` | 200, 114 rows, years 2017 to 2024, twelve land cover areas in ha, `area` in metadata |

### Issues

**High**

**CS-45. Yearly tree and shrub areas swing by a factor of two and mirror each other**
- Observed (call 12.1), tehsil totals in ha by year, 2017 to 2024:
  - `tree_forest_area`: 35,611; 23,182; 22,008; 37,302; 41,301; 43,013; 31,510; 38,005
  - `shrub_scrub_area`: 23,219; 45,661; 46,753; 14,194; 12,800; 14,005; 34,700; 13,981
- Tree cover falls by 35% from 2017 to 2018 and rises by 70% from 2019 to 2020. Trees do not do that. The two classes move in opposite directions and their sum is far steadier (35% to 48% of area), and tree area follows the year's rainfall (r = 0.63 over the eight years). This looks like the classifier labelling the same vegetation as tree in wet years and shrub in dry years.
- `built-up_area` also moves in ways built-up land does not: 7,871 ha in 2020, 6,316 in 2021, 9,342 in 2024.
- Impact: any year-on-year forest change, and the change detection products built on these maps (tree cover loss and gain, CS-27; Query 4), may largely reflect wet and dry years. In Query 4, nine of ten micro-watersheds showed both large losses and large gains, which fits this.
- Suggested fix: stabilise perennial classes across years (temporal smoothing or a multi-year tree mask); publish per-class accuracy; warn against using single-year tree area as a time series.

**Medium**

**CS-46. Land cover classes sum to about 94.5% of area; water class names undefined**
- Observed (call 12.1): for every micro-watershed and year the twelve class areas sum to between 94.3% and 94.8% of `metadata.area`. The missing 5.5% is constant enough to be systematic (a projection or pixel-area difference, or an unreported class).
- `k_water_area`, `kr_water_area`, `krz_water_area` are not expanded. They appear to be exclusive classes: water in kharif only, in kharif and rabi, and in all three seasons. If so they confirm the nesting in CS-43, and they show kharif-only water is tiny (2 to 42 ha a year across the tehsil).
- Their sum does not match the surface water dataset: for 2017, k + kr + krz is 1,192 ha, against `kharif_area` 775 ha and `total_area` 1,224 ha in `surfacewaterbodies_annual` (call 11.1). See CS-44.
- Suggested fix: explain the area difference; expand the water class names; reconcile the two water datasets.

**Low**

**CS-47. `cropland_area` is zero in every row**
- Observed (call 12.1): 0 for all 912 unit-years, while the single, double and triple cropped classes hold the cropland. The field is either unused or a parent class that was never filled.
- Suggested fix: drop it or fill it with the sum of the cropped classes.

**Also seen**
- CS-27: the field is `tree_forest_area`; plantations, orchards and natural forest are not separated, which matters for a recharge question.
- CS-41: "groundwater recharge" had to be taken as `delta_g`, a water balance residual. No measured recharge or observed water level is offered.
- CS-21: here the classes do not exceed 100%, so the over-100% sums in the KYL route come from that route's own denominators.

---

## Query 13

> Give a ranked list of villages on access to surface water during the dry season?

Outcome: ranking delivered for 405 villages. No API route gives water by village, and the waterbody route failed (CS-48), so the ranking was built from two GeoServer layers fetched in a browser: each waterbody was assigned to the village containing its centre.

### API calls

| # | Call | Parameters | Result |
|---|---|---|---|
| 13.1 | `get_waterbodies_data_by_admin` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani` | 502, `Merged dataset not available for given area.` |
| 13.2 | `get_tehsil_data` | same, `data: mws_intersect_villages,social_economic_indicator` | 200. `mws_intersect_villages` 108 rows; `social_economic_indicator` 339 rows |

Direct GeoServer requests:

| # | Layer | Result |
|---|---|---|
| 13.3 | `swb:surface_waterbodies_chik_ballapur_chintamani` | 200, 3,263 waterbody polygons with per-year `area_YY-YY`, `k_`, `kr_`, `krz_` fields |
| 13.4 | `panchayat_boundaries:chik_ballapur_chintamani` (not in the list from call 9.2; name guessed) | 200, 443 village polygons |
| 13.5 | `swb:waterbodies_zoi_chik_ballapur_chintamani` | 200, 3,263 features (inspected only) |

### Issues

**High**

**CS-48. Waterbody route returns 502 for Chintamani**
- Observed (call 13.1): `Merged dataset not available for given area.` The underlying layer exists and is complete on GeoServer (call 13.3), and `get_generated_layer_urls` lists it.
- A 502 is a gateway error code; the condition is "data not prepared", for which 404 or 409 would be clearer.
- `get_waterbody_data` (single waterbody) was not tried; it reads the same merged dataset.
- Impact: the only API route with per-waterbody seasonal water is unusable for this tehsil.
- Suggested fix: build the merged dataset for all active tehsils, or have `get_active_locations` say which routes work for each tehsil.

**Medium**

**CS-49. Waterbody layer: a third of features lie outside the tehsil; duplicate and empty attribute columns**
- Observed (call 13.3):
  - 1,055 of 3,263 waterbodies have their centre outside every Chintamani village polygon. Their `village_name` values belong to neighbouring tehsils and states (for example "t.sadum", 79 waterbodies). The layer covers whole micro-watersheds, which extend beyond the tehsil, but it is named and listed as the tehsil's.
  - `State Name`, `District Name`, `Block/Tehsil Name` and `Village Name` are null, while lower-case `village_name` and `covering_village_names` are filled. Two columns for the same thing, one empty.
  - About 60 census-style columns (`construction_cost`, `storage_capacity_water_body_original`, `no_people_benefited_by_water_body`, ...) are null on every feature checked.
  - `k_`, `kr_`, `krz_` are percentages of `area_ored`, and `area_YY-YY` is hectares; none of this is documented. `area_ored` is unexplained (it appears to be the union of water extent over all years).
- Impact: summing the layer gives totals for an area about one and a half times the tehsil; a user filtering by the null admin columns gets nothing.
- Suggested fix: add a flag or filter for "inside tehsil"; drop empty columns; document the seasonal fields.

**Low**

**CS-50. Data-entry errors in village names and attribute names**
- Observed: village `M0Shilahalli` (624537) with a zero in the name (call 13.4); attribute `construcion_year` (call 13.3); `town_municipalty_name` (call 13.3).

**Also seen**
- CS-44 (new evidence, partly resolved): summing the layer over all 3,263 waterbodies reproduces the API's `total_area` exactly (2017: 1,224 ha; 2022: 3,394 ha) from `k_` x `area_ored`. So the API's `total_area` is the layer's kharif water, and the API's `total_swb_area` is the sum of `area_ored` (3,883 ha). The API's `kharif_area` (775 ha in 2017) and `zaid_area` (567 ha) match nothing in the layer, whose `kr_` and `krz_` sums are 1,222 and 833 ha. The two sources use the same season names for different quantities.
- CS-43: in the layer, `kr_` equals `k_` for most waterbodies as well (tehsil sums 1,222 vs 1,224 ha in 2017).
- CS-20 and CS-49: tehsil-level datasets from `get_tehsil_data` are sums over whole micro-watersheds, so they include land and water outside the tehsil. This affects every tehsil total reported earlier in this log's queries.
- CS-17: no route or dataset gives any water indicator by village. `mws_intersect_villages` gives overlap areas, which only allows spreading a micro-watershed's water evenly across its villages; that is wrong for waterbodies, which are point-like.
- CS-19: 32 of the 443 village features are exact duplicates of another feature's geometry (Ammanallur is one of 32 cases, not an isolated one).
- CS-18: 68 village features have `vill_ID` 0 and all census fields 0; the first row of `social_economic_indicator` is one of them (all zeros).
- CS-38: `mws_intersect_villages` has 108 rows against 114 micro-watersheds; `social_economic_indicator` has 339 villages against 411 distinct village polygons.
- CS-13: `village_ids` in `mws_intersect_villages` is a string containing a list (`"[624606, 624607]"`), next to `village_details.keys` as a real list of strings.
- CS-09: `tehsil_units` gives "value" for most fields of `mws_intersect_villages`.
- CS-15: the village boundary layer is not in the list from `get_generated_layer_urls`, and `get_village_geometries` is truncated, so there is no documented way to get all village polygons.

---

## Query 14

> Try doing this relationally instead of using the geoserver layers with spatial joins. Use the waterbody APIs to join waterbodies with micro-watersheds (each waterbody has an id and it is already mapped with micro-watersheds it falls into), and the MWS APIs to map MWSes to villages (the MWS data contains a list of villages that an MWS intersects with). This will not give an exact answer but it can give clusters of villages that intersect with MWSes with low dry season water access. Create a separate artifact for this.

Outcome: clusters delivered using API tables only. The waterbody-level join asked for was not possible: both waterbody routes fail (CS-48) and the waterbody-to-micro-watershed table is cut off (CS-15). Dry-season water per micro-watershed came from `surfacewaterbodies_annual` (call 11.1), which is the same waterbody data already summed by micro-watershed; villages came from `mws_intersect_villages` and names from `social_economic_indicator` (call 13.2).

### API calls

| # | Call | Parameters | Result |
|---|---|---|---|
| 14.1 | `get_waterbodies_data_by_admin` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani` | 502 again, `Merged dataset not available for given area.` |
| 14.2 | `get_waterbody_data` | same, `uid: 2_30416_1985` (a waterbody ID seen in the GeoServer layer) | 502, same message |
| 14.3 | `get_tehsil_data` | same, `data: mws_intersect_swb` | 200, `body` is a string of exactly 180,000 characters with `truncated: true`; 1,436 complete waterbody rows covering 46 of 114 micro-watersheds |

### Issues

**High:** none new. CS-48 and CS-15 both blocked the intended method; see "Also seen".

**Medium**

**CS-51. Micro-watershed-to-village mapping is incomplete in three ways**
- Observed (`mws_intersect_villages`, call 13.2, used here):
  - Six micro-watersheds have no row: 2_31090, 3_3881, 3_5597, 3_7455, 3_7697, 3_8046. All six have rows in the water, hydrology and cropping datasets.
  - For the 108 that are present, the listed villages cover a median of 79% of the micro-watershed's area, and as little as 0%. The rest lies in villages of neighbouring tehsils, which are not listed. A micro-watershed's water is therefore attributed only to the part of its population that happens to be in this tehsil.
  - Only villages with a census code appear (338). The 68 no-code units (CS-18) are absent, so they cannot be reached by any ID join.
- `percentage_of_area` is the share of the micro-watershed's area, not of the village's; this is not stated. The village's own area is not given and had to be reconstructed by summing its overlaps.
- Impact: village-level results built from this table are biased near the tehsil edge and silently drop about a sixth of village units.
- Suggested fix: include all intersecting villages regardless of tehsil (with their tehsil named); add rows for the six missing micro-watersheds; add `village_area` and the share of the village in each micro-watershed.

**Also seen**
- CS-48 (High): `get_waterbody_data` fails the same way as `get_waterbodies_data_by_admin` (calls 14.1, 14.2). No API route returns seasonal water for an individual waterbody in this tehsil, so the waterbody-to-micro-watershed join could only be done on pre-summed data.
- CS-15 (High): `mws_intersect_swb` (call 14.3) is the third dataset cut at 180,000 characters. It is a plain table, not geometry, so pagination alone would fix it. 68 micro-watersheds' waterbody lists are lost.
- CS-12: in call 14.3, `waterbodies_name` is null for most rows, and `latitude`/`longitude` are strings padded to seven decimals but rounded to two ("13.2800000").
- CS-23: `body` in call 14.3 is an escaped JSON string, unlike other `get_tehsil_data` responses that fit under the limit.
- CS-20: 71 of the 1,436 waterbody IDs parsed span more than one micro-watershed (IDs such as `3_3246_3_3360_2371`) and appear once per micro-watershed, so summing by micro-watershed risks double counting. Whether `surfacewaterbodies_annual` splits or duplicates their area is not stated.
- CS-44: the dry-season figure used here is the API's `zaid_area`, which is lower than the GeoServer layer's `krz_` sum used in Query 13 (tehsil 2017: 567 vs 833 ha).

---

## Query 15

> Use your knowledge to build a list of government schemes in Chintamani / Karnataka, and build an artifact to show which schemes will be most relevant in which micro-watershed or village cluster. Think from the standpoint of social-ecological stresses that can be inferred based on the data of these MWSes and also attempt convergence of schemes, E.g. de-silting of waterbodies to improve water access can be supplemented with fishery for improved livelihood.

Outcome: artifact delivered. Stress indicators for 114 micro-watersheds were computed from datasets fetched in Queries 9 to 13 plus the calls below. The scheme list is from general knowledge and is not part of the API.

### API calls

| # | Call | Parameters | Result |
|---|---|---|---|
| 15.1 | `get_tehsil_data` | `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani, data: drought,soge_vector,livestock,aquifer_vector` | 200, `body` string cut at 180,000 characters. `livestock` complete (343 villages); `aquifer_vector` cut off; `drought` and `soge_vector` absent from the returned text |
| 15.2 | `get_tehsil_data` | same, `data: change_detection_degradation,change_detection_tree_cover_decrease,restoration_vector,nrega_annual` | 200, cut at 180,000 characters. First three complete (114 rows each); `nrega_annual` cut off |
| 15.3 | `get_tehsil_data` | same, `data: soge_vector` | 200, 114 rows |
| 15.4 | `get_tehsil_data` | same, `data: drought` | 200, `{"tehsil_data": {}, "tehsil_units": {}}` |
| 15.5 | `get_tehsil_data` | same, `data: nrega_annual` | 200, 108 rows, years 2005 to 2024 |

### Issues

**High:** none new.

**Medium**

**CS-52. `drought` dataset returns an empty object with status 200**
- Observed (call 15.4): `tehsil_data` and `tehsil_units` are both empty. `drought` is in the list of valid names (call 9.1), is the example used in the route's own description, and a Drought layer for this tehsil is listed by `get_generated_layer_urls` (call 9.2). In call 15.1 it was also silently missing from a multi-dataset response.
- The KYL route returns `drought_category` and `avg_number_dry_spell` for these micro-watersheds, so the source data exists.
- Impact: no drought frequency could be used in the stress screening; a proxy from cropping intensity was used instead. A caller cannot tell "no data" from "no drought".
- Suggested fix: return 404 with a reason when a valid dataset has no data for the tehsil; never return an empty success.

**CS-53. Groundwater extraction class disagrees between routes; block-level values presented per micro-watershed**
- Observed (call 15.3): `soge_vector` gives `class_code: 4`, `class_name: "Over Exploited"` for 107 of 114 micro-watersheds. `get_mws_kyl_indicators` gave `soge_class: 3` for the same micro-watersheds (calls 3.8 to 3.10, 4.3 to 4.12). Either the two routes use different code tables or one is wrong.
- `soge_dev` takes only seven distinct values across 114 micro-watersheds (160.61 for most; also 163.17, 184.85, 139.45, 108.74, 54.04). These are block- or assessment-unit figures copied to every micro-watershed inside the unit. Nothing says so, and the spread between neighbouring micro-watersheds is therefore not real.
- Seven micro-watersheds at the north-east edge are "Safe" at 54.04%, next to neighbours at 160%, which is the boundary of a different assessment unit (probably a neighbouring block or state), not a hydrological difference.
- This dataset does provide the legend that CS-03 asks for (`class_name`), which the KYL route lacks.
- Suggested fix: one code table across routes; return the assessment unit name and year; state that the value is not computed per micro-watershed.

**Low**

**CS-54. Inconsistent ID key and partial coverage in `nrega_annual` and `livestock`**
- `nrega_annual` rows are keyed `metadata.mws_id`; every other annual dataset uses `metadata.uid`; `mws_intersect_villages` uses `mws_uid`. Three names for the same key.
- `nrega_annual` has 108 rows (the same six micro-watersheds missing as in CS-51). Its series runs from 2005 with zeros up to 2015 for the rows inspected; whether those are true zeros or missing geotags is not stated (CS-10).
- `livestock` has 343 village rows, of which 57 carry `data_availability_status: "no data available for this village"`. The status field is good practice; the other datasets would benefit from the same.
- `livestock` is at village level inside a route described as "one row per micro-watershed".

**Also seen**
- CS-15 (High): asking for several datasets in one call (15.1, 15.2) produces a response over the 180,000-character limit, and the datasets at the end are cut off or missing. The multi-dataset option noted as working in Query 13 only works for small datasets.
- CS-22 (partly resolved): `aquifer_vector` returns `aquifer_class: "Hard Rock"` with a percentage by rock type (100% banded gneissic complex for the rows read), while the KYL route's `aquifer_class` is 0 everywhere. The KYL field is the one that is unpopulated or uncoded.
- CS-45: tree-cover loss was left out of the stress flags because of the tree and shrub instability.
- CS-51: livestock and population had to be apportioned from villages to micro-watersheds by overlap area, and are unavailable for the six micro-watersheds with no village list.
- CS-05: `change_detection_degradation` and `restoration_vector` carry no period or date.

## Query 16

> To identify various stresses, try to use the get_tehsil_data API instead of the kyl_indicators API. KYL indicators are summary indicators built from the finer tehsil data, but the tehsil data will be easier to interpret since the columns typically contain unit values. Also process the tree cover data even though an instability was found and match with afforestation related government schemes. Report if drought information remains hard to access from the tehsil data, although it should have weeks of mild/moderate/severe drought and weeks of dry spells. Create a methodology tab on the artifact to explain the rules used to flag various types of stresses.

Outcome: the scheme convergence artifact was rebuilt with 12 stresses and 2 opportunities, all from `get_tehsil_data` columns with units, and a Methodology tab was added. Drought is accessible through `croppingdrought_kharif` (weekly counts per kharif season), not through `drought`. Tree data was used for three new flags despite CS-45 and CS-55.

### API calls

All calls use `state: Karnataka, district: Chik Ballapur, tehsil: Chintamani`.

| # | Call | Parameters | Result |
|---|---|---|---|
| 16.1 | `get_tehsil_data` | `data: drought` | 200, `{"tehsil_data": {}, "tehsil_units": {}}` again |
| 16.2 | `get_tehsil_data` | `data: croppingdrought_kharif` | 200, 114 rows, kharif 2017 to 2024, 92k characters, complete |
| 16.3 | `get_tehsil_data` | `data: drought_causality` | 200, `body` returned as a string cut at 180,000 characters; 90 of 114 rows parseable |
| 16.4 | `get_tehsil_data` | `data: change_detection_tree_cover_increase` | 200, 114 rows |
| 16.5 | `get_tehsil_data` | `data: overall_tree_change` | 200, 114 rows |
| 16.6 | `get_tehsil_data` | `data: canopy_cover_density` | 200, 114 rows, 2017 to 2023 |
| 16.7 | `get_tehsil_data` | `data: canopy_height` | 200, 114 rows, 2017 to 2023 |
| 16.8 | `get_tehsil_data` | `data: overall_tree_change,change_detection_tree_cover_increase,canopy_cover_density` | 200, 111,674 characters, complete (re-fetch so all three could be processed together) |
| 16.9 | `get_tehsil_data` | `data: green_credit` | 200, `{"tehsil_data": {}, "tehsil_units": {}}` |

Also reused: `hydrological_annual` (call 10.1), `change_detection_tree_cover_decrease`, `change_detection_degradation`, `restoration_vector` (call 15.2), and the datasets listed under Query 15.

### Is drought information hard to access?

Partly. The dataset named `drought` is still empty (CS-52), but `croppingdrought_kharif` has what is needed: for each micro-watershed and kharif season, the number of weeks of `no_drought`, `mild`, `moderate` and `severe` drought, `dry_spell` weeks, `total_weeks` (24 or 25), `monsoon_onset`, and kharif cropped area. The four classes add up to `total_weeks` in all 912 rows. Nothing in the dataset list or route description points a caller from `drought` to `croppingdrought_kharif`, so it is easy to conclude that drought data is missing. The content has its own problems (CS-57, CS-58).

### Issues

**High**

**CS-55. Tree-change datasets disagree with each other and with tree cover**
- `overall_tree_change.tree_cover_increase_area` is a median 2.5 times `change_detection_tree_cover_increase.total_tree_cover_increase_area` for the same micro-watershed (for 2_28284: 935.39 ha against 447.76 ha). `tree_cover_decrease_area` is a median 1.8 times `change_detection_tree_cover_decrease.total_tree_cover_decrease_area`.
- In 106 of 114 micro-watersheds, the gain in `overall_tree_change` is larger than `area_under_tree_cover` in the same row (2_28284: 935 ha gained, 572 ha under tree cover).
- Gain exceeds loss in 113 of 114 micro-watersheds, a net tree-cover increase of a median 8% of land area. Given CS-45, much of this is likely class switching between tree and shrub, not planting.
- Neither dataset states the period, or whether "increase" is gross pixel transitions summed over years or a change between two end years (CS-05).
- Impact: the tree-loss flag had to use gross loss only; no net change could be reported with confidence.
- Suggested fix: derive both datasets from one change-detection run; document the period, the method (end-to-end or summed annual), and the minimum persistence required before a pixel counts as changed.

**Medium**

**CS-56. Canopy density and height series unstable; 2020 missing data flagged inconsistently**
- Summed over the tehsil, `high_density_area + low_density_area` is 34,174 ha (2017), 22,648 (2018), 19,267 (2019), 21,385 (2020), 40,706 (2021), 44,509 (2022), 31,563 (2023). Canopy height areas move the same way.
- 2020: `canopy_cover_density.missing_data_area` totals 16,535 ha, but `canopy_height.missing_data_area` is 0 in the same year while its medium and tall areas fall to near zero (2_28284: 0 ha medium and tall, 0 ha missing). The same gap is labelled missing in one dataset and absent canopy in the other.
- Both series end in 2023; the other annual datasets run to 2024.
- Workaround: years with more than 5% missing were dropped and 2017–19 was compared with 2021–23; the canopy flag used `overall_tree_change.degradation` instead.
- Suggested fix: mark the same gap as missing in both datasets; flag low-confidence years; extend to 2024.

**CS-57. `croppingdrought_kharif`: the mild class is near-universal; definitions undocumented**
- A median of 21.6 of 24 kharif weeks are `mild` drought, and the class barely varies with rainfall: in 2021, the wettest year (median 1,465 mm, call 10.1), the median micro-watershed had 23 of 24 weeks in mild drought; in 2017 (1,051 mm) it had 24 of 24. `no_drought` is 0 or 1 week per season in every row; no micro-watershed has more than 2 drought-free weeks across eight seasons. The class does not separate wet years from dry ones.
- `dry_spell` is not defined (consecutive dry days? rainfall threshold? 4-week window?). It ranges from 0 to 5 weeks a season and is zero in 2019 to 2021 everywhere.
- `kharif_cropped_area` (unit "%") is 100 in 2017 in all 114 rows, so it is a percentage of the 2017 area, not of the micro-watershed or cropland. This is not stated.
- `kharif_cropped` is in sq km; every other area in `get_tehsil_data` is in ha.
- Workaround: the drought flag uses moderate plus severe weeks, and dry spells separately.
- Suggested fix: publish the class thresholds (which indices, which percentiles), check the mild threshold, define a dry-spell week, and state the baseline for `kharif_cropped_area`.

**CS-58. `drought_causality` uses undefined codes and changing keys**
- Each year holds `{"keys": [...], "values": [...]}` objects. The mild keys switch between `mild_drought_mai_score` (537 row-years) and `mild_drought_vci_score` (183 row-years) from one year to the next, with no explanation of MAI, VCI or the score scale.
- Moderate and severe causes are given as `moderate_drought_path1`, `path3`, `path6` and `path9`, with no legend; 225 row-years are an empty `{}`.
- `annual_units` has no entry for any of these.
- The response is cut at 180,000 characters and arrives as a string (CS-15), so 24 of 114 rows are lost.
- Suggested fix: a legend for each path and score, a fixed set of keys per year, units, and pagination.

**Also seen**
- CS-52 (Medium): `drought` empty again (16.1); `green_credit`, also in the valid list, is empty too (16.9). This was the only dataset that could have tied the Green Credit Programme to specific land.
- CS-15 (High): `drought_causality` cut off (16.3). A three-dataset call of about 112k characters (16.8) did come back complete.
- CS-45 (High): tree data used despite the instability, for gross tree loss, canopy degradation and a tree-planting opportunity. These flags are marked as the least certain on the artifact.
- CS-05: `overall_tree_change`, `change_detection_tree_cover_increase` and `restoration_vector` carry no period.
- `restoration_vector.wide_scale_restoration_area` covers a median 54% of each micro-watershed, much of it farmland. Not a bug, but the meaning of "wide-scale restoration" (from which atlas, which year) should be documented.

**Working as expected (Query 16)**
- `croppingdrought_kharif` was complete for 114 units and 8 seasons, its week classes summed exactly to `total_weeks`, and it carried a full `annual_units` block.
- `hydrological_annual`: precipitation − ET − runoff matched `delta_g` within 0.01 mm in all 912 row-years, so the recomputed cumulative balance equals the summed `delta_g` here.

---

## Query 17

**Request:** Build social-ecological functional types for 8 districts (73 tehsils). Pull every tehsil dataset, label each MWS as a mix of system archetypes, trigger stresses from a causal knowledge graph and match schemes.

**Call sequence:** `get_active_locations` → `get_tehsil_data` (309 calls; datasets packed per tehsil) → GeoServer WFS (`crop_intensity:{d}_{t}_intensity`, `panchayat_boundaries:{d}_{t}`, `lulc_vector:lulc_vector_{d}_{t}`, `mws_layers:deltaG_well_depth_{d}_{t}`) for geometry and back-fill.

### CS-59 · Truncated responses with no pagination
`get_tehsil_data` cuts off large datasets with no page or offset parameter. `lulc_vector` truncates for tehsils with more than about 118 MWS. `croppingintensity_annual`, `hydrological_annual`, `livestock` and `social_economic_indicator` truncate for the largest tehsils. Chikhaldara drought came back with 195 of 273 rows. Jaypur and Ballia livestock were truncated at 427 and 423 rows. The workaround was to back-fill from GeoServer, which matched the API exactly where both had data.
**Fix:** add `page`/`offset` or a per-dataset limit, and include `complete: false` with a next-page token when a response is cut.
**Update (15 Nov 2026):** the truncation is in the MCP server, not the API. Called directly with the API key, `get_tehsil_data` returned every dataset complete for the same kind of tehsils: `lulc_vector` with 171 of 171 MWS for Junnar (251,000 characters) and 170 for Daund, and `antyodaya` with 188 villages for Bhor (1.3 million characters). The MCP server cuts the body at 180,000 characters (CS-84). The fix belongs in the MCP server; pagination would still help clients with size limits.

### CS-60 · District name with a parenthetical alias fails
`get_active_locations` lists "Keonjhar (Kendujhar)". Passing that string returns a DistrictSOI 404, so the district cannot be reached.
**Fix:** accept the listed name, or return a canonical slug in `get_active_locations`.

### CS-61 · `filtered_mws` layer URL is "unknown"
`get_generated_layer_urls` returns `unknown` for the `filtered_mws` layer. The response for that route is also very large (it lists every layer for the tehsil), which makes it costly to call just to find one layer.
**Fix:** fill in the URL, and allow filtering by layer name.

### CS-62 · `green_credit` exposes presigned S3 URLs
`green_credit` rows (Nandapur 4_48305, Jaypur 4_58094) carry `kml_url` values that are AWS presigned URLs. They include the access-key ID and a signature. These should not be in a public API response. The pipeline strips `kml_url` on ingest.
**Fix:** serve the KML through an API route, or use short-lived signed URLs issued on request.

### CS-63 · Same MWS returns different values from different tehsils
972 of 4,598 MWS straddle tehsil boundaries, so each tehsil's response includes them. For the same `uid`, `hydrological_annual` (`delta_g`, `et`), `croppingdrought_kharif` and sometimes `soge_vector` differ between tehsils. Area and land use agree. Example: 12_208742 has `delta_g` mean −34.97 mm in Belthara Road and −35.97 mm in Sikandarpur. Drought mean moderate+severe weeks are 0.50 and 0.625.
**Fix:** compute MWS layers once on the full MWS polygon and serve identical values regardless of the requesting tehsil. For SOGE, report the area-weighted block value or the block of majority area.

### CS-64 · `mws_intersect_villages` lists only villages inside the requested tehsil
For a boundary MWS, village intersections sum to far less than the MWS area. Median coverage is 0.85 after merging all tehsils of a district, and 0.6 within a single tehsil. A few MWS show village intersect area up to 5× the MWS area (e.g. in Srikakulam), which points to overlapping village polygons.
**Fix:** return all villages that intersect the MWS, with a tehsil column, and check village polygon overlaps.

### CS-65 · `surfacewaterbodies_annual` omits MWS with no water body and can exceed MWS area
MWS with no water body are absent rather than zero. The pipeline imputes zero. In a few MWS, `total_area` is up to 5.9× the MWS area. This suggests water-body polygons are not clipped to the MWS. Separately, `kharif_area` and `rabi_area` are nearly equal in many rows, which makes it unclear what `rabi_area` measures.
**Fix:** return zero rows, clip to the MWS, and document the seasonal columns.

### CS-66 · Livestock and social rows do not match village polygons
Haveli returns 113 social/livestock rows, but GeoServer has 549 village polygons. Villages with `data_availability_status` "no data available for this village" are included with zeros, which reads as zero livestock.
**Fix:** return null values when there is no data, and document how villages are matched to the livestock census.

### CS-67 · Modelled groundwater change is biased negative
Across the 4,598 MWS, the median `delta_g` is −76 mm/yr. The summed `welldepth` falls 10.6 m over 2017–24 (−1.3 m/yr). That includes MWS in Safe blocks with stage of extraction near 20% (Godda, Koraput). Pune's median is −45 m over eight years. These values cannot be used against CGWB absolute thresholds, so the pipeline uses pooled percentiles.
**Fix:** document the components and their uncertainty, validate against CGWB observation wells, and say whether `welldepth` is a water-level change or a storage change divided by specific yield.

### CS-68 · Precipitation is spatially over-smoothed and departs from district normals
CoRE precipitation for 2017–24 gives Srikakulam 1,742 mm against an 1,162 mm normal, and Godda 1,008 mm against about 1,530 mm. Pune shows 627–874 mm, although its tehsils span roughly 450 to over 2,000 mm. The pipeline rescales precipitation to district normals.
**Fix:** state the source and resolution of the precipitation layer; consider IMD 0.25° gridded data.

### CS-69 · `literacy_rate` uses total population as the denominator
`literacy_rate` matches `P_LIT / TOT_P`, which includes children aged 0–6. Census literacy uses the population aged 7+. Koraput comes out at 32% against a Census figure of 49%.
**Fix:** use the 7+ population, or rename the field.

### CS-70 · Cropping intensity is relative to cultivable area and double cropping is over-detected in sub-humid areas
`cropping_intensity` divides by `sum_area` (cultivable area including fallow), not net sown area, so values below 1 occur. In Godda, the median cropping intensity is 1.48 and the double-cropped share is 0.77, while the ICAR-CRIDA plan gives about 1.08 and 15% irrigated. Residual-moisture greenness and weeds are probably counted as a second crop.
**Fix:** document the denominator and add a confidence flag or a minimum-NDVI threshold for the second season.

### CS-71 · District naming differs from current boundaries
"Ananthapur" tehsils such as Kadiri-area mandals now belong to Sri Sathya Sai district, and Salumber is now its own district in Rajasthan. The API uses the old names.
**Fix:** add a current-district field or an alias table.

### CS-72 · Small responses are returned inline by the client
This is a client-side limit, not an API bug. Responses below about 50k characters are returned inline instead of being saved to a file. Batch ingestion therefore needs padding datasets to force saving.

### CS-73 · Land-cover classes cover only 80–90% of some MWS; `cropland_area` is always zero
In 835 of 4,598 MWS (18%), the `lulc_vector` classes average 80–90% of the MWS area. Both API rows and GeoServer rows show this. The MWS are concentrated in hilly, monsoon-cloudy tehsils: Jaypur, Koraput and Narayanpatana (Koraput); Girwa (Udaipur); Mawal and Khed (Pune); and Sundarpahari, Poreyahat and Boarijor (Godda). Example: 25_14663 sums to 0.89. Meanwhile `cropland_area` is zero in every row returned. The missing area is probably cropland whose season could not be classified, or no-data pixels, but the response does not say.
**Fix:** return the generic cropland class (or an explicit unclassified/no-data class) so classes add up to the MWS area.

## Query 18

**Request:** Refresh the eight sample districts with the datasets added for the signal-based rules (`soil_health`, `nrega_annual`, `antyodaya`, `facilities_proximity`, `river`, `mws_connectivity`, `forest_fringes`, `forest_fire`, `tree_in_grassland`, `ndvi`) and report missing variables.

**Call sequence:** `list_public_apis` → `get_tehsil_data` (Srikakulam / Kaviti, 16 MWS, seven new datasets) → `get_active_locations` (same tehsil). Both calls returned 404 because the MCP server on the user's computer was configured for the UAT host, which has no v2 routes. This was a local configuration problem, fixed the same evening, and is not logged as an API issue. The variable definitions were checked in the meantime against the published API metadata. (Metadata: `https://docs.core-stack.org/use-precomputed-data/api-metadata/`, `get_tehsil_data` data dictionary.)

**Missing variables:** none. All 37 columns that the new indicators read are listed in the metadata, for example `N_p05_in_kg_per_ha`, `total_hhd_mobilized_into_shg`, `bank_branch_distance_in_km`, `tree_loss_in_tree_in_shrub_area_in_ha` and `shrub_slope`. The problems are with the schema of the older datasets and with the route itself, below.

### CS-74 · Documented schema differs from the responses ingested in October
The pipeline was built on rows of the form `{"metadata": {"uid": …}, "annual": {"time": [2017, …], "delta_g": […]}}` with plain column names (`uid`, `total_area`, `cropping_intensity`, `mild`, `built-up_area`, `aquifer_classes` / `aquifer_percentages`, `total_population`). The metadata now describes flat rows with unit and year suffixes:
- `hydrological_annual`: `DeltaG_in_mm_2017-2018`, `ET_in_mm_…`, `RunOff_in_mm_…`, `WellDepth_in_m_…`, `UID`;
- `croppingDrought_kharif`: `Mild_in_weeks_2017`, `drysp_unit_4_weeks_2017`, `kharif_cropped_sqkm_2017`;
- `croppingIntensity_annual`: `cropping_intensity_unit_less_2017-2018`, `*_area_in_ha_…`;
- `lulc_vector`, `surfaceWaterBodies_annual`, `restoration_vector`, the change-detection datasets: `*_in_ha`;
- `terrain`: `*_area_percent`; `soge_vector`: `soge_dev_percent`; `aquifer_vector`: one `principle_aq_<class>_percent` column per class;
- `social_economic_indicator`: `total_population_count`, `total_SC_population_count`, `literacy_rate_percent`;
- `mws_intersect_villages`: `MWS UID`, `Village Details`, `Village IDs`.

If the live API now returns this form, a client built on the October responses loses nearly every indicator without an error. It could not be confirmed against the live API at the time. The SEFT loader now accepts both forms (`seft/schema.py`), and the offline test exercises both. The structure of `Village Details` is not documented, so the loader still expects the October form (`keys`, `values`, `area_intersect`).
**Fix:** version the response schema (for example `schema_version` in every response), announce breaking renames, and document the structure of nested fields such as `Village Details`.
**Update (Query 19):** the live API still returns the October form for the annual datasets, so the documented flat form is not what `get_tehsil_data` sends (CS-82). The Excel export (Bhandaria) follows the documented form.

### CS-75 · Tree-cover change datasets renamed
`change_detection_tree_cover_decrease` and `change_detection_tree_cover_increase`, used in October, are not in the documented list. The list has `change_detection_deforestation` (`total_deforestation_area_in_ha`, `forest_to_farm_area_in_ha`, …) and `change_detection_afforestation` (`total_afforestation_area_in_ha`, …), plus `overall_tree_change`, which disagrees with them (CS-55). The SEFT config now requests the documented names, and the loader reads files saved under either name.
**Fix:** keep the old names as aliases for a deprecation period, or return an error that names the replacement.

### CS-76 · `green_credit` no longer documented
`green_credit` returned an empty object in Query 15 (CS-52) and rows with presigned S3 URLs in Query 17 (CS-62). It is now absent from the documented dataset list. SEFT marks it optional, so its absence does not fail `audit`.
**Fix:** state whether the dataset is withdrawn, and if so where Green Credit projects can be obtained.

### CS-78 · `hydrological_annual` field descriptions contradict the layer description
The layer description says the vector holds annual precipitation, runoff, evapotranspiration, the water balance (P − ET − runoff) and the *cumulative* water balance since 2017. The field metadata describes `G_in_mm` as "Groundwater storage change (G)" and `DeltaG_in_mm` only as "DeltaG in mm". It also leaves open whether `WellDepth_in_m` is a depth or a change in depth. This matters for CS-67 (the strong negative bias): SEFT uses `DeltaG` as the annual storage change and the trend of cumulative `WellDepth` as the water-level trend. If `G` is the cumulative balance, a second reading of the same quantity is available for checking.
**Fix:** define each field in the metadata (formula, period, sign convention, annual or cumulative), consistent with the layer description and `computing/mws/well_depth.py`.
**Update (Query 19):** the live values answer the question: `delta_g` = P − ET − runoff, `g` = cumulative `delta_g`, `welldepth` = `delta_g` / specific yield (CS-85).

### CS-79 · Year suffixes mix calendar and agricultural years
`lulc_vector`, `croppingDrought_kharif` and `nrega_annual` use calendar-year suffixes (`_2017` … `_2024`). `croppingIntensity_annual`, `hydrological_annual` and `surfaceWaterBodies_annual` use agricultural years (`_2017-2018` … `_2024-2025`). Joining them by year needs an assumption about which agricultural year a calendar-year label means. SEFT keys an agricultural year by its first year (2017-2018 → 2017).
**Fix:** use one convention, and state the start month of each year in the metadata.

### CS-80 · Dataset ids mix camelCase and snake_case
`croppingIntensity_annual`, `croppingDrought_kharif`, `surfaceWaterBodies_annual`, `village_GP`, `Canopy_Cover_Density` and `Canopy_height` are camelCase; the other 38 ids are snake_case. The October calls used lower-case ids (`croppingintensity_annual`) and were accepted, but whether matching is case-insensitive is not documented.
**Fix:** accept ids case-insensitively and document it, or move all ids to snake_case with aliases.

### CS-81 · Metadata gaps in the newer datasets
- `ndvi`: `shrub_slope`, `crop_slope` and `tree_slope` have no unit, period or method ("Shrub slope."), so a threshold cannot be set; SEFT uses pooled percentiles. The `*_trend` values are not listed.
- `forest_fire`: `fire_count_per_year` is one number, but the averaging period is not stated.
- `nrega_annual`: category names contain spaces and a hyphen (`Off-farm livelihood assets_count_2018`); it is not stated whether counts are works started, completed or cumulative; the ID key differs from other datasets (CS-54).
- `mws_connectivity`: `upstream_mws` is typed "string" but described as a list; the separator is not stated.
- `antyodaya`: `data_availability_status` values are not listed; `village_id` is a float; the survey period (2018–2020) is given only in the layer description.
- `soil_health`: the metadata do not say what area the percentiles describe. (Clarified by the CoRE team on 21 Nov 2026: N, P, K and OC percentiles describe the cropped area, `area_under_cropping`; `oc_olm` percentiles describe the tree-cover area, `area_under_tree_cover`, from OpenLandMap.) It is not stated whether the values are predicted or sampled.
**Fix:** give units, period, method and allowed values for each field.

## Query 19

**Request:** Refresh the sample districts through the MCP server, now pointed at a working host, using the Excel export of Bhandaria as a guide to field names. The full refresh was then run directly against the API with a production key.

**Call sequence:** `get_active_locations` (Kaviti) → `get_tehsil_data` (Kaviti; 15 datasets) → 400 (unknown names) → `get_tehsil_data` (12 datasets; body cut at 180,000 characters) → `get_tehsil_data` (11 datasets) → `get_tehsil_data` (`ndvi_shrub`, `canal`, `green_credit`, `overall_tree_change`, `change_detection_tree_cover_decrease`) → `get_generated_layer_urls` (Kaviti).

**Missing variables:** forest fires, forest-edge degradation and trees in grassland could not be requested by name through v2 (CS-83); they were later fetched through v1, and v2 also returns them with `data=all`. `ndvi_shrub`, `canal` and `green_credit` came back empty for Kaviti and were left out of the response without notice (as in CS-52). Everything else the indicators need is present.

### CS-82 · Live responses differ from the documented schema and from the Excel export
`get_tehsil_data` returns:
- annual datasets (`hydrological_annual`, `croppingdrought_kharif`, `nrega_annual`) in the October form: `{"metadata": {"uid": …}, "annual": {"time": ["2017", …], "delta_g": […]}, "annual_units": …}`;
- `nrega_annual` keyed by `metadata.mws_id`, not `uid`;
- flat datasets with lower-case keys and `uid`, not `UID`;
- unit suffixes kept in some fields and dropped in others: `n_p05_in_kg_per_ha` but `oc_p05` (documented `OC_p05_in_percent`), and `bank_branch_distance` (documented `bank_branch_distance_in_km`); `area_under_cropping` (documented `_in_ha`);
- `aquifer_vector` as `aquifer_classes` / `aquifer_percentages` lists, not `principle_aq_<class>_percent`; `tehsil_units` still lists the `principle_aq_*` names.

The Excel export of Bhandaria uses the documented names (`UID`, `DeltaG_in_mm_2017-2018`, `OC_p05_in_percent`). A client built from the documentation or the export therefore misreads the API. SEFT now reads all three forms (`seft/schema.py`).
**Fix:** make the API, the docs and the export use one schema, and make `tehsil_units` describe the fields actually returned.

### CS-83 · Forest and NDVI datasets cannot be requested by name in v2
`data=forest_fire,forest_fringes,ndvi,tree_in_grassland` returns 400 "Unknown data filter value(s)". The accepted list in the error message has `ndvi_shrub` instead of `ndvi`, and no fire, forest-edge or tree-in-grassland entry. Yet v2 does serve all four. Called with no `data` parameter, or with `data=all`, it returns `forest_fire`, `forest_fringes`, `tree_in_grassland` and `ndvi` with the same rows and values as v1. This was checked for Kaviti on 16 Nov 2026: 14, 16, 16 and 16 MWS, all identical. The filter is therefore out of step with the data. `data=ndvi_shrub`, which the filter accepts, returns an empty `tehsil_data`.

The filter list also still has `change_detection_tree_cover_decrease` / `_increase`, which the docs replace with `change_detection_deforestation` / `_afforestation` (CS-75). It also lists datasets missing from the docs: `agroecological`, `factory_csr`, `lcw_conflict`, `mining` and `drought`.

v1 and v2 also name the forest-edge columns differently. v1 has `tree_deforestation_fringe_area_in_ha`; v2 has `tree_tree_cover_decrease_fringe_area` (with "tree" doubled), with the values unchanged. The same holds for `tree_in_grassland`: v1 `shrubs_trees_area_in_ha`, v2 `shrubs_trees_area`.
**Fix:** accept every dataset that `data=all` returns as a filter value (`forest_fire`, `forest_fringes`, `tree_in_grassland`, `ndvi`); drop or fix `ndvi_shrub`; keep the documented names as aliases; and use the same column names in both versions.

### CS-84 · The MCP server cuts responses at 180,000 characters, with no flag (the API itself does not)
A 12-dataset request for Kaviti (16 MWS, 30 villages) returned `body` as a string of exactly 180,000 characters, ending mid-row. The JSON was unparseable, and four datasets were present, one of them (`facilities_proximity`) cut after 9 of 19 villages. Datasets are not returned in the order requested, so which ones survive is unpredictable. An Antyodaya row is about 4,500 characters (160 fields), so one call holds about 40 villages; most sample tehsils have 130 to 550. The layer list (`get_generated_layer_urls`) has no Antyodaya, facilities, soil or NREGA layer, so GeoServer back-fill (CS-59) is not available for them.
The API does not cut responses. Called directly (`https://geoserver.core-stack.org/api/v2/get_tehsil_data/` with `X-API-Key`), the same Kaviti request returned all 19 facilities villages. Antyodaya came back complete at 800,000 characters for Haveli and 1.3 million for Bhor. The 180,000-character limit is applied by the MCP server, which returns the cut body as a string with status 200 and no warning. It is also the cause of the October truncation (CS-59).
**Fix (MCP server):** raise or remove the limit, or split large responses across calls, and say when a body has been cut (`truncated: true`, original length). **Fix (API, optional):** pagination and a `fields=` filter would let size-limited clients get complete data.

### CS-85 · `delta_g` is P − ET − runoff only; `welldepth` is a fixed multiple of it
In all 16 Kaviti MWS, `delta_g` equals precipitation − ET − runoff to 0.01 mm, `g` is its running sum, and `welldepth` equals `delta_g` times a constant per MWS (0.013 to 0.033 m per mm, so a specific yield of 0.03 to 0.08). The balance has no baseflow, lateral flow or groundwater extraction term. In wet hard-rock MWS it implies storage gains of 500 to 1,350 mm a year, and water-table rises of 10 to 28 m a year (22_25114: +1,161 mm and +23.9 m in 2017-18). In dry irrigated MWS it gives the strong negative values of CS-67. `welldepth` is an annual change in water level, not a well depth, and adds no information beyond `delta_g`. SEFT therefore uses only percentile-based groundwater signals (CS-67).
**Fix:** subtract baseflow and extraction (CGWB draft data), or rename the fields as "vertical water surplus"; state that `welldepth` is a change in level.

## Query 20

**Request:** Full refresh of the eight sample districts (73 tehsils, 4,598 MWS) directly against the API.

**Call sequence:** `get_tehsil_data` v2, one request per dataset per tehsil (about 1,800 requests, five in parallel, 8–15 s each) → `get_tehsil_data` v1, one request per tehsil, for `forest_fire`, `forest_fringes`, `tree_in_grassland` and `ndvi` → `seft.cli audit` → `seft.cli run`.

**Result:** every request succeeded and no response was cut (CS-84). MWS and village counts match the October run exactly (4,598 MWS, 9,522 villages). All 27 causal pathways now have data. The datasets that are still incomplete are listed under CS-88.

### CS-86 · `soge_vector` is now yearly, with `-9999` for missing values
In October, `soge_vector` returned one assessment per block (`soge_dev`, `class_name`). Production v2 now returns an `annual` block with assessments for 2011, 2013, 2017, 2020, 2022, 2023, 2024 and 2025 in 72 of 73 tehsils. v1 returns the same as `soge_dev_percent_2025` and so on. Missing values are `-9999`, including whole fields in 2025 (`extraction_for_irrigation_in_bcm`, `natural_discharge_in_bcm`). Two things follow:
- A client expecting the October form fails on the text field (`class_name`: "Semi-Critical").
- Results shift with the newest assessment. The median stage of extraction for Ananthapur MWS moved from 93% to 61%, and MWS flagged for over-extraction from 58% to 43%.

SEFT uses the latest year with a valid stage of extraction and records it as `assessment_year`.
**Fix:** announce the change, use `null` instead of `-9999`, and state which assessment year is current.

### CS-87 · NDVI slopes are rounded to zero
`shrub_slope`, `tree_slope` and `crop_slope` have two decimals. Annual NDVI slopes are of the order of 0.001, so 96% of the 5,647 MWS have a slope of exactly 0. The trend class is more useful: `shrub_trend` is "No trend" in 4,751, "Increasing" in 672 and "Decreasing" in 224. SEFT uses the class. As first written, the shrubland NDVI signal was on in every MWS, because the pooled threshold was 0.
**Fix:** return slopes with four or more significant digits, and give their unit and period (CS-81).

### CS-88 · Coverage gaps after a complete fetch
These datasets returned complete responses that lack rows for some MWS listed in the tehsil's MWS layer:

| Dataset | Tehsils affected | MWS missing |
|---|---|---|
| `mws_intersect_villages` | 54 | 418 |
| `soil_health` | 27 | 90 |
| `soge_vector` | 26 | 88 |
| `mws_connectivity` | 16 | 73 |

Why these MWS are missing was not checked. Boundary-straddling MWS (CS-63) are a likely cause for the village links, since the API lists only villages inside the selected district. A missing village-link row means the MWS gets no Census, livestock, Antyodaya or facilities data.
**Fix:** include every MWS of the tehsil in every MWS-level dataset, with nulls where a value is unavailable, and include villages from neighbouring districts in `mws_intersect_villages`.

## Query 21

**Request:** Full refresh of the same 73 tehsils with a single v2 request per tehsil, and no v1 calls.

**Call sequence:** `get_tehsil_data` v2 with no `data` filter, one request per tehsil (73 requests, five in parallel, about 1 MB each) → `seft.cli audit` → `seft.cli run`.

**Result:** every request succeeded and returned every dataset the atlas uses, including `forest_fire`, `forest_fringes`, `tree_in_grassland` and `ndvi` (CS-83). The v2 forest-edge and trees-in-grassland columns, mapped to the v1 names, give the same values as v1. Compared with the 16 Nov run (v2 per dataset plus v1), 98.7% of the 2.5 million exported values are unchanged, and pathway counts differ by at most two MWS. The differences come from CS-89, not from the change of request.

### CS-89 · Census village rows changed without notice
A refetch on 21 Nov 2026 returned a different `social_economic_indicator` from the one fetched on 15 Nov, with no version or date to show it had changed:

- **Villages dropped.** In 13 tehsils (12 in Srikakulam, plus Raptadu in Ananthapur), 206 villages that `mws_intersect_villages` still lists no longer have a Census row. In Burja, 24 of 85 linked villages are gone; in Sitampeta, 26 of 48. The MWS concerned keep their village links but lose population, SC/ST and literacy for that part of their area. Population coverage of the MWS area fell, for example from 50% to 47% of the area of Burja MWS 22_20116.
- **Duplicates corrected.** Six villages in Udaipur, Amaravati and Pune had double population and caste counts on 15 Nov and now have half, with corrected names: SAWEENA KHERA (RURAL) became SAWEENA (RURAL), 8,982 became 4,491; BORHADEWADI (NV) became PIMPRI CHINCHWAD, 6.9 million became 3.5 million. This looks like a fix.
- **Placeholder removed.** A placeholder row (village_id 0, "Forest", all zeros) is no longer returned in any tehsil.

The same 61 rows for Burja come back with `data=social_economic_indicator`, with `data=all` and with no filter, so the change is in the data, not the request. The effect on the atlas is small: four pathways changed by one or two MWS out of 4,598, because the social signals use population per hectare of covered area and shares, which do not depend on full coverage.
**Fix:** restore the dropped villages or say why they were removed; version or date the Census layer so users can see when it changes.

## Query 22

**Request:** Add the `mining` dataset to the 73 sample tehsils, and NREGA, FPO and cooperative fields to the atlas rules.

**Call sequence:** `get_tehsil_data` v2 without a `data` filter, one request per tehsil (73 requests), keeping only `mining` → `seft.cli run`.

**Result:** `mining` has 38 rows (31 in Udaipur, 4 in Koraput, 3 in Ananthapur) in 18 MWS (13, 3 and 2). Each row is a mining site or an environmental-clearance proposal in an MWS. The dataset is left out of the response where a tehsil has none, as with `forest_fire` (CS-52).
- **Unknown fields:** 27 of the 38 rows have `division`, `proposal`, `sector_moefcc` and `village` all set to "unknown", so these mapped sites cannot be matched to a clearance or a mineral.
- **Godda:** no rows, though the district has coal mining. The layer may not cover every mine.

### CS-90 · Cooperative distances look incomplete
`cooperative_cat_distance` (label "Cooperatives And Societies") is above 50 km for 7,283 of the 9,529 sample villages, with a median of 78 km. Bank branch distances in the same rows are all below 50 km. In Ananthapur, `agri_industry_co_operatives_societies_distance` repeats the same value. Primary agricultural credit societies (PACS) exist in most panchayats, so the cooperative point layer appears to cover only a few societies. The atlas leaves this field out of its rules.
**Fix:** state which cooperatives the layer includes; add PACS locations if they are meant to be covered.

## Query 23

**Request:** Ground-truth check: fetch the tehsils listed in a ground-truth file (`seft.cli groundtruth`) and score the atlas and Signal_Verification rules.

**Call sequence:** `get_active_locations` v2 (once, cached) → `get_tehsil_data` v2 without a `data` filter, one request per tehsil, plus GeoServer geometry → `seft.cli groundtruth`.

**Result:** all 32 block names were found in `get_active_locations`. "Keonjhar" is listed as "Keonjhar (Kendujhar)". Karera (Shivpuri, Bhilwara) and Mau (Chitrakoot, Mau) each appear in two districts and were settled by which tehsil contains the listed MWS.

### CS-91 · Nitrogen is zero across Udaipur
In `soil_health`, available nitrogen is 0 kg/ha for most Udaipur MWS:
- **Udaipur:** the median of the MWS means is 0.16; in most rows `n_p05` to `n_p50` are exactly 0, and the 95th percentile of MWS means is 56.
- **Other districts:** the median MWS ranges from 69 kg/ha (Chitrakoot) to 589 kg/ha (Palghar).
- **Other nutrients in Udaipur:** phosphorus, potassium and organic carbon look normal in the same rows.

This looks like a gap in the nitrogen layer stored as 0. Rules read it as severe nitrogen deficiency.
**Fix:** return null where the nitrogen layer has no value, and check the Udaipur nitrogen layer.

## To verify, not confirmed as bugs

- `antyodaya.availability_of_fpos_pacs` is blank in 7,493 of the 9,340 sample villages that answered the survey; the rest say FPO, PACS or Both. The atlas reads a blank as "neither". If a blank means "not asked", FPO access is understated.

- `antyodaya` piped-water coverage dates from the 2018–20 survey, before most Jal Jeevan Mission connections. It is low in most MWS (39–87% of MWS per district below half of households), so drinking-water signals built on it overstate current scarcity. A current JJM coverage field would help.

- `/api/v1/get_tehsil_data/` ignores the `data` filter and returns every dataset (about 1 MB for a 16-MWS tehsil), in the documented flat schema. It serves `forest_fire`, `forest_fringes`, `tree_in_grassland` and `ndvi`, as v2 does without a `data` filter (CS-83). Its `soge_vector` has yearly assessments 2011–2025 and uses `-9999` for missing extraction and recharge values. Its `mws_intersect_villages` returns `village details` as the string form of a Python dict (`"{580399: {'area_intersect': 56.9, …}}"`), not JSON.

- The UAT host (`uat.core-stack.org:444`) answers unknown paths with Django's debug page (`DEBUG = True`), which lists the URL configuration.

- `avg_precipitation` for Chintamani micro-watersheds is about 800 to 1,000 mm, which seems high for this part of Karnataka. It may reflect the averaging period (CS-05).
- `urbanization_area` and `degradation_land_area` are labelled "ha". Given CS-04 and CS-16, these labels are worth checking.

## Working as expected

- `get_admin_details_by_latlon` and `get_mwsid_by_latlon` agreed with each other on every point tested.
- `decrease_in_tree_cover` in the KYL route matched `total_tree_cover_decrease_area` in the tehsil dataset for all 13 micro-watersheds checked.
- `get_tehsil_data` returned per-micro-watershed `area` and a `tehsil_units` block with clear units.
- `croppingintensity_annual` returned a complete, consistent 2017 to 2024 series for all 114 micro-watersheds, and its IDs matched the GeoServer layer exactly.
- The unknown-name error in call 9.1 listed every valid dataset name.
- `get_tehsil_data` accepted two dataset names in one call (call 13.2).
- `hydrological_annual` returned promptly, complete for 114 units and 8 years, and its water balance closed exactly.

## Routes not yet exercised

`get_waterbody_data`.

## Change log

- 10 Oct 2026: file created with 25 issues from the first four queries.
- 10 Oct 2026: reorganised by query with call sequences and bug IDs. Two earlier entries were split so each ID is a single fixable issue (village ID problems into CS-18, CS-19 and CS-28; field hints into CS-02 and CS-24), giving 28 IDs.
- 10 Oct 2026: Query 7 added (fortnightly water balance). New IDs CS-29 to CS-35; CS-26 extended to a second route.
- 10 Oct 2026: Queries 8 and 9 added (cropping intensity map). New IDs CS-36 to CS-40; CS-15 extended to `get_mws_geometries`; CS-25 and CS-31 revised after the valid dataset list became known.
- 10 Oct 2026: Query 10 added (water balance vs cropping intensity). New IDs CS-41 and CS-42.
- 10 Oct 2026: Query 11 added (kharif and rabi surface water map). New IDs CS-43 and CS-44.
- 10 Oct 2026: Query 12 added (tree cover vs groundwater balance). New IDs CS-45 to CS-47.
- 10 Oct 2026: Query 13 added (village ranking on dry-season water). New IDs CS-48 to CS-50; CS-44 largely explained by comparing the API with the GeoServer layer.
- 10 Oct 2026: Query 14 added (relational village clusters). New ID CS-51; CS-48 extended to `get_waterbody_data`; CS-15 extended to `mws_intersect_swb`.
- 10 Oct 2026: Query 15 added (scheme convergence by micro-watershed). New IDs CS-52 to CS-54.
- 12 Oct 2026: Query 16 added (stresses from tehsil data, tree cover, drought access, methodology). New IDs CS-55 to CS-58; CS-52 extended to `green_credit`; CS-45 and CS-15 seen again.
- 13 Oct 2026: Query 17 added (social-ecological functional types across 8 districts). New IDs CS-59 to CS-72; CS-52 seen again (green_credit), CS-15 extended to straddling MWS.
- 18 Oct 2026: CS-73 added (land-cover classes do not cover the full MWS in hilly tehsils), found while explaining how system shares add up to 100%.
- 15 Nov 2026: Query 18 added (data refresh for the signal-based rules). The refresh was blocked by a local MCP configuration problem (since fixed); the variable definitions were checked against the published metadata. New IDs CS-74 to CS-81.
- 15 Nov 2026 (evening): Query 19 added (refresh through the reconfigured MCP server). New IDs CS-82 to CS-85; CS-74 and CS-78 updated.
- 15 Nov 2026 (late evening): CS-77 withdrawn (local MCP configuration, fixed). CS-84 and CS-59 attributed to the MCP server after direct API calls returned complete data.
- 16 Nov 2026: Query 20 added (full direct refresh). New IDs CS-86 to CS-88.
- 16 Nov 2026 (evening): CS-83 corrected after a v1/v2 comparison for Kaviti. v2 returns the forest and NDVI datasets with `data=all`; only its `data=` filter rejects them.
- 21 Nov 2026: Query 21 added (refresh with one v2 request per tehsil, no v1). New ID CS-89. The v1 note under "To verify" now records only what v1 returns, since the atlas no longer calls it.
- 21 Nov 2026 (evening): Query 22 added (mining, NREGA and FPO fields). New ID CS-90; FPO blanks added under "To verify".
- 21 Nov 2026 (late evening): Query 23 added (ground-truth check). New ID CS-91; soil percentile coverage clarified in Query 18.
