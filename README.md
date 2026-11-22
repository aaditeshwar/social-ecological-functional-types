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

The same flow, with the files each step writes:

```mermaid
flowchart LR
  add["add"] --> loc["config/locations.json"]
  loc --> fetch["fetch"]
  fetch --> raw["data/raw/ + data/geo/geometry_raw.json"]
  loc --> run["run"]
  raw --> run
  kn["knowledge/*.json"] --> run
  run --> csv["out/csv/"]
  run --> webd["web/data/"]
  webd --> atlas["web/index.html"]
  kn --> gt["groundtruth"]
  raw --> gt
  webd --> gt
  gt --> gto["out/groundtruth/"]
```

## What the commands do

Every command is `python -m seft.cli <name>`. `--locations FILE` (default `config/locations.json`) is the worklist of districts and tehsils. `--knowledge` defaults to `knowledge/`, `--out` to `out/`.

### `add`

Creates or updates a locations file so later commands know where to work.

* **Reads:** `--locations` if it already exists (`{"districts": [...]}`).
* **Writes:** the same file. Adds a district if it is new, otherwise appends tehsils that are not already listed. Names must match the CoRE Stack API (`get_active_locations`), including hyphens (`Mulshi-Paud`).
* **Used by:** `fetch`, `audit`, `run` and `all` as the list of places to download and analyse. The atlas district list is not updated until `run` writes `web/data/index.json`.

```bash
python -m seft.cli add --state Maharashtra --district Yavatmal --tehsils "Darwha,Pusad,Arni,Digras"
# or a separate file:  --locations config/yavatmal.json
```

### `fetch`

Downloads CoRE Stack data for every tehsil in the locations file. Cached complete files are skipped unless `--force`. `--only lulc_vector` fetches a single dataset.

* **Reads:** `config/locations.json` (or `--locations`), `config/datasets.json` (which datasets, MWS vs village), any existing `data/geo/geometry_raw.json` and `data/raw/...` caches, and `data/geo/geoserver_backfill.json` (stored GeoServer rows for the test districts).
* **Writes:**
  * `data/geo/geometry_raw.json` — MWS polygons, village points and tehsil outlines, keyed `district_slug/tehsil_slug`. The MWS count is the expected row count for MWS-level datasets. `run` later copies these polygons into the atlas bundles.
  * `data/raw/<state>/<district>/<tehsil>/_response.json.gz` — the tehsil's full API response (presigned S3 links stripped). A dataset added to `config/datasets.json` later is extracted from this file with no new API call.
  * `data/raw/<state>/<district>/<tehsil>/<dataset>.json` — one cache file per dataset, with `rows`, `complete`, `n_rows` and `expected_mws`. These are the only raw inputs `run` needs.
* **Used by:** `load.py` during `run` and `groundtruth`; `audit` to list gaps. `data/raw/` is gitignored and not shipped; without it, use `python -m seft.rescore` on the existing atlas bundles.

What it does, in order:

* **Geometry first.** For each tehsil it downloads MWS polygons and village points from GeoServer (`crop_intensity:{district}_{tehsil}_intensity` and `panchayat_boundaries:{district}_{tehsil}`) into `data/geo/geometry_raw.json`.
* **One request per tehsil.** It calls `/api/v2/get_tehsil_data/` once, without a `data` filter, and splits the response into the datasets in `config/datasets.json`. The filter is not used because it rejects `forest_fire`, `forest_fringes`, `tree_in_grassland` and `ndvi`, which the unfiltered response includes (CS-83). Failed requests are retried. Presigned S3 links in `green_credit` are stripped (CS-62).
* **Back-fill.** A dataset that comes back cut off, or with fewer MWS than the geometry, is marked `complete: false`. Incomplete `lulc_vector` and `croppingintensity_annual` are back-filled from the GeoServer layers behind the API (CS-59). Set `SEFT_NO_GEOSERVER=1` to skip that. Stored rows in `data/geo/geoserver_backfill.json` fill other truncated test-district datasets.
* **Audit.** `python -m seft.cli audit` only reads the cache and prints what is still missing or incomplete. It writes nothing.

The default endpoints can be changed with `CORE_STACK_API_BASE` and `CORE_STACK_GEOSERVER`.

### `run`

