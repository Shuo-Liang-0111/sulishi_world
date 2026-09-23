import bpy,json,hashlib
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld')
scene=bpy.context.scene
col=bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE']
assert scene['photogrammetry_nodes_loaded']==scene['photogrammetry_nodes_expected']==len(col.objects)
assert str(scene['version']).startswith('G1_004')
VERSION=scene['version']
for o in scene.objects:o.select_set(o.name.startswith('I3S_'))
target=ROOT/f'web/assets/{VERSION}_photo.glb'
bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,
                         export_extras=True,export_yup=True,export_normals=False,
                         export_cameras=False,export_lights=False)
native=ROOT/f'native/{VERSION}_photogrammetry_reference.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(native))
status=json.loads((ROOT/'runtime/current_scene.json').read_text())
status.update(photo_glb=str(target),photo_glb_bytes=target.stat().st_size,
              photo_glb_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
              viewer_version=VERSION,viewer_note='Photo layer exported from this native; survey layer retained for comparison.')
(ROOT/'runtime/current_scene.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
manifest={'version':VERSION,'survey_version':'G1_003r2','survey_glb':'G1_003r2_survey.glb',
          'photo_glb':target.name,'photo_nodes':len(col.objects),'photogrammetry_ready':True,
          'quality':'unmodified_source_reference','accepted':False}
(ROOT/'web/assets/current.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'photo_glb':str(target),'bytes':target.stat().st_size,'nodes':len(col.objects)}))
