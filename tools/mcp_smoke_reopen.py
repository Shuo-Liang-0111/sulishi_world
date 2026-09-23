import bpy
bpy.ops.wm.open_mainfile(filepath='F:/MyWorld/ZurichWorld/runtime/mcp_smoke/connection_test.blend')
obj = bpy.data.objects['Zurich_MCP_Connection_Check']
assert obj['verification_marker'] == 'zurich-mcp-20260921'
assert abs(obj.dimensions.x - 1.0) < 0.01
assert bpy.context.scene.blendermcp_port == 19876
print('MCP_SAVED_SCENE_REOPEN_VERIFIED')

