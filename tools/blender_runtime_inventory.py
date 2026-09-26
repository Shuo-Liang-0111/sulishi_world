"""Read the current native world for a versioned runtime export.

Detect cumulative photo changes from actual object/mesh state, never from the
last operation's cut manifest. No scene mutation, export, or acceptance claim.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys
import time
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import read_path, write_path, validate_native
from blender_geometry_fingerprint import mesh_digest


def build_inventory():
    started = time.time()
    scene = bpy.context.scene
    native = validate_native(bpy.data.filepath)
    version = scene['version']
    cp = json.loads(read_path(f'evidence/{version}/checkpoint.json').read_text())
    with native.open('rb') as stream:
        digest = hashlib.file_digest(stream,'sha256').hexdigest()
    assert digest == cp['native_sha256']
    visible = set()
    def visit(collection, hidden=False):
        hidden = hidden or collection.hide_render
        if not hidden:
            visible.update(ob.name for ob in collection.objects if not ob.hide_render)
        for child in collection.children:
            visit(child, hidden)
    visit(scene.collection)
    origin = bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE']
    context = bpy.data.collections['04_RETAINED_PHOTO_CONTEXT']
    originals = {str(ob['source_node']):ob for ob in origin.objects}
    assert len(originals) == len(origin.objects) == 2039
    mesh_hashes = {}
    def fingerprint(mesh):
        key = mesh.as_pointer()
        if key not in mesh_hashes:
            mesh_hashes[key] = mesh_digest(mesh)['sha256']
        return mesh_hashes[key]
    photo_rows = []
    for ob in context.objects:
        key = str(ob['source_node']); source = originals[key]
        assert ob.type == source.type == 'MESH'
        assert ob.parent is None and source.parent is None
        assert not ob.constraints and not source.constraints
        assert not ob.modifiers and not source.modifiers
        different = []
        if ob.data is not source.data and fingerprint(ob.data) != fingerprint(source.data):
            different.append('mesh_or_uv_attributes')
        if ob.matrix_basis != source.matrix_basis:
            different.append('transform')
        if [slot.material for slot in ob.material_slots] != [slot.material for slot in source.material_slots]:
            different.append('material_slots')
        photo_rows.append(dict(node=key,object=ob.name,source_object=source.name,
            changed=bool(different),differences=different,faces=len(ob.data.polygons),
            vertices=len(ob.data.vertices),empty=len(ob.data.polygons)==0,
            visible=ob.name in visible,
            current_mesh_sha256=fingerprint(ob.data) if different else None))
    assert len({r['node'] for r in photo_rows}) == len(photo_rows)

    building = bpy.data.collections['10_BELLEVUE_RECONSTRUCTION']
    authored = [o for o in building.all_objects if o.name in visible]
    meshes = [o for o in authored if o.type=='MESH']
    collections = []
    for col in [building,*list(building.children_recursive)]:
        objects = [o for o in col.objects if o.name in visible]
        if objects:
            collections.append(dict(name=col.name,objects=len(objects),
                polygons=sum(len(o.data.polygons) for o in objects if o.type=='MESH'),
                vertices=sum(len(o.data.vertices) for o in objects if o.type=='MESH')))
    materials = {slot.material.name:slot.material for ob in authored for slot in ob.material_slots if slot.material}
    material_rows = []
    for name, material in sorted(materials.items()):
        nodes = list(material.node_tree.nodes) if material.use_nodes else []
        images = [dict(name=n.image.name,file=bpy.path.abspath(n.image.filepath,library=n.image.library),
                       width=n.image.size[0],height=n.image.size[1],colorspace=n.image.colorspace_settings.name)
                  for n in nodes if n.type=='TEX_IMAGE' and n.image]
        # Presence flags require review; they are not assertions that a material
        # can be reproduced by glTF's narrower PBR graph.
        node_types = sorted(set(n.type for n in nodes))
        complex_nodes = sorted(set(node_types)-{'OUTPUT_MATERIAL','BSDF_PRINCIPLED','TEX_COORD','MAPPING','TEX_IMAGE','NORMAL_MAP'})
        material_rows.append(dict(name=name,node_types=node_types,images=images,
            nontrivial_export_nodes=complex_nodes,requires_material_equivalence_review=bool(complex_nodes)))
    cameras = []
    # SF1's six review cameras belong to its isolated increment collection;
    # enumerating only the historic review collection silently dropped them.
    for ob in scene.objects:
        if ob.type!='CAMERA':continue
        assert ob.parent is None and not ob.constraints
        cameras.append(dict(name=ob.name,collections=sorted(c.name for c in ob.users_collection),matrix_basis=[list(row) for row in ob.matrix_basis],
            camera_type=ob.data.type,lens_mm=ob.data.lens,sensor_width=ob.data.sensor_width,
            sensor_height=ob.data.sensor_height,sensor_fit=ob.data.sensor_fit,
            shift_x=ob.data.shift_x,shift_y=ob.data.shift_y,
            near=ob.data.clip_start,far=ob.data.clip_end))
    lights = []
    for ob in scene.objects:
        if ob.type!='LIGHT' or ob.name not in visible:continue
        record=dict(name=ob.name,type=ob.data.type,matrix_basis=[list(row) for row in ob.matrix_basis],
            color=list(ob.data.color),energy=ob.data.energy)
        for prop in ['size','size_y','shape','shadow_soft_size','angle','spread','normalize']:
            if hasattr(ob.data,prop):record[prop]=getattr(ob.data,prop)
        lights.append(record)
    shape_keys = []
    for ob in meshes:
        if not ob.data.shape_keys:continue
        keys=ob.data.shape_keys
        shape_keys.append(dict(object=ob.name,keys=[k.name for k in keys.key_blocks],
            action=keys.animation_data.action.name if keys.animation_data and keys.animation_data.action else None,
            modifiers=[m.type for m in ob.modifiers]))
    interactions = []
    for ob in authored:
        values={k:ob[k] for k in ob.keys() if any(word in k.lower() for word in ['interact','door','facility','state'])}
        if values:interactions.append(dict(object=ob.name,properties={k:str(v) for k,v in values.items()}))
    report=dict(version=version,native=str(native),native_sha256=digest,
        visible_authored_objects=len(authored),authored_types=dict(Counter(o.type for o in authored)),
        authored_polygons=sum(len(o.data.polygons) for o in meshes),
        authored_vertices=sum(len(o.data.vertices) for o in meshes),
        collections=collections,photo=photo_rows,
        photo_changed_nodes=[r['node'] for r in photo_rows if r['changed']],
        photo_empty_nodes=[r['node'] for r in photo_rows if r['empty']],
        photo_missing_nodes=sorted(set(originals)-{r['node'] for r in photo_rows}),
        materials=material_rows,cameras=cameras,lights=lights,shape_keys=shape_keys,
        interaction_markers=interactions,
        native_color=dict(view_transform=scene.view_settings.view_transform,look=scene.view_settings.look,
                          exposure=scene.view_settings.exposure,gamma=scene.view_settings.gamma),
        export_completed=False,runtime_same_version_verified=False,natural_use_verified=False,
        elapsed_seconds=time.time()-started)
    target=write_path(f'evidence/{version}/runtime_inventory.json')
    target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report,target


if __name__=='__main__':
    report,target=build_inventory()
    print('RUNTIME_INVENTORY',json.dumps({k:report[k] for k in
        ['version','visible_authored_objects','authored_polygons','authored_vertices','authored_types','elapsed_seconds']} |
        dict(photo_changed=len(report['photo_changed_nodes']),photo_empty=len(report['photo_empty_nodes']),
             cameras=len(report['cameras']),materials=len(report['materials']),file=str(target))),flush=True)
