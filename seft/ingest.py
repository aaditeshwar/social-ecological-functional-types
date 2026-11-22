"""Parse get_tehsil_data responses (complete JSON or a body string cut at the
MCP size limit) and write one cache file per dataset.

Usage: python -m seft.ingest STATE DISTRICT TEHSIL response.json [...]
"""
import json, sys, datetime
from .util import raw_dir, dump_json

def _rows_from_truncated(s, name):
    """Recover complete rows of dataset `name` from a truncated JSON string."""
    key = '"%s": [' % name
    i = s.find(key)
    if i < 0:
        return None, False
    j = i + len(key)
    dec = json.JSONDecoder(); out = []
    while True:
        while j < len(s) and s[j] in ', \n':
            j += 1
        if j >= len(s):
            return out, False
        if s[j] == ']':
            return out, True
        try:
            o, j = dec.raw_decode(s, j)
        except ValueError:
            return out, False
        out.append(o)

NESTED = {'values', 'keys', 'features', 'village_details'}

def parse_response(obj):
    """Return {dataset: (rows, units, complete)} from one API response object."""
    body = obj.get('body', obj)
    res = {}
    if isinstance(body, str):
        import re
        names = re.findall(r'"([a-z_0-9]+)": \[\{', body)
        seen = []
        for n in names:
            if n in seen or n.endswith('_causality') or n in NESTED:
                continue
            seen.append(n)
        for n in seen:
            rows, complete = _rows_from_truncated(body, n)
            if rows is not None and (rows or complete):
                res[n] = (rows, {}, complete)
        return res
    data = body.get('data', {})
    td = data.get('tehsil_data', {}); tu = data.get('tehsil_units', {})
    for n, rows in td.items():
        res[n] = (rows, tu.get(n, {}), True)
    return res

def ingest(state, district, tehsil, paths, requested=None):
    d = raw_dir(state, district, tehsil)
    got = {}
    for p in paths:
        obj = json.load(open(p))
        if isinstance(obj, list):  # tool-result wrapper [{type,text}]
            obj = json.loads(obj[0]['text'])
        for n, (rows, units, complete) in parse_response(obj).items():
            prev = got.get(n)
            if prev and prev[2] and not complete:
                continue
            got[n] = (rows, units, complete)
    for n, (rows, units, complete) in got.items():
        dump_json({'dataset': n, 'state': state, 'district': district, 'tehsil': tehsil,
                   'complete': complete, 'n_rows': len(rows), 'units': units, 'rows': rows,
                   'fetched': datetime.date.today().isoformat(), 'source': 'get_tehsil_data'},
                  d / (n + '.json'))
    if requested:
        for n in requested:
            if n not in got and not (d / (n + '.json')).exists():
                dump_json({'dataset': n, 'complete': True, 'n_rows': 0, 'rows': [], 'units': {},
                           'note': 'absent from response (empty dataset)',
                           'fetched': datetime.date.today().isoformat(), 'source': 'get_tehsil_data'},
                          d / (n + '.json'))
    return {n: (len(v[0]), v[2]) for n, v in got.items()}

if __name__ == '__main__':
    s, di, t = sys.argv[1:4]
    print(ingest(s, di, t, sys.argv[4:]))
