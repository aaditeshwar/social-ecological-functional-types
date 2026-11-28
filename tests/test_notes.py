from seft.util import load_json, knowledge_dir
from seft.notes_check import check_notes


def _vars(p):
    return {v['id'] for v in load_json(p)['variables']}


def test_intro_notes_valid():
    kd = knowledge_dir()
    dims = [d['id'] for d in load_json(kd / 'contexts.json')['dimensions']]
    assert check_notes(load_json(kd / 'notes.json'), ('mws', 'unit'), extra=_vars(kd / 'variables.json'), dims=dims) == []
    assert check_notes(load_json(kd / 'waterbody' / 'notes.json'), ('waterbody', 'unit'),
                       extra=_vars(kd / 'waterbody' / 'variables.json')) == []


def test_intro_notes_catch_errors():
    N = {'_fields': {'unit': {'n, area_ha': ''}},
         'unit': {'main': [{'when': 'n >', 'text': '{n}'}, {'when': 'n > 1', 'text': '{nope}'}], 'add': []}}
    errs = check_notes(N, ('unit',))
    assert any('unit.main[0]' in e for e in errs) and any("['nope']" in e for e in errs) and any('last rule' in e for e in errs)


def test_wb_dedupe_fallback_home_tehsil():
    from seft.wb.run import dedupe
    B = [{'wb_id': 1, 'district': 'D', 'tehsil': 'A', 'area_ha': 2, 'mws': {'mws_tehsil': 'B'}},
         {'wb_id': 1, 'district': 'D', 'tehsil': 'B', 'area_ha': 1, 'mws': {'mws_tehsil': 'B'}},
         {'wb_id': 2, 'district': 'D', 'tehsil': 'A', 'area_ha': 1, 'mws': {}},
         {'wb_id': 2, 'district': 'D', 'tehsil': 'C', 'area_ha': 3, 'mws': {}},
         {'wb_id': 3, 'district': 'D', 'tehsil': 'A', 'area_ha': 1, 'mws': {}}]
    out = dedupe(B, log=lambda m: None, shapes={})
    assert [(b['wb_id'], b['tehsil']) for b in out] == [(1, 'B'), (2, 'C'), (3, 'A')]


def test_wb_dedupe_by_boundary():
    from shapely.geometry import box
    from shapely.prepared import prep
    from seft.wb.run import dedupe
    S = {'D': {'A': prep(box(0, 0, 1, 1)), 'B': prep(box(1, 0, 2, 1)), 'X': prep(box(2, 0, 3, 1))}}
    B = [{'wb_id': 1, 'district': 'D', 'tehsil': 'A', 'centroid': [1.5, 0.5], 'area_ha': 1, 'mws': {}},
         {'wb_id': 1, 'district': 'D', 'tehsil': 'B', 'centroid': [1.5, 0.5], 'area_ha': 1, 'mws': {}},   # in B: keep B
         {'wb_id': 2, 'district': 'D', 'tehsil': 'A', 'centroid': [1.5, 0.2], 'area_ha': 1, 'mws': {}},   # only listed in A, lies in B: move
         {'wb_id': 3, 'district': 'D', 'tehsil': 'A', 'centroid': [2.5, 0.5], 'area_ha': 1, 'mws': {}},   # lies in X, not in the run: drop
         {'wb_id': 4, 'district': 'D', 'tehsil': 'A', 'centroid': [0.5, 0.5], 'area_ha': 1, 'mws': {}},
         {'wb_id': 5, 'district': 'D', 'tehsil': 'A', 'centroid': [9, 9], 'area_ha': 1, 'mws': {}}]       # outside all: keep
    out = dedupe(B, log=lambda m: None, shapes=S)
    assert [(b['wb_id'], b['tehsil']) for b in out] == [(1, 'B'), (2, 'B'), (4, 'A'), (5, 'A')]


def test_intro_render_matches_page_formatting():
    from seft.intro_notes import render, fmt, plain_label
    spec = {'main': [{'when': 'n == 0', 'text': 'none'}, {'when': 'true', 'text': '{unit_label_cap} has {n} ({x})'}],
            'add': [{'when': "status in ['r', 'n']", 'text': 'first wet {first_wet_year}.'}, {'when': 'missing > 1', 'text': 'never'}]}
    out = render(spec, {'unit_label_cap': 'Bid district', 'n': 127489, 'x': 10.25, 'status': 'r', 'first_wet_year': 2022})
    assert out == 'Bid district has 1,27,489 (10.3) first wet 2022.'
    assert fmt(0.58) == '0.6' and fmt(-4.2) == '-4.2' and plain_label('Semi-arid (< 900 mm)') == 'semi-arid'
    assert plain_label('VB-G RAM G scheme') == 'VB-G RAM G scheme'
