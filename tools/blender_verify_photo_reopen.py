import bpy, json
from pathlib import Path

ROOT = Path('F:/MyWorld/ZurichWorld')
pointer = json.loads((ROOT/'runtime/current_scene.json').read_text(encoding='utf-8'))
native = Path(pointer['native']).resolve()
assert native.is_relative_to((ROOT/'native').resolve()) and native.exists()
bpy.ops.wm.open_mainfile(filepath=str(native))
scene = bpy.context.scene
photo = bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE']
meshes = [o for o in photo.objects if o.type == 'MESH']
missing = [im.filepath for im in bpy.data.images if im.source == 'FILE'
           and im.filepath and not im.packed_file and not Path(bpy.path.abspath(im.filepath)).exists()]
triangles = 0
for o in meshes:
    o.data.calc_loop_triangles()
    triangles += len(o.data.loop_triangles)
assert len(meshes) == pointer['expected_nodes'] == 2039
assert triangles == 2081616
assert scene['version'] == pointer['version']
assert not missing, missing[:5]
result = {'native':str(native), 'version':scene['version'], 'reopened':True,
          'photo_meshes':len(meshes), 'triangles':triangles, 'missing_images':missing,
          'meaning':'Persistent editable source reference; not close-range or interaction acceptance.'}
(ROOT/'evidence'/scene['version']/'native_reopen.json').write_text(
    json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result))
