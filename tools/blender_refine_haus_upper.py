"""Repair observed corner construction errors and strengthen facade articulation."""
import bpy,bmesh,json,ast,math,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');sc=bpy.context.scene;assert sc['version']=='G1_010'
d=json.loads((R/'derived/haus_bellevue/upper_input.json').read_text());f=d['frontage']
C=np.array(f['C']);rt=np.array(f['right']);out=np.array(f['out']);Z=f['floor_local']
T=np.array(d['corner']['center_local']);radius=d['corner']['radius_m'];a0,a1=np.radians(d['corner']['visible_angles_deg'])
stone=bpy.data.materials['beige_wall_001'];plinth=bpy.data.materials['HB | grey sandstone plinth'];iron=bpy.data.materials['HU | forged iron balcony']
col=bpy.data.collections['17_HAUS_BELLEVUE_UPPER'];groups={}
source=ast.parse((R/'tools/blender_build_haus_upper.py').read_text())
names=['group','add','P','cube','beam','tube','baluster','ornament','balcony','curved','tangent_frame']
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'upper_helpers','exec'))

# Joints stop at the full stone reveal, never extend across glass.
old=bpy.data.objects['HU_CORNER_GROUND_RUSTIC_JOINT'];bpy.data.objects.remove(old,do_unlink=True)
angles=np.radians([-64.42,-13.6,37.24])
for label,width,z0,z1 in [('GROUND',2.04,.37,4.38),('MEZZ',1.26,5.25,7.98)]:
 half=np.arcsin((width/2+.21)/radius);intervals=[];cursor=a0
 for a in angles:
  if a-half>cursor:intervals.append((cursor,a-half))
  cursor=a+half
 if cursor<a1:intervals.append((cursor,a1))
 for z in np.arange(z0,z1,.35):
  for aa,bb in intervals:curved('HU_CORNER_'+label+'_MASONRY_JOINTS',z,z+.012,radius+.001,radius+.003,aa,bb,plinth)

# The photo shows substantial stone balconies on the low mezzanine axes.
centers=[(a+b)/2 for a,b in f['bays']]
for i in [3,7]:balcony(f'HU_MAIN_MEZZ_BALCONY_{i}',centers[i],2.00,4.95,True)

# Corner pilasters, capitals and window aprons provide relief visible obliquely.
for j,a in enumerate(np.radians([-88,-39.01,11.82])):
 tf=tangent_frame(a)
 cube('HU_CORNER_PILASTERS',(0,.065,14.37),(.36,.24,11.98),stone,.004,tf)
 for k in range(5):cube('HU_CORNER_FLUTES',(-.135+k*.067,.202,14.37),(.038,.048,11.63),stone,.010,tf)
 for z,w,h in [(8.44,.49,.15),(20.34,.62,.17),(20.14,.50,.17)]:cube('HU_CORNER_CAPITALS',(0,.09,z),(w,.37,h),stone,.006,tf)
 for u in [-.17,0,.17]:ornament('HU_CORNER_CAPITALS',u,.288,20.16,.103,tf)

# Sculpted rectangular aprons below tall windows, based on the existing photo;
# fabrication dimensions remain explicit inference.
for L in d['levels'][1:]:
 for i,u in enumerate(centers):
  if i==5:continue
  z=L['sill']-.40
  for side in [-1,1]:cube('HU_MAIN_WINDOW_APRONS',(u+side*.58,-.043,z),(.064,.105,.44),stone,.004)
  for zz in [z-.22,z+.22]:cube('HU_MAIN_WINDOW_APRONS',(u,-.043,zz),(1.20,.105,.064),stone,.004)

for (name,_),g in groups.items():
 assert name not in bpy.data.objects
 me=bpy.data.meshes.new(name);me.from_pydata(g['v'],[],g['f']);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new(name,me);col.objects.link(ob);me.materials.append(g['mat'])
 for face in me.polygons:face.use_smooth=g['smooth']
 uv=me.uv_layers.new(name='metre_scale')
 for face in me.polygons:
  axes=[i for i in range(3) if i!=int(np.argmax(abs(np.array(face.normal))))]
  for li in face.loop_indices:
   p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/3,p[axes[1]]/3)
 if g['bevel']:
  mod=ob.modifiers.new('Fine material edge radius','BEVEL');mod.width=g['bevel'];mod.segments=2;ob.modifiers.new('Weighted architectural normals','WEIGHTED_NORMAL')
 ob['egid']=9011202;ob['place']='Haus Bellevue';ob['evidence_basis']='Existing SPPA exterior reference; ornament construction dimensions inferred.';ob['collision_role']='solid_pending_runtime';ob['quality_status']='native candidate, not accepted'

cutpath=R/'derived/bellevue/west_context/haus_upper_balcony_refined_cut.json';cut=json.loads(cutpath.read_text())
ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};orig={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for p in cut['overrides']:
 ob=ctx[str(p['node'])];src=orig[str(p['node'])];vv=np.array(p['vertices']);uvv=np.array(p['uv_source_v_unflipped']);me=bpy.data.meshes.new('HU_R1_CONTEXT_'+str(p['node']));me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.astype(np.float32).reshape(-1));ob.data=me;ob['construction_mask']=cut['mask_basis']

for name,u,v,target,lens in [('HB_QA_FULL_FACADE',13.5,15,(14,0,11.8),17),('HB_QA_CORNER',41,22,(30,-1.5,12.8),23)]:
 xy=P(u,v,40);z=None
 for ob in bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].all_objects:
  if ob.type=='MESH' and (ob.name.startswith('BE_PAVING_') or ob.name in ['BE_WEST_PLATFORM','HB_SIDEWALK_ASPHALT']):
   hit,pt,_,_=ob.ray_cast(ob.matrix_world.inverted()@Vector(xy),Vector((0,0,-1)))
   world=ob.matrix_world@pt
   if hit and world.z<15:z=world.z if z is None else max(z,world.z)
 assert z is not None, (name,u,v,'No authored ground beneath this camera')
 camera=bpy.data.objects[name];camera.location=Vector((xy[0],xy[1],z+1.65));camera.rotation_euler=(Vector(P(*target))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=lens;camera['floor_height_local']=z

audit=json.loads((R/'derived/haus_bellevue/roof_triangulation_audit.json').read_text())
for name in ['HU_SOURCE_ROOF_SLATE','HU_SOURCE_ROOF_METAL','HU_SOURCE_ROOF_DORMER_WALL']:
 ob=bpy.data.objects.get(name)
 if ob:ob['evidence_basis']='Official roof/wall polygon surfaces triangulated and clipped. Original vertices preserved; repaired/intersection vertices interpolated on source face planes. Largest nonplanar source residual 0.03271m. Materials are visual proxies.'
sc['version']='G1_010r1';sc['photo_cut_file']=str(cutpath.relative_to(R));sc.camera=bpy.data.objects['HB_QA_CORNER'];bpy.context.view_layer.update()
native=R/'native/G1_010r1_haus_upper_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=sc['version'],native=str(native),source_cut_file=sc['photo_cut_file'],source_cut_nodes=len(cut['overrides']),source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2))
e=R/'evidence/G1_010r1';e.mkdir(exist_ok=True);(e/'refinement.json').write_text(json.dumps({'version':sc['version'],'fixes':['Corner joints stop at window reveals','Curved balcony photo remnants clipped within limited height band','Mezzanine stone balconies and corner pilasters added from existing photo'],'roof_triangulation_audit':audit,'native':str(native),'accepted':False},indent=2))
print(json.dumps({'version':sc['version'],'upper_objects':len(col.objects),'native':str(native),'accepted':False}))
