"""Build knowledge/commons_connect.json: a structured local version of the Commons Connect forms.

`python -m seft.cli cc-build --forms <folder with the ODK .xlsx templates>` reads the templates (seft.odk), keeps the
English labels, options, relevance and required flags, and adds, for every question:
  role         'inform' (the answer says something about the landscape, a resource or a plan) or 'record' (names,
               beneficiary details, dimensions, photos, locations, identifiers): records are always kept, not scored
  atlas_match  the atlas questions it overlaps: {atlas: 'ws'|'wb', id, how: 'same'|'derived'|'overlap', map/bins}.
               'same' and 'derived' answers are passed to the atlas (so the inference is updated as the field worker
               goes); 'overlap' means the questions cover related ground but one cannot be read off the other
  must_ask     a rule for the must-ask score (0-100): base, atlas weight and conditions (seft.priority)
  prefill      the answer the atlas expects, for the field worker to confirm instead of asking from scratch
The landscape section (Landscape Description Forms.docx, not yet an ODK form) and the forest forms (Word only) are
written out here by hand, and atlas questions missing from the landscape form are added to it.
"""
import json
from pathlib import Path
from .util import ROOT

# ---------------------------------------------------------------- forms and their place in the flow
FORMS = [
    dict(id='landscape', title='Landscape description', section='landscape', step='Landscape', unit='mws',
         doc='Landscape Description Forms.docx', odk=None,
         about='Proposed new first step, before resource mapping: community questions about the landscape, arranged by '
               'production system and causal pathway. The atlas inference is shown first; the field worker confirms it '
               'and asks the questions whose answers are likely to change it.'),
    dict(id='settlement', title='Settlements', section='resource_mapping', step='Settlements', unit='settlement',
         doc='Add Settlements Form.docx', odk='Add_Settlements_form _V1.0.1.xlsx',
         about='One form per settlement (hamlet or tola), filled during the transect walk.'),
    dict(id='waterbody', title='Water structures', section='resource_mapping', step='Waterbodies', unit='waterbody',
         doc='Add Water Structures Form.docx', odk='Add_Waterbodies_Form_V1.0.3.xlsx',
         about='One form per water structure. Structures detected from satellite data appear on the Commons Connect map; '
               'the waterbody atlas gives their type and likely stresses.'),
    dict(id='well', title='Wells', section='resource_mapping', step='Wells', unit='well',
         doc='Add Well Form.docx', odk='Add_well_form_V1.0.1.xlsx', about='One form per well, hand pump or borewell.'),
    dict(id='crop', title='Cropping pattern', section='resource_mapping', step='Crops', unit='crop_patch',
         doc='Cropping Pattern Form.docx', odk='crop_form_V1.0.0.xlsx', about='One form per farm patch (crop grid cell).'),
    dict(id='forest_patch', title='Forest patch mapping (CFR)', section='resource_mapping', step='Forest patches',
         unit='forest_patch', doc='Resource ForestQuestionnaire.docx', odk=None,
         about='Word draft, not yet an ODK form: one form per forest patch the settlements use.'),
    dict(id='recharge_new', title='Propose new recharge structure', section='planning', group='groundwater_recharge',
         kind='new', unit='work', doc='Propose New Recharge Structure.docx',
         odk='NRM_form_propose_new_recharge_structure_V1.0.0.xlsx'),
    dict(id='recharge_maintenance', title='Maintenance of existing recharge structures', section='planning',
         group='groundwater_recharge', kind='maintenance', unit='work',
         doc='Propose Maintenance On Existing Water Recharge Structure.docx',
         odk='Propose_Maintenance_on_Existing_Water_Recharge_Structures_V1.1.1.xlsx'),
    dict(id='surface_maintenance', title='Maintenance of surface water structures', section='planning',
         group='surface_waterbody', kind='maintenance', unit='work', doc='Propose Maintenance on Surface Water structure.docx',
         odk='NRM_form_NRM_form_Waterbody_Screen_V1.0.0.xlsx'),
    dict(id='surface_maintenance_rs', title='Maintenance of remotely sensed water structures', section='planning',
         group='surface_waterbody', kind='maintenance', unit='work',
         doc='Propose Maintenance on  Remote Sensed Surface Water structure.docx',
         odk='PM_Remote_Sensed_Surface_Water_structure_V1.0.0.xlsx',
         about='The same questions as the surface water maintenance form, for a structure already on the map from '
               'satellite data (the waterbody atlas record).'),
    dict(id='irrigation_new', title='Propose new irrigation work', section='planning', group='irrigation',
         kind='new', unit='work', doc='Propose New Irrigation Work.docx', odk='NRM_form_Agri_Screen_V1.0.0.xlsx'),
    dict(id='irrigation_maintenance', title='Maintenance of existing irrigation structures', section='planning',
         group='irrigation', kind='maintenance', unit='work', doc='Propose Maintenance On Existing Irrigation Structure.docx',
         odk='Propose_Maintenance_on_Existing_Irrigation_Structures_V1.1.1.xlsx'),
    dict(id='agrohorticulture', title='Agroforestry and orchards', section='planning', group='agroforestry',
         kind='new', unit='work', doc='Agro Horticulture.docx', odk='Agrohorticulture.xlsx',
         about='Commons Connect has no maintenance form for plantations; survival and gap filling are planned again '
               'through this form.'),
    dict(id='livelihood', title='Livelihoods: livestock, kitchen gardens, fisheries', section='planning',
         group='livelihood', kind='new', unit='work', doc='NRM Livelihood Form.docx', odk='NRM Livelihood Form.xlsx'),
    dict(id='forest_planning', title='Forest patch planning', section='planning', group='forest', kind='new',
         unit='work', doc='Planning ForestQuestionnaire.docx', odk=None, about='Word draft, not yet an ODK form.'),
]
PLAN_GROUPS = [
    ('groundwater_recharge', 'Groundwater recharge'), ('surface_waterbody', 'Surface waterbodies (maintenance; new ones are proposed as recharge or irrigation works)'),
    ('irrigation', 'Irrigation on farms'), ('agroforestry', 'Agroforestry and orchards'),
    ('livelihood', 'Livelihoods (cattle and goat sheds, fisheries)'), ('forest', 'Forests')]

SECTIONS = [
    ('landscape', 'Landscape', 'What the atlas infers about the micro-watershed, confirmed with the community.'),
    ('resource_mapping', 'Resource mapping', 'Transect walk: settlements, waterbodies, wells, crops and forest patches.'),
    ('planning', 'Planning', 'Demands for new works and for maintenance, ranked by what suits this landscape.'),
]

# ---------------------------------------------------------------- helpers to write questions
def O(*pairs):
    return [{'id': i, 'label': l} for i, l in pairs]

YND = O(('yes', 'Yes'), ('no', 'No'), ('dk', "Don't know"))

def am(id, how='same', atlas='ws', map=None, bins=None, value=None, note=None):
    d = {'atlas': atlas, 'id': id, 'how': how}
    if map: d['map'] = map
    if bins: d['bins'] = bins
    if value: d['value'] = value
    if note: d['note'] = note
    return d

def M(base=None, rules=None, why=None):
    d = {}
    if base is not None: d['base'] = base
    if rules: d['rules'] = [{'if': r[0], 'score': r[1], 'why': r[2], **({'mode': r[3]} if len(r) > 3 else {})} for r in rules]
    if why: d['why'] = why
    return d

def P(*rules):
    """prefill rules: (condition, option id or list of ids, why)."""
    return [{'if': c, ('values' if isinstance(v, list) else 'value'): v, 'why': w} for c, v, w in rules]

def L(id, text, type='select_one', options=None, relevant=None, atlas=None, must=None, prefill=None, routes=None,
      note=None, from_atlas=None, origin='doc', sets_var=None, relevant_expr=None):
    q = {'name': id, 'type': type, 'label': text, 'role': 'inform', 'origin': origin}
    if options is not None: q['options'] = options
    if relevant: q['relevant'] = relevant
    if from_atlas: q['from_atlas'] = from_atlas
    if atlas: q['atlas_match'] = atlas if isinstance(atlas, list) else [atlas]
    if must: q['must_ask'] = must
    if prefill: q['prefill'] = prefill
    if routes: q['routes'] = routes
    if note: q['note'] = note
    if sets_var: q['sets_var'] = sets_var
    return q

def A(atlas_id, relevant=None, must=None, prefill=None, note=None, atlas='ws'):
    """A landscape (or waterbody) question added from the atlas: text and options are copied when the file is built."""
    return L(('ls_' if atlas == 'ws' else 'wbx_') + atlas_id, None, from_atlas=[atlas, atlas_id], relevant=relevant,
             atlas=am(atlas_id, 'same', atlas), must=must, prefill=prefill, note=note, origin='atlas')

POS = lambda *ids: ' or '.join(f"nz(pos_{i.replace('.', '__')}) == 1" for i in ids)

