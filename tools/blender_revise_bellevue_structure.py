"""G1_005r3: repair evidence-visible roof and physical support issues locally."""
import bpy,bmesh,json,math,ast
from pathlib import Path
import numpy as np
from mathutils import Vector,Matrix
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene.get('version') in ['G1_005r2','G1_005r3']
data=json.loads((ROOT/'derived/bellevue/block_input.json').read_text())
detail=json.loads((ROOT/'derived/bellevue/roof_detail.json').read_text())
C=np.array(data['center_lv95'])-np.array(data['origin'][:2]);FLOOR=data['ground_fit']['ground_plane_z_ln02'][2]-400
angle=math.radians(-102);front=np.array([math.cos(angle),math.sin(angle)]);right=np.array([-front[1],front[0]])
building=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION']
# Reuse only pure geometry definitions; never execute the initial builder's scene reset.
tree=ast.parse((ROOT/'tools/blender_build_bellevue.py').read_text())
functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['P','mesh','triangles','box','lathe','arc','tube','material']]
exec(compile(ast.Module(body=functions,type_ignores=[]),'bellevue_geometry_helpers','exec'))
roofmat=bpy.data.materials['BE | folded grey metal roof'];plaster=bpy.data.materials['BE | warm pale painted soffit']
aluminium=bpy.data.materials['BE | satin anodised aluminium'];darkmetal=bpy.data.materials['BE | dark structural metal']
countermetal=bpy.data.materials['BE | stainless counter'];glass=bpy.data.materials['BE | clear curved 12mm glass']
dark=bpy.data.materials['BE | dark counter plinth']
def remove(name):
    ob=bpy.data.objects.get(name)
    if ob:bpy.data.objects.remove(ob,do_unlink=True)
def replace(name,tt,mat,basis):
    remove(name);return triangles(name,tt,mat,basis)

bs=roofmat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.42,.435,.435,1)
bs.inputs['Metallic'].default_value=.48;bs.inputs['Roughness'].default_value=.58
for item in detail['refinements']:replace('BE_SOURCE_'+item['id'],item['triangles'],plaster,item['basis'])
replace('BE_SKYLIGHT_SURVEYED_RIM',detail['skylight_rim_triangles'],aluminium,'Official upper rim polygons from source 187305; underground closure excluded')
for i,plate in enumerate(detail['plates']):replace('BE_ROOF_COLUMN_PLATE_%02d'%i,plate['triangles'],roofmat,plate['basis'])
for ob in list(building.objects):
    if ob.name.startswith('BE_ROOF_STANDING_SEAM_'):bpy.data.objects.remove(ob,do_unlink=True)
for i,points in enumerate(detail['seams']):
    ob=tube('BE_ROOF_STANDING_SEAM_%03d'%i,points,.006,roofmat)
    ob['evidence_basis']='Radial roof seams visible in original aerial; spacing and fold profile inferred'

# Left and right retract away from the centre into the fixed curved glazing.
for name,sign in [('BE_ENTRANCE_L',-1),('BE_ENTRANCE_R',1)]:
    pivot=bpy.data.objects[name];pivot['open_rotation_z']=sign*math.radians(20)
    pivot.rotation_euler.z=pivot['open_rotation_z'];pivot['state']='open'
    for child in pivot.children:child.matrix_parent_inverse=Matrix.Translation((-C[0],-C[1],-FLOOR))
glass.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.012
for ob in building.objects:
    if ob.type=='MESH' and ('GLASS' in ob.name or ob.name.startswith('BE_WINDROSE_')):
        # Smooth only cylindrical side walls; top and edge caps keep their real flat normals.
        for face in ob.data.polygons:face.use_smooth=abs(face.normal.z)<.1

# Appliances must be supported by real joinery. Relocation is a local interior inference.
delta=Vector((front[0]*2.15,front[1]*2.15,0))
for ob in building.objects:
    if ob.name.startswith('BE_ESPRESSO_') and not ob.get('support_repaired'):
        ob.location+=delta;ob['support_repaired']=True
for name in ['BE_SERVICE_CABINET','BE_SERVICE_WORKTOP','BE_SERVICE_PLINTH','BE_BAR_TOP']:
    remove(name)
box('BE_SERVICE_PLINTH',(-1.15,2.55,.055),(.88,.68,.11),dark)
box('BE_SERVICE_CABINET',(-1.15,2.55,.565),(1.02,.78,.91),countermetal)
box('BE_SERVICE_WORKTOP',(-1.15,2.55,1.06),(1.08,.84,.08),countermetal)
arc('BE_BAR_TOP',2.65,3.69,1.035,1.09,-105,105,countermetal,step=2)
# Display case's rear edge now lies completely on the curved worktop.
case_delta=Vector((front[0]*.24,front[1]*.24,0))
for ob in building.objects:
    if ob.name.startswith(('BE_DISPLAY_CASE','BE_DISPLAY_GLASS')) and not ob.get('support_repaired'):
        ob.location+=case_delta;ob['support_repaired']=True

# Minimal real recessed housings for the existing documented downlights.
for i,u in enumerate([-4.8,-2.4,0,2.4,4.8]):
    for suffix in ['TRIM','LENS']:remove('BE_DOWNLIGHT_%02d_%s'%(i,suffix))
    lathe('BE_DOWNLIGHT_%02d_TRIM'%i,[(.072,2.94),(.072,2.965),(.056,2.965),(.056,2.94)],aluminium,(u,-1),32)
    lightmat=material('BE | opal luminaire',(.88,.87,.81),.32)
    lightmat.node_tree.nodes.get('Principled BSDF').inputs['Emission Color'].default_value=(1,.85,.66,1)
    lightmat.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=1
    lathe('BE_DOWNLIGHT_%02d_LENS'%i,[(0,2.943),(.056,2.943)],lightmat,(u,-1),32)
scene['version']='G1_005r3';scene['quality_status']='local structure corrections; full G1 still incomplete'
native=ROOT/'native/G1_005r3_bellevue_working.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(native))
status=json.loads((ROOT/'runtime/bellevue_working.json').read_text());status.update(version=scene['version'],native=str(native),new_objects=len(building.objects))
(ROOT/'runtime/bellevue_working.json').write_text(json.dumps(status,indent=2))
print(json.dumps({'version':scene['version'],'native':str(native),'roof_plates':len(detail['plates']),'seams':len(detail['seams']),'door_rotations':{n:bpy.data.objects[n].rotation_euler.z for n in ['BE_ENTRANCE_L','BE_ENTRANCE_R']}}))
