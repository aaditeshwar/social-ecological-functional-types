# core-seft

`core-seft` scores **districts**, **tehsils**, **micro-watersheds (MWS)** and **waterbodies** from CoRE Stack data. It returns the same public summary the Explore pages show: notes, mix, landscape context, villages, matched schemes, **intervention suggestions** (suited / possible), evidence, and (for an MWS or waterbody) **atlas and Commons Connect questions ranked by must-ask score**. The payload is meant to sit inside field apps such as Commons Connect (planning a visit) or Know Your Landscape (an entity briefing).

Two clocks:

* **Library** (`core-seft` on PyPI / this repo) — fetch, cache, `analyse` contract.
* **Knowledge pack** (`knowledge/*.json`) — signals, thresholds, notes, questions, published percentile pools.

The atlas CLI in this repository stays as the maintainer product. Apps import `core_seft`.

## Install

From this repository (editable):

```bash
python -m pip install -e .
```

Set a CoRE Stack API key (needed only when the queried tehsil or district is not already cached):

```bash
export CORE_STACK_API_KEY=...                 # bash
$env:CORE_STACK_API_KEY = "..."               # PowerShell
```

Choose a cache folder. The default is `~/core-seft-data`. Against this repo’s sample districts, point at the repo `data/` folder:

```python
from core_seft import Session
s = Session(data_dir="data")                  # repo cache
# s = Session(data_dir="~/core-seft-data")    # library default
```

On Windows use `python -m pip` rather than `pip` if Application Control blocks `pip.exe`.

## Analyse

```python
from core_seft import Session

s = Session(data_dir="data", api_key=None)    # api_key default: CORE_STACK_API_KEY
s.refresh_knowledge()                         # optional; ships a default pack

r = s.analyse("district", state="Jharkhand", district="Godda")
r = s.analyse("tehsil", state="Jharkhand", district="Godda", tehsil="Basantrai")
r = s.analyse("mws", state="Jharkhand", district="Godda", tehsil="Basantrai", uid="12_313813")
r = s.analyse("waterbody", state="Jharkhand", district="Godda", tehsil="Basantrai", uid="9628377")
r = s.analyse("mws", state="Jharkhand", district="Godda", tehsil="Basantrai", uid="12_313813",
              answers={"sys_irrigated_share": "low"})
print(r.mix["dominant"], [i["name"] for i in r.interventions[:5]])

# impact of an intervention on a waterbody (registry record, or the intervention passed here)
r = s.analyse("waterbody-impact", state="Maharashtra", district="Pune", tehsil="Daund", uid="7806220")
r = s.analyse("waterbody-impact", state="Maharashtra", district="Pune", tehsil="Daund", uid="7805722",
              intervention={"type": "desilting", "year": 2023, "volume_m3": 10000})
r = s.analyse("waterbody-impact", state="Maharashtra", district="Pune", tehsil="Daund")   # average of the tehsil
```

`kind="waterbody-impact"` returns a plain dict. For a waterbody: `waterbody` (id, type, area, MWS, location),
`records` (one per window: `single`, or `first` and `combined` when there are several works; each with
`pre_years`, `post_years`, `controls`, `effects` for W, RR and SR with the four estimators, placebos and
percentile, `verdict`, `reason`, `flags`, `quality_flags`, `note` and the `group` mean for the district and
type), `source` (`registry` or `supplied`), `screened` (whether a registry covers the district, so treated
waterbodies are kept out of the controls; without one every other waterbody is assumed untreated) and
`registries`. For a district or tehsil: `average` (n, mean, 95% range, likely gains and losses, the note) and
`records`. Registries are read from `<data_dir>/registries/` and the repository's `data/registries/`. Controls
come from every cached tehsil of the district plus the waterbody's own tehsil; fetch neighbouring tehsils first
for waterbodies near a tehsil edge. The first call in a district builds the pool and computes every registered
work there (tens of seconds); later calls reuse it.

Module-level `analyse(...)` is the same after `core_seft.configure(data_dir=..., api_key=...)`.

Every call needs **state and district** (CoRE Stack spelling). Tehsil is required for `kind="tehsil"`. For MWS and waterbody, pass **both** `tehsil=` and `uid=` — that is the call that downloads one tehsil on a miss. Omitting `tehsil=` still works if that uid is already in `data_dir`. `analyse` never searches India for a uid.

