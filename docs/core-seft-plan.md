# core-seft: library plan

Python library for on-demand social-ecological analysis of CoRE Stack entities.
This is a plan only; the atlas CLI, `web/` and `knowledge/` in this repo stay as they are.

**PyPI / pip name:** `core-seft`  
**Import:** `from core_seft import Session, analyse`

An app (Commons Connect, a notebook, a state dashboard) creates a session with a CoRE Stack API key and a data folder, then calls `analyse`. Missing districts are fetched and cached. New signals and thresholds arrive as a **knowledge pack**, not a rewrite of the caller.

## Goals

* One function to analyse a **district**, **tehsil**, **micro-watershed (MWS)** or **waterbody**.
* Return public notes, the data and signals used, system mix, context, schemes, **intervention suggestions** (suited / possible, with landscape fit), and (for MWS/waterbody) community questions.
* Accept partial community answers and return a richer assessment (same rules as the atlas).
* Fetch-on-miss **only at district grain**. Never pull a whole state or India from `analyse`.
* Keep knowledge (rules, thresholds, notes, questions, published pools) versioned independently of library code.
* Reuse this repo’s scorer. Do not fork the rule engine.

## Non-goals (v1)

* Serving `web/index.html` or writing atlas bundles.
* Ground-truth / census comparison / sheet rules.
* `analyse` resolving an entity with only a uid (callers pass **state and district**; tehsil when the kind is tehsil; uid when the kind is mws or waterbody).
* Bulk `fetch_india`. `fetch_state` may exist later as an explicit helper, never as a side effect of `analyse`.

## Public API

```python
from core_seft import Session

s = Session(data_dir="~/core-seft-data", api_key=None)  # api_key default: CORE_STACK_API_KEY
s.refresh_knowledge()                                   # optional; ships a default pack

r = s.analyse("district", state="Odisha", district="Koraput")
r = s.analyse("tehsil", state="Odisha", district="Koraput", tehsil="Jaypur")
r = s.analyse("mws", state="Odisha", district="Koraput", uid="...")
r = s.analyse("waterbody", state="Odisha", district="Koraput", uid="...")
r = s.analyse("mws", state="...", district="...", uid="...",
              answers={"sys_irrigated_share": "less_than_model"})
```

Module-level `analyse(...)` is the same after `core_seft.configure(data_dir=..., api_key=...)`.

| Argument | Role |
|---|---|
| `kind` | `district` \| `tehsil` \| `mws` \| `waterbody` |
| `state`, `district` | CoRE Stack names, exact spelling |
| `tehsil` | required for `kind="tehsil"` |
| `uid` | required for `mws` and `waterbody` |
| `answers` | `{question_id: option_id}`; ignored for district/tehsil |
| `fetch` | default `True`: if the district cache is incomplete, fetch that district then score. `False`: raise with a clear miss |

Helpers (not used by `analyse` except district miss):

* `s.fetch_district(state, district)` — all tehsils of that district (API + geometry; waterbody layers when `kind` needs them or `include="waterbody"`).
* `s.refresh_knowledge(version="latest")` — install a knowledge pack into `data_dir/knowledge/`.
* `s.knowledge_version`, `s.library_version`.

### Fetch-on-miss

* Cache key is **district** (all its tehsils under `data_dir/raw/<state>/<district>/...`).
* `kind=tehsil|mws|waterbody` still fetches the **parent district** if needed.
* Waterbody analysis needs watershed datasets **and** `swb_layers.json.gz`. A waterbody miss may fetch layers for that district even if MWS data are already cached.
* Incomplete tehsils: try GeoServer back-fill as `seft.cli fetch` does; still-incomplete datasets are scored as unknown, not a hard fail, unless `lulc_vector` is missing (cannot build MWS records).

## Result envelope (every kind)

