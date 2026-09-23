"""Local reflections captured from the unchanged native world, never a city photo."""
import bpy,json,math,sys,struct,hashlib
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;V=s['version'];assert V in ['G1_015r1','G1_015r2','G1_015r3','G1_016r1','G1_017','G1_017r1','G1_018r3']
args=sys.argv[sys.argv.index('--')+1:];assert len(args)==1
key=args[0];assert key in ['NORTH','FRONT','EAST_INFO','EAST_BIN','FOUNTAIN']
source=bpy.data.objects[{'EAST_INFO':'BE_QA_SOUTH_EAST_INFO_WIDE','EAST_BIN':'BE_QA_SOUTH_EAST_BIN_OPENING','FOUNTAIN':'F59_ROOT'}.get(key,'BE_QA_SERVICE_'+key)]
data=bpy.data.cameras.new('TEMP_REFLECTION_CAMERA');camera=bpy.data.objects.new('TEMP_REFLECTION_CAMERA',data);s.collection.objects.link(camera)
assert 'PANO' in {e.identifier for e in data.bl_rna.properties['type'].enum_items}
data.type='PANO';data.panorama_type='EQUIRECTANGULAR';camera.location=source.location.copy();camera.rotation_euler=(math.pi/2,0,0);s.camera=camera
excluded_self_water=[]
if key=='FOUNTAIN':
 camera.location.z+=.82
 for ob in list(bpy.data.collections['27_BELLEVUE_FOUNTAIN_59'].objects):
  if ob.name=='F59_WATER_SURFACE' or ob.name.startswith('F59_JET_'):
   ob.hide_render=True;excluded_self_water.append(ob.name)
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=24;s.render.threads_mode='FIXED';s.render.threads=10;s.render.use_persistent_data=False
s.render.use_compositing=False;s.render.use_sequencer=False;s.render.resolution_x=1024;s.render.resolution_y=512;s.render.resolution_percentage=100
# Same photographic texture tiers as native review; authored surfaces stay full-res.
with (R/'web/assets/G1_004r2_photo_stream.glb').open('rb') as f:
 f.seek(12);length,tag=struct.unpack('<II',f.read(8));manifest=json.loads(f.read(length))
records={m['name']:m['extras']['runtime_texture_lod'] for m in manifest['materials']}
used_full=0;budget=0
items=[]
for obj in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects:
 corners=[obj.matrix_world@Vector(p) for p in obj.bound_box];center=sum(corners,Vector())/8
 distance=max(1,(center-camera.location).length-max((p-center).length for p in corners))
 for mat in obj.data.materials:
  if mat.name in records:items.append((distance,mat,records[mat.name]))
for distance,mat,record in sorted(items,key=lambda x:x[0]):
 cost=record['width']*record['height']*4
 if distance<100 and used_full<180 and budget+cost<300*1024*1024:used_full+=1;budget+=cost;continue
 tier='medium' if distance<200 else 'low';image=bpy.data.images.load(str(R/'web/assets'/record[tier]),check_existing=True)
 for n in mat.node_tree.nodes:
  if n.type=='TEX_IMAGE':n.image=image
path=R/'web/assets'/f'{V}_service_reflection_{key.lower()}.hdr'
s.render.image_settings.file_format='HDR';s.render.filepath=str(path)
bpy.context.view_layer.update();assert 'FINISHED' in bpy.ops.render.render(write_still=True,scene=s.name)
s.render.image_settings.file_format='PNG'
preview=R/'evidence'/V/f'service_reflection_{key.lower()}.png';bpy.data.images['Render Result'].save_render(str(preview),scene=s)
receipt={'version':V,'key':key,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
 'position_yup':[camera.location.x,camera.location.z,-camera.location.y],
 'source_camera':source.name,'native_unchanged':True,'authored_textures_downscaled':False,'samples':24,
 'excluded_self_water_for_capture':excluded_self_water,
 'limitation':'Static local environment approximation; not a ray-traced reflection or moving-object reflection.'}
(R/'evidence'/V/f'service_reflection_{key.lower()}.json').write_text(json.dumps(receipt,indent=2))
print('LOCAL_REFLECTION_FINISHED',key,flush=True)
