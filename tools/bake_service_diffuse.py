"""Native static diffuse transport on the verified AO UVs; never save the blend.

This is a fixed-light cache. PBR colour/roughness/normal and geometry remain
separate. Moving doors are not baked into permanent illumination.
"""
import bpy
import hashlib
import json
import math
import numpy as np
import struct
import sys
from pathlib import Path
from mathutils import Vector

R = Path('F:/MyWorld/ZurichWorld')
sys.path.insert(0,str(R/'tools'))
from radiance_cache_io import write_hdr,read_hdr
s = bpy.context.scene
V = s['version']
assert V in ['G1_015r3','G1_016r1','G1_017','G1_017r1','G1_018r3']
assert all(p.normal.z < -.999 for p in bpy.data.objects['SV_SOURCE_SOFFIT'].data.polygons)
source = json.loads((R/'derived/runtime_occlusion'/V/'manifest.json').read_text())
uvs = np.load(R/source['uv_file'])
out = R/'derived/runtime_lighting'/V
out.mkdir(parents=True, exist_ok=True)
s.render.engine = 'CYCLES'
s.cycles.device = 'CPU'
s.cycles.samples = 128
s.render.threads_mode = 'FIXED'
s.render.threads = 10
s.render.use_persistent_data = False
s.cycles.use_denoising = False
s.render.use_compositing = False
s.render.use_sequencer = False
s.render.bake.use_pass_direct = True
s.render.bake.use_pass_indirect = True
s.render.bake.use_pass_color = False
s.render.bake.target = 'IMAGE_TEXTURES'
s.render.bake.margin = 3
s.render.bake.use_clear = True
assert 'DIFFUSE' in {x.identifier for x in bpy.ops.object.bake.get_rna_type().properties['type'].enum_items}

# Preserve full authored detail. Only remote photographic context uses the
# existing review texture tiers; no source geometry is removed.
with (R/'web/assets/G1_004r2_photo_stream.glb').open('rb') as f:
    f.seek(12)
    length, tag = struct.unpack('<II', f.read(8))
    photo = json.loads(f.read(length))
records = {m['name']: m['extras']['runtime_texture_lod'] for m in photo['materials']}
camera = bpy.data.objects['BE_QA_SERVICE_NORTH']
items = []
for ob in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects:
    corners = [ob.matrix_world @ Vector(p) for p in ob.bound_box]
    center = sum(corners, Vector()) / 8
    distance = max(1, (center-camera.location).length-max((p-center).length for p in corners))
    for mat in ob.data.materials:
        if mat.name in records: items.append((distance, mat, records[mat.name]))
full = 0
budget = 0
for distance, mat, record in sorted(items, key=lambda x:x[0]):
    cost = record['width'] * record['height'] * 4
    if distance < 100 and full < 180 and budget + cost < 300*1024*1024:
        full += 1
        budget += cost
        continue
    tier = 'medium' if distance < 200 else 'low'
    image = bpy.data.images.load(str(R/'web/assets'/record[tier]), check_existing=True)
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE': node.image = image

