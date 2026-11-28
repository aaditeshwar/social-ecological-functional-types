"""Introductory notes for micro-watersheds, tehsils, districts and waterbodies, from the rules in knowledge/notes.json
and knowledge/waterbody/notes.json. Mirror of the page's noteRender / mwsNoteEnv / unitNoteEnv / wbNoteEnv /
wbUnitNoteEnv (web/index.html), so the atlas and core-seft write the same note from the same data.

Each kind has `main` rules (the first whose `when` holds gives the opening sentence) and `add` rules (every one that
holds appends a sentence). Placeholders in braces are filled from the environment built here; the fields are
documented in each file's `_fields`."""
import math
import re
from collections import Counter
from .expr import evaluate
from .util import load_json, knowledge_dir

YEARS = list(range(2017, 2025))
STATUS_CODE = {'regular': 'r', 'rarely_wet': 'x', 'new': 'n', 'dry': 'd'}


def rules(which='watershed', kd=None):
    kd = kd or knowledge_dir()
    p = kd / ('notes.json' if which == 'watershed' else 'waterbody/notes.json')
    return load_json(p) if p.exists() else {}


# ---------------------------------------------------------------- formatting

def plain_label(s):
    """Label without bracketed definitions, first letter in lower case unless it starts an acronym."""
    s = re.sub(r'\s*\([^)]*\)', '', str(s or '')).strip()
    return s[0].lower() + s[1:] if s and not re.match(r'^[A-Z]{2}', s) else s


def join_and(xs):
    xs = [x for x in xs if x]
    return xs[0] if len(xs) == 1 else (', '.join(xs[:-1]) + ' and ' + xs[-1] if xs else '')


def _group_in(n):
    """Indian digit grouping, as the page's toLocaleString('en-IN')."""
    s = str(abs(int(n))); sign = '-' if n < 0 else ''
    if len(s) <= 3: return sign + s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2: parts.insert(0, head[-2:]); head = head[:-2]
    if head: parts.insert(0, head)
    return sign + ','.join(parts + [tail])


def fmt(v, key=''):
    """Numbers as the page writes them: whole numbers grouped (en-IN), others to one decimal; years as they are."""
    if isinstance(v, bool): return 'yes' if v else 'no'
    if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)):
        if 'year' in key: return str(int(v)) if float(v).is_integer() else str(v)
        if float(v).is_integer(): return _group_in(int(v))
        x = math.floor(v * 10 + 0.5) / 10
        if float(x).is_integer(): return _group_in(int(x))
        whole, dec = divmod(abs(x), 1)
        return ('-' if x < 0 else '') + _group_in(int(whole)) + '.' + str(int(round(dec * 10)))
    return '' if v is None else str(v)


def render(spec, env):
    if not spec: return ''
    env = {**env, 'true': True, 'false': False}

    def ok(r):
        try: v = evaluate(r['when'], env)
        except Exception: return False
        return v is not None and not (isinstance(v, float) and math.isnan(v)) and bool(v)

    def fill(t):
        return re.sub(r'\{(\w+)\}', lambda m: fmt(env[m.group(1)], m.group(1))
                      if env.get(m.group(1)) not in (None, '') else m.group(0), t)
    out = []
    m = next((r for r in spec.get('main', []) if ok(r)), None)
    if m: out.append(fill(m['text']))
    out += [fill(r['text']) for r in spec.get('add', []) if ok(r)]
    return ' '.join(out)


def _pct(a, b):
    return round(a / b * 100) if b else 0


def _r(x):
    return int(math.floor(x + 0.5)) if x is not None else 0


# ---------------------------------------------------------------- watersheds

