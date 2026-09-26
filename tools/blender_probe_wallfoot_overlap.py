"""Diagnose actual r16 side pixels against separate component surfaces."""
from pathlib import Path
import hashlib,json,os,sys
import bpy,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path

s=bpy.context.scene;assert s['version']=='G1_027r16'
cp=json.loads(read_path('evidence/G1_027r16/checkpoint.json').read_text())
with Path(bpy.data.filepath).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==cp['native_sha256']
d=json.loads(read_path('derived/stadelhofen_joint/G1_027r16/construction.json').read_text())
A,U,N=[np.asarray(d['frame'][k]) for k in ['A','U','N']]
def Q(p):
    p=np.asarray(p);return [float((p[:2]-A)@U),float((p[:2]-A)@N),float(p[2])]
s.render.resolution_x=1400;s.render.resolution_y=960;s.render.resolution_percentage=100
cam=bpy.data.objects['SJ_QA_SIDE'];f=cam.data.view_frame(scene=s)
xmin,xmax=min(p.x for p in f),max(p.x for p in f)
ymin,ymax=min(p.y for p in f),max(p.y for p in f)
deps=bpy.context.evaluated_depsgraph_get();trees={}
for name in ['SF1_CHEEK_1_MASONRY','SF1_CHEEK_1_COPING','SF1_APRON_CONTINUOUS_SUBBASE',
             'SJ_RIGHT_PAVING_BED','SJ_RIGHT_PAVING_JOINTS','SJ_RIGHT_STONE_123','SJ_RIGHT_STONE_132',
             'SJ_RIGHT_PLINTH_CORE','SJ_RIGHT_PLINTH_COURSE_0','CTX_I3S_32639']:
    ob=bpy.data.objects[name];ev=ob.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles()
    vv=[ev.matrix_world@v.co for v in me.vertices];ff=[list(t.vertices) for t in me.loop_triangles]
    trees[name]=BVHTree.FromPolygons(vv,ff,all_triangles=True);ev.to_mesh_clear()
rows=[]
for label,x,y in [('dark_wall_patch',800,787),('pale_wall_triangle',650,823),('front_dark_sliver',278,885),
                  ('wall_above',767,731),('stone_strip',773,860),('right_wall_base',1014,788),
                  ('boundary_triangle',543,840),('rear_dark_patch',842,779)]:
    p=Vector((xmin+(x+.5)/1400*(xmax-xmin),ymax-(y+.5)/960*(ymax-ymin),f[0].z))
    direction=(cam.matrix_world.to_3x3()@p).normalized();hits=[]
    for name,tree in trees.items():
        hit,normal,face,dist=tree.ray_cast(cam.matrix_world.translation,direction,12)
        if hit is not None:hits.append({'object':name,'distance':dist,'triangle':face,'uvz':Q(hit),'normal':list(normal)})
    hits.sort(key=lambda h:h['distance']);rows.append({'label':label,'pixel':[x,y],'hits':hits})
out={'process_id':os.getpid(),'native_sha256':cp['native_sha256'],'camera':cam.name,'pixels':rows,'native_saved':False}
if globals().get('REQUIRE_CLEAR_WALL',False):
    checks=[]
    for row in rows:
        if row['label'] not in ['dark_wall_patch','pale_wall_triangle','front_dark_sliver','boundary_triangle','rear_dark_patch']:continue
        hits=row['hits'];assert hits[0]['object']=='SF1_CHEEK_1_MASONRY',(row['label'],hits[:2])
        base=next(h for h in hits if h['object']=='SF1_APRON_CONTINUOUS_SUBBASE')
        gap=base['distance']-hits[0]['distance'];assert gap>.006,(row['label'],gap)
        checks.append({'label':row['label'],'base_behind_masonry_m':gap})
    assert len(checks)==5
    out['actual_wall_clearance_verified']=checks
write_path('evidence/G1_027r16/wallfoot_overlap_probe.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('OVERLAP_PROBED',json.dumps([{'label':r['label'],'first':r['hits'][:2]} for r in rows]),flush=True)
