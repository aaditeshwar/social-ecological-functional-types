# Waterbody patterns against the Water Body Census (22 Nov 2026)

`python tools/wb_census_compare.py` joins the census fields that CoRE Stack matched to its waterbodies onto
the waterbody atlas (6,134 in-scope waterbodies of 0.05 ha or more have census fields) and compares them with
the atlas's signals, roles and rules.

Two caveats limit what this can show:
- **The match is approximate.** CoRE Stack matched census points to its waterbodies by proximity and by
  capacity against area. Some matched records carry the wrong block or basin (WB-07). Census fields are
  therefore not inputs to the atlas, only a check.
- **The census describes 2017-18.** It can check the state of a waterbody at the start of the series, and
  its use, but not changes after 2019, such as a waterbody that stopped holding water in 2023-24.

Rates are the share of waterbodies where the rule fires, among those it applies to.

## What agrees

| Census field | Atlas pattern | Result |
|---|---|---|
| How full it gets: Full / ¾ / ½ / ¼ | Median kharif fill; inflow shortfall | Fill 40% / 41% / 33% / 31%; shortfall fires 6% / 11% / 15% / 18% |
| Not in use (663) vs in use (5,471) | Shrinking or silting; inflow shortfall | Silting 28% vs 20%; shortfall 15% vs 9% |
| Encroached (87) vs not | Shrinking or silting | 32% vs 20% |
| Present storage below 80% of original (2,299) vs 80% or more (1,906) | Inflow shortfall; silting | Shortfall 13% vs 7%; silting 20% vs 16% |
| Under repair (137) vs not | Stopped holding water | 22% vs 11% |
| Water user association exists (286) vs none (3,067) | Water not reaching fields | 18% vs 39% |
| Used for irrigation (2,316) | Irrigation role | Mean 0.64 vs 0.47 |
| Used for pisciculture (2,227) | Fishery role | Mean 0.51 vs 0.33 |
| Census type "percolation tanks / check dams" | Atlas types | Mostly headwater ponds and on-stream ponds and tanks |
| Census type "Ponds" | Atlas types | Mostly farm and village ponds |

## What does not agree, or cannot be checked

- **Fill frequency** ("filled every year", "usually", "rarely", "never") barely separates the atlas's fill: the
  median is 43-46% in every class. Inflow shortfall rises only from 8% to 15%, and "never filled" (149) looks
  like the best-filled class. Either the field is unreliable or the match is wrong more often for it.
- **Stopped holding water** fires in 16% of waterbodies the census calls "filled up every year". This is not a
  contradiction: the census year is 2017-18 and the atlas pattern is about 2023-24 against 2017-19.
- **Fishery opportunity** fires equally (75-76%) whether or not the census lists pisciculture, and no
  persistence threshold (rabi water 40% or 60%, summer water 20% or 30%) separates the two. Water lasting into
  rabi is common where the fishery role applies; what separates fishery use is the fishery role itself.
- **Recharge role** is only slightly higher where the census lists groundwater recharge (0.36 vs 0.31).
- **Census "Tank"** waterbodies are often typed as farm ponds (462 of 1,554), that is, off the drainage line
  and under 0.5 ha in CoRE. The CoRE polygon may cover only part of the tank, or tanks fed by channels may sit
  off the mapped drainage line.

## Tuning ideas (not applied)

1. **Stopped holding water:** require 0.25 ha or more and both of the last two years at 15% fill or less (not
   their mean). Rate 15% to 11%; Srikakulam 26% to 20%, Udaipur 25% to 16%. The association with "under
   repair" becomes stronger: 15% vs 6% (2.5 times) instead of 22% vs 11% (2 times).
2. **Inflow shortfall:** keep the rule; the "how full" gradient supports it. Lower present-to-original storage
   goes with shortfall more than with the silting trend, so silt that built up before 2017 shows as poor
   filling, not as a trend. Add "accumulated silt" as a cause in its note where the catchment is eroding, and
   ask about silt depth there too.
3. **Shrinking or silting:** keep; the not-in-use and encroachment contrasts support it. Name encroachment of
   the bed as a cause alongside silt.
4. **Water not reaching fields:** keep; the water user association contrast (18% vs 39%) is the clearest
   support in this check. Name the absence of a water user association in the note.
5. **Fishery opportunity:** raise the gate to a fishery role of 0.5 or more and treat it as a candidate list
   for discussion, since persistence alone does not separate fishery use.
6. **Typing:** consider a large catchment for the waterbody's size (catchment 20 times its area or more) as
   evidence of an on-stream position, so that channel-fed tanks off the mapped drainage line are typed as
   tanks rather than farm or village ponds.
