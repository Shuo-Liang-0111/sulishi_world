"""Disposable connection/renderer check, never a city-quality deliverable."""
import bpy
from mathutils import Vector

assert bpy.context.scene.name == 'Zurich_G1_Working', 'Do not overwrite a working scene'
assert len(bpy.context.scene.objects) == 0, 'Smoke test requires the empty bootstrap scene'
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.5))
obj = bpy.context.object
obj.name = 'Zurich_MCP_Connection_Check'
obj['verification_marker'] = 'zurich-mcp-20260921'
mat = bpy.data.materials.new('Smoke ceramic')
mat.diffuse_color = (0.06, 0.26, 0.22, 1)
mat.use_nodes = True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = mat.diffuse_color
mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.4
obj.data.materials.append(mat)
bevel = obj.modifiers.new('Edge', 'BEVEL')
bevel.width = 0.035
bevel.segments = 3
bpy.ops.mesh.primitive_plane_add(size=8)
bpy.context.object.name = 'Smoke floor'
bpy.ops.object.light_add(type='AREA', location=(2, -2, 4))
bpy.context.object.data.energy = 450
bpy.context.object.data.shape = 'DISK'
bpy.context.object.data.size = 3
bpy.ops.object.camera_add(location=(2.7, -3.7, 2.4))
cam = bpy.context.object
cam.rotation_euler = (Vector((0, 0, .45)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
scene = bpy.context.scene
scene.camera = cam
scene.world.color = (.15, .15, .15)
scene.render.engine = 'CYCLES'
scene.cycles.device = 'GPU'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x = 640
scene.render.resolution_y = 480
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'AgX'
scene.render.filepath = 'F:/MyWorld/ZurichWorld/runtime/mcp_smoke/render.png'
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.region_3d.view_perspective = 'CAMERA'
bpy.ops.wm.save_as_mainfile(filepath='F:/MyWorld/ZurichWorld/runtime/mcp_smoke/connection_test.blend')
bpy.ops.render.render(write_still=True)
print('SMOKE_CREATED_SAVED_RENDERED')

