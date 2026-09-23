"""Separate surveyed glazing from the opaque annular roof for correct light visibility."""
import bpy,bmesh,json
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version']=='G1_006'
roof=bpy.data.objects['BE_SOURCE_bauten_dachmodell_3d.111603'];mat=bpy.data.materials['BE | clear curved 12mm glass']
glass_faces=[p for p in roof.data.polygons if roof.data.materials[p.material_index]==mat]
if glass_faces:
    indices=sorted({i for p in glass_faces for i in p.vertices});remap={i:j for j,i in enumerate(indices)}
    me=bpy.data.meshes.new('Surveyed Bellevue glass cone');me.from_pydata([list(roof.data.vertices[i].co) for i in indices],[],[[remap[i] for i in p.vertices] for p in glass_faces]);me.update();me.materials.append(mat)
    ob=bpy.data.objects.new('BE_SKYLIGHT_GLASS_CONE',me);bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].objects.link(ob)
    ob['evidence_basis']='Exact glass-bearing polygons split from official central roof; 12mm thickness inferred'
    ob['place']='Bellevue_Rondell';ob.visible_shadow=False
    modifier=ob.modifiers.new('Physical glazing thickness','SOLIDIFY');modifier.thickness=.012;modifier.offset=-1
    bm=bmesh.new();bm.from_mesh(roof.data);bm.faces.ensure_lookup_table();bmesh.ops.delete(bm,geom=[bm.faces[p.index] for p in glass_faces],context='FACES');bm.to_mesh(roof.data);bm.free()
roof.visible_shadow=True
scene['skylight_transport']='Opaque roof annulus and clear cone separated; only glazing omits opaque shadow in the thin-glass approximation'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'native/G1_006_bellevue_working.blend'))
print(json.dumps({'glass_faces_split':len(glass_faces),'opaque_roof_casts_shadow':roof.visible_shadow,'native':bpy.data.filepath}))
