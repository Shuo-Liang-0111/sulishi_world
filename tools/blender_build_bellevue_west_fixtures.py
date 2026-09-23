"""Source-located station fixtures, with uncertain fabrication explicitly tagged."""
import bpy,bmesh,json,math,ast,hashlib
import numpy as np
from mathutils import Vector,Matrix
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version']=='G1_008r2'
path=ROOT/'derived/bellevue/west_context/fixtures_input.json';data=json.loads(path.read_text(encoding='utf-8'))
digest=hashlib.sha256(path.read_bytes()).hexdigest();ORIGIN=np.array([2683775,1246700])
name='14_BELLEVUE_WEST_FACILITIES'
assert not bpy.data.collections.get(name),'Do not duplicate a partially executed build.'
building=bpy.data.collections.new(name);bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(building)
tree=ast.parse((ROOT/'tools/blender_build_bellevue.py').read_text());defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','box','lathe','tube']]
exec(compile(ast.Module(body=defs,type_ignores=[]),'geometry_helpers','exec'))
platform=json.loads((ROOT/'derived/bellevue/west_context/platform_input.json').read_text());tt=np.array(platform['parts']['platform']);centres=tt[:,:,:2].mean(axis=1)
def ground(xy):
 for i in np.argsort(np.linalg.norm(centres-xy,axis=1))[:100]:
  t=tt[i];a=(t[1:,:2]-t[0,:2]).T
  if abs(np.linalg.det(a))<1e-10:continue
  w=np.linalg.solve(a,xy-t[0,:2])
  if min(w)>=-1e-6 and sum(w)<=1.000001:return float(t[0,2]+w@(t[1:,2]-t[0,2]))
 raise ValueError('Facility support outside reconstructed platform')
def frame(xy,axis):
 global C,right,front,FLOOR
 C=np.array(xy)-ORIGIN;right=np.array(axis);right=right/np.linalg.norm(right);front=np.array([-right[1],right[0]]);FLOOR=ground(C)
def P(u,v,z):
 xy=C+right*u+front*v;return (float(xy[0]),float(xy[1]),float(FLOOR+z))
def material(name,color,rough=.5,metal=0,emission=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal
 if emission:n.inputs['Emission Color'].default_value=(*color,1);n.inputs['Emission Strength'].default_value=emission
 m.diffuse_color=(*color,1);return m
metal=bpy.data.materials['BE | satin anodised aluminium'];dark=bpy.data.materials['BE | dark structural metal'];wood=bpy.data.materials['oak_veneer_01'];glass=bpy.data.materials['BE | clear curved 12mm glass']
grey=material('BE | VBZ painted grey housing',(.46,.47,.455),.53,.12)
blue=material('BE | ZVV control blue',(.007,.125,.31),.48,.05)
black=material('BE | equipment black gasket',(.006,.007,.008),.71)
paper=material('BE | equipment warm white',(.73,.72,.68),.77)
ink=material('BE | equipment dark ink',(.009,.018,.029),.82)
yellow=material('BE | ZVV UI selection yellow',(.65,.71,.05),.59,0,.1)
screen=material('BE | equipment LCD pale',(.41,.51,.60),.23,0,.16)
display=material('BE | DFI dark face',(.008,.012,.013),.22)
amber=material('BE | DFI muted amber lettering',(.55,.27,.025),.42,0,.6)
posters=[material('BE | inferred poster teal',(.014,.135,.155),.78),material('BE | inferred poster coral',(.43,.09,.045),.8),material('BE | inferred poster blue',(.032,.062,.18),.78)]
def text_obj(name,body,u,v,z,size,mat,side=1):
 cu=bpy.data.curves.new(name,'FONT');cu.body=body;cu.size=size;cu.extrude=0;cu.align_y='BOTTOM_BASELINE';cu.resolution_u=4
 ob=bpy.data.objects.new(name,cu);building.objects.link(ob);ob.location=P(u,v,z)
 x=Vector((*right*side,0));y=Vector((0,0,1));normal=x.cross(y)
 ob.rotation_euler=Matrix((x,y,normal)).transposed().to_euler();cu.materials.append(mat)
 bpy.context.view_layer.update();me=bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()));replacement=bpy.data.objects.new(name+'_MESH',me);building.objects.link(replacement);replacement.matrix_world=ob.matrix_world.copy();replacement['label_text']=body
 bpy.data.objects.remove(ob,do_unlink=True);replacement.name=name;return replacement
