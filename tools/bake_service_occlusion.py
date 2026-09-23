"""Bake geometry-derived indirect occlusion without altering the native project.

An evaluated, joined receiver is used only to pack an additional UV channel.
Per-object loop UVs are mapped back by exact topology hashes at export. Base
color, roughness, normal maps, source geometry and native modifiers stay intact.
This finite-distance AO is an approximation, not a complete GI/lightmap bake.
"""
import bpy
import json
import math
import hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector

R = Path('F:/MyWorld/ZurichWorld')
s = bpy.context.scene
V = s['version']
assert V == 'G1_015r1'
OUT = R/'derived/runtime_occlusion'/V
OUT.mkdir(parents=True, exist_ok=True)
s.render.engine = 'CYCLES'
s.cycles.device = 'CPU'
s.cycles.samples = 48
s.render.threads_mode = 'FIXED'
s.render.threads = 10
s.render.use_persistent_data = False
assert 'EMIT' in {x.identifier for x in bpy.ops.object.bake.get_rna_type().properties['type'].enum_items}
assert 'IMAGE_TEXTURES' in {x.identifier for x in s.render.bake.bl_rna.properties['target'].enum_items}
assert 'PNG' in {x.identifier for x in s.render.image_settings.bl_rna.properties['file_format'].enum_items}

def mesh_arrays(me):
    v=np.empty(len(me.vertices)*3,np.float32);me.vertices.foreach_get('co',v)
    ids=np.empty(len(me.loops),np.int32);me.loops.foreach_get('vertex_index',ids)
    h=hashlib.sha256(v.tobytes()+ids.tobytes()).hexdigest()
    return v.reshape(-1,3),ids,h

def transmissive(ob):
    for mat in ob.data.materials:
        if not mat or not mat.use_nodes:continue
        for n in mat.node_tree.nodes:
            if n.type=='BSDF_TRANSPARENT':return True
            if n.type=='BSDF_PRINCIPLED' and n.inputs.get('Transmission Weight') and n.inputs['Transmission Weight'].default_value>.1:return True
    return False

def moving(ob):
    while ob:
        role=str(ob.get('interaction_role','')).lower()
        if any(t in role for t in ['hinge','door','sliding']):return True
        ob=ob.parent
    return False

authored=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION']
receivers=[o for o in authored.all_objects if o.type=='MESH' and
           (o.name.startswith('SV_') or o.name in ['BS_ASPHALT','BS_SOIL','BS_TREE_PIT_EXPOSED_ASPHALT_EDGES'])
           and not transmissive(o) and not moving(o)]
receivers.sort(key=lambda o:o.name)
assert len(receivers)>100
bpy.context.view_layer.update()
deps=bpy.context.evaluated_depsgraph_get()
vertices=[];faces=[];smooth=[];records=[];loop_start=0
for ob in receivers:
    evaluated=ob.evaluated_get(deps);me=evaluated.to_mesh()
    vv,ids,digest=mesh_arrays(me)
    transformed=vv@np.asarray(ob.matrix_world,dtype=np.float64)[:3,:3].T+np.asarray(ob.matrix_world.translation)
    offset=len(vertices);vertices.extend(transformed.tolist())
    faces.extend([tuple(int(i)+offset for i in p.vertices) for p in me.polygons])
    smooth.extend(p.use_smooth for p in me.polygons)
    records.append({'name':ob.name,'topology_sha256':digest,'loops':len(me.loops),'loop_start':loop_start,'vertices':len(me.vertices)})
    loop_start+=len(me.loops);evaluated.to_mesh_clear()
    ob.hide_render=True

