"""Main-line integration helper. Import author collection; crop CURRENT local tiles.

Never loads an old context mesh into the main scene, never saves a main native,
never changes the global working pointer. The reviewer calls apply_to_current()
in a fresh new main working version and chooses when/where to save it.
"""
from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,'H:/MyWorld/ZurichWorld/tools')
from sf1_common import OUT,D,Q,sha
import bpy
from blender_photo_clip import cut_object
from blender_geometry_fingerprint import mesh_digest

def apply_to_current(increment=None,allow_changed_target_meshes=False):
    if increment is None:increment=OUT/f"native/{D['version']}_author_increment.blend"
    increment=Path(increment).resolve();assert increment.is_relative_to(OUT.resolve()) and increment.is_file()
    manifest=json.loads((OUT/f"evidence/{D['version'].split('_')[-1]}/construction.json").read_text())
    assert sha(increment)==manifest['increment_sha256'],'Increment differs from this version manifest.'
    assert sha(OUT/'derived/build_input.json')==manifest['build_input_sha256'],'Specification changed after native construction.'
    assert bpy.data.collections.get(D['import_collection']) is None,'SF1 already exists; do not append duplicates.'
    inventory=json.loads((OUT/'derived/native_context_inventory.json').read_text())
    before={r['original_name']:r for r in inventory['objects']}
    transforms=json.loads((OUT/'derived/verified_source_transforms.json').read_text())
    assert transforms['base_sha256']==D['base_sha256']
    expected_states={r['original_name']:r['state'] for r in transforms['objects']}
    checks=[]
    # Validate all targets before changing any mesh.
    for name in D['candidate_old_objects']:
        ob=bpy.data.objects[name];row=before[name]
        matrix=[float(v) for r in ob.matrix_world for v in r]
        assert matrix==expected_states[name]['matrix_world'],('Target transform changed',name,'actual',matrix,'recorded',expected_states[name]['matrix_world'])
        digest=json.loads(json.dumps(mesh_digest(ob.data)))
        same=digest==row['mesh_digest']
        assert same or allow_changed_target_meshes,('Target geometry changed since r8; inspect/rebase bounded crop before overriding this guard.',name)
        checks.append(dict(object=name,base_fingerprint_matches=same,before=digest))
    with bpy.data.libraries.load(str(increment),link=False) as (src,dst):
        assert D['import_collection'] in src.collections
        dst.collections=[D['import_collection']]
    C=dst.collections[0];bpy.context.scene.collection.children.link(C)
    assert C.get('sf1_version')==D['version'],'Wrong increment version.'
    assert C.get('build_spec_sha256')==manifest['build_input_sha256']
    assert all(ob.name.startswith('SF1_') for ob in C.all_objects)
    assert not any(ob.name.startswith('SF1_REF_') for ob in C.all_objects)
    b=D['scope_local'];boxes=D.get('crop_boxes',[[*b['u'],*b['v'],*b['z']]]);cuts=[]
    for name in D['candidate_old_objects']:
        ob=bpy.data.objects[name]
        result=cut_object(ob,Q,boxes);assert result,('Empty bounded crop',name)
        result['after']=mesh_digest(ob.data);cuts.append(result)
    bpy.context.view_layer.update()
    return dict(increment=str(increment),increment_sha256=sha(increment),collection=C.name,authored_objects=[o.name for o in C.all_objects],target_checks=checks,bounded_cuts=cuts,
        source_transform_verification_sha256=sha(OUT/'derived/verified_source_transforms.json'),
        base_native_sha256=D['base_sha256'],crop_boxes_uvz=boxes,coordinate_frame={k:D[k] for k in ['origin','A','U','N']},
        merged_context_from_old_native=False,main_native_saved=False,public_runtime_enabled=False,
        pending=['Full-scene independent views and seam checks','Public station interior continuation and door/runtime integration'])

if __name__=='__main__':
    raise RuntimeError('Reviewer must import and call apply_to_current() inside an explicitly chosen new main scene; this helper never selects or saves that scene.')
