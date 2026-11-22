"""Compare waterbody patterns with the Water Body Census fields matched to CoRE waterbodies.

The census fields are matched to CoRE waterbodies by proximity and by capacity against area, so they may not be
accurate, and they describe the census reference year (2017-18). They are used only to check patterns, not as
inputs. Run after wb-layers:  python tools/wb_census_compare.py
"""
import sys, json, gzip, pickle, collections, statistics as st, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seft.util import iter_locations, raw_dir, load_json, ROOT
from seft.wb.run import main as wb_run

def census_fields():
    C = {}
    for s, d, t in iter_locations(load_json(ROOT / 'config' / 'waterbody' / 'locations.json')):
        with gzip.open(raw_dir(s, d, t) / 'swb_layers.json.gz', 'rt', encoding='utf-8') as f:
            for w in json.load(f)['waterbodies']:
                if w.get('census_id') in (None, 'NA'): continue
                C[str(w.get('UID', w.get('wb_id')))] = w
    return C

B, _ = wb_run(log=lambda m: None)
C = census_fields()
J = []
for b in B:
    cs = [C[str(i)] for i in b['fragment_ids'] if str(i) in C]
    if cs: J.append((b, cs[0]))
scope={'river_reach','canal_fed','onstream_tank','small_onstream_pond','headwater_pond','village_pond','farm_pond'}
J=[(b,c) for b,c in J if b['type'] in scope]
def tf(x): return {'True':True,'1.0':True,'False':False,'0.0':False}.get(x)
def num(x):
    try: return float(x)
    except: return None
def trig(b,r): return b['rules'][r]['status']=='triggered'
def app(b,r): return b['rules'][r]['status'] in ('triggered','not triggered')
def rate(rows,r):
    a=[b for b,c in rows if app(b,r)]; return (len(a), round(100*sum(trig(b,r) for b in a)/len(a)) if a else None)
print('in-scope with census',len(J))
# 1 fill frequency vs our fill
print('\n1. Census fill frequency vs our kharif fill (regular waterbodies)')
for k in ('Filled up every year','Usually filled up','Rarely filled up','Never filled up'):
    rows=[(b,c) for b,c in J if c.get('filled_up_storage_space_name')==k]
    kf=[b['vars']['k_fill'] for b,c in rows if b['vars'].get('regular') and isinstance(b['vars'].get('k_fill'),(int,float))]
    yw=[b['vars']['years_wet'] for b,c in rows]
    print(f" {k}: n {len(rows)}, median years wet {st.median(yw) if yw else None}, median fill {round(st.median(kf)) if kf else None}%,",
          'inflow shortfall',rate(rows,'wb.inflow_shortfall'),'drought failure',rate(rows,'wb.drought_failure'),'stopped',rate(rows,'wb.sudden_loss'))
print('\n2. Census how full vs our fill')
for k in ('Full','Upto 3/4','Upto 1/2','Upto 1/4','Nil/Negligible filled up'):
    rows=[(b,c) for b,c in J if c.get('filled_up_storage_name')==k]
    kf=[b['vars']['k_fill'] for b,c in rows if isinstance(b['vars'].get('k_fill'),(int,float))]
    print(f" {k}: n {len(rows)}, median fill {round(st.median(kf)) if kf else None}%, inflow shortfall {rate(rows,'wb.inflow_shortfall')}")
print('\n3. In use / not in use, and reasons not in use')
for k in (True,False):
    rows=[(b,c) for b,c in J if tf(c.get('ref_water_body_in_use_id_name'))==k]
    print(f" in use={k}: n {len(rows)}", {r.split('.')[1]:rate(rows,r) for r in ('wb.sudden_loss','wb.siltation','wb.inflow_shortfall','wb.poor_retention')}, 'median years wet',st.median([b['vars']['years_wet'] for b,c in rows]))
