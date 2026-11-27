# Waterbody impact knowledge

Read by `seft/impact` (`impact-run`) and `core_seft` (`analyse("waterbody-impact", ...)`).

* `settings.json` — intervention types; the outcomes (weeks of water W = 17.3 × (k + kr + krz) / 100, rabi
  retention kr / k and summer retention krz / k, the last two only when the kharif fill is 10% or more); matching
  (`radius_km` 20, `n_controls` 10, `min_controls` 5, exact on atlas type, own MWS excluded, 200 m around
  treated waterbodies excluded, the features); the four estimators (all reported, `did` the headline); placebo
  offsets; minimum pre years; the untreated reference (sample size, minimum before falling back to all types,
  seed); verdict percentiles (gain at 90, loss at 10, placebos within the reference's 25th–75th band); confidence
  flags (under 0.5 ha, river reach and canal-fed, one post year, unscreened controls); registry quality checks
  (link distance, implausible depth) and their labels; the units for averages.
* `notes.json` — public notes. For a waterbody (`waterbody`) and for a unit (`unit`): the first `main` rule whose
  `when` holds gives the main sentence, every `add` rule whose `when` holds appends one. Placeholders are listed
  in `seft/impact/notes.py`. Expressions use the syntax of the other knowledge files.

Size floor and scope follow the waterbody atlas (`knowledge/waterbody/types.json`: 0.05 ha; reservoirs, large
rivers and unclassified waterbodies out of scope).

Registry format (`data/registries/<id>.json`): `{"registry": {id, name, source, version, intervention_types,
year_convention, layers}, "interventions": [{id, type, year, volume_m3, point, desilting_point, waterbody: {wb_id,
fragment_id, state, district, tehsil, type, area_ha, match: {method, distance_m}}, location: {state, district,
tehsil, status}, names, source: {layer, record, uid, mws_uid, also_in}, implementer, quality_flags}]}`.
Several records may name the same waterbody and year (modules of about 10,000 m³); they are summed.