image = bpy.data.images.new('TEMP_STATIC_DIFFUSE', width=4096, height=4096, alpha=False, float_buffer=True)
image.colorspace_settings.name = 'Linear Rec.709'
copies = []
materials = {}
collection = bpy.data.collections.new('TEMP_DIFFUSE_RECEIVERS')
s.collection.children.link(collection)
bpy.context.view_layer.update()
deps = bpy.context.evaluated_depsgraph_get()
for record in source['receivers']:
    original = bpy.data.objects[record['name']]
    mesh = bpy.data.meshes.new_from_object(original.evaluated_get(deps), preserve_all_data_layers=True, depsgraph=deps)
    v = np.empty(len(mesh.vertices)*3, np.float32)
    mesh.vertices.foreach_get('co', v)
    ids = np.empty(len(mesh.loops), np.int32)
    mesh.loops.foreach_get('vertex_index', ids)
    assert hashlib.sha256(v.tobytes()+ids.tobytes()).hexdigest() == record['topology_sha256'], original.name
    # Join must not leave each object's active UV under a different layer name:
    # unlinked material texture inputs would otherwise sample an empty layer.
    if not mesh.uv_layers:
        mesh.uv_layers.new(name='native_primary_uv')
    primary_name=mesh.uv_layers[0].name
    mesh.uv_layers[0].name='native_primary_uv'
    uv = mesh.uv_layers.new(name='runtime_indirect_occlusion')
    uv.data.foreach_set('uv', uvs[record['uv_key']].ravel())
    # Original material maps use their original UV; only the bake target uses UV1.
    mesh.uv_layers.active_index = 0
    mesh.uv_layers[0].active_render = True
    for index, mat in enumerate(list(mesh.materials)):
        assert mat and mat.use_nodes
        material_key=(mat.name,primary_name)
        if material_key not in materials:
            copy = mat.copy()
            for node in copy.node_tree.nodes:
                if node.type=='UVMAP' and node.uv_map==primary_name:
                    node.uv_map='native_primary_uv'
            target = copy.node_tree.nodes.new('ShaderNodeTexImage')
            target.image = image
            copy.node_tree.nodes.active = target
            materials[material_key] = copy
        mesh.materials[index] = materials[material_key]
    copy = bpy.data.objects.new('BAKE_'+original.name, mesh)
    collection.objects.link(copy)
    copy.matrix_world = original.matrix_world.copy()
    copies.append(copy)
    original.hide_render = True

moving_excluded = []
# hide_render tags the collection cache; never mutate while traversing its RNA
# all_objects iterator (Blender 4.5 invalidates that iterator).
for ob in list(bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].all_objects):
    ancestor = ob
    while ancestor:
        if any(part in str(ancestor.get('interaction_role', '')).lower() for part in ['hinge', 'door', 'sliding']):
            ob.hide_render = True
            moving_excluded.append(ob.name)
            break
        ancestor = ancestor.parent

for ob in s.objects: ob.select_set(False)
for ob in copies: ob.select_set(True)
bpy.context.view_layer.objects.active = copies[0]
# One receiver avoids sequential baking and preserves the exact packed UVs.
assert 'FINISHED' in bpy.ops.object.join()
receiver = bpy.context.object
receiver.data.uv_layers.active_index = 0
receiver.data.uv_layers[0].active_render = True
assert len(receiver.data.loops) == sum(x['loops'] for x in source['receivers'])
print('DIFFUSE_BAKE_START', V, len(source['receivers']), len(receiver.data.loops), flush=True)
assert 'FINISHED' in bpy.ops.object.bake(type='DIFFUSE', uv_layer='runtime_indirect_occlusion')
path = R/'web/assets'/f'{V}_service_diffuse_linear.hdr'
# The bake/save path labelled the earlier generated cache as sRGB in Blender
# 4.5.13. Write its in-memory linear samples explicitly instead of relying on
# inferred file colour management.
pixels=np.empty(4096*4096*4,np.float32);image.pixels.foreach_get(pixels)
rgb=np.ascontiguousarray(pixels.reshape(4096,4096,4)[::-1,:,:3])
write_hdr(path,rgb);decoded=read_hdr(path)
quantization=float((np.abs(decoded-rgb)/(rgb.max(axis=2,keepdims=True)+1e-8)).max())
assert quantization<.009,quantization
report = {
    'version': V, 'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    'native': bpy.data.filepath, 'receivers': [x['name'] for x in source['receivers']],
    'uv_topology_verified': True, 'uv_source': source['uv_file'],
    'samples': 128, 'resolution': [4096,4096], 'pass': 'DIFFUSE_DIRECT_INDIRECT_NO_COLOR',
    'linear': True, 'native_saved': False, 'moving_occluders_excluded': moving_excluded,
    'encoding':'Direct RGBE from in-memory linear pixels; Image.save colour conversion bypassed',
    'written_linear_max_relative_error':quantization,
    'replaces_rejected_gamma_encoded_file':f'{V}_service_diffuse.hdr',
    'limitation': 'Static diffuse lighting for fixed native light state. No dynamic diffuse shadows or weather updates; moving and transmissive receivers are excluded.'
}
(out/'manifest.json').write_text(json.dumps(report, indent=2))
print('DIFFUSE_BAKE_FINISHED', V, str(path), flush=True)
