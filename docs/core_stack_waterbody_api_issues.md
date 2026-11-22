# CoRE Stack public API: waterbody issues log

Issues with the waterbody routes (`get_waterbodies_data_by_admin`, `get_waterbody_data`), the `swb` GeoServer layers (`swb:surface_waterbodies_{district}_{tehsil}`, `swb:waterbodies_zoi_{district}_{tehsil}`, `crop_intensity:{district}_{tehsil}_intensity_ZOI`) and the surface-water datasets in `get_tehsil_data`.

- Started 22 Nov 2026, when work began on a waterbody atlas. The general log is `docs/core_stack_api_issues.md`.
- New waterbody issues are numbered `WB-01` onwards. Six earlier issues were moved here from the general log and keep their `CS-` numbers (CS-12, CS-43, CS-44, CS-48, CS-49, CS-65).
- Calls were made directly over HTTPS with the API key as the `X-API-Key` header (not shown), except where noted.
- Tehsils checked on 22 Nov 2026: Srikakulam / Kaviti (1,876 records), Udaipur / Gogunda (3,172), Amaravati / Morshi (1,999), Karnataka / Chik Ballapur / Chintamani (502, see CS-48).

Severity:
- **High**: led or could lead to a wrong conclusion, or blocked the task.
- **Medium**: forced a workaround or left a result ambiguous.
- **Low**: cosmetic or documentation.

Clarified by the CoRE Stack team (22 Nov 2026), so not logged as issues:
- `k`, `kr` and `krz` are the percentages of the waterbody's area that held water in kharif, in kharif and rabi, and in kharif, rabi and zaid.
- The zone of influence is a radius in metres around the waterbody that grows with the logarithm of its size.
- The Water Body Census fields are matched to CoRE waterbodies by proximity and by similarity of storage capacity to waterbody area, so they may not be accurate.

## Summary

| ID | Severity | Issue | Route or layer |
|---|---|---|---|
| WB-01 | High | Fragmented waterbodies: several `wb_id`s carry one waterbody's `area_ored` and yearly series | `get_waterbodies_data_by_admin` |
| WB-02 | High | Zone-of-influence records cannot be linked to waterbody records | `get_waterbodies_data_by_admin` |
| WB-03 | Medium | `category_sq_m` is "0-500" for every waterbody | `get_waterbodies_data_by_admin` |
| WB-04 | Medium | Wrong or missing units: `zoi`, `sum`, `k`/`kr`/`krz` | `get_waterbodies_data_by_admin` |
| WB-05 | Medium | Two record shapes in one list, with no type field | `get_waterbodies_data_by_admin` |
| WB-06 | Medium | Very large waterbodies with implausible stream order and catchment; river pieces marked off the drainage line | `get_waterbodies_data_by_admin` |
| WB-07 | Medium | Census fields carry wrong admin and basin names | `get_waterbodies_data_by_admin` |
| WB-08 | Low | No coordinates or geometry in the API response | `get_waterbodies_data_by_admin` |
| WB-09 | Low | Waterbodies in MWS outside the tehsil are included without a flag | `get_waterbodies_data_by_admin` |
| CS-12 | Low | Waterbody list bloats the response, little usable content | `get_mws_kyl_indicators` |
| CS-43 | High | Kharif and rabi surface water areas are near-identical; seasonal fields appear nested and are undefined | `get_tehsil_data` |
| CS-44 | Medium | Three undefined "total" water areas that disagree (`total_area`, `total_swb_area`, kharif) | `get_tehsil_data` |
| CS-48 | High | Waterbody routes return 502 `Merged dataset not available for given area` for Chintamani | `get_waterbodies_data_by_admin`, `get_waterbody_data` |
| CS-49 | Medium | Waterbody layer: a third of features lie outside the tehsil; duplicate and empty attribute columns | GeoServer `swb` layer |
| CS-65 | Unrated | `surfacewaterbodies_annual` omits MWS with no water body and can exceed MWS area | `get_tehsil_data` |

## New issues (22 Nov 2026)

**WB-01. Fragmented waterbodies: several `wb_id`s carry one waterbody's `area_ored` and yearly series** (High)
- Observed (Kaviti): `wb_id` 15293126 (`total_area` 0.02 ha) and 15293143 (0.01 ha) both report `area_ored` 21.37 ha and the same `area`, `k`, `kr` and `krz` series for 2017–24. Both are pieces of the Bahuda river.
- Records that share `area_ored` and an identical yearly series: 1,010 records but 464 distinct series in Kaviti, 1,781 and 892 in Gogunda, 1,118 and 470 in Morshi. Some identical series in very small waterbodies may be chance, so these counts are an upper bound on fragmentation.
- Impact: summing waterbodies counts the same water several times; a fragment of 0.01 ha appears to hold 20 ha of water.
- Suggested fix: merge fragments into one waterbody with one id, or give every fragment a parent id.

