# Waterbody knowledge

The waterbody atlas treats each waterbody as the unit and takes its landscape context from the watershed
atlas (through its home MWS). All logic sits in eight JSON files, read by `python -m seft.cli wb-run` and by the
page (web/index.html, Waterbodies); `wb-validate` checks that every id, expression, question and source resolves.

- `types.json`: size floor (0.05 ha), `derived` fields evaluated first (`on_stream`, `fed_by_stream`) and the
  type rules, checked in order (out of scope: unclassified, reservoir, large river; in scope: river reach,
  canal-fed, on-stream tank, small on-stream pond, headwater pond, village pond, farm pond). The type fields
  `inflow` and `ownership` are unknown from data and set only by community answers, so without answers the types
  are those from data.
- `variables.json`: every waterbody variable (computed in `seft/wb/indicators.py`) and the type fields, with unit,
  description and sources. Signals and roles also read the home MWS as `mws_<id>` (watershed `variables.json`),
  `share_<system>` and `ctx_<dimension>`.
- `signals.json`: graded signals from each waterbody's own series and zone of influence (evidence and opportunity),
  and yes/no context signals. Most thresholds are absolute; `s_poor_fill` is pooled by type (lowest 20%, severe
  10%). Trend and recent-loss signals use relative fill (fill divided by the tehsil's median fill that year).
- `roles.json`: weights from 0 to 1 for what the water is likely used for: irrigation, kharif drought
  protection, fishery, livestock, recharge and domestic. Rule intensities are scaled by the roles they name.
- `rules.json`: stress and opportunity rules with the types they apply to, a gate, a trigger, an intensity,
  `severe_at`, a confidence, a rationale, a public note, interventions and sources.
- `questions.json`: community questions. Type questions set `inflow` or `ownership` (`set`), after which the type
  and every rule are evaluated again. Stress questions carry likelihood ratios for rules (`stress`), applied to a
  prior set by the data result (`assessment`), as in the watershed atlas. `wb-assess --answers` gives the same
  results as the page.
- `schemes.json`: the schemes that can fund each rule's interventions, and the farm-pond schemes behind recent
  ponds, with status notes checked on the date in `verified` (MGNREGS was replaced by VB-G RAM G on 1 July 2026).
- Interventions come from the shared catalogue `knowledge/interventions.json`: `addresses_wb` lists the waterbody
  rules an intervention responds to and `wb_types` the types it applies to; its landscape fit is judged on the
  waterbody's home micro-watershed. `wb-run` writes `interventions_suited` / `interventions_possible` per waterbody.
- `sources.json`: waterbody sources. Every `sources` list may also cite ids from the watershed `knowledge/sources.json`.
  Thresholds without a published norm cite `expert_judgement`.

Status per rule and waterbody: not applicable, triggered, not triggered, or insufficient data. Most rules are
checked only for waterbodies that hold water in 3 or more of the 8 years and are not new (first wet in 2022
or later).

Changes after comparing with the Water Body Census fields (22 Nov 2026) are listed in
`docs/waterbody_census_comparison.md`.
