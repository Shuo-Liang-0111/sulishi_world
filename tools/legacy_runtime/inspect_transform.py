import bpy,json
src=next(iter(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects));ob=next(x for x in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects if x['source_node']==src['source_node'])
def props(x):return {'name':x.name,'location':list(x.location),'world':list(x.matrix_world.translation),'basis':list(x.matrix_basis.translation),'parent':x.parent.name if x.parent else None,'hide_viewport':x.hide_viewport}
print(json.dumps([props(src),props(ob)]))
