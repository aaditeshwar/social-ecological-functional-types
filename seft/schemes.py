"""Match schemes (knowledge/schemes.json) to an MWS's triggered stresses and archetypes."""
from .expr import evaluate
from .util import ROOT, load_json

def load_schemes(path=None):
    return load_json(path or ROOT / 'knowledge' / 'schemes.json')

def eligible(env, spec, state):
    """Schemes whose state and eligibility condition fit the MWS, before looking at stresses."""
    out = []
    for s in spec['schemes']:
        if s['state'] and s['state'] != state: continue
        if s.get('condition'):
            try:
                if evaluate(s['condition'], env) is not True: continue
            except Exception:
                continue
        out.append(s['id'])
    return out

def match(env, stresses, mix, spec, state):
    minshare = spec.get('match_rules', {}).get('archetype_min_share', 0.15)
    trig = {k for k, v in stresses.items() if v.get('positive', v.get('status') == 'triggered')}
    big = {k for k, v in mix['shares'].items() if v >= minshare}
    out = []
    for s in spec['schemes']:
        if s['state'] and s['state'] != state: continue
        if s.get('condition'):
            try:
                if evaluate(s['condition'], env) is not True: continue
            except Exception:
                continue
        hit = [x for x in s['addresses'] if x in trig]
        if not hit: continue
        arch = [a for a in s['archetypes'] if a in big]
        if s['archetypes'] and not arch:
            continue
        out.append({'id': s['id'], 'because': hit, 'archetypes': arch,
                    'rank': len(hit) + 0.5 * len(arch) + (0.25 if s['level'] == 'state' else 0)})
    out.sort(key=lambda x: -x['rank'])
    return out
