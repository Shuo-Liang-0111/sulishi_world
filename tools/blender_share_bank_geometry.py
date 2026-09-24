"""Share24 unchanged bank crown meshes with retained025r1, without visual loss.

The newly created026 checkpoint is saved first so the retained source can be
linked as an external library. Only this current026 file is rewritten; all
previous checkpoints remain. This avoids adding another~320MB every revision.
"""
from pathlib import Path
import hashlib,json,shutil,sys
import bpy

R=Path('F:/MyWorld/ZurichWorld');E=R/'evidence/G1_026';s=bpy.context.scene
sys.path.insert(0,str(R/'tools'))
from blender_geometry_fingerprint import mesh_digest,object_state
target=R/'native/G1_026_bridgehead_portal_working.blend';base=R/'native/G1_025r1_bank_tree_replacement_working.blend'
assert s['version']=='G1_026' and Path(bpy.data.filepath).resolve()==target.resolve()
assert shutil.disk_usage(R).free>150_000_000
expected='76d89aef5c2f551e56d595ee1c521de140f19263df68e28b9af4ccc10a83718f'
with base.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==expected
targets=[o for o in bpy.data.collections['41_BRIDGEHEAD_TREES'].objects if o.name.endswith(('_TWIGS','_LEAVES'))]
assert len(targets)==24 and all(o.data.library is None for o in targets)
before={o.name:object_state(o) for o in s.objects};owners={o.data.name:o for o in targets};names=sorted(owners)
digests={name:mesh_digest(ob.data) for name,ob in owners.items()}
other={o.name:o.data for o in s.objects if o.type=='MESH' and o not in targets}
with bpy.data.libraries.load(str(base),link=True,relative=True) as (src,dst):
    assert set(names)<=set(src.meshes);dst.meshes=names[:]
for name,mesh in zip(names,dst.meshes):
    assert mesh.library and mesh_digest(mesh)==digests[name],name
    ob=owners[name];old=ob.data;materials=[slot.material for slot in ob.material_slots];ob.data=mesh
    for slot,material in zip(ob.material_slots,materials):slot.link='OBJECT';slot.material=material
    assert object_state(ob)==before[ob.name]
    old.use_fake_user=False;assert old.users==0;bpy.data.meshes.remove(old)
bpy.context.view_layer.update()
assert {o.name:object_state(o) for o in s.objects}==before
assert all(bpy.data.objects[name].data==data for name,data in other.items())
record=json.loads((E/'checkpoint.json').read_text());old_bytes=record['native_bytes'];old_hash=record['native_sha256']
libs=record['required_immutable_libraries'];libs[base.name]=expected
assert {Path(bpy.path.abspath(lib.filepath)).name for lib in bpy.data.libraries}==set(libs)
for lib in bpy.data.libraries:
    path=Path(bpy.path.abspath(lib.filepath)).resolve();assert path.parent==target.parent.resolve()
    lib.filepath=bpy.path.relpath(str(path),start=str(target.parent))
missing=[im.name for im in bpy.data.images if im.source=='FILE' and not im.packed_file and im.filepath and not Path(bpy.path.abspath(im.filepath,library=im.library)).is_file()]
assert not missing,missing
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True,relative_remap=False)
with target.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
record.update(native_sha256=digest,native_bytes=target.stat().st_size,required_immutable_libraries=libs,
    storage_sharing_applied=True,before_sharing_bytes=old_bytes,before_sharing_sha256=old_hash,
    shared_meshes={name:json.loads(json.dumps(value)) for name,value in digests.items()},
    shared_objects={ob.name:ob.data.name for ob in targets})
(E/'checkpoint.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
p=R/'runtime/station_road_working.json';w=json.loads(p.read_text());w.update(version=s['version'],native=str(target),
    source_cut_file=s['photo_cut_file'],source_cut_sha256=record['source_cut_sha256'],accepted=False,not_published=True,
    next='Inspect saved026 portal and upper bridgehead at original views, verify shared crown meshes, then corresponding realtime material/physical integration.')
p.write_text(json.dumps(w,ensure_ascii=False,indent=2),encoding='utf-8')
print('BANK_CROWNS_SHARED',json.dumps(dict(native_bytes=record['native_bytes'],sha256=digest,shared_meshes=len(names),objects=len(s.objects),required_libraries=libs)),flush=True)
