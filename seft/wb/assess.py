"""`python -m seft.cli wb-assess --answers community_answers.json`: re-assess waterbodies with community answers.

The page (web/index.html, waterbody atlas) does the same in the browser; both follow knowledge/waterbody/questions.json.
  1. Type questions set fields the type rules read (inflow, ownership). The type is reassigned
     (seft.wb.build.assign_type) and signals, roles and rules are scored again for the new type.
  2. Each rule's data result sets a prior probability (assessment.base_prior, by status and intensity, pulled toward
     0.5 by the rule's confidence). Each stress answer multiplies the odds by its likelihood ratio for that rule.
  3. A rule is present at assessment.positive_at or more; severe when the data say severe and the answers have not
     lowered its probability, or when an answer marked severe was given and the probability reaches severe_at.

Answers file: {"answers": {"<district slug>:<wb_id>": {"<question id>": "<option id>", ...}, ...}}.
Writes out/waterbody/answers/assessed.csv: one row per answered waterbody and rule.
"""
import csv, json
from pathlib import Path
from ..util import ROOT, load_json, slug
from .build import assign_type
from .score import score

def prior(status, intensity, confidence, A):
    bp = A['base_prior']; I = (intensity or 0) / 100
    if status == 'triggered': base = bp['triggered_min'] + (bp['triggered_max'] - bp['triggered_min']) * I
    elif status == 'not triggered': base = bp['not_triggered'] + (bp['partial_max'] - bp['not_triggered']) * I
    elif status == 'not applicable': return None
    else: base = bp['unknown']
    return 0.5 + (base - 0.5) * A['confidence_shrink'].get(confidence, 0.8)

def band(p, A):
    for b in A['bands']:
        if p >= b['min']: return b['label']
    return A['bands'][-1]['label']

def collect(answers, K):
    """(fields set by type questions, {rule: lr product}, rules with a severe answer, {rule: [(qid, lr)]})."""
    Q = {q['id']: q for q in K['questions']['type_questions'] + K['questions']['stress_questions']}
    sets, lrs, sev, used = {}, {}, set(), {}
    for qid, oid in (answers or {}).items():
        q = Q.get(qid)
        o = next((o for o in (q or {}).get('options', []) if o['id'] == oid), None)
        if not o: continue
        sets.update(o.get('set') or {})
        for e in o.get('stress') or []:
            lrs[e['id']] = lrs.get(e['id'], 1.0) * e['lr']; used.setdefault(e['id'], []).append((qid, e['lr']))
            if e.get('severe'): sev.add(e['id'])
    return sets, lrs, sev, used

def assess(b, answers, K, pools, types):
    """Result for one waterbody: {'type', 'type_data', 'rules': {id: {...}}}. b must be scored (b['vars'], b['rules'])."""
    A = K['questions']['assessment']
    sets, lrs, sev, used = collect(answers, K)
    t_data = b['type']; rules = b['rules']; t = t_data
    if sets:
        t = assign_type(b, types, sets)
        if t != t_data:
            scope = {x['id'] for x in types['types'] if x['in_scope']}
            bb = dict(b, type=t)
            rules = score(bb, b['vars'], K, pools)[2] if t in scope else {}
    conf = {r['id']: r.get('confidence', 'medium') for r in K['rules']['rules']}
    sev_at = {r['id']: r.get('severe_at', 70) for r in K['rules']['rules']}
    out = {}
    for r in K['rules']['rules']:
        rid = r['id']; x = rules.get(rid) or {'status': 'not applicable', 'intensity': None}
        p0 = prior(x['status'], x['intensity'], conf[rid], A)
        if p0 is None:
            out[rid] = dict(x, prior=None, post=None, band=None, positive=False, severe=False, used=[]); continue
        o = p0 / (1 - p0) * lrs.get(rid, 1.0); p = o / (1 + o)
        pos = p >= A['positive_at']
        data_sev = x['status'] == 'triggered' and (x['intensity'] or 0) >= sev_at[rid]
        severe = pos and ((data_sev and p >= p0 - 1e-9) or (rid in sev and p >= A['severe_at']))
        out[rid] = dict(x, prior=round(p0, 4), post=round(p, 4), band=band(p, A), positive=pos, severe=severe, used=used.get(rid, []))
    return {'type': t, 'type_data': t_data, 'rules': out}

def main(answers_path, cfg_path=None, out=None, log=print):
    from .run import score_all
    doc = json.loads(Path(answers_path).read_text(encoding='utf-8'))
    ans = doc.get('answers', doc)
    cfg = load_json(cfg_path or ROOT / 'config' / 'waterbody' / 'locations.json')
    B, stats, types, K, pools = score_all(cfg, log=log)
    by = {f"{slug(b['district'])}:{b['wb_id']}": b for b in B}
    rows = []
    for key, a in ans.items():
        b = by.get(key)
        if not b: log(f'  {key}: not in this run'); continue
        R = assess(b, a, K, pools, types)
        for rid, x in R['rules'].items():
            rows.append({'waterbody': key, 'type_data': R['type_data'], 'type': R['type'], 'rule': rid, 'status': x['status'],
                         'intensity': x['intensity'], 'prior': x['prior'], 'posterior': x['post'], 'band': x['band'],
                         'present': x['positive'], 'severe': x['severe'], 'answers': ';'.join(f'{q}x{lr}' for q, lr in x['used'])})
        log(f"  {key}: type {R['type_data']}" + (f" -> {R['type']}" if R['type'] != R['type_data'] else '') +
            f"; present: {', '.join(r for r, x in R['rules'].items() if x['positive']) or 'none'}")
    out = Path(out or ROOT / 'out' / 'waterbody' / 'answers'); out.mkdir(parents=True, exist_ok=True)
    if rows:
        with open(out / 'assessed.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        log(f'  wrote {out / "assessed.csv"} ({len(rows)} rows)')
    return rows
