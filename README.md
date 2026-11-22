# SEFT: social-ecological systems of micro-watersheds from CoRE Stack data

This repository turns CoRE Stack micro-watershed (MWS) and village data into:

1. **Indicators** per MWS: means, trends, variability and co-incident changes.
2. **Context classes**: rainfall regime, aquifer, terrain, groundwater category and canal access.
3. **A mixture of system archetypes** per MWS: rainfed dryland, rainfed sub-humid, groundwater-, canal- and tank-irrigated, forest fringe, tree crops, pastoral, peri-urban.
4. **Observed stresses and opportunities** per production system (agriculture, livestock and commons, forest, peri-urban, and the cross-cutting socio-economic system of households). Each observed stress is made of causal pathways: rules written over a library of system, stress and context signals, nested where they share a mechanism (`groundwater.over_extraction`), with an intensity from 0 to 100, a plain-language public note, and re-assessment with community answers.
5. **Matching central and state schemes**, and village clusters (each village goes to the MWS it overlaps most).

All logic and metadata sit in `knowledge/*.json`, so domain experts can review and edit them without touching code.
The repository ships with results for eight test districts, so the atlas opens straight away.

## Quick start: open the atlas

Open `web/index.html` in a browser. It works directly from disk, or you can serve it with
`python -m http.server -d web 8000` and open http://localhost:8000.

The atlas covers Pune, Amaravati, Ananthapur, Srikakulam, Godda, Koraput, Udaipur and Ballia:
73 tehsils and 4,598 MWS. The same results are in `out/csv/` as tables.

## Running for new locations

```bash
python -m pip install -r requirements.txt
export CORE_STACK_API_KEY=...            # your CoRE Stack key; never commit it
export CORE_STACK_API_VERSION=v2          # optional; v2 is the default and serves every dataset

# 1. say where (names exactly as the CoRE Stack API lists them)
python -m seft.cli add --state Maharashtra --district Yavatmal --tehsils "Darwha,Pusad,Arni,Digras"

# 2. download, check, analyse
python -m seft.cli fetch                 # API data + GeoServer geometry; cached datasets are skipped
python -m seft.cli audit                 # lists anything missing or incomplete
python -m seft.cli run                   # writes out/csv, out/web and web/data (the atlas data)
# or all three at once:  python -m seft.cli all
```

On Windows, use `python -m pip` rather than `pip`. Windows Application Control often blocks `.venv\Scripts\pip.exe`. After `py -m venv .venv` and `.\.venv\Scripts\Activate.ps1`, run `python -m pip install -r requirements.txt`. If `python` is not on PATH in that shell, use `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`. Set the API key in PowerShell with `$env:CORE_STACK_API_KEY = "..."` and, if needed, `$env:CORE_STACK_API_VERSION = "v2"`. These last only for that session.

Open `web/index.html` again: new districts appear on the India map and in the district list.
No HTML changes are needed.

Which locations a run covers depends on how you add them:

* **One combined run (recommended).** Add the new districts to `config/locations.json` and run everything.
  Pooled percentile thresholds are then computed across all locations together. This needs the raw data
  of every district, so the first `fetch` also downloads the eight test districts: 73 tehsils × 18
  datasets, which takes roughly 20–30 minutes.
* **Only the new districts.** Keep them in their own file and merge them into the existing atlas:
  ```bash
  python -m seft.cli add --locations config/yavatmal.json --state Maharashtra --district Yavatmal --tehsils "..."
  python -m seft.cli all --locations config/yavatmal.json --merge
  ```
  `--merge` keeps the districts already in `web/data/`, and `mws_all.csv` and `villages_all.csv` are rebuilt to
  include every district. The new districts' percentile thresholds are pooled over the new run only.

### What `fetch` does

* **Geometry first.** For each tehsil it downloads the MWS polygons and village points from GeoServer
  (`crop_intensity:{district}_{tehsil}_intensity` and `panchayat_boundaries:{district}_{tehsil}`) into
  `data/geo/geometry_raw.json`. The MWS count is used to check that datasets are complete.
* **One request per tehsil.** It calls `/api/v2/get_tehsil_data/` once per tehsil, without a `data`
  filter, and splits the response into the datasets listed in `config/datasets.json`, stored in
  `data/raw/<state>/<district>/<tehsil>/<dataset>.json`. The filter is not used because it rejects
  `forest_fire`, `forest_fringes`, `tree_in_grassland` and `ndvi`, which the unfiltered response
  includes (CS-83). Failed requests are retried. The presigned S3 links in `green_credit` are stripped.
