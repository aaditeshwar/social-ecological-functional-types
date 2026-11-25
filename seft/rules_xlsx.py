"""`python -m seft.cli rules-xlsx --v1 WaterStructure_Suitability_Rules.xlsx [--out FILE]`: the site rules of
knowledge/interventions.json written back into the layout of the CoRE Stack suitability-rules workbook.

Sheets: RULES (the workbook's structures and parameters with the current values, their basis, sources and notes),
SOURCES, ABOUT. Site layers only; landscape rules
(suits / avoid) stay in the interventions file. Structures the catalogue does not cover (Well, Canal, Large Water
Body) are taken from the input workbook as 'not reviewed'.
"""
import json, re
from pathlib import Path
from .util import ROOT

def main(src, out=None, log=print):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    out = Path(out or ROOT / 'out' / 'WaterStructure_Suitability_Rules_v2.xlsx'); out.parent.mkdir(parents=True, exist_ok=True)
    I=json.load(open(ROOT / 'knowledge' / 'interventions.json',encoding='utf-8')); IV={x['id']:x for x in I['interventions']}
    S={s['id']:s for s in json.load(open(ROOT / 'knowledge' / 'sources.json',encoding='utf-8'))['sources']}
    ws0=openpyxl.load_workbook(src)['RULES']
    orig=[]; cur=None
    for r in range(4,ws0.max_row+1):
        a,b=ws0.cell(r,1).value,ws0.cell(r,2).value
        if a: cur=a.strip()
        if b: orig.append((cur,b.strip(),*(ws0.cell(r,c).value for c in range(3,7))))
    MAP={'Check Dam':'check_dam','Farm Pond':'farm_pond','Farm Bund':'contour_graded_bunds','30-40 Model Structure':'model_30_40',
     'Soakage Pits':'recharge_pits_shafts','Rock Fill Dam':'gabion_rockfill','Diversion Drains':'diversion_drain','Drainage Soakage Channels':'diversion_drain',
     'Percolation Tank':'percolation_tank','Recharge Pits':'recharge_pits_shafts','Community Pond':'community_pond','Contour Bund':'contour_graded_bunds',
     'Graded Bund':'contour_graded_bunds','Stone Bunding':'stone_bunding','Earthen Gully Plug':'earthen_gully_plug','Trench cum Bund Network':'trench_cum_bund',
     'Loose Boulder Structure':'loose_boulder_check','Continuous Contour Trenches (CCT)':'cct','Staggered Contour Trenches (SCT)':'sct',
     'Water Absorption Trenches (WAT)':'wat','5% Model Structure':'five_percent_model'}
    PMAP={'Slope':'Slope','Stream Order':'Stream order','Catchment Area':'Catchment area','Drainage Distance':'Distance to drainage line','LULC':'Land use'}
    def ours(iid,struct,p):
        rows=IV[iid]['site_rules']; want=PMAP.get(p,p)
        if iid=='contour_graded_bunds':
            if want=='Slope': want='Slope (contour bund)' if struct=='Contour Bund' else 'Slope (graded bund)'
            if want=='Land use': want='Land use (farm bund)'
        if iid=='recharge_pits_shafts' and want=='Land use': want='Land use (recharge pits)'
        return next((r for r in rows if r['parameter']==want),None)
    norm=lambda x: re.sub(r'\s+','',str(x or '')).replace('–','-').replace('hectares','ha').lower()
    order=[]; [order.append(s) for s,*_ in orig if s not in order]
    rows=[]
    for st in order:
        iid=MAP.get(st); used=set()
        for s,p,unit,a,pa,n in [o for o in orig if o[0]==st]:
            r=ours(iid,st,p) if iid else None
            if r is None:
                rows.append(dict(st=st,p=p,unit=unit,a=a,pa=pa,n=n,basis='not reviewed' if not iid else 'not sourced',src='',note='Structure not in the interventions catalogue yet.' if not iid else '')); continue
            used.add(r['parameter'])
            if r['basis']=='not sourced':
                rows.append(dict(st=st,p=p,unit=unit,a=a,pa=pa,n=n,basis='not sourced',src='',note=r.get('note',''))); continue
            rows.append(dict(st=st,p=p,unit=unit,a=r['accepted'],pa=r['partial'],n=r['not_accepted'],basis=r['basis'],src='; '.join(S[x]['citation'].split(').')[0]+')' for x in r.get('sources',[]) if x in S and x!='structure_rules'),note=r.get('note','')))
        if iid:   # rows we added (soil, distance where the sheet had none)
            for r in IV[iid]['site_rules']:
                if r['parameter'] in used or r['basis'] not in ('source','proposed'): continue
                if iid=='contour_graded_bunds' and ((st=='Contour Bund' and 'graded' in r['parameter']) or (st=='Graded Bund' and 'contour bund' in r['parameter']) or (st!='Farm Bund' and 'farm bund' in r['parameter'])): continue
                if iid=='contour_graded_bunds' and st=='Farm Bund' and r['parameter'].startswith('Slope'): continue
                if iid=='recharge_pits_shafts' and r['parameter'].startswith('Land use'): continue
                if iid=='diversion_drain': continue
                rows.append(dict(st=st,p=r['parameter'].replace(' (Commons Connect classes)',''),unit=r.get('unit',''),a=r['accepted'],pa=r['partial'],n=r['not_accepted'],basis=r['basis'],src='; '.join(S[x]['citation'].split(').')[0]+')' for x in r.get('sources',[]) if x in S and x!='structure_rules'),note=r.get('note','')))
    wb=openpyxl.Workbook(); ws=wb.active; ws.title='RULES'
    navy=PatternFill('solid',fgColor='1F3864'); blue=PatternFill('solid',fgColor='2E75B6')
    fills={'D':'C6EFCE','E':'FFEB9C','F':'FFC7CE'}; bfill={'source':'FFFFFF','proposed':'E2EFDA','not sourced':'F2F2F2','not reviewed':'F2F2F2'}
    thin=Side(style='thin',color='BFBFBF'); B=Border(left=thin,right=thin,top=thin,bottom=thin)
    H=['Structure','Parameter','Unit','✔  Accepted','▲  Partially Accepted','✖  Not Accepted','Basis','Sources','Notes']
    ws['A1']='WATER STRUCTURES — SUITABILITY RULES (site layers), 25 November 2026'; ws['A1'].font=Font(bold=True,size=13,color='FFFFFF'); ws['A1'].fill=navy; ws.merge_cells('A1:I1')
    ws['A2']='  ✔ ACCEPTED  —  Ideal site conditions        ▲ PARTIALLY ACCEPTED  —  Works with caution        ✖ NOT ACCEPTED  —  Unsuitable.   Site layers only (slope, stream order raster, catchment, distance to drainage line, land use, soil); landscape rules (rainfall, aquifer, groundwater stage, depth to water) are in the atlas.'
    ws.merge_cells('A2:I2'); ws['A2'].alignment=Alignment(wrap_text=True); ws.row_dimensions[2].height=30
    for i,h in enumerate(H,1):
        c=ws.cell(3,i,h); c.font=Font(bold=True,color='FFFFFF'); c.fill=blue; c.alignment=Alignment(wrap_text=True,vertical='center'); c.border=B
    r0=4; prev=None; start=None
    for x in rows:
        if prev is not None and x['st']!=prev:
            if r0-1>start: ws.merge_cells(start_row=start,start_column=1,end_row=r0-1,end_column=1)
            r0+=1
        if x['st']!=prev: start=r0; ws.cell(r0,1,x['st']).font=Font(bold=True)
        vals=[None,x['p'],x['unit'],x['a'],x['pa'],x['n'],x['basis'],x['src'],x['note']]
        for i,v in enumerate(vals,1):
            c=ws.cell(r0,i) if i==1 else ws.cell(r0,i,v); c.alignment=Alignment(wrap_text=True,vertical='top'); c.border=B
            L=get_column_letter(i)
            if L in fills: c.fill=PatternFill('solid',fgColor=fills[L])
            if L=='G': c.fill=PatternFill('solid',fgColor=bfill.get(x['basis'],'FFFFFF')); c.font=Font(bold=x['basis']=='proposed')
        prev=x['st']; r0+=1
    if r0-1>start: ws.merge_cells(start_row=start,start_column=1,end_row=r0-1,end_column=1)
    for L,w in zip('ABCDEFGHI',(22,22,9,30,30,28,12,40,60)): ws.column_dimensions[L].width=w
    ws.freeze_panes='C4'
    # SOURCES
    ss=wb.create_sheet('SOURCES'); ss.append(['Id','Citation','Link','Used for'])
    for c in ss[1]: c.font=Font(bold=True,color='FFFFFF'); c.fill=blue
    used=sorted({s for x in I['interventions'] for r in x.get('site_rules',[]) for s in r.get('sources',[])})
    for k in used:
        s=S[k]; ss.append([k,s['citation'],s.get('url',''),s.get('used_for','')])
    for L,w in zip('ABCD',(24,70,50,80)): ss.column_dimensions[L].width=w
    for row in ss.iter_rows(min_row=2):
        for c in row: c.alignment=Alignment(wrap_text=True,vertical='top')
    # ABOUT
    ab=wb.create_sheet('ABOUT')
    txt=["CoRE Stack water structures suitability rules (site layers), 25 November 2026, with the published manuals and papers behind them (SOURCES sheet).",
    "Basis: source = a published manual or paper gives the value; proposed = reasoned from the sources where none gives a number (review before use); not sourced = no published source found; not reviewed = structure not yet in the interventions catalogue.",
    "Stream order is the CoRE Stack stream order raster: every 30 m pixel carries the Strahler order of the drainage line it drains into. For structures built across a drainage line (check dams, gully plugs, boulder checks, gabions, percolation tanks) read it on the line, where it is the line's own order. For area treatments and ponds on farmland it places the land in the ridge-to-valley sequence.",
    "Soil is not yet a CoRE Stack layer; the classes are those of the Commons Connect forms (Black, Red, Laterite, Alluvial, Sandy, Clay, Rocky), recorded by the field worker.",
    "Landscape rules (rainfall, aquifer type, groundwater stage, depth to water after the monsoon) are not in this sheet: they decide whether an intervention suits the micro-watershed and are kept in knowledge/interventions.json (suits / avoid) in the social-ecological-functional-types repository. Depth to water is asked of the community until a layer exists.",
    "Generated from knowledge/interventions.json by `python -m seft.cli rules-xlsx`; Well, Canal and Large Water Body are taken from the input workbook as they are."]
    for i,t in enumerate(txt,1):
        c=ab.cell(i,1,t); c.alignment=Alignment(wrap_text=True,vertical='top')
    ab.column_dimensions['A'].width=130
    wb.save(out)
    log(f"wrote {out}: {len(rows)} rows")
    return out
