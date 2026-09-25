"""Verify the finite photo edit from the saved checkpoint, including retained UVs."""
import hashlib
import json
import sys
from pathlib import Path
import bpy
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path
from blender_geometry_fingerprint import mesh_digest

assert bpy.context.scene['version']=='G1_027r3'
spec_path=read_path('derived/bridge_context/027r3_cleanup_input.json')
spec=json.loads(spec_path.read_text())
built=json.loads(read_path('evidence/G1_027r3/construction.json').read_text())
assert hashlib.sha256(spec_path.read_bytes()).hexdigest()==built['input_sha256']
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
checked=[]
for row,after in zip(spec['objects'],built['objects']):
    assert row['object']==after['object']
    ob=bpy.data.objects[row['object']];mesh=ob.data
    assert json.loads(json.dumps(mesh_digest(mesh)))==after['after_fingerprint'],ob.name
    before=json.loads(read_path('derived/bridge_context/'+ob.name+'.json').read_text())
    remove=set(row['removed_faces']);keep=[i for i in range(len(before['faces'])) if i not in remove]
    assert [list(p.vertices) for p in mesh.polygons]==[before['faces'][i] for i in keep]
    assert np.array_equal(np.array([list(ob.matrix_world@v.co) for v in mesh.vertices]),np.array(before['vertices']))
    uv=mesh.uv_layers.active
    assert np.array_equal(np.array([uv.data[i].uv[:] for p in mesh.polygons for i in p.loop_indices]),
                          np.array([uv for i in keep for uv in before['uv_faces'][i]]))
    checked.append(dict(object=ob.name,kept_faces=len(keep),removed_faces=len(remove)))
report=dict(version='G1_027r3',checked=checked,total_removed_faces=sum(q['removed_faces'] for q in checked),
    retained_vertex_and_uv_values_exact=True,flags_lamps_water_not_in_removal=True,visual_acceptance=False,natural_use_verified=False)
write_path('evidence/G1_027r3/photo_cleanup_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BRIDGE_PHOTO_CLEANUP_VERIFIED',json.dumps(report),flush=True)
