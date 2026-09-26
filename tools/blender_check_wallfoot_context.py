"""Independently verify the persisted four-face scan-foot correction."""
from pathlib import Path
import hashlib,json,os,sys
import bpy,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path
from blender_geometry_fingerprint import mesh_digest

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def check():
    r=json.loads(read_path('evidence/G1_027r16/adjacent_ground_repair.json').read_text())
    br=json.loads(read_path('evidence/G1_027r16/wallfoot_build_report.json').read_text())
    assert sha(br['adjacent_photo_repair_file'])==br['adjacent_photo_repair_sha256']
    assert sha(r['preserved_array_file'])==r['preserved_array_sha256']
    old=np.load(r['preserved_array_file']);ob=bpy.data.objects[r['object']];me=ob.data
    assert json.loads(json.dumps(mesh_digest(me)))==r['after']
    p=np.asarray([v.co[:] for v in me.vertices],dtype=np.float32)
    faces=np.asarray([x.vertices[:] for x in me.polygons],dtype=np.int32)
    ids=[x['vertex'] for x in r['changed_vertices']]
    keep=np.ones(len(p),bool);keep[ids]=False
    assert np.array_equal(p[keep],old['positions'][keep])
    assert np.array_equal(faces,old['faces'])
    assert np.array_equal(np.asarray(ob.matrix_world),old['matrix'])
    assert np.array_equal(np.asarray([x.uv[:] for x in me.uv_layers.active.data],dtype=np.float32),old['uv'])
    assert np.array_equal(np.asarray([x.use_smooth for x in me.polygons]),old['smooth'])
    assert np.array_equal(np.asarray([x.material_index for x in me.polygons]),old['materials'])
    for row in r['changed_vertices']:assert np.array_equal(p[row['vertex']],np.asarray(row['new_local_xyz'],dtype=np.float32))
    # Derive the reference plane afresh from actual unchanged adjacent geometry,
    # rather than accepting the builder's supplied coefficient or slope limit.
    matrix=np.asarray(ob.matrix_world);world=p@matrix[:3,:3].T+matrix[:3,3]
    pp=world[faces[85]];normal=np.cross(pp[1]-pp[0],pp[2]-pp[0]);normal/=np.linalg.norm(normal)
    error=float(np.abs((world[faces[[28,87]]]-pp[0])@normal).max())
    assert error<.00002,('Repaired paving not coplanar with actual adjacent ground',error)
    report={'process_id':os.getpid(),'passed':True,'preserved_vertices':int(keep.sum()),'changed_vertices':len(ids),
            'affected_faces':r['affected_faces'],'unchanged_uv_and_topology':True,
            'adjacent_plane_error_m':error,'visual_acceptance':False}
    write_path('evidence/G1_027r16/adjacent_ground_fresh_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('ADJACENT_GROUND_CHECKED',json.dumps(report),flush=True)
    return report

if __name__=='__main__':check()
