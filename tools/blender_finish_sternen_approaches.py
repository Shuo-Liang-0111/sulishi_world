"""027r6 -> r7: sign in its bay, emissive globes, continuous neutral paving.

This changes the local approach and visual interiors, not the building footprint
or any camera. The existing restaurant remains closed and is not an accepted
public interior. Outer paving evidence and inference are retained separately.
"""
from pathlib import Path
import hashlib
import importlib
import json
import math
import shutil
import sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).resolve().parent))
importlib.invalidate_caches()
from workspace_paths import ROOT, read_path, write_path
from blender_geometry_fingerprint import object_state
from blender_photo_clip import cut_object

s = bpy.context.scene
assert s['version'] == 'G1_027r6'
version = 'G1_027r7'
target = write_path('native/G1_027r7_sternen_street_approaches.blend')
assert not target.exists() and shutil.disk_usage(ROOT).free > 3_000_000_000
cp = json.loads(read_path('evidence/G1_027r6/checkpoint.json').read_text())
with Path(bpy.data.filepath).open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == cp['native_sha256']
previous = json.loads(read_path('evidence/G1_027r6/build_report.json').read_text())
input_path = read_path('derived/sternen_grill/r7_ground_input.json')
ground = json.loads(input_path.read_text())
for name, digest in ground['input_sha256'].items():
    assert hashlib.sha256(read_path('derived/sternen_grill/'+name).read_bytes()).hexdigest() == digest
d = json.loads(read_path('derived/sternen_grill/build_input.json').read_text())
A, U, N = (np.array(d[k]) for k in ['A','U','N'])
W, D = d['width'], d['depth']
C = bpy.data.collections['45_STERNEN_GRILL_FRONTAGES']
before = {o.name: object_state(o) for o in s.objects}
source = bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE']
source_ids = {o.name: o.data.as_pointer() for o in source.objects}


def P(u,v,z):
    return Vector((*list(A + U*u + N*v), z))


def Q(point):
    point = np.asarray(point)
    return np.r_[(point[:2]-A)@U, (point[:2]-A)@N, point[2]]


# The photograph shows lettering over the third opening, clear of the piers.
sign = bpy.data.objects['SG_RESTAURANT_LETTERING']
sign_bounds = np.array([Q(sign.matrix_world@v.co) for v in sign.data.vertices])
sign_center_before = float((sign_bounds[:,0].min()+sign_bounds[:,0].max())/2)
target_center = W * 2.5/4
sign.location += Vector((*list(U*(target_center-sign_center_before)),0))
sign['placement_basis'] = 'Third front transom bay in PSP exterior photographs; exact lettering fabrication inferred.'

