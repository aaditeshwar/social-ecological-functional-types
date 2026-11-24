# Knowledge files

These nine JSON files hold every rule, threshold, weight, scheme and question that the pipeline uses.
None of them contains code. After editing, run:

```bash
python -m seft.cli validate     # every expression parses, every id resolves
python -m seft.cli run          # recompute tables and atlas (add --merge if you only fetched some districts)
```

The atlas shows these files in its tabs: Knowledge graph, System archetypes, Stress rules, Community
questions, Schemes and Methodology. Change a file, run, and reload the page to see the effect.

## Expressions

Formulas and conditions are short Python-like expressions, evaluated safely by `seft/expr.py`:

* **Arithmetic and logic:** `+ - * /`, comparisons, `and / or / not`, `x if cond else y`, `in [..]`.
* **Dataset columns, through an alias:** for example `lulc.tree_forest_area` or `hydro.delta_g`. The aliases are:

  | Alias | Dataset |
  |---|---|
  | `lulc` | `lulc_vector` |
  | `ci` | `croppingintensity_annual` |
  | `drought` | `croppingdrought_kharif` |
  | `hydro` | `hydrological_annual` |
  | `swb` | `surfacewaterbodies_annual` |
  | `aquifer` | `aquifer_vector` |
  | `terrain` | `terrain` |
  | `soge` | `soge_vector` |
  | `rest` | `restoration_vector` |
  | `degr` | `change_detection_degradation` |
  | `tcd` | `change_detection_tree_cover_decrease` |
  | `tci` | `change_detection_tree_cover_increase` |
  | `urb` | `change_detection_urbanization` |
  | `canal` | `canal` (`n`, `projects`) |
  | `gc` | `green_credit` (`n`) |
  | `vill` | village population and livestock, apportioned by area |

  Annual columns are series over 2017–2024.
* **Other ids:** earlier variable ids from `variables.json`, plus `area` (MWS area, ha).
* **Context classes:** `ctx.<dimension>`, for example `ctx.aquifer == 'hard_rock'`.
* **System shares:** `share_<archetype>`, available in stress rules and scheme conditions.
* **Functions:**
  * on series: `mean`, `median`, `sum`, `min`, `max`, `first`, `last`, `range`, `std`, `cv`, `slope` (Theil–Sen per year), `mk_p` (Mann–Kendall p), `early(x,k)`, `late(x,k)`, `frac(cond)` (share of years true), `count(cond)`, `runs(cond)`, `cumsum`;
  * general: `div(a,b)` (safe division), `nz(x,default)`, `ramp(x,lo,hi)` (0→1 between lo and hi), `clip`, `abs`, `known`, `isnan`.

Missing data is treated as unknown. An `or` can still be true if another part is true; an `and` cannot.

## The files

| File | What to edit | Notes |
|---|---|---|
| `variables.json` | Indicator definitions: `id`, `expr`, `unit`, `label`, `group`. | `min_coverage` blanks village-based values when villages with data cover less than 20% of the MWS. `series: true` marks helper series that are not exported. |
| `contexts.json` | Context dimensions and their classes (first matching class wins), and `rainfall_normals` per district. | Add a district's normal (mm) when you add a district. Without one, CoRE precipitation is used unscaled. |
| `archetypes.json` | `helpers` (weights, evaluated in order), `archetypes` (share rule, `present_at`, colour, confidence, explanation), `normalisation`, `confidence_rubric`. | Shares are fractions of MWS area. The pipeline closes them to 100% (see `normalisation`). |
| `signals.json` | The signal library: `kind` system / stress / context; `expr` (yes/no) or `var`, `direction`, `thresholds`, `percentile_fallback`. | Threshold signals grade 0, then 0.5 at the threshold to 1 at the severe threshold; on at 0.5. |
| `taxonomy.json` | `production_systems` (archetypes, presence `signal`, `observed_stresses` with `pathways`) and `groups` (rules sharing a mechanism). | An observed stress is shown where its production system is present, flagged when any of its rules of the same type is, and takes the highest intensity. A rule may sit under several production systems (floods). |
| `causal_graph.json` | `nodes`, `edges` (sign, mechanism, confidence, `condition`, sources), `stresses` (the finer rules). | Each rule has id `<group>.<rule>` (or a plain id), `group`, `sheet_pathway`, `signals` by role, `systems`, `trigger`, `intensity`, `severe_at`, `confidence`, `rationale`, `interpretation`, `public_note`. |
| `schemes.json` | Schemes: `level`, `state`, `addresses` (stress ids), `archetypes`, optional `condition`, `caution`, `status`. | A scheme matches when it addresses a stress that is present, fits the state and condition, and, if it lists archetypes, one of them holds at least 15% of the MWS. |
| `questions.json` | `system_questions` and `stress_questions`, and `assessment` (priors, confidence shrink, bands). | Each option has likelihood ratios for stresses (`lr`), and optionally `set` (override a weight) or `shift` (move share between archetypes). |
| `interventions.json` | Supply- and demand-side interventions, shared with the waterbody atlas: `side`, `category`, `what`, `where`, `site_spec` (ridge-to-valley placement from the CoRE Stack toolkit paper), `site_rules` (accepted / partially accepted / not accepted slope, stream order, catchment, distance to drainage and land use from the structure-suitability spreadsheet), `landscape`, `archetypes`, `suits` / `avoid` (landscape fit test), `caution`, `addresses` (stress ids), `addresses_wb` and `wb_types` (waterbody rules and types), `schemes`, `practice`, `sources`. | For each MWS, interventions that respond to a present stress are listed as suited (`suits` holds), not suited (`avoid` holds) or possible. Expressions read variables, `share_<archetype>` and the context classes as `terrain`, `aquifer`, `rainfall`, `gw_category`, `canal`, `cropping`. |
| `interventions.json` → `fit.community_vars` | Variables only a community answer supplies (now `wl_post_monsoon`, depth to water after the monsoon, from the landscape question `ls_wl_post`). Unknown by default, so they change no verdict until answered. | `site_rules` hold only site layers (slope, stream order, catchment, distance to drainage, land use, soil); rainfall, aquifer, groundwater stage and depth to water belong in `suits` / `avoid`. |
| `commons_connect.json` | Built by `python -m seft.cli cc-build --forms <folder>` from the Commons Connect ODK templates; edit the annotations in `seft/commons_connect.py` and rebuild. `forms` (section landscape / resource_mapping / planning, questions with `role`, `atlas_match`, `must_ask`, `prefill`, `routes`, `work_map`), `priority` (weights and bands of the must-ask score). | `must_ask.rules` are expressions over the watershed variables, `share_<archetype>`, context classes, `ps_<production system>`, `p_` / `pos_` / `urg_<rule>` (dots as `__`) and `ask_<atlas question>`; in the waterbody form also `wtype`, `wp_` / `wpos_<rule>` and `wask_<question>`. |
| `sources.json` | Bibliography: `id`, `citation`, `url`, `used_for`. | Every `sources` list in the other files refers to these ids. |

