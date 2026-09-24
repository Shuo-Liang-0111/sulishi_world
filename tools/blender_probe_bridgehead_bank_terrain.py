"""Read-only extraction of the retained terrain supporting upper-bank authoring.

Uses local-coordinate matrix arithmetic, then adds LV95 origin in float64.
Never add million-metre coordinates to a float32 mathutils Vector.
"""
from pathlib import Path
import hashlib,json
import bpy
import numpy as np

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/bridgehead_bank'
assert bpy.context.scene['version'].startswith(('G1_024','G1_025'))
ob=bpy.data.objects['SURVEY_TERRAIN']
v=np.array([list(ob.matrix_world@q.co) for q in ob.data.vertices],dtype=np.float64)
f=np.array([list(p.vertices) for p in ob.data.polygons]);assert f.shape[1]==3
c=v[f].mean(axis=1)
mask=(c[:,0]>-330)&(c[:,0]<-190)&(c[:,1]>30)&(c[:,1]<170)
triangles=v[f[mask]]+np.array([2683775.,1246700.,400.])
path=D/'survey_terrain.npz';D.mkdir(parents=True,exist_ok=True)
if path.exists():
    old=np.load(path)['triangles']
    assert old.shape==triangles.shape and np.array_equal(old,triangles),'Existing extraction differs; inspect before replacing'
else:np.savez_compressed(path,triangles=triangles)
report=dict(native=bpy.data.filepath,scene_version=bpy.context.scene['version'],
    selected_triangles=int(mask.sum()),origin_lv95_ln02=[2683775,1246700,400],
    output_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),scene_changed=False)
(D/'terrain_provenance.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('BANK_TERRAIN_PROVENANCE',json.dumps(report),flush=True)
