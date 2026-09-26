"""Close the measured narrow paving joint by repairing two scan-foot vertices.

The adjacent planar pavement (unchanged face85) supplies the level. This is an
inferred repair of scanning distortion, not a centimetre survey measurement.
No face is hidden/deleted; the four connected faces keep their UVs and identity.
"""
from pathlib import Path
import hashlib,json,os,sys
import bpy,numpy as np
import runpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path
from blender_geometry_fingerprint import mesh_digest,object_state

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

s=bpy.context.scene;assert s['version']=='G1_027r16'
assert Path(bpy.data.filepath).name=='G1_027r16_stadelhofen_wallfoot_candidate_r04.blend'
cp_path=write_path('evidence/G1_027r16/checkpoint.json')
cp=json.loads(cp_path.read_text());assert sha(bpy.data.filepath)==cp['native_sha256']
runpy.run_path(str(Path(__file__).parent/'blender_check_stadelhofen_wallfoot.py'),run_name='__main__')
target=write_path('native/G1_027r16_stadelhofen_wallfoot_candidate_r05.blend');assert not target.exists()
ground_path=read_path('derived/stadelhofen_joint/G1_027r16/current_adjacent_ground.json')
d=json.loads(ground_path.read_text());assert d['native_sha256']==cp['native_sha256']
A,U,N=[np.asarray(d['frame'][k]) for k in ['A','U','N']]
ob=bpy.data.objects[d['object']];before=mesh_digest(ob.data)
assert json.loads(json.dumps(before))==d['mesh'] and not ob.modifiers
states={x.name:object_state(x) for x in s.objects}
pointers={x.name:x.data.as_pointer() for x in s.objects if x.type=='MESH'}
old=ob.data
xyz=np.asarray([v.co[:] for v in old.vertices],dtype=np.float32)
faces=np.asarray([p.vertices[:] for p in old.polygons],dtype=np.int32)
assert faces.shape==(len(old.polygons),3)
uv=np.asarray([x.uv[:] for x in old.uv_layers.active.data],dtype=np.float32)
smooth=np.asarray([p.use_smooth for p in old.polygons]);mats=np.asarray([p.material_index for p in old.polygons])
sealed=write_path('derived/stadelhofen_joint/G1_027r16/adjacent_photo_before.npz')
assert not sealed.exists()
np.savez_compressed(sealed,positions=xyz,faces=faces,uv=uv,smooth=smooth,materials=mats,
                    matrix=np.asarray(ob.matrix_world,dtype=float))
rows={r['polygon']:r for r in d['rows']}
plane_pts=np.asarray(rows[85]['uvz'])
plane=np.linalg.solve(np.c_[np.ones(3),plane_pts[:,:2]],plane_pts[:,2])
# These two broken scan-foot points are shared geometrically by four faces.
# Include every coincident occurrence, including the lower corners of the wall,
# so lowering the paving never tears a wall/ground seam.
corners=[np.asarray(rows[28]['uvz'][2]),np.asarray(rows[87]['uvz'][2])]
new=old.copy();new.name='SJ_REPAIRED_GROUND_'+ob.name
changed=[]
for v in new.vertices:
    world=ob.matrix_world@v.co
    q=np.array([(np.asarray(world[:2])-A)@U,(np.asarray(world[:2])-A)@N,world.z])
    if not any(np.linalg.norm(q-c)<.00001 for c in corners):continue
    level=float(np.array([1,q[0],q[1]])@plane)
    assert .07<q[2]-level<.09
    repaired=Vector((world.x,world.y,level));v.co=ob.matrix_world.inverted()@repaired
    changed.append({'vertex':v.index,'old_local_xyz':xyz[v.index].tolist(),'new_local_xyz':list(v.co),
                    'uvz_before':q.tolist(),'uvz_after':[q[0],q[1],level]})
assert len(changed)==5
ids={r['vertex'] for r in changed}
affected=[p.index for p in new.polygons if ids.intersection(p.vertices)]
assert affected==[28,87,97,98],affected
new.update();ob.data=new
assert all(object_state(bpy.data.objects[n])==state for n,state in states.items())
assert all(bpy.data.objects[n].data.as_pointer()==p for n,p in pointers.items() if n!=ob.name)
report={'process_id':os.getpid(),'object':ob.name,'source_native_sha256':cp['native_sha256'],
        'diagnostic_file':str(ground_path),'diagnostic_sha256':sha(ground_path),
        'before':before,'after':mesh_digest(new),'preserved_array_file':str(sealed),'preserved_array_sha256':sha(sealed),
        'basis_face':85,'basis_plane_c_u_v':plane.tolist(),'changed_vertices':changed,'affected_faces':affected,
        'inferred':True,'basis':'Continue adjacent observed plane85 through two distorted scan-foot corners; preserve real wall and external layout.',
        'source_photography_unchanged':True,'visual_acceptance':False}
rp=write_path('evidence/G1_027r16/adjacent_ground_repair.json')
rp.write_text(json.dumps(report,indent=2),encoding='utf-8')
br=write_path('evidence/G1_027r16/wallfoot_build_report.json');r=json.loads(br.read_text())
r['adjacent_photo_repair_file']=str(rp);r['adjacent_photo_repair_sha256']=sha(rp)
br.write_text(json.dumps(r,indent=2),encoding='utf-8')
s['latest_construction']='Main r16 candidate: lower return, whole stones, clean base edge, and bounded scan-foot continuity.'
bpy.ops.wm.save_as_mainfile(filepath=str(target),check_existing=False,compress=True)
cp.update(native=str(target),native_sha256=sha(target),native_bytes=target.stat().st_size,
          native_fresh_reopen_verified=False,wallfoot_bounded_geometry_verified=False,visual_acceptance=False,
          approved_as_working_native=False,runtime_exported=False,natural_use_verified=False)
cp_path.write_text(json.dumps(cp,indent=2),encoding='utf-8')
print('WALLFOOT_CONTEXT_CANDIDATE_SAVED',json.dumps({k:cp[k] for k in ['native','native_sha256','native_bytes','objects']}),flush=True)
