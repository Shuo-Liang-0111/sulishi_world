"""Read the retained terrain mesh to constrain the southern approach heights.

Run in the existing native scene before preparing023 input. No scene mutation.
"""
from pathlib import Path
import json
import bpy
import numpy as np

R=Path('F:/MyWorld/ZurichWorld')
assert bpy.context.scene['version'].startswith(('G1_022','G1_023'))
ob=bpy.data.objects['SURVEY_TERRAIN']
v=np.array([(ob.matrix_world@q.co)[:] for q in ob.data.vertices])
faces=np.array([list(p.vertices) for p in ob.data.polygons]);assert faces.shape[1]==3
centre=v[faces].mean(1)
mask=(centre[:,0]>-320)&(centre[:,0]<-235)&(centre[:,1]>65)&(centre[:,1]<165)
np.savez_compressed(R/'derived/bellevue/quaibruecke_connection/survey_terrain_context.npz',
                    triangles=v[faces[mask]]+np.array([2683775,1246700,400]))
print(json.dumps({'terrain_nearby_triangles':int(mask.sum()),'scene_unmodified':True}))
