"""Locate observed defects in the actual east review image; no geometry mutation."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_015'
c=bpy.data.objects['BE_QA_SOUTH_GROVE_EAST'];s.camera=c
s.render.resolution_x=1600;s.render.resolution_y=1050
bpy.context.view_layer.update()
frame=c.data.view_frame(scene=s);xmin=min(p.x/-p.z for p in frame);xmax=max(p.x/-p.z for p in frame);ymin=min(p.y/-p.z for p in frame);ymax=max(p.y/-p.z for p in frame)
objects=list(bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects)+list(bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].all_objects)
deps=bpy.context.evaluated_depsgraph_get();evaluated=[]
for ob in objects:
    if ob.type not in ['MESH','CURVE','FONT'] or ob.hide_render:continue
    eo=ob.evaluated_get(deps);inv=eo.matrix_world.inverted();evaluated.append((ob,eo,inv))
records=[]
for px,py,reason in [(843,274,'floating central photo canopy'),(726,318,'left photo remnant'),
                      (1112,225,'upper photo fragment'),(1180,683,'pale arc at nearest tree'),
                      (708,667,'pale arc at central tree'),(1457,651,'flat photo near road')]:
    d=Vector((xmin+(xmax-xmin)*px/1600,ymax-(ymax-ymin)*py/1050,-1)).normalized()
    d=c.matrix_basis.to_quaternion()@d;hits=[]
    for ob,eo,inv in evaluated:
        hit,p,normal,index=eo.ray_cast(inv@c.location,inv.to_3x3()@d)
        if hit:
            wp=eo.matrix_world@p;dist=(wp-c.location).length
            if dist<150:hits.append({'object':ob.name,'source_node':ob.get('source_node'),
                                    'distance_m':dist,'point_local':list(wp),'face':index})
    hits.sort(key=lambda h:h['distance_m'])
    records.append({'pixel':[px,py],'reason':reason,'hits':hits[:4]})
(R/'evidence/G1_015/east_residual_rays.json').write_text(json.dumps(records,indent=2))
print(json.dumps(records),flush=True)
