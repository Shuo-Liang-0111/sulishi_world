"""Make the freestanding information faces legible from both approaches."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_012';d=json.loads((R/'derived/bellevue/corner_fixtures/input.json').read_text());C=np.array(d['information'][0]['geometry']['coordinates'][0])-np.array(d['origin'][:2]);u=np.array(d['u']);v=np.array(d['v']);col=bpy.data.collections['19_BELLEVUE_CORNER_FIXTURES'];new=[]
def rotation(mid):
 c=Vector((*mid,0));return Matrix.Translation(c)@Matrix.Rotation(math.pi,4,'Z')@Matrix.Translation(-c)
for prefix,axis,mid in [('CF_INFO_MAIN_NOTICE',u,.35),('CF_INFO_RETURN_NOTICE',v,.36)]:
 ob=bpy.data.objects[prefix+'_PRINT']
 # Existing quad used local u toward the viewer's left on its outward face.
 for x in ob.data.uv_layers.active.data:x.uv.x=1-x.uv.x
 M=rotation(C+axis*mid)
 for ob in list(col.objects):
  if ob.name.startswith(prefix) and not ob.name.endswith('_BACK') and '_HINGE_' not in ob.name and not ob.name.endswith('_KEYHOLE'):
   dup=ob.copy();dup.data=ob.data.copy();dup.name=ob.name+'_REVERSE';col.objects.link(dup);dup.matrix_world=M@ob.matrix_world;new.append(dup.name)
for name,axis,front,mid in [('CF_INFO_NAME_TEXT',u,v,.35),('CF_INFO_MODE_TEXT',u,v,.35),('CF_INFO_RETURN_TITLE',v,-u,.36)]:
 ob=bpy.data.objects[name];local=np.array(ob.location[:2])-C;along=float(local@axis);depth=float(local@front)
 # Face the printed side outwards; then add the second physical enamel face.
 ob.location.x,ob.location.y=C+axis*(2*mid-along)+front*depth;ob.rotation_euler.z+=math.pi
 dup=ob.copy();dup.data=ob.data.copy();dup.name=name+'_REVERSE';col.objects.link(dup);dup.matrix_world=rotation(C+axis*mid)@ob.matrix_basis;new.append(dup.name)
bpy.data.objects['BE_QA_CORNER_FIXTURES'].data.lens=32
s['version']='G1_012r1';s.camera=bpy.data.objects['BE_QA_CORNER_FIXTURES'];bpy.context.view_layer.update();native=R/'native/G1_012r1_corner_fixtures_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=s['version'],native=str(native),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2));e=R/'evidence/G1_012r1';e.mkdir(exist_ok=True);(e/'face_refinement.json').write_text(json.dumps({'version':s['version'],'new_reverse_faces':new,'basis':'Normal approach render showed blank reverse. Correct local handedness of print and title, and use a physically double-sided frame. Exact fixture subtype remains inferred.','accepted':False},indent=2));print(json.dumps({'version':s['version'],'new_faces':len(new)}))