# ---------------------------------------------------------------- landscape section (Landscape Description Forms.docx)
LANDSCAPE = [
  dict(id='s1', title='Socio-economic vulnerability', production_system='socio_economic',
       pathways=['multidimensional_vulnerability', 'drinking_water'], questions=[
    L('ls_1_1', 'What are the main socio-economic difficulties faced by households in this village?', 'select_multiple', O(
        ('employment', 'Limited local employment or livelihood opportunities'),
        ('schemes', 'Difficulty accessing government employment schemes, including MGNREGA/VB-G RAM G'),
        ('finance', 'Difficulty accessing banks, loans or financial services'),
        ('education', 'Limited access to education, literacy or skill development'),
        ('shg', 'Limited participation in Self-Help Groups (SHGs) or community groups'),
        ('social', 'Social barriers affecting access to employment, schemes, land, forests, water or other common resources'),
        ('income', 'Low or uncertain household income'), ('other', 'Other'), ('dk', "Don't know")),
      atlas=[am('bank_access', 'overlap', note="'Difficulty accessing banks' covers the same ground as bank_access"),
             am('income', 'overlap')],
      must=M(45, [(POS('multidimensional_vulnerability'), 65, 'several kinds of disadvantage are likely to overlap here; the answer shows which ones to plan for')]),
      prefill=P((POS('multidimensional_vulnerability'), ['employment', 'income'], 'the vulnerability index is high'))),
    L('ls_1_2', 'Can households access MGNREGA/VB-G RAM G employment when they need it?', 'select_one', O(
        ('yes', 'Yes, generally'), ('partly', 'Partly; work is available only sometimes'), ('no', 'No, access is difficult'),
        ('dk', "Don't know / not applicable")),
      atlas=am('nrega_work', 'same', map={'yes': 'good', 'partly': 'partial', 'no': 'none'})),
    L('ls_1_2a', 'What are the main difficulties?', 'select_multiple', O(
        ('work', 'Not enough work available'), ('wages', 'Delays in receiving wages'),
        ('jobcard', 'Difficulty applying for work or accessing job cards'), ('info', 'Lack of information or support'),
        ('other', 'Other')), relevant="ls_1_2 == 'partly' or ls_1_2 == 'no'", must=M(45)),
    L('ls_1_3', 'Do Scheduled Caste (SC), Scheduled Tribe (ST) or other socially marginalised communities face barriers in accessing employment, services, government schemes or common resources?',
      'select_one', O(('yes', 'Yes'), ('no', 'No'), ('dk', "Don't know / prefer not to say")),
      must=M(35, [('nz(st_share) + nz(sc_share) >= 0.3', 65, 'SC and ST households are a large share of the population here')]),
      note='If yes, note the barriers in a few words.'),
    L('ls_1_4', 'Are women and other community members able to participate in active SHGs or other community groups?', 'select_one', O(
        ('wide', 'Yes, participation is widespread'), ('limited', 'Some groups exist, but participation is limited'),
        ('few', 'Few or no active groups are available'), ('dk', "Don't know")),
      atlas=am('shg_membership', 'derived', map={'wide': 'most', 'limited': 'some', 'few': 'few'},
               note='shg_membership asks for the share of households; the bands correspond roughly')),
    L('ls_1_4a', 'If participation is limited, what are the main reasons?', 'select_multiple', O(
        ('few', 'Few groups exist or groups are inactive'), ('aware', 'Limited awareness or support'),
        ('excluded', 'Some community members are excluded'), ('other', 'Other')),
      relevant="ls_1_4 == 'limited' or ls_1_4 == 'few'", must=M(35)),
    L('ls_1_5', 'Compared with 5–10 years ago, how has access to employment, banking, education and community support changed?', 'select_one', O(
        ('much', 'Improved significantly'), ('some', 'Improved somewhat'), ('same', 'No major change'), ('worse', 'Worsened'),
        ('dk', "Don't know")), must=M(25, why='context for the plan; no atlas rule reads it')),
    L('ls_1_6', 'Do people migrate outside the village for work or livelihood opportunities?', 'select_one', O(
        ('many', 'Many households'), ('some', 'Some households'), ('few', 'Very few or none'), ('dk', "Don't know")),
      atlas=am('migration', 'derived', map={'many': 'high', 'some': 'moderate', 'few': 'low'})),
    L('ls_1_6a', 'What are the main reasons for migration?', 'select_multiple', O(
        ('employment', 'Lack of local employment'), ('farm_income', 'Low or uncertain agricultural income'),
        ('water', 'Water scarcity, drought or other environmental stresses'), ('wages', 'Low wages or irregular work'),
        ('credit', 'Limited access to credit or livelihood support'), ('education', 'Education or better opportunities elsewhere'),
        ('other', 'Other')), relevant="ls_1_6 == 'many' or ls_1_6 == 'some'",
      must=M(40, [(POS('drought.kharif_drought', 'groundwater.over_extraction'), 55, 'water stress is likely; the answer shows whether it drives migration')])),
    L('ls_1_7', 'What improvements would help young people build their livelihoods locally?', 'select_multiple', O(
        ('employment', 'More local employment opportunities'), ('agri', 'Better agriculture and allied livelihood opportunities'),
        ('skills', 'Vocational training and skill development'), ('credit', 'Easier access to credit and government schemes'),
        ('enterprise', 'Support for small businesses and entrepreneurship'), ('resources', 'Better access to productive resources'),
        ('other', 'Other')), must=M(30, why='context for the plan')),
    A('landholding'), A('income'), A('bank_access'),
    A('drinking_summer'), A('drinking_water_quality'), A('jjm_taps'),
    A('mining_water', must=M(None, [('nz(mining_projects) == 0', 5, 'no mines are recorded near this micro-watershed', 'set')])),
  ]),
  dict(id='s2', title='Agriculture and farming', production_system='agriculture',
       pathways=['groundwater', 'drought', 'irrigation', 'soil', 'productivity', 'waterbody_shrinkage'], questions=[
    L('ls_2_1', 'Is farming an important livelihood in this area?', 'select_one', YND,
      must=M(None, [('f_crop >= 0.3', 10, 'farmland covers much of the micro-watershed: confirm and move on'),
                    ('f_crop < 0.3 and f_crop >= 0.1', 55, 'farmland is a modest share; the answer decides whether to ask the farming questions'),
                    ('f_crop < 0.1', 35, 'little farmland is mapped here')]),
      prefill=P(('f_crop >= 0.2', 'yes', 'farmland covers at least a fifth of the micro-watershed'),
                ('f_crop < 0.05', 'no', 'hardly any farmland is mapped'))),
    L('ls_2_2', 'Which problems are farmers experiencing?', 'select_multiple', O(
        ('water', 'Not enough water for crops'), ('yield', 'Crop yields are low or have declined'),
        ('failure', 'Crops have failed or been lost'), ('price', 'Difficulty getting a good price or selling produce'),
        ('other', 'Other')), relevant="ls_2_1 != 'no'", routes=['ls_2_3', 'ls_2_9', 'ls_2_10'],
      prefill=P((POS('groundwater.over_extraction', 'drought.kharif_drought', 'irrigation.rabi_water_shortfall', 'groundwater.water_balance_deficit'), ['water'], 'a water-security stress is likely'),),
      note='A routing question: its score is the highest score of the questions it leads to.'),
    L('ls_2_3', 'What may be causing the water shortage?', 'select_multiple', O(
        ('drought', 'Drought or poor rainfall'), ('groundwater', 'Groundwater levels are falling'),
        ('irrigation', 'Irrigation is insufficient, unreliable or too costly'), ('rainfed', 'Most farming depends on rainfall'),
        ('other', 'Other'), ('dk', "Don't know")), relevant="'water' in ls_2_2",
      routes=['ls_2_4', 'ls_2_5', 'ls_2_6', 'ls_2_7', 'ls_2_8', 'ls_kharif_dry_spells'],
      prefill=P((POS('groundwater.over_extraction', 'groundwater.water_balance_deficit'), ['groundwater'], 'groundwater stress is likely'),
                (POS('drought.kharif_drought'), ['drought'], 'kharif drought is likely'))),
    L('ls_2_4', 'Have wells or borewells become deeper over the past 5–10 years, or have shallow wells dried up?', 'select_one', O(
        ('same', 'Water levels are roughly unchanged'), ('deeper', 'Wells have become more than 2–3 metres deeper'),
        ('dried', 'Shallow wells or springs have dried up, permanently or for longer periods'), ('dk', "Don't know")),
      relevant="'groundwater' in ls_2_3", atlas=am('gw_well_depth', 'same', map={'same': 'stable', 'deeper': 'deepening', 'dried': 'failed'})),
    L('ls_2_5', 'Approximately how many borewells or tubewells are there within 2–3 km?', 'integer', None,
      relevant="'groundwater' in ls_2_3",
      atlas=am('gw_borewell_density', 'derived', bins=[[10, 'few'], [51, 'moderate'], [None, 'many']],
               note='the number is put in the atlas bands: under 10, 10–50, more than 50')),
    L('ls_2_6', 'Has well or borewell water become salty, left white deposits, or started harming crops?', 'select_one', O(
        ('none', 'No noticeable change'), ('mild', 'Some saltiness or deposits, but water is still usable for some crops'),
        ('severe', 'Water is very salty or causes crop damage'), ('dk', "Don't know")),
      relevant="'groundwater' in ls_2_3", atlas=am('gw_salinity', 'same', map={'none': 'none', 'mild': 'mild', 'severe': 'severe'})),
    L('ls_2_7', 'Have tanks, ponds or check dams become shallower or started drying faster after the monsoon?', 'select_one', O(
        ('none', 'No noticeable change'), ('some', 'Some silt has accumulated and they dry somewhat faster'),
        ('heavy', 'They are heavily silted, much shallower or dry quickly'), ('dk', "Don't know")),
      relevant="'irrigation' in ls_2_3", atlas=am('tank_siltation', 'same', map={'none': 'none', 'some': 'moderate', 'heavy': 'severe'})),
    L('ls_2_8', 'Roughly what share of cultivated land receives irrigation during the rabi or summer season?', 'select_one', O(
        ('low', 'Less than 10%'), ('moderate', '10–30%'), ('high', 'More than 30%'), ('dk', "Don't know")),
      relevant="'rainfed' in ls_2_3", atlas=am('sys_irrigated_share', 'same', map={'low': 'low', 'moderate': 'moderate', 'high': 'high'}),
      note='The atlas asks this whenever farmland covers 10% or more, because it moves share between rainfed and irrigated systems.'),
    L('ls_2_9', 'What may be contributing to low yields or crop losses?', 'select_multiple', O(
        ('chemicals', 'High dependence on chemical fertilisers or pesticides'), ('monocrop', 'Growing the same crop repeatedly'),
        ('seeds', 'Difficulty getting good-quality or suitable seeds, including local varieties'), ('soil', 'Declining soil quality'),
        ('other', 'Other'), ('dk', "Don't know")), relevant="'yield' in ls_2_2 or 'failure' in ls_2_2",
      atlas=am('soil_fertiliser', 'overlap'), must=M(35)),
    L('ls_2_10', 'Is poor access to markets or infrastructure contributing to this problem?', 'select_one', YND,
      relevant="'price' in ls_2_2", must=M(30), note='If yes, note the main difficulty.'),
    L('ls_wl_post', 'After the monsoon (October–November), how far below the ground is the water in open wells?', 'select_one', O(
        ('lt3', 'Less than 3 m (within about 10 feet)'), ('3to8', '3–8 m (about 10–25 feet)'), ('gt8', 'More than 8 m (over about 25 feet)'),
        ('none', 'There are no open wells nearby'), ('dk', "Don't know")),
      origin='added',
      must=M(30, [("aquifer == 'hard_rock' or nz(soge_stage) >= 70", 60, 'recharge works are likely to be planned here, and they need room in the aquifer'),
                  (POS('groundwater.over_extraction', 'groundwater.water_balance_deficit', 'groundwater.recharge_opportunity'), 75, 'groundwater stress is likely: recharge works are likely to be planned, and they need room in the aquifer')]),
      note='Not yet a CoRE Stack layer. The answer goes to the landscape fit of recharge works: percolation tanks, check dams, dug-well recharge and recharge pits and shafts are not suited where the water is within 3 m after the monsoon, and recharge shafts suit best where it is deeper than 8 m (CGWB, Gujarat IWMP manual).',
      sets_var={'var': 'wl_post_monsoon', 'values': {'lt3': 2, '3to8': 5, 'gt8': 10}}),
    A('gw_new_wells_rabi', relevant="ls_2_1 != 'no'"), A('kharif_dry_spells', relevant="ls_2_1 != 'no'"),
    A('kharif_unsown', relevant="ls_2_1 != 'no'"), A('tank_encroach', relevant="ls_2_1 != 'no'"),
    A('recharge_sites'), A('erosion_gullies', relevant="ls_2_1 != 'no'"), A('soil_fertiliser', relevant="ls_2_1 != 'no'"),
    A('fields_abandoned', relevant="ls_2_1 != 'no'"), A('waterlogging', relevant="ls_2_1 != 'no'"),
    A('sys_rabi_source', relevant="ls_2_1 != 'no'"), A('sys_after_paddy', relevant="ls_2_1 != 'no'"),
    A('sys_canal_reliability', relevant="ls_2_1 != 'no'"), A('sys_tree_type'),
  ]),
  dict(id='s3', title='Livestock and fodder', production_system='livestock',
       pathways=['fodder', 'livestock_water_scarcity'], questions=[
    L('ls_3_1', 'Is keeping livestock an important livelihood in this area?', 'select_one', YND,
      must=M(None, [('share_pastoral >= 0.05 or nz(tlu_per_ha) >= 1.5', 15, 'the atlas already finds a large herd here: confirm'),
                    ('share_pastoral < 0.05 and nz(tlu_per_ha) < 1.5', 45, 'the atlas finds few animals; the answer decides whether to ask the livestock questions')]),
      prefill=P(('share_pastoral >= 0.05 or nz(tlu_per_ha) >= 1.5', 'yes', 'grazing commons and a large herd are mapped here'))),
    L('ls_3_2', 'Are livestock numbers, health or productivity declining?', 'select_one', YND, relevant="ls_3_1 != 'no'",
      routes=['ls_3_3', 'ls_3_4'], must=M(40)),
    L('ls_3_3', 'What issues are affecting fodder availability and grazing conditions?', 'select_multiple', O(
        ('green', 'Shortage of green fodder, especially during summer or dry periods'), ('dry', 'Shortage of dry fodder or crop residues'),
        ('grasses', 'Decline in useful grasses and fodder plants'), ('fodder_trees', 'Loss of trees and shrubs that provide fodder'),
        ('bought', 'Increased dependence on purchased fodder'), ('distance', 'Increased distance or time required to collect fodder'),
        ('overgrazing', 'Overgrazing due to excessive livestock pressure'), ('crowding', 'Too many animals grazing in the same area'),
        ('shrinking', 'Grazing lands or pastures becoming smaller due to encroachment or land-use change'),
        ('degrading', 'Grasslands degrading, with reduced grass cover or increasing bare patches'),
        ('erosion', 'Soil erosion in grazing areas'), ('invasive', 'Invasive or unwanted plants replacing useful grasses and fodder species'),
        ('trees_lost', 'Loss of trees and shrubs from grasslands'),
        ('water_short', 'Not enough water for animals, especially in summer'), ('water_drying', 'Grazing areas or nearby water sources are drying up'),
        ('other', 'Other'), ('dk', "Don't know")), relevant="ls_3_2 == 'yes'",
      atlas=[am('fodder_commons', 'overlap'), am('livestock_summer_water', 'overlap'), am('sys_grazing', 'overlap')]),
    L('ls_3_4', 'When is fodder shortage most severe?', 'select_one', O(
        ('year', 'Throughout the year'), ('summer', 'During summer'), ('drought', 'During drought or poor rainfall periods'),
        ('post_monsoon', 'After the monsoon, during the dry season'), ('none', 'No major seasonal shortage'),
        ('other', 'Other'), ('dk', "Don't know")), relevant="ls_3_2 == 'yes'",
      atlas=am('fodder_commons', 'derived', map={'year': 'bare', 'summer': 'short', 'post_monsoon': 'short', 'drought': 'short', 'none': 'enough'},
               note='a shortage all year means the commons are bare; a seasonal one that they run short')),
    L('ls_3_5', 'How have fodder availability and grazing conditions changed over the past 5–10 years?', 'select_one', O(
        ('better', 'Improved'), ('same', 'No major change'), ('slight', 'Slightly declined'), ('much', 'Significantly declined'),
        ('dk', "Don't know")), relevant="ls_3_2 == 'yes'",
      must=M(35, [('known(p_fodder__commons_degradation) and p_fodder__commons_degradation >= 0.3 and p_fodder__commons_degradation <= 0.7', 55,
                   'commons degradation is uncertain in the data; a trend from the community helps')])),
    A('fodder_commons', relevant="ls_3_1 != 'no'"), A('livestock_summer_water', relevant="ls_3_1 != 'no'"),
    A('sys_grazing', relevant="ls_3_1 != 'no'"), A('restoration_land'),
  ]),
  dict(id='s4', title='Forests, forest produce and biodiversity', production_system='forest', pathways=['forest'], questions=[
    L('ls_4_1', 'Are forests, forest produce or forest-based livelihoods important to people in this area?', 'select_one', YND,
      must=M(None, [('f_forest >= 0.2 or share_forest_fringe >= 0.15', 15, 'forest covers much of the area: confirm'),
                    ('f_forest < 0.2 and f_forest >= 0.03 and share_forest_fringe < 0.15', 50, 'some forest is mapped; the answer decides whether to ask the forest questions'),
                    ('f_forest < 0.03', 10, 'hardly any forest is mapped', 'set')]),
      prefill=P(('f_forest >= 0.1 or share_forest_fringe >= 0.15', 'yes', 'forest or a forest fringe is mapped here'),
                ('f_forest < 0.03', 'no', 'hardly any forest is mapped'))),
    L('ls_4_2', 'Which problems are being experienced?', 'select_multiple', O(
        ('A', 'Forest produce has declined'), ('B', 'Wildlife damages crops or livestock, or creates safety concerns'),
        ('C', 'Local plant and animal species are becoming less common'),
        ('D', 'Forest areas are shrinking or becoming separated into smaller patches'), ('other', 'Other'), ('dk', "Don't know")),
      relevant="ls_4_1 != 'no'", routes=['ls_4_3', 'ls_4_4', 'ls_4_5', 'ls_4_7', 'ls_4_9', 'ls_4_11'],
      prefill=P((POS('forest.tree_cover_loss'), ['D'], 'tree cover loss is likely'), (POS('forest.fringe_degradation'), ['A'], 'the forest fringe is degrading'))),
    L('ls_4_3', 'What may be contributing to forest degradation or the decline in forest produce?', 'select_multiple', O(
        ('cover', 'Forest cover or quality has declined'), ('cleared', 'Forest land is being cleared or encroached upon'),
        ('grazing', 'Heavy grazing in forest areas'), ('fire', 'Forest fires'), ('varieties', 'Local varieties of useful plants or trees are disappearing'),
        ('invasive', 'Invasive plants are spreading and affecting local species'), ('access', 'Forest produce is becoming harder to access or collect'),
        ('other', 'Other'), ('dk', "Don't know")), relevant="'A' in ls_4_2 or 'D' in ls_4_2",
      atlas=[am('forest_clearing', 'overlap'), am('forest_fire', 'overlap')]),
    L('ls_4_4', 'Is there a functioning village forest protection committee, Joint Forest Management (JFM) committee, or recognised Community Forest Resource (CFR) rights arrangement?', 'select_one', O(
        ('active', 'Active, with regular activities or protection measures'), ('inactive', 'Exists but is mostly inactive'),
        ('none', 'No functioning arrangement'), ('dk', "Don't know / not applicable")),
      relevant="'D' in ls_4_2", atlas=am('forest_governance', 'same', map={'active': 'active', 'inactive': 'inactive', 'none': 'none'})),
    L('ls_4_5', 'How often do forest fires occur, and has this changed?', 'select_one', O(
        ('rare', 'Rare; no noticeable increase'), ('occasional', 'Occasional; fires seem to be increasing'),
        ('frequent', 'Frequent or repeated fires in the same areas'), ('dk', "Don't know / not applicable")),
      relevant="'A' in ls_4_2 or 'D' in ls_4_2", atlas=am('forest_fire', 'same', map={'rare': 'rare', 'occasional': 'occasional', 'frequent': 'frequent'})),
    L('ls_4_6', 'Are forest boundaries clearly marked on the ground, and are there boundary disputes?', 'select_one', O(
        ('marked', 'Clearly marked; no major disputes'), ('partly', 'Partly marked or markings are poorly maintained'),
        ('disputed', 'Not clearly marked, or active disputes exist'), ('dk', "Don't know / not applicable")),
      relevant="'D' in ls_4_2", must=M(35)),
    L('ls_4_7', 'Compared with five years ago, how much has the collection of important forest produce changed?', 'select_one', O(
        ('little', 'Little change; stable or less than 25% decline'), ('noticeable', 'Noticeable decline of about 25–50%'),
        ('severe', 'Severe decline of more than 50%, or access is largely blocked'), ('dk', "Don't know / not applicable")),
      relevant="'A' in ls_4_2", atlas=am('forest_ntfp', 'derived', map={'little': 'abundant', 'noticeable': 'reduced', 'severe': 'rare'})),
    L('ls_4_8', 'Could loss or fragmentation of wildlife habitat be contributing to the conflict?', 'select_one', YND,
      relevant="'B' in ls_4_2", must=M(30)),
    L('ls_4_9', 'Have forest patches become more fragmented over the past 10–15 years?', 'select_one', O(
        ('none', 'No major change'), ('some', 'Some forest patches have become separated'),
        ('isolated', 'Forest areas are now mostly isolated patches'), ('dk', "Don't know / not applicable")),
      relevant="'C' in ls_4_2 or 'D' in ls_4_2", atlas=am('forest_fragmentation', 'same', map={'none': 'connected', 'some': 'partial', 'isolated': 'isolated'})),
    L('ls_4_10', 'What may be contributing to the loss of local plants and animals?', 'select_multiple', O(
        ('fire', 'Forest fires'), ('quality', 'Declining forest quality'), ('clearing', 'Forest clearing or encroachment'),
        ('grazing', 'Grazing pressure'), ('varieties', 'Loss of local varieties or species'), ('invasive', 'Spread of invasive plants'),
        ('isolated', 'Forest patches becoming isolated'), ('other', 'Other'), ('dk', "Don't know")),
      relevant="'C' in ls_4_2", must=M(30)),
    L('ls_4_11', 'Have community members filed claims under the Forest Rights Act (FRA)?', 'select_one', O(
        ('none', 'No claims filed'), ('pending', 'Claims filed, but most are pending or rejected'),
        ('recognised', 'Some individual or community forest rights have been recognised'), ('dk', "Don't know / not applicable")),
      relevant="ls_4_1 != 'no'", atlas=am('fra_claims', 'same', map={'none': 'none', 'pending': 'pending', 'recognised': 'recognised'})),
    A('forest_clearing', relevant="ls_4_1 != 'no'"),
  ]),
  dict(id='s5', title='Fisheries', production_system='livestock', pathways=['fishery_potential'], questions=[
    L('ls_5_1', 'Is fishing or fish production an important livelihood or resource in this area?', 'select_one', YND,
      must=M(None, [('swb_frac < 0.003', 10, 'hardly any surface water is mapped', 'set'),
                    (POS('fishery_potential'), 45, 'ponds here hold water long enough for a fish crop')], why=None),
      prefill=P((POS('fishery_potential'), 'yes', 'waterbodies here hold water long enough for fish'), ('swb_frac < 0.003', 'no', 'hardly any surface water'))),
    L('ls_5_2', 'Are people experiencing low fish production, fewer fish or fewer fish species?', 'select_one', YND,
      relevant="ls_5_1 == 'yes'", routes=['ls_5_3'], must=M(40)),
    L('ls_5_3', 'What may be contributing to low fish production or fewer fish?', 'select_multiple', O(
        ('drying', 'Ponds or water bodies dry up seasonally'), ('silt', 'Ponds or tanks have become shallow due to silt accumulation'),
        ('management', 'Water bodies are poorly maintained or managed'), ('access', 'People have limited access to water bodies for fishing'),
        ('other', 'Other'), ('dk', "Don't know")), relevant="ls_5_2 == 'yes'", routes=['ls_5_4', 'ls_5_5', 'ls_5_6', 'ls_5_7'], must=M(40)),
    L('ls_5_4', 'Seasonal drying: when do these ponds or water bodies usually dry up?', 'select_one', O(
        ('before_summer', 'Before the end of summer'), ('summer', 'During summer only'), ('never', 'They retain water throughout the year'),
        ('more', 'Drying has increased compared with the past'), ('dk', "Don't know")), relevant="'drying' in ls_5_3",
      atlas=[am('fishery_ponds', 'overlap'), am('wbq_months', 'overlap', atlas='wb', note='asked per waterbody in the waterbody form')]),
    L('ls_5_5', 'Siltation: how has silt accumulation affected the ponds or tanks?', 'select_one', O(
        ('none', 'No noticeable change'), ('some', 'Some silt has accumulated and water-holding capacity has reduced'),
        ('heavy', 'Heavy silt accumulation has made the water bodies much shallower'), ('dk', "Don't know")),
      relevant="'silt' in ls_5_3", atlas=am('tank_siltation', 'derived', map={'none': 'none', 'some': 'moderate', 'heavy': 'severe'})),
    L('ls_5_6', 'Water body management: are the ponds or other water bodies regularly maintained?', 'select_one', O(
        ('regular', 'Yes, regularly maintained'), ('occasional', 'Occasionally maintained'), ('poor', 'Poorly maintained or not maintained'),
        ('dk', "Don't know")), relevant="'management' in ls_5_3", must=M(35)),
    L('ls_5_7', "Access to fishing: what limits people's access to these water bodies?", 'select_multiple', O(
        ('rights', 'Restrictions on fishing or use rights'), ('private', 'Water bodies are privately controlled or leased'),
        ('disputes', 'Disputes over access or fishing rights'), ('far', 'Water bodies are difficult to reach'), ('other', 'Other'),
        ('dk', "Don't know / not applicable")), relevant="'access' in ls_5_3", atlas=am('wbq_fishing', 'overlap', atlas='wb'), must=M(35)),
    A('fishery_ponds', relevant="ls_5_1 != 'no'"),
  ]),
  dict(id='s6', title='Settlement growth and floods', production_system='peri_urban', pathways=['urban_encroachment', 'flood_exposure'],
       added=True, questions=[A('sys_settlement'), A('land_sale'), A('flooding')]),
]

