"""Read-only scene ray diagnosis of the actual r16 close-up residuals."""
from pathlib import Path
import hashlib,json,os,sys
import bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path

s=bpy.context.scene;assert s['version']=='G1_027r16'
cp=json.loads(read_path('evidence/G1_027r16/checkpoint.json').read_text())
with Path(bpy.data.filepath).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==cp['native_sha256']
d=json.loads(read_path('derived/stadelhofen_joint/G1_027r16/construction.json').read_text())
A,U,N=[np.asarray(d['frame'][k]) for k in ['A','U','N']]
def Q(p):
    p=np.asarray(p);return [float((p[:2]-A)@U),float((p[:2]-A)@N),float(p[2])]
def P(u,v,z):return Vector((*list(A+U*u+N*v),z))
s.render.resolution_x=1400;s.render.resolution_y=960;s.render.resolution_percentage=100
cam=bpy.data.objects['SJ_QA_WALLFOOT'];frame=cam.data.view_frame(scene=s)
xmin,xmax=min(v.x for v in frame),max(v.x for v in frame)
ymin,ymax=min(v.y for v in frame),max(v.y for v in frame)
render_visible=set()
def collect(c,hidden=False):
    hidden=hidden or c.hide_render
    if not hidden:
        render_visible.update(o.name for o in c.objects if not o.hide_render and o.visible_camera)
    for child in c.children:collect(child,hidden)
collect(s.collection)
# The source/archive collection is not in the rendered view. Exclude it from
# the read-only scene-ray query too; do not diagnose invisible reference hits.
excluded=[]
for ob in s.objects:
    if ob.name not in render_visible:
        ob.hide_set(True);excluded.append(ob.name)
bpy.context.view_layer.update()
deps=bpy.context.evaluated_depsgraph_get()


def hits(origin,direction,maxdist):
    result=[];distance=0.
    for _ in range(8):
        hit,p,n,index,ob,matrix=s.ray_cast(deps,origin+direction*distance,direction,distance=maxdist-distance)
        if not hit:break
        record={'object':ob.name,'face':index,'xyz':list(p),'uvz':Q(p),'normal':list(n),
                'materials':[slot.material.name if slot.material else None for slot in ob.material_slots]}
        if ob.type=='MESH':
            ev=ob.evaluated_get(deps);me=ev.to_mesh()
            if index>=0 and index<len(me.polygons):
                polygon=me.polygons[index]
                record['polygon_uvz']=[Q(matrix@me.vertices[i].co) for i in polygon.vertices]
            ev.to_mesh_clear()
        result.append(record)
        distance=(p-origin).length+.0005
        if distance>=maxdist:break
    return result


pixels=[]
sun=next(o for o in s.objects if o.type=='LIGHT' and o.data.type=='SUN')
to_sun=(sun.matrix_world.to_quaternion()@Vector((0,0,1))).normalized()
for label,x,y in [('rear_dark_triangle',797,523),('rear_raised_edge',897,424),
                   ('middle_dark_edge',803,561),('middle_cheek_triangle',667,645),
                   ('front_cheek_triangle',558,806),('front_isolated_sliver',619,809),
                   ('new_stone_centre',734,655),('exterior_scan_ridge',1184,448)]:
    local=Vector((xmin+(x+.5)/1400*(xmax-xmin),ymax-(y+.5)/960*(ymax-ymin),frame[0].z))
    direction=(cam.matrix_world.to_3x3()@local).normalized()
    found=hits(cam.matrix_world.translation,direction,12)
    shadow=hits(Vector(found[0]['xyz'])+Vector(found[0]['normal'])*.002,to_sun,30) if found else []
    pixels.append({'label':label,'pixel':[x,y],'hits':found,'toward_sun_hits':shadow})
vertical=[]
for u,v in [(13.20,-.60),(13.20,-.40),(13.20,-.10),(13.20,.3),
            (13.28,-.5),(13.40,-.5),(13.50,-.4),(13.30,.2)]:
    vertical.append({'uv':[u,v],'hits':hits(P(u,v,12),Vector((0,0,-1)),2.)})
report={'native_sha256':cp['native_sha256'],'process_id':os.getpid(),'camera':'SJ_QA_WALLFOOT',
        'pixels':pixels,'vertical_probes':vertical,'render_invisible_objects_excluded':excluded,
        'native_saved':False,'visual_acceptance':False}
write_path('evidence/G1_027r16/wallfoot_residual_probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('WALLFOOT_RESIDUAL_PROBED',json.dumps([{'label':r['label'],'first':r['hits'][0]['object'] if r['hits'] else None} for r in pixels]),flush=True)
