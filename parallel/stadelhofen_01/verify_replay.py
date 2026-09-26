"""Verify integration on the bounded baseline, never on the main native."""
import sys,os,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,'H:/MyWorld/ZurichWorld/tools')
from sf1_common import *
from blender_geometry_fingerprint import mesh_digest
from apply_increment import apply_to_current
assert Path(bpy.data.filepath).resolve()==(OUT/'native/SF1_baseline_local.blend').resolve()
assert bpy.context.scene.get('sf1_version')=='SF1_baseline'
baseline_hash=sha(bpy.data.filepath);base_hash=sha(D['base_native'])
inv=json.loads((OUT/'derived/native_context_inventory.json').read_text())
for row in inv['objects']:bpy.data.objects[row['local_name']].name=row['original_name']
result=apply_to_current();tag=D['version'].split('_')[-1]
cuts=json.loads((OUT/'derived/crop_manifest.json').read_text())['cuts'];compared=[]
for row in cuts:
    digest=json.loads(json.dumps(mesh_digest(bpy.data.objects[row['base_object']].data)))
    assert digest==row['after_digest'],row['base_object']
    compared.append(row['base_object'])
manifest=json.loads((OUT/f'evidence/{tag}/construction.json').read_text());C=bpy.data.collections[D['import_collection']]
assert len(C.all_objects)==len(manifest['authored_objects'])
for row in manifest['authored_objects']:
    ob=bpy.data.objects[row['name']];assert ob.name in C.all_objects
    if ob.type=='MESH':assert json.loads(json.dumps(mesh_digest(ob.data)))==row['mesh_digest'],ob.name
control=bpy.data.objects['SF1_DOOR_CENTRE_CONTROL'];states=[]
for f in [0,1,0]:
    control['open_fraction']=float(f);control.update_tag();bpy.context.scene.frame_set(bpy.context.scene.frame_current);bpy.context.view_layer.update()
    angles=[bpy.data.objects['SF1_BAY2_'+x+'_PIVOT'].rotation_euler.z for x in ['LEFT','RIGHT']]
    assert all(abs(a-e)<1e-5 for a,e in zip(angles,[-f*math.radians(95),f*math.radians(95)]))
    states.append(dict(fraction=f,actual_angles_radians=angles))
unchanged=[]
verified=json.loads((OUT/'derived/verified_source_transforms.json').read_text());expected={r['original_name']:r['state']['matrix_world'] for r in verified['objects']}
for row in inv['objects']:
    assert [float(x) for r in bpy.data.objects[row['original_name']].matrix_world for x in r]==expected[row['original_name']],row['original_name']
    if row['original_name'] in compared:continue
    assert json.loads(json.dumps(mesh_digest(bpy.data.objects[row['original_name']].data)))==row['mesh_digest']
    unchanged.append(row['original_name'])
assert sha(bpy.data.filepath)==baseline_hash and sha(D['base_native'])==base_hash==D['base_sha256']
write(f'evidence/{tag}/integration_replay.json',dict(version=D['version'],process_id=os.getpid(),passed=True,main_native_saved=False,local_baseline_saved=False,main_base_sha256=base_hash,author_objects=len(C.all_objects),compared_cropped_meshes=compared,unchanged_context=unchanged,driver_states=states,import_report=result))
print('SF1_INTEGRATION_REPLAY_OK',len(C.all_objects),len(compared),len(unchanged),flush=True)
