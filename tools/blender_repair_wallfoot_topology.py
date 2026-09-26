"""Remove diagnosed dangling base sheets wholly enclosed by the rebuilt wall."""
from pathlib import Path
import hashlib,json,os,sys
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path
from blender_geometry_fingerprint import mesh_digest

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

assert Path(bpy.data.filepath).name=='G1_027r16_stadelhofen_wallfoot_candidate_r07.blend'
cp_path=write_path('evidence/G1_027r16/checkpoint.json');cp=json.loads(cp_path.read_text())
probe=json.loads(read_path('evidence/G1_027r16/base_topology_probe.json').read_text())
assert sha(bpy.data.filepath)==cp['native_sha256']==probe['native_sha256']
target=write_path('native/G1_027r16_stadelhofen_wallfoot_candidate_r08.blend');assert not target.exists()
ob=bpy.data.objects[probe['object']];before=mesh_digest(ob.data)
bm=bmesh.new();bm.from_mesh(ob.data);bm.faces.ensure_lookup_table();bm.edges.ensure_lookup_table()
bad=[e for e in bm.edges if not e.is_manifold]
assert len(bad)==6 and all(len(e.link_faces)==1 for e in bad)
chosen={f for e in bad for f in e.link_faces}
assert {f.index for f in chosen}=={row['index'] for e in probe['edges'] for row in e['faces']}
assert len(chosen)==3
# They are isolated sheets, not boundary faces of the volumetric base. Every
# face reachable across any of their edges must be one of these three faces.
assert all(f in chosen for c in chosen for e in c.edges for f in e.link_faces)
deps=bpy.context.evaluated_depsgraph_get();vv=[];ff=[]
for name in ['SJ_RIGHT_PLINTH_CORE','SJ_RIGHT_PLINTH_COURSE_0','SJ_RIGHT_PLINTH_COURSE_1']:
    other=bpy.data.objects[name];ev=other.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles();offset=len(vv)
    vv.extend(ev.matrix_world@v.co for v in me.vertices)
    ff.extend([offset+i for i in t.vertices] for t in me.loop_triangles);ev.to_mesh_clear()
wall=BVHTree.FromPolygons(vv,ff,all_triangles=True)
contained=[]
for v in {v for f in chosen for v in f.verts}:
    p=ob.matrix_world@v.co
    low,_,_,_=wall.ray_cast(Vector((p.x,p.y,10.0)),Vector((0,0,1)),2)
    high,_,_,_=wall.ray_cast(Vector((p.x,p.y,12.0)),Vector((0,0,-1)),2)
    assert low and high and low.z<p.z<high.z,('Dangling face outside actual wall',list(p))
    contained.append({'xyz':list(p),'wall_lower':low.z,'wall_upper':high.z})
removed=[{'face':f.index,'vertices':[v.index for v in f.verts],'area_m2':f.calc_area()} for f in chosen]
removed_candidates={v for f in chosen for v in f.verts}
# BMesh deletion may renumber indices. Keep the surviving element references,
# not mutable integer indices, when proving that no coordinate moved.
retained=[(v,tuple(v.co)) for v in bm.verts if v not in removed_candidates]
bmesh.ops.delete(bm,geom=list(chosen),context='FACES')
assert all(e.is_manifold for e in bm.edges), 'Surviving base is still open'
assert all(v.is_valid and tuple(v.co)==co for v,co in retained)
volume=bm.calc_volume(signed=True);assert volume>0
bm.to_mesh(ob.data);bm.free();ob.data.update()
rp=write_path('evidence/G1_027r16/wallfoot_build_report.json');r=json.loads(rp.read_text())
assert r['changed_old_meshes'][ob.name]['after']==json.loads(json.dumps(before))
r['changed_old_meshes'][ob.name]['after']=mesh_digest(ob.data)
r['base_topology_repair']={'process_id':os.getpid(),'source_native_sha256':cp['native_sha256'],
    'before':before,'after':mesh_digest(ob.data),'removed_isolated_faces':removed,
    'all_removed_vertices_within_actual_plinth':contained,'surviving_closed_volume_m3':volume,
    'retained_vertices_moved':False,'isolated_nonvolume_sheets_only':True}
rp.write_text(json.dumps(r,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(target),check_existing=False,compress=True)
cp.update(native=str(target),native_sha256=sha(target),native_bytes=target.stat().st_size,
          native_fresh_reopen_verified=False,wallfoot_bounded_geometry_verified=False,
          visual_acceptance=False,approved_as_working_native=False)
cp_path.write_text(json.dumps(cp,indent=2),encoding='utf-8')
print('BASE_TOPOLOGY_CANDIDATE_SAVED',json.dumps({k:cp[k] for k in ['native','native_sha256','native_bytes']}),flush=True)
import runpy
runpy.run_path(str(Path(__file__).parent/'blender_check_stadelhofen_01.py'),run_name='__main__')
print('SAME_PROCESS_STATION_PREFLIGHT_PASSED; fresh reopen and visual review still required',flush=True)
