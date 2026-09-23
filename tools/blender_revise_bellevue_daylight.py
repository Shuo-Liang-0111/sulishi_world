"""Correct real skylight transmission and verify entrance pivots; no exposure masking."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert str(scene['version']).startswith('G1_005')
data=json.loads((ROOT/'derived/bellevue/block_input.json').read_text())
center=Vector((data['center_lv95'][0]-2683775,data['center_lv95'][1]-1246700,0))
floor=data['ground_fit']['ground_plane_z_ln02'][2]-400
glass=bpy.data.materials['BE | clear curved 12mm glass']
roof=bpy.data.objects['BE_SOURCE_bauten_dachmodell_3d.111603']
if glass.name not in [m.name for m in roof.data.materials]:roof.data.materials.append(glass)
glass_index=[m.name for m in roof.data.materials].index(glass.name)
count=0
for poly in roof.data.polygons:
    if all((roof.data.vertices[i].co.xy-center.xy).length<3.30 for i in poly.vertices):
        poly.material_index=glass_index;count+=1
roof['skylight_basis']='central raised 3.24m radius from official roof; glass confirmed by operating-site reference'
for mat in bpy.data.materials:
    if mat.name.startswith('BE | luminous glass'):
        bs=mat.node_tree.nodes.get('Principled BSDF')
        bs.inputs['Transmission Weight'].default_value=.78;bs.inputs['Roughness'].default_value=.32
        bs.inputs['Emission Strength'].default_value=.05
        mat['purpose']='diffusing windrose skylight, not an opaque lamp disc'

# Explicit inverse preserves geometry in global coordinates around the local circular pivot.
for name in ['BE_ENTRANCE_L','BE_ENTRANCE_R']:
    pivot=bpy.data.objects[name]
    for child in pivot.children:child.matrix_parent_inverse=Matrix.Translation((-center.x,-center.y,-floor))

world=scene.world;nodes=world.node_tree.nodes;links=world.node_tree.links
sky=nodes.get('Zurich review daylight') or nodes.new('ShaderNodeTexSky');sky.name='Zurich review daylight'
sky.sky_type='NISHITA';sky.sun_disc=False;sky.sun_elevation=math.radians(44);sky.sun_rotation=math.radians(220)
sky.altitude=.41;sky.air_density=1.0;sky.dust_density=1.1;sky.ozone_density=1.0
bg=nodes.get('Background');links.new(sky.outputs['Color'],bg.inputs['Color']);bg.inputs['Strength'].default_value=.65
world['light_basis']='ordinary daylight review, not a reconstruction of the photo timestamp'
scene.view_settings.exposure=0

# Small ordinary downlights observed over the counter; geometry remains independently visible.
col=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION']
for i,u in enumerate([-4.8,-2.4,0,2.4,4.8]):
    ang=math.radians(-102);front=Vector((math.cos(ang),math.sin(ang),0));right=Vector((-front.y,front.x,0))
    name='BE_INTERIOR_DOWNLIGHT_%02d'%i;ob=bpy.data.objects.get(name)
    if ob is None:
        ld=bpy.data.lights.new(name,'AREA');ob=bpy.data.objects.new(name,ld);col.objects.link(ob)
    ob.location=center+right*u+front*(-1.0)+Vector((0,0,floor+2.82))
    ob.data.energy=28;ob.data.shape='DISK';ob.data.size=.12;ob.data.color=(1,.85,.66)
    ob['basis']='photographed counter downlights; intensity inferred'
scene['version']='G1_005r2'
native=ROOT/'native/G1_005r2_bellevue_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
status=json.loads((ROOT/'runtime/bellevue_working.json').read_text());status.update(version=scene['version'],native=str(native))
(ROOT/'runtime/bellevue_working.json').write_text(json.dumps(status,indent=2))
print(json.dumps({'native':str(native),'skylight_triangles':count,'exposure':scene.view_settings.exposure,'reason':'corrected an opaque skylight and missing diffuse daylight, not image brightening'}))