collection=bpy.data.collections.new('TEMP_OCCLUSION_RECEIVER');s.collection.children.link(collection)
me=bpy.data.meshes.new('TEMP_SERVICE_AO_UV');me.from_pydata(vertices,[],faces);me.update()
del vertices,faces
me.polygons.foreach_set('use_smooth',smooth)
uv=me.uv_layers.new(name='runtime_indirect_occlusion')
ob=bpy.data.objects.new('TEMP_SERVICE_AO_RECEIVER',me);collection.objects.link(ob)
for obj in s.objects:obj.select_set(False)
ob.select_set(True);bpy.context.view_layer.objects.active=ob
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(70),island_margin=.00015,area_weight=.5,correct_aspect=True,scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT')
assert len(me.loops)==loop_start
uv=me.uv_layers['runtime_indirect_occlusion']
uvs=np.empty(len(me.loops)*2,np.float32);uv.data.foreach_get('uv',uvs);uvs=uvs.reshape(-1,2)
assert np.isfinite(uvs).all() and uvs.min()>=-.00001 and uvs.max()<=1.00001
print('AO_RECEIVERS',len(receivers),'LOOPS',loop_start,flush=True)

# AO only evaluates geometry. Avoid allocating all photographic/PBR textures for
# this scalar visibility calculation; keep every opaque occluder's exact mesh.
white=bpy.data.materials.new('TEMP_AO_OPAQUE');white.use_nodes=True
ignored=[]
for item in list(s.objects):
    if item==ob or item.type not in ['MESH','CURVE','FONT']:continue
    if item.hide_render:continue
    if transmissive(item) or moving(item):
        item.hide_render=True;ignored.append(item.name);continue
    item.data.materials.clear();item.data.materials.append(white)
    if item.type=='MESH':
        for p in item.data.polygons:p.material_index=0

mat=bpy.data.materials.new('TEMP_AO_EMISSION');mat.use_nodes=True
ns=mat.node_tree.nodes;ns.clear();links=mat.node_tree.links
output=ns.new('ShaderNodeOutputMaterial');emit=ns.new('ShaderNodeEmission')
ao=ns.new('ShaderNodeAmbientOcclusion');ao.inputs['Distance'].default_value=16.;ao.samples=32
links.new(ao.outputs['AO'],emit.inputs['Color']);links.new(emit.outputs[0],output.inputs['Surface'])
tex=ns.new('ShaderNodeTexImage');tex.image=bpy.data.images.new('SERVICE_INDIRECT_OCCLUSION',width=4096,height=4096,alpha=False,float_buffer=False)
tex.image.colorspace_settings.name='Non-Color';ns.active=tex
me.materials.clear();me.materials.append(mat)
for face in me.polygons:face.material_index=0
assert all(me.materials[p.material_index]==mat for p in me.polygons)
s.render.bake.target='IMAGE_TEXTURES';s.render.bake.margin=2;s.render.bake.use_clear=True
assert 'FINISHED' in bpy.ops.object.bake(type='EMIT')
image_path=OUT/'service_indirect_occlusion.png';tex.image.filepath_raw=str(image_path);tex.image.file_format='PNG';tex.image.save()
arrays={}
for i,rec in enumerate(records):
    key=f'uv_{i}';rec['uv_key']=key
    start=rec['loop_start'];arrays[key]=uvs[start:start+rec['loops']]
np.savez_compressed(OUT/'receiver_uv.npz',**arrays)
report={'version':V,'native':bpy.data.filepath,'receivers':records,'image':str(image_path.relative_to(R)),
        'uv_file':str((OUT/'receiver_uv.npz').relative_to(R)),
        'image_sha256':hashlib.sha256(image_path.read_bytes()).hexdigest(),
        'distance_m':16,'samples':48,'resolution':[4096,4096],
        'transparent_and_moving_occluders_excluded':ignored,
        'source_geometry_changed':False,'native_saved':False,'visual_review_passed':False,
        'limitation':'Finite-distance static AO for indirect lighting; not full GI, not a replacement for dynamic shadows or local reflections.'}
(OUT/'manifest.json').write_text(json.dumps(report,indent=2))
print('AO_BAKE_FINISHED',V,len(records),image_path,flush=True)
