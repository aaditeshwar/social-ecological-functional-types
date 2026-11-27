"""waterbody-impact: the effect of an intervention (desilting first) on a waterbody's seasonal water.

registry.py  intervention registries: build from GeoServer layer lists, resolve names, link to atlas waterbodies
pool.py      the waterbodies controls are drawn from (atlas waterbodies with their yearly series and MWS context)
estimate.py  controls, the four estimators, placebos, the untreated reference and the verdict
notes.py     public notes from the rules in knowledge/impact/notes.json
run.py       impact-run: every registry record, averages by unit, outputs for the atlas
"""