**WB-02. Zone-of-influence records cannot be linked to waterbody records** (High)
- Observed: waterbody records are keyed by `wb_id` (an integer, also in `UID`, for example 15294152). Zone-of-influence records are keyed by `UID` values such as `22_25114_102`, an MWS uid and an index, and carry no `wb_id`. Kaviti has 1,010 waterbody records and 866 zone-of-influence records.
- The GeoServer layers do not help: `swb:surface_waterbodies_*` uses the same `UID` (= `wb_id`) as the API, and `swb:waterbodies_zoi_*` has only `UID` (the MWS-uid-and-index form), the cropping fields, `zoi`, `zoi_area`, `sum` and the polygon. No field in either layer names the other. The Landscape Explorer matches the two layers on `UID`, which cannot succeed for this tehsil.
- A spatial match works for most: for 626 of Kaviti's 866 zones of influence, the centre of the zone lies within 10 m of a waterbody's centre (median 3 m), and the radius rises steadily with waterbody area (about 27 m at 0.01 ha, 140 m at 0.1 ha, 500 m at 1 ha, 790 m at 8 ha). Most of the 384 waterbodies left without a zone are fragments of one waterbody (WB-01): 337 of them share their series with another record.
- Impact: cropping intensity in a waterbody's zone of influence, the main evidence for irrigation use, cannot be attached to the waterbody from the API alone.
- Checked on 22 Nov 2026 for all 73 tehsils of the eight atlas districts: only Srikakulam / Sitampeta has a zone-of-influence layer with `wb_id` (1,886 zones; all 1,705 of its waterbodies have one, and `UID` equals `wb_id`). The other 72 use the MWS-uid-and-index form with no `wb_id`; for Pune / Baramati the zone-of-influence layer could not be read at all. Outside these districts, North Goa / Bardez also has `wb_id`, while South Goa / Sanguem does not.
- Suggested fix: put `wb_id` on each zone-of-influence record and feature, or nest the zone-of-influence fields inside the waterbody record. Explain what the index in the zone-of-influence `UID` refers to.

**WB-03. `category_sq_m` is "0-500" for every waterbody** (Medium)
- Observed: all 3,909 waterbody records in the three tehsils have `category_sq_m` "0-500", including waterbodies of 2,822 ha.
- Suggested fix: compute the size class from the area, or drop the field.

**WB-04. Wrong or missing units** (Medium)
- Observed: `zoi` is labelled "count" but is a radius in metres (`zoi_area` equals pi x `zoi`^2 to within 4%). `sum` is labelled "ha" but is in square metres (164,099.07 against `total_cropable_area_ever_hydroyear` 16.41 ha for `22_25114_102`). `k`, `kr` and `krz` are labelled "value" but are percentages.
- Suggested fix: correct the unit labels and document each field.

**WB-05. Two record shapes in one list, with no type field** (Medium)
- Observed: `data` mixes waterbody records (135 metadata fields and `area`, `k`, `kr`, `krz` per year) with zone-of-influence records (5 metadata fields and cropping per year). They can only be told apart by which fields are present.
- Suggested fix: return them as two named lists, or add a `record_type` field.

**WB-06. Very large waterbodies with implausible stream order and catchment; river pieces marked off the drainage line** (Medium)
- Observed (Kaviti): one waterbody of 2,822 ha spans 11 MWS, with `max_stream_order` 1 and `max_catchment_area` 14.31 ha; it is probably the sea or a coastal lagoon. River pieces of the Bahuda have `max_stream_order` 6 but `on_drainage_line` false.
- Impact: hydrological position, which decides the waterbody type, is unreliable for the largest bodies and for river pieces.
- Suggested fix: mask the sea and estuaries; document how stream order, catchment area and the drainage-line flag are computed for polygons that cross several streams.

**WB-07. Census fields carry wrong admin and basin names** (Medium)
- Observed (Kaviti, `wb_id` 15294152): the matched census record gives block Ichchapuram and village Kotari, while the waterbody lies in Kaviti tehsil (villages Bhyripuram and Tulasigam), and gives `basin_name` "Area of North Ladakha not draining into Indus Basin", `sub_basin_name` "Shaksgam". Matched on 2–5% of waterbodies (49 of 1,010 in Kaviti).
- Impact: the fields cannot be relied on without checking the match; the atlas does not use them in its main analysis.
- Suggested fix: publish the match method and a match-quality score; correct the basin join.

**WB-08. No coordinates or geometry in the API response** (Low)
- Observed: waterbody records have no latitude, longitude or polygon, except the census coordinates on matched records. Geometry is only in the GeoServer layer.
- Suggested fix: add a centroid (latitude, longitude) to each record.