# ---------------------------------------------------------------- forest forms (Word drafts)
FOREST_PATCH = [
    L('fp_category', 'Forest patch category', 'select_one', O(('rf', 'Forest Department: Reserved Forest'), ('pf', 'Forest Department: Protected Forest'),
        ('ogf', 'Other government forest'), ('cmf', 'Community-managed forest'), ('cfr', 'Community Forest Rights (CFR) area'),
        ('khesra', 'Khesra forest (revenue department)'), ('private', 'Private forest'), ('pa', 'Wildlife sanctuary or national park'),
        ('gramya', 'Gramya jungle'), ('dk', 'Not known'), ('other', 'Other')), must=M(60)),
    L('fp_area', 'Approximate area of the forest patch', 'select_one', O(('lt10', 'Less than 10 ha'), ('10_50', '10–50 ha'),
        ('50_100', '50–100 ha'), ('gt100', 'More than 100 ha'), ('dk', "Don't know")), must=M(20, why='the map gives the area')),
    L('fp_access', 'How accessible is this forest patch to the settlement?', 'select_one', O(('easy', 'Easily accessible'),
        ('seasonal', 'Accessible only during certain seasons'), ('difficult', 'Difficult to access'), ('very', 'Very difficult to access'),
        ('dk', "Don't know")), must=M(45)),
    L('fp_land_use', 'Primary land use', 'select_multiple', O(('produce', 'Forest produce collection'), ('jhum_fallow', 'Jhum fallow'),
        ('jhum', 'Jhum (current)'), ('grazing', 'Grazing'), ('protected', 'Protected or conserved'), ('sacred', 'Sacred grove')), must=M(55)),
    L('fp_households', 'Approximately how many households depend on this forest patch?', 'integer', None, must=M(70)),
    L('fp_uses', 'How do communities mainly use this forest patch?', 'select_multiple', O(('ntfp', 'NTFP collection'), ('fuelwood', 'Fuelwood'),
        ('grazing', 'Grazing'), ('timber', 'Timber'), ('bamboo', 'Bamboo'), ('litter', 'Leaf litter'), ('medicinal', 'Medicinal plants'),
        ('food', 'Food / wild edible plants'), ('water', 'Irrigation / water support'), ('cultural', 'Cultural / religious purposes'),
        ('recreation', 'Recreation'), ('other', 'Other')), must=M(70)),
    L('fp_ntfp', 'Which are the three most important NTFPs for livelihoods?', 'select_multiple', O(('mahua', 'Mahua'), ('tendu', 'Tendu'),
        ('sal', 'Sal leaves'), ('honey', 'Honey'), ('tamarind', 'Tamarind'), ('amla', 'Amla'), ('harra', 'Harra'), ('bahera', 'Bahera'),
        ('lac', 'Lac'), ('medicinal', 'Medicinal plants'), ('mushrooms', 'Mushrooms'), ('char', 'Char'), ('karanj', 'Karanj'),
        ('kusum', 'Kusum'), ('chironji', 'Chironji'), ('other', 'Other')), relevant="'ntfp' in fp_uses",
      atlas=am('forest_ntfp', 'overlap'), must=M(55)),
    L('fp_biodiversity', 'Which biodiversity resources are present in this forest patch?', 'select_multiple', O(('trees', 'Native tree species'),
        ('medicinal', 'Medicinal plants'), ('edible', 'Edible wild plants'), ('mammals', 'Wild mammals'), ('birds', 'Birds'),
        ('reptiles', 'Reptiles / amphibians'), ('bees', 'Bees / pollinators'), ('fish', 'Fish / aquatic species'), ('other', 'Other')), must=M(30)),
    L('fp_past', 'What forest-related activities have previously been demanded or undertaken for this forest patch?', 'select_multiple', O(
        ('plantation', 'Tree plantation / afforestation'), ('anr', 'Natural or assisted natural regeneration'), ('protection', 'Protection of existing forest'),
        ('fire', 'Fire prevention / management'), ('invasive', 'Removal / control of invasive species'), ('restoration', 'Restoration of degraded forest areas'),
        ('smc', 'Soil and moisture conservation within the forest'), ('fodder', 'Fodder / pasture development'), ('bamboo', 'Bamboo plantation / regeneration'),
        ('ntfp_regen', 'NTFP regeneration / improvement'), ('ntfp_mgmt', 'NTFP-based resource management'), ('boundary', 'Forest boundary / protection measures'),
        ('habitat', 'Wildlife habitat improvement'), ('other', 'Other'), ('none', 'None previously demanded'), ('dk', "Don't know")), must=M(50)),
    L('fp_past_status', 'What is the current status of the previously demanded or undertaken activity?', 'select_one', O(
        ('working', 'Completed and functioning'), ('maintenance', 'Completed but requires maintenance'), ('partial', 'Partially completed'),
        ('not', 'Not completed'), ('dk', "Don't know")), relevant="not ('none' in fp_past)", must=M(50)),
    L('fp_past_scheme', 'Under which scheme were funds made available for work in this forest patch?', 'select_one', O(
        ('mgnrega', 'MGNREGA / VB-G RAM G'), ('campa', 'CAMPA'), ('jfm', 'Joint Forest Management (JFM)'), ('gim', 'Green India Mission (GIM)'),
        ('nap', 'National Afforestation Programme (NAP)'), ('tsp', 'Tribal Sub-Plan / Forest Rights-related funds'),
        ('state', 'State Government forest / afforestation scheme'), ('self', 'Self-funded / community contribution'), ('other', 'Other'),
        ('dk', "Don't know")), relevant="not ('none' in fp_past)", must=M(30)),
    L('fp_problems', 'What are the main problems affecting this forest patch? (up to 3)', 'select_multiple', O(
        ('fire', 'Forest fire'), ('cutting', 'Illegal tree cutting'), ('ntfp', 'Declining NTFPs'), ('overgrazing', 'Overgrazing'),
        ('water', 'Water scarcity'), ('encroachment', 'Encroachment'), ('mining', 'Mining'), ('climate', 'Climate impacts: heat, drought, erratic rainfall'),
        ('regeneration', 'Poor regeneration'), ('harvesting', 'Unsustainable harvesting of forest produce'), ('invasive', 'Invasive species'),
        ('conflict', 'Wildlife conflict'), ('hunting', 'Hunting / poaching'), ('habitat', 'Wildlife habitat degradation'), ('other', 'Other')),
      atlas=[am('forest_fire', 'overlap'), am('forest_clearing', 'overlap'), am('forest_ntfp', 'overlap')], must=M(60)),
    L('fp_degraded', 'Are there areas within the forest patch that the community considers degraded or requiring restoration?', 'select_one', YND,
      atlas=am('restoration_land', 'overlap'), must=M(60)),
    L('fp_degraded_why', 'What are the main reasons for degradation?', 'select_multiple', O(('fire', 'Forest fire'), ('overgrazing', 'Overgrazing'),
        ('cutting', 'Tree cutting'), ('invasive', 'Invasive species'), ('erosion', 'Soil erosion'), ('water', 'Water scarcity'),
        ('mining', 'Mining / extraction'), ('encroachment', 'Encroachment'), ('harvesting', 'Unsustainable harvesting'), ('other', 'Other')),
      relevant="fp_degraded == 'yes'", must=M(50)),
    L('fp_managed_by', 'Who manages this forest patch?', 'select_multiple', O(('gram_sabha', 'Gram Sabha / village institution'),
        ('fd', 'Forest Department'), ('cfrmc', 'CFR Management Committee'), ('vss', 'Van Suraksha Samiti / JFM committee'),
        ('private', 'Private owner'), ('other', 'Other')), atlas=am('forest_governance', 'overlap'), must=M(55)),
    L('fp_rights', 'What rights or management arrangement applies over this forest patch?', 'select_one', O(
        ('cfr', 'Community Forest Rights (CFR) recognised'), ('jfm', 'Joint Forest Management (JFM) area'), ('fd', 'Forest Department managed'),
        ('revenue', 'Revenue Department managed'), ('private', 'Private ownership'), ('none', 'No formal rights'), ('dk', "Don't know")),
      atlas=am('fra_claims', 'derived', map={'cfr': 'recognised'}, note='only a recognised CFR can be read across to fra_claims'), must=M(55)),
    L('fp_rules', 'Are there community rules for managing the forest?', 'select_one', YND, atlas=am('forest_governance', 'overlap'), must=M(50)),
    L('fp_rules_cover', 'What do the rules cover?', 'select_multiple', O(('cutting', 'Tree cutting'), ('ntfp', 'NTFP collection'),
        ('grazing', 'Grazing'), ('fire', 'Fire prevention'), ('seasonal', 'Seasonal protection'), ('outsiders', 'Outsider access'), ('other', 'Other')),
      relevant="fp_rules == 'yes'", must=M(40)),
]
for q in FOREST_PATCH: q['origin'] = 'doc'

