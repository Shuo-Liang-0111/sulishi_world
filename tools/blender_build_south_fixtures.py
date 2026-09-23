"""AV3573 equipment: actual anchors; explicitly inferred fabrication variants."""
import bpy,bmesh,json,math,ast,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version']=='G1_013'
d=json.loads((R/'derived/bellevue/south_context/info/input.json').read_text())
f=json.loads((R/'derived/bellevue/south_context/fixtures_input.json').read_text())
old=json.loads((R/'derived/bellevue/corner_fixtures/input.json').read_text())
O=np.array([2683775,1246700,400]);name='23_BELLEVUE_SOUTH_FIXTURES'
assert name not in bpy.data.collections
building=bpy.data.collections.new(name);bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(building)
def anchor(src,z):return np.r_[np.array(src['geometry']['coordinates'][0])-O[:2],z]
def clone(ob,name,M,source,basis):
 dup=ob.copy();dup.data=ob.data.copy();dup.name=name;building.objects.link(dup);dup.matrix_world=M@ob.matrix_basis
 for key in ['egid','derived_source_sha256']:
  if key in dup:del dup[key]
 dup['source_id']=source;dup['place']='Bellevue AV3573 south public space';dup['evidence_basis']=basis;dup['quality_status']='working, not accepted';return dup
# Preserve source top elevations; total pole lengths include the embedded section.
mc=anchor(old['mast'],old['mast_ground_local'])
mast_receipts=[]
for src,gz in [(d['mast'],d['mast_ground_local']),(f['mast2']['source'],f['mast2']['ground_local'])]:
 nc=anchor(src,gz);scale=(src['properties']['hoehemastok']-O[2]-nc[2])/(old['mast']['properties']['hoehemastok']-O[2]-mc[2]);M=Matrix.Translation(Vector(nc))@Matrix.Diagonal((1,1,scale,1))@Matrix.Translation(Vector(-mc));ident=src['properties']['objectid']
 for ob in bpy.data.collections['19_BELLEVUE_CORNER_FIXTURES'].objects:
  if ob.name.startswith('CF_MAST_'):clone(ob,ob.name.replace('CF_MAST_1800',f'BSF_MAST_{ident}'),M,src['id'],'Official XY and top elevation; supported by AV3573 reconstructed grade. Shaft family, coating, taper, collars and hatch inferred.')
 mast_receipts.append({'id':src['id'],'ground_local':gz,'source_top_ln02':src['properties']['hoehemastok']})
a=anchor(old['information'][0],old['info_ground_local']);b=anchor(d['information'][0],d['info_ground_local'])
def mov(axis):
 angle=math.atan2(d[axis][1],d[axis][0])-math.atan2(old[axis][1],old[axis][0]);return Matrix.Translation(Vector(b))@Matrix.Rotation(angle,4,'Z')@Matrix.Translation(Vector(-a))
Mu,Mv=mov('u'),mov('v');mapmat=bpy.data.materials['CF | original Bellevue neighborhood notice'].copy();mapmat.name='BSF | south-anchor neighborhood notice';im=bpy.data.images.load(str(R/'derived/bellevue/south_context/info/neighborhood_map.png'),check_existing=True)
for n in mapmat.node_tree.nodes:
 if n.type=='TEX_IMAGE':n.image=im
for ob in bpy.data.collections['19_BELLEVUE_CORNER_FIXTURES'].objects:
 if not ob.name.startswith('CF_INFO_'):continue
 side=('_RETURN_' in ob.name or '_SIDE_LOW_' in ob.name or ob.name in ['CF_INFO_GROUND_SLEEVE_2','CF_INFO_GROUND_PATCH_2'])
 dup=clone(ob,ob.name.replace('CF_','BSF_',1).replace('INFO_1143','INFO_2864').replace('INFO_2584','INFO_2581'),Mv if side else Mu,'haltestellen_infosystem.2864+2581','Actual paired XY and bearings. VBZ2016 tubular family proxy, type74/88 semantics and anchor convention unresolved. Own locally centered AV map, not current posted notice.')
 for i,m in enumerate(dup.data.materials):
  if m is bpy.data.materials['CF | original Bellevue neighborhood notice']:dup.data.materials[i]=mapmat