def tag_since(old,source,basis,role):
 for ob in building.objects:
  if ob.name in old:continue
  ob['source_id']=source;ob['evidence_basis']=basis;ob['facility_role']=role
  ob['place']='Bellevue_Raemistrasse_2015_shelter';ob['egid']=302063027;ob['derived_source_sha256']=digest;ob['quality_status']='working reconstruction; physical use and final appearance not accepted'
def bolt(name,u,v,z):
 return lathe(name,[(0,z),(.009,z),(.009,z+.006),(0,z+.006)],metal,center=(u,v),steps=6)

# The source bench point is an assembly anchor, not permission to intersect the ads.
for ob in list(bpy.data.collections['13_BELLEVUE_WEST_SHELTER'].objects):
 if ob.name.startswith('BE_WEST_BENCH_'):bpy.data.objects.remove(ob,do_unlink=True)
row=data['ad_row'];frame(row['centres_lv95'][1],row['axis']);anchor_floor=FLOOR
starts=set(building.objects.keys())
for i,xy in enumerate(row['centres_lv95']):
 old=set(building.objects.keys());frame(xy,row['axis']);FLOOR=anchor_floor
 # Three physical framed panels. No unsupported extension wings are added.
 box(f'BE_WEST_AD_{i}_CORE',(0,0,1.29),(1.195,.074,1.78),grey,.009)
 for side in [-1,1]:
  box(f'BE_WEST_AD_{i}_PAPER_{side}',(0,side*.038,1.29),(1.135,.002,1.72),posters[i],.001)
  box(f'BE_WEST_AD_{i}_GLASS_{side}',(0,side*.043,1.29),(1.14,.005,1.725),glass,.001)
  for sign in [-1,1]:box(f'BE_WEST_AD_{i}_VFRAME_{side}_{sign}',(sign*.582,side*.042,1.29),(.03,.020,1.78),metal,.003)
  for height in [.415,2.165]:box(f'BE_WEST_AD_{i}_HFRAME_{side}_{height}',(0,side*.042,height),(1.19,.020,.03),metal,.003)
 # Original typographic designs are editable geometry, not unlicensed site photos.
 for side in [1,-1]:
  v=-side*.0396;u=-.47*side
  for k,line in enumerate([['Zürich','am Wasser'],['Zu Fuss','durch die Stadt'],['Unterwegs','in Zürich']][i]):text_obj(f'BE_WEST_AD_{i}_TEXT_{side}_{k}',line,u,v,1.92-k*.17,.132 if i!=2 else .112,paper,side)
  for k in range(5):
   zz=.79+k*.11;points=[P((-0.46+j*.046)*side,v,zz+.07*math.sin(j*.23+k*.8)) for j in range(21)]
   tube(f'BE_WEST_AD_{i}_ART_{side}_{k}',points,.0002,paper)
  text_obj(f'BE_WEST_AD_{i}_FOOT_{side}','Stadt. Wege. Begegnungen.',u,v,.53,.036,paper,side)
 for u in [-.582,.582]:
  gz=ground(np.array(P(u,0,0)[:2]))-FLOOR
  box(f'BE_WEST_AD_{i}_FOOT_{u}',(u,0,(gz+.41)/2),(.035,.074,.41-gz),metal,.003)
  box(f'BE_WEST_AD_{i}_BASE_{u}',(u,0,gz+.006),(.09,.13,.012),metal,.003)
 tag_since(old,row['ids'][i],row['poster_format_basis']+' '+row['artwork_basis'],'wind_protection_poster_case')

