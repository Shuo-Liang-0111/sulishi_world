"""Apply the reviewed hardware construction at the second actual platform endpoint."""
import bpy,json,math,numpy as np,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_012r3';old=json.loads((R/'derived/bellevue/corner_fixtures/input.json').read_text());d=json.loads((R/'derived/bellevue/west_end_fixtures/input.json').read_text());O=np.array(d['origin']);name='20_BELLEVUE_WEST_END_FIXTURES';assert name not in bpy.data.collections;col=bpy.data.collections.new(name);bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(col)
def point(rec,kind):return np.r_[np.array(rec[kind]['geometry']['coordinates'][0])-O[:2],rec['mast_ground_local']]
mc=point(old,'mast');nc=point(d,'mast');scale=(d['mast']['properties']['hoehemastok']-O[2]-nc[2])/(old['mast']['properties']['hoehemastok']-O[2]-mc[2]);M_m=Matrix.Translation(Vector(nc))@Matrix.Diagonal((1,1,scale,1))@Matrix.Translation(Vector(-mc))
a=np.r_[np.array(old['information'][0]['geometry']['coordinates'][0])-O[:2],old['info_ground_local']];b=np.r_[np.array(d['information'][0]['geometry']['coordinates'][0])-O[:2],d['info_ground_local']]
def move(axis):
 angle=math.atan2(d[axis][1],d[axis][0])-math.atan2(old[axis][1],old[axis][0]);return Matrix.Translation(Vector(b))@Matrix.Rotation(angle,4,'Z')@Matrix.Translation(Vector(-a))
Mu,Mv=move('u'),move('v');newmap=bpy.data.materials['CF | original Bellevue neighborhood notice'].copy();newmap.name='CF2 | endpoint-specific Bellevue map';image=bpy.data.images.load(str(R/'derived/bellevue/west_end_fixtures/neighborhood_map.png'),check_existing=True)
for n in newmap.node_tree.nodes:
 if n.type=='TEX_IMAGE':n.image=image
names=[]
for ob in list(bpy.data.collections['19_BELLEVUE_CORNER_FIXTURES'].objects):
 if ob.type not in ['MESH','CURVE','FONT']:continue
 dup=ob.copy();dup.data=ob.data.copy();dup.name=ob.name.replace('CF_','CF2_',1).replace('MAST_1800','MAST_1793').replace('INFO_1143','INFO_2120').replace('INFO_2584','INFO_2585');col.objects.link(dup)
 if ob.name.startswith('CF_MAST_'):M=M_m;dup['source_id']='fahrleitungen_mast.1793'
 else:
  side=('_RETURN_' in ob.name or '_SIDE_LOW_' in ob.name or ob.name in ['CF_INFO_GROUND_SLEEVE_2','CF_INFO_GROUND_PATCH_2']);M=Mv if side else Mu;dup['source_id']='haltestellen_infosystem.2120+2585'
  for i,m in enumerate(dup.data.materials):
   if m is bpy.data.materials['CF | original Bellevue neighborhood notice']:dup.data.materials[i]=newmap
 dup.matrix_world=M@ob.matrix_basis;dup['place']='Bellevue west platform opposite endpoint';dup['evidence_basis']='Same recorded equipment family74/88 as first pair; shape is still inferred from VBZ tube standards. Own source XY/orientation, reconstructed platform ground and original locally recentered notice. Mast1793 top420.2m preserved.';names.append(dup.name)

cutpath=R/'derived/bellevue/west_context/west_end_fixture_photo_cut.json';cut=json.loads(cutpath.read_text());ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};orig={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for p in cut['overrides']:
 ob=ctx[str(p['node'])];src=orig[str(p['node'])];vv=np.array(p['vertices']);uvv=np.array(p['uv_source_v_unflipped']);me=bpy.data.meshes.new('CF2_CONTEXT_'+str(p['node']));me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.astype(np.float32).reshape(-1));ob.data=me;ob['construction_mask']=cut['mask_basis']
xy=b[:2]-np.array(d['v'])*5.5+np.array(d['u'])*2;grounds=[]
for ob in bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].all_objects:
 if ob.type=='MESH' and (ob.name.startswith('BE_PAVING_') or ob.name in ['BE_WEST_PLATFORM','HB_SIDEWALK_ASPHALT']):
  hit,p,_,_=ob.ray_cast(Vector((*xy,40)),Vector((0,0,-1)))
  if hit:grounds.append(p.z)
assert grounds;cd=bpy.data.cameras.new('BE_QA_WEST_END_FIXTURES');co=bpy.data.objects.new(cd.name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(co);co.location=(*xy,max(grounds)+1.65);co.rotation_euler=(Vector(b+np.r_[np.array(d['u'])*.3,1.7])-co.location).to_track_quat('-Z','Y').to_euler();cd.lens=32;co['eye_height_m']=1.65
s['version']='G1_012r4';s['photo_cut_file']=str(cutpath.relative_to(R));s.camera=co;bpy.context.view_layer.update();bpy.ops.file.pack_all();native=R/'native/G1_012r4_platform_fixtures_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native));rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=s['version'],native=str(native),source_cut_file=s['photo_cut_file'],source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2));e=R/'evidence/G1_012r4';e.mkdir(exist_ok=True);(e/'construction.json').write_text(json.dumps({'version':s['version'],'native':str(native),'new_endpoint_objects':len(names),'total_fixture_objects':len(names)+len(bpy.data.collections['19_BELLEVUE_CORNER_FIXTURES'].objects),'source_ids':[d['mast']['id'],*[x['id'] for x in d['information']]],'inferred_subtypes':True,'accepted':False},indent=2));print(json.dumps({'version':s['version'],'new_objects':len(names)}))
