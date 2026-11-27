# Configuration

* `locations.json` — districts and tehsils of the watershed atlas:
  `{"note": "...", "roles": {...}, "districts": [{"state": "...", "district": "...", "tehsils": ["...", ...], "roles": ["pools"]}]}`.
  `roles` says what a district is for: `pools` (sample for the percentile pools), `groundtruth` (compared with
  labels), `coverage` (extra districts, scored with the published pools). Entries without roles count as `pools`.
  `add --role` sets them; `run --update-pools` recomputes the pools over the `pools` districts.
  Names must be spelt exactly as the CoRE Stack API lists them (`get_active_locations`), including
  hyphens (`Mulshi-Paud`). Add entries by hand or with `python -m seft.cli add`. You can keep several
  files, such as one per batch, and pass `--locations FILE` to any command.
* `datasets.json` — the `get_tehsil_data` datasets that `fetch` downloads. `level` is `mws` or `village`;
  MWS-level datasets are checked against the MWS count from GeoServer. `bytes_per_row` was used to size
  requests in the original session and is informational.
* `counts.json` — MWS and village-polygon counts of the test tehsils, for reference.
* `waterbody/locations.json` — the same for the waterbody atlas. `groundtruth` here is the Water Body Census
  comparison (`wb-census`); `pools` the sample for the waterbody pools (`wb-run --update-pools`).
* `groundtruth/locations.json` — the watershed ground-truth tehsils (role `groundtruth`), rebuilt by the
  `groundtruth` command from `final_ground_truth.json`; `add --role groundtruth` appends to it.
* `impact/locations.json` — districts of the waterbody-impact module, with roles `reference` (untreated
  waterbodies here form the published reference distributions), `test` (results reviewed for decisions; now
  Pune and Amaravati) and `coverage` (fetched for control pools or on demand). `impact-build-registry --role`
  sets the role of districts it adds; it also adds their tehsils to `waterbody/locations.json` as `coverage`.
* `impact/aliases.json` — district and tehsil names in registry layers that `get_active_locations` spells
  differently (`"Maharashtra/Beed": "Bid"`). Add an entry when `impact-build-registry` reports a name unresolved.

**Modules depend on each other's locations.** The waterbody atlas draws on the watershed atlas's MWS bundles and
context, and the impact module on the waterbody atlas. So adding locations to a module also adds them, as
coverage, to the modules it depends on (`seft.util.register_locations`; `MODULE_DEPENDS` in `seft/util.py`):

| Command | Writes | Also adds, as coverage, to |
| --- | --- | --- |
| `add` | `locations.json` | — |
| `wb-add` | `waterbody/locations.json` | `locations.json` |
| `impact-build-registry` | `impact/locations.json` (`--role`) | `waterbody/locations.json`, `locations.json` |

`wb-fetch`, `impact-link` and `impact-run` first sync their module's locations into its dependencies, so files
edited by hand catch up too. A new district in a dependency gets the role `coverage`. Tehsils added to an
existing pools or ground-truth district are listed under `coverage_tehsils`: they are fetched and scored, but
left out of the pools sample and the ground-truth comparison (`seft.util.with_role`, `role_tehsils`).
`wb-fetch` and `wb-run` end by listing waterbody districts that have no watershed bundle yet
(`web/data/d_<district>.json`), with the commands that build it (`fetch`, then `run --merge`).
Districts fetched on demand by core-seft are recorded in `<data_dir>/index.json`, one list for all modules.
