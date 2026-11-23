"""Turn a scored MWS / waterbody / district record into the public analyse envelope."""
import math
from collections import Counter, defaultdict

from seft.expr import evaluate

from .types import AnalyseResult


def jsonable(x):
    if x is None:
        return None
    if isinstance(x, (str, bool, int)):
        return x
    if isinstance(x, float):
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    if hasattr(x, 'item') and not isinstance(x, (bytes, bytearray)):
        try:
            return jsonable(x.item())
        except Exception:
            pass
    if isinstance(x, dict):
        return {k: jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    return str(x)


def _show(q, env):
    expr = q.get('show_if')
    if not expr:
        return True
    try:
        return evaluate(expr, env) is True
    except Exception:
        return False


def _os_index(T):
    out = {}
    for p in T['production_systems']:
        for o in p['observed_stresses']:
            out[f"{p['id']}.{o['id']}"] = (p, o)
            out[(p['id'], o['id'])] = (p, o)
    return out


def _load_cc():
    from seft.util import knowledge_dir, load_json
    p = knowledge_dir() / 'commons_connect.json'
    return load_json(p) if p.exists() else None


def _priority(CC):
    if CC and CC.get('priority'):
        return CC['priority']
    from seft.commons_connect import PRIORITY
    return PRIORITY


def _must_ask(score, why, P):
    from seft.priority import band
    if score is None:
        return None
    return {'score': int(score), 'band': band(score, P), 'why': why or ''}


def _ask_summary(rows, P):
    from seft.priority import band
    out = {'must': 0, 'useful': 0, 'skip': 0}
    for row in rows:
        m = row.get('must_ask') or {}
        b = m.get('band') or (band(m['score'], P) if m.get('score') is not None else None)
        if b in out:
            out[b] += 1
    out['n'] = len(rows)
    return out


def present_questions(Q, env, kind='mws', scores=None, P=None, stress=None):
    if kind != 'mws':
        return []
    P = P or _priority(_load_cc())
    scores = scores or {}
    relevant = set()
    for sid, res in (stress or {}).items():
        if res.get('status') == 'not applicable':
            continue
        relevant.add(sid)
    out = []
    for bucket, label in (('system_questions', 'system'), ('stress_questions', 'stress')):
        for q in Q.get(bucket, []):
            if not _show(q, env):
                continue
            stresses = sorted({e['id'] for o in q.get('options', []) for e in o.get('stress', [])})
            if not stresses:
                stresses = list(q.get('stresses') or [])
            sets = sorted({k for o in q.get('options', []) for k in (o.get('set') or {})})
            s, why = scores.get(q['id'], (None, None))
            row = {
                'id': q['id'], 'kind': label, 'text': q['text'],
                'options': [{'id': o['id'], 'label': o['label']} for o in q.get('options', [])],
                'affects_stresses': stresses, 'affects_systems': sets,
                'applies': True if label == 'system' else bool(relevant and (set(stresses) & relevant)),
            }
            if q.get('rationale'):
                row['rationale'] = q['rationale']
            if s is not None:
                row['must_ask'] = _must_ask(s, why, P)
            out.append(row)
    out.sort(key=lambda x: (-(x.get('must_ask') or {}).get('score', -1), x['id']))
    return out


def present_wb_questions(K, b, scores=None, P=None):
    P = P or _priority(_load_cc())
    scores = scores or {}
    env = dict(b.get('vars') or {})
    env.update(type=b.get('type'), wb_type=b.get('wb_type'))
    relevant = {rid for rid, res in (b.get('rules') or {}).items()
                if res.get('status') != 'not applicable'}
    t, td = b.get('type'), b.get('type_data') or b.get('type')
    out = []
    for bucket, label in (('type_questions', 'type'), ('stress_questions', 'stress')):
        for q in K['questions'].get(bucket, []):
            if q.get('show_if') and not _show(q, env):
                continue
            applies_to = q.get('applies_to')
            if applies_to and t not in applies_to and td not in applies_to:
                continue
            stresses = sorted({e['id'] for o in q.get('options', []) for e in o.get('stress', [])})
            if not stresses:
                stresses = list(q.get('rules') or [])
            sets = sorted({k for o in q.get('options', []) for k in (o.get('set') or {})})
            s, why = scores.get(q['id'], (None, None))
            row = {
                'id': q['id'], 'kind': label, 'text': q['text'],
                'options': [{'id': o['id'], 'label': o['label']} for o in q.get('options', [])],
                'affects_stresses': stresses, 'affects_fields': sets,
                'applies': True if label == 'type' else bool(set(stresses) & relevant) if relevant else bool(stresses),
            }
            if q.get('rationale'):
                row['rationale'] = q['rationale']
            if s is not None:
                row['must_ask'] = _must_ask(s, why, P)
            out.append(row)
    out.sort(key=lambda x: (-(x.get('must_ask') or {}).get('score', -1), x['id']))
    return out


def present_cc_questions(CC, env, ask, P, IV=None, pos=None, pos_wb=None, forms=None, detail='summary'):
    """Ranked Commons Connect inform questions with must-ask scores (same rules as the field-visit tab)."""
    if not CC:
        return []
    from seft.priority import cc_form_scores, plan_question
    pos, pos_wb = pos or set(), pos_wb or set()
    wanted = set(forms) if forms is not None else None
    out = []
    for form in CC.get('forms') or []:
        if wanted is not None and form.get('id') not in wanted:
            continue
        qs = [plan_question(q, IV, env, pos, pos_wb, P) if form.get('section') == 'planning' else q
              for q in form.get('questions') or []]
        scored = cc_form_scores({'questions': qs}, env, ask, P)
        by_name = {q['name']: q for q in qs}
        for name, (s, why) in scored.items():
            q = by_name.get(name) or {}
            if q.get('hidden') or q.get('kind') in ('intro', 'computed'):
                continue
            if q.get('role') != 'inform' and detail != 'full':
                continue
            m = _must_ask(s, why, P) if s is not None else None
            if detail != 'full' and m and m['band'] == 'skip':
                continue
            row = {
                'form': form['id'], 'form_title': form.get('title') or form['id'],
                'section': form.get('section'), 'step': form.get('step'),
                'id': name, 'label': q.get('label') or name, 'role': q.get('role') or 'inform',
                'type': q.get('type'),
                'options': [{'id': o['id'], 'label': o.get('label', o['id'])} for o in q.get('options') or []],
            }
            if form.get('group'):
                row['group'] = form['group']
            if q.get('atlas_match'):
                row['atlas_match'] = [{'atlas': m.get('atlas'), 'id': m.get('id'), 'how': m.get('how')}
                                      for m in q['atlas_match']]
            if m:
                row['must_ask'] = m
            out.append(row)
    sec = {'landscape': 0, 'resource_mapping': 1, 'planning': 2}
    out.sort(key=lambda x: (sec.get(x.get('section'), 9),
                            -(x.get('must_ask') or {}).get('score', -1),
                            x.get('form', ''), x['id']))
    return out


def present_interventions(rows, IV, detail='summary'):
    spec = {x['id']: x for x in IV['interventions']}
    out = []
    for row in rows or []:
        if row.get('fit') == 'not suited' and detail != 'full':
            continue
        s = spec.get(row['id'], {})
        out.append({
            'id': row['id'], 'name': s.get('name', row['id']), 'side': s.get('side') or row.get('side'),
            'category': s.get('category'), 'fit': row.get('fit'), 'because': row.get('because') or [],
            'what': s.get('what'), 'where': s.get('where'), 'landscape': s.get('landscape'),
            'caution': s.get('caution'),
            'schemes': s.get('schemes') or [],
        })
    return out


def present_schemes(rows, SC):
    spec = {s['id']: s for s in SC['schemes']}
    out = []
    for m in rows or []:
        s = spec.get(m['id'], {})
        out.append({
            'id': m['id'], 'name': s.get('name', m['id']), 'because': m.get('because') or [],
            'archetypes': m.get('archetypes') or [], 'caution': s.get('caution'),
            'status': s.get('status'), 'level': s.get('level'), 'state': s.get('state'),
            'relevant_components': s.get('relevant_components') or [],
        })
    return out


def present_wb_schemes(b, K):
    from seft.wb.score import scheme_links
    spec = {s['id']: s for s in K['schemes']['schemes']}
    ids, seen = [], set()
    for rid, r in (b.get('rules') or {}).items():
        if r.get('status') != 'triggered':
            continue
        for sid in scheme_links(rid, b, K):
            if sid in seen:
                continue
            seen.add(sid); ids.append(sid)
    return [{'id': i, 'name': spec.get(i, {}).get('name', i),
             'caution': spec.get(i, {}).get('caution'), 'status': spec.get(i, {}).get('status'),
             'level': spec.get(i, {}).get('level')} for i in ids]


def _mix(r, A=None):
    m = r.get('mix') or {}
    shares = jsonable(m.get('shares') or {})
    labels = {a['id']: a['label'] for a in (A or {}).get('archetypes') or []}
    out = {
        'shares': shares,
        'present': list(m.get('present') or []),
        'dominant': m.get('dominant'),
        'raw_total': jsonable(m.get('raw_total')),
    }
    if labels:
        out['labels'] = {k: labels.get(k, k) for k in shares}
        if m.get('dominant'):
            out['dominant_label'] = labels.get(m['dominant'], m['dominant'])
        out['present_labels'] = [labels.get(k, k) for k in out['present']]
    return out


def _context(r, C=None):
    ctx = r.get('ctx') or {}
    env = r.get('env') or {}
    out = dict(ctx) if hasattr(ctx, 'items') else {}
    if env.get('rain_norm') is not None:
        out['rain_norm'] = jsonable(env.get('rain_norm'))
    if env.get('rain_factor') is not None:
        out['rain_factor'] = jsonable(env.get('rain_factor'))
    if C:
        labels = {}
        for dim in C.get('dimensions') or []:
            cid = out.get(dim['id'])
            cl = next((c for c in dim.get('classes') or [] if c['id'] == cid), None)
            labels[dim['id']] = cl['label'] if cl else cid
        out['labels'] = labels
    return jsonable(out)


def _production_systems(r, T):
    sig = r.get('signals') or {}
    out = []
    for p in (T or {}).get('production_systems') or []:
        g = sig.get(p['signal']) or {}
        on = g.get('on')
        if on is True:
            out.append({'id': p['id'], 'label': p.get('label', p['id']), 'present': True})
    return out


def _villages(uid, vill, cl, district):
    if not vill or not cl:
        return []
    by_d = cl.get(district) if isinstance(cl.get(district), dict) else None
    ids = (by_d or cl).get(uid) or []
    table = vill.get(district) if isinstance(vill.get(district), dict) else vill
    rows = []
    for vid in ids:
        v = (table or {}).get(vid) or {}
        L = v.get('livestock') or {}
        sheep = L.get('sheep_total'); goat = L.get('goat_total')
        rows.append({
            'id': vid, 'name': v.get('name'), 'tehsil': v.get('tehsil'),
            'population': v.get('pop'), 'st_population': v.get('st'), 'sc_population': v.get('sc'),
            'literacy_rate': jsonable(v.get('literacy')),
            'livestock_total': L.get('all_livestock_total'),
            'sheep_goat': None if sheep is None and goat is None else (sheep or 0) + (goat or 0),
            'overlap_share': jsonable(v.get('overlap_share')),
        })
    rows.sort(key=lambda x: (-(x.get('population') or 0), x.get('name') or ''))
    return rows


def _notes_and_stresses(r, G, T, detail='summary'):
    rules = {x['id']: x for x in G['stresses']}
    osi = _os_index(T)
    notes, observed = [], []
    for key, pw in (r.get('pathways') or {}).items():
        present = bool(pw.get('positive')) or pw.get('status') == 'triggered'
        if not present and detail != 'full':
            continue
        base = key.split(':')[0]
        p_o = osi.get(base)
        label = p_o[1]['label'] if p_o else key
        note = (p_o[1].get('public_note') if p_o else None) or ''
        row = {
            'id': key, 'label': label, 'status': pw.get('status'),
            'intensity': jsonable(pw.get('intensity')), 'severity': pw.get('severity') or pw.get('assessed_severity'),
            'posterior': jsonable(pw.get('posterior')), 'band': pw.get('band'),
            'positive': list(pw.get('positive') or []), 'public_note': note if present else None,
        }
        observed.append(row)
        if present and note:
            notes.append({'id': key, 'label': label, 'public_note': note, 'type': (p_o[1].get('type') if p_o else 'stress')})
    pathways = []
    for rid, res in (r.get('stress') or {}).items():
        if res.get('status') == 'not applicable' and detail != 'full':
            continue
        rule = rules.get(rid, {})
        on = res.get('positive') or res.get('status') == 'triggered'
        pathways.append({
            'id': rid, 'label': rule.get('label', rid), 'status': res.get('status'),
            'intensity': jsonable(res.get('intensity')), 'severity': res.get('severity') or res.get('assessed_severity'),
            'posterior': jsonable(res.get('posterior')), 'band': res.get('band'),
            'public_note': rule.get('public_note') if on else None,
            'signals_on': res.get('signals_on') or [], 'signals_unknown': res.get('signals_unknown') or [],
        })
    return notes, observed, pathways


def _signals(r, S, used, detail='summary'):
    spec = {s['id']: s for s in S['signals']}
    out = []
    for sid, sig in (r.get('signals') or {}).items():
        if detail != 'full' and sid not in used:
            continue
        s = spec.get(sid, {})
        out.append({
            'id': sid, 'kind': sig.get('kind') or s.get('kind'), 'on': sig.get('on'),
            'grade': jsonable(sig.get('grade')), 'value': jsonable(sig.get('value')),
            'threshold': jsonable(sig.get('threshold')), 'severe_threshold': jsonable(sig.get('severe_threshold')),
            'basis': sig.get('basis'),
        })
    return out


def _indicators(r, S, used, detail='full'):
    ind = r.get('ind') or {}
    if detail == 'full':
        return jsonable({k: v for k, v in ind.items() if not isinstance(v, (dict, list))})
    vars_ = set()
    spec = {s['id']: s for s in S['signals']}
    for sid in used:
        s = spec.get(sid) or {}
        if s.get('var'):
            vars_.add(s['var'])
    vars_.update(('rain_norm', 'precip_mean', 'f_crop', 'f_forest', 'f_commons', 'swb_frac', 'n_canals'))
    return jsonable({k: ind.get(k) for k in sorted(vars_) if k in ind})


def present_mws(r, G, T, S, SC, Q, IV, versions, answers=None, mix_before=None, diff=None, detail='summary',
               A=None, C=None, CC=None, villages=None):
    from seft.priority import atlas_scores_from_mws, cc_env_from_mws
    from seft.interventions import fit_env
    if A is None:
        from seft.archetypes import load_archetypes
        A = load_archetypes()
    if C is None:
        from seft.context import load_contexts
        C = load_contexts()
    CC = CC if CC is not None else _load_cc()
    P = _priority(CC)
    used = set()
    for res in (r.get('stress') or {}).values():
        if res.get('status') == 'not applicable' and detail != 'summary':
            pass
        used.update(res.get('signals_on') or [])
        used.update(res.get('signals_unknown') or [])
    notes, observed, pathways = _notes_and_stresses(r, G, T, detail)
    mix = _mix(r, A)
    mb = _mix({'mix': mix_before}, A) if mix_before else None
    env = r.get('env') or {}
    scores, st, conf = atlas_scores_from_mws(r, Q, A, G, P, answers if answers is not None else r.get('answers'))
    cc_env = cc_env_from_mws(r, T, st, conf, Q['assessment'], P, scores)
    cc_env.update(fit_env(r.get('ind') or {}, r.get('ctx'), (r.get('mix') or {}).get('shares')))
    ask = {('ws', k): v[0] for k, v in scores.items()}
    pos = {k for k, v in (r.get('stress') or {}).items()
           if v.get('positive') or v.get('status') == 'triggered'}
    cc_forms = [f['id'] for f in (CC or {}).get('forms') or []
                if f.get('id') != 'waterbody' and (f.get('unit') == 'mws' or f.get('section') in
                                                   ('landscape', 'resource_mapping', 'planning'))]
    cc_qs = present_cc_questions(CC, cc_env, ask, P, IV=IV, pos=pos, forms=cc_forms, detail=detail)
    qs = present_questions(Q, env, 'mws', scores=scores, P=P, stress=r.get('stress'))
    vrows = villages if villages is not None else []
    area = r.get('area')
    canals = list(r.get('canals') or [])
    ident = {k: v for k, v in {
        'uid': r['uid'], 'tehsil': r.get('tehsil'), 'tehsils': list(r.get('tehsils') or []),
        'area_ha': jsonable(area),
        'area_km2': round(area / 100, 1) if isinstance(area, (int, float)) else None,
        'n_villages': r.get('n_villages') if r.get('n_villages') is not None else len(vrows),
        'canals': canals or None,
    }.items() if v not in (None, [])}
    return AnalyseResult(
        kind='mws', state=r['state'], district=r['district'], tehsil=r.get('tehsil'), uid=str(r['uid']),
        library_version=versions['library'], knowledge_version=versions['knowledge'],
        identity=ident,
        context=_context(r, C), mix=mix, mix_before=mb,
        notes=notes, observed_stresses=observed, pathways=pathways,
        signals=_signals(r, S, used, detail), indicators=_indicators(r, S, used, detail),
        schemes=present_schemes(r.get('schemes'), SC),
        interventions=present_interventions(r.get('interventions'), IV, detail),
        questions=qs, commons_connect=cc_qs, villages=vrows,
        production_systems=_production_systems(r, T),
        must_ask_summary={'atlas': _ask_summary(qs, P), 'commons_connect': _ask_summary(cc_qs, P)},
        answers_applied=dict(answers or r.get('answers') or {}),
        evidence={'n_signals_used': len(used), 'pools': 'pack'},
        diff=diff,
    )


def _rule_on(res, positive_at):
    if 'positive' in res:
        return bool(res.get('positive'))
    post = res.get('post') if res.get('post') is not None else res.get('posterior')
    if post is not None:
        return post >= positive_at
    return res.get('status') == 'triggered'


def present_waterbody(b, K, mws, versions, answers=None, detail='summary', A=None, C=None, CC=None):
    from seft.interventions import suggest, load_interventions
    from seft.wb.score import iv_env
    from seft.wb.run import status as wb_status
    from seft.priority import atlas_scores_from_wb, cc_env_from_mws, cc_env_from_wb, atlas_scores_from_mws

    IV = K.get('interventions') or load_interventions()
    CC = CC if CC is not None else _load_cc()
    P = _priority(CC)
    if A is None:
        from seft.archetypes import load_archetypes
        A = load_archetypes()
    if C is None:
        from seft.context import load_contexts
        C = load_contexts()
    pos = {rid for rid, r in (b.get('rules') or {}).items()
           if r.get('positive') or r.get('status') == 'triggered'}
    ivs = suggest(iv_env(b.get('mws') or {}), pos, IV, key='addresses_wb', wb_type=b.get('type')) if pos else []
    notes, pathways = [], []
    rulespec = {x['id']: x for x in K['rules']['rules']}
    A_assess = K['questions']['assessment']
    pa = A_assess.get('positive_at', 0.5)
    for rid, res in (b.get('rules') or {}).items():
        post = res.get('post') if res.get('post') is not None else res.get('posterior')
        on = _rule_on(res, pa)
        if res.get('status') == 'not applicable' and detail != 'full':
            continue
        rule = rulespec.get(rid, {})
        pathways.append({
            'id': rid, 'label': rule.get('label', rid), 'status': res.get('status'),
            'intensity': jsonable(res.get('intensity')), 'posterior': jsonable(post),
            'band': res.get('band'), 'public_note': rule.get('public_note') if on else None,
        })
        if on and rule.get('public_note'):
            notes.append({'id': rid, 'label': rule.get('label', rid), 'public_note': rule['public_note'], 'type': 'stress'})
    mix = None
    ctx = None
    mws_env = None
    mws_pos = set()
    mscores = {}
    if mws:
        mix = _mix(mws, A)
        ctx = _context(mws, C)
        from seft.stresses import load_graph
        from seft.assess import load_questions
        Qw = load_questions()
        mscores, mst, mconf = atlas_scores_from_mws(mws, Qw, A, load_graph(), P, mws.get('answers'))
        mws_env = cc_env_from_mws(mws, None, mst, mconf, Qw['assessment'], P, mscores)
        mws_pos = {k for k, v in (mws.get('stress') or {}).items()
                   if v.get('positive') or v.get('status') == 'triggered'}
    elif b.get('mws'):
        m = b['mws']
        ctx = {k[4:]: v for k, v in m.items() if k.startswith('ctx_')}
        shares = {k[6:]: v for k, v in m.items() if k.startswith('share_')}
        mix = _mix({'mix': {'shares': shares, 'dominant': m.get('dominant_system'),
                            'present': [k for k, v in shares.items() if v], 'raw_total': None}}, A)
        ctx = _context({'ctx': ctx, 'env': {}}, C)
    scores, st, conf = atlas_scores_from_wb(b, K, P, answers)
    wb_env = cc_env_from_wb(b, K, st, conf, A_assess, P, scores, mws_env)
    ask = {('ws', k): v[0] for k, v in mscores.items()}
    ask.update({('wb', k): v[0] for k, v in scores.items()})
    cc_qs = present_cc_questions(CC, wb_env, ask, P, IV=IV, pos=mws_pos, pos_wb=pos,
                                 forms=['waterbody'], detail=detail)
    qs = present_wb_questions(K, b, scores=scores, P=P)
    tspec = next((t for t in K['types']['types'] if t['id'] == b.get('type')), {})
    rolespec = {x['id']: x for x in K.get('roles', {}).get('roles') or []}
    roles = jsonable(b.get('roles') or {})
    role_labels = {i: rolespec[i].get('label', i) for i in roles if i in rolespec}
    xy = b.get('centroid') or []
    vars_list = (K.get('variables') or {}).get('variables') or []
    ids = {v['id'] for v in vars_list}
    ind = dict(b.get('vars') or {})
    if detail != 'full' and ids:
        ind = {k: v for k, v in ind.items() if k in ids}
    ident = {k: v for k, v in {
        'uid': b.get('wb_id'), 'name': b.get('wb_name'),
        'type': b.get('type'), 'type_label': tspec.get('label'),
        'type_description': tspec.get('description'),
        'type_from_data': b.get('type_data'),
        'status': b.get('status') or wb_status(b),
        'area_ha': jsonable(b.get('area_ha')), 'home_mws': b.get('home_mws'), 'tehsil': b.get('tehsil'),
        'stream_order': b.get('stream_order'), 'zoi_match': b.get('zoi_match'),
        'lon': xy[0] if len(xy) == 2 else None, 'lat': xy[1] if len(xy) == 2 else None,
        'villages': b.get('villages') or None, 'canal_project': b.get('canal_project'),
    }.items() if v not in (None, '', [])}
    return AnalyseResult(
        kind='waterbody', state=b['state'], district=b['district'], tehsil=b.get('tehsil'), uid=str(b.get('wb_id')),
        library_version=versions['library'], knowledge_version=versions['knowledge'],
        identity=ident,
        type=b.get('type'), status=b.get('status') or wb_status(b),
        roles=roles,
        context=jsonable(ctx), mix=mix,
        notes=notes, pathways=pathways,
        schemes=present_wb_schemes(b, K),
        interventions=present_interventions(ivs, IV, detail),
        questions=qs, commons_connect=cc_qs,
        must_ask_summary={'atlas': _ask_summary(qs, P), 'commons_connect': _ask_summary(cc_qs, P)},
        answers_applied=dict(answers or {}),
        indicators=jsonable(ind),
        evidence={'home_mws': b.get('home_mws'), 'pools': 'pack',
                  'role_labels': role_labels or None},
    )


def rollup(recs, G, T, SC, IV, versions, kind, state, district, tehsil=None, waterbodies=None):
    recs = [r for r in recs if tehsil is None or r.get('tehsil') == tehsil]
    n = len(recs)
    tot = sum(r.get('area') or 0 for r in recs) or 1.0
    shares = {}
    if recs:
        arch = list((recs[0].get('mix') or {}).get('shares') or {})
        shares = {a: round(sum((r.get('mix') or {}).get('shares', {}).get(a, 0) * (r.get('area') or 0) for r in recs) / tot, 4)
                  for a in arch}
    dominant = max(shares, key=shares.get) if shares else None
    ctx_dist = {}
    if recs:
        for dim in (recs[0].get('ctx') or {}):
            w = defaultdict(float)
            for r in recs:
                w[r.get('ctx', {}).get(dim)] += r.get('area') or 0
            ctx_dist[dim] = {str(k): round(v / tot, 3) for k, v in w.items() if k is not None}
    osi = _os_index(T)
    observed, notes = [], []
    keys = list((recs[0].get('pathways') or {}) if recs else [])
    for key in keys:
        hit = [r for r in recs if (r.get('pathways') or {}).get(key, {}).get('status') == 'triggered'
               or (r.get('pathways') or {}).get(key, {}).get('positive')]
        if not hit:
            continue
        intens = [((r.get('pathways') or {}).get(key) or {}).get('intensity') for r in hit]
        intens = [x for x in intens if isinstance(x, (int, float))]
        p_o = osi.get(key.split(':')[0])
        label = p_o[1]['label'] if p_o else key
        note = p_o[1].get('public_note') if p_o else None
        observed.append({
            'id': key, 'label': label, 'n_mws': len(hit), 'share': round(len(hit) / n, 3) if n else 0,
            'mean_intensity': round(sum(intens) / len(intens), 1) if intens else None,
            'public_note': note,
        })
        if note:
            notes.append({'id': key, 'label': label, 'public_note': note, 'type': p_o[1].get('type') if p_o else 'stress'})
    spec_s = {s['id']: s for s in SC['schemes']}
    sc_c = Counter(x['id'] for r in recs for x in r.get('schemes') or [])
    schemes = [{'id': i, 'name': spec_s.get(i, {}).get('name', i), 'n_mws': c, 'share': round(c / n, 3) if n else 0}
               for i, c in sc_c.most_common()]
    spec_i = {x['id']: x for x in IV['interventions']}
    iv_c = Counter(x['id'] for r in recs for x in r.get('interventions') or [] if x.get('fit') == 'suited')
    interventions = [{'id': i, 'name': spec_i.get(i, {}).get('name', i), 'side': spec_i.get(i, {}).get('side'),
                      'category': spec_i.get(i, {}).get('category'), 'n_mws': c, 'share': round(c / n, 3) if n else 0}
                     for i, c in iv_c.most_common()]
    tehsils = []
    if kind == 'district':
        by = defaultdict(list)
        for r in recs:
            by[r.get('tehsil')].append(r)
        for t, rs in sorted(by.items(), key=lambda x: x[0] or ''):
            a = sum(x.get('area') or 0 for x in rs)
            sh = {s: sum((r.get('mix') or {}).get('shares', {}).get(s, 0) * (r.get('area') or 0) for r in rs)
                  for s in shares}
            tehsils.append({'tehsil': t, 'n_mws': len(rs), 'area_ha': round(a, 1),
                            'dominant': max(sh, key=sh.get) if sh else None})
    n_vill = sum(r.get('n_villages') or 0 for r in recs)
    return AnalyseResult(
        kind=kind, state=state, district=district, tehsil=tehsil,
        library_version=versions['library'], knowledge_version=versions['knowledge'],
        identity={k: v for k, v in {
            'state': state, 'district': district, 'tehsil': tehsil, 'n_mws': n,
            'n_villages': n_vill, 'area_ha': round(tot, 1),
        }.items() if v is not None},
        mix={'shares': shares, 'dominant': dominant, 'present': [k for k, v in shares.items() if v >= 0.05],
             'raw_total': None},
        context=ctx_dist, notes=notes, observed_stresses=observed,
        schemes=schemes, interventions=interventions, tehsils=tehsils,
        waterbodies=waterbodies, questions=[], answers_applied={},
        evidence={'n_scored': n, 'pools': 'pack'},
    )


def mws_diff(before, after):
    """Short diff of status/posterior/schemes/interventions after community answers."""
    ch = []
    for k, a in (after.get('stress') or {}).items():
        b = (before.get('stress') or {}).get(k, {})
        if (b.get('status'), b.get('posterior'), b.get('positive')) != (a.get('status'), a.get('posterior'), a.get('positive')):
            ch.append({'id': k, 'status': [b.get('status'), a.get('status')],
                       'posterior': [b.get('posterior'), a.get('posterior')],
                       'positive': [b.get('positive'), a.get('positive')]})
    def ids(rows, key='id'):
        return [x[key] for x in rows or []]
    sch_b, sch_a = set(ids(before.get('schemes'))), set(ids(after.get('schemes')))
    iv_b = {x['id']: x.get('fit') for x in before.get('interventions') or []}
    iv_a = {x['id']: x.get('fit') for x in after.get('interventions') or []}
    mix_b = (before.get('mix') or {}).get('shares')
    mix_a = (after.get('mix') or {}).get('shares')
    return {
        'stresses': ch,
        'schemes_added': sorted(sch_a - sch_b), 'schemes_removed': sorted(sch_b - sch_a),
        'interventions': {k: {'from': iv_b.get(k), 'to': iv_a.get(k)} for k in sorted(set(iv_b) | set(iv_a)) if iv_b.get(k) != iv_a.get(k)},
        'mix_changed': mix_b != mix_a,
    }
