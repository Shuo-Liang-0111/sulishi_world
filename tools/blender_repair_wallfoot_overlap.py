"""Remove only the obsolete base/sidewall overlap inside existing masonry."""
from pathlib import Path
import hashlib,json,os,sys
import bpy,bmesh,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path
from blender_geometry_fingerprint import mesh_digest,object_state

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

s=bpy.context.scene;assert s['version']=='G1_027r16'
assert Path(bpy.data.filepath).name=='G1_027r16_stadelhofen_wallfoot_candidate_r05.blend'
cpp=write_path('evidence/G1_027r16/checkpoint.json')
cp=json.loads(read_path('evidence/G1_027r16/attempt05_wall_overlap_failure/checkpoint.json').read_text())
assert sha(bpy.data.filepath)==cp['native_sha256']
target=write_path('native/G1_027r16_stadelhofen_wallfoot_candidate_r07.blend');assert not target.exists()
sp=read_path('derived/stadelhofen_joint/G1_027r16/construction_r07.json');d=json.loads(sp.read_text())
assert d['base_cut_inside_cheek_m']==.01
assert d['cutter_vertical_offsets_m'][0]==-.043, 'Keep the continuous lower bearing bed'
for row in d['source_files']:assert sha(row['path'])==row['sha256']
A,U,N=[np.asarray(d['frame'][k]) for k in ['A','U','N']]
before={o.name:object_state(o) for o in s.objects}
pointers={o.name:o.data.as_pointer() for o in s.objects if o.type=='MESH'}
base=bpy.data.objects['SF1_APRON_CONTINUOUS_SUBBASE'];old_hash=mesh_digest(base.data)
mesh=d['cutter'];me=bpy.data.meshes.new('SJ_TEMP_BURIED_BASE_CUT_mesh')
me.from_pydata([[*(A+U*p[0]+N*p[1]),p[2]] for p in mesh['vertices_uvz']],[],mesh['faces']);me.update()
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
assert all(e.is_manifold for e in bm.edges);bm.to_mesh(me);bm.free()
cut=bpy.data.objects.new('SJ_TEMP_BURIED_BASE_CUT',me);s.collection.objects.link(cut)
mod=base.modifiers.new('remove_buried_coplanar_base_only','BOOLEAN');mod.solver='EXACT';mod.operation='DIFFERENCE';mod.object=cut
bpy.context.view_layer.objects.active=base;base.select_set(True)
assert 'FINISHED' in bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(cut,do_unlink=True)
assert all(object_state(bpy.data.objects[n])==v for n,v in before.items())
assert all(bpy.data.objects[n].data.as_pointer()==p for n,p in pointers.items() if n!=base.name)
rp=write_path('evidence/G1_027r16/wallfoot_build_report.json')
r=json.loads(read_path('evidence/G1_027r16/attempt05_wall_overlap_failure/wallfoot_build_report.json').read_text())
assert r['changed_old_meshes'][base.name]['after']==json.loads(json.dumps(old_hash))
r['changed_old_meshes'][base.name]['after']=mesh_digest(base.data)
r['specification_file']=str(sp);r['specification_sha256']=sha(sp)
r['buried_overlap_repair']={'process_id':os.getpid(),'source_native_sha256':cp['native_sha256'],
    'before':old_hash,'after':mesh_digest(base.data),'clearance_inside_existing_cheek_m':.01,
    'cut_bottom_relative_to_actual_ground_m':-.043,'lower_bearing_bed_retained':True,
    'sidewall_and_stones_unchanged':True,'independent_hidden_volume_check_required':True}
rp.write_text(json.dumps(r,indent=2),encoding='utf-8')
s['latest_construction']='Main wallfoot repair: same external structure; remove obsolete buried base coplanar with the cheek wall.'
bpy.ops.wm.save_as_mainfile(filepath=str(target),check_existing=False,compress=True)
cp.update(native=str(target),native_sha256=sha(target),native_bytes=target.stat().st_size,
          native_fresh_reopen_verified=False,wallfoot_bounded_geometry_verified=False,visual_acceptance=False,
          approved_as_working_native=False,runtime_exported=False,natural_use_verified=False)
cpp.write_text(json.dumps(cp,indent=2),encoding='utf-8')
print('BURIED_OVERLAP_CANDIDATE_SAVED',json.dumps({k:cp[k] for k in ['native','native_sha256','native_bytes','objects']}),flush=True)
import runpy
runpy.run_path(str(Path(__file__).parent/'blender_check_stadelhofen_01.py'),run_name='__main__')
print('SAME_PROCESS_STATION_PREFLIGHT_PASSED; fresh reopen and visual review still required',flush=True)