# The visible luminous sphere itself now emits the light. The previous area
# sources were separate flat emitters visible through transmission, not fixtures.
emitters = []
removed_lights = []
for level in ['GROUND','RESTAURANT']:
    lamps = [o for o in C.objects if o.type == 'LIGHT' and o.name.startswith('SG_R6_'+level+'_LIGHT_')]
    globe = bpy.data.objects['SG_R6_'+level+'_OPAL_GLOBE']
    assert lamps and globe.type == 'MESH' and not globe.parent
    world_area = 0.
    for face in globe.data.polygons:
        points = [globe.matrix_world@globe.data.vertices[i].co for i in face.vertices]
        world_area += sum((points[j]-points[0]).cross(points[j+1]-points[0]).length/2 for j in range(1,len(points)-1))
    power = sum(ob.data.energy for ob in lamps)
    material = globe.data.materials[0].copy()
    material.name = 'SG | r7 '+level.lower()+' luminous opal globes'
    bs = next(n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bs.inputs['Emission Strength'].default_value = power / (math.pi * world_area)
    material['emission_basis'] = 'Approximate former total emitter power distributed over the actual globe surface; not photometric site measurement.'
    globe.data.materials[0] = material
    emitters.append(dict(object=globe.name,area_m2=world_area,approximate_total_power_w=power,
                         emission_strength=power/(math.pi*world_area),material=material.name))
    for light in lamps:
        removed_lights.append(light.name)
        bpy.data.objects.remove(light,do_unlink=True)
assert len(removed_lights) == 8

# Keep the globally shared asphalt untouched. Retain its CC0 aggregate, roughness
# and normal maps; adjust only this local surface's excessive red cast.
old_asphalt = bpy.data.materials['asphalt_03']
old_users = {o.name for o in s.objects if o.type=='MESH' and old_asphalt in o.data.materials[:]}
paving = old_asphalt.copy(); paving.name = 'SG | r7 neutral street asphalt'
nodes, links = paving.node_tree.nodes, paving.node_tree.links
bs = next(n for n in nodes if n.type == 'BSDF_PRINCIPLED')
incoming = next(link for link in links if link.to_node == bs and link.to_socket == bs.inputs['Base Color'])
socket = incoming.from_socket; links.remove(incoming)
hue = nodes.new('ShaderNodeHueSaturation')
hue.inputs['Saturation'].default_value = .06
hue.inputs['Value'].default_value = 1.
links.new(socket,hue.inputs['Color']);links.new(hue.outputs['Color'],bs.inputs['Base Color'])
paving['source_asset'] = 'Poly Haven asphalt_03 CC0; local color correction, 2.05m repeat, existing roughness and normal retained.'
paving['evidence_basis'] = 'Neutral dark-grey public approach in viewed exterior photographs; material values inferred.'
old_ground = bpy.data.objects['SG_R6_RESTORED_STREET_GROUND']
bpy.data.objects.remove(old_ground,do_unlink=True)
name = 'SG_R7_CONTINUOUS_STREET_APPROACH'
mesh = bpy.data.meshes.new(name)
mesh.from_pydata(ground['vertices'],[],ground['faces']);mesh.update()
assert not mesh.validate(clean_customdata=False)
mesh.materials.append(paving)
uv = mesh.uv_layers.new(name='metre_scale')
uv.data.foreach_set('uv',np.asarray([mesh.vertices[loop.vertex_index].co[:2] for loop in mesh.loops],dtype=np.float32).ravel()/2.05)
approach = bpy.data.objects.new(name,mesh);C.objects.link(approach)
approach['evidence_basis'] = ground['basis']
approach['source_input_sha256'] = hashlib.sha256(input_path.read_bytes()).hexdigest()

# Remove only ground-like photo triangles in the replacement footprint. Keep
# furniture, faces, vertical walls and all unaffected UVs; never reload old tiles.
context = json.loads(read_path('derived/sternen_grill/context_probe.json').read_text())
cuts = []
for row in context['rows']:
    ob = bpy.data.objects[row['name']]
    eligible = []
    for face in ob.data.polygons:
        points = np.array([ob.matrix_world@ob.data.vertices[i].co for i in face.vertices])
        normal = np.cross(points[1]-points[0],points[2]-points[0]);length=np.linalg.norm(normal)
        if length>1e-9 and abs(normal[2])>length*.75 and points[:,2].max()<8.89:
            eligible.append(face.index)
    result = cut_object(ob,Q,ground['replacement_boxes'],eligible_faces=eligible)
    if result:
        result['eligible_source_faces'] = eligible
        cuts.append(result)

bpy.context.view_layer.update()
allowed = {o.name for o in C.objects} | set(removed_lights) | {'SG_R6_RESTORED_STREET_GROUND'} | {r['object'] for r in cuts}
assert not [name for name,state in before.items() if name not in allowed and object_state(bpy.data.objects[name])!=state]
assert source_ids == {o.name:o.data.as_pointer() for o in source.objects}
assert old_users-{'SG_R6_RESTORED_STREET_GROUND'} == {o.name for o in s.objects if o.type=='MESH' and old_asphalt in o.data.materials[:]}

# Probe the actual scene, including the formerly unsupported convex corner.
deps = bpy.context.evaluated_depsgraph_get()
samples = [(u,v) for u in np.linspace(.45,W-.45,15) for v in [.5,1.,2.,3.,4.]]
samples += [(W+offset,v) for offset in [.5,1.,2.] for v in [-15.,-12.,-9.,-6.,-3.,-.5,0.,.5,1.]]
contacts=[]; retained_obstructions=[]
surface_tree=BVHTree.FromObject(approach,deps)
for u,v in samples:
    support,normal,_,_=surface_tree.ray_cast(P(u,v,9.1),Vector((0,0,-1)),1.2)
    assert support is not None and 8.35<support.z<8.8 and normal.z>.98,(u,v)
    hit,p,n,face,ob,m=s.ray_cast(deps,P(u,v,9.1),Vector((0,0,-1)),distance=1.2)
    assert hit
    row=dict(u=float(u),v=float(v),height=p.z,normal_z=n.z,object=ob.name,support_z=support.z)
    # The outer lane contains unreconstructed scan furniture. Record it rather
    # than deleting it, or calling every point a clear walking location.
    if abs(p.z-support.z)>.02 or n.z<.98:
        assert u>W+1.5,('obstruction in repaired inner approach',row)
        retained_obstructions.append(row)
    contacts.append(row)

s['version']=version
s['latest_construction']='Sternen sign placement, physical globe emission and continuous grey street/lane approach'
merged={r['object']:r for r in previous['photo_cuts']};merged.update({r['object']:r for r in cuts})
report=dict(previous)
report.update(version=version,base_native=cp['native'],base_native_sha256=cp['native_sha256'],
              created_objects=sorted(o.name for o in C.objects),added_objects=[name],
              removed_objects=removed_lights+['SG_R6_RESTORED_STREET_GROUND'],
              photo_cuts=list(merged.values()),incremental_photo_cuts=cuts,
              ground_repair_input=str(input_path),ground_input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),
              sign_center_before=sign_center_before,sign_center_after=target_center,
              physical_globe_emitters=emitters,continuous_ground_contacts=contacts,
              retained_outer_lane_scan_obstructions=retained_obstructions,
              shared_asphalt_untouched=True,old_cameras_unchanged=True,
              removed_auxiliary_lights=removed_lights,unrelated_objects_unchanged=len(before)-len(allowed & before.keys()),
              limits=previous['limits']+ground['limits'])
write_path(f'evidence/{version}/build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(target),check_existing=False,compress=True)
with target.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
receipt={k:cp[k] for k in ['storage_sharing_applied','required_immutable_libraries','shared_meshes','shared_objects']}
receipt.update(version=version,native=str(target),native_sha256=digest,native_bytes=target.stat().st_size,
               objects=len(s.objects),native_fresh_reopen_verified=False,visual_acceptance=False,
               runtime_exported=False,natural_use_verified=False)
write_path(f'evidence/{version}/checkpoint.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('STERNEN_APPROACH_SAVED',json.dumps({k:receipt[k] for k in
    ['version','native','native_sha256','native_bytes','objects']}),flush=True)
