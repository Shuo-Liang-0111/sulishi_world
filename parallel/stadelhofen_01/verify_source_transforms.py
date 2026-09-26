"""Capture evaluated transforms from the pinned r8 objects, without opening a city scene."""
import sys,os,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,'H:/MyWorld/ZurichWorld/tools')
from sf1_common import *
from blender_geometry_fingerprint import mesh_digest,object_state
assert not bpy.data.filepath,'Run from factory startup, no working scene.'
assert sha(D['base_native'])==D['base_sha256']
inv=json.loads((OUT/'derived/native_context_inventory.json').read_text());old={r['original_name']:r for r in inv['objects']}
C=collection('SF1_SOURCE_TRANSFORM_PROBE')
with bpy.data.libraries.load(D['base_native'],link=False) as (src,dst):
    dst.objects=list(old)
for ob in dst.objects:C.objects.link(ob)
bpy.context.view_layer.update()
rows=[]
for ob in dst.objects:
    assert json.loads(json.dumps(mesh_digest(ob.data)))==old[ob.name]['mesh_digest']
    state=object_state(ob)
    rows.append(dict(original_name=ob.name,state=state,initial_transform_record_was_stale=state['matrix_world']!=old[ob.name]['object_state']['matrix_world']))
assert sha(D['base_native'])==D['base_sha256']
result=dict(base_native=D['base_native'],base_sha256=D['base_sha256'],process_id=os.getpid(),objects=rows,source_geometry_matches_initial_inventory=True,saved_any_native=False,reason='Initial extraction inventory captured matrix_world immediately after library append/link and before dependency evaluation. This independently re-appends only the 53 pinned source objects and updates the dependency graph before recording their world transforms.')
write('derived/verified_source_transforms.json',result);write('evidence/v05/source_transform_verification.json',result)
print('SF1_SOURCE_TRANSFORMS_VERIFIED',len(rows),'initial_stale',sum(r['initial_transform_record_was_stale'] for r in rows),flush=True)
