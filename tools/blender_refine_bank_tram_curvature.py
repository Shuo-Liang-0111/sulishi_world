"""r13 -> r14: repair disconnected curved skins and refit their attachments."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT, read_path, write_path
from blender_geometry_fingerprint import mesh_digest, object_state


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def surface_tree(ob):
    me = ob.data
    me.calc_loop_triangles()
    return BVHTree.FromPolygons([ob.matrix_world @ v.co for v in me.vertices],
                               [list(t.vertices) for t in me.loop_triangles], all_triangles=True)


def support(tree, xy):
    p, n, _, _ = tree.ray_cast(Vector((float(xy[0]), float(xy[1]), 13.1)), Vector((0, 0, -1)), 1.5)
    assert p is not None
    return p, n


s = bpy.context.scene
assert s['version'] == 'G1_027r13'
cp = json.loads(read_path('evidence/G1_027r13/checkpoint.json').read_text())
assert sha(bpy.data.filepath) == cp['native_sha256']
lease = json.loads(read_path('runtime/coordination/blender_lease.json').read_text(encoding='utf-8-sig'))
assert lease['owner_role'] == 'main' and lease['main_may_launch'] and not lease['secondary_may_launch']
version = 'G1_027r14'
target = write_path('native/G1_027r14_bank_tram_curvature.blend')
assert not target.exists() and shutil.disk_usage(ROOT).free > 3_000_000_000
spec_path = read_path('derived/bellevue/bank_tram_shelter/curvature_repair_r14.json')
spec = json.loads(spec_path.read_text())
assert spec['base_native_sha256'] == cp['native_sha256'] and spec['ready_for_native_repair']
for row in spec['source_files']:
    assert sha(row['path']) == row['sha256']
assert sha(spec['arrays_path']) == spec['arrays_sha256']
arrays = np.load(spec['arrays_path'])
bpy.context.view_layer.update()
before = {o.name: object_state(o) for o in s.objects}
pointers = {o.name: o.data.as_pointer() for o in s.objects if o.type == 'MESH'}
source = bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE']
source_pointers = {o.name: o.data.as_pointer() for o in source.objects}
old_soffit = surface_tree(bpy.data.objects['BST_CANOPY_SOFFIT'])
changed, meshes = set(), []
for index, row in enumerate(spec['parts']):
    ob = bpy.data.objects[row['object']]
    assert json.loads(json.dumps(mesh_digest(ob.data))) == row['original_digest']
    assert [list(r) for r in ob.matrix_world] == row['native_matrix']
    verts, faces, normals = [arrays[f'{key}{index}'] for key in ['v', 'f', 'n']]
    me = bpy.data.meshes.new(ob.name + '_continuous_r14')
    me.from_pydata(verts.tolist(), [], faces.tolist())
    me.update()
    for mat in ob.data.materials:
        me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    uv = me.uv_layers.new(name='metric_surface')
    for loop in me.loops:
        q = verts[loop.vertex_index]
        uv.data[loop.index].uv = (q[0]/2., q[1]/2.)
    me.normals_split_custom_set([normals[loop.vertex_index].tolist() for loop in me.loops])
    me.update()
    ob.data = me
    changed.add(ob.name)
    meshes.append(dict(object=ob.name, before=row['original_digest'], after=mesh_digest(me)))

new_soffit = surface_tree(bpy.data.objects['BST_CANOPY_SOFFIT'])
attachments = []
for index in range(3):
    ob = bpy.data.objects[f'BST_COLUMN_{index}']
    original = [tuple(v.co) for v in ob.data.vertices]
    ob.data = ob.data.copy()
    assert len(original) == 9*64
    deltas = []
    for v in list(ob.data.vertices)[-64:]:
        point, _ = support(new_soffit, v.co[:2])
        z = point.z+.005
        deltas.append(z-v.co.z)
        v.co.z = z
    ob.data.update()
    assert [tuple(v.co) for v in ob.data.vertices[:-64]] == original[:-64]
    attachments.append(dict(object=ob.name, affected_vertices=64, max_abs_delta_m=max(abs(v) for v in deltas),
                            basis='Only mushroom head rim refitted to actual refined soffit; shaft and foot preserved.'))
    changed.add(ob.name)

# Six small recessed lenses and trims remain rigid circular pieces. Rotate each
# onto the actual local tangent; do not warp individual rim vertices to the roof.
for name in ['BST_RECESSED_LIGHT_TRIM', 'BST_RECESSED_LIGHT_LENS']:
    ob = bpy.data.objects[name]
    original = np.array([v.co for v in ob.data.vertices])
    assert len(original) == 6*48
    ob.data = ob.data.copy()
    for i in range(6):
        group = original[i*48:(i+1)*48]
        xy = group[:, :2].mean(axis=0)
        old_p, _ = support(old_soffit, xy)
        new_p, new_n = support(new_soffit, xy)
        assert new_n.z < -.8
        rotation = Vector((0, 0, 1)).rotation_difference(-new_n).to_matrix()
        center_before = Vector((float(xy[0]), float(xy[1]), old_p.z))
        center_after = Vector((float(xy[0]), float(xy[1]), new_p.z))
        for j, q in enumerate(group):
            ob.data.vertices[i*48+j].co = center_after + rotation @ (Vector(q)-center_before)
    ob.data.update()
    attachments.append(dict(object=name, affected_vertices=len(original), rigid_pieces=6,
                            basis='Rigid recessed fittings reseated at unchanged six anchors on the native tangent.'))
    changed.add(name)

bpy.context.view_layer.update()
assert {o.name for o in s.objects} == set(before)
assert all(object_state(bpy.data.objects[n]) == value for n, value in before.items())
assert all(bpy.data.objects[n].data.as_pointer() == p for n, p in pointers.items() if n not in changed)
assert {o.name: o.data.as_pointer() for o in source.objects} == source_pointers and len(source_pointers) == 2039
collection = bpy.data.collections['47_BELLEVUE_BANK_TRAM_SHELTER']
bank_report = json.loads(read_path('evidence/G1_027r13/bank_shelter_build_report.json').read_text())
bank_report['version'] = version
bank_report['preserved_report_base'] = 'G1_027r13'
bank_report['prepared_files'].append(dict(path=str(spec_path), sha256=sha(spec_path)))
bank_report['author_meshes'] = {o.name: mesh_digest(o.data) for o in collection.objects if o.type == 'MESH'}
bank_report['author_states'] = {o.name: object_state(o) for o in collection.objects}
for row in bank_report['column_checks']:
    row['top_ring'] = [list(v.co) for v in list(bpy.data.objects[row['object']].data.vertices)[-64:]]
write_path(f'evidence/{version}/bank_shelter_build_report.json').write_text(json.dumps(bank_report, indent=2), encoding='utf-8')
report = dict(version=version, base_native_sha256=cp['native_sha256'], specification_sha256=sha(spec_path),
              refined_meshes=meshes, refitted_attachments=attachments, changed_meshes=sorted(changed),
              preserved_object_states=len(before), source_preserved=2039, cameras_and_light_objects_unchanged=True,
              visual_acceptance=False, natural_use_verified=False)
write_path(f'evidence/{version}/bank_curvature_build_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
for name in ['build_report.json', 'ubs_build_report.json', 'nearfront_build_report.json', 'sf1_merge_report.json',
             'bank_shelter_repair_report.json']:
    r = json.loads(read_path(f'evidence/G1_027r13/{name}').read_text())
    r['version'] = version
    r['preserved_report_base'] = 'G1_027r13'
    write_path(f'evidence/{version}/{name}').write_text(json.dumps(r, indent=2), encoding='utf-8')
s['version'] = version
s['latest_construction'] = 'Bank canopy connected fine curvature, continuous normals and reseated mushroom heads/recessed fittings'
bpy.ops.wm.save_as_mainfile(filepath=str(target), check_existing=False, compress=True)
receipt = {k: cp[k] for k in ['storage_sharing_applied', 'required_immutable_libraries', 'shared_meshes', 'shared_objects']}
receipt.update(version=version, native=str(target), native_sha256=sha(target), native_bytes=target.stat().st_size,
               objects=len(s.objects), native_fresh_reopen_verified=False, visual_acceptance=False,
               runtime_exported=False, natural_use_verified=False)
write_path(f'evidence/{version}/checkpoint.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('BANK_CURVATURE_SAVED', json.dumps({k: receipt[k] for k in ['native', 'native_sha256', 'native_bytes', 'objects']}), flush=True)
