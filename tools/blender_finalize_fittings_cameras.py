"""Correct two unaccepted review cameras onto actual pavement; save separately.

The initial author view exposed their water-side XY error. No scene geometry,
existing camera, material or lighting is changed. Preserve the candidate native.
"""
from pathlib import Path
import hashlib,json,sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import ROOT,read_path,write_path
from blender_geometry_fingerprint import object_state
assert bpy.context.scene['version']=='G1_027r4'
before={o.name:object_state(o) for o in bpy.context.scene.objects}
record_path=read_path('evidence/G1_027r4/checkpoint.json');record=json.loads(record_path.read_text())
assert Path(bpy.data.filepath).name=='G1_027r4_bridge_fittings_working.blend'
target=write_path('native/G1_027r4_bridge_fittings_checked_cameras.blend');assert not target.exists()
write_path('evidence/G1_027r4/initial_candidate_checkpoint.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
s=bpy.context.scene;deps=bpy.context.evaluated_depsgraph_get();cameras=[]
for name,xy,look,lens in [('BF_QA_LAMP',[-311.1,108.7],[-304.1,109.0,14.4],42),('BF_QA_FLAGS',[-295,112.8],[-266.5,115.2,17.0],34)]:
    hit,p,n,f,floor,m=s.ray_cast(deps,Vector((*xy,13.5)),Vector((0,0,-1)),distance=8)
    assert hit and floor.name.startswith('BD_SURFACE_') and n.z>.9
    ob=bpy.data.objects[name];ob.location=(*xy,p.z+1.7)
    ob.rotation_euler=(Vector(look)-ob.location).to_track_quat('-Z','Y').to_euler();ob.data.lens=lens
    ob['floor_source']=floor.name;ob['eye_height_m']=1.7
    cameras.append(dict(name=name,location=list(ob.location),target=look,lens=lens,floor=floor.name,eye_height_m=1.7))
s.camera=bpy.data.objects['BD_QA_EAST'];bpy.context.view_layer.update()
assert all(object_state(bpy.data.objects[name])==state for name,state in before.items() if name not in ['BF_QA_LAMP','BF_QA_FLAGS'])
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True,relative_remap=True)
with target.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
record.update(native=target.relative_to(ROOT).as_posix(),native_bytes=target.stat().st_size,native_sha256=digest,
    review_cameras=cameras,initial_candidate_native='native/G1_027r4_bridge_fittings_working.blend')
write_path('evidence/G1_027r4/camera_floor_correction.json').write_text(json.dumps(dict(cameras=cameras,
    reason='Initial supplemental cameras were above water; relocated onto actual bridge pavement at 1.7m eye height before visual review.',geometry_changed=False),indent=2),encoding='utf-8')
record_path.write_text(json.dumps(record,indent=2),encoding='utf-8')
print('FITTINGS_REVIEW_CAMERAS_SAVED',json.dumps(dict(native=str(target),sha256=digest,cameras=cameras)),flush=True)
