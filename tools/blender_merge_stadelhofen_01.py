"""Integrate a separately reviewed SF1 increment onto the current r10 native.

No old city tile is imported. Current target meshes must match the reviewed
baseline before bounded crops are replayed. The source archive and all other
existing objects remain untouched. Main visual approval is required first.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import runpy
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT, read_path, write_path
from blender_geometry_fingerprint import mesh_digest, object_state


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


s = bpy.context.scene
assert s['version'] == 'G1_027r10'
lease = json.loads(read_path('runtime/coordination/blender_lease.json').read_text(encoding='utf-8-sig'))
assert lease['owner_thread'] == '01a08947-06f2-7123-b7c7-c955cfa6c809' and lease['main_may_launch']
decision = json.loads(read_path('evidence/stadelhofen_01_main_review.json').read_text())
assert decision['approved_for_integration'] and decision['six_original_views_actually_inspected']
package = ROOT / 'parallel/stadelhofen_01'
spec = json.loads((package / 'derived/build_input.json').read_text())
tag = spec['version'].split('_')[-1]
manifest = json.loads((package / f'evidence/{tag}/construction.json').read_text())
assert spec['version'] == decision['package_version']
assert manifest['increment_sha256'] == decision['increment_sha256']
assert sha(package / 'derived/build_input.json') == decision['spec_sha256'] == manifest['build_input_sha256']
assert sha(manifest['native']) == manifest['sha256'] == decision['native_sha256']
checkpoint = json.loads(read_path('evidence/G1_027r10/checkpoint.json').read_text())
assert sha(bpy.data.filepath) == checkpoint['native_sha256'] and checkpoint['native_fresh_reopen_verified']
runpy.run_path(str(ROOT/'tools/blender_probe_bank_tram_shelter.py'),
              init_globals={'FULL_PLATFORM':True},run_name='__main__')
version = 'G1_027r11'
target = write_path('native/G1_027r11_stadelhofen_entry_integrated.blend')
assert not target.exists() and shutil.disk_usage(ROOT).free > 3_000_000_000
assert not any(o.name.startswith('SF1_') for o in s.objects)
before = {o.name: object_state(o) for o in s.objects}
pointers = {o.name: o.data.as_pointer() for o in s.objects if o.type == 'MESH'}
source = {o.name: o.data.as_pointer() for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
old_cameras = {o.name: {'matrix': [list(r) for r in o.matrix_world], 'lens': o.data.lens,
                      'sensor_width': o.data.sensor_width} for o in s.objects if o.type == 'CAMERA'}
sys.path.insert(0, str(package))
from apply_increment import apply_to_current
result = apply_to_current(allow_changed_target_meshes=False)
changed = {r['object'] for r in result['bounded_cuts']}
assert changed == set(spec['candidate_old_objects'])
assert all(r['base_fingerprint_matches'] for r in result['target_checks'])
assert source == {o.name: o.data.as_pointer() for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
assert all(object_state(bpy.data.objects[n]) == state for n, state in before.items())
assert all(bpy.data.objects[n].data.as_pointer() == p for n, p in pointers.items() if n not in changed)
names = ('SF1_QA_ENTRY', 'SF1_QA_REVERSE', 'SF1_QA_APPROACH', 'SF1_QA_CONTEXT',
         'SF1_QA_DOOR_DETAIL', 'SF1_QA_DOOR_OPEN')
with bpy.data.libraries.load(manifest['native'], link=False) as (src, dst):
    assert all(n in src.objects for n in names)
    # Blender replaces this assigned list's strings with loaded IDs on exit.
    # Keep the immutable requested names separate for validation/reporting.
    dst.objects = list(names)
camera_collection = bpy.data.collections['90_REVIEW_CAMERAS']
for camera in dst.objects:
    assert camera.type == 'CAMERA' and camera.name in names and camera.parent is None, (
        camera.name, camera.type, camera.parent.name if camera.parent else None, names)
    camera_collection.objects.link(camera)
bpy.context.view_layer.update()
assert all({'matrix': [list(r) for r in bpy.data.objects[n].matrix_world],
            'lens': bpy.data.objects[n].data.lens,
            'sensor_width': bpy.data.objects[n].data.sensor_width} == old for n, old in old_cameras.items())
author = bpy.data.collections[spec['import_collection']]
for row in manifest['authored_objects']:
    ob = bpy.data.objects[row['name']]
    assert ob.name in author.all_objects and ob.type == row['type']
    if ob.type == 'MESH':
        assert json.loads(json.dumps(mesh_digest(ob.data))) == row['mesh_digest'], ob.name
assert not bpy.data.objects['SF1_DOOR_CENTRE_CONTROL'].get('public_runtime_enabled', False)
s['sf1_version'] = spec['version']
s['version'] = version
s['latest_construction'] = 'Reviewed Stadelhofen central entrance increment; full-scene integration review pending'
report = dict(version=version, base_native_sha256=checkpoint['native_sha256'],
              package_version=spec['version'], package_spec_sha256=decision['spec_sha256'],
              package_native_sha256=decision['native_sha256'], import_report=result,
              source_objects_unchanged=len(source), old_objects_unchanged=len(before),
              old_cameras=old_cameras, review_cameras=names,
              author_states={o.name: object_state(o) for o in author.all_objects},
              author_meshes={o.name: mesh_digest(o.data) for o in author.all_objects if o.type == 'MESH'},
              camera_states={o.name: object_state(o) for o in dst.objects},
              package_boundary_receipt_sha256=sha(package / f'evidence/{tag}/actual_boundary_probe.json'),
              public_runtime_enabled=False, visual_acceptance=False, natural_use_verified=False)
write_path(f'evidence/{version}/sf1_merge_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
for name in ['build_report.json', 'ubs_build_report.json', 'nearfront_build_report.json']:
    data = json.loads(read_path(f'evidence/G1_027r10/{name}').read_text())
    data['version'] = version
    data['preserved_report_base'] = 'G1_027r10'
    if name == 'build_report.json':
        counts = data.setdefault('subsequent_photo_counts', {})
        counts.update({n: len(bpy.data.objects[n].data.polygons) for n in changed})
    write_path(f'evidence/{version}/{name}').write_text(json.dumps(data, indent=2), encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(target), check_existing=False, compress=True)
receipt = {k: checkpoint[k] for k in ['storage_sharing_applied', 'required_immutable_libraries', 'shared_meshes', 'shared_objects']}
receipt.update(version=version, native=str(target), native_sha256=sha(target),
               native_bytes=target.stat().st_size, objects=len(s.objects),
               native_fresh_reopen_verified=False, visual_acceptance=False,
               runtime_exported=False, natural_use_verified=False)
write_path(f'evidence/{version}/checkpoint.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('SF1_MAIN_INTEGRATED', json.dumps({k:receipt[k] for k in ['native', 'native_sha256', 'native_bytes', 'objects']}), flush=True)
