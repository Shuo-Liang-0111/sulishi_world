import bpy,json
from mathutils import Vector
scene=bpy.context.scene;cam=bpy.data.objects['BE_QA_TRACK_NEAR'];deps=bpy.context.evaluated_depsgraph_get();frame=cam.data.view_frame(scene=scene)
# Blender view_frame order: top-right, bottom-right, bottom-left, top-left.
rows=[]
for px,py in [(1430,725),(1200,630),(1300,730),(500,940),(1000,460)]:
 u=px/1600;v=1-py/1050
 local=Vector((min(p.x for p in frame)+(max(p.x for p in frame)-min(p.x for p in frame))*u,min(p.y for p in frame)+(max(p.y for p in frame)-min(p.y for p in frame))*v,frame[0].z))
 origin=cam.matrix_world.translation; direction=(cam.matrix_world.to_quaternion()@local).normalized();hit,pos,normal,index,obj,matrix=scene.ray_cast(deps,origin,direction)
 rows.append({'pixel':[px,py],'hit':hit,'object':obj.name if obj else None,'pos':list(pos),'material':obj.data.materials[obj.data.polygons[index].material_index].name if obj and obj.type=='MESH' else None})
print(json.dumps(rows))
