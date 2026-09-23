"""Check every authored identity and sampled geometry round trips, then reopen native."""
import bpy,json,numpy as np
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');original=bpy.context.scene;V=original['version']
station_record=json.loads((ROOT/'runtime/station_road_working.json').read_text())
record=station_record if station_record['version']==V else json.loads((ROOT/'runtime/bellevue_working.json').read_text())
assert record['version']==V
col=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'];deps=bpy.context.evaluated_depsgraph_get()
names=['BE_PUBLIC_PLATFORM','BE_SOURCE_bauten_dachmodell_3d.153133','BE_SKYLIGHT_SURVEYED_RIM','BE_DOOR_GLASS_L','BE_DOOR_GLASS_R','BE_HIGH_TABLE_00','BE_BAR_TOP','BE_DISPLAY_CASE_BASE','BE_ROOF_STANDING_SEAM_000','BE_COLUMN_00_STEEL']
if bpy.data.objects.get('BE_PLATFORM_CURB_TOP'):
    names+=['BE_PLATFORM_CURB_TOP','BE_PLATFORM_CURB_FACE']
    names += [o.name for o in col.all_objects if o.get('surface_role') in ['road_concrete','rail_steel','groove_floor']][:5]
    if bpy.data.objects.get('BE_CROSSING_BAR_000'):
        names += ['BE_CROSSING_BAR_000','BE_CROSSING_BAR_069']
if bpy.data.objects.get('BE_WEST_PLATFORM'):
    names+=['BE_WEST_PLATFORM','BE_WEST_CURB_FACE','BE_WEST_SHELTER_ROOF_METAL',
            'BE_WEST_SHELTER_SOFFIT','BE_WEST_COLUMN_FLARE_00','BE_WEST_BENCH_SEAT_0',
            'BE_WEST_AD_0_GLASS_-1','BE_WEST_TICKET_BODY','BE_WEST_DFI_CASE']
if bpy.data.objects.get('BE_TREE_69773_WOOD'):
    names+=['BE_TREE_69773_WOOD','BE_TREE_69773_TWIGS','BE_TREE_69773_LEAVES']
if bpy.data.objects.get('HB_SIDEWALK_ASPHALT'):
    names+=['HB_SIDEWALK_ASPHALT','HB_SIDEWALK_CURB_FACE','HB_BAY_5_SILL','HB_ENTRY_L_GLASS','HB_BAY_0_GLASS_0','HB_PIER_04_COURSE_03']
if bpy.data.objects.get('HU_MAIN_MEZZ_W00_GLASS'):
    names+=['HU_MAIN_MEZZ_W00_GLASS','HU_MAIN_PIANO_W00_STONE','HU_MAIN_EAVE',
            'HU_CORNER_BALCONY','HU_CORNER_PILASTERS','HU_MAIN_MEZZ_BALCONY_3_SLAB',
            'HU_SOURCE_ROOF_SLATE','HU_SOURCE_ROOF_DORMER_WALL']
if bpy.data.objects.get('HU_OCULUS_0_STONE'):
    names+=['HU_OCULUS_0_STONE','HU_OCULUS_0_GLASS','HU_OCULUS_2_FLASHING']
if bpy.data.objects.get('HB_TREE_119962_WOOD'):
    names+=['HB_TREE_119962_WOOD','HB_TREE_119962_TWIGS','HB_TREE_119962_LEAVES','HU_BALCONY_WALL_PLATES','HU_ROOF_DRUM_RAIL','HU_ROOF_DRUM_BALUSTERS']
if bpy.data.objects.get('CF_MAST_1800_SHAFT'):
    names+=['CF_MAST_1800_SHAFT','CF_INFO_1143_MAIN_FRAME','CF_INFO_2584_RETURN_FRAME',
            'CF_INFO_MAIN_NOTICE_GLASS','CF_INFO_MAIN_NOTICE_PRINT_REVERSE','CF_INFO_NAME_TEXT_REVERSE']
if bpy.data.objects.get('CF2_MAST_1793_SHAFT'):
    names+=['CF2_MAST_1793_SHAFT','CF2_INFO_2120_MAIN_FRAME','CF2_INFO_2585_RETURN_FRAME',
            'CF2_INFO_MAIN_NOTICE_PRINT_REVERSE','CF2_INFO_NAME_TEXT_REVERSE']
