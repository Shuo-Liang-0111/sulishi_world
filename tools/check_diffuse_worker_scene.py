"""Render the temporary bake geometry to detect changes caused by preparation."""
import bpy,json
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld')
script=(R/'tools/bake_service_diffuse.py').read_text()
exec(compile(script.split("print('DIFFUSE_BAKE_START'")[0],'temporary_bake_geometry','exec'))
s.camera=camera;s.cycles.samples=24;s.cycles.use_denoising=True
if hasattr(s.cycles,'denoising_use_gpu'):s.cycles.denoising_use_gpu=False
s.render.resolution_x=1280;s.render.resolution_y=840;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG'
s.render.filepath=str(R/'evidence/G1_015r3/diffuse_worker_scene.png')
bpy.context.view_layer.update()
report={'version':V,'temporary_receiver_faces':len(receiver.data.polygons),
        'source_native_saved':False,'view':str(s.view_settings.view_transform),
        'look':str(s.view_settings.look),'exposure':s.view_settings.exposure,
        'normal_range':{},'material_geometry_diagnostic':True}
record=next(r for r in source['receivers'] if r['name']=='SV_SOURCE_SOFFIT')
obj=bpy.data.objects['SV_SOURCE_SOFFIT']
report['original_soffit']={'matrix':list(sum((list(row) for row in obj.matrix_world),[])),
  'normals':sorted(set(round(p.normal.z,3) for p in obj.data.polygons)),
  'materials':[m.name for m in obj.data.materials],
  'visibility':{k:getattr(obj,k) for k in ['visible_camera','visible_diffuse','visible_glossy','visible_shadow']}}
(R/'evidence/G1_015r3/diffuse_worker_scene.json').write_text(json.dumps(report,indent=2))
assert 'FINISHED' in bpy.ops.render.render(write_still=True)
print('DIFFUSE_WORKER_SCENE_RENDERED',flush=True)