FOREST_PLANNING = [
    L('fpl_demand', 'Is the community planning or demanding any forest-related activity in this forest patch?', 'select_one', O(('yes', 'Yes'), ('no', 'No')), must=M(80)),
    L('fpl_who', 'Who is raising the demand or planning the activity?', 'select_one', O(('community', 'Community'), ('fug', 'Forest User Group'),
        ('fpc', 'FPC'), ('cfr', 'CFR Committee'), ('shg', 'SHG'), ('cluster', 'Cluster / group'), ('individual', 'Individual'), ('other', 'Other')),
      relevant="fpl_demand == 'yes'"),
    L('fpl_activities', 'What activities are being planned or demanded in this forest patch?', 'select_multiple', O(
        ('anr', 'Assisted Natural Regeneration (ANR)'), ('fire', 'Forest fire prevention / management'), ('cutting', 'Protection from illegal tree cutting'),
        ('grazing', 'Grazing management'), ('fencing', 'Boundary protection / fencing'), ('habitat', 'Wildlife habitat improvement'),
        ('invasive', 'Removal / management of invasive species'), ('sacred', 'Protection of sacred groves'), ('native', 'Native species planting / forest restoration'),
        ('ntfp', 'Sustainable NTFP management'), ('patrol', 'Forest protection / patrolling'), ('bamboo', 'Bamboo / cane management'), ('other', 'Other')),
      relevant="fpl_demand == 'yes'"),
    L('fpl_how', 'How does the community plan to take up the proposed activity?', 'select_one', O(('scheme', 'Demand through government scheme / convergence'),
        ('self', 'Community self-planned activity'), ('both', 'Both')), relevant="fpl_demand == 'yes'", must=M(50)),
    L('fpl_schemes', 'Which government departments or schemes could support the proposed activity?', 'select_multiple', O(
        ('mgnrega', 'MGNREGA / VB-G RAM G'), ('fd', 'Forest Department'), ('campa', 'CAMPA'), ('gim', 'Green India Mission (GIM)'),
        ('pmksy', 'PMKSY / Watershed Programme'), ('nrlm', 'NRLM / SRLM'), ('tribal', 'Tribal Welfare Department'), ('rd', 'Rural Development Department'),
        ('gp', 'Gram Panchayat'), ('agri', 'Agriculture Department'), ('other', 'Other'), ('dk', "Don't know")), relevant="fpl_demand == 'yes'", must=M(50)),
    L('fpl_households', 'Estimated number of beneficiary households', 'integer', None, relevant="fpl_demand == 'yes'", must=M(60)),
    L('fpl_priority', 'Priority of the demand', 'select_one', O(('very_high', 'Very high'), ('high', 'High'), ('medium', 'Medium'), ('low', 'Low')),
      relevant="fpl_demand == 'yes'", must=M(60)),
]
for q in FOREST_PLANNING: q['origin'] = 'doc'
FOREST_PLANNING[1]['role'] = 'record'; FOREST_PLANNING[2]['work_types'] = True