Turns the cache and the knowledge files into tables and the atlas. `python -m seft.cli all` is `fetch`, then `validate`, then `run`. `validate` only reads `knowledge/*.json` and checks that every expression parses and every id resolves; it writes nothing.

* **Reads:**
  * `--locations` and every `knowledge/*.json`
  * `data/raw/<state>/<district>/<tehsil>/*.json` (refuses to start if `lulc_vector.json` is missing)
  * `data/geo/geometry_raw.json` and `data/geo/india_states.json` (map outlines)
  * optional `--answers FILE` (`community_answers.json` saved from the atlas)
* **Writes:**
  * `out/csv/mws_<district>.csv` and `villages_<district>.csv`, plus `mws_all.csv` and `villages_all.csv` — one row per MWS or village: indicators, context classes, system shares, pathway and stress status/intensity, schemes, village cluster size.
  * `out/web/index.json` — district summaries, India state outlines, a copy of all nine knowledge files, and the pooled percentile thresholds used in this run.
  * `out/web/d_<slug>.json` — one bundle per district: encoded MWS polygons, tehsil outlines, compact MWS records (indicators, mix, stresses, signals, schemes, village ids) and village rows with coordinates.
  * `web/data/` — the same bundles as both `.json` (for `http://`) and `.js` (for `file://`), plus `web/data/csv/` copies of the tables. This is what `web/index.html` loads. `--no-web` skips the atlas and writes only CSV. `--merge` keeps district bundles already in `web/data/` that this run did not produce, and rebuilds `mws_all.csv` / `villages_all.csv` over every district in the atlas.