for k,n in collections.Counter(c.get('scheme_status_reason_name') for b,c in J if c.get('scheme_status_reason_name')).most_common():
    rows=[(b,c) for b,c in J if c.get('scheme_status_reason_name')==k]
    print(f"  not-in-use reason {k}: n {n}", {r.split('.')[1]:rate(rows,r) for r in ('wb.sudden_loss','wb.siltation','wb.inflow_shortfall')}, 'years wet',st.median([b['vars']['years_wet'] for b,c in rows]))
print('\n4. Under repair / encroached')
for f in ('ref_water_body_under_repair_renovation_restoration_id_name','ref_selection_id_water_body_encroached_name'):
    for k in (True,False):
        rows=[(b,c) for b,c in J if tf(c.get(f))==k]
        print(f" {f.split('_id_')[-1] if '_id_' in f else f}={k}: n {len(rows)}", {r.split('.')[1]:rate(rows,r) for r in ('wb.sudden_loss','wb.siltation','wb.inflow_shortfall','wb.poor_retention')})
print('\n5. Storage present/original vs our shrinking signal')
pairs=[]
for b,c in J:
    o,p=num(c.get('storage_capacity_water_body_original')),num(c.get('storage_capacity_water_body_present'))
    if o and p is not None and o>0 and p<=o*1.5: pairs.append((p/o,b))
for lo,hi in ((0,0.5),(0.5,0.8),(0.8,1.01),(1.01,9)):
    rows=[(b,None) for r,b in pairs if lo<=r<hi]
    print(f" present/original {lo}-{hi}: n {len(rows)}", {r.split('.')[1]:rate(rows,r) for r in ('wb.siltation','wb.sudden_loss','wb.inflow_shortfall')})
print('\n6. Use reasons vs roles (mean role weight)')
roles=['role_irrigation','role_drought_protection','role_fishery','role_livestock','role_recharge_domestic']
uses=collections.Counter()
for b,c in J:
    us={c.get('ref_reason_water_body_in_use_id1_name'),c.get('reason_water_body_in_use_name2'),c.get('reason_water_body_in_use_name3')}-{None}
    for u in us: uses[u]+=1
for u,n in uses.most_common(6):
    yes=[b for b,c in J if u in {c.get('ref_reason_water_body_in_use_id1_name'),c.get('reason_water_body_in_use_name2'),c.get('reason_water_body_in_use_name3')}]
    no=[b for b,c in J if u not in {c.get('ref_reason_water_body_in_use_id1_name'),c.get('reason_water_body_in_use_name2'),c.get('reason_water_body_in_use_name3')}]
    print(f" {u} (n {n}):", {r.split('_',1)[1]:(round(st.mean(b['roles'][r] for b in yes),2), round(st.mean(b['roles'][r] for b in no),2)) for r in roles})
print('\n7. Census type vs our type')
ct=collections.defaultdict(collections.Counter)
for b,c in J: ct[c.get('ref_water_body_type_id_name')][b['type']]+=1
for k,v in ct.items(): print(' ',k,dict(v.most_common()))
print('\n8. Fishery: pisciculture use vs fishery rules')
for k in (True,False):
    rows=[(b,c) for b,c in J if ('Pisciculture' in {c.get('ref_reason_water_body_in_use_id1_name'),c.get('reason_water_body_in_use_name2'),c.get('reason_water_body_in_use_name3')})==k]
    print(f" pisciculture={k}: n {len(rows)}", {r.split('.')[1]:rate(rows,r) for r in ('wb.fishery_opportunity','wb.fishery_constraint')}, 'kr mean',round(st.mean(b['vars']['kr_mean'] or 0 for b,c in rows)))
print('\n9. WUA exists vs water not reaching fields')
for k in ('Yes','No','Not Known'):
    rows=[(b,c) for b,c in J if c.get('ref_selection_id_wua_exists_name')==k]
    print(f" WUA {k}: n {len(rows)}", rate(rows,'wb.irrigation_underuse'))