# ---------------------------------------------------------------- annotations for the ODK forms
WB_SILT = {'Low': 'little', 'Moderate': 'some', 'High': 'much'}
ANN = {
 'settlement': {
    'number_households': dict(role='inform', must=M(100, why='needed for every plan; not known from the atlas')),
    'count_sc': dict(role='inform', must=M(80, why='the census share is in the atlas, but not by settlement'), hint='Census 2011 (whole MWS): SC {sc_share:pct}, ST {st_share:pct}'),
    'count_st': dict(role='inform', must=M(80), hint='Census 2011 (whole MWS): ST {st_share:pct}'),
    'count_obc': dict(role='inform', must=M(70)), 'count_general': dict(role='inform', must=M(70)),
    'distance_settlement': dict(role='inform', must=M(30)),
    'road_connected': dict(role='inform', must=M(45)), 'settlement_electricity': dict(role='inform', must=M(40)),
    'landless_farmers': dict(role='inform', must=M(70), atlas=am('landholding', 'derived',
        value='(nz(landless_farmers) + nz(marginal_farmers)) / max(1, nz(landless_farmers) + nz(marginal_farmers) + nz(small_farmers) + nz(medium_farmers) + nz(big_farmers))',
        bins=[[0.25, 'minority'], [0.5, 'about_half'], [None, 'majority']],
        note='landless and marginal (< 2.5 acres, that is < 1 ha) farmers as a share of all farmers; read when all five counts are filled')),
    'marginal_farmers': dict(role='inform', must=M(70)), 'small_farmers': dict(role='inform', must=M(60)),
    'medium_farmers': dict(role='inform', must=M(55)), 'big_farmers': dict(role='inform', must=M(55)),
    'Cattle': dict(role='inform', must=M(50, [('ps_livestock == 1', 70, 'livestock is a production system here')])),
    'Goats': dict(role='inform', must=M(50, [('ps_livestock == 1', 75, 'livestock is a production system here')]),
                  atlas=am('sys_grazing', 'overlap', note='sheep and goat numbers indicate, but do not say, how many households graze the commons')),
    'Sheep': dict(role='inform', must=M(50, [('ps_livestock == 1', 75, 'livestock is a production system here')])),
    'Poultry': dict(role='inform', must=M(35)), 'Piggery': dict(role='inform', must=M(35)), 'Bail': dict(role='inform', must=M(40)),
    'Households_BPL_cards': dict(role='inform', must=M(60)), 'NREGA_applied': dict(role='inform', must=M(60)),
    'NREGA_have_job_card': dict(role='inform', must=M(60)),
    'NREGA_work_days': dict(role='inform', must=M(60), atlas=am('nrega_work', 'derived', bins=[[15, 'none'], [50, 'partial'], [None, 'good']],
        note='fewer than 15 days is little or no work; 50 or more days is good')),
    'reason_low_work': dict(role='inform', must=M(50), atlas=am('migration', 'overlap')),
    'work_demands': dict(role='inform', must=M(50, why='past demands show what the community already wants')),
    'select_multiple_issues': dict(role='inform', must=M(55)), 'select_one_contributions': dict(role='inform', must=M(55)),
    'Other_information': dict(role='record'),
 },
 'waterbody': {
    'select_one_water_structure': dict(role='inform', must=M(100, why='decides the repair questions'), prefill=P(
        ("wtype == 'farm_pond'", 'Farm pond', 'the atlas types it as a farm pond'),
        ("wtype == 'village_pond'", 'Community Pond', 'the atlas types it as a village pond'),
        ("(wtype == 'onstream_tank' or wtype == 'reservoir') and area_ha >= 5", 'Large water body', 'a tank or reservoir of 5 ha or more'),
        ("wtype == 'onstream_tank' or wtype == 'small_onstream_pond' or wtype == 'headwater_pond' or wtype == 'canal_fed'", 'Community Pond', 'a stream- or canal-fed tank or pond'))),
    'select_one_manages': dict(role='inform', atlas=am('wbq_wua', 'derived', 'wb', map={'Water user association': 'active', 'Pani Panchayats': 'active', 'Nobody': 'none'},
        note="'Village institutions' and 'Neighbouring farmers' do not say whether a committee is active; ask wbq_wua as well")),
    'select_one_owns': dict(role='inform', prefill=P(("wtype == 'farm_pond'", 'Private', 'the atlas types it as a farm pond (private)'),
                                                     ("wtype == 'village_pond'", 'Community', 'the atlas types it as a village pond (common)')),
                            atlas=am('wbt_ownership', 'derived', 'wb', map={'Community': 'common', 'Private': 'private', 'Shared among families': 'private'},
        note='shared among a few families is treated as private: the type rules separate common village ponds from ponds owned by one or a few farmers')),
    'households_benefited': dict(role='inform', must=M(60)),
    'select_multiple_caste_use': dict(role='inform', must=M(50, [('nz(st_share) + nz(sc_share) >= 0.3', 65, 'SC and ST households are a large share here; who uses the water matters for equity')])),
    'select_multiple_uses_structure': dict(role='inform', must=M(60), atlas=[am('wbq_users', 'overlap', 'wb'), am('wbq_fishing', 'overlap', 'wb'), am('wbq_animals', 'overlap', 'wb')]),
    'select_one_scheme': dict(role='inform', must=M(35)),
    'select_one_maintenance': dict(role='inform', must=M(70, [("nz(wpos_wb__siltation) == 1 or nz(wpos_wb__poor_retention) == 1 or nz(wpos_wb__inflow_shortfall) == 1", 90, 'the atlas finds siltation, leakage or a shortfall of inflow likely here')])),
    'Last_maintenance': dict(role='inform', must=M(55)),
    'select_one_visible_water_structure': dict(role='record'),
    'age_ws': dict(role='inform', must=M(35)),
 },
 'well': {
    'select_one_well_type': dict(role='inform', must=M(100)),
    'select_one_y_n': dict(role='inform', must=M(40, [('share_groundwater_irrigated >= 0.15', 60, 'groundwater irrigation is present: electrified borewells drive extraction')])),
    'select_one_owns': dict(role='inform', must=M(60)), 'select_multiple_caste_use': dict(role='inform', must=M(50)),
    'select_one_scheme': dict(role='inform', must=M(30)),
    'select_one_year': dict(role='inform', must=M(60), atlas=[am('gw_well_depth', 'derived', map={'Dec': 'failed', 'Jan': 'failed', 'Feb': 'failed', 'Mar': 'failed', 'Apr': 'failed', 'May': 'failed', 'June': 'stable'},
        note="a well that goes dry in rabi or summer reads as 'failed'; a well with water until June as 'stable' (read for open wells and hand pumps only)"), am('drinking_summer', 'overlap')]),
    'households_benefited': dict(role='inform', must=M(55)), 'Is_water_from_well_used': dict(role='inform', must=M(45)),
    'select_one_well_used': dict(role='inform', must=M(45), atlas=am('sys_rabi_source', 'overlap')),
    'is_maintenance_required': dict(role='inform', must=M(65)), 'repairs_type': dict(role='inform', must=M(60)),
    'select_one_change_water_quality': dict(role='inform', atlas=am('drinking_water_quality', 'derived',
        map={'Significant deterioration (e.g., murky, bad taste, discoloration)': 'unsafe', 'Minor deterioration (e.g., slight change in clarity or taste)': 'some',
             'No noticeable change': 'fine', 'Minor improvement (e.g., clearer water, better taste)': 'fine',
             'Significant improvement (e.g., clear water, restored natural color and taste)': 'fine'})),
    'select_one_pollutants_groundwater': dict(role='inform', must=M(40), atlas=[am('mining_water', 'overlap'), am('drinking_water_quality', 'overlap')]),
    'select_one_water_structure_near_you': dict(role='inform', must=M(40), atlas=am('recharge_sites', 'overlap')),
    'select_one_change_observed': dict(role='inform', atlas=am('gw_well_depth', 'derived', map={'Decreasing_levels': 'deepening', 'Not_observed_changes': 'stable', 'Increasing_levels': 'stable'},
        note="'Decreasing levels' means the water level has gone down: the well has deepened")),
 },
 'crop': {
    'Uncropped_barren_land': dict(role='inform', must=M(60)),
    'select_multiple_widgets': dict(role='inform', atlas=[am('sys_rabi_source', 'overlap'), am('sys_irrigated_share', 'overlap')]),
    'select_one_classified': dict(role='inform', must=M(45, [(POS('flood_exposure', 'irrigation.waterlogging'), 65, 'floods or waterlogging are likely; lowland patches are most exposed')])),
    'select_one_practice': dict(role='inform', must=M(80), atlas=[am('sys_irrigated_share', 'overlap'), am('sys_after_paddy', 'overlap')]),
    'select_multiple_cropping_kharif': dict(role='inform', must=M(75)), 'total_area_cultivation_kharif': dict(role='inform', must=M(55)),
    'select_multiple_cropping_Rabi': dict(role='inform', must=M(70), atlas=am('sys_after_paddy', 'overlap')), 'total_area_cultivation_Rabi': dict(role='inform', must=M(55)),
    'select_multiple_cropping_Zaid': dict(role='inform', must=M(50)), 'total_area_cultivation_Zaid': dict(role='inform', must=M(45)),
    'select_one_productivity': dict(role='inform', atlas=am('fields_abandoned', 'overlap'),
        must=M(40, [('known(urg_productivity__declining_intensity)', 'urg_productivity__declining_intensity', 'reads directly on the declining-intensity rule')])),
    'soil_degraded': dict(role='inform', atlas=[am('soil_fertiliser', 'overlap'), am('erosion_gullies', 'overlap')]),
    'select_one_reason_degradation_1': dict(role='inform', must=M(45)),
 },
}
# silt amounts in the waterbody form read directly on wbq_silt
for k in ('Select_one_silt_fp', 'Select_one_silt_canal', 'Select_one_silt_cp', 'Select_one_silt_cd', 'Select_one_silt_pt', 'Select_one_silt_lwb',
          'Select_one_silt_trench', 'Select_one_silt_ds', 'Select_one_silt_rp', 'Select_one_silt_sp', 'Select_one_silt_cct', 'Select_one_silt_sct',
          'Select_one_silt_wct', 'Select_one_silt_rfd', 'Select_one_silt_sb', 'Select_one_silt_dd', 'Select_one_silt_bunding',
          'Select_one_silt_model5', 'Select_one_silt_model30', 'Select_one_silt_underground_dyke'):
    ANN['waterbody'][k] = dict(role='inform', atlas=am('wbq_silt', 'derived', 'wb', map=WB_SILT))
