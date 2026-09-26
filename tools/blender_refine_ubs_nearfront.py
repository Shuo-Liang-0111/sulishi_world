"""Repair the rejected r9 entrance without changing its camera or the shelter.

This script must run only after the main thread receives the Blender lease.
The measured AV26313 strip already has authored ground. Farther station
canopy, poster cases, street furniture and the source archive are preserved.
"""
from pathlib import Path
import hashlib,json,shutil,sys
import bpy,numpy as np
from mathutils import Vector

sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import ROOT,read_path,write_path
from blender_geometry_fingerprint import object_state,mesh_digest
from blender_photo_clip import cut_object

s=bpy.context.scene
assert s['version']=='G1_027r9'
lease=json.loads(read_path('runtime/coordination/blender_lease.json').read_text(encoding='utf-8-sig'))
assert lease['owner_thread']=='01a08947-06f2-7123-b7c7-c955cfa6c809', 'Main Blender lease required'
assert not lease.get('secondary_may_launch',False)
version='G1_027r10'
target=write_path('native/G1_027r10_ubs_nearfront_repair.blend')
assert not target.exists() and shutil.disk_usage(ROOT).free>3_000_000_000
cp=json.loads(read_path('evidence/G1_027r9/checkpoint.json').read_text())
with Path(bpy.data.filepath).open('rb') as f:
    assert hashlib.file_digest(f,'sha256').hexdigest()==cp['native_sha256']
assert cp['native_fresh_reopen_verified'] and not cp['visual_acceptance']
specpath=read_path('derived/ubs_theaterstrasse20/build_input.json')
reviewpath=read_path('derived/ubs_theaterstrasse20/sidewalk_review.json')
d=json.loads(specpath.read_text());review=json.loads(reviewpath.read_text())
r=json.loads(read_path('evidence/G1_027r9/ubs_build_report.json').read_text())
assert hashlib.sha256(specpath.read_bytes()).hexdigest()==r['spec_sha256']
A,U,N=(np.array(d[k]) for k in ['A','U','N'])
def Q(p):return np.r_[(p[:2]-A)@U,(p[:2]-A)@N,p[2]]

# Reconstructed sidewalk only. The real station shelter is more than 12m out.
box=[-.055,d['street_width_m']+.025,1.18,4.4,8.18,12.10]
assert all(not x['intersects_proposed_review'] for x in review['official_vbz_fixtures'])
assert any(x['id']=='av_bo_boflaeche_a.26313' and x['type']=='befestigt.Trottoir'
           and x['area_m2']>70 for x in review['proposed_review_land_use'])
