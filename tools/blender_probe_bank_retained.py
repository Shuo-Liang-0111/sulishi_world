"""Read retained-photo hits and original UVs from actual rejected bank views.

Only the visible photographic context is traced. Results are not claimed to be
the frontmost hit of the entire scene; authored structures are reviewed apart.
"""
from pathlib import Path
import json
import bpy
import numpy as np
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version']=='G1_025r1'
cases={
    'QB_QA_SOUTH':[(600,240),(930,280),(915,70),(440,615)],
    'UB_QA_SOUTH':[(420,435),(850,460),(1110,500),(400,178),(700,400)],
    'UB_QA_NORTH':[(637,555),(433,525),(1100,500),(1070,312)]}
objects=[o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects
         if o.type=='MESH' and not o.hide_render]
origin=np.array([2683775.,1246700.,400.]);rows=[]
size=(s.render.resolution_x,s.render.resolution_y)
try:
    s.render.resolution_x=1280;s.render.resolution_y=840
    for name,pixels in cases.items():
        cam=bpy.data.objects[name];frame=cam.data.view_frame(scene=s)
        xmin=min(p.x/-p.z for p in frame);xmax=max(p.x/-p.z for p in frame)
        ymin=min(p.y/-p.z for p in frame);ymax=max(p.y/-p.z for p in frame)
        near=[]
        for ob in objects:
            v=np.array([ob.matrix_world@Vector(q) for q in ob.bound_box])
            if np.linalg.norm(np.clip(np.array(cam.location),v.min(0),v.max(0))-np.array(cam.location))<100:
                near.append((ob,ob.matrix_world.inverted()))
        for x,y in pixels:
            ray=cam.matrix_world.to_quaternion()@Vector((xmin+(xmax-xmin)*x/1280,ymax-(ymax-ymin)*y/840,-1)).normalized()
            hits=[]
            for ob,inv in near:
                hit,p,normal,index=ob.ray_cast(inv@cam.location,inv.to_3x3()@ray)
                if not hit:continue
                q=ob.matrix_world@p;distance=(q-cam.location).length
                if distance>100:continue
                f=ob.data.polygons[index]
                uv=np.array([ob.data.uv_layers.active.data[i].uv[:] for i in f.loop_indices]);uv[:,1]=1-uv[:,1]
                hits.append(dict(object=ob.name,node=str(ob['source_node']),face=index,
                    point_lv95=(np.array(q,dtype=np.float64)+origin).tolist(),distance_m=distance,
                    vertices_lv95=[(np.array(ob.matrix_world@ob.data.vertices[i].co,dtype=np.float64)+origin).tolist() for i in f.vertices],
                    original_uv=uv.tolist()))
            hits.sort(key=lambda q:q['distance_m'])
            rows.append(dict(camera=name,pixel=[x,y],hits=hits[:1]))
finally:s.render.resolution_x,s.render.resolution_y=size
report=dict(version=s['version'],photo_only=True,scene_changed=False,pixels=rows)
(R/'evidence/G1_025r1/retained_bank_probes.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(hits=[dict(camera=q['camera'],pixel=q['pixel'],first={k:v for k,v in q['hits'][0].items() if k not in ['vertices_lv95','original_uv']} if q['hits'] else None) for q in rows])),flush=True)
