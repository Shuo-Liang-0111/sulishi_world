"""AV459 working platform: original source is immutable; all heights retain provenance."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version']=='G1_007r5', 'Open the saved reviewed predecessor before applying this pass'
path=ROOT/'derived/bellevue/west_context/platform_input.json';data=json.loads(path.read_text());digest=hashlib.sha256(path.read_bytes()).hexdigest()
assert data['report']['slope_quantiles'][-1]<.09
col=bpy.data.collections.new('12_BELLEVUE_WEST_PLATFORM');bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(col)
soil=bpy.data.materials.new('BE | west tree pit soil');soil.use_nodes=True
bs=next(n for n in soil.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.067,.052,.033,1);bs.inputs['Roughness'].default_value=.97
soil['evidence_basis']='Inferred exposed soil; source tree and pit position retained, not a site material sample'
mats={'platform':bpy.data.materials['asphalt_03'],'curb_top':bpy.data.materials['concrete_floor_01'],'curb_face':bpy.data.materials['concrete_floor_01'],'curb_joint':bpy.data.materials['BE | curb mineral mortar'],'tree_soil':soil}
for key,triangles in data['parts'].items():
 t=np.array(triangles);name='BE_WEST_'+key.upper();me=bpy.data.meshes.new(name);me.from_pydata(t.reshape(-1,3).tolist(),[],np.arange(t.size//3).reshape(-1,3).tolist());me.update();me.materials.append(mats[key])
 uv=me.uv_layers.new(name='real_world_scale');uv.data.foreach_set('uv',np.array(data['uv'][key],dtype=np.float32).reshape(-1))
 ob=bpy.data.objects.new(name,me);col.objects.link(ob)
 ob['source_id']=data['report']['source_id'];ob['surface_role']='west_platform_'+key;ob['derived_source_sha256']=digest;ob['evidence_basis']=data['report']['basis'];ob['quality_status']='working geometry; native visual and continuous walking not accepted'
 ob['collision_role']='potential_walkable_surface_not_runtime_enabled' if key in ['platform','curb_top'] else 'not_runtime_enabled'
cutpath=ROOT/'derived/bellevue/west_context/photo_cut.json';cut=json.loads(cutpath.read_text())
context={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};originals={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for p in cut['overrides']:
 key=str(p['node']);ob=context[key];origin=originals[key];assert ob.matrix_basis==origin.matrix_basis
 vv=np.array(p['vertices'],dtype=np.float32);uvv=np.array(p['uv_source_v_unflipped'],dtype=np.float32);me=bpy.data.meshes.new('BE_WEST_CONTEXT_'+key);me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for mat in origin.data.materials:me.materials.append(mat)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.flatten());ob.data=me
 ob['construction_mask']=cut['mask_basis'];ob['source_geometry_unchanged_in_reference']=True
assert len(context)==2039 and len(originals)==2039
# Floor interpolation on authored triangles, avoiding nominal camera elevations.
tt=np.array(data['parts']['platform']);centres=tt[:,:,:2].mean(axis=1)
def height(xy):
 for i in np.argsort(np.linalg.norm(centres-xy,axis=1))[:100]:
  tri=tt[i];ab=(tri[1:,:2]-tri[0,:2]).T
  if abs(np.linalg.det(ab))<1e-10:continue
  w=np.linalg.solve(ab,xy-tri[0,:2])
  if min(w)>=-1e-7 and sum(w)<=1.0000001:return float(tri[0,2]+w@(tri[1:,2]-tri[0,2]))
 raise ValueError('Camera not on platform')
for name,xy,target in [
 ('BE_QA_WEST_PLATFORM',[2683537,1246849],[2683554,1246858,410.1]),
 ('BE_QA_WEST_PLATFORM_REVERSE',[2683563,1246864],[2683534,1246845,410.1])]:
 xy=np.array(xy)-[2683775,1246700];floor=height(xy);cd=bpy.data.cameras.new(name);ob=bpy.data.objects.new(name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(ob);ob.location=(*xy,floor+1.65);cd.lens=32
 ob.rotation_euler=(Vector(np.array(target)-[2683775,1246700,400])-ob.location).to_track_quat('-Z','Y').to_euler();ob['eye_height_m']=1.65;ob['floor_height_local']=floor
scene['version']='G1_008';scene['photo_cut_file']=str(cutpath.relative_to(ROOT));scene['quality_status']='West platform working; visual and daily-use verification incomplete';scene.camera=bpy.data.objects['BE_QA_WEST_PLATFORM'];bpy.context.view_layer.update()
native=ROOT/'native/G1_008_west_platform_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
record=json.loads((ROOT/'runtime/station_road_working.json').read_text());record.update(version=scene['version'],native=str(native),source_cut_file=scene['photo_cut_file'],source_cut_nodes=len(cut['overrides']),west_platform_input_sha256=digest,accepted=False,not_published=True,next='Review native human-eye platform in both directions; resolve source shelter/tree artifacts and connections before publication')
(ROOT/'runtime/station_road_working.json').write_text(json.dumps(record,indent=2));out=ROOT/'evidence/G1_008';out.mkdir(exist_ok=True)
(out/'platform_build.json').write_text(json.dumps({'version':scene['version'],'objects':[o.name for o in col.objects],'report':data['report'],'source_cut':cut['west_stats'],'accepted':False},indent=2))
print(json.dumps({'version':scene['version'],'native':str(native),'new_objects':len(col.objects),'source_count':len(originals),'accepted':False}))
