"""Public notes for impact results, from the rules in knowledge/impact/notes.json.

Waterbody notes (`waterbody`, environment built by run.note_env)
  Placeholders: intervention_label_lower, year_label, type_label, type_label_plural, effect_signed, effect_abs,
    n_controls, radius_km, post_text, reason, volume_text, depth_text, flags_text, group_n, group_unit,
    group_mean_signed, group_label, group_placebo_text.
  Fields usable in `when`: verdict, has_volume, implausible, n_flags, group_n, group_concern (and any placeholder).

Unit notes for MWS / tehsil / district averages (`unit`, environment built by run.unit_stats)
  Placeholders: n, min_n, unit_label, intervention_label_lower, mean_signed, mean_abs, lo_signed, hi_signed,
    n_gain, n_loss, expected_each, placebo_abs, placebo_text.
  Fields usable in `when`: n, min_n, lo, hi, placebo_concern (and any placeholder).

The fixed panel text (`panel`) is not rendered here: it is copied into web impact.json and filled by the page
(impT in web/index.html); its placeholders are listed in `panel._placeholders`.
"""
from ..expr import evaluate
from ..util import load_json, knowledge_dir

def rules():
    return load_json(knowledge_dir() / 'impact' / 'notes.json')

class _Safe(dict):
    def __missing__(self, k): return '{' + k + '}'

def render(kind, env, R=None):
    R = R or rules(); spec = R[kind]; env = {**env, 'true': True, 'false': False}
    parts = []
    for r in spec['main']:
        try: ok = evaluate(r['when'], env)
        except Exception: ok = False
        if ok: parts.append(r['text'].format_map(_Safe(env))); break
    for r in spec.get('add', []):
        try: ok = evaluate(r['when'], env)
        except Exception: ok = False
        if ok: parts.append(r['text'].format_map(_Safe(env)))
    return ' '.join(parts)

def signed(x, n=1):
    return '–' if x is None else (f'+{x:.{n}f}' if x > 0 else f'{x:.{n}f}'.replace('-', '−'))

def years_text(ys):
    if not ys: return 'no years'
    lab = [f'{y}-{str(y + 1)[2:]}' for y in ys]
    return lab[0] if len(lab) == 1 else (', '.join(lab[:-1]) + ' and ' + lab[-1])