# Source DFI direction interpreted as the arm bearing, with own floor contact.
prev=json.loads((R/'derived/bellevue/west_context/fixtures_input.json').read_text())['dfi']
oldxy=np.array(prev['source_point_lv95'])-O[:2];base=bpy.data.objects['BE_WEST_DFI_BASE'];oldz=min((base.matrix_world@Vector(p)).z for p in base.bound_box)
newc=anchor(f['dfi']['source'],f['dfi']['ground_local']);theta=math.radians(float(f['dfi']['source']['properties']['orientierung']));axis=np.array([math.sin(theta),math.cos(theta)])
angle=math.atan2(axis[1],axis[0])-math.atan2(prev['axis_toward_track'][1],prev['axis_toward_track'][0]);M=Matrix.Translation(Vector(newc))@Matrix.Rotation(angle,4,'Z')@Matrix.Translation(Vector((*-oldxy,-oldz)))
for ob in bpy.data.collections['14_BELLEVUE_WEST_FACILITIES'].objects:
 if ob.name.startswith('BE_WEST_DFI_'):clone(ob,ob.name.replace('BE_WEST_DFI_','BSF_DFI67_'),M,f['dfi']['source']['id'],'Actual Info Smart XY and source bearing; dimensions from existing photo-informed family. Arm bearing convention inferred; Bellevue header only, no live departure claims.')
