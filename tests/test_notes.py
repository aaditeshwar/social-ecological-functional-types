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


def test_wb_dedupe_prefers_home_tehsil():
    from seft.wb.run import dedupe
    B = [{'wb_id': 1, 'tehsil': 'A', 'area_ha': 2, 'mws': {'mws_tehsil': 'B'}},
         {'wb_id': 1, 'tehsil': 'B', 'area_ha': 1, 'mws': {'mws_tehsil': 'B'}},
         {'wb_id': 2, 'tehsil': 'A', 'area_ha': 1, 'mws': {}},
         {'wb_id': 2, 'tehsil': 'C', 'area_ha': 3, 'mws': {}},
         {'wb_id': 3, 'tehsil': 'A', 'area_ha': 1, 'mws': {}}]
    out = dedupe(B, log=lambda m: None)
    assert [(b['wb_id'], b['tehsil']) for b in out] == [(1, 'B'), (2, 'C'), (3, 'A')]
