"""Trace actual023 rejected-view pixels; keep source identity over guesses."""
from pathlib import Path
import json
import numpy as np
import bpy
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version'].startswith('G1_023')
oldres=(s.render.resolution_x,s.render.resolution_y)
s.render.resolution_x=1280;s.render.resolution_y=840
cases=globals().get('PROBE_CASES',{'QB_QA_NORTH':[(640,420),(320,300),(950,510)],
       'QB_QA_INTERIOR':[(785,435),(1060,420)],
       'QB_QA_BEAMS':[(210,372),(1130,387),(618,342)],
       'QB_QA_SOUTH':[(700,280),(950,260),(272,445)],
       'QB_QA_STAIR':[(870,287),(224,138)]})
visible=set()
def collect(col,parent_hidden=False):
    hidden=parent_hidden or col.hide_render
    if not hidden:visible.update(o for o in col.objects if o.type=='MESH' and not o.hide_render)
    for child in col.children:collect(child,hidden)
collect(s.collection)
objects=list(visible)
rows=[]
for name,pixels in cases.items():
    cam=bpy.data.objects[name];frame=cam.data.view_frame(scene=s)
    xmin=min(p.x/-p.z for p in frame);xmax=max(p.x/-p.z for p in frame)
    ymin=min(p.y/-p.z for p in frame);ymax=max(p.y/-p.z for p in frame)
    candidates=[]
    for ob in objects:
        corners=np.array([ob.matrix_world@Vector(p) for p in ob.bound_box]);lo=corners.min(0);hi=corners.max(0)
        if np.linalg.norm(np.clip(np.array(cam.location),lo,hi)-np.array(cam.location))<100:
            candidates.append((ob,ob.matrix_world.inverted()))
    for x,y in pixels:
        direction=cam.matrix_world.to_quaternion()@Vector((xmin+(xmax-xmin)*x/1280,ymax-(ymax-ymin)*y/840,-1)).normalized()
        hits=[]
        for ob,inv in candidates:
            hit,p,normal,index=ob.ray_cast(inv@cam.location,inv.to_3x3()@direction)
            if hit:
                q=ob.matrix_world@p;distance=(q-cam.location).length
                if distance<100:hits.append(dict(name=ob.name,node=ob.get('source_node'),face=index,
                        point_lv95=(np.array(q)+[2683775,1246700,400]).tolist(),distance_m=distance))
        hits.sort(key=lambda h:h['distance_m']);rows.append(dict(camera=name,pixel=[x,y],hits=hits[:3]))
s.render.resolution_x,s.render.resolution_y=oldres
world=s.world
lighting={'world':world.name if world else None,'nodes':[],'lights':[]}
if world and world.use_nodes:
    for node in world.node_tree.nodes:
        rec={'type':node.type}
        if node.type=='BACKGROUND':rec.update(strength=node.inputs['Strength'].default_value,color=list(node.inputs['Color'].default_value))
        if node.type=='TEX_ENVIRONMENT':rec['image']=node.image.name if node.image else None
        lighting['nodes'].append(rec)
lighting['lights']=[dict(name=o.name,type=o.data.type,energy=o.data.energy) for o in s.objects if o.type=='LIGHT']
record={'version':s['version'],'pixels':rows,'lighting':lighting,'native_saved':False}
(R/'evidence'/s['version']/globals().get('PROBE_OUTPUT','obstruction_diagnosis.json')).write_text(json.dumps(record,indent=2))
print(json.dumps({'hits':[dict(camera=r['camera'],pixel=r['pixel'],first=r['hits'][0] if r['hits'] else None) for r in rows], 'lighting':lighting}),flush=True)