* **Full responses kept.** Each tehsil's complete response is also saved, gzipped, as
  `data/raw/<state>/<district>/<tehsil>/_response.json.gz` (presigned links stripped). When a dataset is
  added to `config/datasets.json` later, `fetch` extracts it from that file without calling the API;
  `--force` downloads the response again.
* **Back-fill.** A dataset that comes back cut off, or with fewer MWS than the geometry, is marked
  `complete: false`. Incomplete `lulc_vector` and `croppingintensity_annual` are back-filled from the
  GeoServer layers behind the API, which match it exactly (CS-59). Set `SEFT_NO_GEOSERVER=1` to skip
  the back-fill when GeoServer cannot be reached.
* **Audit.** `audit` lists anything still missing or incomplete. `fetch --force` re-downloads, and
  `fetch --only lulc_vector` fetches a single dataset.

The default endpoints can be changed with the environment variables `CORE_STACK_API_BASE` and
`CORE_STACK_GEOSERVER`.

### Community answers

The atlas lets a field team answer the questions in `knowledge/questions.json` for an MWS and re-assess the
stresses. The answers can be saved as `community_answers.json`. Running
`python -m seft.cli run --answers community_answers.json` gives the same results in the tables.

## Checking the rules against ground truth

```bash
python -m seft.cli groundtruth --truth path/to/final_ground_truth.json
```

The input lists micro-watersheds known to have a pathway (`positive`) or not (`negative`), by
`block_name` (tehsil) and `uid`. The tool:

1. **Resolves locations.** Each block name is matched against `get_active_locations`, cached in
   `config/groundtruth/active_locations.json` (`--refresh-locations` downloads it again). A name found in
   more than one district is settled by which tehsil's data contain the listed uid. The result is in
   `config/groundtruth/locations.json` and `resolution.json`.
2. **Fetches the data.** It uses the normal fetcher, so the data are cached once under `data/raw/` and
   reused. `--force` refreshes them, and `--no-fetch` uses only the cache.
3. **Scores both rule sets.**
   - **Atlas rules** use the atlas's own pooled thresholds from `web/data/index.json` (`--pools run`
     pools over the ground-truth MWS instead).
   - **Sheet rules** are the Signal_Verification sheet's patterns, in `knowledge/sheet_rules.json`. That
     file is built by `tools/build_sheet_rules.py` and evaluated by `seft/sheet.py`. Their signals are
     0/1, `or` is a sum and `and` a product.
4. **Reports.** It writes confusion matrices to `out/groundtruth/report.md` and `confusion.csv`, and
   one row per label with the rule results and signals to `detail.csv`.

`config/groundtruth/pathways.json` maps each ground-truth pathway to atlas rules and a sheet pattern.

The report also includes:
- **Metrics:** balanced accuracy and F1 for every row.
- **Firing rates:** the share of the atlas sample MWS where each rule fires. Computing this needs one run of the whole sample, which is then cached per knowledge version; `--no-sample` skips it.
- **Combination tables:** atlas OR sheet, atlas AND sheet, and the sheet with each atlas sub-pathway, plus a confidence-tier table showing how often the label is positive when both, one or neither rule set fires.
- **Changes made:** the list in `config/groundtruth/changes.md`.
- **Pathway by pathway:** the original rule, the changes made and further options for each pathway, from `config/groundtruth/suggestions.md`. `python tools/groundtruth_whatif.py` scores candidate rule changes without applying them.

## Layout

```
config/
  locations.json      districts and tehsils to analyse (edit, or use `seft.cli add`)
  datasets.json       get_tehsil_data datasets and whether they are MWS- or village-level
  counts.json         MWS and village counts of the test tehsils (reference)
knowledge/            all logic and metadata, editable by experts (see knowledge/README.md)
  variables.json      indicator definitions (expressions over the datasets)
  contexts.json       context classes and district rainfall normals
  archetypes.json     system archetypes, weights, share rules, confidence rubric
  signals.json        signal library: system, stress and context signals with thresholds and grades
  taxonomy.json       production systems → observed stresses → causal-pathway groups
  causal_graph.json   nodes, signed edges, and the causal-pathway rules (signals by role, trigger, intensity, public note)
  schemes.json        central and state schemes and the signals they respond to
  questions.json      community MCQs: likelihood ratios for stresses, weight overrides for systems
  sources.json        bibliography referenced by id from every other file
seft/                 Python package
  cli.py              command line (add, fetch, audit, validate, run, all)
  fetch.py            API and GeoServer download, completeness checks, back-fill
  ingest.py           parses API responses (including cut-off ones)
  load.py             reads the cache, merges MWS shared across tehsils, apportions villages
  expr.py             safe expression language used by every knowledge file
  indicators.py, context.py, archetypes.py, signals.py, stresses.py, assess.py, schemes.py
  rescore.py          re-scores the atlas from the indicators stored in web/data (no raw data needed)
  pipeline.py         end-to-end analysis
  export.py           CSV tables and atlas bundles
  webdata.py          copies the bundles to web/data (.json and .js), combines the CSV tables
  validate.py         checks every expression and id reference in knowledge/
  audit.py            coverage report;  backfill.py: the GeoServer back-fill used for the test districts
data/
  geo/                MWS, village and tehsil geometry, India state outlines, GeoServer back-fill of the test districts
  raw/                downloaded API data (created by fetch; not shipped)
out/csv/              result tables (mws_<district>.csv, villages_<district>.csv, *_all.csv)
web/
  index.html          the atlas
  data/               atlas data: index + one bundle per district, as .json and .js, and the CSV tables
docs/                 CoRE Stack API issues log (CS-01 to CS-73)
tests/test_offline.py runs add -> fetch -> audit -> validate -> run against a mock CoRE Stack server
```

