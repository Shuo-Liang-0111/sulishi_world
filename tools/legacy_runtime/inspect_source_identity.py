import bpy,json
from pathlib import Path
p=Path('F:/MyWorld/ZurichWorld')
cut={str(x['node']) for x in json.loads((p/'derived/bellevue/photo_cut.json').read_text())['overrides']}
src={str(x['source_node']):x for x in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
out=[]
for ob in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects:
 if str(ob['source_node']) in cut:continue
 old=src[str(ob['source_node'])]
 err=max(abs(ob.matrix_world[r][c]-old.matrix_world[r][c]) for r in range(4) for c in range(4))
 if ob.data is not old.data or err:out.append({'name':ob.name,'same_data':ob.data is old.data,'matrix_error':err,'old_scale':list(old.scale),'new_scale':list(ob.scale)})
print(json.dumps({'count':len(out),'items':out[:20]}))
