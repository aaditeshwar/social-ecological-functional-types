# Configuration

* `locations.json` — districts and tehsils to analyse:
  `{"districts": [{"state": "...", "district": "...", "tehsils": ["...", ...]}]}`.
  Names must be spelt exactly as the CoRE Stack API lists them (`get_active_locations`), including
  hyphens (`Mulshi-Paud`). Add entries by hand or with `python -m seft.cli add`. You can keep several
  files, such as one per batch, and pass `--locations FILE` to any command.
* `datasets.json` — the `get_tehsil_data` datasets that `fetch` downloads. `level` is `mws` or `village`;
  MWS-level datasets are checked against the MWS count from GeoServer. `bytes_per_row` was used to size
  requests in the original session and is informational.
* `counts.json` — MWS and village-polygon counts of the test tehsils, for reference.
