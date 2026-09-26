"""Export all current authored regions and exact leaves into a review candidate.

Material conversion gaps are explicit. This never replaces the public version,
never edits/saves the native scene, and never reimports an old author snapshot.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import time
import bpy
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path,validate_native
from blender_pack_current_leaves import pack_leaf


def file_sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


scene=bpy.context.scene;version=scene['version'];assert version=='G1_027r15'
native=validate_native(bpy.data.filepath);native_stat=native.stat();native_sha=file_sha(native)
inventory=json.loads(read_path(f'evidence/{version}/runtime_inventory.json').read_text())
routes=json.loads(read_path(f'derived/runtime_current/{version}/material_routes.json').read_text())
assert inventory['native_sha256']==routes['native_sha256']==native_sha
assert inventory['authored_roots']==['10_BELLEVUE_RECONSTRUCTION','SF1_AUTHOR_ENTRANCE']
folder=write_path(f'web/assets/{version}_current_r01/manifest.json').parent
assert shutil.disk_usage(folder).free>15*1024**3,'Current-world candidate needs at least 15 GiB on the active output volume.'
manifest_file=folder/'manifest.json';assert not manifest_file.exists(),'Previous attempt must be reviewed, not overwritten.'
expected_dir=write_path(f'derived/runtime_current/{version}/author_expected_r01/.keep').parent
originals={name:bpy.data.objects[name] for name in inventory['visible_authored_object_names']}
geometry={name:ob for name,ob in originals.items() if ob.type in ['MESH','CURVE','FONT','EMPTY']}
leaf_names={name for m in routes['materials'] if 'subsurface_scattering' in m['special_handling'] for name in m['objects']}
assert len(leaf_names)==50 and leaf_names<=set(geometry)
roots=[bpy.data.collections[name] for name in inventory['authored_roots']]
ownership={};groups=[]
for root in roots:
    for collection in [root,*list(root.children_recursive)]:
        names=sorted(ob.name for ob in collection.objects if ob.name in geometry and ob.name not in leaf_names)
        for name in names:
            assert name not in ownership,('Multi-collection author requires explicit ownership',name)
            ownership[name]=collection.name
        if names:groups.append((collection.name,names))
assert set(ownership)|leaf_names==set(geometry)
report={'version':version,'native_sha256':native_sha,'process_id':os.getpid(),'status':'exporting_review_candidate',
        'authored_roots':inventory['authored_roots'],'expected_geometry_objects':len(geometry),'expected_geometry_names':sorted(geometry),
        'chunks':[],'leaves':[],'camera_inventory':inventory['cameras'],'lights':inventory['lights'],
        'native_color':inventory['native_color'],'shape_keys':inventory['shape_keys'],
        'material_routes_summary':routes['summary'],'materials_fully_converted':False,'full_runtime_published':False,'natural_use_verified':False}
def save_report():manifest_file.write_text(json.dumps(report,indent=2),encoding='utf-8')
save_report();deps=bpy.context.evaluated_depsgraph_get()
for index,name in enumerate(sorted(leaf_names)):
    result=pack_leaf(geometry[name],folder/'leaves',version,native_sha)
    report['leaves'].append({'name':name,'metadata':'leaves/'+name+'.json','bytes':result['bytes'],'sha256':result['sha256'],
                             'vertices':result['source_vertex_count'],'triangles':result['source_triangle_count']})
    save_report();print('CURRENT_LEAF_EXPORTED',index+1,len(leaf_names),name,result['bytes'],flush=True)

for group_index,(collection_name,names) in enumerate(groups):
    target=folder/f'part_{group_index:02d}.glb';expected_file=expected_dir/f'part_{group_index:02d}.npz'
    assert not target.exists() and not expected_file.exists()
    temporary=bpy.data.collections.new('TEMP_CURRENT_AUTHOR_EXPORT');scene.collection.children.link(temporary)
    created=[];meshes=[];mapping={};expected={};records=[]
    try:
        for object_index,name in enumerate(names):
            ob=geometry[name];ev=ob.evaluated_get(deps);mesh=None
            if ob.type!='EMPTY':
                if ob.type=='MESH' and ob.data.shape_keys:
                    assert ob.name=='F59_WATER_SURFACE' and not ob.modifiers
                    mesh=ob.data.copy();assert mesh.shape_keys and mesh.shape_keys.animation_data.action
                else:mesh=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=deps)
                meshes.append(mesh);mesh.calc_loop_triangles()
                xyz=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',xyz)
                triangles=np.empty(len(mesh.loop_triangles)*3,np.int32);mesh.loop_triangles.foreach_get('vertices',triangles)
                triangle_loops=np.empty(len(mesh.loop_triangles)*3,np.int32);mesh.loop_triangles.foreach_get('loops',triangle_loops)
                normals=np.empty(len(mesh.corner_normals)*3,np.float32);mesh.corner_normals.foreach_get('vector',normals)
                material_ids=np.empty(len(mesh.loop_triangles),np.int32);mesh.loop_triangles.foreach_get('material_index',material_ids)
                key=f'o{object_index:04d}'
                expected[key+'_positions']=xyz.reshape(-1,3);expected[key+'_triangles']=triangles.reshape(-1,3)
                expected[key+'_triangle_loops']=triangle_loops.reshape(-1,3)
                expected[key+'_corner_normals']=normals.reshape(-1,3)
                if mesh.shape_keys:
                    expected[key+'_export_basis_normals']=np.asarray(mesh.shape_keys.key_blocks[0].normals_split_get(),np.float32).reshape(-1,3)
                expected[key+'_triangle_materials']=material_ids
                expected[key+'_matrix']=np.asarray(ev.matrix_world,dtype=np.float64)
                for uv_index,uv_layer in enumerate(mesh.uv_layers):
                    uv=np.empty(len(uv_layer.data)*2,np.float32);uv_layer.data.foreach_get('uv',uv)
                    expected[key+f'_uv{uv_index}']=uv.reshape(-1,2)
                records.append({'name':name,'key':key,'vertices':len(mesh.vertices),'triangles':len(mesh.loop_triangles),
                                'uv_layers':[layer.name for layer in mesh.uv_layers],
                                'materials':[slot.material.name if slot.material else None for slot in ob.material_slots]})
            dup=bpy.data.objects.new('RT_'+name,mesh);temporary.objects.link(dup);created.append(dup);mapping[name]=dup
            dup.matrix_world=ev.matrix_world.copy()
            for key,value in ob.items():dup[key]=value
            dup['native_object']=name;dup['construction_version']=version
            if ob.parent:dup['native_parent']=ob.parent.name
        for name,dup in mapping.items():
            ob=geometry[name]
            if ob.parent and ob.parent.name in mapping:
                world=dup.matrix_world.copy();dup.parent=mapping[ob.parent.name];dup.matrix_world=world
        bpy.context.view_layer.update()
        for ob in scene.objects:ob.select_set(False)
        for ob in created:ob.select_set(True)
        animation=any(geometry[name].type=='MESH' and geometry[name].data.shape_keys for name in names)
        bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_extras=True,
            export_yup=True,export_apply=False,export_materials='EXPORT',export_cameras=False,export_lights=False,
            export_tangents=True,export_animations=animation,export_morph=True,
            export_animation_mode='ACTIVE_ACTIONS',export_frame_range=False,export_anim_slide_to_zero=True,
            export_force_sampling=True,export_nla_strips_merged_animation_name='F59_CONTINUOUS_WATER')
        np.savez_compressed(expected_file,**expected)
        report['chunks'].append({'collection':collection_name,'file':target.name,'bytes':target.stat().st_size,
            'sha256':file_sha(target),'native_objects':names,'expected_file':str(expected_file),'expected_sha256':file_sha(expected_file),
            'geometry':records,'contains_native_water_animation':animation,'material_conversion_verified':False})
        save_report();print('CURRENT_AUTHOR_CHUNK_EXPORTED',group_index+1,len(groups),collection_name,len(names),target.stat().st_size,flush=True)
    finally:
        for ob in created:bpy.data.objects.remove(ob,do_unlink=True)
        for mesh in meshes:
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        bpy.data.collections.remove(temporary)
    assert native.stat().st_size==native_stat.st_size and native.stat().st_mtime_ns==native_stat.st_mtime_ns
assert file_sha(native)==native_sha
report['status']='geometry_candidate_exported_material_review_pending';report['native_unmodified']=True
report['total_bytes']=sum(r['bytes'] for r in report['chunks'])+sum(r['bytes'] for r in report['leaves'])
save_report()
write_path(f'evidence/{version}/current_author_candidate_export.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('CURRENT_AUTHOR_CANDIDATE_EXPORTED_NOT_PUBLISHED',json.dumps({'chunks':len(report['chunks']),'leaf_objects':len(report['leaves']),'bytes':report['total_bytes']}),flush=True)