if bpy.data.objects.get('BS_ASPHALT'):
    names+=['BS_ASPHALT','BS_CURB_FACE','BS_SOIL','BS_TREE_17167_WOOD','BS_TREE_17167_LEAVES','BS_TREE_68441_WOOD','BS_TREE_68441_LEAVES']
if bpy.data.objects.get('BSF_BIN631_SHEET_SHELL'):
    names+=['BSF_MAST_1799_SHAFT','BSF_MAST_4217_SHAFT','BSF_DFI67_CASE',
            'BSF_INFO_2864_MAIN_FRAME','BSF_INFO_2581_RETURN_FRAME','BSF_INFO_MAIN_NOTICE_PRINT_REVERSE',
            'BSF_BIN631_SHEET_SHELL','BSF_BIN631_CLOSED_SLOPING_LID','BSF_BIN631_DARK_INNER_LINER']
if bpy.data.objects.get('SV_FLOOR_TILES'):
    names+=['SV_FLOOR_TILES','SV_LANDING_ASPHALT','SV_SOURCE_CANOPY_ROOF','SV_SOURCE_SKYLIGHT','SV_SOURCE_FASCIA','SV_CERAMIC_FACE_TILES','SV_ENTRY_WOMEN_LEAF_PANE','SV_WC_0_PAN','SV_CONTINUOUS_BASIN_TOP_W','SV_AD_623_GLASS','SV_BENCH_1592_SLAT_0']
    names += [f'BS_TREE_{ident}_{role}' for ident in [138633,64381,139162] for role in ['WOOD','LEAVES']]
if bpy.data.objects.get('BS_TREE_129634_WOOD'):
    names += [f'BS_TREE_{ident}_{role}' for ident in [129634,36770,53451,121245,60694,65530,114064] for role in ['WOOD','LEAVES']]
if bpy.data.objects.get('BS_TREE_PIT_EXPOSED_ASPHALT_EDGES'):
    names.append('BS_TREE_PIT_EXPOSED_ASPHALT_EDGES')
stack=None
if (ROOT/'evidence'/V/'print_stack.json').exists():
    stack=json.loads((ROOT/'evidence'/V/'print_stack.json').read_text())
elif V in ['G1_016r1','G1_017','G1_017r1','G1_018r3']:
    stack={'gaps':[{'name':o.name} for o in col.all_objects if o.name.startswith('SV_AD_') and any(k in o.name for k in ['_TEXT_','_ART_LINE_','_FOOT'])]}
    assert len(stack['gaps'])==60
if stack:
    names+=['SV_SOURCE_SOFFIT',*[p['name'] for p in stack['gaps']]]
if bpy.data.objects.get('BSE_MAST_4211_SHAFT'):
    names += [o.name for o in bpy.data.collections['26_BELLEVUE_SOUTH_EAST_FACILITIES'].objects if o.type in ['MESH','CURVE','FONT']]
if bpy.data.objects.get('F59_ROOT'):
    names += [o.name for o in bpy.data.collections['27_BELLEVUE_FOUNTAIN_59'].objects if o.type in ['MESH','CURVE','FONT']]
expected_names={o.name for o in col.all_objects if o.type in ['MESH','CURVE','FONT','EMPTY']}
def native_bounds(ob):
    evaluated=ob.evaluated_get(deps);me=evaluated.to_mesh()
    vv=np.array([list(ob.matrix_world@v.co) for v in me.vertices]);evaluated.to_mesh_clear()
    return np.r_[vv.min(axis=0),vv.max(axis=0)]
expected={n:native_bounds(bpy.data.objects[n]) for n in names}
uv_ranges={}
if V in ['G1_016r1','G1_017','G1_017r1','G1_018r3']:
    repairs=json.loads((ROOT/'evidence/G1_016r1/surface_repair.json').read_text())
    for item in repairs['corrected_tree_uvs']:
        name=item['object'];me=bpy.data.objects[name].data
        slots={i for i,m in enumerate(me.materials) if m and m.name.startswith('HB | continuous plane trunk atlas')}
        values=[me.uv_layers.active.data[li].uv.y for p in me.polygons if p.material_index in slots for li in p.loop_indices]
        uv_ranges[name]=(min(values),max(values))
