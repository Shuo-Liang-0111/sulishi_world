"""Read missing procedural-coordinate semantics from the current native file.

The first graph snapshot intentionally remains immutable. Noise family and
coordinate-object references are required before translating procedural nodes.
"""
from pathlib import Path
import hashlib
import json
import os
import sys
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import read_path, write_path, validate_native


def value(v):
    if v is None or isinstance(v, (str, bool, int, float)):
        return v
    if isinstance(v, bpy.types.ID):
        return {'id_type': type(v).__name__, 'name': v.name_full}
    return [value(x) for x in v]


native = validate_native(bpy.data.filepath)
version = bpy.context.scene['version']
assert version == 'G1_027r15'
with native.open('rb') as f:
    digest = hashlib.file_digest(f, 'sha256').hexdigest()
original_path = read_path(f'evidence/{version}/runtime_material_graphs.json')
graph = json.loads(original_path.read_text())
assert graph['native_sha256'] == digest
target = write_path(f'evidence/{version}/runtime_material_semantics.json')
assert not target.exists(), 'Keep earlier native semantics evidence'
rows = []
for material in graph['materials']:
    actual = bpy.data.materials[material['name']]
    nodes = []
    for archived in material['nodes']:
        node = actual.node_tree.nodes[archived['name']]
        assert node.type == archived['type']
        if node.type not in {'TEX_COORD', 'TEX_NOISE', 'MAP_RANGE', 'BUMP'}:
            continue
        fields = {'name': node.name, 'type': node.type}
        for prop in ['noise_type', 'noise_dimensions', 'normalize', 'object', 'from_instancer', 'interpolation_type', 'invert']:
            if hasattr(node, prop):
                fields[prop] = value(getattr(node, prop))
        if hasattr(node, 'texture_mapping'):
            mapping = node.texture_mapping
            fields['texture_mapping'] = {key: value(getattr(mapping, key)) for key in
                ['vector_type', 'translation', 'rotation', 'scale', 'mapping_x', 'mapping_y', 'mapping_z', 'use_min', 'use_max', 'min', 'max'] if hasattr(mapping, key)}
        nodes.append(fields)
    if nodes:
        rows.append({'material': material['name'], 'nodes': nodes})
result = {'version': version, 'native_sha256': digest, 'graph_sha256': hashlib.sha256(original_path.read_bytes()).hexdigest(),
          'process_id': os.getpid(), 'blender': bpy.app.version_string, 'materials': rows,
          'native_modified': False, 'procedural_materials_converted': False}
inventory = json.loads(read_path(f'evidence/{version}/runtime_inventory.json').read_text())
depsgraph = bpy.context.evaluated_depsgraph_get()
anchors = {'version': version, 'native_sha256': digest, 'process_id': os.getpid(), 'cameras': [], 'lights': []}
for kind in ['cameras', 'lights']:
    for item in inventory[kind]:
        original = bpy.data.objects[item['name']]
        evaluated = original.evaluated_get(depsgraph)
        anchors[kind].append({'name': original.name, 'matrix_world': [list(row) for row in evaluated.matrix_world],
            'parent': original.parent.name if original.parent else None,
            'constraints': [{'name': c.name, 'type': c.type, 'mute': c.mute} for c in original.constraints],
            'world_matches_archived_basis': all(abs(evaluated.matrix_world[i][j]-item['matrix_basis'][i][j]) < 1e-7 for i in range(4) for j in range(4))})
anchor_file = write_path(f'web/assets/{version}_runtime_anchors.json')
assert not anchor_file.exists(), 'Keep prior camera/light world-matrix evidence'
anchor_file.write_text(json.dumps(anchors, indent=2), encoding='utf-8')
result['runtime_anchors'] = {'path': str(anchor_file), 'sha256': hashlib.sha256(anchor_file.read_bytes()).hexdigest(),
    'world_differs_from_old_basis': [x['name'] for kind in ['cameras', 'lights'] for x in anchors[kind] if not x['world_matches_archived_basis']]}
target.write_text(json.dumps(result, indent=2), encoding='utf-8')
print('NATIVE_PROCEDURAL_SEMANTICS_READ', len(rows), flush=True)
