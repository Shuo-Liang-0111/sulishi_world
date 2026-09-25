"""Identify remaining bridgehead floating photo fragments in saved 027r4 views."""
from pathlib import Path
import json,sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import write_path

s=bpy.context.scene;assert s['version']=='G1_027r4'
deps=bpy.context.evaluated_depsgraph_get();rows=[]
for name,pixels in {'BF_QA_FLAGS':[(348,590),(685,704),(883,658)],
                    'BD_QA_EAST':[(112,405),(399,363),(814,377)]}.items():
    camera=bpy.data.objects[name];frame=camera.data.view_frame(scene=s)
    x0,x1=min(p.x for p in frame),max(p.x for p in frame)
    y0,y1=min(p.y for p in frame),max(p.y for p in frame)
    for x,y in pixels:
        q=Vector((x0+(x+.5)/1280*(x1-x0),y1-(y+.5)/840*(y1-y0),frame[0].z))
        direction=(camera.matrix_world.to_3x3()@q).normalized();start=camera.matrix_world.translation.copy();hits=[]
        for _ in range(3):
            hit,p,n,face,ob,m=s.ray_cast(deps,start,direction,distance=180)
            if not hit:break
            hits.append(dict(object=ob.name,face=face,point=list(p),source_node=ob.get('source_node'),
                             source_id=ob.get('source_id'),collections=[c.name for c in ob.users_collection]))
            start=p+direction*.002
        rows.append(dict(camera=name,pixel=[x,y],hits=hits))
report=dict(version=s['version'],native=bpy.data.filepath,image_size=[1280,840],
    samples=rows,scene_modified=False,classification_complete=False,
    purpose='Localize visible suspended source fragments before reconstructing their actual street/structure counterparts; no deletion is authorized by a ray hit alone.')
write_path('evidence/G1_027r4/remaining_context_probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps([dict(camera=r['camera'],pixel=r['pixel'],first_hit=r['hits'][0] if r['hits'] else None) for r in rows]))