frame(data['bench']['source_point_lv95'],data['bench']['axis']);old=set(building.objects.keys());seat_v=-.40
for i in range(6):box(f'BE_WEST_BENCH_SEAT_{i}',(0,seat_v-.235+i*.094,.46),(3.46,.081,.042),wood,.009)
for i in range(4):box(f'BE_WEST_BENCH_BACK_{i}',(0,-.105-i*.012,.615+i*.087),(3.46,.036,.072),wood,.008)
for j,u in enumerate([-1.42,0,1.42]):
 gz=ground(np.array(P(u,seat_v,0)[:2]))-FLOOR
 tube(f'BE_WEST_BENCH_FRAME_{j}',[P(u,-.60,gz+.012),P(u,-.55,.40),P(u,-.20,.40),P(u,-.125,.57),P(u,-.16,.88)],.019,dark)
 tube(f'BE_WEST_BENCH_REAR_LEG_{j}',[P(u,-.20,.40),P(u,-.15,gz+.012)],.018,dark)
 for v in [-.60,-.15]:box(f'BE_WEST_BENCH_BASE_{j}_{v}',(u,v,gz+.006),(.09,.085,.012),dark,.002)
 tube(f'BE_WEST_BENCH_ARM_{j}',[P(u,-.145,.66),P(u,-.26,.69),P(u,-.57,.68),P(u,-.61,.62)],.016,metal)
for ob in building.objects:
 if ob.name not in old and ob.type=='MESH' and ob.data.materials and ob.data.materials[0]==wood:
  uv=ob.data.uv_layers.new(name='real_2m_wood_grain')
  for f in ob.data.polygons:
   for li in f.loop_indices:
    v=ob.data.vertices[ob.data.loops[li].vertex_index].co;q=np.array(v[:2])-C
    uv.data[li].uv=(float(q@right)/2,(v.z-FLOOR if abs(f.normal.z)<.6 else float(q@front))/2)
tag_since(old,data['bench']['source_id'],data['bench']['basis'],'seating')

# Source polygon constrains ticket machine width/depth; details are photo-informed.
t=data['ticket'];frame(t['center_lv95'],t['axis']);old=set(building.objects.keys());w=t['source_width_m'];d=t['source_depth_m']
box('BE_WEST_TICKET_BODY',(0,0,1.255),(w,d,1.53),grey,.026)
for u in [-.35,.35]:
 gz=ground(np.array(P(u,0,0)[:2]))-FLOOR
 tube('BE_WEST_TICKET_LEG_'+str(u),[P(u,0,gz+.01),P(u,0,2.045)],.029,metal)
 box('BE_WEST_TICKET_FOOT_'+str(u),(u,0,gz+.008),(.11,.16,.016),metal,.004)
 bolt('BE_WEST_TICKET_BOLT_A_'+str(u),u,-.047,gz+.016);bolt('BE_WEST_TICKET_BOLT_B_'+str(u),u,.047,gz+.016)
box('BE_WEST_TICKET_PANEL_SEAM',(-.08,-d/2-.002,1.275),(.66,.007,1.405),black,.015)
box('BE_WEST_TICKET_BLUE_FACE',(-.08,-d/2-.011,1.275),(.647,.014,1.39),blue,.012)
box('BE_WEST_TICKET_SCREEN_GASKET',(-.105,-d/2-.020,1.355),(.462,.015,.423),black,.008)
box('BE_WEST_TICKET_SCREEN',(-.105,-d/2-.029,1.355),(.425,.005,.384),screen,.003)
v=-d/2-.033
text_obj('BE_WEST_TICKET_ZVV','ZVV',-.362,v,1.846,.084,paper)
text_obj('BE_WEST_TICKET_TITLE','Tickets ab Zürich, Bellevue',-.304,v,1.49,.017,ink)
for i,label in enumerate(['Kurzstrecke','Einzelbillett','24h-Ticket','Anderer Zielort']):
 z=1.432-i*.063;box(f'BE_WEST_TICKET_KEY_{i}',(-.122,v,z),(.358,.002,.047),yellow,.003);text_obj(f'BE_WEST_TICKET_KEYTEXT_{i}',label,-.292,v-.002,z-.007,.019,ink)
box('BE_WEST_TICKET_PAYMENT_RECESS',(.315,-d/2-.004,1.365),(.184,.016,.92),black,.013)
box('BE_WEST_TICKET_CARD_TERMINAL',(.315,-d/2-.030,1.215),(.137,.066,.245),dark,.009)
box('BE_WEST_TICKET_CARD_LCD',(.315,-d/2-.065,1.258),(.092,.007,.057),screen,.003)
for i in range(3):
 for j in range(3):box(f'BE_WEST_TICKET_CARD_KEY_{i}_{j}',(.275+j*.034,-d/2-.067,1.212-i*.024),(.025,.006,.017),metal,.002)
