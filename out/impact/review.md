# Impact review

924 records; 488 assessable single or first windows; 84 of them carry quality flags and are left out of averages.

| Verdict | n |
| --- | --- |
| not_assessable | 431 |
| no_change | 378 |
| inconclusive | 57 |
| likely_gain | 38 |
| likely_loss | 20 |

## Not assessable

| Reason | n |
| --- | --- |
| no year of water data after the work yet | 252 |
| its type is out of the atlas scope | 176 |
| only 2 similar untreated waterbodies within 20 km (at least 5 needed) | 1 |
| only 3 similar untreated waterbodies within 20 km (at least 5 needed) | 1 |
| only 1 similar untreated waterbodies within 20 km (at least 5 needed) | 1 |

## Estimators (weeks of water, unflagged records)

| Estimator | Mean | Same sign as DiD |
| --- | --- | --- |
| did | +1.11 | — |
| did_rain | +0.88 | 85% |
| prepost_rain | -2.46 | 64% |
| counterfactual | +1.12 | 92% |

Placebo DiD: mean -0.01, spread 5.49 weeks over 713 placebo windows.

## By district

| Unit | n | Mean DiD (95% range) | Likely gain / loss | Reference mean |
| --- | --- | --- | --- | --- |
| Bid | 62 | +4.02 (+2.11, +5.99) | 6 / 2 | +0.57 |
| Chhatarpur | 52 | +2.51 (-0.31, +5.34) | 8 / 3 | -0.95 |
| Pune | 36 | -0.48 (-2.55, +1.64) | 2 / 1 | -0.28 |
| Nashik | 32 | +2.37 (+0.04, +4.68) | 1 / 2 | -0.07 |
| Yavatmal | 31 | -0.25 (-2.77, +2.44) | 1 / 0 | -0.99 |
| Aurangabad | 26 | -1.93 (-4.78, +0.91) | 2 / 2 | -0.43 |
| Chitrakoot | 25 | +1.58 (-2.45, +5.79) | 3 / 2 | -1.27 |
| Amaravati | 23 | -0.82 (-5.94, +3.88) | 0 / 1 | -0.40 |
| Washim | 22 | +0.05 (-1.43, +1.74) | 1 / 0 | +0.56 |
| Solapur | 20 | +5.11 (+1.69, +8.93) | 2 / 0 | +1.03 |
| Parbhani | 19 | -0.03 (-1.75, +1.76) | 1 / 0 | -0.13 |
| Sirohi | 13 | -2.24 (-10.46, +5.45) | 3 / 1 | -1.67 |
| Jalna | 11 | -2.95 (-8.23, +1.63) | 0 / 3 | -0.58 |
| Baran | 5 | +3.49 (-1.75, +7.95) | 0 / 0 | +0.05 |
| Hingoli | 5 | -8.75 (-22.27, +0.01) | 0 / 0 | +1.08 |
| Nanded | 5 | +3.93 (+1.24, +7.28) | 0 / 0 | -0.67 |
| Sangli | 5 | -0.46 (-3.10, +2.15) | 0 / 0 | -1.25 |
| Ahamadnagar | 4 | +1.76 (-1.02, +6.39) | 0 / 0 | +0.20 |
| Usmanabad | 3 | +0.81 (-0.24, +1.48) | 0 / 0 | +0.90 |
| Thane | 2 | +2.22 (+1.65, +2.79) | 0 / 0 | +0.45 |
| Jalgaon | 1 | +2.10 (+2.10, +2.10) | 0 / 0 | -0.50 |
| Gondia | 1 | -0.50 (-0.50, -0.50) | 0 / 0 | -0.03 |
| Satara | 1 | -0.74 (-0.74, -0.74) | 0 / 0 | -1.39 |

## By type

| Unit | n | Mean DiD (95% range) | Likely gain / loss | Reference mean |
| --- | --- | --- | --- | --- |
| onstream_tank | 165 | +0.93 (-0.05, +2.04) | 8 / 6 | +0.10 |
| headwater_pond | 162 | +1.29 (-0.04, +2.68) | 13 / 10 | -0.28 |
| village_pond | 45 | +1.37 (-2.28, +4.92) | 5 / 0 | -0.92 |
| river_reach | 11 | +1.49 (-4.80, +8.15) | 2 / 1 | -1.56 |
| farm_pond | 9 | +1.63 (-3.87, +7.05) | 2 / 0 | -1.09 |
| canal_fed | 7 | -1.47 (-5.98, +2.61) | 0 / 0 | -1.49 |
| small_onstream_pond | 5 | +0.69 (-3.49, +4.21) | 0 / 0 | +0.00 |

## By ctx_rainfall

| Unit | n | Mean DiD (95% range) | Likely gain / loss | Reference mean |
| --- | --- | --- | --- | --- |
| semi_arid | 307 | +1.52 (+0.55, +2.49) | 28 / 15 | -0.31 |
| dry_subhumid | 89 | -0.14 (-1.73, +1.19) | 2 / 2 | -0.19 |

## By ctx_aquifer

| Unit | n | Mean DiD (95% range) | Likely gain / loss | Reference mean |
| --- | --- | --- | --- | --- |
| hard_rock | 353 | +0.84 (-0.06, +1.67) | 25 / 16 | -0.18 |
| alluvium | 49 | +3.02 (-0.32, +5.98) | 5 / 1 | -0.92 |
| saline | 1 | +9.87 (+9.87, +9.87) | 0 / 0 | -0.39 |

## By dominant_system

| Unit | n | Mean DiD (95% range) | Likely gain / loss | Reference mean |
| --- | --- | --- | --- | --- |
| rainfed_dryland | 248 | +1.57 (+0.59, +2.54) | 19 / 9 | +0.00 |
| groundwater_irrigated | 60 | +0.08 (-2.36, +2.49) | 1 / 5 | -0.80 |
| forest_fringe | 44 | +0.13 (-2.67, +2.90) | 3 / 2 | -0.42 |
| canal_irrigated | 20 | +1.10 (-3.56, +5.70) | 3 / 1 | -0.89 |
| rainfed_rice_subhumid | 17 | -1.07 (-4.79, +2.77) | 1 / 0 | -1.05 |
| tree_crops | 10 | +2.23 (-3.22, +8.72) | 3 / 0 | -0.87 |
| pastoral | 4 | +4.53 (+0.65, +9.04) | 0 / 0 | +0.19 |
| tank_irrigated | 1 | +3.04 (+3.04, +3.04) | 0 / 0 | +0.78 |
