"""Fresh-native checks for the bounded r10 repair; visual use remains separate."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,sys
import bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path
from blender_photo_clip import subtract_box,area

s=bpy.context.scene;assert s['version'] in ['G1_027r10','G1_027r11','G1_027r12','G1_027r13','G1_027r14','G1_027r15']
version=s['version'];native=Path(bpy.data.filepath)
with native.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
cp=json.loads(read_path(f'evidence/{version}/checkpoint.json').read_text())
assert digest==cp['native_sha256']
r=json.loads(read_path(f'evidence/{version}/nearfront_build_report.json').read_text())
A,U,N=(np.array(r['frame'][k]) for k in ['A','U','N'])
def Q(p):return np.r_[(p[:2]-A)@U,(p[:2]-A)@N,p[2]]
box=np.array(r['bounds_front_frame']);box[::2]+=2e-5;box[1::2]-=2e-5
assert all(x['local_bounds'][0][1]>box[3]+7 for x in r['protected_shelters'])
maximum=0.;faces_checked=0
for row in r['photo_cuts']:
    ob=bpy.data.objects[row['object']];assert len(ob.data.polygons)==row['new_faces']
    for face in ob.data.polygons:
        poly=[Q(np.array(ob.matrix_world@ob.data.vertices[i].co)) for i in face.vertices]
        outside,inside=subtract_box(poly,box)
        overlap=area(inside);maximum=max(maximum,overlap);faces_checked+=1
        assert overlap<1e-5,(ob.name,face.index,overlap)
ground=bpy.data.objects['UF_CONTINUOUS_STREET_APPROACH']
positions=np.empty(len(ground.data.vertices)*3,dtype=np.float32)
ground.data.vertices.foreach_get('co',positions)
indices=np.empty(len(ground.data.loops),dtype=np.int32)
ground.data.loops.foreach_get('vertex_index',indices)
assert hashlib.sha256(positions.tobytes()+indices.tobytes()).hexdigest()==r['ground_geometry_sha256']
uv_errors=[]
for ob in [ground,bpy.data.objects['SG_R7_CONTINUOUS_STREET_APPROACH']]:
    uv=ob.data.uv_layers.active
    for loop in ob.data.loops:
        p=ob.matrix_world@ob.data.vertices[loop.vertex_index].co
        actual=np.array(uv.data[loop.index].uv);expected=np.array([p.x,p.y])/2.05
        error=float(np.max(abs(actual-expected)));uv_errors.append(error)
        assert error<1.5e-5,(ob.name,loop.index,error)
current_cameras={o.name:{'matrix':[list(row) for row in o.matrix_world],
                        'lens':o.data.lens,'sensor_width':o.data.sensor_width}
                 for o in s.objects if o.type=='CAMERA'}
assert all(current_cameras.get(name)==state for name,state in r['before_cameras'].items())
added=set(current_cameras)-set(r['before_cameras'])
if version in ['G1_027r11','G1_027r12','G1_027r13','G1_027r14','G1_027r15']:
    merge=json.loads(read_path(f'evidence/{version}/sf1_merge_report.json').read_text())
    expected_added=set(merge['review_cameras'])
    if version in ['G1_027r12','G1_027r13','G1_027r14','G1_027r15']:
        bank=json.loads(read_path(f'evidence/{version}/bank_shelter_build_report.json').read_text())
        expected_added.update(row['name'] for row in bank['review_cameras'])
    assert added==expected_added
else:assert not added
bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
cam=bpy.data.objects['UF_QA_ENTRY'];direction=cam.matrix_world.to_quaternion()@Vector((0,0,-1))
hit,p,n,fi,ob,m=s.ray_cast(deps,cam.location,direction,distance=8)
assert hit and ob.name.startswith('UF_'),ob.name if hit else None
checks=json.loads(read_path(f'evidence/{version}/ubs_fresh_checks.json').read_text())
assert checks['process_id']==os.getpid() and checks['native_sha256']==digest
strip=[x for x in checks['headroom'] if box[0]<x['u']<box[1] and box[2]<x['v']<box[3]]
assert len(strip)==96 and all(x['clear'] for x in strip),[x for x in strip if not x['clear']]
report=dict(version=version,native=str(native),native_sha256=digest,process_id=os.getpid(),
            checked_utc=datetime.now(timezone.utc).isoformat(),remaining_photo_faces_checked=faces_checked,
            max_remaining_intersection_m2=maximum,matched_paving_uv_period_m=2.05,
            max_uv_error=max(uv_errors),nearfront_headroom_samples=len(strip),nearfront_headroom_clear=True,
            entry_centre_first_hit=ob.name,entry_centre_distance_m=float((p-cam.location).length),
            original_cameras_unchanged=len(r['before_cameras']),visual_acceptance=False,
            runtime_collision_verified=False,natural_use_verified=False)
write_path(f'evidence/{version}/nearfront_fresh_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('UBS_NEARFRONT_CHECKED',json.dumps(report),flush=True)