Pooled percentile thresholds are computed across every MWS in this run (unless `rescore` / `groundtruth` pass in the atlas's stored pools). After `run`, open `web/index.html`; new districts appear on the India map with no HTML changes.

### Community answers

The atlas lets a field team answer the questions in `knowledge/questions.json` for an MWS and re-assess the stresses in the browser. Save them from the Explore or Data tab as `community_answers.json`. Running `python -m seft.cli run --answers community_answers.json` writes the same posteriors and schemes into `out/csv/` and `web/data/`.

### `groundtruth`

Scores atlas rules and Signal_Verification sheet rules against labelled micro-watersheds.

```bash
python -m seft.cli groundtruth --truth path/to/final_ground_truth.json
```

The input lists MWS known to have a pathway (`positive`) or not (`negative`), by `block_name` (tehsil) and `uid`. `config/groundtruth/pathways.json` maps each ground-truth pathway to atlas rule ids and a sheet pattern.

* **Reads:** the truth file; `config/groundtruth/pathways.json`; `knowledge/*.json` and `knowledge/sheet_rules.json`; `web/data/index.json` (atlas pooled thresholds, unless `--pools run`); `config/locations.json` when computing sample firing rates; `config/groundtruth/changes.md` and `suggestions.md` (copied into the report).
* **Writes:**
  * `config/groundtruth/active_locations.json` — cache of `get_active_locations` (`--refresh-locations` downloads it again).
  * `config/groundtruth/locations.json` — resolved `{state, district, tehsils}` for the labelled blocks.
  * `config/groundtruth/resolution.json` — how each block name was matched (including ambiguous names settled by uid).
  * `config/groundtruth/final_ground_truth.json` — copy of `--truth` when a different path is passed.
  * `data/raw/...` for those tehsils, through the normal fetcher (`--no-fetch` uses only the cache; `--force` re-downloads).
  * `out/groundtruth/report.md` — confusion tables, combination tables, changes and suggestions.
  * `out/groundtruth/confusion.csv`, `detail.csv` (one row per label with rule results and signals), `combinations.csv`, `results.json`.
  * `out/groundtruth/sample_rates.json` — firing rates over the atlas sample, cached per knowledge version (`--no-sample` skips this).

Steps:

1. **Resolve locations.** Each block name is matched against `get_active_locations` without case. `"Keonjhar (Kendujhar)"` also matches `keonjhar` and `kendujhar`. A name found in more than one district is settled by which tehsil's `lulc_vector.json` contains the listed uid.
2. **Fetch** those tehsils into `data/raw/` like any other location.
3. **Score both rule sets.** Atlas rules use the pooled thresholds from `web/data/index.json` so they match the live atlas (`--pools run` pools over the ground-truth MWS instead). Sheet rules (`knowledge/sheet_rules.json`, built by `tools/build_sheet_rules.py`, evaluated by `seft/sheet.py`) treat signals as 0/1, `or` as a sum and `and` as a product. An atlas pathway is present when any of its rules is triggered; unknown predictions are left out of accuracy.
4. **Report.** Metrics (balanced accuracy, F1), sample firing rates, atlas OR/AND sheet combinations, and a confidence-tier table (how often the label is positive when both, one or neither rule set fires). `python tools/groundtruth_whatif.py` scores candidate rule changes without applying them.

### `wb-layers` (waterbody atlas, in progress)

Downloads the two GeoServer waterbody layers for every tehsil and keeps a compact copy. This is the first step of the waterbody atlas.

* **Reads:** `config/waterbody/locations.json` (or `--locations`): by default the 73 tehsils of the eight original atlas districts. Layers come from `swb:surface_waterbodies_{district}_{tehsil}` (polygons, attributes, yearly `area`, `k`, `kr`, `krz`) and `swb:waterbodies_zoi_{district}_{tehsil}` (zone-of-influence circles with yearly cropping) on `CORE_STACK_GEOSERVER`.
* **Writes:** `data/raw/<state>/<district>/<tehsil>/swb_layers.json.gz`, with waterbodies (attributes, yearly series as lists, centroid, bounding box, polygon simplified to about 5 m) and zones of influence (attributes, yearly cropping, centre, bounding box, radius `zoi` in metres). Cached tehsils are skipped unless `--force`. `--bundle FILE.zip` also packs all the layer files into one zip.
* **Network:** GeoServer is on port 8443, so run this where that port is reachable.
* **Caveat:** most tehsils' zone-of-influence layers carry no `wb_id` (WB-02 in `docs/core_stack_waterbody_api_issues.md`), so zones are matched to waterbodies by location.

```bash
python -m seft.cli wb-layers --bundle wb_layers.zip
```

## How the frontend works

`web/index.html` is a single-page atlas. It does not read `knowledge/` or `data/raw/` itself. Everything it needs is written into `web/data/` by `run` (via `seft/webdata.py`).

**Boot.** On load it calls `loadData("index")`:

* over `http://` or `https://`, it fetches `web/data/index.json`;
* over `file://` (opened from disk), browsers block `fetch`, so it loads `web/data/index.js`, which assigns the same object to `window.SEFT_DATA["index"]`.

`index.json` holds:

* `districts` — name, slug, state, tehsil list, outline, bounds, area-weighted system mix, stress rates, top schemes (drives the India map and the district picker);
* `states` — India state outlines, copied from `data/geo/india_states.json`;
* `knowledge` — a snapshot of all nine `knowledge/*.json` files (tabs, labels, questions, scheme text, methodology);
* `pools` and `signal_thresholds` — the percentile cut-offs used when this atlas was built.

**District data.** Choosing a district calls `loadBundle(slug)`, which loads `web/data/d_<slug>.json` (or `.js`). That bundle has encoded MWS polygons (`m.g`), tehsil outlines, compact MWS records (indicators `i`, context `c`, mix `m`, stresses `s`, signal grades `sg`, schemes `sc`, village ids `v`) and village rows with lon/lat. Geometry uses the same delta encoding as `seft/geo.py` (`decode()` in the page). Bundles stay in memory (`BUNDLES`) so switching tehsils does not reload.

**Tabs.** Explore (map + reading pane), Data (CSV downloads from `web/data/csv/mws_*.csv` and `villages_*.csv`), Knowledge graph, System archetypes, Stress rules, Community questions, Schemes, Methodology. The last five render only from `IDX.knowledge`; they do not hit the network again.

**In-browser scoring.** The block between `/*CORE-START*/` and `/*CORE-END*/` mirrors `seft/expr.py`, `archetypes.py`, `signals.py` / `stresses.py`, `assess.py` and `schemes.py`. Community answers therefore re-score mix, stresses and schemes in the page without Python. Keep that block in step when changing those modules. Answers stay in the browser until saved as `community_answers.json` and passed to `run --answers`.

**Without a rebuild.** Editing `knowledge/*.json` does not change the page until `run` (or `python -m seft.rescore`) rewrites `web/data/index.json`. `rescore` reuses indicators, contexts and mix already stored in the bundles, so it does not need `data/raw/`.

## Layout

```
config/
  locations.json      districts and tehsils to analyse (edit, or use `seft.cli add`)
  datasets.json       get_tehsil_data datasets and whether they are MWS- or village-level
  counts.json         MWS and village counts of the test tehsils (reference)
  groundtruth/        labelled MWS, pathway map, location resolution (see groundtruth command)
knowledge/            all logic and metadata, editable by experts (see knowledge/README.md)
seft/                 Python package (walkthrough below)
tools/                sheet-rule compiler and ground-truth what-if
data/
  geo/                MWS, village and tehsil geometry, India state outlines, GeoServer back-fill of the test districts
  raw/                downloaded API data (created by fetch; not shipped)
out/csv/              result tables (mws_<district>.csv, villages_<district>.csv, *_all.csv)
out/groundtruth/      confusion matrices and detail from the groundtruth command
out/web/              atlas bundles before they are copied to web/data (gitignored)
web/
  index.html          the atlas
  data/               atlas data: index + one bundle per district, as .json and .js, and the CSV tables
docs/                 CoRE Stack API issues log (CS-01 to CS-73)
tests/test_offline.py add -> fetch -> audit -> validate -> run against a mock CoRE Stack server
```

## Code walkthrough

Read the files in this order. It is the path a new location takes from a tehsil name to a pixel on the map.

### 1. Config and knowledge (what you edit)

Nothing in `seft/` hard-codes a district, an indicator or a rule. Locations live in `config/locations.json`. Which API datasets to cache is `config/datasets.json`. Every formula, threshold, system share, stress rule, scheme and community question is a JSON file in `knowledge/` (`knowledge/README.md` is the editing guide). `config/counts.json` is a reference table of test-tehsil MWS counts; the pipeline does not read it.

### 2. Entry point — `seft/cli.py`

`python -m seft.cli` is the only command you need day to day. It parses subcommands and calls the modules below. `add` writes the locations file itself. `fetch` / `audit` / `validate` / `run` / `groundtruth` import the matching module. `all` is fetch, then validate, then run.

### 3. Shared helpers — `seft/util.py`

Repository root, JSON load/save, `slug` (cache path names) and `gs_slug` (GeoServer layer names, which keep hyphens). `raw_dir(state, district, tehsil)` is `data/raw/<slug>/<slug>/<slug>/`. `iter_locations` walks the locations file.

### 4. Download — `seft/fetch.py`, `geo.py`, `ingest.py`, `schema.py`, `backfill.py`

`fetch.py` is the driver described under `fetch` above: GeoServer geometry, one unfiltered API request per tehsil, split into dataset files, completeness checks, live GeoServer back-fill of truncated LULC and cropping intensity.

* `geo.py` encodes Shapely polygons as compact integer delta-rings. The same encoding is stored in `geometry_raw.json`, copied into atlas bundles, and decoded in `web/index.html`.
* `ingest.py` turns a `get_tehsil_data` JSON (or a string cut off at the MCP size limit) into `{dataset: (rows, units, complete)}`. `python -m seft.ingest` can parse a saved MCP response by hand.
* `schema.py` maps the documented API column names (unit suffixes, `DeltaG_in_mm_2017-2018`) onto the internal names the knowledge files use (`hydro.delta_g`). It accepts both the nested v1-style rows and the flat v2 rows.
* `backfill.py` applies `data/geo/geoserver_backfill.json` to incomplete test-district caches (hydrology, livestock, and similar) after the live fetch.

### 5. Coverage check — `seft/audit.py`

Reads each required dataset file in `data/raw/` and prints `missing` / `incomplete:n/expected` / `ok`. Use it after `fetch` and before `run`.

### 6. Cache → one record per MWS — `seft/load.py`

This is the join step. For each tehsil it reads the cached JSON files, aliases datasets (`lulc_vector` → `lulc`, `hydrological_annual` → `hydro`, …), turns yearly columns into numpy series on 2017–2024, and builds village tables. An MWS that straddles tehsils appears in several responses, sometimes with different values (CS-63); `load_district` keeps the copy from the home tehsil (largest village-area overlap) and records the others in `tehsils`. Village census and livestock values are apportioned to MWS by intersection area for indicators, and each village is assigned to the MWS it overlaps most for the cluster list.

### 7. Expression language — `seft/expr.py`

Every `expr` / `share` / `trigger` / `condition` in the knowledge files is evaluated here. Only arithmetic, comparisons, `and`/`or`/`not`, attribute access (`lulc.tree_forest_area`), `in`, and a whitelist of functions (`mean`, `slope`, `div`, `ramp`, …) are allowed, so a JSON file cannot run arbitrary code. Series are numpy arrays; missing values are NaN and propagate as unknown.

### 8. Analysis pipeline — `seft/pipeline.py` and the stage modules

`pipeline.run` is three passes over every MWS in the locations file:

1. **Indicators** (`indicators.py` + `knowledge/variables.json`). Expressions over the loaded datasets, in dependency order. Village-based values are blanked when villages with data cover less than 20% of the MWS. District rainfall is then rescaled to the normals in `contexts.json` (`rain_norm`); Pune is left unscaled.
2. **Contexts and system mix** (`context.py`, `archetypes.py`). Each MWS gets one class per dimension (rainfall regime, aquifer, terrain, groundwater category, canal access). Helpers and share rules split the MWS area among archetypes and close the shares to 100%. Community answers can override helpers or shift share (`assess.system_overrides`).
3. **Signals, stresses, schemes** (`signals.py`, `stresses.py`, `assess.py`, `schemes.py`). Pooled percentiles are computed once over the whole run. Each signal grades 0–1; rules in `causal_graph.json` combine them (`systems` gate, `trigger`, `intensity` 0–100) and `taxonomy.json` rolls them up to observed stresses inside production systems. `assess.py` turns status + intensity + confidence into a prior and updates it with answer likelihood ratios. `schemes.py` matches central and state schemes to triggered stresses, state, eligibility condition and archetype share.

`pipeline.score` is the per-MWS last step; `rescore.py` and `groundtruth.py` call it on records that already have indicators.

### 9. Outputs — `seft/export.py` and `seft/webdata.py`

`export.write_csv` writes the wide MWS and village tables. `export.write_web` builds `out/web/index.json` and `d_<slug>.json`, packing knowledge, geometry and results. `webdata.build` copies those bundles to `web/data/` as `.json` and `.js` and combines per-district CSVs into `mws_all.csv` / `villages_all.csv`. `--merge` is implemented here: existing `d_*.json` whose district is not in the new index are kept. `python -m seft.webdata` re-copies `out/web` if you need to, without re-running the analysis.

### 10. Atlas — `web/index.html`

See [How the frontend works](#how-the-frontend-works). After `run`, this is the only file a reader opens.

### 11. Knowledge checks and rescore — `seft/validate.py`, `seft/rescore.py`

`validate.py` walks every expression and id in `knowledge/` (variables, context classes, helpers, shares, signals, graph edges, scheme conditions, question targets, source ids). Run it after editing JSON, before `run`.

`rescore.py` rebuilds stresses, schemes and tables from the indicators already stored in `web/data/`, without `data/raw/`. Use it after changing `signals.json`, `causal_graph.json`, `taxonomy.json`, `questions.json` or `schemes.json`. Variables added since the bundles were built stay missing until the locations are fetched and `run` again.

### 12. Ground truth — `seft/groundtruth.py`, `seft/sheet.py`, `tools/`

`groundtruth.py` is the `groundtruth` command: resolve blocks, fetch, score atlas + sheet, write `out/groundtruth/`. `sheet.py` evaluates `knowledge/sheet_rules.json` (0/1 signals; unknown signals make the trigger `insufficient data` unless every fill-in agrees). `tools/build_sheet_rules.py` regenerates that JSON from the Signal_Verification conventions. `tools/groundtruth_whatif.py` scores candidate atlas expressions against the last ground-truth cache without changing the live rules; results feed `config/groundtruth/suggestions.md`.

### 13. Tests — `tests/test_offline.py`

Starts a mock API and GeoServer serving a synthetic district built on Basantrai (Godda) geometry, copies the repo to a temp directory, and runs `add` → `fetch` → `audit` → `validate` → `run --merge`. The mock truncates `lulc_vector` so the GeoServer back-fill is exercised. No API key or network is needed.

`seft/__init__.py` only holds the package version. `docs/core_stack_api_issues.md` is the numbered log (CS-01 …) of API quirks that the modules above work around.

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