# Manufacturer-constrained 110L Haifisch variant, not a generic open cylinder.
defs=[n for n in ast.parse((R/'tools/blender_build_bellevue.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','box','lathe','tube']]
exec(compile(ast.Module(body=defs,type_ignores=[]),'geometry_helpers','exec'))
C=anchor(f['bin']['source'],f['bin']['ground_local'])[:2];FLOOR=f['bin']['ground_local'];th=math.radians(float(f['bin']['source']['properties']['orientierung']));front=np.array([math.sin(th),math.cos(th)]);right=np.array([-front[1],front[0]])
def P(u,v,z):
 xy=C+right*u+front*v;return (float(xy[0]),float(xy[1]),float(FLOOR+z))
steel=bpy.data.materials['BE | satin anodised aluminium'].copy();steel.name='BSF | ground stainless bin shell';bs=next(n for n in steel.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.48,.50,.49,1);bs.inputs['Metallic'].default_value=.94;bs.inputs['Roughness'].default_value=.39
dark=bpy.data.materials['BE | dark structural metal'];rubber=bpy.data.materials['BE | equipment black gasket'];paint=bpy.data.materials['CF | metre-scale satin coat']
before=set(building.objects.keys());r=.225;inner=.222;half=math.asin(.1305/r)
angles=sorted(set(np.linspace(-math.pi,math.pi,193).tolist()+[-half,half]));levels=[.063,.898,1.008,'top']
def height(z,t):return 1.067-.022*math.cos(t) if z=='top' else z
vv=[]
for rr in [r,inner]:
 for z in levels:
  for t in angles:vv.append(P(rr*math.sin(t),rr*math.cos(t),height(z,t)))
n=len(angles);ff=[];stride=n*len(levels)
for layer in [0,1]:
 for k in range(3):
  for j in range(n-1):
   if k==1 and -half+1e-8<(angles[j]+angles[j+1])/2<half-1e-8:continue
   a=layer*stride+k*n+j;face=(a,a+1,a+1+n,a+n);ff.append(face if layer==0 else face[::-1])
# Close all aperture cut edges with the actual3mm sheet thickness.
for zidx in [1,2]:
 for j in range(n-1):
  if -half+1e-8<(angles[j]+angles[j+1])/2<half-1e-8:
   a=zidx*n+j;ff.append((a,a+stride,a+stride+1,a+1))
for t in [-half,half]:
 j=angles.index(t);a=n+j;ff.append((a,a+n,a+n+stride,a+stride))
shell=mesh('BSF_BIN631_SHEET_SHELL',vv,ff,steel,True)
# Solid sloping lid and underside rim. No artificial open top.
vl=[P(0,0,1.067),P(0,0,1.063)];fl=[]
for t in angles[:-1]:
 z=height('top',t);vl.extend([P((r+.002)*math.sin(t),(r+.002)*math.cos(t),z),P((r+.002)*math.sin(t),(r+.002)*math.cos(t),z-.004)])
count=len(angles)-1
for j in range(count):
 a=2+2*j;b2=2+2*((j+1)%count);fl.extend([(0,a,b2),(1,b2+1,a+1),(a,a+1,b2+1,b2)])
mesh('BSF_BIN631_CLOSED_SLOPING_LID',vl,fl,steel)
lathe('BSF_BIN631_BASE',[(0,0),(.200,0),(.208,.013),(.214,.052),(.221,.063),(0,.063)],paint)
lathe('BSF_BIN631_DARK_INNER_LINER',[(0,.075),(.19,.075),(.19,.925),(.186,.925),(.186,.08),(0,.08)],rubber)
# Door seams and low-profile hinges are real geometry, with inferred placement.
for sign in [-1,1]:
 t=sign*1.64;points=[P((r+.0005)*math.sin(t),(r+.0005)*math.cos(t),z) for z in [.092,.85]];tube(f'BSF_BIN631_DOOR_SEAM_{sign}',points,.00065,dark)
for z in [.19,.68]:
 t=-1.64;u=(r+.002)*math.sin(t);v=(r+.002)*math.cos(t);tube('BSF_BIN631_HINGE_'+str(z),[P(u,v,z),P(u,v,z+.044)],.006,steel)
t=1.64;u=(r+.002)*math.sin(t);v=(r+.002)*math.cos(t)
box('BSF_BIN631_LOCK',(u,v,.54),(.005,.025,.025),steel,.001)
# Metre-based UVs support the ground satin coating without huge stretched maps.
for ob in building.objects:
 if ob.name not in before:
  for key in ['egid']:
   if key in ob:del ob[key]
  ob['source_id']=f['bin']['source']['id'];ob['place']='Bellevue AV3573 south public space';ob['evidence_basis']=f['bin']['basis'];ob['facility_role']='litter_bin_not_yet_interactive';ob['quality_status']='working, not accepted'
  if ob.type=='MESH':
   uv=ob.data.uv_layers.new(name='physical_metre_coordinates')
   for l in ob.data.loops:
    p=ob.data.vertices[l.vertex_index].co;q=np.array(p[:2])-C;uv.data[l.index].uv=(math.atan2(q@right,q@front)*r,p.z-FLOOR)
cutpath=R/'derived/bellevue/west_context/south_fixtures_photo_cut.json';cut=json.loads(cutpath.read_text());ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};orig={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for p in cut['overrides']:
 ob=ctx[str(p['node'])];src=orig[str(p['node'])];v=np.array(p['vertices']);uvv=np.array(p['uv_source_v_unflipped']);me=bpy.data.meshes.new('BSF_CONTEXT_'+str(p['node']));me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.astype(np.float32).reshape(-1));ob.data=me;ob['construction_mask']=cut['mask_basis']
xy=C+front*3.1-right*1.0;hit,g,_,_=bpy.data.objects['BS_ASPHALT'].ray_cast(Vector((*xy,30)),Vector((0,0,-1)));assert hit
cd=bpy.data.cameras.new('BE_QA_SOUTH_FACILITIES');co=bpy.data.objects.new(cd.name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(co);co.location=(*xy,g.z+1.65);cd.lens=38;co.rotation_euler=(Vector((*C,FLOOR+1.04))-co.location).to_track_quat('-Z','Y').to_euler();co['eye_height_m']=1.65;co['floor_height_local']=g.z
s['version']='G1_013r1';s['photo_cut_file']=str(cutpath.relative_to(R));s.camera=co;bpy.context.view_layer.update();bpy.ops.file.pack_all();native=R/'native/G1_013r1_south_facilities_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=s['version'],native=str(native),source_cut_file=s['photo_cut_file'],source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2));e=R/'evidence'/s['version'];e.mkdir(exist_ok=True);report={'version':s['version'],'native':str(native),'objects':len(building.objects),'mast_receipts':mast_receipts,'bin_height_m':1.089,'bin_variant_inferred':True,'accepted':False,'interactive':False};(e/'construction.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
