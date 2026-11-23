"""Read an ODK XLSForm (survey, choices, settings sheets) into a plain structure.

Used by `python -m seft.cli cc-build --forms <folder>` to make knowledge/commons_connect.json from the Commons
Connect templates. Only the English labels are kept; the forms also carry Hindi, Gujarati, Kannada, Odia and Telugu.
"""
import re

META = {'start', 'end', 'today', 'deviceid', 'username', 'phonenumber', 'audit'}

def _s(v):
    if v is None: return ''
    v = str(v).translate({0x2019: "'", 0x2018: "'", 0x201c: '"', 0x201d: '"'})
    return re.sub(r'\s+', ' ', v).strip()

def _col(hdr, *names):
    """Index of the first column whose name (ignoring case and spaces) starts with one of names."""
    norm = [re.sub(r'\s', '', h).lower() for h in hdr]
    for n in names:
        n = n.lower()
        for i, h in enumerate(norm):
            if h == n or h.startswith(n): return i
    return None

def _rows(ws):
    rows = [r for r in ws.iter_rows(values_only=True) if any(c not in (None, '') for c in r)]
    if not rows: return [], []
    return [_s(h) for h in rows[0]], rows[1:]

def _strip_html(t):
    return _s(re.sub(r'<[^>]+>', '', t))

def odk_to_expr(s):
    """ODK relevance (XPath) -> the atlas expression language (seft.expr, PyEval in the page):
    ${a} -> a, selected(${a}, 'x') -> 'x' in a, = -> ==, false() -> (1 == 0), true() -> (1 == 1)."""
    if not s: return ''
    s = re.sub(r"selected\(\s*\$\{\s*(\w+)\s*\}\s*,\s*'([^']*)'\s*\)", r"('\2' in \1)", s)
    s = re.sub(r"\$\{\s*(\w+)\s*\}", r"\1", s)
    s = s.replace('false()', '(1 == 0)').replace('true()', '(1 == 1)')
    s = re.sub(r"(?<![<>!=])=(?!=)", "==", s)
    return re.sub(r'\s+', ' ', s).strip()

def parse_xlsform(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    sh = {ws.title.lower(): ws for ws in wb.worksheets}
    # settings
    hdr, rows = _rows(sh['settings']) if 'settings' in sh else ([], [])
    settings = {h: _s(v) for h, v in zip(hdr, rows[0])} if rows else {}
    # choices
    choices = {}
    if 'choices' in sh:
        hdr, rows = _rows(sh['choices'])
        iL, iN, iE = _col(hdr, 'list_name'), _col(hdr, 'name'), _col(hdr, 'label::english', 'label')
        for r in rows:
            ln = _s(r[iL])
            if not ln: continue
            # option ids are kept as written (they are the values ODK stores); labels are cleaned
            choices.setdefault(ln, []).append({'id': re.sub(r'\s+', ' ', str(r[iN] or '')).strip(), 'label': _strip_html(_s(r[iE]))})
    # survey
    hdr, rows = _rows(sh['survey'])
    c = {k: _col(hdr, *v) for k, v in {
        'type': ['type'], 'name': ['name'], 'label': ['label::english', 'label'], 'hint': ['hint::english', 'hint'],
        'relevant': ['relevant'], 'required': ['required'], 'constraint': ['constraint'], 'calculation': ['calculation'],
        'read_only': ['read_only'], 'appearance': ['appearance']}.items()}
    g = lambda r, k: _s(r[c[k]]) if c[k] is not None and c[k] < len(r) else ''
    items, groups = [], []
    for r in rows:
        t = g(r, 'type'); name = g(r, 'name')
        if not t: continue
        base = t.split()[0]
        if base in META: continue
        if base in ('begin_group', 'begin', 'begin_repeat'):
            groups.append({'name': name, 'label': _strip_html(g(r, 'label')), 'relevant': g(r, 'relevant')}); continue
        if base in ('end_group', 'end', 'end_repeat'):
            if groups: groups.pop()
            continue
        q = {'name': name, 'type': base, 'label': _strip_html(g(r, 'label'))}
        if base in ('select_one', 'select_multiple'):
            parts = t.split()
            q['list'] = parts[1] if len(parts) > 1 else ''
            q['or_other'] = 'or_other' in parts
            q['options'] = list(choices.get(q['list'], []))
        for k in ('hint', 'relevant', 'constraint', 'calculation', 'appearance'):
            v = g(r, k)
            if v: q[k] = _strip_html(v) if k == 'hint' else v
        req = g(r, 'required').lower()
        q['required'] = req in ('yes', 'true', 'true()', '1')
        rel_g = [x['relevant'] for x in groups if x['relevant']]
        if rel_g: q['group_relevant'] = rel_g
        rel = [r for r in rel_g + [q.get('relevant', '')] if r]
        if rel: q['relevant_expr'] = ' and '.join(f'({odk_to_expr(r)})' for r in rel)
        if groups: q['group'] = ' / '.join(x['label'] or x['name'] for x in groups)
        hidden = q.get('relevant') == 'false()' or any(x == 'false()' for x in rel_g) or \
            g(r, 'read_only').lower() in ('yes', 'true', 'true()') or bool(q.get('calculation'))
        if hidden: q['hidden'] = True
        items.append(q)
    return {'settings': settings, 'questions': items}
