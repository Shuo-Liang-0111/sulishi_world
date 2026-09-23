"""Exact numeric mesh fingerprints for storage-only native changes."""
import hashlib
import json
import numpy as np


def mesh_digest(mesh):
    digest = hashlib.sha256()

    def field(label, collection, prop, width, dtype):
        digest.update(label.encode())
        data = np.empty(len(collection) * width, dtype=dtype)
        collection.foreach_get(prop, data)
        digest.update(data.tobytes())

    field('positions', mesh.vertices, 'co', 3, np.float32)
    field('edges', mesh.edges, 'vertices', 2, np.int32)
    field('corner_vertices', mesh.loops, 'vertex_index', 1, np.int32)
    field('corner_edges', mesh.loops, 'edge_index', 1, np.int32)
    for prop, dtype in [('loop_start', np.int32), ('loop_total', np.int32),
                        ('material_index', np.int32), ('use_smooth', np.bool_)]:
        field(prop, mesh.polygons, prop, 1, dtype)
    attributes = []
    for attr in mesh.attributes:
        meta = [attr.name, attr.domain, attr.data_type, len(attr.data)]
        attributes.append(meta)
        digest.update(json.dumps(meta).encode())
        if not attr.data:
            continue
        sample = attr.data[0]
        for prop in sample.bl_rna.properties:
            if prop.identifier == 'rna_type':
                continue
            if prop.type not in {'FLOAT', 'INT', 'BOOLEAN'}:
                raise AssertionError(('Unhandled mesh attribute', attr.name, prop.identifier, prop.type))
            dtype = {'FLOAT': np.float32, 'INT': np.int32, 'BOOLEAN': np.bool_}[prop.type]
            field(attr.name + ':' + prop.identifier, attr.data, prop.identifier,
                  max(1, prop.array_length), dtype)
    uv_meta = [(uv.name, uv.active_render, uv.active_clone) for uv in mesh.uv_layers]
    digest.update(json.dumps(uv_meta).encode())
    digest.update(str(mesh.uv_layers.active_index).encode())
    return {'sha256': digest.hexdigest(), 'vertices': len(mesh.vertices),
            'loops': len(mesh.loops), 'polygons': len(mesh.polygons),
            'attributes': attributes, 'uv_layers': uv_meta}


def object_state(obj):
    """Resolved material slots, transforms and visibility must survive sharing."""
    return {'name': obj.name, 'type': obj.type,
            'matrix_world': [float(v) for row in obj.matrix_world for v in row],
            'parent': obj.parent.name if obj.parent else None,
            'collections': sorted(c.name for c in obj.users_collection),
            'hide_render': obj.hide_render, 'hide_viewport': obj.hide_viewport,
            'materials': [slot.material.name if slot.material else None for slot in obj.material_slots]}
