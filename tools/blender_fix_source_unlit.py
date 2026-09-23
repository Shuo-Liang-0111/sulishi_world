import bpy,json
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld')
scene=bpy.context.scene
for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects:
    for m in o.data.materials:
        nodes=m.node_tree.nodes
        tex=next(n for n in nodes if n.type=='TEX_IMAGE')
        output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
        # Blender's shipped glTF unlit detector recognizes a color socket feeding Surface.
        # Blender itself converts that color to a unit-strength emission closure.
        m.node_tree.links.new(tex.outputs['Color'],output.inputs['Surface'])
        m['export_shading']='KHR_materials_unlit via direct color output'
scene['version']='G1_004r2'
native=ROOT/'native/G1_004r2_photogrammetry_reference.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(native))
record=json.loads((ROOT/'runtime/current_scene.json').read_text())
record.update(native=str(native),version='G1_004r2',viewer_note='source shader parity correction; re-export pending')
(ROOT/'runtime/current_scene.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({'corrected_materials':len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects),
                  'basis':'installed official glTF exporter unlit.py direct-color detector','native':str(native)}))
