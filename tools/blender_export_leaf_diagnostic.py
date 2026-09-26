"""Export one native tree twice for an actual Three.js representation comparison.

The instance representation retains each native leaf normal in a float texture.
It does not approximate normals using the affine position transform (which was
measured to introduce up to 13.6 degrees of error). Native materials, scene and
the public runtime pointer are untouched. This is an isolated geometry probe.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import read_path, write_path, validate_native
from blender_geometry_fingerprint import mesh_digest


def oct_encode(normals):
    p = normals / np.abs(normals).sum(axis=-1, keepdims=True)
    result = p[:, :2].copy()
    lower = p[:, 2] < 0
    result[lower] = (1-np.abs(result[lower, ::-1])) * np.where(result[lower] >= 0, 1, -1)
    return result.astype(np.float32)


def oct_decode(p):
    n = np.c_[p.astype(np.float64), 1-np.abs(p.astype(np.float64)).sum(axis=-1)]
    t = np.maximum(-n[:, 2], 0)
    n[:, :2] += np.where(n[:, :2] >= 0, -t[:, None], t[:, None])
    return n/np.linalg.norm(n, axis=-1, keepdims=True)


s = bpy.context.scene
version = s['version']
assert version == 'G1_027r15'
native = validate_native(bpy.data.filepath)
stat = native.stat()
with native.open('rb') as stream:
    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
cp = json.loads(read_path(f'evidence/{version}/checkpoint.json').read_text())
assert digest == cp['native_sha256']
ob = bpy.data.objects['BE_TREE_69773_LEAVES']
bpy.context.view_layer.update()
assert ob.parent is None and not ob.constraints and ob.matrix_world == ob.matrix_basis
assert not ob.modifiers and not ob.data.shape_keys and not ob.data.has_custom_normals
me = ob.data
assert all(p.use_smooth and len(p.vertices) == 3 for p in me.polygons)
faces = np.empty(len(me.loops), dtype=np.int32)
me.loops.foreach_get('vertex_index', faces)
faces = faces.reshape(-1, 3)
fcount = int(np.flatnonzero(faces[:, 0] != faces[0, 0])[0])
vcount = int(faces[fcount].min())
count = len(me.vertices)//vcount
pattern = faces[:fcount]
assert np.array_equal(faces.reshape(count, fcount, 3), pattern+np.arange(count)[:, None, None]*vcount)
positions = np.empty(len(me.vertices)*3, dtype=np.float32)
me.vertices.foreach_get('co', positions)
leaves = positions.reshape(count, vcount, 3).astype(np.float64)
centers = leaves.mean(1)
local = leaves-centers[:, None, :]
reference = local[0]
transforms = np.einsum('iv,nvj->nij', np.linalg.pinv(reference), local)
determinants = np.linalg.det(transforms)
assert np.all(determinants > 1e-9), 'Reflections or singular leaf transforms require separate winding handling.'
matrices = np.tile(np.eye(4), (count, 1, 1))
matrices[:, :3, :3] = transforms.transpose(0, 2, 1)
matrices[:, :3, 3] = centers
matrices = matrices.astype(np.float32)
template = reference.astype(np.float32)
runtime_positions = np.einsum('vj,nij->nvi', template, matrices[:, :3, :3])+matrices[:, None, :3, 3]
position_error = np.linalg.norm(runtime_positions.astype(np.float64)-leaves, axis=-1)
assert position_error.max() < .0001

normals = np.empty(len(me.vertices)*3, dtype=np.float32)
me.vertices.foreach_get('normal', normals)
normals = normals.reshape(-1, 3)
assert np.all(np.linalg.norm(normals, axis=-1) > .99)
corners = np.empty(len(me.corner_normals)*3, dtype=np.float32)
me.corner_normals.foreach_get('vector', corners)
assert np.max(np.abs(corners.reshape(-1, 3)-normals[faces.ravel()])) < 1e-6
encoded = oct_encode(normals)
decoded = oct_decode(encoded)
normal_reference = normals.astype(np.float64)
normal_reference /= np.linalg.norm(normal_reference, axis=-1, keepdims=True)
angles = np.degrees(np.arccos(np.clip((decoded*normal_reference).sum(-1), -1, 1)))
assert angles.max() < .0001
width = 1024
height = math.ceil(len(normals)/width)
normal_texture = np.zeros((height*width, 2), dtype=np.float32)
normal_texture[:len(normals)] = encoded

uv = np.empty(len(me.loops)*2, dtype=np.float32)
me.uv_layers.active.data.foreach_get('uv', uv)
uv = uv.reshape(count, fcount*3, 2)
assert np.array_equal(uv, np.broadcast_to(uv[:1], uv.shape))
colors = me.color_attributes['LeafColor']
assert colors.domain == 'POINT' and colors.data_type == 'FLOAT_COLOR'
color_data = np.empty(len(colors.data)*4, dtype=np.float32)
colors.data.foreach_get('color', color_data)
color_data = color_data.reshape(count, vcount, 4)
assert np.all(color_data[:, :, 3] == 1)
template_color = (color_data[0, :, :3]/color_data[0, 0, :3]).astype(np.float32)
instance_color = color_data[:, 0, :3].copy()
color_error = float(np.max(abs(template_color[None]*instance_color[:, None]-color_data[:, :, :3])))
assert color_error < 1e-6
mat = ob.material_slots[0].material
assert {n.type for n in mat.node_tree.nodes} == {'OUTPUT_MATERIAL','BSDF_PRINCIPLED','VERTEX_COLOR'}
bs = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')

arrays = dict(reference_positions=positions, reference_normals=normals,
              reference_colors=color_data[:, :, :3].reshape(-1, 3), reference_indices=faces.astype(np.uint32),
              template_positions=template, template_indices=pattern.astype(np.uint16),
              template_colors=template_color, template_corner_uv=uv[0],
              instance_matrices=matrices.transpose(0, 2, 1), instance_colors=instance_color,
              native_normal_oct_texture=normal_texture)
blob = bytearray()
description = {}
for key, values in arrays.items():
    values = np.ascontiguousarray(values)
    while len(blob) % 4:
        blob.append(0)
    data = values.tobytes()
    description[key] = dict(offset=len(blob), bytes=len(data), dtype=values.dtype.str,
                            shape=list(values.shape), sha256=hashlib.sha256(data).hexdigest())
    blob.extend(data)
folder = f'web/assets/{version}_leaf_diagnostic/'
binary = write_path(folder+'tree.bin')
metadata = write_path(folder+'tree.json')
assert not binary.exists() and not metadata.exists()
binary.write_bytes(blob)
assert hashlib.sha256(binary.read_bytes()).hexdigest() == hashlib.sha256(blob).hexdigest()
reference_bytes = sum(description[k]['bytes'] for k in description if k.startswith('reference_'))
packed_bytes = sum(description[k]['bytes'] for k in description if not k.startswith('reference_'))
out = dict(version=version, native_sha256=digest, native_object=ob.name,
           native_mesh_digest=mesh_digest(me), file='tree.bin', bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest(),
           arrays=description, leaves=count, vertices_per_leaf=vcount, faces_per_leaf=fcount,
           object_matrix_world=[list(row) for row in ob.matrix_world],
           native_local_bounds=[leaves.min((0,1)).tolist(), leaves.max((0,1)).tolist()],
           normal_texture_dimensions=[width, height],
           max_float32_affine_position_error_m=float(position_error.max()),
           minimum_instance_determinant=float(determinants.min()),
           max_normal_roundtrip_error_degrees=float(angles.max()), max_color_error=color_error,
           reference_attribute_bytes=reference_bytes, packed_attribute_bytes=packed_bytes,
           native_material=dict(name=mat.name, roughness=bs.inputs['Roughness'].default_value,
                                metallic=bs.inputs['Metallic'].default_value,
                                native_subsurface_weight=bs.inputs['Subsurface Weight'].default_value),
           comparison_scope='Same Three.js standard material on expanded native geometry and instanced geometry; normal texture stores per-leaf native normals. No native subsurface/material/light equivalence claim.',
           native_unmodified=True, browser_verified=False, full_runtime_published=False)
metadata.write_text(json.dumps(out, indent=2), encoding='utf-8')
write_path(f'evidence/{version}/leaf_diagnostic_export.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
assert native.stat().st_size == stat.st_size and native.stat().st_mtime_ns == stat.st_mtime_ns
print('LEAF_DIAGNOSTIC_EXPORTED', json.dumps({k:out[k] for k in ['leaves','reference_attribute_bytes','packed_attribute_bytes','max_float32_affine_position_error_m','max_normal_roundtrip_error_degrees']}), flush=True)
