"""r14 -> r15: only the diagnosed photographic remnants along the bank eave."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT, read_path, write_path
from blender_apply_barycentric_cut import apply as apply_cut
from blender_geometry_fingerprint import mesh_digest, object_state


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


s = bpy.context.scene
assert s['version'] == 'G1_027r14'
base = 'G1_027r14'
version = 'G1_027r15'
cp = json.loads(read_path(f'evidence/{base}/checkpoint.json').read_text())
assert sha(bpy.data.filepath) == cp['native_sha256']
lease = json.loads(read_path('runtime/coordination/blender_lease.json').read_text(encoding='utf-8-sig'))
assert lease['owner_role'] == 'main' and lease['main_may_launch'] and not lease['secondary_may_launch']
target = write_path('native/G1_027r15_bank_eave_scan_repair.blend')
assert not target.exists() and shutil.disk_usage(ROOT).free > 3_000_000_000
spec_path = read_path('derived/ubs_theaterstrasse20/upper_residual_repair_r15.json')
d = json.loads(spec_path.read_text())
assert d['base_native_sha256'] == cp['native_sha256'] and d['ready_for_native_repair']
for row in d['sources']:
    assert sha(row['path']) == row['sha256']
for row in d['actual_upper_objects']:
    assert json.loads(json.dumps(mesh_digest(bpy.data.objects[row['object']].data))) == row['mesh_digest']
bpy.context.view_layer.update()
before = {o.name: object_state(o) for o in s.objects}
pointers = {o.name: o.data.as_pointer() for o in s.objects if o.type == 'MESH'}
originals = {o.name: o.data.as_pointer() for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
assert len(originals) == 2039
cuts = [apply_cut(bpy.data.objects[row['object']], row) for row in d['rows']]
changed = {row['object'] for row in cuts}
assert changed == {'CTX_I3S_33552','CTX_I3S_33436','CTX_I3S_33386'}
assert set(before) == {o.name for o in s.objects}
assert all(object_state(bpy.data.objects[n]) == row for n, row in before.items())
assert all(bpy.data.objects[n].data.as_pointer() == pointer for n, pointer in pointers.items() if n not in changed)
assert {o.name: o.data.as_pointer() for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects} == originals

counts = {row['object']: len(bpy.data.objects[row['object']].data.polygons) for row in cuts}
for name in ['build_report.json','ubs_build_report.json','nearfront_build_report.json','sf1_merge_report.json',
             'bank_shelter_build_report.json','bank_shelter_repair_report.json','bank_curvature_build_report.json']:
    report = json.loads(read_path(f'evidence/{base}/{name}').read_text())
    report['version'] = version
    report['preserved_report_base'] = base
    if name == 'build_report.json':
        report.setdefault('subsequent_photo_counts', {}).update(counts)
    if name == 'ubs_build_report.json':
        report['final_photo_counts'].update({n:c for n,c in counts.items() if n in report['final_photo_counts']})
    if name == 'nearfront_build_report.json':
        for row in report['photo_cuts']:
            if row['object'] in counts:
                row['new_faces'] = counts[row['object']]
    if name == 'bank_shelter_build_report.json':
        report['prepared_files'].append(dict(path=str(spec_path), sha256=sha(spec_path)))
        for row in report['bounded_photo_cuts']:
            if row['object'] in changed:
                row['after'] = next(c['after'] for c in cuts if c['object'] == row['object'])
                row['subsequent_repair_version'] = version
    write_path(f'evidence/{version}/{name}').write_text(json.dumps(report, indent=2), encoding='utf-8')
report = dict(version=version, base_native_sha256=cp['native_sha256'], specification_sha256=sha(spec_path),
              photo_cuts=cuts, preserved_object_states=len(before), source_preserved=2039,
              all_authored_geometry_cameras_lights_unchanged=True,
              bounded_scan_halo_is_inferred=True, visual_acceptance=False, natural_use_verified=False)
write_path(f'evidence/{version}/upper_residual_build_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
s['version'] = version
s['latest_construction'] = 'Only bounded scan remnants at rebuilt UBS front eave; measured building geometry and other areas unchanged'
bpy.ops.wm.save_as_mainfile(filepath=str(target), check_existing=False, compress=True)
receipt = {k:cp[k] for k in ['storage_sharing_applied','required_immutable_libraries','shared_meshes','shared_objects']}
receipt.update(version=version, native=str(target), native_sha256=sha(target), native_bytes=target.stat().st_size,
               objects=len(s.objects), native_fresh_reopen_verified=False, visual_acceptance=False,
               runtime_exported=False, natural_use_verified=False)
write_path(f'evidence/{version}/checkpoint.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('UBS_EAVE_REPAIR_SAVED', json.dumps({k:receipt[k] for k in ['native','native_sha256','native_bytes','objects']}), flush=True)
