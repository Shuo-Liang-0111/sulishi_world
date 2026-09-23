"""2015 Rämistrasse canopy, source plan and bounded section refinement."""
import bpy,bmesh,json,math,ast,hashlib,numpy as np
from mathutils import Vector
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene;assert scene['version']=='G1_008'
path=ROOT/'derived/bellevue/west_context/canopy_input.json';data=json.loads(path.read_text());digest=hashlib.sha256(path.read_bytes()).hexdigest()
building=bpy.data.collections.new('13_BELLEVUE_WEST_SHELTER');bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(building)
tree=ast.parse((ROOT/'tools/blender_build_bellevue.py').read_text());defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','triangles','box','lathe','tube']];exec(compile(ast.Module(body=defs,type_ignores=[]),'geometry_helpers','exec'))
C=np.array(data['axis_local'][0]);axis=np.array(data['axis_local'][1])-C;right=axis/np.linalg.norm(axis);front=np.array([-right[1],right[0]]);FLOOR=0.
def P(u,v,z):
 xy=C+right*u+front*v;return (float(xy[0]),float(xy[1]),float(z))
def mat(name,color,rough=.6,metal=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal;return m
roof=bpy.data.materials['BE | folded grey metal roof'];soffit=bpy.data.materials['BE | warm pale painted soffit'];metal=bpy.data.materials['BE | satin anodised aluminium'];dark=bpy.data.materials['BE | dark structural metal'];wood=bpy.data.materials['oak_veneer_01']
for key,t in data['parts'].items():
 ob=triangles('BE_WEST_SHELTER_'+key.upper(),t,soffit if key=='soffit' else roof,data['basis'])
 if key in ['roof_metal','soffit']:
  for face in ob.data.polygons:face.use_smooth=True
for i,points in enumerate(data['standing_seams']):tube(f'BE_WEST_SHELTER_FOLD_{i:03d}',points,.004,roof)
# The internal drain is a physical channel, not a line drawn over the photograph.
length=np.linalg.norm(axis);box('BE_WEST_ROOF_CENTRAL_GUTTER',(length/2,0,12.122),(length,.14,.035),dark,.005)
platform=json.loads((ROOT/'derived/bellevue/west_context/platform_input.json').read_text());tt=np.array(platform['parts']['platform']);centres=tt[:,:,:2].mean(axis=1)
def ground(xy):
 for i in np.argsort(np.linalg.norm(centres-xy,axis=1))[:100]:
  t=tt[i];a=(t[1:,:2]-t[0,:2]).T
  if abs(np.linalg.det(a))<1e-10:continue
  w=np.linalg.solve(a,xy-t[0,:2])
  if min(w)>=-1e-6 and sum(w)<=1.000001:return float(t[0,2]+w@(t[1:,2]-t[0,2]))
 raise ValueError('Support outside authored platform')
opal=mat('BE | west canopy opal ring',(.77,.75,.65),.34)
for i,xy in enumerate(data['support_centres_local']):
 z=ground(np.array(xy));base=lathe(f'BE_WEST_COLUMN_{i:02d}',[(0,z),(.205,z),(.205,z+.055),(.183,z+.075),(.183,11.30),(.20,11.37)],soffit,world_center=xy)
 profile=[(.20,11.37),(.217,11.45),(.25,11.52),(.32,11.61),(.43,11.70),(.56,11.76),(.69,11.799)]
 lathe(f'BE_WEST_COLUMN_FLARE_{i:02d}',profile,soffit,world_center=xy)
 lathe(f'BE_WEST_COLUMN_LIGHT_{i:02d}',[(.192,11.355),(.227,11.355),(.232,11.39),(.198,11.39)],opal,world_center=xy)
 base['support_xy_quality']='inferred from official circular end centres and midpoint, not surveyed steelwork'
# A single VBZ long bench has a recorded point/orientation. Its slat spacing,
# length and leg details remain a conservative photo-informed first reconstruction.
bench=np.array([2683547.601,1246856.883])-[2683775,1246700];bu,bv=(bench-C)@right,(bench-C)@front;bz=ground(bench)
benchobs=[]
for j in range(6):benchobs.append(box(f'BE_WEST_BENCH_SEAT_{j}',(bu,bv-.235+j*.094,bz+.46),(4.0,.082,.04),wood,.009))
for j in range(4):benchobs.append(box(f'BE_WEST_BENCH_BACK_{j}',(bu,bv+.30,bz+.60+j*.085),(4.0,.038,.073),wood,.006))
for i,along in enumerate([-1.65,0,1.65]):
 benchobs.append(box(f'BE_WEST_BENCH_LEG_{i}',(bu+along,bv,bz+.24),(.065,.42,.44),dark,.009));benchobs.append(box(f'BE_WEST_BENCH_BACK_POST_{i}',(bu+along,bv+.335,bz+.49),(.045,.045,.86),dark,.005))
for ob in benchobs:
 ob['source_id']='haltestellen_sitzgelegenheit.544';ob['evidence_basis']='Official VBZ bench point, Bank in WH lang. Axis interpreted against actual platform and reference photograph; 4m length, wood selection and fabrication details are inferred.'
 if ob.data.materials[0] is wood:
  uv=ob.data.uv_layers.new(name='world_grain_scale')
  for f in ob.data.polygons:
   for li in f.loop_indices:
    v=ob.data.vertices[ob.data.loops[li].vertex_index].co;q=np.array(v[:2])-C;u=float(q@right);w=float(q@front)
    uv.data[li].uv=(u/2,(v.z if abs(f.normal.z)<.6 else w)/2)
for ob in building.objects:
 ob['egid']=302063027;ob['place']='Bellevue_Raemistrasse_2015_shelter';ob['derived_source_sha256']=digest;ob['quality_status']='working reconstruction, not accepted'
 if not ob.get('source_id'):ob['source_id']=data['roof_source'];ob['evidence_basis']=data['basis']
cutpath=ROOT/'derived/bellevue/west_context/shelter_photo_cut.json';cut=json.loads(cutpath.read_text());context={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};originals={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for p in cut['overrides']:
 key=str(p['node']);ob=context[key];origin=originals[key];vv=np.array(p['vertices'],dtype=np.float32);uvv=np.array(p['uv_source_v_unflipped'],dtype=np.float32)
 me=bpy.data.meshes.new('BE_WEST_SHELTER_CONTEXT_'+key);me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in origin.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.flatten());ob.data=me;ob['construction_mask']=cut['mask_basis']
scene['version']='G1_008r1';scene['photo_cut_file']=str(cutpath.relative_to(ROOT));scene.camera=bpy.data.objects['BE_QA_WEST_PLATFORM'];bpy.context.view_layer.update()
native=ROOT/'native/G1_008r1_west_shelter_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native));record=json.loads((ROOT/'runtime/station_road_working.json').read_text());record.update(version=scene['version'],native=str(native),source_cut_file=scene['photo_cut_file'],canopy_input_sha256=digest,accepted=False,not_published=True,next='Render both ordinary platform directions; complete missing real station fixtures and diagnose replacement boundary before runtime review')
(ROOT/'runtime/station_road_working.json').write_text(json.dumps(record,indent=2));out=ROOT/'evidence/G1_008r1';out.mkdir(exist_ok=True)
(out/'shelter_build.json').write_text(json.dumps({'version':scene['version'],'objects':len(building.objects),'source_cut':cut['shelter_stats'],'native':str(native),'accepted':False,'incomplete_facilities':['ticket machine','wind/ad panels','tactile boarding marker'],'source_reference':'sources/references/bellevue_shelters/Immobilia_2016_05.pdf p76'},indent=2));print(json.dumps({'version':scene['version'],'new_objects':len(building.objects),'native':str(native),'accepted':False}))
