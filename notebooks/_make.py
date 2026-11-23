"""Write the four sample notebooks. Run: python notebooks/_make.py"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def nb(cells):
    out = []
    for c in cells:
        if c.startswith('#'):
            out.append({'cell_type': 'markdown', 'metadata': {}, 'source': [x + '\n' for x in c.split('\n')]})
        else:
            src = [x + '\n' for x in c.split('\n')]
            if src:
                src[-1] = src[-1].rstrip('\n')
            out.append({'cell_type': 'code', 'execution_count': None, 'metadata': {}, 'outputs': [], 'source': src})
    return {
        'nbformat': 4, 'nbformat_minor': 5,
        'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
                     'language_info': {'name': 'python'}},
        'cells': out,
    }


def write(name, cells):
    p = HERE / name
    p.write_text(json.dumps(nb(cells), indent=1), encoding='utf-8')
    print(p)


write('01_analyse_mws.ipynb', [
    '# Analyse a micro-watershed\n\nUses the cached Godda district in this repo (`data/`). No network if that cache is present.',
    '''from pathlib import Path
from core_seft import Session

ROOT = Path("..").resolve()
s = Session(data_dir=ROOT / "data", knowledge_dir=ROOT / "knowledge")
r = s.analyse("mws", state="Jharkhand", district="Godda", uid="12_313813", fetch=False)
print(r.identity)
print("mix", r.mix["dominant"], r.mix["shares"])
print("context", r.context)
print("notes", [n["id"] for n in r.notes])
print("schemes", [x["name"] for x in r.schemes[:8]])
print("interventions", [(x["fit"], x["name"]) for x in r.interventions[:8]])
print("knowledge", r.knowledge_version, "library", r.library_version)''',
    '''r2 = s.analyse("mws", state="Jharkhand", district="Godda", uid="12_313813",
               answers={"sys_irrigated_share": "low"}, fetch=False)
print("answers", r2.answers_applied)
print("diff", r2.diff)
print("mix after", r2.mix["dominant"])
print("interventions after", [(x["fit"], x["name"]) for x in r2.interventions[:8]])''',
])

write('02_analyse_waterbody.ipynb', [
    '# Analyse a waterbody\n\nNeeds watershed datasets **and** `swb_layers.json.gz` for Godda in `data/raw`.',
    '''from pathlib import Path
from core_seft import Session

ROOT = Path("..").resolve()
s = Session(data_dir=ROOT / "data", knowledge_dir=ROOT / "knowledge")
r = s.analyse("waterbody", state="Jharkhand", district="Godda", uid="9628377", fetch=False)
print(r.identity)
print("type", r.type, "status", r.status)
print("roles", r.roles)
print("home mix", (r.mix or {}).get("dominant"))
print("home context", r.context)
print("notes", [n["id"] for n in r.notes])
print("schemes", [x["name"] for x in r.schemes[:8]])
print("interventions", [(x["fit"], x["name"]) for x in r.interventions[:8]])''',
])

write('03_district_and_tehsil.ipynb', [
    '# District then tehsil\n\nNo community answers. Tehsil rows on the district result are a drill-down list.',
    '''from pathlib import Path
from core_seft import Session

ROOT = Path("..").resolve()
s = Session(data_dir=ROOT / "data", knowledge_dir=ROOT / "knowledge")
d = s.analyse("district", state="Jharkhand", district="Godda", fetch=False)
print(d.identity)
print("mix", d.mix)
print("context", d.context)
print("top interventions", d.interventions[:8])
print("tehsils", d.tehsils)
t = s.analyse("tehsil", state="Jharkhand", district="Godda", tehsil="Basantrai", fetch=False)
print("tehsil mix", t.mix["dominant"], "n_mws", t.identity["n_mws"])
print("questions", t.questions)''',
])

write('04_fetch_and_knowledge.ipynb', [
    '# Fetch-on-miss and knowledge version\n\n`fetch=False` raises `CacheMiss` when the district is not in `data_dir`. Keep `CORE_STACK_API_KEY` in the environment; do not put it in this file.',
    '''from pathlib import Path
import tempfile
from core_seft import Session, CacheMiss

ROOT = Path("..").resolve()
empty = tempfile.mkdtemp()
s = Session(data_dir=empty, knowledge_dir=ROOT / "knowledge")
try:
    s.analyse("district", state="Jharkhand", district="Godda", fetch=False)
except CacheMiss as e:
    print("miss:", e)

s2 = Session(data_dir=ROOT / "data", knowledge_dir=ROOT / "knowledge")
r = s2.analyse("mws", state="Jharkhand", district="Godda", uid="12_313813", fetch=False)
print("knowledge_version", r.knowledge_version, "library_version", r.library_version)
# s2.refresh_knowledge()   # copies the bundled pack into data_dir/knowledge
# Needs CORE_STACK_API_KEY and the network:
# s.analyse("district", state="Jharkhand", district="Godda", fetch=True)''',
])
