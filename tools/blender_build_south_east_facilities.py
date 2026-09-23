"""Build three source-located east-side assemblies using reviewed fabrication."""
import bpy,bmesh,json,math,ast,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version']=='G1_015r3'
D=R/'derived/bellevue/south_context/east_facilities'
d=json.loads((D/'input.json').read_text());info=d['information']
old=json.loads((R/'derived/bellevue/corner_fixtures/input.json').read_text())
old_bin=json.loads((R/'derived/bellevue/south_context/fixtures_input.json').read_text())['bin']
O=np.asarray(d['origin']);name='26_BELLEVUE_SOUTH_EAST_FACILITIES'
assert name not in bpy.data.collections
building=bpy.data.collections.new(name);bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(building)
def anchor(src,z):return Vector((*list(np.asarray(src['geometry']['coordinates'][0])-O[:2]),z))
def clone(ob,name,matrix,source,basis):
    result=ob.copy();result.data=ob.data.copy();result.name=name;building.objects.link(result)
    result.parent=None
    result.matrix_world=matrix@ob.matrix_world
    for key in ['egid','derived_source_sha256']:
        if key in result:del result[key]
    result['source_id']=source;result['evidence_basis']=basis
    result['place']='Bellevue AV3573 east facilities';result['quality_status']='working_unaccepted'
    result['collision_role']='solid_pending_runtime'
    return result

# Anchors must hit the current actual native ground, not only a planning plane.
ground=bpy.data.objects['BS_ASPHALT'];support={}
for key,src,z in [('mast',d['mast']['source'],d['mast']['ground_local']),
                  ('info',info['information'][0],info['info_ground_local']),
                  ('bin',d['bin']['source'],d['bin']['ground_local'])]:
    position=anchor(src,z);hit,p,normal,index=ground.ray_cast(Vector((position.x,position.y,40)),Vector((0,0,-1)))
    assert hit and abs(p.z-z)<.003,(key,hit,p.z,z)
    support[key]=float(p.z)

source_pole=anchor(old['mast'],old['mast_ground_local']);target_pole=anchor(d['mast']['source'],support['mast'])
translation=Matrix.Translation(target_pole-source_pole)
for ob in bpy.data.collections['19_BELLEVUE_CORNER_FIXTURES'].objects:
    if ob.name.startswith('CF_MAST_') and not ob.name.endswith('_SHAFT'):
        clone(ob,ob.name.replace('CF_MAST_1800','BSE_MAST_4211'),translation,d['mast']['source']['id'],
              'Official XY and top; reviewed collar/access hatch dimensions retained without height scaling. Shaft family and fabrication inferred.')
