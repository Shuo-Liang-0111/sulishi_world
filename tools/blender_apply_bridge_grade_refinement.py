"""Apply a fully checked322-mesh refinement while retaining the027r1 file."""
from pathlib import Path
import hashlib,json,runpy,sys
import bpy
import numpy as np
R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/bridge_grade'
s=bpy.context.scene;assert s['version']=='G1_027r1'
assert Path(bpy.data.filepath).name=='G1_027r1_bridgehead_grade_working.blend'
E=R/'evidence/G1_027r2';E.mkdir(exist_ok=True)
meta=json.loads((D/'027r2_refined_objects.json').read_text());report=json.loads((D/'027r2_refinement.json').read_text())
assert not report['unresolved']
runpy.run_path(str(R/'tools/blender_check_bridge_grade_refinement.py'))
sys.path.insert(0,str(R/'tools'));from blender_geometry_fingerprint import mesh_digest,object_state
from blender_bridge_refinement_cleanup import strip_zero_faces
ref=np.load(D/'027r2_refined_reference.npz');patch=np.load(D/'027r2_refined_patch.npz')
old={o.name:object_state(o) for o in s.objects}
for row in meta['objects']:
    ob=bpy.data.objects[row['name']]
    assert json.loads(json.dumps(mesh_digest(ob.data)))==row['before_fingerprint'],ob.name
    assert ob.data.users==1 and not ob.data.library
prepared=[];zero_cleanup=[]
try:
    for row in meta['objects']:
        ob=bpy.data.objects[row['name']];key=row['key'];me=bpy.data.meshes.new('BRIDGE_REFINED_'+ob.name)
        prepared.append((row,ob,me))
        me.from_pydata(patch[key].tolist(),[],ref[key+'_faces'].tolist());me.update()
        for slot in ob.material_slots:me.materials.append(slot.material)
        me.polygons.foreach_set('material_index',ref[key+'_material_index'])
        me.polygons.foreach_set('use_smooth',ref[key+'_use_smooth'])
        for i,name in enumerate(row['uv_names']):
            uv=me.uv_layers.new(name=name);uv.data.foreach_set('uv',ref[key+'_uv_'+str(i)].ravel())
        clean,bad=strip_zero_faces(me)
        if bad:
            bpy.data.meshes.remove(me);me=clean;prepared[-1]=(row,ob,me)
            zero_cleanup.append(dict(name=ob.name,zero_area_faces=bad))
        assert not me.validate(clean_customdata=False),('Invalid prepared mesh',ob.name)
        assert len(me.polygons)==len(ref[key+'_faces'])-len(bad)
    for row,ob,me in prepared:
        prior=ob.data;materials=[slot.material for slot in ob.material_slots];ob.data=me
        for slot,mat in zip(ob.material_slots,materials):slot.material=mat
        ob['grade_revision']='G1_027r2'
        ob['grade_basis']='Existing source fit; continuous retained-bank extension and refined same-footprint mesh.'
        if prior.users==0 and prior.library is None:bpy.data.meshes.remove(prior)
except Exception:
    for _,ob,me in prepared:
        if me.users==0:bpy.data.meshes.remove(me)
    raise
assert {o.name:object_state(o) for o in s.objects}==old
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
s['version']='G1_027r2';s['grade_refinement_file']='derived/bellevue/bridge_grade/027r2_refinement.json'
bpy.context.view_layer.update()
record=dict(version=s['version'],objects=len(s.objects),replaced_meshes=len(prepared),
    zero_area_cleanup=zero_cleanup,
    input_sha256=hashlib.sha256((D/'027r2_refinement.json').read_bytes()).hexdigest(),
    after_fingerprints=[dict(name=ob.name,mesh_fingerprint=mesh_digest(ob.data)) for _,ob,_ in prepared],
    source_footprints_preserved=True,original_photo_meshes_unchanged=True,materials_lights_cameras_unchanged=True,
    visual_acceptance=False,natural_use_verified=False,runtime_exported=False)
(E/'construction.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
runpy.run_path(str(R/'tools/blender_check_bridge_grade_refinement.py'))
print('BRIDGE_GRADE_REFINED',len(prepared),flush=True)