# atlas waterbody questions the form does not ask
WB_ADDED = ['wbt_inflow', 'wbq_inlet', 'wbq_diverted', 'wbq_encroach', 'wbq_leak', 'wbq_months', 'wbq_drought', 'wbq_sharing',
            'wbq_users', 'wbq_channels', 'wbq_wua', 'wbq_animals', 'wbq_fishing', 'wbq_fish_dry', 'wbq_canal', 'wbq_river_dry', 'wbq_sand']

# work types in the planning forms -> interventions (knowledge/interventions.json)
WORK = {
    'Farm pond': ['farm_pond', 'pond_lining'], 'Community Pond': ['community_pond', 'traditional_harvesting'],
    'Well': ['solar_pumps_safeguards', 'protective_irrigation'], 'Canal': ['diversion_based_irrigation', 'conveyance_pipelines'],
    'Farm bund': ['farm_bunds'], 'Check dam': ['check_dam'], 'Percolation tank': ['percolation_tank'],
    'Earthen gully plug': ['earthen_gully_plug'], 'Drainage/soakage channels': ['diversion_drain'], 'Recharge pits': ['recharge_pits_shafts'],
    'Sokage pits': ['recharge_pits_shafts'], 'Soakage pits': ['recharge_pits_shafts'], 'Trench cum bund network': ['trench_cum_bund'],
    'Continuous contour trenches (CCT)': ['cct'], 'Staggered Contour trenches(SCT)': ['sct'], 'Water absorption trenches(WAT)': ['wat'],
    'Loose boulder structure': ['loose_boulder_check'], 'Rock fill dam': ['gabion_rockfill'], 'Stone bunding': ['stone_bunding'],
    'Diversion drains': ['diversion_drain'], 'Bunding:Contour bunds/ graded bunds': ['contour_bunds', 'graded_bunds'],
    '5% model structure': ['five_percent_model'], '5% Model structure': ['five_percent_model'],
    '30-40 model structure': ['model_30_40'], '30-40 Model structure': ['model_30_40'],
    'Underground dyke': ['subsurface_dyke'], 'Recharge shaft': ['recharge_pits_shafts'], 'Injection well': ['dug_well_recharge'],
    'Large water body': ['tank_cascade', 'encroachment_protection'],
}
MAINT = ['desilting', 'bund_sluice_repair', 'inlet_restoration']   # maintenance of any surface structure
FOREST_WORK = {'anr': ['forest_regeneration'], 'fire': ['fire_management'], 'cutting': ['forest_regeneration'], 'grazing': ['commons_pasture'],
               'fencing': ['forest_regeneration'], 'habitat': ['forest_regeneration', 'riparian_buffer'], 'invasive': ['commons_pasture', 'forest_regeneration'],
               'sacred': ['forest_regeneration'], 'native': ['forest_regeneration'], 'ntfp': ['forest_regeneration'], 'patrol': ['forest_regeneration'],
               'bamboo': ['agroforestry', 'forest_regeneration']}