before=set(bpy.data.objects);qa=bpy.data.scenes.new('TEMP_BELLEVUE_ROUNDTRIP');bpy.context.window.scene=qa
report={'version':V,'matches':[]}
try:
    bpy.ops.import_scene.gltf(filepath=str(ROOT/f'web/assets/{V}_bellevue.glb'));bpy.context.view_layer.update()
    imported=list(set(bpy.data.objects)-before);identities={o.get('native_object') for o in imported if 'native_object' in o}
    assert expected_names==identities, f'Missing or extra authored objects: {expected_names^identities}'
    report['identities_verified']=len(identities)
    for name,old in expected.items():
        roots=[o for o in imported if o.get('native_object')==name];assert len(roots)==1
        vertices=[]
        for ob in [roots[0],*roots[0].children_recursive]:
            if ob.type=='MESH':vertices.extend([list(ob.matrix_world@v.co) for v in ob.data.vertices])
        vv=np.array(vertices);new=np.r_[vv.min(axis=0),vv.max(axis=0)];error=float(abs(new-old).max())
        assert error<.002, f'{name}: {error}m geometry drift'
        report['matches'].append({'name':name,'max_error_m':error})
    if uv_ranges:
        report['upper_trunk_uv_checks']=[]
        for name,expected_uv in uv_ranges.items():
            root=next(o for o in imported if o.get('native_object')==name);values=[]
            for ob in [root,*root.children_recursive]:
                if ob.type!='MESH':continue
                me=ob.data;slots={i for i,m in enumerate(me.materials) if m and m.name.startswith('HB | continuous plane trunk atlas')}
                values.extend(me.uv_layers.active.data[li].uv.y for p in me.polygons if p.material_index in slots for li in p.loop_indices)
            assert values,name
            actual=(min(values),max(values));error=max(abs(a-b) for a,b in zip(actual,expected_uv));assert error<.000001,(name,actual,expected_uv)
            report['upper_trunk_uv_checks'].append({'name':name,'max_v':actual[1],'max_uv_roundtrip_error':error})
    if stack:
        from mathutils import Vector
        roof=next(o for o in imported if o.get('native_object')=='SV_SOURCE_SOFFIT')
        normal_values=[]
        for ob in [roof,*roof.children_recursive]:
            if ob.type=='MESH':
                normal_matrix=ob.matrix_world.to_3x3().inverted().transposed()
                normal_values.extend((normal_matrix@p.normal).normalized().z for p in ob.data.polygons)
        assert normal_values and max(normal_values)<-.999,'Export changed soffit outward side'
        spec=json.loads((ROOT/'derived/bellevue/south_service/input.json').read_text())
        direction=np.asarray([*spec['axis_v'],0.])
        def depth_range(name):
            root=next(o for o in imported if o.get('native_object')==name)
            values=[]
            for ob in [root,*root.children_recursive]:
                if ob.type=='MESH':values.extend(float(direction@np.asarray(ob.matrix_world@v.co)) for v in ob.data.vertices)
            return min(values),max(values)
        gaps=[]
        for item in stack['gaps']:
            name=item['name'];prefix='_'.join(name.split('_')[:3]);lo,hi=depth_range(name)
            above=lo-depth_range(prefix+'_ART')[1];clearance=depth_range(prefix+'_GLASS')[0]-hi
            assert above>.0001 and clearance>.0001,(name,above,clearance)
            gaps.append({'name':name,'above_art_m':above,'glass_clearance_m':clearance})
        report['surface_stack']={'soffit_normals_max_z':max(normal_values),'print_parts_checked':len(gaps),
            'min_above_art_m':min(x['above_art_m'] for x in gaps),'min_glass_clearance_m':min(x['glass_clearance_m'] for x in gaps)}
finally:
    bpy.context.window.scene=original
    for ob in list(set(bpy.data.objects)-before):bpy.data.objects.remove(ob,do_unlink=True)
    bpy.data.scenes.remove(qa)
bpy.ops.wm.open_mainfile(filepath=record['native'])
assert bpy.context.scene['version']==V
missing=[i.name for i in bpy.data.images if i.source=='FILE' and not i.packed_file and i.filepath and not Path(bpy.path.abspath(i.filepath)).exists()]
assert not missing, missing
report.update(native_reopen_verified=True,missing_images=missing,accepted=False,full_G1_complete=False)
(ROOT/'evidence'/V/'roundtrip.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
