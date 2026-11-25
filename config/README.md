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
