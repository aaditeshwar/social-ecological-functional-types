"""`python -m seft.cli wb-audit`: per tehsil, whether the waterbody layers are cached, how many waterbodies
and zones of influence they hold, whether the zones carry wb_id (WB-02), whether the layer has drainage fields
(WB-10), and whether the API datasets the waterbody rules use are cached."""
import gzip, json
from ..util import raw_dir, iter_locations
from .layers import LAYERS_FILE

NEEDED = ['antyodaya.json', 'mws_intersect_villages.json', 'croppingdrought_kharif.json', 'lulc_vector.json']

def report(cfg, log=print):
    ok = 0; n = 0
    for s, d, t in iter_locations(cfg):
        n += 1; p = raw_dir(s, d, t) / LAYERS_FILE; notes = []
        if not p.exists(): notes.append('no waterbody layers')
        else:
            with gzip.open(p, 'rt', encoding='utf-8') as f: doc = json.load(f)
            W, Z = doc['waterbodies'], doc['zoi']
            if not doc.get('zoi_has_wb_id'): notes.append('zones matched by location (no wb_id)')
            if W and 'on_drainage_line' not in W[0]: notes.append('old layer without drainage fields')
            notes.insert(0, f'{len(W)} waterbody records, {len(Z)} zones')
        miss = [x for x in NEEDED if not (raw_dir(s, d, t) / x).exists()]
        if miss: notes.append('missing ' + ', '.join(miss))
        good = p.exists() and not miss
        ok += good
        log(f"{d} / {t}: " + '; '.join(notes))
    log(f'{ok} of {n} tehsils have the waterbody layers and the API datasets the rules need.')
