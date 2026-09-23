"""Six physical emissive directions establish Blender-to-glTF HDR orientation."""
import bpy,math,json
from mathutils import Vector
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld')
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene
axes=[('PX',(1,0,0),(1,0,0)),('NX',(-1,0,0),(0,1,1)),('PY',(0,1,0),(0,1,0)),('NY',(0,-1,0),(1,0,1)),('PZ',(0,0,1),(0,0,1)),('NZ',(0,0,-1),(1,1,0))]
for name,direction,color in axes:
    bpy.ops.mesh.primitive_plane_add(size=20,location=Vector(direction)*10)
    ob=bpy.context.object;ob.name=name;ob.rotation_euler=Vector(direction).to_track_quat('Z','Y').to_euler()
    mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.node_tree.nodes.clear()
    emission=mat.node_tree.nodes.new('ShaderNodeEmission');emission.inputs['Color'].default_value=(*color,1)
    out=mat.node_tree.nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(emission.outputs[0],out.inputs['Surface']);ob.data.materials.append(mat)
data=bpy.data.cameras.new('AXIS_CAMERA');camera=bpy.data.objects.new('AXIS_CAMERA',data);s.collection.objects.link(camera)
data.type='PANO';data.panorama_type='EQUIRECTANGULAR';camera.rotation_euler=(math.pi/2,0,0);s.camera=camera
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1;s.render.threads_mode='FIXED';s.render.threads=4
s.render.resolution_x=256;s.render.resolution_y=128;s.render.resolution_percentage=100
s.render.image_settings.file_format='HDR';s.render.filepath=str(R/'evidence/panorama_axis_calibration.hdr')
bpy.ops.render.render(write_still=True)
image=bpy.data.images.load(s.render.filepath);w,h=image.size;pixels=list(image.pixels)
report=[]
for u,v in [(.001,.5),(.25,.5),(.5,.5),(.75,.5),(.5,.99),(.5,.01)]:
    x=min(w-1,int(u*w));y=min(h-1,int(v*h));i=(y*w+x)*4;color=pixels[i:i+3]
    name,direction,_=min(axes,key=lambda a:sum((color[j]-a[2][j])**2 for j in range(3)))
    report.append({'uv_bottom_origin':[u,v],'rgb_linear':color,'blender_direction':direction,'axis':name,'gltf_direction':[direction[0],direction[2],-direction[1]]})
(R/'evidence/panorama_axis_calibration.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