defs=ast.parse((R/'tools/blender_build_bellevue.py').read_text())
exec(compile(ast.Module(body=[n for n in defs.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','lathe']],type_ignores=[]),'pole_geometry','exec'))
top=d['mast']['source']['properties']['hoehemastok']-O[2];floor=support['mast'];C=np.asarray(target_pole[:2])
paint=bpy.data.materials['CF | metre-scale satin coat']
shaft=lathe('BSE_MAST_4211_SHAFT',[(0,floor-.13),(.166,floor-.13),(.166,floor+.13),(.139,floor+.26),(.126,floor+2.2),(.10,floor+6.5),(.078,top-.05),(.078,top),(0,top)],paint,world_center=C.tolist(),steps=64)
uv=shaft.data.uv_layers.new(name='physical_metre_coordinates')
for face in shaft.data.polygons:
    pts=np.array([shaft.data.vertices[shaft.data.loops[i].vertex_index].co[:] for i in face.loop_indices]);angles=np.unwrap(np.arctan2(pts[:,1]-C[1],pts[:,0]-C[0]))
    for j,li in enumerate(face.loop_indices):uv.data[li].uv=(float(angles[j]*.14),float(pts[j,2]-floor))
shaft['source_id']=d['mast']['source']['id'];shaft['evidence_basis']='Actual mast4211 XY and LN02 top418.93m. Inferred taper on current grade; access parts retain their fabrication dimensions.'
if 'egid' in shaft:del shaft['egid']
shaft['place']='Bellevue AV3573 east facilities'
shaft['collision_role']='solid_pending_runtime'

source_info=anchor(old['information'][0],old['info_ground_local']);target_info=anchor(info['information'][0],support['info'])
def move(axis):
    a=math.atan2(info[axis][1],info[axis][0])-math.atan2(old[axis][1],old[axis][0])
    return Matrix.Translation(target_info)@Matrix.Rotation(a,4,'Z')@Matrix.Translation(-source_info)
main,side=move('u'),move('v')
original_map=bpy.data.materials['CF | original Bellevue neighborhood notice'];new_map=original_map.copy();new_map.name='BSE | east-anchor neighborhood map'
image=bpy.data.images.load(str(D/'info/neighborhood_map.png'),check_existing=True)
for node in new_map.node_tree.nodes:
    if node.type=='TEX_IMAGE':node.image=image
for ob in bpy.data.collections['19_BELLEVUE_CORNER_FIXTURES'].objects:
    if not ob.name.startswith('CF_INFO_'):continue
    return_side=('_RETURN_' in ob.name or '_SIDE_LOW_' in ob.name or ob.name in ['CF_INFO_GROUND_SLEEVE_2','CF_INFO_GROUND_PATCH_2'])
    copy=clone(ob,ob.name.replace('CF_','BSE_',1).replace('INFO_1143','INFO_2717').replace('INFO_2584','INFO_2580'),side if return_side else main,
               'haltestellen_infosystem.2717+2580','Actual shared XY and source bearings. Reviewed tubular frame family; type74/88 interpretation and anchor convention inferred. New locally centred AV map, no departure claims.')
    for i,material in enumerate(copy.data.materials):
        if material==original_map:copy.data.materials[i]=new_map

source_bin=anchor(old_bin['source'],old_bin['ground_local']);target_bin=anchor(d['bin']['source'],support['bin'])
angle=math.radians(float(old_bin['source']['properties']['orientierung'])-float(d['bin']['source']['properties']['orientierung']))
bin_transform=Matrix.Translation(target_bin)@Matrix.Rotation(angle,4,'Z')@Matrix.Translation(-source_bin)
bin_names=[]
for ob in bpy.data.collections['23_BELLEVUE_SOUTH_FIXTURES'].objects:
    if ob.name.startswith('BSF_BIN631_'):
        copy=clone(ob,ob.name.replace('BSF_BIN631_','BSE_BIN1173_'),bin_transform,d['bin']['source']['id'],
         'Official Haifisch bin XY/bearing; reviewed110L family with3mm sheet, open deposit slot and separate liner. Installed volume variant and use marks inferred.')
        bin_names.append(copy.name)
assert bin_names

cut_path=R/d['cut_file'];assert hashlib.sha256(cut_path.read_bytes()).hexdigest()==d['cut_sha256']
cut=json.loads(cut_path.read_text());context={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
originals={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
assert len(originals)==2039
for item in cut['overrides']:
    ob=context[str(item['node'])];src=originals[str(item['node'])];vv=np.asarray(item['vertices']).reshape(-1,3);uvs=np.asarray(item['uv_source_v_unflipped']).reshape(-1,2)
    me=bpy.data.meshes.new('BSE_CONTEXT_'+str(item['node']));me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
    for material in src.data.materials:me.materials.append(material)
    uv=me.uv_layers.new(name='source_photo_uv');uvs[:,1]=1-uvs[:,1];uv.data.foreach_set('uv',uvs.astype(np.float32).ravel())
    ob.data=me;ob['construction_mask']=cut['mask_basis']

camera_records=[]
for suffix,centre,offset,height in [('INFO',target_info,Vector((-3.5,3,0)),1.6),('BIN',target_bin,Vector((2.4,1.3,0)),.68),('REVERSE',target_info,Vector((3,-2.6,0)),1.5)]:
    position=centre+offset;hit,p,_,_=ground.ray_cast(Vector((position.x,position.y,40)),Vector((0,0,-1)))
    assert hit,('Review camera off ground',suffix)
    name='BE_QA_SOUTH_EAST_'+suffix;data=bpy.data.cameras.new(name);ob=bpy.data.objects.new(name,data);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(ob)
    ob.location=(position.x,position.y,p.z+1.65);target=Vector((centre.x,centre.y,centre.z+height))
    ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler();data.lens=38;ob['eye_height_m']=1.65;camera_records.append(name)
bpy.context.view_layer.update()
assert abs(max((shaft.matrix_world@v.co).z for v in shaft.data.vertices)-top)<.0001
s['version']='G1_016';s['photo_cut_file']=d['cut_file'];native=R/'native/G1_016_south_east_facilities_working.blend'
s.camera=bpy.data.objects[camera_records[0]];bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(native))
w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=s['version'],native=str(native),source_cut_file=d['cut_file'],source_cut_sha256=d['cut_sha256'],source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True)
(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2))
report={'version':s['version'],'native':str(native),'new_objects':len(building.objects),'source_ids':[d['mast']['source']['id'],'haltestellen_infosystem.2717','haltestellen_infosystem.2580',d['bin']['source']['id']],
        'ground_local':support,'source_mast_top_ln02':top+400,'bin_parts':len(bin_names),'cameras':camera_records,'photo_source_originals_preserved':2039,'visual_and_use_acceptance':False}
E=R/'evidence'/s['version'];E.mkdir(exist_ok=True);(E/'construction.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
