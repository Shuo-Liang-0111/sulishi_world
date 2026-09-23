"""Check the persisted repaired edges against actual asphalt and soil vertices."""
import bpy,json
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;V=s['version'];assert V in ['G1_015r1','G1_015r2','G1_015r3','G1_016','G1_016r1','G1_017','G1_017r1']
edge=bpy.data.objects['BS_TREE_PIT_EXPOSED_ASPHALT_EDGES'].data
soil={tuple(v.co[:2]):v.co.z for v in bpy.data.objects['BS_SOIL'].data.vertices}
asphalt={tuple(v.co[:2]):v.co.z for v in bpy.data.objects['BS_ASPHALT'].data.vertices}
miss=[];upper=[];lower=[]
for v in edge.vertices:
    key=tuple(v.co[:2])
    if key not in soil or key not in asphalt:miss.append(key);continue
    ds=abs(v.co.z-soil[key]);da=abs(v.co.z-asphalt[key])
    assert min(ds,da)<.00002,(key,ds,da)
    if ds<da:lower.append(ds)
    else:upper.append(da)
assert not miss,('Edge coordinates absent from one of the two real boundaries',len(miss))
assert upper and lower
report={'version':V,'edge_vertices_checked':len(edge.vertices),'unmatched_boundary_vertices':len(miss),
        'max_soil_seam_error_m':max(lower),'max_asphalt_seam_error_m':max(upper),
        'checked_existing_surfaces':['BS_ASPHALT','BS_SOIL'],'collision_or_visual_acceptance':False}
(R/'evidence'/V/'pit_edge_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