`fetch=True` (default): download **and cache** any missing tehsils, then score. The grain is **tehsil** for `kind="tehsil"|"mws"|"waterbody"`, and **all tehsils of the district** for `kind="district"`. `fetch=False` raises `CacheMiss` instead of hitting the network. A waterbody query may also fetch GeoServer layers for that tehsil. District queries do not fetch waterbody layers unless `include="waterbody"`.

## Result fields

Every kind includes `kind`, `state`, `district`, `library_version`, `knowledge_version`, `identity`, `notes`, `evidence`, `questions`, `answers_applied`, `interventions`.

| Field | MWS / waterbody | District / tehsil |
|---|---|---|
| `intro_note` | Short introductory note: for an MWS its system mix, contexts, likely stresses, opportunities and schemes; for a waterbody its type, size, water presence, trend, likely uses, stresses and recorded interventions | Size, system mix, common contexts, the most common stresses and opportunity, the scheme matched most often |
| `identity` | Area, canals, villages count; waterbody also has type label, description, coordinates, stream order | Counts and area |
| `context` | Classes with labels (rainfall, aquifer, terrain, …); waterbody copies the **home MWS** | Distribution of classes |
| `mix` | System shares, labels, dominant, present | Area-weighted mean shares |
| `production_systems` | Production systems the atlas finds present | — |
| `villages` | Census cluster (name, population, overlap), ranked like Explore | — |
| `schemes` | Matched schemes with names, level, components, because | Schemes that match often (count / share) |
| `interventions` | Suited then possible; stresses addressed, `what`, `where`, landscape, caution, schemes | Interventions suited in many MWS (count / share) |
| `questions` | Atlas questions with `show_if` true, ranked by **must-ask** (`score` 0–100, `band` must/useful/skip, `why`) | `[]` |
| `commons_connect` | Commons Connect inform questions (landscape + resource mapping + planning on an MWS; waterbody form on a waterbody), same must-ask scores as the field-visit tab | — |
| `must_ask_summary` | Counts of must / useful / skip for atlas and Commons Connect | — |
| `diff` | After `answers`: status / posterior / schemes / interventions that changed | — |
| `waterbodies` | MWS with `include="waterbody"`: `n_waterbodies` and `note` for the waterbodies whose home is this MWS | When waterbody layers are cached (or `include="waterbody"`): counts, rule rates and `note` on the waterbodies of the district or tehsil |

Must-ask scores use the same rules as `seft.priority` and the Explore / Commons Connect tabs (`knowledge/commons_connect.json` → `priority`). Bands: **must** ≥ 60, **useful** ≥ 30, **skip** below that. `detail="summary"` omits Commons Connect questions in the skip band; `detail="full"` keeps them. Apps should treat skip-band atlas questions as collapsed, as the page does.

The notes come from the rules in `knowledge/notes.json` (MWS, tehsil, district) and `knowledge/waterbody/notes.json` (waterbody, and the waterbodies of an MWS, tehsil or district), rendered by `seft/intro_notes.py`, which mirrors the atlas page: the same data and answers give the same note. For farm and headwater ponds the waterbody note also says whether the pond's water looks lined or unlined and whether it is a new pond (first wet from 2019), from `seft.impact.farmpond.note_fields` and the thresholds in `knowledge/impact/farmponds.json`; the effect of new ponds on cropping is computed by `impact-farmpond` and shown in the atlas, not by `analyse`. A tehsil query fetches only that tehsil's layers, so its waterbodies are those whose centre lies inside the tehsil boundary (`seft/wb/run.py` `dedupe`); a waterbody listed only in a neighbouring tehsil's layer is counted in the atlas but not here.

`r.to_dict()` is JSON-safe. `detail="full"` adds not-applicable rules and every indicator.

## Predict impact and site suitability

```python
import core_seft as cs

# a proposed farm pond in a micro-watershed (or lat=/lon=, or waterbody= for an existing one)
p = cs.predict_impact("new_pond", state="Maharashtra", district="Pune", mws="25_14510",
                      type="farm_pond", area_ha=0.3, lined=True)
p["predicted"]            # cropping intensity around the pond, percentage points
p["group"], p["similar"]  # the fifth of assessed ponds it falls in (mean, 95% range, p10-p90) and the most similar ponds

# desilting an existing waterbody
d = cs.predict_impact("desilting", state="Maharashtra", district="Pune", waterbody=7809068, volume_m3=5000)
d["predicted"], d["range95_single"]   # weeks of water a year

# which structures suit a site, with predicted impact where the model covers the structure
s = cs.site_suitability({"slope_pct": 3, "stream_order": 2, "catchment_ha": 4, "drainage_distance_m": 100,
                         "land_use": "single kharif", "soil_group": "C"},
                        state="Maharashtra", district="Pune", mws="25_14510", area_ha=0.3)
[(x["structure"], x["verdict"]) for x in s]
```

