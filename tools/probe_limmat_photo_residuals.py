"""Read-only ray attribution of defects actually visible in019r1 review images."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_019r1'
saved_res=(s.render.resolution_x,s.render.resolution_y);s.render.resolution_x=1280;s.render.resolution_y=840
cases={'BE_QA_LIMMAT_SOUTH':[(120,430),(640,430),(1100,450)],'BE_QA_LIMMAT_NORTH':[(180,410),(450,180),(800,170),(1200,540)],'BE_QA_LIMMAT_PLANE_ROOT':[(640,420),(1000,300)],'BE_QA_LIMMAT_SOPHORA_ROOT':[(1150,665)],'BE_QA_LIMMAT_REVERSE':[(1000,420),(550,700)]}
objects=list(bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects);rec=[]
for name,pixels in cases.items():
 c=bpy.data.objects[name];frame=c.data.view_frame(scene=s);xmin=min(p.x/-p.z for p in frame);xmax=max(p.x/-p.z for p in frame);ymin=min(p.y/-p.z for p in frame);ymax=max(p.y/-p.z for p in frame)
 candidates=[]
 for ob in objects:
  corners=[ob.matrix_world@Vector(p) for p in ob.bound_box];low=np.min(corners,axis=0);high=np.max(corners,axis=0);nearest=np.clip(np.asarray(c.location),low,high)
  if np.linalg.norm(nearest-np.asarray(c.location))<40:candidates.append((ob,ob.matrix_world.inverted()))
 for px,py in pixels:
  direction=c.matrix_world.to_quaternion()@Vector((xmin+(xmax-xmin)*px/1280,ymax-(ymax-ymin)*py/840,-1)).normalized();hits=[]
  for ob,inv in candidates:
   hit,point,normal,index=ob.ray_cast(inv@c.location,inv.to_3x3()@direction)
   if not hit:continue
   world=ob.matrix_world@point;distance=(world-c.location).length
   if distance<35:
    poly=ob.data.polygons[index];vv=[list(ob.matrix_world@ob.data.vertices[i].co) for i in poly.vertices];hits.append({'object':ob.name,'node':ob.get('source_node'),'face':index,'point_local':list(world),'distance_m':distance,'triangle_local':vv})
  hits.sort(key=lambda x:x['distance_m']);rec.append({'camera':name,'pixel':[px,py],'hits':hits[:3]})
s.render.resolution_x,s.render.resolution_y=saved_res
(R/'evidence/G1_019r1/photo_residual_rays.json').write_text(json.dumps(rec,indent=2))
print(json.dumps([{'camera':x['camera'],'pixel':x['pixel'],'nearest':x['hits'][0] if x['hits'] else None} for x in rec]),flush=True)
