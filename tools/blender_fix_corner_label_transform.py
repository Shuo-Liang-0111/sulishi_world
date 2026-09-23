"""Use fresh local basis for unparented labels after changing their transform."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_012r1';d=json.loads((R/'derived/bellevue/corner_fixtures/input.json').read_text());C=np.array(d['information'][0]['geometry']['coordinates'][0])-np.array(d['origin'][:2]);u=np.array(d['u']);v=np.array(d['v']);normals=[]
for name,axis,mid in [('CF_INFO_NAME_TEXT',u,.35),('CF_INFO_MODE_TEXT',u,.35),('CF_INFO_RETURN_TITLE',v,.36)]:
 center=Vector((*list(C+axis*mid),0));M=Matrix.Translation(center)@Matrix.Rotation(math.pi,4,'Z')@Matrix.Translation(-center);a=bpy.data.objects[name];b=bpy.data.objects[name+'_REVERSE'];assert a.parent is None;b.matrix_world=M@a.matrix_basis
bpy.context.view_layer.update()
for name in ['CF_INFO_NAME_TEXT','CF_INFO_MODE_TEXT','CF_INFO_RETURN_TITLE']:
 a=bpy.data.objects[name];b=bpy.data.objects[name+'_REVERSE'];na=a.matrix_world.to_quaternion()@Vector((0,0,1));nb=b.matrix_world.to_quaternion()@Vector((0,0,1));assert na.dot(nb)<-.999;normals.append({'name':name,'normal_dot':na.dot(nb)})
s['version']='G1_012r2';native=R/'native/G1_012r2_corner_fixtures_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native));rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=s['version'],native=str(native),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2));e=R/'evidence/G1_012r2';e.mkdir(exist_ok=True);(e/'label_basis_fix.json').write_text(json.dumps({'version':s['version'],'normal_checks':normals,'reason':'matrix_world was not reevaluated between source-label edit and mirrored duplication. Persisted matrix_basis is current for unparented objects.','accepted':False},indent=2));print(json.dumps({'version':s['version'],'label_pairs':len(normals)}))
