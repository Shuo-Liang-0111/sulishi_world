"""Attribute visible021 photo remnants before deciding any further clipping."""
from pathlib import Path
import json
import numpy as np
import bpy
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version'].startswith('G1_021')
res=s.render.resolution_x,s.render.resolution_y;s.render.resolution_x=1280;s.render.resolution_y=840
trees=json.loads((R/'sources/features/bauminventar.geojson').read_text())['features']
authored={int(o['source_id'].split('.')[-1]) for name in ['31_LIMMAT_SIDEWALK_TREES','34_RIVIERA_TREES']
          if name in bpy.data.collections for o in bpy.data.collections[name].objects}
cases=globals().get('PROBE_PIXELS',{'RQ_QA_ALONG':[(930,175),(760,435),(1090,485),(1260,200)],'RQ_QA_REVERSE':[(400,350),(1000,400)],'RQ_QA_STAIR':[(700,330)]})
objects=list(bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects);records=[]
for name,pixels in cases.items():
 c=bpy.data.objects[name];frame=c.data.view_frame(scene=s)
 xmin=min(p.x/-p.z for p in frame);xmax=max(p.x/-p.z for p in frame);ymin=min(p.y/-p.z for p in frame);ymax=max(p.y/-p.z for p in frame)
 candidates=[]
 for ob in objects:
  corners=[ob.matrix_world@Vector(p) for p in ob.bound_box];low=np.min(corners,axis=0);high=np.max(corners,axis=0)
  if np.linalg.norm(np.clip(np.asarray(c.location),low,high)-np.asarray(c.location))<45:candidates.append((ob,ob.matrix_world.inverted()))
 for px,py in pixels:
  direction=c.matrix_world.to_quaternion()@Vector((xmin+(xmax-xmin)*px/1280,ymax-(ymax-ymin)*py/840,-1)).normalized();hits=[]
  for ob,inv in candidates:
   hit,point,normal,index=ob.ray_cast(inv@c.location,inv.to_3x3()@direction)
   if not hit:continue
   world=ob.matrix_world@point;distance=(world-c.location).length
   if distance>45:continue
   xy=np.asarray(world)[:2]+[2683775,1246700]
   near=sorted([(float(np.linalg.norm(np.array(t['geometry']['coordinates'])-xy)),t) for t in trees],key=lambda a:a[0])[:3]
   hits.append({'node':ob.get('source_node'),'face':index,'point_local':list(world),'distance_m':distance,
     'nearest_inventory_trees':[{'id':t['properties']['objectid'],'distance_m':d,'authored':t['properties']['objectid'] in authored} for d,t in near]})
  hits.sort(key=lambda h:h['distance_m']);records.append({'camera':name,'pixel':[px,py],'hits':hits[:2]})
s.render.resolution_x,s.render.resolution_y=res
(R/'evidence'/s['version']/'photo_residual_rays.json').write_text(json.dumps(records,indent=2))
print(json.dumps([{'camera':r['camera'],'pixel':r['pixel'],'hit':r['hits'][0] if r['hits'] else None} for r in records]),flush=True)
