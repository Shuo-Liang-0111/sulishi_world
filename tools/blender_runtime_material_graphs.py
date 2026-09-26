"""Read the exact material graphs for every accepted authored scene root.

This is a read-only inventory, not a material conversion or equivalence claim.
Run after blender_runtime_inventory.py in the same current-native process.
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
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, bpy.types.ID):
        return {'id_type':type(v).__name__, 'name':v.name_full}
    return [value(x) for x in v]


def socket_record(socket, index):
    row = {'index':index, 'name':socket.name, 'identifier':socket.identifier,
           'type':socket.type, 'linked':socket.is_linked, 'enabled':socket.enabled}
    if hasattr(socket, 'default_value'):
        row['default'] = value(socket.default_value)
    return row


native = validate_native(bpy.data.filepath)
version = bpy.context.scene['version']
before = native.stat()
with native.open('rb') as stream:
    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
inventory = json.loads(read_path(f'evidence/{version}/runtime_inventory.json').read_text())
assert inventory['native_sha256'] == digest
assert 'SF1_AUTHOR_ENTRANCE' in inventory['authored_roots'], 'Use the corrected complete root inventory.'
target = write_path(f'evidence/{version}/runtime_material_graphs.json')
assert not target.exists(), 'Preserve the previous graph snapshot.'
materials = {}
for name in inventory['visible_authored_object_names']:
    for slot in bpy.data.objects[name].material_slots:
        if slot.material:
            materials.setdefault(slot.material.name, set()).add(name)
assert set(materials) == {m['name'] for m in inventory['materials']}
rows = []
for name, users in sorted(materials.items()):
    material = bpy.data.materials[name]
    row = {'name':name, 'used_by':sorted(users), 'use_nodes':material.use_nodes,
           'diffuse_color':list(material.diffuse_color), 'nodes':[], 'links':[]}
    for prop in ['surface_render_method','use_backface_culling','displacement_method','max_vertex_displacement']:
        if hasattr(material, prop):
            row[prop] = value(getattr(material, prop))
    if material.use_nodes:
        tree = material.node_tree
        for node in tree.nodes:
            n = {'name':node.name, 'class':node.bl_idname, 'type':node.type, 'mute':node.mute,
                 'inputs':[socket_record(s,i) for i,s in enumerate(node.inputs)],
                 'outputs':[socket_record(s,i) for i,s in enumerate(node.outputs)]}
            for prop in ['operation','blend_type','data_type','vector_type','interpolation','projection',
                         'projection_blend','extension','space','uv_map','attribute_name','attribute_type',
                         'layer_name','noise_dimensions','normalize','wave_type','bands_direction',
                         'rings_direction','wave_profile','invert','clamp','use_clamp','is_active_output']:
                if hasattr(node, prop):
                    n[prop] = value(getattr(node, prop))
            if hasattr(node, 'image') and node.image:
                image = node.image
                n['image'] = {'name':image.name, 'file':bpy.path.abspath(image.filepath,library=image.library),
                              'colorspace':image.colorspace_settings.name, 'size':list(image.size),
                              'source':image.source, 'alpha_mode':image.alpha_mode}
            if hasattr(node, 'color_ramp'):
                ramp = node.color_ramp
                n['color_ramp'] = {'mode':ramp.color_mode, 'hue_interpolation':ramp.hue_interpolation,
                                   'interpolation':ramp.interpolation,
                                   'elements':[{'position':e.position,'color':list(e.color)} for e in ramp.elements]}
            if hasattr(node, 'node_tree') and node.node_tree:
                n['group'] = node.node_tree.name
            if hasattr(node, 'object') and node.object:
                n['coordinate_object'] = node.object.name
            row['nodes'].append(n)
        row['links'] = [{'from_node':link.from_node.name,
                         'from_socket_index':list(link.from_node.outputs).index(link.from_socket),
                         'to_node':link.to_node.name,
                         'to_socket_index':list(link.to_node.inputs).index(link.to_socket)} for link in tree.links]
    rows.append(row)
assert native.stat().st_size == before.st_size and native.stat().st_mtime_ns == before.st_mtime_ns
report = {'version':version, 'native_sha256':digest, 'process_id':os.getpid(),
          'authored_roots':inventory['authored_roots'], 'materials':rows,
          'native_unmodified':True, 'runtime_materials_converted':False,
          'limit':'Node graph and parameters only. Group internals, geometry-dependent inputs, baking and visual agreement need separate handling.'}
target.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('MATERIAL_GRAPH_SNAPSHOT',json.dumps({'materials':len(rows),'path':str(target)}),flush=True)
