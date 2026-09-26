"""r12 -> r13: reviewed scan-remnant cuts and correctly oriented bench grain.

Retain r12 as failed visual evidence. Do not change roof, columns, platform,
roads, facilities, cameras, lights or the other construction line.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT, read_path, write_path
from blender_apply_barycentric_cut import apply as apply_cut
from blender_geometry_fingerprint import mesh_digest, object_state


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


s = bpy.context.scene
assert s['version'] == 'G1_027r12'
assert sha(bpy.data.filepath) == 'aa40c5cb2834120b6a98c6b1311d65c0c1eb2e4aca9174aafc0c61d76bbedea2'
lease = json.loads(read_path('runtime/coordination/blender_lease.json').read_text())
assert lease['owner_role'] == 'main' and lease['main_may_launch'] and not lease['secondary_may_launch']
version = 'G1_027r13'
target = write_path('native/G1_027r13_bank_tram_residual_repair.blend')
assert not target.exists() and shutil.disk_usage(ROOT).free > 3_000_000_000
spec_path = read_path('derived/bellevue/bank_tram_shelter/residual_repair_r13.json')
d = json.loads(spec_path.read_text())
assert d['base_native_sha256'] == sha(bpy.data.filepath) and d['ready_for_native_repair']
for row in d['sources']:
    assert sha(row['path']) == row['sha256'], row['path']
old_report = json.loads(read_path('evidence/G1_027r12/bank_shelter_build_report.json').read_text())
cp = json.loads(read_path('evidence/G1_027r12/checkpoint.json').read_text())
fixtures = json.loads(read_path('derived/bellevue/bank_tram_shelter/fixtures_input.json').read_text())
bpy.context.view_layer.update()
before = {o.name:object_state(o) for o in s.objects}
pointers = {o.name:o.data.as_pointer() for o in s.objects if o.type == 'MESH'}
source_pointers = {o.name:o.data.as_pointer() for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
assert len(source_pointers) == 2039
cuts = [apply_cut(bpy.data.objects[row['object']],row) for row in d['rows']]
changed = {r['object'] for r in cuts}
uv_rows = []
for index,bench in enumerate(fixtures['benches']):
    for part in ['SEAT','BACK']:
        name = f'BST_BENCH_{index}_{part}'
        ob = bpy.data.objects[name]
        old = mesh_digest(ob.data)
        positions = np.empty(len(ob.data.vertices)*3,dtype=np.float32)
        ob.data.vertices.foreach_get('co',positions)
        old_positions = positions.tobytes()
        ob.data = ob.data.copy()
        uv = ob.data.uv_layers.active
        for face in ob.data.polygons:
            for li in face.loop_indices:
                q = np.asarray(ob.data.vertices[ob.data.loops[li].vertex_index].co)
                delta = q[:2]-np.asarray(bench['centre_xy'])
                along = float(delta@bench['axis'])/2.
                cross = (q[2]-bench['floor_z'] if abs(face.normal.z)<.5 else float(delta@bench['front']))/2.
                # The actually inspected oak image runs along texture V.
                # Keep a finite 2-D projection at the small cut end surfaces.
                if abs(np.asarray(face.normal)[:2]@bench['axis']) > .9:
                    uv.data[li].uv = (float(delta@bench['front'])/2.,(q[2]-bench['floor_z'])/2.)
                else:
                    uv.data[li].uv = (cross,along)
        ob.data.update()
        ob.data.vertices.foreach_get('co',positions)
        assert positions.tobytes() == old_positions, name
        uv_rows.append(dict(object=name,before=old,after=mesh_digest(ob.data),
                            texture_grain_axis='V',physical_grain_axis='bench long axis',geometry_changed=False))
        changed.add(name)
assert set(before) == {o.name for o in s.objects}
assert all(object_state(bpy.data.objects[n]) == row for n,row in before.items())
assert all(bpy.data.objects[n].data.as_pointer() == pointer for n,pointer in pointers.items() if n not in changed)
assert {o.name:o.data.as_pointer() for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects} == source_pointers

report = old_report
report['version'] = version
report['preserved_report_base'] = 'G1_027r12'
report['prepared_files'].append(dict(path=str(spec_path),sha256=sha(spec_path)))
photo_changes = {r['object']:r for r in cuts}
original_photo_rows = {r['object']:r for r in report['bounded_photo_cuts']}
for name,row in photo_changes.items():
    if name in original_photo_rows:
        original_photo_rows[name]['after'] = row['after']
        original_photo_rows[name]['subsequent_repair_version'] = version
    else:
        original_photo_rows[name] = row
report['bounded_photo_cuts'] = list(original_photo_rows.values())
collection = bpy.data.collections['47_BELLEVUE_BANK_TRAM_SHELTER']
report['author_meshes'] = {o.name:mesh_digest(o.data) for o in collection.objects if o.type=='MESH'}
report['author_states'] = {o.name:object_state(o) for o in collection.objects}
report['visual_acceptance'] = False
report['natural_use_verified'] = False
write_path(f'evidence/{version}/bank_shelter_build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
repair = dict(version=version,base_native_sha256=cp['native_sha256'],
              specification_sha256=sha(spec_path),photo_cuts=cuts,wood_uv=uv_rows,
              preserved_objects=len(before),source_preserved=2039,
              authored_positions_and_lights_unchanged=True,cameras_unchanged=True,
              visual_acceptance=False,natural_use_verified=False)
write_path(f'evidence/{version}/bank_shelter_repair_report.json').write_text(json.dumps(repair,indent=2),encoding='utf-8')
counts = {row['object']:len(bpy.data.objects[row['object']].data.polygons) for row in cuts}
for name in ['build_report.json','ubs_build_report.json','nearfront_build_report.json','sf1_merge_report.json']:
    r = json.loads(read_path(f'evidence/G1_027r12/{name}').read_text())
    r['version'] = version
    r['preserved_report_base'] = 'G1_027r12'
    if name == 'build_report.json':r.setdefault('subsequent_photo_counts',{}).update(counts)
    if name == 'ubs_build_report.json':r['final_photo_counts'].update({n:v for n,v in counts.items() if n in r['final_photo_counts']})
    if name == 'nearfront_build_report.json':
        for row in r['photo_cuts']:
            if row['object'] in counts:row['new_faces'] = counts[row['object']]
    write_path(f'evidence/{version}/{name}').write_text(json.dumps(r,indent=2),encoding='utf-8')
s['version'] = version
s['latest_construction'] = 'Bank canopy residual-scan repair and lengthwise bench grain; native layout and physical supports unchanged'
bpy.ops.wm.save_as_mainfile(filepath=str(target),check_existing=False,compress=True)
receipt = {k:cp[k] for k in ['storage_sharing_applied','required_immutable_libraries','shared_meshes','shared_objects']}
receipt.update(version=version,native=str(target),native_sha256=sha(target),native_bytes=target.stat().st_size,
               objects=len(s.objects),native_fresh_reopen_verified=False,visual_acceptance=False,
               runtime_exported=False,natural_use_verified=False)
write_path(f'evidence/{version}/checkpoint.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('BANK_SHELTER_REPAIRED',json.dumps({k:receipt[k] for k in ['native','native_sha256','native_bytes','objects']}),flush=True)
