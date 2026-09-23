"""Fix confirmed soffit winding and printed content depth, with no layout edits."""
import bpy
import bmesh
import hashlib
import json
import numpy as np
from pathlib import Path

R=Path('F:/MyWorld/ZurichWorld')
s=bpy.context.scene
assert s['version']=='G1_015r1'
ob=bpy.data.objects['SV_SOURCE_SOFFIT']
before=np.array([v.co[:] for v in ob.data.vertices])
assert all(p.normal.z>.999 for p in ob.data.polygons)

# Preserve already checked UV charts by face/vertex identity. They are still
# useful for a new lighting bake, but the previous soffit visibility is invalid.
cache=R/'derived/runtime_occlusion/G1_015r1'
manifest=json.loads((cache/'manifest.json').read_text())
arrays=dict(np.load(cache/'receiver_uv.npz'))
rec=next(r for r in manifest['receivers'] if r['name']==ob.name)
old_uv=arrays[rec['uv_key']]
chart={}
for p in ob.data.polygons:
    face=tuple(sorted(p.vertices))
    for li in p.loop_indices: chart[(face,ob.data.loops[li].vertex_index)]=old_uv[li]
bm=bmesh.new();bm.from_mesh(ob.data)
bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
bm.to_mesh(ob.data);bm.free();ob.data.update()
assert np.array_equal(before,np.array([v.co[:] for v in ob.data.vertices]))
assert all(p.normal.z<-.999 for p in ob.data.polygons)
new_uv=np.empty((len(ob.data.loops),2),np.float32)
for p in ob.data.polygons:
    face=tuple(sorted(p.vertices))
    for li in p.loop_indices: new_uv[li]=chart[(face,ob.data.loops[li].vertex_index)]
arrays[rec['uv_key']]=new_uv
v=np.empty(len(ob.data.vertices)*3,np.float32);ob.data.vertices.foreach_get('co',v)
ids=np.empty(len(ob.data.loops),np.int32);ob.data.loops.foreach_get('vertex_index',ids)
rec['topology_sha256']=hashlib.sha256(v.tobytes()+ids.tobytes()).hexdigest()
ob['surface_side_basis']='GroundSurface underside of surveyed canopy; outward normals face down. Coordinates unchanged.'

# Printed graphics belong behind the back of the 5mm cover pane. Their old
# reference depth lay inside the glass volume by 0.5mm.
d=json.loads((R/'derived/bellevue/south_service/input.json').read_text())
front=np.asarray(d['axis_v'])
printed=[]
for part in bpy.data.collections['24_BELLEVUE_SERVICE_PAVILION'].objects:
    if part.name.startswith('SV_AD_') and any(k in part.name for k in ['_TEXT_','_ART_LINE_','_FOOT']):
        part.location.x-=front[0]*.002
        part.location.y-=front[1]*.002
        part['print_depth_basis']='Printed graphic placed behind glazing on the artwork layer; 2mm corrective offset, original XY anchor and frame unchanged.'
        printed.append(part.name)
assert len(printed)==60

s['version']='G1_015r2'
native=R/'native/G1_015r2_service_surface_working.blend'
new_cache=R/'derived/runtime_occlusion'/s['version'];new_cache.mkdir(parents=True,exist_ok=True)
np.savez_compressed(new_cache/'receiver_uv.npz',**arrays)
manifest.update(version=s['version'],native=str(native),uv_file=str((new_cache/'receiver_uv.npz').relative_to(R)),
    inherited_scalar_ao_from='G1_015r1',invalid_scalar_ao_receivers=[ob.name,*printed],
    limitation='Reuses unchanged receiver visibility; corrected soffit and printed parts must not use old AO values. Packed UVs have been remapped for a fresh diffuse-light bake.')
(new_cache/'manifest.json').write_text(json.dumps(manifest,indent=2))
bpy.context.view_layer.update()
s.camera=bpy.data.objects['BE_QA_SERVICE_NORTH']
bpy.ops.wm.save_as_mainfile(filepath=str(native))
w=json.loads((R/'runtime/station_road_working.json').read_text())
w.update(version=s['version'],native=str(native),accepted=False,not_published=True)
(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2))
report={'version':s['version'],'native':str(native),'soffit_faces':len(ob.data.polygons),
 'all_soffit_normals_down':True,'coordinates_exactly_unchanged':True,'printed_graphics_adjusted':len(printed),
 'print_shift_m':.002,'old_soffit_occlusion_rejected':True,'visual_acceptance':False}
e=R/'evidence'/s['version'];e.mkdir(exist_ok=True)
(e/'surface_repair.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
