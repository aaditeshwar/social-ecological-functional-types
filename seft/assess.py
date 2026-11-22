"""Community answers: adjust the system mix and re-assess stresses (knowledge/questions.json).

answers: {question_id: option_id}. The same logic runs in the web atlas, so results match.
"""
import math
from .util import ROOT, load_json
from .expr import evaluate

def load_questions(path=None):
    return load_json(path or ROOT / 'knowledge' / 'questions.json')

def _opts(Q, answers):
    allq = {q['id']: q for q in Q['system_questions'] + Q['stress_questions']}
    for qid, oid in (answers or {}).items():
        q = allq.get(qid)
        if not q: continue
        o = next((o for o in q['options'] if o['id'] == oid), None)
        if o: yield q, o

def system_overrides(Q, answers):
    sets, shifts = {}, []
    for q, o in _opts(Q, answers):
        sets.update(o.get('set', {}))
        shifts += o.get('shift', [])
    return sets, shifts

def prior(result, conf, A):
    """Prior from the data result, rising with intensity (0-100), then shrunk toward 0.5 by confidence."""
    st, I = result['status'], (result.get('intensity') or 0) / 100
    bp = A['base_prior']
    if st == 'triggered': base = bp['triggered_min'] + (bp['triggered_max'] - bp['triggered_min']) * I
    elif st == 'not triggered': base = bp['not_triggered'] + (bp['partial_max'] - bp['not_triggered']) * I
    elif st == 'not applicable': return None
    else: base = bp['unknown']
    return 0.5 + (base - 0.5) * A['confidence_shrink'].get(conf, 0.8)

def band(p, A):
    for b in A['bands']:
        if p >= b['min']: return b['label']
    return A['bands'][-1]['label']

def reassess(stress_res, graph, Q, answers):
    A = Q['assessment']
    conf = {s['id']: s['confidence'] for s in graph['stresses']}
    lrs, sev_flag, used = {}, set(), {}
    for q, o in _opts(Q, answers):
        for e in o['stress']:
            lrs[e['id']] = lrs.get(e['id'], 1.0) * e['lr']
            used.setdefault(e['id'], []).append(q['id'])
            if e.get('severe'): sev_flag.add(e['id'])
    for sid, r in stress_res.items():
        p0 = prior(r, conf[sid], A)
        if p0 is None:
            r.update(prior=None, posterior=None, band=None, positive=False, answered=[]); continue
        odds = p0 / (1 - p0) * lrs.get(sid, 1.0)
        p = odds / (1 + odds)
        pos = p >= A['positive_at']
        sev = None
        if pos:
            data_sev = r.get('would_severity') == 'severe' and p >= p0 - 1e-9
            sev = 'severe' if data_sev or (sid in sev_flag and p >= A['severe_at']) else 'moderate'
        r.update(prior=round(p0, 3), posterior=round(p, 3), band=band(p, A), positive=pos,
                 assessed_severity=sev, answered=used.get(sid, []))
    return stress_res
