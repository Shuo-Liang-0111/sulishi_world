"""Run through Blender MCP. This is a geospatial reference checkpoint, not final art."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector
import numpy as np

ROOT=Path('F:/MyWorld/ZurichWorld')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'native/G1_000_empty.blend'))
scene=bpy.context.scene
scene.name='Zurich_G1'
scene['origin_lv95_ln02']=[2683775.0,1246700.0,400.0]
scene['quality_status']='G1_001_geographic_reference_not_accepted'
scene['source_epoch']='evidence_fused_ordinary_built_state_see_planning_scene_spec'
scene.blendermcp_port=19876
scene.blendermcp_auto_start_server=True

def collection(name):
    c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
terrain_col=collection('01_SURVEY_TERRAIN_REFERENCE')
building_col=collection('02_SURVEY_LOD2_REFERENCE')
camera_col=collection('90_REVIEW_CAMERAS')

def mat(name,color,rough=0.75):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough
    return m
roofmat=mat('SURVEY roof | no finish inference',(0.42,0.37,0.33))
wallmat=mat('SURVEY wall | no facade detail yet',(0.69,0.67,0.60))
bottommat=mat('SURVEY sunk bottom | not floor',(0.25,0.25,0.25))
ortho=bpy.data.materials.new('SWISSIMAGE | reference only, baked shadows and cars')
ortho.use_nodes=True
nodes=ortho.node_tree.nodes;nodes.clear()
out=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');tex=nodes.new('ShaderNodeTexImage')
tex.image=bpy.data.images.load(str(ROOT/'sources/references/swissimage-context.jpg'),check_existing=True)
tex.extension='EXTEND'
ortho.node_tree.links.new(tex.outputs['Color'],em.inputs['Color'])
ortho.node_tree.links.new(em.outputs[0],out.inputs['Surface'])
base=json.loads((ROOT/'derived/G1_geo_base.json').read_text())
for item in base['objects']:
    mesh=bpy.data.meshes.new(item['id'])
    mesh.from_pydata(item['vertices'],[],item['faces']);mesh.update()
    obj=bpy.data.objects.new(item['id'],mesh)
    target=terrain_col if item['kind']=='terrain_reference' else building_col
    target.objects.link(obj)
    for key in ['kind','source','role','in_scope','floor_warning']:
        if key in item:obj[key]=item[key]
    if 'source_properties' in item:obj['source_properties']=json.dumps(item['source_properties'])
    if item['kind']=='terrain_reference':
        mesh.materials.append(ortho)
        layer=mesh.uv_layers.new(name='LV95_SWISSIMAGE_reference')
        coords=np.asarray(item['vertices'],dtype=float)
        xy=(coords[:,:2]+np.array([2683775,1246700])-np.array([2683420,1246300]))/np.array([780,810])
        uv=np.array([xy[l.vertex_index] for l in mesh.loops],dtype=np.float32)
        layer.data.foreach_set('uv',uv.ravel())
    else:
        for m in [roofmat,wallmat,bottommat]:mesh.materials.append(m)
        mesh.polygons.foreach_set('material_index',item['materials'])
        obj['collision_status']='not_accepted_survey_bottoms_are_sunk'

def camera(name,pos,target,lens=42,ortho_scale=None):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);camera_col.objects.link(o)
    o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    d.lens=lens;d.clip_start=.1;d.clip_end=5000
    if ortho_scale:d.type='ORTHO';d.ortho_scale=ortho_scale
    return o
overview=camera('QA_Whole_context_SW',(-590,-650,590),(0,35,15),43)
top=camera('QA_Topdown',(35,-5,1200),(35,-5,0),42,860)
# Exact vertical top camera orientation makes north point up.
top.rotation_euler=(0,0,0)
camera('QA_Plaza_1m65',(-131,-15,10.10),(-31,-60,14),32)
camera('QA_Station_approach_1m65',(9,40,10.50),(52,79,13),32)
sun_data=bpy.data.lights.new('Review daylight','SUN');sun_data.energy=2.0;sun_data.angle=math.radians(4)
sun=bpy.data.objects.new('Review daylight',sun_data);camera_col.objects.link(sun)
sun.rotation_euler=(math.radians(35),math.radians(-22),math.radians(-30))
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.42,.52,.65,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
scene.render.engine='CYCLES';scene.cycles.device='GPU';scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.view_settings.view_transform='AgX'
scene.camera=overview
scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.clip_end=5000
            area.spaces.active.region_3d.view_distance=600
            area.spaces.active.region_3d.view_location=Vector((0,0,20))
native=ROOT/'native/G1_001_geographic_reference.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(native))
(ROOT/'runtime/current_scene.json').write_text(json.dumps({'native':str(native),
    'stage':'geographic_reference','accepted':False,'objects':len(scene.objects)},indent=2),encoding='utf-8')
print(json.dumps({'native':str(native),'objects':len(scene.objects),'triangles':base['total_triangles'],
                  'quality':'source geometry only; human-height reconstruction pending'}))
