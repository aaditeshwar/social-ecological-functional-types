# Waterbody patterns against the Water Body Census

6134 in-scope waterbodies have census fields matched by CoRE Stack. The match is by proximity and by capacity against area, so it may be wrong for some waterbodies (WB-07 in docs/core_stack_waterbody_api_issues.md), and the census describes 2017-18: it can check the state at the start of the series and the uses, not changes after 2019. Census fields are not inputs to the atlas.

Cells give the share of waterbodies where the rule fires, among those it applies to (n in brackets).

## How full it gets (`filled_up_storage_name`)

| Census | n | Median kharif fill | Inflow shortfall |
|---|---|---|---|
| Full | 1122 | 40% | 6% (821) |
| Upto 3/4 | 1632 | 41% | 11% (1119) |
| Upto 1/2 | 1151 | 33% | 14% (751) |
| Upto 1/4 | 354 | 31% | 20% (200) |
| Nil/Negligible filled up | 176 | 42% | 9% (122) |

## How often it fills (`filled_up_storage_space_name`)

| Census | n | Inflow shortfall | Fails in drought years |
|---|---|---|---|
| Filled up every year | 1801 | 8% (1269) | 25% (334) |
| Usually filled up | 1592 | 12% (1061) | 12% (642) |
| Rarely filled up | 893 | 15% (579) | 9% (358) |
| Never filled up | 149 | 6% (104) | 19% (68) |

## In use (`ref_water_body_in_use_id_name`)

| Census | n | Shrinking or silting | Inflow shortfall | Stopped holding water |
|---|---|---|---|---|
| in use | 5471 | 20% (2783) | 9% (3833) | 9% (3056) |
| not in use | 663 | 28% (284) | 15% (437) | 2% (339) |

## Encroached (`ref_selection_id_water_body_encroached_name`)

| Census | n | Shrinking or silting |
|---|---|---|
| encroached | 87 | 32% (44) |
| not encroached | 6047 | 21% (3023) |

## Under repair (`ref_water_body_under_repair_renovation_restoration_id_name`)

| Census | n | Stopped holding water |
|---|---|---|
| under repair | 137 | 19% (90) |
| not under repair | 5997 | 8% (3305) |

## Present storage against original (`storage present / original`)

| Census | n | Inflow shortfall | Shrinking or silting |
|---|---|---|---|
| below 80% | 2299 | 13% (1543) | 21% (912) |
| 80% or more | 2002 | 7% (1388) | 16% (1021) |

## Water user association (`ref_selection_id_wua_exists_name`)

| Census | n | Water not reaching fields |
|---|---|---|
| Yes | 286 | 19% (107) |
| No | 3067 | 40% (1026) |
| Not Known | 1966 | 37% (639) |

## Used for pisciculture (`use: Pisciculture`)

| Census | n | Fishery candidate |
|---|---|---|
| pisciculture | 2227 | 78% (286) |
| other uses | 3907 | 73% (368) |

## Census uses against atlas roles

Mean role weight where the census lists the use, against where it does not.

| Use | n | Irrigation | Kharif drought protection | Fishery | Livestock water | Recharge and domestic water |
|---|---|---|---|---|---|---|
| Irrigation | 2316 | 0.64 vs 0.47 | 0.51 vs 0.47 | 0.42 vs 0.37 | 0.01 vs 0.15 | 0.27 vs 0.38 |
| Pisciculture | 2227 | 0.69 vs 0.44 | 0.39 vs 0.54 | 0.51 vs 0.33 | 0.01 vs 0.16 | 0.31 vs 0.35 |
| Ground water recharge | 3627 | 0.47 vs 0.62 | 0.51 vs 0.45 | 0.36 vs 0.45 | 0.12 vs 0.07 | 0.36 vs 0.31 |
| Domestic/Drinking | 499 | 0.58 vs 0.53 | 0.48 vs 0.48 | 0.39 vs 0.39 | 0.05 vs 0.11 | 0.33 vs 0.34 |

## Census type against atlas type

| Census type | river_reach | canal_fed | onstream_tank | small_onstream_pond | headwater_pond | village_pond | farm_pond |
|---|---|---|---|---|---|---|---|
| Ponds (2836) | 3% | 8% | 3% | 3% | 9% | 19% | 55% |
| Water consv schemes/percolation tanks/check-dams (1672) | 12% | 5% | 16% | 13% | 29% | 5% | 19% |
| Tank (1554) | 5% | 11% | 12% | 4% | 24% | 14% | 30% |
| Others (27) | 11% | 11% | 7% | 11% | 22% | 0% | 37% |
| Lakes (24) | 4% | 4% | 0% | 0% | 12% | 17% | 62% |
| Reservoirs (21) | 14% | 5% | 10% | 0% | 14% | 38% | 19% |

Tuning decisions taken from this check are listed in docs/waterbody_census_comparison.md.
