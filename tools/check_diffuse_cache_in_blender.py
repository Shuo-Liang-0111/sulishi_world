"""Render the exported radiance cache with Blender's own linear colour pipeline."""
import bpy,json
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld')
script=(R/'tools/bake_service_diffuse.py').read_text()
exec(compile(script.split("print('DIFFUSE_BAKE_START'")[0],'temporary_bake_geometry','exec'))
cache=bpy.data.images.load(str(R/'web/assets/G1_015r3_service_diffuse.hdr'),check_existing=False)
cache.colorspace_settings.name='Linear Rec.709'
for mat in receiver.data.materials:
    ns=mat.node_tree.nodes;links=mat.node_tree.links
    bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED');out=next(n for n in ns if n.type=='OUTPUT_MATERIAL')
    uv=ns.new('ShaderNodeUVMap');uv.uv_map='runtime_indirect_occlusion'
    tex=ns.new('ShaderNodeTexImage');tex.image=cache;links.new(uv.outputs['UV'],tex.inputs['Vector'])
    product=ns.new('ShaderNodeMixRGB');product.blend_type='MULTIPLY';product.inputs[0].default_value=1
    links.new(tex.outputs['Color'],product.inputs[1])
    base=bs.inputs['Base Color']
    if base.is_linked:links.new(base.links[0].from_socket,product.inputs[2])
    else:product.inputs[2].default_value=base.default_value
    emission=ns.new('ShaderNodeEmission');links.new(product.outputs[0],emission.inputs['Color']);links.new(emission.outputs[0],out.inputs['Surface'])
s.camera=camera;s.cycles.samples=16;s.cycles.use_denoising=True
if hasattr(s.cycles,'denoising_use_gpu'):s.cycles.denoising_use_gpu=False
s.render.resolution_x=1280;s.render.resolution_y=840;s.render.resolution_percentage=100
s.render.image_settings.file_format='PNG';s.render.filepath=str(R/'evidence/G1_015r3/diffuse_cache_blender_comparison.png')
bpy.context.view_layer.update();assert 'FINISHED' in bpy.ops.render.render(write_still=True)
print('DIFFUSE_CACHE_BLENDER_COMPARISON_DONE',flush=True)