## Data access

`fetch` calls the CoRE Stack API directly (`https://geoserver.core-stack.org/api/<version>/get_tehsil_data/`)
with the key in the `X-API-Key` header, read from `CORE_STACK_API_KEY`. Both versions work; the loader reads
either response format (`seft/schema.py`). Direct calls return complete data. The MCP server cuts responses at
180,000 characters (CS-84), so use it only for small checks; `python -m seft.ingest` can parse saved MCP
responses if needed. Without network access, `python -m seft.rescore` re-scores the shipped atlas.

## Editing the knowledge

See `knowledge/README.md`. Run `python -m seft.cli validate` after every edit, then `run`.
Without the raw API cache, `python -m seft.rescore` re-scores the shipped atlas from its stored indicators
(refreshed 16 Nov 2026). A variable added after that stays missing until the locations are fetched again.

## Testing

`python tests/test_offline.py` starts a mock API and GeoServer serving a synthetic district. It runs the
full new-location workflow on a temporary copy of the repository, including a cut-off `lulc_vector`
response that must be back-filled, and checks that the district is merged into the atlas. No key or
network is needed.

## Method decisions and data caveats

The atlas Methodology tab and `docs/core_stack_api_issues.md` (CS-01 to CS-73) give the full account.
The decisions that most affect results are:

* **Watersheds on tehsil borders.** 972 of the 4,598 test MWS straddle tehsils, and the API returns each copy,
  sometimes with different values (CS-63). Each is counted once, using the copy from its home tehsil
  (the tehsil holding most of its village area).
* **Irrigation.** Non-kharif greenness overstates irrigation in sub-humid districts (CS-70). Groundwater
  irrigation is therefore scaled by the block stage of groundwater extraction, and the remainder counts
  as rainfed second cropping on residual moisture.
* **Rainfall.** CoRE precipitation is smoothed and departs from district normals (CS-68). Rainfall regimes
  use it rescaled to the normals in `knowledge/contexts.json`. Pune is left unscaled.
* **Groundwater change.** Modelled groundwater change (`delta_g`, `welldepth`) is biased strongly negative
  (CS-67). Absolute CGWB water-level thresholds are therefore switched off (`use_absolute: false`) and
  pooled percentiles are used. The block stage of extraction keeps its published 70/90/100% cut-offs.
* **Literacy.** CoRE literacy divides by total population including children aged 0–6 (CS-69), so the
  literacy threshold is lowered to match.
* **System shares.** The shares partition the MWS area. Raw shares below 100% leave the remainder as
  unclassified land in "other"; this happens in 18% of MWS, mostly in hilly tehsils (CS-73). Raw shares
  above 100% are scaled down. Systems at 1% or more are shown. A system is "present" at its own
  threshold (15%; 10% for tank and pastoral; 8% for peri-urban). Rule confidence never scales a share.
* **Community re-assessment.** The data result sets a prior that rises with intensity: triggered 0.60
  to 0.90, not triggered 0.15 to 0.35 (partial evidence), missing data 0.40. Rule confidence pulls the prior toward 0.5
  (high ×1, medium ×0.8, low ×0.6). Answers multiply the odds by likelihood ratios, and a stress counts
  as present at 0.5. The likelihood ratios are expert judgement and should be calibrated against field
  answers.
* **Other API caveats.** `green_credit` rows carry presigned S3 URLs, which are stripped on fetch (CS-62).
  Some responses are truncated; `audit` flags them (CS-59).

The JavaScript in `web/index.html` between `/*CORE-START*/` and `/*CORE-END*/` mirrors `seft/expr.py`,
`archetypes.py`, `signals.py`/`stresses.py` (applicability and pathways), `assess.py` and `schemes.py`. Keep them in step when changing that logic.
