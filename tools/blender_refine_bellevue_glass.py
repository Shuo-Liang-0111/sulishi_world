"""Keep glass panels planar and enable native caustic transport, no exposure changes."""
import bpy,bmesh,json
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version']=='G1_005r3'
building=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION']
for ob in building.objects:
    if ob.type!='MESH':continue
    if ob.name.startswith('BE_DISPLAY_GLASS'):
        for p in ob.data.polygons:p.use_smooth=False
    if ob.name.startswith(('BE_FIXED_GLASS','BE_DOOR_GLASS')):
        bm=bmesh.new();bm.from_mesh(ob.data)
        edges=[e for e in bm.edges if e.is_manifold and e.calc_face_angle()>0.45]
        bmesh.ops.split_edges(bm,edges=edges);bm.to_mesh(ob.data);bm.free();ob.data.update()
    if hasattr(ob.cycles,'is_caustics_caster'):
        ob.cycles.is_caustics_caster=any(m and 'glass' in m.name for m in ob.data.materials)
        ob.cycles.is_caustics_receiver=not ob.cycles.is_caustics_caster
for ld in bpy.data.lights:
    if hasattr(ld.cycles,'is_caustics_light'):ld.cycles.is_caustics_light=True
if hasattr(scene.world.cycles,'is_caustics_light'):scene.world.cycles.is_caustics_light=True
scene.cycles.caustics_refractive=True
scene.cycles.max_bounces=max(12,scene.cycles.max_bounces)
scene.cycles.transmission_bounces=12
scene.cycles.transparent_max_bounces=12
scene['version']='G1_005r4'
scene['glass_transport_note']='Planar case normals restored, curved panel caps split; MNEE caster/receiver enabled where API supports it. Exposure unchanged; not a lighting acceptance.'
native=ROOT/'native/G1_005r4_bellevue_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
status=json.loads((ROOT/'runtime/bellevue_working.json').read_text());status.update(version=scene['version'],native=str(native))
(ROOT/'runtime/bellevue_working.json').write_text(json.dumps(status,indent=2))
print(json.dumps({'version':scene['version'],'native':str(native),'world_caustics':getattr(scene.world.cycles,'is_caustics_light',None),'transmission_bounces':scene.cycles.transmission_bounces,'exposure':scene.view_settings.exposure}))