WORK_Q = {  # (form, question) -> intervention map for its options
    ('recharge_new', 'TYPE_OF_WORK_ID'): 'work', ('irrigation_new', 'TYPE_OF_WORK_ID'): 'work',
    ('recharge_maintenance', 'select_one_recharge_structure'): 'work', ('surface_maintenance', 'TYPE_OF_WORK'): 'maint',
    ('surface_maintenance_rs', 'TYPE_OF_WORK'): 'maint', ('irrigation_maintenance', 'select_one_irrigation_structure'): 'maint',
}
PLAN_INFORM = {   # inform questions of the planning forms (everything else in them is a record)
    'irrigation_new': {'select_multiple_cropping_kharif': 50, 'select_one_cropping_pattern': 40, 'departments_converged': 45},
    'recharge_new': {'departments_converged': 45},
    'recharge_maintenance': {'past_repair': 55},
    'agrohorticulture': {'select_one_y_n': 80, 'select_multiple_species': 60, 'land_type': 50, 'land_ownership': 55, 'current_land_use': 55,
                         'soil_type': 40, 'water_availability': 60, 'agro_model': 60, 'departments_converged': 45, 'crop_area': 50, 'total_saplings': 40},
    'livelihood': {'is_demand_livestock': 80, 'demands_promoting_livestock': 60, 'assets_kg': 60, 'support_apart_labour': 40,
                   'is_demand_fisheries': 70, 'demands_promoting_fisheries': 60, 'departments_converged': 40,
                   'departments_converged_kg': 35, 'departments_converged_fisheries': 40},
}
PLAN_DEMAND_IV = {   # yes/no demand questions -> interventions, so they are scored by fit
    ('agrohorticulture', 'select_one_y_n'): ['agroforestry'], ('livelihood', 'is_demand_livestock'): ['fodder_livestock'],
    ('livelihood', 'is_demand_fisheries'): ['fishery_development'], ('livelihood', 'assets_kg'): ['equitable_planning'],
}
RECORD_HINTS = ('beneficiary', 'ben_', 'name', 'contact', 'khasra', 'gender', 'length', 'width', 'depth', 'height', 'breadth',
                'diameter', 'work_id', 'block_', 'plan_', 'user_latlon', 'corresponding', 'total_cluster', 'text_one', 'other_issue',
                'settlements_id', 'waterbodies_id', 'well_id', 'crop_grid', 'specify')

def _role(q):
    if q['type'] in ('note', 'geopoint', 'geotrace', 'geoshape', 'image', 'audio', 'video') or q.get('hidden'): return 'record'
    n = q['name'].lower()
    if q['type'] in ('text', 'integer', 'decimal') and any(h in n for h in RECORD_HINTS): return 'record'
    if q['type'] == 'select_one' and n in ('gender', 'select_gender', 'gender_livestock', 'gender_kitchen_gardens', 'gender_fisheries'): return 'record'
    if q['type'] == 'text': return 'record'
    if n.startswith('demand_type') or n in ('livestock_demand',): return 'record'
    return 'inform'

def _atlas_q(K, atlas, qid):
    Q = K[atlas]
    for k in ('system_questions', 'stress_questions', 'type_questions'):
        for q in Q.get(k, []):
            if q['id'] == qid: return q, k
    raise KeyError(f'{atlas}:{qid}')

def _from_atlas(q, K):
    atlas, qid = q.pop('from_atlas')
    aq, kind = _atlas_q(K, atlas, qid)
    q['label'] = aq['text']; q['type'] = 'select_one'
    q['options'] = [{'id': o['id'], 'label': o['label']} for o in aq['options']]
    q['atlas_match'][0]['map'] = {o['id']: o['id'] for o in aq['options']}
    q['atlas_kind'] = kind
    if aq.get('show_if'): q['atlas_show_if'] = aq['show_if']
    return q