def _mix_env(shares, A, min_share=None):
    spec = {a['id']: a for a in A['archetypes']}
    ix = sorted(((a, v or 0) for a, v in shares.items() if a != 'other'), key=lambda x: -x[1])
    lab = lambda a: plain_label(spec.get(a, {}).get('label', a))
    present_at = lambda a: spec.get(a, {}).get('present_at', 0.15)
    return {'dom_label': lab(ix[0][0]) if ix else '', 'dom_pct': _r(ix[0][1] * 100) if ix else 0,
            'second_label': lab(ix[1][0]) if len(ix) > 1 else '', 'second_pct': _r(ix[1][1] * 100) if len(ix) > 1 else 0,
            'mix_text': join_and([f'{lab(a)} ({_r(v * 100)}%)' for a, v in ix if v >= (present_at(a) if min_share is None else min_share)]),
            'n_systems': sum(1 for a, v in ix if v >= present_at(a))}


def _os_label(key, T, extra=None):
    base, _, t = key.partition(':')
    p_id, o_id = base.split('.', 1)
    p = next(x for x in T['production_systems'] if x['id'] == p_id)
    o = next(x for x in p['observed_stresses'] if x['id'] == o_id)
    opp = (t or o['type']) == 'opportunity'
    return (plain_label(o['label']) + (' (opportunity)' if opp and o['type'] != 'opportunity' else '')
            + ' (' + plain_label(p['label']).lower() + (', ' + extra if extra else '') + ')')


def _is_opp(key, T):
    base, _, t = key.partition(':')
    if t: return t == 'opportunity'
    p_id, o_id = base.split('.', 1)
    p = next(x for x in T['production_systems'] if x['id'] == p_id)
    return next(x for x in p['observed_stresses'] if x['id'] == o_id)['type'] == 'opportunity'


def mws_env(r, A, C, T):
    env = dict(r.get('env') or {})
    env['ctx'] = dict(r.get('ctx') or {})
    env.update(_mix_env((r.get('mix') or {}).get('shares') or {}, A))
    env.update(area_ha=_r(r.get('area') or 0), tehsil=r.get('tehsil'))
    for d in C['dimensions']:
        cl = next((c for c in d['classes'] if c['id'] == (r.get('ctx') or {}).get(d['id'])), None)
        env[d['id'] + '_label'] = plain_label(cl['label']) if cl else ''
    sig = r.get('signals') or {}
    env['ps_text'] = join_and([plain_label(p['label']) for p in T['production_systems'] if (sig.get(p['signal']) or {}).get('on') is True])
    pw = r.get('pathways') or {}
    ks = sorted((k for k, v in pw.items() if v.get('positive')),
                key=lambda k: (-(pw[k].get('posterior') or 0), -(pw[k].get('intensity') or 0)))
    st = [k for k in ks if not _is_opp(k, T)]; op = [k for k in ks if _is_opp(k, T)]
    sev = lambda k: (pw[k].get('assessed_severity') or pw[k].get('severity')) == 'severe'
    env.update(n_stress=len(st), stress_text=join_and([_os_label(k, T) for k in st[:3]]), n_severe=sum(1 for k in st if sev(k)),
               n_opp=len(op), opp_text=join_and([_os_label(k, T) for k in op[:3]]), n_schemes=len(r.get('schemes') or []))
    return env


def unit_env(recs, label, A, C, T, SC):
    n = len(recs); area = sum(r.get('area') or 0 for r in recs)
    env = {'unit_label': label, 'unit_label_cap': label[:1].upper() + label[1:], 'n': n, 'area_km2': _r(area / 100)}
    tot = area or 1.0
    arch = [a['id'] for a in A['archetypes']]
    shares = {a: sum(((r.get('mix') or {}).get('shares') or {}).get(a, 0) * (r.get('area') or 0) for r in recs) / tot for a in arch}
    env.update(_mix_env(shares, A, 0.1))
    for d in C['dimensions']:
        c = Counter((r.get('ctx') or {}).get(d['id']) for r in recs if (r.get('ctx') or {}).get(d['id']))
        top = c.most_common(1)
        cl = next((x for x in d['classes'] if top and x['id'] == top[0][0]), None)
        env[d['id'] + '_label'] = plain_label(cl['label']) if cl else ''
        env[d['id'] + '_pct'] = _pct(top[0][1], n) if top else 0
    keys = list((recs[0].get('pathways') or {}) if recs else [])
    rate = {k: sum(1 for r in recs if ((r.get('pathways') or {}).get(k) or {}).get('status') == 'triggered') / (n or 1) for k in keys}
    ks = sorted(keys, key=lambda k: -rate[k])
    st = [k for k in ks if not _is_opp(k, T)]; op = [k for k in ks if _is_opp(k, T)]
    common = [k for k in st if rate[k] >= 0.25]
    env.update(stress1_label=_os_label(st[0], T) if st else '', stress1_pct=_r(rate[st[0]] * 100) if st else 0,
               n_stress_common=len(common), stress_text=join_and([_os_label(k, T, f'{_r(rate[k] * 100)}%') for k in common[:3]]),
               opp_label=_os_label(op[0], T) if op and rate[op[0]] > 0 else '', opp_pct=_r(rate[op[0]] * 100) if op else 0)
    sc = Counter(x['id'] for r in recs for x in r.get('schemes') or []).most_common(1)
    names = {s['id']: s['name'] for s in SC['schemes']}
    env['scheme_label'] = names.get(sc[0][0], '') if sc else ''
    env['scheme_pct'] = _pct(sc[0][1], n) if sc else 0
    return env


