"""Complete visible overflow connection and improve the cast's surface/detail."""
import bpy,bmesh,json,ast,math
import numpy as np
from mathutils import Vector
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/fountain59';scene=bpy.context.scene;assert scene['version']=='G1_018r1'
d=json.loads((D/'input.json').read_text());root=bpy.data.objects['F59_ROOT'];collection=bpy.data.collections['27_BELLEVUE_FOUNTAIN_59']
tree=ast.parse((R/'tools/blender_build_fountain59.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','lathe','unit','add_tube','tube_object','ellipsoid']],type_ignores=[]),'fountain_helpers','exec'))
silver=bpy.data.materials['F59 | weathered chromium silver'];pipe_metal=bpy.data.materials['F59 | worn polished outlet'];recess=bpy.data.materials['F59 | sheltered casting recess']
for name in ['F59_OVERFLOW_PERFORATED_SHELL','F59_OVERFLOW_ROLLED_TOP','F59_OVERFLOW_CAP']:
    bpy.data.objects[name].location.z=-.012
lathe('F59_OVERFLOW_RISER',[(.045,.306),(.052,.306),(.052,.697),(.045,.697),(.045,.306)],pipe_metal,96)
lathe('F59_DRAIN_FLANGE',[(.044,.309),(.076,.309),(.078,.312),(.074,.315),(.044,.315),(.044,.309)],pipe_metal,96)
for i in range(3):
    cast=bpy.data.objects[f'F59_SCULPTURE_{i+1}'];v=[];f=[]
    for sign in [-1,1]:
        ellipsoid(v,f,[-.249,sign*.048,.136],[.011,.006,.011])
        circle=[[-.249+.013*math.cos(t),sign*.049,.136+.013*math.sin(t)] for t in np.linspace(0,2*math.pi,49)]
        add_tube(v,f,circle,.00115,8)
    mesh(f'F59_{i}_BULGING_FISH_EYES',v,f,pipe_metal,parent=cast)
    v=[];f=[]
    for sign in [-1,1]:ellipsoid(v,f,[-.249,sign*.0545,.136],[.0055,.0014,.0055])
    mesh(f'F59_{i}_FISH_IRIS_RELIEF',v,f,recess,parent=cast)
    v=[];f=[]
    pts=[(.073,.0,.112),(.090,.0,.160),(.137,.0,.170),(.168,.0,.148),(.174,.0,.102)]
    for off in [-.0018,.0018]:v.extend([(x,y+off,z) for x,y,z in pts])
    f.extend([tuple(reversed(range(5))),tuple(range(5,10))])
    for j in range(5):f.append((j,(j+1)%5,(j+1)%5+5,j+5))
    fin=mesh(f'F59_{i}_DORSAL_FIN',v,f,silver,parent=cast);mod=fin.modifiers.new('Cast fin edge radius','BEVEL');mod.width=.0012;mod.segments=3
    v=[];f=[]
    for sign in [-1,1]:
        for t in np.linspace(0,1,9):
            add_tube(v,f,[(.085+.07*t,sign*.002,.111),(.092+.054*t,sign*.0026,.144),(.096+.048*t,sign*.002,.160)],.00055,6)
    mesh(f'F59_{i}_DORSAL_FLUTING',v,f,pipe_metal,parent=cast)
    for suffix in ['CAST_FINS']:
        ob=bpy.data.objects[f'F59_{i}_{suffix}'];mod=ob.modifiers.new('Small rounded cast edges','BEVEL');mod.width=.001;mod.segments=3

# Export-friendly image roughness variation, in actual local metres.
texture=silver.node_tree.nodes.new('ShaderNodeTexImage');texture.image=bpy.data.images.load(str(D/'textures/chrome_cast_roughness.png'),check_existing=True);texture.image.colorspace_settings.name='Non-Color';silver.node_tree.links.new(texture.outputs['Color'],silver.node_tree.nodes.get('Principled BSDF').inputs['Roughness'])
silver['roughness_basis']='Original0.16m tile, bounded0.185..0.40; mottled wear inferred from inspected casting image. Not an alloy identification.'
for ob in collection.objects:
    if ob.type=='MESH' and silver in ob.data.materials[:]:
        uv=ob.data.uv_layers.active or ob.data.uv_layers.new(name='cast_surface_metre_coordinates')
        for loop in ob.data.loops:
            p=ob.data.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(p.x/.16,(p.y+p.z*.63)/.16)

scene.frame_set(1);scene['version']='G1_018r2';bpy.context.view_layer.update();E=R/'evidence/G1_018r2';E.mkdir(exist_ok=True)
report={'version':scene['version'],'new_objects':len(collection.objects),'drain_riser_range':[.306,.697],'collar_bottom':.692,'water_level':.707,'lowest_hole_center_world_local':.701,'visible_connection_inferred':True,'material_roughness_tile_m':.16,'dimension_anchor_preserved':True,'visual_and_use_accepted':False}
(E/'connections.json').write_text(json.dumps(report,indent=2))
native=R/'native/G1_018r2_fountain_connections_working.blend';bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=scene['version'],native=str(native),accepted=False,not_published=True,next='Render native fountain alone in memory; inspect all four actual views, then prepare matching runtime.');(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2))
print(json.dumps(report))