def build(forms_dir, out=None, log=print):
    from .odk import parse_xlsform
    forms_dir = Path(forms_dir)
    K = {'ws': json.loads((ROOT / 'knowledge' / 'questions.json').read_text(encoding='utf-8')),
         'wb': json.loads((ROOT / 'knowledge' / 'waterbody' / 'questions.json').read_text(encoding='utf-8'))}
    out_forms = []
    for F in FORMS:
        f = {k: v for k, v in F.items() if k not in ('odk',)}
        f['odk_file'] = F['odk']
        if F['id'] == 'landscape':
            secs = []
            for s in LANDSCAPE:
                s = json.loads(json.dumps(s))
                s['questions'] = [_from_atlas(q, K) if q.get('from_atlas') else q for q in s['questions']]
                for q in s['questions']: q['section'] = s['id']
                secs.append(s)
            f['sections'] = [{k: v for k, v in s.items() if k != 'questions'} for s in secs]
            f['questions'] = [q for s in secs for q in s['questions']]
        elif F['id'] == 'forest_patch':
            f['questions'] = json.loads(json.dumps(FOREST_PATCH))
        elif F['id'] == 'forest_planning':
            qs = json.loads(json.dumps(FOREST_PLANNING))
            for q in qs:
                if q.get('work_types'):
                    q.pop('work_types'); q['work_map'] = {o['id']: FOREST_WORK.get(o['id'], []) for o in q['options']}; q['role'] = 'inform'
                    q['must_ask'] = M(None, why='scored by how well the activities suit this landscape')
            f['questions'] = qs
        else:
            X = parse_xlsform(forms_dir / F['odk'])
            f['form_title'] = X['settings'].get('form_title'); f['form_id'] = X['settings'].get('form_id')
            f['odk_version'] = X['settings'].get('version') or None
            ann = ANN.get(F['id'], {})
            qs = []
            for q in X['questions']:
                if q['type'] == 'note': continue
                a = ann.get(q['name'], {})
                if F['id'] == 'waterbody' and q['name'].startswith('Repair_of_'):
                    a = dict(role='inform', must=M(50, why='the repairs needed; shown when the structure needs repair'),
                             atlas=[am('wbq_silt', 'overlap', 'wb'), am('wbq_leak', 'overlap', 'wb'), am('wbq_inlet', 'overlap', 'wb')])
                q['role'] = a.get('role') or _role(q)
                if F['section'] == 'planning':
                    pi = PLAN_INFORM.get(F['id'], {})
                    q['role'] = 'inform' if q['name'] in pi or (F['id'], q['name']) in WORK_Q else 'record'
                    if q['name'].startswith('demand_type') or q['name'] == 'livestock_demand':
                        q['role'] = 'inform'; q['must_ask'] = M(100, why='who raises the demand; decides the questions that follow')
                    if q['name'] in pi: q['must_ask'] = M(pi[q['name']])
                    if F.get('kind') == 'maintenance' and q['type'] == 'select_multiple' and not q.get('hidden'):
                        q['role'] = 'inform'; q['must_ask'] = M(55, why='the repairs needed; shown for the structure chosen')
                        q['atlas_match'] = [am('wbq_silt', 'overlap', 'wb'), am('wbq_leak', 'overlap', 'wb'), am('wbq_inlet', 'overlap', 'wb')] \
                            if F['group'] == 'surface_waterbody' else []
                        if not q['atlas_match']: q.pop('atlas_match')
                    wk = WORK_Q.get((F['id'], q['name']))
                    if wk:
                        q['work_map'] = {o['id']: (WORK.get(o['id'], []) if wk == 'work' else
                                                   (['dug_well_recharge'] if o['id'] == 'Well' else ['conveyance_pipelines', 'pim_wua'] if o['id'] == 'Canal'
                                                    else ['farm_bunds'] if o['id'] == 'Farm bund' else list(dict.fromkeys(MAINT + WORK.get(o['id'], [])))))
                                         for o in q.get('options', [])}
                        missing = [o['id'] for o in q['options'] if not q['work_map'].get(o['id'])]
                        if missing: log(f"  {F['id']}.{q['name']}: no intervention for {missing}")
                        q['must_ask'] = M(None, why='scored by how well the work types suit this landscape and the stresses found')
                    dv = PLAN_DEMAND_IV.get((F['id'], q['name']))
                    if dv: q['demand_iv'] = dv
                if q['role'] == 'inform':
                    if a.get('atlas'): q['atlas_match'] = a['atlas'] if isinstance(a['atlas'], list) else [a['atlas']]
                    if a.get('must'): q['must_ask'] = a['must']
                    elif 'must_ask' not in q: q['must_ask'] = M(40 if not q.get('atlas_match') else None)
                    if a.get('hint'): q['atlas_hint'] = a['hint']
                    if a.get('prefill'): q['prefill'] = a['prefill']
                q['origin'] = 'odk'
                qs.append(q)
            if F['id'] in ('recharge_new', 'irrigation_new'):
                qs.append(L('site_soil', 'Soil at the proposed site', 'select_one', O(('Black', 'Black'), ('Red', 'Red'), ('Laterite', 'Laterite'),
                    ('Alluvial', 'Alluvial'), ('Sandy', 'Sandy'), ('Clay', 'Clay'), ('Rocky', 'Rocky')), origin='added',
                    relevant_expr=None, must=M(70, why='field record of the soil at the site'),
                    note='Added. The classes are those the Commons Connect forms use for desilting and plantations. Kept as field data; the site rules read soil as the hydrologic soil group.'))
            if F['id'] == 'waterbody':
                for qid in WB_ADDED:
                    if any(m['id'] == qid for x in qs for m in x.get('atlas_match', []) if m['how'] == 'same'): continue
                    qs.append(_from_atlas(A(qid, atlas='wb'), K))
            f['questions'] = qs
        n_inf = sum(1 for q in f['questions'] if q.get('role') == 'inform')
        log(f"  {F['id']}: {len(f['questions'])} questions, {n_inf} inform")
        out_forms.append(f)
    doc = {
        '_about': 'Structured local version of the Commons Connect forms (ODK templates and Word drafts), with the atlas '
                  'questions each one overlaps and a must-ask rule. Built by `python -m seft.cli cc-build --forms <folder>` '
                  '(seft/commons_connect.py); scored by seft/priority.py and, in the browser, by the Commons Connect tab '
                  'of web/index.html. Option ids are the values the ODK forms store.',
        'version': '0.1', 'built_from': 'commons_connect_forms.zip (12 ODK XLSForm templates, 15 Word documents)',
        'sections': [{'id': a, 'label': b, 'about': c} for a, b, c in SECTIONS],
        'plan_groups': [{'id': a, 'label': b} for a, b in PLAN_GROUPS],
        'priority': PRIORITY,
        'forms': out_forms,
    }
    out = Path(out or ROOT / 'knowledge' / 'commons_connect.json')
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    log(f'  wrote {out}')
    return doc

PRIORITY = {
    'about': "Each question gets a must-ask score from 0 to 100. Atlas questions are scored from the current inference "
             "(seft/priority.py); a Commons Connect question takes the highest of its own base score, the scores of the "
             "atlas questions it matches (times the weight for how closely they match), and the scores of its rules that "
             "hold here (a question with no base score, rule or match gets default_base). A routing question takes the highest score of the questions it leads to. Records (names, "
             "beneficiary details, dimensions, photos) are always kept and are not scored.",
    'bands': [{'min': 60, 'id': 'must', 'label': 'Must ask'}, {'min': 30, 'id': 'useful', 'label': 'Useful'},
              {'min': 0, 'id': 'skip', 'label': 'Can skip'}],
    'match_weight': {'same': 1.0, 'derived': 0.9, 'overlap': 0.6},
    'default_base': 40,
    'stress_question': "For every rule the question informs (and that applies here), with p its current probability: "
                       "flip = the chance that the answer takes the rule across the positive line (positive_at): when "
                       "some answer would do so, p if the rule is below the line (a supporting answer is needed) or 1 − p "
                       "if above it, scaled so that 0.5 counts fully; move = the largest change in probability any answer "
                       "would make (0.4 counts fully); uncertainty = 1 − |2p − 1|; borderline = how close the data are to "
                       "the rule's threshold (for a triggered rule 1 − intensity/100, for a rule not triggered its "
                       "partial intensity/100, 1 when the data are missing); low confidence = 1 for a low-confidence rule, "
                       "0.5 for medium. Rule score = 100 × (0.35 flip + 0.1 move + 0.15 uncertainty + 0.3 borderline + "
                       "0.1 low confidence). Question score = the highest rule score, plus 5 for each further rule scoring "
                       "50 or more. urg_<rule> is the score of a typical question for that rule, one with likelihood "
                       "ratios 0.4 and 2.5.",
    'stress_weights': {'flip': 0.35, 'move': 0.1, 'move_full': 0.4, 'uncertainty': 0.15, 'borderline': 0.3, 'low_confidence': 0.1,
                       'breadth_bonus': 5, 'breadth_at': 50},
    'urgency_lrs': [0.4, 2.5],
    'system_question': "For each answer the system mix is recomputed. cross = for the systems some answer would take across "
                       "their presence threshold (present_at), how close the share is to that threshold now (1 at the "
                       "threshold, 0 at zero or twice the threshold), the largest; shift = the mean share of the MWS the "
                       "answers would move (total variation; 0.15 counts fully). Score = 100 × (0.6 cross + 0.4 shift), or "
                       "the stress score of its options if that is higher. A system question whose show_if fails scores 0.",
    'system_weights': {'cross': 0.6, 'shift': 0.4, 'shift_full': 0.15},
    'type_question': "Waterbody type questions: for each answer the type is reassigned. Score = 100 × (0.6 if some answer "
                     "changes the type + 0.4 × the share of answers that do).",
    'type_weights': {'any': 0.6, 'share': 0.4},
    'planning': "A work type scores 90 when an intervention it builds suits this landscape and responds to a stress found "
                "here, 65 when it is possible and responds to a stress, 40 when it suits but no stress calls for it, 20 "
                "when it is only possible, and 5 when it is not suited. A work-type question and its form take the "
                "highest score of their work types.",
    'planning_scores': {'suited_stress': 90, 'possible_stress': 65, 'suited': 40, 'possible': 20, 'not_suited': 5},
    'env': "Rule conditions use the watershed variables, share_<system>, the context classes (rainfall, aquifer, terrain, "
           "gw_category, canal, cropping), ps_<production system> (1 present, 0 absent), p_<rule> (probability), "
           "pos_<rule> (1 when likely present), urg_<rule> (the rule's must-ask score) and ask_<atlas question>, with "
           "dots in rule ids written as double underscores (p_groundwater__over_extraction). In the waterbody form: "
           "the waterbody variables, wtype, wp_<rule>, wpos_<rule> and wask_<question>; in the MWS, n_wb and "
           "wbpos_<rule> (number of waterbodies where the rule is likely).",
}