```text
kind, state, district, tehsil?, uid?
library_version, knowledge_version
identity          # names, counts, area where known
notes             # list of {id, label, public_note, type} for stresses/opportunities that are present
evidence          # indicators / signals actually used (see below)
questions         # atlas questions with must-ask scores (MWS/waterbody), or []
commons_connect   # Commons Connect questions with must-ask scores (MWS/waterbody)
answers_applied   # echo of answers, or {}
interventions     # suited/possible suggestions (entity) or frequency counts (district/tehsil)
```

### `kind="mws"`

Built from `pipeline.score` (and mix/context already on the record).

* **identity:** uid, home tehsil, all tehsils the MWS straddles, area_ha, area_km2, n_villages, canal project names.
* **context:** one class per dimension (rainfall regime, aquifer, terrain, groundwater category, canal access) with labels, plus `rain_norm` / `rain_factor`.
* **mix:** `shares`, `labels`, `present`, `dominant` / `dominant_label`, `raw_total` (same as `archetypes.finish`). If answers include system questions, this is the **updated** mix; include `mix_before` when it changed.
* **production_systems:** taxonomy systems the signals find present (same chips as Explore).
* **villages:** cluster assigned by largest overlap: name, population, ST/SC, literacy, livestock, overlap share.
* **observed_stresses:** production system → observed stress → status, intensity, severity, posterior, band, public note, triggered pathway ids.
* **pathways:** each causal-pathway rule that applies: status, intensity, public note, `signals_on`, `signals_unknown`, data values for those signals.
* **signals:** id, kind, grade, on/unknown, threshold used (absolute or pooled).
* **indicators:** values for variables that appear in those signals or in the mix helpers (not the entire variables.json dump unless asked via `detail="full"`).
* **schemes:** matched schemes (`id`, name, level, relevant_components, because, archetypes, caution/status from knowledge).
* **interventions:** from `seft.interventions.suggest` (catalogue `knowledge/interventions.json`). Each entry: id, name, side (supply/demand), category, fit (`suited` / `possible` / omit `not suited` by default), stresses it addresses (`because`), short `what`, `where`, `landscape`, caution, linked scheme ids. Ranked suited first. Recomputed after answers so suggestions follow the updated mix and posteriors.
* **questions:** atlas questions with `show_if` true, ranked by must-ask score (0–100, band must/useful/skip, why), options, which stresses/systems they affect. Same scoring as Explore (`seft.priority`). After `answers`, posteriors and mix update; return a short **diff**.
* **commons_connect:** Commons Connect inform questions (landscape, resource mapping except the per-waterbody form, planning) with the same must-ask scores as the field-visit tab. Planning work-type questions use intervention landscape fit. `detail="summary"` drops skip-band items.
* **must_ask_summary:** counts of must / useful / skip for atlas and Commons Connect.

### `kind="waterbody"`

Built from `seft.wb.score` / assess.

* **identity:** uid, type, type_label, type_description, status (`regular` / `rarely_wet` / `new`), area, home MWS uid, tehsil, stream order, lon/lat, covering villages.
* **type:** assigned type, type fields (`inflow`, `ownership` if answered), why (which type rule).
* **roles:** irrigation, drought protection, fishery, livestock, recharge, domestic (0–1); labels on `evidence.role_labels`.
* **context / mix:** copied from the **home MWS** (landscape setting, not a waterbody mix).
* **observed_stresses / rules:** waterbody rules with public notes, intensities, signals used; `not applicable` omitted from `notes` but listed in `pathways` if `detail="full"`.
* **schemes:** from `knowledge/waterbody/schemes.json`.
* **interventions:** same catalogue, keyed by `addresses_wb` and `wb_types`; landscape fit is evaluated on the **home MWS** (`seft.wb.score.iv_env`). Suited and possible only, unless `detail="full"`.
* **questions:** type and stress questions ranked by must-ask score (type: would an answer change the type; stress: same as MWS), same protocol as `wb-assess` / Explore.
* **commons_connect:** the waterbody form questions with must-ask scores (atlas matches weighted in).
* **must_ask_summary:** counts of must / useful / skip.
* **indicators:** waterbody variables plus the home-MWS fields the rules read (`mws_*`, `share_*`, `ctx_*`).

