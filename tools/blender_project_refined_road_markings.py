"""Conform the candidate's real paint-film vertices to its actual ground BVH.

Read-only for the native scene. This changes the prepared payload, then demands
the ordinary checks again; diagnostic mode itself is never an acceptance.
"""
from pathlib import Path
import hashlib,json,runpy
import bpy
import numpy as np

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/bridge_grade'
assert bpy.context.scene['version']=='G1_027r1'
state=runpy.run_path(str(R/'tools/blender_check_bridge_grade_refinement.py'),init_globals={'DIAGNOSTIC_ONLY':True})
data=np.load(D/'027r2_refined_patch.npz');arrays={k:data[k].copy() for k in data.files};data.close()
ref=np.load(D/'027r2_refined_reference.npz');record=json.loads((D/'027r2_refinement.json').read_text())
before=record['payload_sha256'];details=[]
for row in state['meta']['objects']:
    if row['role'] not in ['paint','crossing_paint']:continue
    key=row['key'];v=arrays[key];old=ref[key]
    xy,inverse=np.unique(old[:,:2],axis=0,return_inverse=True)
    top=np.full(len(xy),-np.inf);np.maximum.at(top,inverse,old[:,2])
    shift=np.zeros(len(v),np.float32);n=0;edge_retries=[]
    for i,p in enumerate(xy):
        if not (-297<p[0]<-254 and 110<p[1]<155):continue
        hit=state['ray'](p)
        matching=inverse==i
        expected=float(v[matching,2].max())-.0015
        if hit is None or abs(hit[0]-expected)>.025:
            # Source polygon and marker boundaries round independently in
            # float32. At an exact shared edge the BVH can miss the walk and
            # hit the road120mm below. Retry within0.2mm, never move the XY.
            alternatives=[state['ray'](p+offset) for offset in
                np.array([[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1],[1,-1],[-1,1]])*.0002]
            alternatives=[h for h in alternatives if h is not None]
            if alternatives:
                candidate=min(alternatives,key=lambda h:abs(h[0]-expected))
                if hit is None or abs(candidate[0]-expected)<abs(hit[0]-expected):
                    edge_retries.append(dict(xy=p.tolist(),first=hit[0] if hit else None,used=candidate[0]))
                    hit=candidate
        assert hit is not None,(row['name'],p.tolist())
        z=hit[0]+.0015-(top[i]-old[matching,2])
        shift[matching]=z-v[matching,2];n+=int(matching.sum())
    assert max(abs(shift))<.025,(row['name'],float(max(abs(shift))))
    v[:,2]+=shift
    details.append(dict(name=row['name'],projected_vertices=n,max_shift_m=float(max(abs(shift))),
                        inferred_film_height_m=.0015,xy_and_uv_unchanged=True,boundary_ray_retries=edge_retries))
np.savez_compressed(D/'027r2_refined_patch.npz',**arrays)
record.update(paint_projection=dict(before_payload_sha256=before,method='Downward ray on actual candidate road/walk/bank,1.5mm film; original thickness preserved.',objects=details),
    payload_sha256=hashlib.sha256((D/'027r2_refined_patch.npz').read_bytes()).hexdigest())
(D/'027r2_refinement.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
runpy.run_path(str(R/'tools/blender_check_bridge_grade_refinement.py'))
print('PAINT_SURFACE_CONFORMED',len(details),flush=True)
