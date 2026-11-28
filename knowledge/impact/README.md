# Waterbody impact knowledge

Read by `seft/impact` (`impact-run`, `impact-farmpond`) and `core_seft` (`analyse("waterbody-impact", ...)`, and
the lined/unlined class in waterbody notes). The atlas's Impact assessment tab describes the methods in full.

* `settings.json` — intervention types; the outcomes (weeks of water W = 17.3 × (k + kr + krz) / 100, rabi
  retention kr / k and summer retention krz / k, the last two only when the kharif fill is 10% or more); matching
  (`radius_km` 20, `n_controls` 10, `min_controls` 5, exact on atlas type, own MWS excluded, 200 m around
  treated waterbodies excluded, the features); the four estimators (all reported, `did` the headline); placebo
  offsets; minimum pre years; the untreated reference (sample size, minimum before falling back to all types,
  seed); verdict percentiles (gain at 90, loss at 10, placebos within the reference's 25th–75th band); confidence
  flags (under 0.5 ha, river reach and canal-fed, one post year, unscreened controls); registry quality checks
  (link distance, implausible depth) and their labels; the units for averages.
* `farmponds.json` — new farm ponds (no registry): the types assessed (farm and headwater ponds), the years
  (2017-2024 series; new if first wet 2019-2023; effects up to 2022 identified, later ones early signs), the
  appearance rules (wet in 75% of years since; a qualifying pre year when half the established waterbodies of the
  MWS were wet and it was not a drought year), drought (4+ weeks), the four outcomes and the footprint and
  background corrections, the estimators (imputation headline with `min_cell`, same-district DiD with `min_n`,
  background change, placebo), the lined/unlined thresholds, verdicts, averages, the heterogeneity forest and the
  effectiveness measure for older structures. Every `about` is shown on the Impact assessment tab.
  Also: `intervention.types` (farm and headwater ponds, and as `exploratory_types` small on-stream ponds, on-stream
  tanks, village ponds and canal-fed ponds), `not_assessed` (river reaches, with the reason shown), `lining.types`
  (the lined/unlined split, farm ponds only), `effectiveness.min_group` (the percentile of an older structure among
  its type in its district) and `heterogeneity.ship_trees` (trees of the prediction model shipped with core_seft).
* `references.json` — the references cited (id, short, citation, url to a public copy where one exists, doi,
  used_for); `impact-validate` checks that every cited id exists.
* `notes.json` — public notes. For a waterbody (`waterbody`) and for a unit (`unit`): the first `main` rule whose
  `when` holds gives the main sentence, every `add` rule whose `when` holds appends one. Placeholders are listed
  in `seft/impact/notes.py`. Expressions use the syntax of the other knowledge files.
  `panel` holds the fixed text around the notes in the atlas panels (headings, table labels, the estimation
  explanation, chart legend). It is copied into `web/data/waterbody/impact.json` by `impact-run` and filled by the
  page; each entry's placeholders are declared in `panel._placeholders`, and `impact-validate` checks that every
  key the page uses exists. Changing any of this text needs `impact-run --finalize-only` (or a full run) to reach
  the atlas. New farm ponds: `fp_waterbody` (one pond: verdict, class, rabi/summer cropping, drought years,
  early years, the district's average), `fp_unit` (district, tehsil, MWS), `fp_old` (older structures, with its position in its district), `fp_none` (why a waterbody has no result) and
  `fp_panel` (fixed text, filled by `fpT` in the page); their placeholders are built in
  `seft/impact/farmpond.py` (`wb_env`, `unit_env`, `old_env`). They reach the atlas with `impact-farmpond`.

Size floor and scope follow the waterbody atlas (`knowledge/waterbody/types.json`: 0.05 ha; reservoirs, large
rivers and unclassified waterbodies out of scope).

Registry format (`data/registries/<id>.json`): `{"registry": {id, name, source, version, intervention_types,
year_convention, layers}, "interventions": [{id, type, year, volume_m3, point, desilting_point, waterbody: {wb_id,
fragment_id, state, district, tehsil, type, area_ha, match: {method, distance_m}}, location: {state, district,
tehsil, status}, names, source: {layer, record, uid, mws_uid, also_in}, implementer, quality_flags}]}`.
Several records may name the same waterbody and year (modules of about 10,000 m³); they are summed.
