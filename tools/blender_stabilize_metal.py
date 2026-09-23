"""Use a shared native/runtime isotropic satin steel pending anisotropy renderer repair."""
import bpy,json
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_006r1'
m=bpy.data.materials['BE | stainless counter'];m.node_tree.nodes.get('Principled BSDF').inputs['Anisotropic'].default_value=0
m['surface_finish_basis']='Photo-informed satin stainless steel. Isotropic roughness .32 retained identically in native/runtime; inferred .35 anisotropy rejected after browser refraction artifacts persisted with valid UV and tangents.'
s['version']='G1_006r2';native=ROOT/'native/G1_006r2_bellevue_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
w=json.loads((ROOT/'runtime/bellevue_working.json').read_text());w.update(version=s['version'],native=str(native));(ROOT/'runtime/bellevue_working.json').write_text(json.dumps(w,indent=2));print(json.dumps({'version':s['version'],'change':'Shared native/runtime satin metal; no per-browser material override'}))
