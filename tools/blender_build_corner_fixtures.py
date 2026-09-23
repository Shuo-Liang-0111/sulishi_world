"""Physical mast and provisional information assembly at actual inventory anchors."""
import bpy,bmesh,json,math,ast,numpy as np,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_011r4';d=json.loads((R/'derived/bellevue/corner_fixtures/input.json').read_text());origin=np.array(d['origin']);name='19_BELLEVUE_CORNER_FIXTURES';assert name not in bpy.data.collections
building=bpy.data.collections.new(name);bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(building)
defs=ast.parse((R/'tools/blender_build_bellevue.py').read_text());exec(compile(ast.Module(body=[n for n in defs.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','box','lathe','tube']],type_ignores=[]),'geometry_helpers','exec'))
C=np.array(d['mast']['geometry']['coordinates'][0])-origin[:2];FLOOR=d['mast_ground_local'];right=np.array([1.,0.]);front=np.array([0.,1.])
def P(u,v,z):return (*list(C+right*u+front*v),FLOOR+z)
def mat(name,color,rough=.5,metal=0,trans=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal;b.inputs['Transmission Weight'].default_value=trans;b.inputs['IOR'].default_value=1.48;return m
paint=mat('CF | aged satin grey painted steel',(.24,.28,.27),.51,.15);edge=mat('CF | exposed zinc fixings',(.35,.38,.365),.37,.82);black=mat('CF | elastomer seal',(.012,.016,.015),.83);white=mat('CF | warm enamel',(.76,.775,.75),.42,.08);blue=mat('CF | VBZ blue enamel',(.014,.078,.18),.40,.1);paper=mat('CF | notice paper',(.82,.825,.785),.9);glass=mat('CF | notice cover glass',(.97,.988,.982),.065,0,1)
top=d['mast']['properties']['hoehemastok']-origin[2]
lathe('CF_MAST_1800_SHAFT',[(0,FLOOR-.13),(.166,FLOOR-.13),(.166,FLOOR+.13),(.139,FLOOR+.26),(.126,FLOOR+2.2),(.10,FLOOR+6.5),(.078,top-.05),(.078,top),(0,top)],paint,world_center=C.tolist(),steps=64)
for i,h in enumerate([.14,.32,2.20,6.45,9.1]):
 rr=[.17,.144,.13,.106,.092][i];lathe('CF_MAST_1800_COLLAR_'+str(i),[(rr-.006,FLOOR+h-.022),(rr+.004,FLOOR+h-.016),(rr+.004,FLOOR+h+.019),(rr-.006,FLOOR+h+.027)],edge,world_center=C.tolist(),steps=40)
box('CF_MAST_1800_ACCESS_RECESS',(0,-.129,.82),(.158,.019,.46),black,.018);box('CF_MAST_1800_ACCESS_COVER',(0,-.140,.82),(.147,.012,.443),paint,.015)
for z in [.637,1.003]:tube('CF_MAST_1800_COVER_SCREW_'+str(z),[P(0,-.148,z),P(0,-.152,z)],.008,edge)
for ob in building.objects:
 ob['source_id']=d['mast']['id'];ob['evidence_basis']='Source XY and top420.5m; mast shape and ground sleeve inferred. Source base408.75 differs from local reconstructed grade.'

C=np.array(d['information'][0]['geometry']['coordinates'][0])-origin[:2];FLOOR=d['info_ground_local'];right=np.array(d['u']);front=np.array(d['v']);r=.075;w=.70
def path_u(height):
 pts=[P(0,0,-.14),P(0,0,height-r)]
 pts += [P(r-r*math.cos(t),0,height-r+r*math.sin(t)) for t in np.linspace(0,math.pi/2,13)[1:]]
 pts += [P(w-r,0,height)]
 pts += [P(w-r+r*math.sin(t),0,height-r+r*math.cos(t)) for t in np.linspace(0,math.pi/2,13)[1:]]
 pts += [P(w,0,-.14)];return pts
tube('CF_INFO_1143_MAIN_FRAME',path_u(3.15),.027,paint)
# The perpendicular shorter return shares the tall frame's first upright.
pts=[P(0,.032,2.10),P(0,w-r,2.10)]+[P(0,w-r+r*math.sin(t),2.10-r+r*math.cos(t)) for t in np.linspace(0,math.pi/2,13)[1:]]+[P(0,w,-.14)]
tube('CF_INFO_2584_RETURN_FRAME',pts,.027,paint)
for idx,(u,v) in enumerate([(0,0),(w,0),(0,w)]):
 tube('CF_INFO_GROUND_SLEEVE_'+str(idx),[P(u,v,-.04),P(u,v,.10)],.03,black)
 box('CF_INFO_GROUND_PATCH_'+str(idx),(u,v,-.008),(.16,.16,.02),bpy.data.materials['asphalt_03'],.018)
tube('CF_INFO_MAIN_LOW_RAIL',[P(0,0,.23),P(w,0,.23)],.023,paint);tube('CF_INFO_SIDE_LOW_RAIL',[P(0,0,.23),P(0,w,.23)],.023,paint)
for z in [.27,2.08]:
 box('CF_INFO_SHARED_CLAMP_'+str(z),(.014,.021,z),(.084,.08,.071),edge,.008)
 for xx in [-.026,.054]:tube('CF_INFO_SHARED_BOLT_'+str((z,xx)),[P(xx,-.023,z),P(xx,-.03,z)],.008,edge)

mapmat=mat('CF | original Bellevue neighborhood notice',(.8,.8,.8),.85);bs=next(n for n in mapmat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');tex=mapmat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(R/'derived/bellevue/corner_fixtures/neighborhood_map.png'),check_existing=True);mapmat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);mapmat['basis']=d['inferred']['sign_faces']
def notice(prefix,u,v,z,width,height):
 box(prefix+'_BACK',(u,v,z),(width,.040,height),white,.012)
 for x in [-1,1]:box(prefix+'_FRAME_'+str(x),(u+x*(width/2-.016),v+.025,z),(.025,.025,height-.015),paint,.004)
 for zz in [-1,1]:box(prefix+'_HFRAME_'+str(zz),(u,v+.025,z+zz*(height/2-.016)),(width,.025,.025),paint,.004)
 box(prefix+'_GASKET',(u,v+.026,z),(width-.044,.008,height-.044),black,.002)
 verts=[P(u-width/2+.028,v+.031,z-height/2+.028),P(u+width/2-.028,v+.031,z-height/2+.028),P(u+width/2-.028,v+.031,z+height/2-.028),P(u-width/2+.028,v+.031,z+height/2-.028)]
 ob=mesh(prefix+'_PRINT',verts,[(0,1,2,3)],mapmat);uv=ob.data.uv_layers.new(name='notice');uv.data.foreach_set('uv',np.array([(0,0),(1,0),(1,1),(0,1)],dtype=np.float32).reshape(-1))
 box(prefix+'_GLASS',(u,v+.035,z),(width-.044,.004,height-.044),glass,.001)
 for zz in [-.32,.32]:box(prefix+'_HINGE_'+str(zz),(u-width/2-.008,v+.018,z+zz),(.016,.033,.075),edge,.004)
 tube(prefix+'_KEYHOLE',[P(u+width/2-.019,v+.041,z),P(u+width/2-.019,v+.046,z)],.006,edge)
notice('CF_INFO_MAIN_NOTICE',.35,0,1.65,.627,.97)
# Stop title is modeled lettering on a thick enamel plate, not pasted source photography.
box('CF_INFO_NAME_BOARD',(.35,0,2.82),(.628,.047,.27),blue,.013)
def label(name,body,u,v,z,size,material):
 cu=bpy.data.curves.new(name,'FONT');cu.body=body;cu.size=size;cu.extrude=.00035;cu.resolution_u=4;cu.font=bpy.data.fonts.load('C:/Windows/Fonts/arial.ttf');ob=bpy.data.objects.new(name,cu);building.objects.link(ob);ob.location=P(u,v,z);x=Vector((*right,0));y=Vector((0,0,1));ob.rotation_euler=Matrix((x,y,x.cross(y))).transposed().to_euler();cu.materials.append(material);return ob
label('CF_INFO_NAME_TEXT','Bellevue',.069,.026,2.80,.121,white)
box('CF_INFO_MODE_BOARD',(.35,0,2.60),(.628,.046,.13),white,.008);label('CF_INFO_MODE_TEXT','Tram / Bus',.09,.026,2.57,.068,blue)
oldright=right.copy();oldfront=front.copy();right=oldfront;front=-oldright
notice('CF_INFO_RETURN_NOTICE',.36,0,1.53,.627,.97)
box('CF_INFO_RETURN_TITLE_BOARD',(.36,0,2.032),(.627,.043,.085),blue,.008);label('CF_INFO_RETURN_TITLE','Umgebung',.065,.025,2.011,.058,white)
right=oldright;front=oldfront
for ob in building.objects:
 if 'egid' in ob:del ob['egid']
 ob['place']='Bellevue west platform source corner';ob['quality_status']='working_not_accepted';ob['collision_role']='solid_pending_runtime';ob['kind']='reconstructed_public_infrastructure'
 if not ob.name.startswith('CF_MAST_'):
  ob['source_id']='haltestellen_infosystem.1143+2584';ob['evidence_basis']='Source shared XY and two orientation values. Tube-frame dimensions from existing VBZ2016 installation drawings; exact assembly/anchor convention and posted graphics inferred, no current timetable claimed.'

cutpath=R/'derived/bellevue/west_context/corner_fixture_photo_cut.json';cut=json.loads(cutpath.read_text());ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};orig={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for p in cut['overrides']:
 ob=ctx[str(p['node'])];src=orig[str(p['node'])];vv=np.array(p['vertices']);uvv=np.array(p['uv_source_v_unflipped']);me=bpy.data.meshes.new('CF_CONTEXT_'+str(p['node']));me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.astype(np.float32).reshape(-1));ob.data=me;ob['construction_mask']=cut['mask_basis']

xy=C-front*5.5+right*2;grounds=[]
for ob in bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].all_objects:
 if ob.type=='MESH' and (ob.name.startswith('BE_PAVING_') or ob.name in ['BE_WEST_PLATFORM','HB_SIDEWALK_ASPHALT']):
  hit,p,_,_=ob.ray_cast(Vector((*xy,40)),Vector((0,0,-1)))
  if hit:grounds.append(p.z)
assert grounds,'Review camera must be over constructed ground'
cd=bpy.data.cameras.new('BE_QA_CORNER_FIXTURES');co=bpy.data.objects.new(cd.name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(co);co.location=(*xy,max(grounds)+1.65);target=Vector((*list(C+right*.3),FLOOR+1.7));co.rotation_euler=(target-co.location).to_track_quat('-Z','Y').to_euler();cd.lens=44;co['eye_height_m']=1.65
s['version']='G1_012';s['photo_cut_file']=str(cutpath.relative_to(R));s.camera=co;bpy.context.view_layer.update();bpy.ops.file.pack_all();native=R/'native/G1_012_corner_fixtures_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=s['version'],native=str(native),source_cut_file=s['photo_cut_file'],source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True,next='Inspect corner fixture front/back, camera approach and residual photographed base fragments; exact info type mapping remains unknown.');(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2))
e=R/'evidence/G1_012';e.mkdir(exist_ok=True);report={'version':s['version'],'native':str(native),'objects':len(building.objects),'inventory_ids':['fahrleitungen_mast.1800','haltestellen_infosystem.1143','haltestellen_infosystem.2584'],'fixture_subtypes_inferred':True,'accepted':False};(e/'construction.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
