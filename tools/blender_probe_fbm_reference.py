"""Render actual installed native noise nodes as emission samples, read-only."""
from pathlib import Path
import hashlib
import json
import os
import sys
import bpy
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path,validate_native

original=bpy.context.scene
version=original['version'];assert version=='G1_027r15'
native=validate_native(bpy.data.filepath)
with native.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
out=write_path(f'evidence/{version}/native_fbm_reference_r02.json');assert not out.exists()
source=bpy.data.materials['UF | warm mottled limestone 0']
coarse=source.node_tree.nodes['Noise Texture'];fine=source.node_tree.nodes['Noise Texture.001']
parameters=[]
for label,node in [('native_facade_colour',coarse),('native_facade_bump',fine)]:
    assert node.noise_type=='FBM' and node.noise_dimensions=='3D' and node.inputs['Distortion'].default_value==0
    parameters.append({'label':label,'scale':node.inputs['Scale'].default_value,'detail':node.inputs['Detail'].default_value,
        'roughness':node.inputs['Roughness'].default_value,'lacunarity':node.inputs['Lacunarity'].default_value,'normalize':node.normalize})
parameters += [dict(label='fractional_detail',scale=2.3,detail=2.75,roughness=.61,lacunarity=2.,normalize=True),
               dict(label='signed_non_normalized',scale=1.7,detail=1.5,roughness=.33,lacunarity=2.,normalize=False)]
positions=[[0.,0.,0.],[.17,.31,.53],[-.37,.19,-.83],[1.23,-4.56,7.89],[-225.541,123.797,7.93],
 [11.134,19.369,17.431],[.00013,-.00021,.00034],[29.193,0.,-31.447],[-100001.1,100001.3,.47],
 [1000001.,-1000003.,.125],[-.9999,1.0001,0.5],[15.917,-8.723,2.453]]
samples=[{'parameters':p,'position':v} for p in parameters for v in positions]
scene=bpy.data.scenes.new('TEMP_NATIVE_FBM_REFERENCE');bpy.context.window.scene=scene
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1
scene.cycles.use_denoising=False;scene.cycles.use_adaptive_sampling=False
scene.render.resolution_x=len(positions)*8;scene.render.resolution_y=len(parameters)*8;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='OPEN_EXR';scene.render.image_settings.color_depth='32';scene.render.image_settings.color_mode='RGBA'
scene.render.image_settings.exr_codec='ZIP';scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
scene.render.film_transparent=True
cam=bpy.data.objects.new('TEMP_FBM_CAMERA',bpy.data.cameras.new('TEMP_FBM_CAMERA'));scene.collection.objects.link(cam)
cam.location=(len(positions)/2,len(parameters)/2,10);cam.data.type='ORTHO';cam.data.ortho_scale=len(positions);scene.camera=cam
for i,sample in enumerate(samples):
    x=i%len(positions);y=i//len(positions)
    mesh=bpy.data.meshes.new(f'TEMP_FBM_TILE_{i}');mesh.from_pydata([(x,y,0),(x+1,y,0),(x+1,y+1,0),(x,y+1,0)],[],[(0,1,2,3)])
    ob=bpy.data.objects.new(mesh.name,mesh);scene.collection.objects.link(ob)
    mat=bpy.data.materials.new(f'TEMP_FBM_SAMPLE_{i}');mat.use_nodes=True;mesh.materials.append(mat)
    nt=mat.node_tree;nt.nodes.clear();output=nt.nodes.new('ShaderNodeOutputMaterial');em=nt.nodes.new('ShaderNodeEmission');noise=nt.nodes.new('ShaderNodeTexNoise')
    noise.noise_type='FBM';noise.noise_dimensions='3D';noise.normalize=sample['parameters']['normalize']
    vector=nt.nodes.new('ShaderNodeCombineXYZ')
    for axis,value in enumerate(sample['position']):vector.inputs[axis].default_value=value
    nt.links.new(vector.outputs[0],noise.inputs['Vector'])
    for key,field in [('Scale','scale'),('Detail','detail'),('Roughness','roughness'),('Lacunarity','lacunarity')]:noise.inputs[key].default_value=sample['parameters'][field]
    noise.inputs['Distortion'].default_value=0
    sample['position']=[s.default_value for s in vector.inputs]
    sample['parameters']=sample['parameters'].copy()
    for key,field in [('Scale','scale'),('Detail','detail'),('Roughness','roughness'),('Lacunarity','lacunarity')]:sample['parameters'][field]=noise.inputs[key].default_value
    # Emission is nonnegative; encode signed test values in a safe positive
    # interval so shader closure clamping cannot masquerade as a noise change.
    encode=nt.nodes.new('ShaderNodeMath');encode.operation='MULTIPLY_ADD'
    encode.inputs[1].default_value=.25;encode.inputs[2].default_value=.5
    nt.links.new(noise.outputs['Fac'],encode.inputs[0]);nt.links.new(encode.outputs[0],em.inputs['Color']);nt.links.new(em.outputs[0],output.inputs['Surface'])
path=write_path(f'evidence/{version}/native_fbm_reference_r02.exr');scene.render.filepath=str(path)
bpy.ops.render.render(write_still=True)
im=bpy.data.images.load(str(path),check_existing=False);pixels=np.asarray(im.pixels[:],np.float32).reshape(scene.render.resolution_y,scene.render.resolution_x,4)
for i,sample in enumerate(samples):
    x=i%len(positions)*8+4;y=i//len(positions)*8+4
    sample['native_linear_rgba']=pixels[y,x].tolist();assert sample['native_linear_rgba'][3]>.999
    sample['native_noise_fac']=(sample['native_linear_rgba'][0]-.5)*4
report={'version':version,'native_sha256':digest,'blender_version':bpy.app.version_string,'process_id':os.getpid(),
 'reference':'Actual installed Cycles ShaderNodeTexNoise Fac, explicitly linked constant CombineXYZ vector, emission encoding and 32-bit linear EXR centre texels.',
 'samples':samples,'source_material':source.name,'native_modified':False,'runtime_passed':False}
bpy.context.window.scene=original
with native.open('rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==digest
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
write_path(f'web/assets/{version}_native_fbm_reference.json').write_text(json.dumps(report),encoding='utf-8')
print('NATIVE_FBM_REFERENCE_RENDERED',len(samples),os.getpid(),flush=True)