### `kind="district"` and `kind="tehsil"`

No community answers. Aggregate entity scores in that unit (tehsil = MWS whose **home** tehsil matches).

* **identity:** name, tehsil list (district), n_mws, n_villages, n_waterbodies (if layers cached; else omit or fetch layers only if already present).
* **mix:** area-weighted mean shares; dominant system of the unit.
* **context:** distribution of classes (counts or area shares) per dimension.
* **observed_stresses:** for each stress, share of MWS where present, mean intensity among those, public note (the taxonomy note, not a new district-specific note).
* **schemes:** schemes that match often (count / share of MWS), with names.
* **interventions:** interventions that are suited in many MWS of the unit (count / share), with names and side.
* **waterbodies (optional section):** counts by type and status, recent ponds, firing rates of waterbody rules — only if waterbody layers are in the cache; do not fetch layers for a district query unless `include="waterbody"`.
* **tehsils:** for `kind=district`, a compact per-tehsil row so a UI can call `kind=tehsil` next.
* **questions:** `[]`.
* **evidence:** the pooled thresholds used and n scored; not every MWS’s signal vector.

## Cache (`data_dir`)

Layout mirrors this repo so `seft.fetch` / `seft.load` can be pointed at a different root:

```text
data_dir/
  raw/<state>/<district>/<tehsil>/*.json
  raw/<state>/<district>/<tehsil>/swb_layers.json.gz
  geo/geometry_raw.json          # or per-district geo files if we split later
  knowledge/                     # installed pack (manifest + json)
  index.json                     # which districts are complete, tehsil lists, uid→tehsil maps
```

v1 can keep one `geometry_raw.json` (as now). Splitting geo by district is an optimisation, not required for the API.

`Session` sets the cache root the way today’s code uses `seft.util.ROOT / 'data'`. Implementation: pass `data_dir` into fetch/load (small plumbing), do not require the git repo.

## Knowledge packs

**Problem today:** each JSON has its own `"version"` (`signals` 0.1, `taxonomy` 0.4, …). Apps cannot pin that.

**Pack** = one versioned bundle:

* `knowledge/*.json`
* `knowledge/waterbody/*.json`
* `pools.json` — published percentile thresholds from the reference sample (from `web/data/index.json` / waterbody index)
* `manifest.json` — `version`, `date`, `min_library`, `datasets_required`

**Maintainer workflow**

Do this in the git repo. Source of truth is the `knowledge/` folder on `main`. The zip is only a snapshot for apps that pin a pack; **do not commit the zip**.

### Where versions live (two clocks)

| Clock | File | Field | Who reads it |
|---|---|---|---|
| **Knowledge pack** | `knowledge/manifest.json` | `"version"` e.g. `"1.4.0"` | `analyse` stamps this as `knowledge_version`. The GitHub tag and zip **file name** must match this string. |
| Pack vs library | `knowledge/manifest.json` | `"min_library"` e.g. `"0.1.0"` | Session refuses the pack if installed `core-seft` is older. |
| **Library** | `pyproject.toml` (`[project] version`) and `core_seft/__init__.py` (`__version__`) | e.g. `"0.1.0"` | `analyse` stamps this as `library_version`. Bump only when fetch / `analyse` code changes. |
| Per-file changelog | `"version"` inside `signals.json`, `taxonomy.json`, … | e.g. `"0.4"` | Humans and `validate` only. **Not** what apps pin. Do not keep these in lockstep with the pack. |