# ---------------------------------------------------------------- waterbodies

def _weeks(b):
    """Weeks of water per year from the yearly seasonal shares, rounded to whole % as in the atlas bundles."""
    out = []
    for i in range(len(YEARS)):
        k = (b.get('k') or [None] * 8)[i] if i < len(b.get('k') or []) else None
        if k is None or (isinstance(k, float) and math.isnan(k)): out.append(None); continue
        v = [(b.get(s) or [None] * 8)[i] if i < len(b.get(s) or []) else None for s in ('k', 'kr', 'krz')]
        v = [0 if x is None or (isinstance(x, float) and math.isnan(x)) else _r(x) for x in v]
        out.append(17.3 * sum(v) / 100)
    return out


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _plural(l):
    return ' / '.join(x + ('es' if re.search(r'(ch|sh|s|x)$', x) else 's') for x in l.split(' / '))


def _status_code(b):
    return STATUS_CODE.get(b.get('status'), b.get('status'))


def wb_env(b, K, works=None, intervention_label='desilting'):
    """b: a scored waterbody with type, rules (after answers, as from seft.wb.assess), roles, vars, k/kr/krz, and
    fp_note (seft.impact.farmpond.note_fields: lined/unlined class and new-pond year of farm and headwater ponds).
    works: years of recorded interventions on it."""
    types = {t['id']: t for t in K['types']['types']}
    T = types.get(b.get('type')) or {'label': b.get('type') or 'waterbody', 'in_scope': False}
    env = dict(b.get('vars') or {})
    wk = _weeks(b); we, wl = _mean(wk[:4]), _mean(wk[4:])
    env.update(type=b.get('type'), type_label=plain_label(T['label']).lower(), in_scope=bool(T.get('in_scope')),
               status=_status_code(b), area_ha=round(b.get('area_ha') or 0, 2), stream_order=b.get('stream_order'),
               n_years=len(YEARS), tehsil=b.get('tehsil'), weeks_mean=_mean(wk), weeks_early=we, weeks_late=wl,
               weeks_change=(wl - we) if we is not None and wl is not None else None)
    rl = {r['id']: r for r in K['roles']['roles']}
    ro = sorted(((k, round(v or 0, 2)) for k, v in (b.get('roles') or {}).items()), key=lambda x: -x[1])
    strong = [k for k, v in ro if v >= 0.5]
    lab = lambda i: plain_label(rl.get(i, {}).get('label', i)).lower()
    env.update(n_roles=len(strong), roles_text=join_and([lab(k) for k in strong]),
               role_top_label=lab(ro[0][0]) if ro and ro[0][1] > 0 else '', role_top=ro[0][1] if ro else 0)
    res = b.get('rules') or {}
    opp = {r['id']: r.get('type') == 'opportunity' for r in K['rules']['rules']}
    pos = sorted((r for r in K['rules']['rules'] if (res.get(r['id']) or {}).get('positive')),
                 key=lambda r: -((res[r['id']].get('post') or 0)))
    st = [r for r in pos if not opp[r['id']]]; op = [r for r in pos if opp[r['id']]]
    rlab = lambda r: plain_label(r['label']).lower()
    env.update(n_stress=len(st), stress_text=join_and([rlab(r) for r in st[:3]]),
               n_severe=sum(1 for r in st if res[r['id']].get('severe')), n_opp=len(op), opp_text=join_and([rlab(r) for r in op[:3]]))
    env.update(b.get('fp_note') or {'fp_lining': '', 'fp_summer_area': None, 'fp_summer_years': None, 'fp_new': False, 'fp_year_label': ''})
    ys = sorted(set(works or []))
    env['n_works'] = len(ys)
    env['works_text'] = (intervention_label.lower() + ' in ' + join_and([f'{y}-{str(y + 1)[2:]}' for y in ys])) if ys else ''
    return env