## Signals and rules

```json
{"id": "s_soge_stage", "kind": "stress", "var": "soge_stage", "direction": "high",
 "thresholds": [{"when": "True", "value": 70, "severe": 100, "sources": ["cgwb_gec2015"]}],
 "use_absolute": true, "percentile_fallback": {"pct": 75, "severe_pct": 90}}
```

* **Choosing the threshold:** the first entry in `thresholds` whose `when` holds for the MWS is used.
  Put context-specific entries first and a `"True"` entry last.
* **Pooled percentiles:** with `use_absolute: false`, or when no entry matches, the threshold is the
  pooled percentile over all MWS in the run. Use this for biased model outputs.
* **Yes/no signals:** a signal with an `expr` instead of a `var` grades 0 or 1. System signals read
  `share_<system>`; context signals read `ctx.<dimension>` or indicators.
* **Rules:** `systems` (over system signals) says where a rule is checked; `trigger` combines signal
  booleans with `and` / `or` (`<id>_g` is a grade; `ntrue`, `nknown` count signals); `intensity` is an
  expression over grades, times 100. In the intensity an unknown stress signal is skipped by
  `max` / `min` / `avg`, and an unknown context signal counts as 0. List every signal a rule uses in its
  `signals` roles (validate checks this).
* **Public note:** plain words for communities, naming the signal ids in brackets, where the rule is checked,
  what makes it more intense and what to verify.

## Adding things

* **A new stress:** add any new signals to `signals.json`, a rule to `stresses` with a public note (id
  `<group>.<rule>` if it joins a group, listed in that group's `children`), place it under an observed stress in
  `taxonomy.json` (by group or rule id), add graph edges if the
  mechanism is new, list it in the `key_stresses` of the relevant archetypes, add scheme `addresses`, and add
  questions for it.
* **A new intervention:** add an entry to `interventions.json` with the stresses (`addresses`) and waterbody rules
  (`addresses_wb`) it responds to and a fit test; `validate` checks every id, scheme and source and that every stress
  and waterbody rule has at least one intervention. Text-only edits reach the page with
  `python -m seft.cli refresh-knowledge`; the MWS tables get the `interventions_suited` / `interventions_possible`
  columns on the next `run` (and the waterbody tables on the next `wb-run`).
* **A new scheme:** add an entry to `schemes.json`. For a state scheme, `state` must match the state name in
  `config/locations.json`.
* **A new archetype:** add a share rule and any helper weights. Make sure the shares still split the MWS
  area without double counting, and give it a colour and a `present_at` threshold.
* **A new indicator from a dataset not yet fetched:** add the dataset to `config/datasets.json`, the alias to
  `ALIASES` (or `FLAT_MWS` / `FLAT_VILLAGE` for flat tables) in `seft/load.py`, then define the variable.
