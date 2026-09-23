"""Apply the observed bark-transition repair to existing source-located planes.

Keep all geometry, roots, inventory heights and adjacent structures. Shared
branches/leaves stay linked; wood meshes and materials remain locally editable.
"""
from pathlib import Path
import hashlib
import json
import shutil
import bpy
import numpy as np

root = Path('F:/MyWorld/ZurichWorld')
scene = bpy.context.scene
assert scene['version'] == 'G1_020r3'
assert (root/'evidence/G1_020r3/shared_geometry_reopen.json').is_file()
assert (root/'evidence/G1_020r3/visual_storage_review.json').is_file()
target = root/'native/G1_020r4_tree_bark_working.blend'
assert not target.exists()
assert shutil.disk_usage(root).free > 500_000_000
old = bpy.data.materials['HB | continuous plane trunk atlas']
material = old.copy()
material.name = 'ZW | plane trunk exfoliation patches'
material['basis'] = 'CC0 coarse Platanus bark and original inferred upper bark. Broader patch coverage repairs the observed repeated height cuff; no individual tree scan.'
material['nominal_atlas_size_m'] = [2.5, 4.5]
folder = root/'derived/materials/plane_trunk_patch'
receipt = json.loads((folder/'receipt.json').read_text())
role_by_source = {'albedo.png': 'albedo', 'roughness.png': 'roughness', 'normal_gl.png': 'normal_gl'}
replaced = []
texture_nodes = [node for node in material.node_tree.nodes if node.type == 'TEX_IMAGE' and node.image]
for node in texture_nodes:
    filename = Path(bpy.path.abspath(node.image.filepath, library=node.image.library)).name
    if filename == 'bark_platanus_Displacement_4k.png':
        # Inspected in020r3: this legacy branch has no material-output link.
        # Remove it only from the new copied material, not the old reference.
        downstream = {link.to_node for output in node.outputs for link in output.links}
        assert downstream and all(n.type == 'DISPLACEMENT' and
            not any(output.links for output in n.outputs) for n in downstream)
        for unused in downstream:
            material.node_tree.nodes.remove(unused)
        material.node_tree.nodes.remove(node)
        continue
    assert filename in role_by_source, filename
    role = role_by_source[filename]
    path = folder/f'{role}.png'
    expected = next(r['sha256'] for r in receipt['files'] if r['file'] == path.name)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    image = bpy.data.images.load(str(path), check_existing=True)
    image.colorspace_settings.name = node.image.colorspace_settings.name
    node.image = image
    node.interpolation = 'Linear'
    replaced.append(role)
assert sorted(replaced) == ['albedo', 'normal_gl', 'roughness']
objects_before = set(scene.objects)
reports = []
for obj in scene.objects:
    if obj.type != 'MESH' or not obj.name.endswith('_WOOD'):
        continue
    slots = [i for i, slot in enumerate(obj.material_slots) if slot.material == old]
    if not slots:
        continue
    mesh = obj.data
    assert mesh.library is None, 'Only already local trunks may be edited here'
    verts = np.empty(len(mesh.vertices)*3, np.float32)
    mesh.vertices.foreach_get('co', verts)
    vertex_sha = hashlib.sha256(verts.tobytes()).hexdigest()
    layer = mesh.uv_layers.active
    indices = [li for face in mesh.polygons if face.material_index in slots for li in face.loop_indices]
    assert indices
    uv = np.asarray([layer.data[li].uv[:] for li in indices], dtype=np.float32)
    assert uv[:, 1].min() >= 0 and uv[:, 1].max() < 1, obj.name
    seed = int(hashlib.sha256(obj.name.encode()).hexdigest()[:8], 16)
    span = float(uv[:, 0].max()-uv[:, 0].min())
    # V stays in physical metres and the trunk base stays on coarse bark.
    # A bounded circumferential phase avoids creating a new U wrap seam.
    available = max(0.0, .999-span)
    phase = ((seed % 10007)/10007)*available - float(uv[:, 0].min())
    for li in indices:
        layer.data[li].uv.x += phase
    for index in slots:
        obj.material_slots[index].material = material
    mesh.vertices.foreach_get('co', verts)
    assert hashlib.sha256(verts.tobytes()).hexdigest() == vertex_sha
    reports.append({'object': obj.name, 'source_id': obj.get('source_id'),
                    'unchanged_vertex_sha256': vertex_sha,
                    'changed_trunk_uv_loops': len(indices), 'u_phase': phase,
                    'physical_height_uv_unchanged': True})
assert len(reports) == 21, len(reports)
assert set(scene.objects) == objects_before
scene['version'] = 'G1_020r4'
scene['tree_bark_revision'] = '21 existing Platanus trunks; same surveyed positions and inventory heights'
bpy.context.view_layer.update()
evidence = root/'evidence/G1_020r4'
evidence.mkdir(exist_ok=True)
record = {'version': scene['version'], 'base': 'G1_020r3', 'trees': reports,
          'source_material_receipt': str((folder/'receipt.json').relative_to(root)),
          'same_geometry_and_positions': True, 'lights_cameras_unchanged': True,
          'native_saved': False, 'visual_acceptance': False, 'natural_use_verified': False}
(evidence/'bark_revision.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('TRUNK_PATCH_APPLIED', json.dumps({'trees': len(reports), 'version': scene['version']}))
