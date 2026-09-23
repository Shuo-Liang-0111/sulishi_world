"""Executed through MCP with START/END supplied by the batch builder."""
import bpy,json,struct
from pathlib import Path
import numpy as np
ROOT=Path('F:/MyWorld/ZurichWorld')
manifest=json.loads((ROOT/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
scene=bpy.context.scene
start=globals().get('START',0);end=globals().get('END',150)
col=bpy.data.collections.get('03_I3S_PHOTOGRAPHIC_REFERENCE')
if col is None:
    col=bpy.data.collections.new('03_I3S_PHOTOGRAPHIC_REFERENCE');scene.collection.children.link(col)
    col['role']='unmodified source photogrammetry; not close-range accepted geometry'
origin=np.array(manifest['origin_epsg2056_ln02'])
for item in manifest['items'][start:end]:
    name='I3S_'+item['node']
    if bpy.data.objects.get(name):continue
    raw=Path(item['geometry']).read_bytes();nv,nf=struct.unpack_from('<II',raw)
    coords=np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3)
    uv=np.frombuffer(raw,dtype='<f4',count=nv*2,offset=8+nv*12).reshape(-1,2).copy()
    uv[:,1]=1.0-uv[:,1]
    if not np.isfinite(coords).all() or not np.isfinite(uv).all():raise ValueError('Non-finite I3S node '+item['node'])
    mesh=bpy.data.meshes.new(name)
    mesh.vertices.add(nv);mesh.vertices.foreach_set('co',coords.ravel())
    mesh.loops.add(nv);mesh.loops.foreach_set('vertex_index',np.arange(nv,dtype=np.int32))
    mesh.polygons.add(nv//3)
    mesh.polygons.foreach_set('loop_start',np.arange(0,nv,3,dtype=np.int32))
    mesh.polygons.foreach_set('loop_total',np.full(nv//3,3,dtype=np.int32))
    mesh.update(calc_edges=True)
    layer=mesh.uv_layers.new(name='I3S_source_V_flipped_for_Blender')
    layer.data.foreach_set('uv',uv.ravel())
    obj=bpy.data.objects.new(name,mesh);col.objects.link(obj)
    obj.location=np.array(item['mbs'][:3])-origin
    obj['kind']='photogrammetry_reference';obj['source_node']=item['node']
    obj['source_layer']=manifest['name'];obj['geometry_sha256']=item['geometry_sha256']
    obj['texture_sha256']=item['texture_sha256'];obj['quality']='unmodified_source_not_accepted'
    obj['interaction']='none; source geometry is not validated collision'
    mat=bpy.data.materials.new(name+'_source_color');mat.use_nodes=True
    nodes=mat.node_tree.nodes;nodes.clear()
    output=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission')
    tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(item['texture'],check_existing=True)
    tex.image.colorspace_settings.name='sRGB'
    mat.node_tree.links.new(tex.outputs['Color'],em.inputs['Color'])
    mat.node_tree.links.new(em.outputs[0],output.inputs['Surface'])
    mat['purpose']='source RGB diagnostic; baked photo illumination, not final PBR'
    mesh.materials.append(mat)
for name in ['01_SURVEY_TERRAIN_REFERENCE','02_SURVEY_LOD2_REFERENCE']:
    bpy.data.collections[name].hide_render=True
    bpy.data.collections[name].hide_viewport=True
scene.camera=bpy.data.objects['QA_Whole_context_SW']
loaded=len(col.objects);complete=loaded==manifest['leaf_count']
scene['photogrammetry_nodes_loaded']=loaded
scene['photogrammetry_nodes_expected']=manifest['leaf_count']
scene['quality_status']='unmodified_photogrammetry_reference_not_accepted'
scene['version']='G1_004' if complete else 'G1_004_working'
name='G1_004_photogrammetry_reference.blend' if complete else 'G1_004_photogrammetry_working.blend'
native=ROOT/'native'/name
bpy.ops.wm.save_as_mainfile(filepath=str(native))
bpy.ops.file.make_paths_relative()
bpy.ops.wm.save_as_mainfile(filepath=str(native))
old=json.loads((ROOT/'runtime/current_scene.json').read_text())
record={'native':str(native),'version':scene['version'],'stage':'photogrammetry_reference',
        'accepted':False,'loaded_nodes':loaded,'expected_nodes':manifest['leaf_count'],
        'source_import_complete':complete,'survey_glb':old.get('survey_glb'),
        'viewer_version':'G1_003r2','viewer_note':'survey comparison is from the prior geographic checkpoint; photo export pending'}
(ROOT/'runtime/current_scene.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({'loaded_nodes':loaded,'expected_nodes':manifest['leaf_count'],
                  'source_import_complete':complete,'native':str(native)}))