def wb_unit_env(bodies, label, K, treated=None):
    scope = {t['id'] for t in K['types']['types'] if t['in_scope']}
    types = {t['id']: t for t in K['types']['types']}
    sc = [b for b in bodies if b.get('type') in scope]
    env = {'unit_label': label, 'unit_label_cap': label[:1].upper() + label[1:], 'n': len(bodies), 'n_scope': len(sc),
           'area_ha': _r(sum(b.get('area_ha') or 0 for b in bodies))}
    tys = Counter(b.get('type') for b in bodies).most_common()
    tl = lambda t: _plural(plain_label((types.get(t) or {'label': t or 'waterbody'})['label']).lower())
    for i in (0, 1):
        x = tys[i] if len(tys) > i else None
        env[f'type{i + 1}_label'] = tl(x[0]) if x else ''
        env[f'type{i + 1}_n'] = x[1] if x else 0
        env[f'type{i + 1}_pct'] = _pct(x[1], len(bodies)) if x else 0
    env['types_text'] = join_and([f'{tl(t)} ({_group_in(n)})' for t, n in tys[:4]])
    code = [_status_code(b) for b in sc]
    env.update(pct_regular=_pct(code.count('r'), len(sc)), pct_rarely=_pct(code.count('x'), len(sc)), n_recent=code.count('n'))
    wk = sorted(x for x in (_mean(_weeks(b)) for b in sc) if x is not None)
    env['weeks_median'] = wk[len(wk) // 2] if wk else None
    summer = sum(1 for b in sc if ((b.get('vars') or {}).get('krz_mean') or 0) >= 30)
    env.update(n_summer=summer, pct_summer=_pct(summer, len(sc)))
    rc = sorted(((r, sum(1 for b in sc if round(((b.get('roles') or {}).get(r['id']) or 0), 2) >= 0.5)) for r in K['roles']['roles']),
                key=lambda x: -x[1])
    env['role_label'] = plain_label(rc[0][0]['label']).lower() if rc and rc[0][1] else ''
    env['role_pct'] = _pct(rc[0][1], len(sc)) if rc else 0
    rows = []
    for r in K['rules']['rules']:
        app = [b for b in bodies if ((b.get('rules') or {}).get(r['id']) or {}).get('status') not in (None, 'not applicable')]
        trig = sum(1 for b in app if b['rules'][r['id']]['status'] == 'triggered')
        if app: rows.append((r, trig / len(app)))
    rows.sort(key=lambda x: -x[1])
    st = [x for x in rows if x[0].get('type') != 'opportunity']; op = [x for x in rows if x[0].get('type') == 'opportunity']
    common = [x for x in st if x[1] >= 0.1]
    rlab = lambda r: plain_label(r['label']).lower()
    env.update(stress1_label=rlab(st[0][0]) if st else '', stress1_pct=_r(st[0][1] * 100) if st else 0,
               n_stress_rules=len(common), stress_text=join_and([f'{rlab(r)} ({_r(v * 100)}%)' for r, v in common[:3]]),
               opp_label=rlab(op[0][0]) if op and op[0][1] > 0 else '', opp_pct=_r(op[0][1] * 100) if op else 0)
    env['n_works'] = sum(1 for b in bodies if str(b.get('wb_id')) in (treated or set()))
    return env