Bump **only** `knowledge/manifest.json` `"version"` when you publish a pack. Use [semver](https://semver.org/) on that field:

* **patch** (`1.4.0` → `1.4.1`) — wording, `public_note`, sources, scheme text, intervention `what` / `caution`. Scoring of a cached district does not change.
* **minor** (`1.4.1` → `1.5.0`) — new or changed signals, thresholds, questions, rules, intervention `suits` / `avoid`, or regenerated `pools.json`, that still run on **existing** district caches.
* **major** (`1.5.0` → `2.0.0`) — new variables (callers must re-fetch the district), or a change to the `analyse` result shape. Also raise `"min_library"` if the new pack needs a newer `core-seft`.

Also set `"date"` (ISO date) in `manifest.json`. If the pack needs extra CoRE Stack datasets, add their names to `"datasets_required"` so `analyse` can tell the caller to re-fetch.

### 1. Edit knowledge JSON in this repo (including the manifest)

There is no separate pack-source tree. Author the rules in `knowledge/`.

**When the pack version changes, always edit** `knowledge/manifest.json`: `"version"`, `"date"`, and `"min_library"` / `"datasets_required"` if those apply.

**Also edit the files that actually changed**, under `knowledge/` (watershed) and/or `knowledge/waterbody/`. How to write notes and questions: `knowledge/README.md`, `knowledge/waterbody/README.md`. Typical files:

* Watershed: `variables.json`, `contexts.json`, `archetypes.json`, `signals.json`, `taxonomy.json`, `causal_graph.json`, `schemes.json`, `questions.json`, `interventions.json`, `sources.json`, `commons_connect.json`.
* Waterbody: `knowledge/waterbody/{types,variables,signals,roles,rules,schemes,questions,sources}.json`.
* `knowledge/pools.json` — **do not hand-edit**. After a `run` / `wb-run` whose thresholds should become the published pools, regenerate it from the atlas indexes:

  ```bash
  python -c "from core_seft.knowledge import dump_pools_from_atlas; print(dump_pools_from_atlas())"
  ```

  That overwrites `knowledge/pools.json` from `web/data/index.json` and `web/data/waterbody/index.json`. Skip this for a wording-only patch.

**Leave out of the pack** (do not zip): `knowledge/README.md`, `knowledge/waterbody/README.md`, `__init__.py`, `__pycache__`. `sheet_rules.json` is for the atlas ground-truth CLI, not `analyse`; including it in the zip is harmless because install copies every `*.json`.

Check expressions and ids, then (if scoring changed) rebuild atlas outputs so pools and the web atlas match the JSON:

```bash
python -m seft.cli validate
python -m seft.cli wb-validate
# if signals, rules, variables or pools changed:
python -m seft.cli run --merge
python -m seft.cli wb-run --merge
# then dump_pools_from_atlas as above
```

Commit the JSON (including `manifest.json` and `pools.json` if regenerated) on `main` as usual.

### 2. Build the zip and attach it to a GitHub Release

Build the zip locally, upload it as a **Release asset**, then delete the local file. It does not live in git.

**Contents of the zip** — JSON only, with a `knowledge/` prefix (preferred). `refresh_knowledge` also accepts the same files at the zip root. Example for pack `1.4.0`:

```text
core-seft-knowledge-1.4.0.zip
└── knowledge/
    ├── manifest.json          # "version" must be "1.4.0"
    ├── pools.json
    ├── variables.json
    ├── contexts.json
    ├── archetypes.json
    ├── signals.json
    ├── taxonomy.json
    ├── causal_graph.json
    ├── schemes.json
    ├── questions.json
    ├── interventions.json
    ├── sources.json
    ├── commons_connect.json
    └── waterbody/
        ├── types.json
        ├── variables.json
        ├── signals.json
        ├── roles.json
        ├── rules.json
        ├── schemes.json
        ├── questions.json
        └── sources.json
```

**Tag, zip name, and URL must match `manifest.json` `"version"`.** `Session.refresh_knowledge("1.4.0")` downloads this exact URL (`core_seft/knowledge.py`, `GITHUB_RELEASE`). A different tag or asset name 404s.

| Piece | Exact value for pack `1.4.0` |
|---|---|
| Git tag | `knowledge-1.4.0` |
| Zip **file name** (Release asset) | `core-seft-knowledge-1.4.0.zip` |
| Download URL | `https://github.com/aaditeshwar/social-ecological-functional-types/releases/download/knowledge-1.4.0/core-seft-knowledge-1.4.0.zip` |

Create the zip from the repo root (only `*.json`, keep the `knowledge/` prefix):

```bash
python -c "from pathlib import Path; import zipfile
ver='1.4.0'; root=Path('knowledge'); z=Path(f'core-seft-knowledge-{ver}.zip')
with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zh:
    for p in root.rglob('*.json'):
        zh.write(p, Path('knowledge')/p.relative_to(root))
print(z.resolve())"
```

Create a GitHub Release on **this** repo (`aaditeshwar/social-ecological-functional-types`), on the commit that contains this `manifest.json` (usually `main`):

1. Releases → Draft a new release.
2. **Tag:** `knowledge-1.4.0` (create the tag on that commit). This is a pack tag, not a PyPI / library tag (`v0.2.0` would be separate).
3. Title e.g. `Knowledge pack 1.4.0`. Notes: patch / minor / major, and what changed.
4. Attach the file `core-seft-knowledge-1.4.0.zip` as a binary asset. Do not paste the zip into the release body.
5. Publish, then confirm the asset URL matches the table.

```bash
gh release create knowledge-1.4.0 core-seft-knowledge-1.4.0.zip \
  --title "Knowledge pack 1.4.0" \
  --notes "Minor: …"
```

v1 does not auto-publish packs from CI.

### 3. After publish

Apps already on that `core-seft` install pick up the pack with:

```python
s.refresh_knowledge("1.4.0")   # pin; downloads the Release zip into data_dir/knowledge/
s.refresh_knowledge()          # "latest": copy the pack bundled with this install (repo/wheel); no network
```

`analyse` then stamps `knowledge_version="1.4.0"`. Callers who do not refresh keep using JSON already in `data_dir/knowledge/` or the bundled pack.

**User workflow:** same two `refresh_knowledge` calls. The wheel / git checkout ships a default pack (`knowledge/` in this repo), so scoring works offline on an already-cached district without a Release download.

**Compatibility:** if pack `min_library` > installed library, refuse and ask to upgrade `core-seft`. If pack needs a dataset absent from the district cache, tell the caller to re-fetch that district.

**Pools** always come from the pack, never recomputed from the user’s one district.

## What to reuse (no rule fork)

| Need | Existing |
|---|---|
| Download district | `seft.fetch.fetch_all` with a one-district locations dict |
| Waterbody layers | `seft.wb.layers.fetch_all_layers` |
| MWS records | `seft.load.load_district` |
| Indicators, mix, context | `seft.pipeline.run` on that district, **passing pack pools** (`pools=` already exists) |
| Score one MWS | `seft.pipeline.score` (includes `r['interventions']`) |
| Intervention suggestions | `seft.interventions.suggest` |
| Answers | `seft.assess` |
| Waterbody score | `seft.wb.build` + `seft.wb.score` + `seft.wb.assess` |
| District/tehsil roll-up | same aggregations as `export.write_web` district summaries, filtered by home tehsil |

New code should be a thin package `core_seft/` (or `seft/api.py` re-exported) that: locates the entity, ensures the district cache, runs the existing pipeline on **that district only**, picks the uid or aggregates.

Do not run the full `config/locations.json` sample inside `analyse`.

## Repo structure

Stay in this repository. Do not split a second git repo for v1.

Add:

* `pyproject.toml` — package name `core-seft`, package dir including `seft` + a small `core_seft` façade.
* `core_seft/` — `Session`, `analyse`, result dataclasses, knowledge-pack install. Calls into `seft.*`.
* `docs/core-seft-plan.md` — this file.
* Later: `docs/core-seft.md` user README (install, `analyse`, packs) — to be written as the first implementation step, from the “Target README” outline below.

Keep: `web/`, `out/`, `seft/cli.py`, `knowledge/`, `tests/test_offline.py`. Atlas remain the maintainer product; `core-seft` is how other software calls the same engine.

Plumbing change: `seft.util.ROOT` / `raw_dir` must honour a cache root for library use. CLI default remains the repo.

## Target README outline (write fully when implementing)

1. What `core-seft` is (four entity kinds; knowledge vs cache).
2. Install: `pip install core-seft`; `CORE_STACK_API_KEY`; choose `data_dir`.
3. `Session` + `analyse` examples for district, tehsil, mws, waterbody, and mws with answers.
4. Fetch-on-miss: district only; `fetch=False`.
5. Result fields: notes, mix, context, schemes, interventions, evidence, questions.
6. `refresh_knowledge` and pinning.
7. Names must match CoRE Stack (`get_active_locations`).
8. Pointers to `knowledge/README.md` and `knowledge/waterbody/README.md` for how notes and questions are authored.
9. Sample notebooks (see phase 8).

## Sample notebooks

After the library can score a cached district, add Jupyter notebooks under `notebooks/` (shipped with the repo, not required on `pip install`). Each notebook should run top to bottom against a **small cached district** (or the mock from `tests/test_offline.py`) so reviewers do not need a full India fetch.

Suggested set:

1. **`01_analyse_mws.ipynb`** — `Session`, `analyse("mws", ...)`, print mix, context, notes, schemes, interventions, evidence; then pass partial `answers` and show the diff.
2. **`02_analyse_waterbody.ipynb`** — one waterbody: type, roles, home-MWS context, rules, schemes, interventions; type/stress answers.
3. **`03_district_and_tehsil.ipynb`** — `kind="district"` then drill into one tehsil; no answers.
4. **`04_fetch_and_knowledge.ipynb`** — `fetch=False` miss vs fetch-on-miss for one district; `knowledge_version` on the result (refresh can be shown as a commented cell if it needs the network).

Notebooks use the same public API as Commons Connect would. Keep secrets in the environment (`CORE_STACK_API_KEY`), never in the notebook file.

## Implementation phases

**0. Contract.** Result dataclasses (or TypedDicts) for the four kinds; tests with one frozen MWS/waterbody JSON (no network). This locks mix/context/schemes/interventions/notes before plumbing.

**1. Cache root.** Parameterise `raw_dir` / geo path. CLI behaviour unchanged.

**2. MWS `analyse`.** Load one cached district, score with pack pools, return full MWS result including mix, context, schemes, interventions, questions. Answers path.

**3. Fetch-on-miss.** If district incomplete and `fetch=True`, `fetch_all` for that district (need tehsil list: `get_active_locations` filtered to the named district).

**4. District and tehsil.** Aggregate the district run; tehsil filters home tehsil.

**5. Waterbody.** Ensure layers; score; include home-MWS mix/context; type/roles/schemes/interventions/questions.

**6. Knowledge packs.** `manifest.json`, ship default pack in the wheel, `refresh_knowledge` from GitHub Releases. Stamp versions on results.

**7. Package.** `pyproject.toml`, `pip install core-seft`, a short user README. Offline test: mock district (extend `tests/test_offline.py` or a smaller `tests/test_core_seft.py`).

**8. Sample notebooks.** Write the notebooks above against a cached or mock district; link them from the user README. They are the worked examples of `analyse` for MWS, waterbody, district/tehsil, fetch-on-miss and knowledge version.

## Open choices (defaults if unspecified)

* **Tehsil list for a new district:** `get_active_locations` (already cached in ground truth as `active_locations.json`). Do not require the caller to pass tehsils.
* **Uid not in district:** error, do not search other districts.
* **`detail="full"`:** include every indicator and every not-applicable rule; default is “present stresses + evidence that fed them + mix/context/schemes”.
* **Import path:** `core_seft` is the supported name; `seft.analyse` may alias it.

## Out of scope until asked

* `fetch_state`.
* Splitting `geometry_raw.json` per district.
* Publishing knowledge packs automatically from CI (manual tag is enough for v1).
* A REST server; Commons Connect can import the library.
