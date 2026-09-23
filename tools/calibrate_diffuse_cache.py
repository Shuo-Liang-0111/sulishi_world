"""Small independent radiometric check for the static-diffuse composition."""
import bpy,json
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld')
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=8
s.render.threads_mode='FIXED';s.render.threads=2
s.world=bpy.data.worlds.new('CALIBRATION_CONSTANT_WORLD');s.world.use_nodes=True
background=s.world.node_tree.nodes.get('Background');background.inputs['Color'].default_value=(1,1,1,1);background.inputs['Strength'].default_value=.6
me=bpy.data.meshes.new('CALIBRATION_QUAD');me.from_pydata([(-1,-1,0),(1,-1,0),(1,1,0),(-1,1,0)],[],[(0,1,2,3)]);me.update()
uv=me.uv_layers.new(name='UVMap')
for li,coord in enumerate([(0,0),(1,0),(1,1),(0,1)]):uv.data[li].uv=coord
ob=bpy.data.objects.new('CALIBRATION_QUAD',me);s.collection.objects.link(ob);ob.select_set(True);bpy.context.view_layer.objects.active=ob
mat=bpy.data.materials.new('CALIBRATION_DIFFUSE');mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');bsdf=nodes.new('ShaderNodeBsdfDiffuse');bsdf.inputs['Color'].default_value=(.3,.5,.8,1);mat.node_tree.links.new(bsdf.outputs[0],out.inputs['Surface'])
image=bpy.data.images.new('CALIBRATION_BAKE',width=16,height=16,alpha=False,float_buffer=True);image.colorspace_settings.name='Linear Rec.709';target=nodes.new('ShaderNodeTexImage');target.image=image;nodes.active=target;me.materials.append(mat)
s.render.bake.use_pass_direct=True;s.render.bake.use_pass_indirect=True;s.render.bake.use_pass_color=False;s.render.bake.use_clear=True;s.render.bake.margin=0
assert 'FINISHED' in bpy.ops.object.bake(type='DIFFUSE',uv_layer='UVMap')
pixel=list(image.pixels[(8*16+8)*4:(8*16+8)*4+3])
assert all(abs(value-.6)<.002 for value in pixel),pixel
report={'test':'Unit-diffuse radiance without base colour under constant0.6 environment','measured_linear_rgb':pixel,'expected_linear_rgb':[.6,.6,.6],
 'conclusion':'DIFFUSE bake with colour disabled returns irradiance/pi. Multiply by diffuse base colour once; do not apply another1/pi.','native_world_not_loaded_or_modified':True}
p=R/'evidence/runtime_diffuse_calibration.json';p.write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