* **`predict_impact("new_pond", ...)`**: types `farm_pond`, `headwater_pond`, `small_onstream_pond`, `onstream_tank`,
  `village_pond` (the last three exploratory; river reaches and canal-fed waterbodies are not assessed). Inputs: where (`waterbody=`, `mws=` or `lat=`/`lon=`,
  with `tehsil=` to fetch only that tehsil), `area_ha=`, and if known `zoi_area_ha=`, `catchment_ha=`, `stream_order=`,
  `lined=` (farm ponds). The micro-watershed's cropping intensity, kharif drought, context and farming-system shares
  are looked up. Unknown sizes are set to the median of assessed structures and listed in `notes`. The model is a
  random forest per type fitted to the effects the atlas measured (imputation estimates, years up to 2022-23); the
  result gives the predicted effect, the fifth of assessed structures it falls in with their observed range, and
  the most similar assessed structures (same district first). A single structure varies by about 20 points from
  year to year, so read the ranges rather than the point value.
* **`predict_impact("desilting", ...)`**: `waterbody=` and `volume_m3=`. A linear model of the headline effect on
  weeks of water (size, depth of silt removed, catchment, stream order, rainfall zone, type) on the assessable
  works; it explains little of the variation (R² is reported), so the prediction stays close to the average and
  `range95_single` is wide.
* **`site_suitability(values, ...)`**: runs `slope_pct`, `stream_order`, `catchment_ha`, `drainage_distance_m`,
  `land_use` (single kharif, single non-kharif, double, triple, croplands, barren, shrub/scrub, trees/forest,
  built-up, water) and `soil_group` (A-D) against the site rules of the 19 structures in
  `knowledge/interventions.json`. Each structure gets suitable / suitable on the values given / partly suitable /
  not suitable / unknown, the missing inputs and each rule with its basis and sources. With `waterbody=` its stream
  order and catchment fill missing values. Point layers (slope, drainage distance, soil) are not fetched yet: pass
  them in.

**Models.** `core_seft/models/farmpond.json.gz` (about 0.4 MB: 100 trees per type as plain arrays, the cut points
and observed effects of each fifth, and the table of assessed structures) and `core_seft/models/desilting.json.gz`
(about 10 kB). Predicting needs numpy only. Rebuild them with the impact commands (they also write copies to
`out/impact/`):

```bash
python -m seft.cli impact-farmpond   # new ponds and tanks: estimates, atlas bundles and farmpond.json.gz
python -m seft.cli impact-run        # desilting estimates and bundles (from the registries)
python -m seft.cli impact-model      # desilting.json.gz from the published desilting bundles
```

The forest settings (trees, leaf size, folds) are `heterogeneity` in `knowledge/impact/farmponds.json`.

## Knowledge packs

Tehsils fetched on demand are listed in `data_dir/index.json` under their district with the role `coverage`: they are scored with the published pools in the knowledge pack (`pools.json`, whose `provenance` names the districts the pools were computed over) and never change them. The atlas's own location roles (`pools`, `groundtruth`, `coverage`) are described in the README (Location roles).

`s.knowledge_version` and `s.library_version` are stamped on every result. `s.refresh_knowledge()` copies the bundled pack into `data_dir/knowledge/`. `s.refresh_knowledge("1.4.0")` tries the matching GitHub Release zip.

Pools (percentile thresholds) always come from the pack, never from the caller’s one district.

How notes and questions are authored: [knowledge/README.md](../knowledge/README.md) and [knowledge/waterbody/README.md](../knowledge/waterbody/README.md).

## Names

State, district and tehsil strings must match CoRE Stack `get_active_locations` (including hyphens such as `Mulshi-Paud`).

## Sample notebooks

Under `notebooks/` (repo only, not required on `pip install`):

1. `01_analyse_mws.ipynb`
2. `02_analyse_waterbody.ipynb`
3. `03_district_and_tehsil.ipynb`
4. `04_fetch_and_knowledge.ipynb`

They use a cached district (Godda in this repo). Keep `CORE_STACK_API_KEY` in the environment, never in the notebook file.

## Plan

The library contract and implementation phases: [core-seft-plan.md](core-seft-plan.md).
