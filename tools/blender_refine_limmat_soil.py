"""Apply the prepared soil-only revision in the live G1_019r2 Blender scene."""
import hashlib
import json
from pathlib import Path
import shutil

import bpy
import numpy as np

ROOT = Path('F:/MyWorld/ZurichWorld')
DATA = ROOT / 'derived/bellevue/limmat_sidewalk'
ASSET = ROOT / 'sources/textures/polyhaven/forest_ground_05'
scene = bpy.context.scene
assert scene['version'] == 'G1_019r2'
destination = ROOT / 'native/G1_019r3_limmat_soil_working.blend'
assert not destination.exists(), 'Never overwrite a native checkpoint'
assert shutil.disk_usage(ROOT).free > 2_000_000_000, 'Insufficient reserve for native checkpoint'
report = json.loads((DATA / 'soil_relief_019r3.json').read_text(encoding='utf-8'))
arrays = np.load(DATA / 'soil_relief_019r3.npz')
obj = bpy.data.objects['LM_SOIL']
assert len(obj.data.vertices) == 8862 and len(obj.data.polygons) == 2954
assert obj.data.materials[0].name == 'HB | compacted granular tree soil'
old_mesh = obj.data
unchanged_meshes = {o.name: (o.data.name, len(o.data.vertices), len(o.data.polygons)) for o in scene.objects if o.type == 'MESH' and o != obj}
old_material_users = sorted(o.name for o in scene.objects if o.type == 'MESH' and any(m == old_mesh.materials[0] for m in o.data.materials))

material = bpy.data.materials.get('forest_ground_05')
if material is None:
    with bpy.data.libraries.load(str(ASSET / 'forest_ground_05_4k.blend'), link=False) as (source, target):
        assert 'forest_ground_05' in source.materials
        target.materials = ['forest_ground_05']
    material = target.materials[0]
assert material.users == 0, 'The imported scan must not change existing objects'
material.name = 'LM | scanned compact earth 2m'
material['source_url'] = 'https://polyhaven.com/a/forest_ground_05'
material['license'] = 'CC0'
material['physical_tile_m'] = 2.0
material['basis'] = report['basis']
nodes, links = material.node_tree.nodes, material.node_tree.links
output = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
# Geometry already contains bounded displacement. A second shader displacement
# would move the carefully fixed pit perimeter or double the surface relief.
for link in list(output.inputs['Displacement'].links):
    links.remove(link)
normal = next(n for n in nodes if n.type == 'NORMAL_MAP')
normal.inputs['Strength'].default_value = 0.75
normal.uv_map = 'scan_metres'
image_records = []
for node in nodes:
    if node.type != 'TEX_IMAGE' or node.image is None:
        continue
    image = node.image
    path = ASSET / 'textures' / Path(image.filepath.replace('\\', '/')).name
    assert path.is_file(), str(path)
    image.filepath = str(path)
    expected = 'sRGB' if '_diff_' in path.name else 'Non-Color'
    assert image.colorspace_settings.name == expected
    image.pack()
    image_records.append({'image': image.name, 'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'colorspace': image.colorspace_settings.name, 'size': list(image.size)})

mesh = bpy.data.meshes.new('LM_SOIL_relief_019r3')
vertices = arrays['vertices']
faces = arrays['faces']
mesh.from_pydata(vertices.tolist(), [], faces.tolist())
mesh.update()
mesh.materials.append(material)
uv_layer = mesh.uv_layers.new(name='scan_metres')
uv_layer.data.foreach_set('uv', arrays['uv'][faces].astype(np.float32).ravel())
for polygon in mesh.polygons:
    polygon.use_smooth = True
obj.data = mesh
obj['surface_revision'] = 'G1_019r3'
obj['surface_basis'] = report['basis']
bpy.context.view_layer.update()
try:
    assert unchanged_meshes == {o.name: (o.data.name, len(o.data.vertices), len(o.data.polygons)) for o in scene.objects if o.type == 'MESH' and o != obj}
    assert sorted(o.name for o in scene.objects if o.type == 'MESH' and any(m == old_mesh.materials[0] for m in o.data.materials)) == [n for n in old_material_users if n != 'LM_SOIL']
    scene['version'] = 'G1_019r3'
    exec(compile((ROOT / 'tools/blender_check_limmat_sidewalk.py').read_text(encoding='utf-8'), 'check_limmat_after_soil', 'exec'))
except Exception:
    obj.data = old_mesh
    scene['version'] = 'G1_019r2'
    raise
evidence = ROOT / 'evidence/G1_019r3'
evidence.mkdir(exist_ok=True)
scene.camera = bpy.data.objects['BE_QA_LIMMAT_SOPHORA_ROOT']
bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True)
assert Path(bpy.data.filepath).resolve() == destination.resolve()
record = {'version': scene['version'], 'native': str(destination), 'base_native': 'native/G1_019r2_limmat_clearance_working.blend', 'modified_object': obj.name, 'unchanged_other_meshes': len(unchanged_meshes), 'material_source': image_records, 'geometry': report, 'old_material_other_users_preserved': [n for n in old_material_users if n != 'LM_SOIL'], 'native_checkpoint_written': True, 'visual_acceptance': False, 'runtime_exported': False, 'natural_use_verified': False}
(evidence / 'construction.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
working_path = ROOT / 'runtime/station_road_working.json'
working = json.loads(working_path.read_text(encoding='utf-8'))
working.update(version=scene['version'], native=str(destination), accepted=False, not_published=True, next='Inspect same two root views and reverse approach. Soil scan/relief is a proxy. Runtime candidate remains018r3 and default007r5.')
working_path.write_text(json.dumps(working, indent=2), encoding='utf-8')
print(json.dumps({'version': scene['version'], 'native': str(destination), 'soil_vertices': len(mesh.vertices), 'soil_triangles': len(mesh.polygons), 'other_meshes_unchanged': len(unchanged_meshes), 'saved': True}))