box('BE_WEST_TICKET_CARD_SLOT',(.315,-d/2-.067,1.126),(.093,.01,.009),black,.001)
box('BE_WEST_TICKET_COIN_PLATE',(.315,-d/2-.019,1.665),(.135,.016,.145),metal,.009)
box('BE_WEST_TICKET_COIN_SLOT',(.315,-d/2-.028,1.665),(.074,.009,.008),black,.001)
box('BE_WEST_TICKET_OUTPUT',(-.07,-d/2-.023,.85),(.30,.045,.071),black,.007)
box('BE_WEST_TICKET_OUTPUT_LIP',(-.07,-d/2-.047,.816),(.30,.015,.012),metal,.003)
text_obj('BE_WEST_TICKET_OUTPUT_TEXT','Billette',-.20,-d/2-.021,.907,.026,paper)
for i in range(11):box(f'BE_WEST_TICKET_REAR_VENT_{i}',(0,d/2+.002,.67+i*.018),(.55,.006,.006),dark,.001)
tag_since(old,t['source_id'],t['basis'],'ticket_machine_not_yet_interactive')

f=data['dfi'];frame(f['source_point_lv95'],f['axis_toward_track']);old=set(building.objects.keys())
box('BE_WEST_DFI_MAST',(0,0,1.53),(.13,.13,3.06),grey,.008)
box('BE_WEST_DFI_BASE',(0,0,.025),(.21,.21,.05),metal,.008)
for u in [-.073,.073]:
 for v in [-.073,.073]:bolt(f'BE_WEST_DFI_ANCHOR_{u}_{v}',u,v,.05)
box('BE_WEST_DFI_CASE',(.70,0,2.765),(1.25,.16,.57),grey,.018)
for side in [-1,1]:
 box(f'BE_WEST_DFI_GASKET_{side}',(.70,side*.081,2.765),(1.12,.013,.448),black,.010)
 box(f'BE_WEST_DFI_DISPLAY_{side}',(.70,side*.090,2.765),(1.08,.007,.411),display,.007)
 text_obj(f'BE_WEST_DFI_HEADER_{side}','Bellevue',.23 if side==-1 else 1.17,side*.095,2.852,.090,amber,side=-side)
 # Timetable values intentionally await the actual transport state/data integration.
box('BE_WEST_DFI_SERVICE_HATCH',(0,-.067,.55),(.087,.012,.38),dark,.005)
tag_since(old,f['source_id'],f['basis'],'passenger_information_not_yet_operational')

# Ordinary eye-height views of the new assembly; floor height is resolved on the mesh.
for cname,xy,target in [
 ('BE_QA_WEST_BENCH',[2683549.2,1246852.8],[2683547.6,1246856.88,409.7]),
 ('BE_QA_WEST_TICKET',[2683545.9,1246855.7],[2683543.4055,1246854.211,409.8])]:
 cxy=np.array(xy)-ORIGIN;z=ground(cxy);cd=bpy.data.cameras.new(cname);ob=bpy.data.objects.new(cname,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(ob);ob.location=(*cxy,z+1.65);cd.lens=40
 ob.rotation_euler=(Vector(np.array(target)-[2683775,1246700,400])-ob.location).to_track_quat('-Z','Y').to_euler();ob['eye_height_m']=1.65;ob['floor_height_local']=z
scene['version']='G1_008r3';scene.camera=bpy.data.objects['BE_QA_WEST_BENCH'];bpy.context.view_layer.update()
out=ROOT/'evidence/G1_008r3';out.mkdir(exist_ok=True)
native=ROOT/'native/G1_008r3_west_facilities_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
record=json.loads((ROOT/'runtime/station_road_working.json').read_text());record.update(version=scene['version'],native=str(native),fixtures_input_sha256=digest,accepted=False,not_published=True,published_as=None,next='Render facilities; check source ambiguity, close views, silhouette and photo-context overlap before export')
(ROOT/'runtime/station_road_working.json').write_text(json.dumps(record,indent=2))
(out/'facilities_build.json').write_text(json.dumps({'version':scene['version'],'objects':len(building.objects),'input_sha256':digest,'native':str(native),'accepted':False,'interaction_implemented':False},indent=2))
print(json.dumps({'version':scene['version'],'objects':len(building.objects),'native':str(native),'accepted':False}))
