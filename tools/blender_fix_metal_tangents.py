"""Give anisotropic surfaces a nondegenerate UV basis before GLTF tangent export."""
import bpy,json,math
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version']=='G1_006'
mat=bpy.data.materials['BE | stainless counter'];changes=[]
for ob in bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].objects:
    if ob.type!='MESH' or mat not in list(ob.data.materials):continue
    uv=ob.data.uv_layers.get('Surface grain direction') or ob.data.uv_layers.new(name='Surface grain direction')
    for p in ob.data.polygons:
        normal=p.normal;axis=max(range(3),key=lambda i:abs(normal[i]));keep=[i for i in range(3) if i!=axis]
        for li in p.loop_indices:
            v=ob.data.vertices[ob.data.loops[li].vertex_index].co
            uv.data[li].uv=(v[keep[0]],v[keep[1]])
    changes.append(ob.name)
mat['surface_basis']='Per-face metre UVs for stable anisotropic tangent; no missing/degenerate texture coordinate fallback.'
scene['version']='G1_006r1';scene['quality_status']='interior UV/tangent repair; whole area not accepted'
native=ROOT/'native/G1_006r1_bellevue_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
w=json.loads((ROOT/'runtime/bellevue_working.json').read_text());w.update(version=scene['version'],native=str(native),new_objects=len(bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].objects))
(ROOT/'runtime/bellevue_working.json').write_text(json.dumps(w,indent=2));out=ROOT/'evidence'/scene['version'];out.mkdir(exist_ok=True)
(out/'metal_uv_repair.json').write_text(json.dumps({'objects':changes,'cause':'Real browser single-variable comparison: disabling anisotropy removes NaN-like black bands and their refracted copies. Metal surfaces lacked UVs.','retained_anisotropy':.35,'requires_runtime_recheck':True},indent=2));print(json.dumps({'version':scene['version'],'changed_meshes':len(changes)}))
