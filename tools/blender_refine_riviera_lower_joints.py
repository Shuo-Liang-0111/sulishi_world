"""Apply the diagnosed real-boundary ramp fix before the first022 checkpoint."""
from pathlib import Path
import ast,json,hashlib
import bpy
import numpy as np
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/riviera_lower';s=bpy.context.scene
assert s['version']=='G1_022'
C=bpy.data.collections['36_RIVIERA_LOWER_APPROACH']
assert not C.get('ramp_boundary_repaired',False),'Repair already applied'
P=json.loads((D/'build_input.json').read_text());O=np.array(P['origin'])
mats={'paving':bpy.data.materials['RL | fine outdoor low deck']}
tree=ast.parse((R/'tools/blender_build_riviera_lower.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='mesh'],type_ignores=[]),'lower_mesh_helper','exec'))
changed=[]
for part in P['parts']:
    if part['role']!='paving':continue
    ob=bpy.data.objects['RL_'+part['name']];old=ob.data
    replacement=mesh('__TEMP_RAMP_'+part['name'],part['vertices'],part['faces'],'paving',part['source'])
    ob.data=replacement.data
    bpy.data.objects.remove(replacement,do_unlink=True)
    if old.users==0:bpy.data.meshes.remove(old)
    changed.append(ob.name)
C['ramp_boundary_repaired']=True
C['build_input_sha256']=hashlib.sha256((D/'build_input.json').read_bytes()).hexdigest()
bpy.context.view_layer.update()
(R/'evidence/G1_022/pre_save_repairs.json').write_text(json.dumps({
    'ramp_problem':'A simplified four-corner ramp omitted a14mm real AV boundary kink. One boundary sliver fell to the lower datum.',
    'repair':'Height classification follows the whole official spur; original XY and its kink retained.',
    'paving_objects_refreshed':changed,
    'bench_bearing_problem':'Initial slat ends stopped10mm before piers.',
    'bench_bearing_repair':'Seat boards extended50mm at each end, now overlap actual pier bearing; source builder updated.',
    'native_saved':False},indent=2))
print('LOWER_JOINT_REPAIRS',len(changed),flush=True)
