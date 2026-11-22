# Waterbody knowledge

The waterbody atlas treats each waterbody as the unit and takes its landscape context from the watershed
atlas (through its home MWS). Files, in the order they are used by `python -m seft.cli wb-run` (check them with `wb-validate`):

- `types.json`: size floor (0.05 ha) and the type rules, checked in order (out of scope: reservoir, large river;
  in scope: river reach, canal-fed, on-stream tank, small on-stream pond, headwater pond, village pond, farm pond).
- `signals.json`: graded signals from each waterbody's own series and zone of influence, and context signals
  from its home MWS. Most thresholds are absolute; `s_poor_fill` is pooled by type (lowest 20%, severe 10%).
  Trend and recent-loss signals use relative fill (fill divided by the tehsil's median fill that year), so
  that drought years such as 2023 do not read as decline.
- `roles.json`: weights from 0 to 1 for what the water is likely used for: irrigation, kharif drought
  protection, fishery, livestock, recharge and domestic. Rule intensities are scaled by the roles they harm.
- `rules.json`: stress and opportunity rules with the types they apply to, a gate, a trigger, an intensity,
  a rationale, a public note, interventions and community questions.

Status per rule and waterbody: not applicable, triggered, not triggered, or insufficient data. Rules are
checked only for waterbodies that hold water in 3 or more of the 8 years and are not new (first wet in 2022
or later), except the recent-loss and canal and river rules, which need 3 wet years.

Changes after comparing with the Water Body Census fields (22 Nov 2026) are listed in
`docs/waterbody_census_comparison.md`.
