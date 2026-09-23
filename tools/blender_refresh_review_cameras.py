import bpy,json
from pathlib import Path
from mathutils import Vector
ROOT=Path('F:/MyWorld/ZurichWorld');V=bpy.context.scene['version'];path=ROOT/f'web/assets/{V}_bellevue.json'
metadata=json.loads(path.read_text());changes=[]
def yup(p):return [p.x,p.z,-p.y]
for ob in bpy.data.collections['90_REVIEW_CAMERAS'].objects:
    if not ob.name.startswith('BE_QA_'):continue
    assert ob.parent is None and not ob.constraints
    forward=ob.matrix_basis.to_quaternion()@Vector((0,0,-1))
    new={'position':yup(ob.location),'target':yup(ob.location+forward*8),'fov':ob.data.angle_y*180/3.141592653589793}
    changes.append({'camera':ob.name,'before':metadata['cameras'][ob.name],'after':new})
    metadata['cameras'][ob.name]=new
path.write_text(json.dumps(metadata,indent=2));(ROOT/f'evidence/{V}/camera_reopen_fix.json').write_text(json.dumps(changes,indent=2));print(json.dumps(changes))