**WB-09. Waterbodies in MWS outside the tehsil are included without a flag** (Low)
- Observed (Kaviti): 51 of 1,010 waterbodies and 29 of 866 zone-of-influence records lie in MWS that are not among the tehsil's 16 MWS. `mws_uid_list` is a pipe-separated string.
- Suggested fix: add an "inside tehsil" flag and return `mws_uid_list` as a list.

## Issues moved from the general log

These keep their original numbers and text; the query numbers refer to the general log. New evidence from 22 Nov 2026 is added at the end of each.

**CS-12. Waterbody list bloats the response, little usable content**
- Observed (call 2.1): `mws_intersect_swb` has 25 entries, all with empty `swbName`. Coordinates are rounded to two decimals (about 1 km), so most entries share one of a few points.
- Query 4 responses carry up to about 100 entries; the few names present are generic ("KERE", "POND", "HALLI").
- Suggested fix: return a count by default and the list on request; give coordinates to at least four decimals.
- See also WB-08: the waterbody routes return no coordinates at all.

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
- 22 Nov 2026: confirmed by the CoRE Stack team that `k`, `kr` and `krz` are nested (kharif; kharif and rabi; kharif, rabi and zaid), as read here.

**CS-44. Three undefined "total" water areas that disagree**
- Observed (call 11.1), 2_28284 in 2017: `kharif_area` 23.34, `total_area` 36.20, `metadata.total_swb_area` 85.58, all "ha".
- Over the tehsil, kharif is 41% to 93% of `total_area` depending on the year, and `total_area` never reaches `total_swb_area`.
- Likely meanings: `total_area` is anything detected as water at any time in the year, and `total_swb_area` is the mapped footprint of the waterbodies. Neither is stated.
- Impact: "share of tank area holding water" could be computed against either, with very different answers.
- Suggested fix: define both; rename `total_area` (for example `any_water_area`) and `total_swb_area` (for example `waterbody_footprint_area`).

**CS-48. Waterbody route returns 502 for Chintamani**
- Observed (call 13.1): `Merged dataset not available for given area.` The underlying layer exists and is complete on GeoServer (call 13.3), and `get_generated_layer_urls` lists it.
- A 502 is a gateway error code; the condition is "data not prepared", for which 404 or 409 would be clearer.
- `get_waterbody_data` (single waterbody) was not tried; it reads the same merged dataset.
- Impact: the only API route with per-waterbody seasonal water is unusable for this tehsil.
- Suggested fix: build the merged dataset for all active tehsils, or have `get_active_locations` say which routes work for each tehsil.
- 22 Nov 2026: still 502 with the same message for Chintamani. The route works for Kaviti, Gogunda and Morshi.

**CS-49. Waterbody layer: a third of features lie outside the tehsil; duplicate and empty attribute columns**
- Observed (call 13.3):
  - 1,055 of 3,263 waterbodies have their centre outside every Chintamani village polygon. Their `village_name` values belong to neighbouring tehsils and states (for example "t.sadum", 79 waterbodies). The layer covers whole micro-watersheds, which extend beyond the tehsil, but it is named and listed as the tehsil's.
  - `State Name`, `District Name`, `Block/Tehsil Name` and `Village Name` are null, while lower-case `village_name` and `covering_village_names` are filled. Two columns for the same thing, one empty.
  - About 60 census-style columns (`construction_cost`, `storage_capacity_water_body_original`, `no_people_benefited_by_water_body`, ...) are null on every feature checked.
  - `k_`, `kr_`, `krz_` are percentages of `area_ored`, and `area_YY-YY` is hectares; none of this is documented. `area_ored` is unexplained (it appears to be the union of water extent over all years).
- Impact: summing the layer gives totals for an area about one and a half times the tehsil; a user filtering by the null admin columns gets nothing.
- Suggested fix: add a flag or filter for "inside tehsil"; drop empty columns; document the seasonal fields.
- 22 Nov 2026: the layer is listed by `get_generated_layer_urls` as `swb:surface_waterbodies_{district}_{tehsil}`, next to `swb:waterbodies_zoi_{district}_{tehsil}` and `crop_intensity:{district}_{tehsil}_intensity_ZOI`. See also WB-09.

**CS-65. `surfacewaterbodies_annual` omits MWS with no water body and can exceed MWS area**
MWS with no water body are absent rather than zero. The pipeline imputes zero. In a few MWS, `total_area` is up to 5.9× the MWS area. This suggests water-body polygons are not clipped to the MWS. Separately, `kharif_area` and `rabi_area` are nearly equal in many rows, which makes it unclear what `rabi_area` measures.
**Fix:** return zero rows, clip to the MWS, and document the seasonal columns.