assert all(x['local_bounds'][0][1]>box[3]+7 for x in review['official_shelter_roofs'])
states={o.name:object_state(o) for o in s.objects}
mesh_pointers={o.name:o.data.as_pointer() for o in s.objects if o.type=='MESH'}
source_pointers={o.name:o.data.as_pointer() for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
cafe={o.name:mesh_digest(o.data) for o in bpy.data.collections['45_STERNEN_GRILL_FRONTAGES'].objects if o.type=='MESH'}
before_cameras={o.name:{'matrix':[list(row) for row in o.matrix_world],
                      'lens':o.data.lens,'sensor_width':o.data.sensor_width}
                for o in s.objects if o.type=='CAMERA'}
cuts=[]
for name,count in r['final_photo_counts'].items():
    ob=bpy.data.objects[name];assert len(ob.data.polygons)==count
    result=cut_object(ob,Q,[box])
    if result:
        result['pass']='reconstructed_AV26313_nearfront';cuts.append(result)
assert cuts and any(x['object']=='CTX_I3S_33436' for x in cuts)

# Keep all existing ground positions and topology; only correct UV units.
ground=bpy.data.objects['UF_CONTINUOUS_STREET_APPROACH']
assert ground.data.users==1
before_ground=mesh_digest(ground.data)
positions=np.empty(len(ground.data.vertices)*3,dtype=np.float32)
ground.data.vertices.foreach_get('co',positions)
indices=np.empty(len(ground.data.loops),dtype=np.int32)
ground.data.loops.foreach_get('vertex_index',indices)
geometry_hash=hashlib.sha256(positions.tobytes()+indices.tobytes()).hexdigest()
uv=ground.data.uv_layers.active
before_uv=np.empty(len(uv.data)*2,dtype=np.float32);uv.data.foreach_get('uv',before_uv)
period=2.05
for face in ground.data.polygons:
    for li in face.loop_indices:
        p=ground.matrix_world@ground.data.vertices[ground.data.loops[li].vertex_index].co
        uv.data[li].uv=(p.x/period,p.y/period)
after_positions=np.empty_like(positions);ground.data.vertices.foreach_get('co',after_positions)
after_indices=np.empty_like(indices);ground.data.loops.foreach_get('vertex_index',after_indices)
assert np.array_equal(positions,after_positions) and np.array_equal(indices,after_indices)
after_uv=np.empty_like(before_uv);uv.data.foreach_get('uv',after_uv)
assert not np.array_equal(before_uv,after_uv)

changed={x['object'] for x in cuts}
assert source_pointers=={o.name:o.data.as_pointer() for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
assert all(mesh_digest(bpy.data.objects[n].data)==h for n,h in cafe.items())
assert all(object_state(bpy.data.objects[n])==state for n,state in states.items())
assert all(bpy.data.objects[n].data.as_pointer()==p for n,p in mesh_pointers.items() if n not in changed)
assert before_cameras=={o.name:{'matrix':[list(row) for row in o.matrix_world],
                              'lens':o.data.lens,'sensor_width':o.data.sensor_width}
                       for o in s.objects if o.type=='CAMERA'}
bpy.context.view_layer.update()
cam=bpy.data.objects['UF_QA_ENTRY'];direction=cam.matrix_world.to_quaternion()@Vector((0,0,-1))
hit,point,normal,face,ob,m=s.ray_cast(bpy.context.evaluated_depsgraph_get(),cam.location,direction,distance=8)
assert hit and ob.name.startswith('UF_'),('entry_still_blocked',ob.name if hit else None)

report=dict(version=version,base_native=cp['native'],base_native_sha256=cp['native_sha256'],
    bounds_front_frame=box,frame=dict(A=d['A'],U=d['U'],N=d['N']),
    reasoning='Replace only retained photo over already-authored near-front sidewalk AV26313. '
              'The official shelter, poster cases and other known VBZ facilities lie outside this volume. '
              'MML photo supports an open bank-side walk strip; unsurveyed small temporary items are not asserted absent.',
    diagnosis_sha256=hashlib.sha256(reviewpath.read_bytes()).hexdigest(),
    photo_cuts=cuts,source_objects_unchanged=len(source_pointers),cafe_meshes_unchanged=len(cafe),
    before_cameras=before_cameras,old_object_states_unchanged=len(states),
    ground_geometry_sha256=geometry_hash,ground_before=before_ground,
    ground_after=mesh_digest(ground.data),ground_uv_period_m=period,
    ground_previous_uv_sha256=hashlib.sha256(before_uv.tobytes()).hexdigest(),
    ground_uv_sha256=hashlib.sha256(after_uv.tobytes()).hexdigest(),
    entry_centre_first_hit=ob.name,entry_centre_distance_m=float((point-cam.location).length),
    protected_shelters=review['official_shelter_roofs'],
    protected_facilities=[x['id'] for x in review['official_vbz_fixtures']],
    limits=['Front view may still intersect the farther real shelter, which remains pending reconstruction.',
            'A central ray is not a visual or walking acceptance. Same-camera renders must be reviewed.',
            'The bank/store is not opened as a public interior; runtime and natural use remain unverified.'])
out=write_path(f'evidence/{version}/nearfront_build_report.json')
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
r.update(version=version,preserved_ubs_report_version='G1_027r9',
         final_photo_counts={n:len(bpy.data.objects[n].data.polygons) for n in r['final_photo_counts']})
write_path(f'evidence/{version}/ubs_build_report.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
old=json.loads(read_path('evidence/G1_027r9/build_report.json').read_text())
counts=old.get('subsequent_photo_counts',{});counts.update(r['final_photo_counts'])
old.update(version=version,subsequent_photo_counts=counts)
write_path(f'evidence/{version}/build_report.json').write_text(json.dumps(old,indent=2),encoding='utf-8')
s['version']=version;s['latest_construction']='AV26313 bounded near-front scan replacement and matching pavement UV; visual review pending'
bpy.ops.wm.save_as_mainfile(filepath=str(target),check_existing=False,compress=True)
with target.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
receipt={k:cp[k] for k in ['storage_sharing_applied','required_immutable_libraries','shared_meshes','shared_objects']}
receipt.update(version=version,native=str(target),native_sha256=digest,native_bytes=target.stat().st_size,
               objects=len(s.objects),native_fresh_reopen_verified=False,visual_acceptance=False,
               runtime_exported=False,natural_use_verified=False)
write_path(f'evidence/{version}/checkpoint.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('UBS_NEARFRONT_SAVED',json.dumps({k:receipt[k] for k in ['version','native','native_bytes','native_sha256','objects']}),flush=True)
