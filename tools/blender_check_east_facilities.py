"""Measure persisted facility feet against the actual sloped platform mesh."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;V=s['version']
assert V in ['G1_016','G1_016r1','G1_017','G1_017r1']
ground=bpy.data.objects['BS_ASPHALT'];assert ground.matrix_world==Matrix.Identity(4)
deps=bpy.context.evaluated_depsgraph_get();results=[]
for name in ['BSE_INFO_GROUND_PATCH_0','BSE_INFO_GROUND_PATCH_1','BSE_INFO_GROUND_PATCH_2','BSE_BIN1173_BASE']:
    ob=bpy.data.objects[name];ev=ob.evaluated_get(deps);me=ev.to_mesh()
    points=[ob.matrix_world@v.co for v in me.vertices];zmin=min(p.z for p in points)
    bottom=[p for p in points if p.z<=zmin+.0002];gaps=[]
    for p in bottom:
        hit,q,_,_=ground.ray_cast(Vector((p.x,p.y,40)),Vector((0,0,-1)))
        assert hit,(name,'foot outside actual platform')
        gaps.append(p.z-q.z)
    ev.to_mesh_clear()
    assert max(gaps)<.025 and min(gaps)>-.10,(name,min(gaps),max(gaps))
    results.append({'name':name,'bottom_points':len(bottom),'min_gap_m':min(gaps),'max_gap_m':max(gaps),'positive_gap_needs_visual_review':max(gaps)>.003})
bin_source=bpy.data.objects['BSF_BIN631_SHEET_SHELL'];bin_new=bpy.data.objects['BSE_BIN1173_SHEET_SHELL']
relative=bin_new.matrix_world@bin_source.matrix_world.inverted();scale=relative.decompose()[2]
assert max(abs(x-1) for x in scale)<.00001,'Bin fabrication was rescaled'
assert len(bin_source.data.vertices)==len(bin_new.data.vertices)
assert all((a.co-b.co).length<.000001 for a,b in zip(bin_source.data.vertices,bin_new.data.vertices))
record={'version':V,'actual_ground':'BS_ASPHALT','feet':results,'bin_fabrication_retained':True,'bin_relative_scale':list(scale),'visual_or_natural_use_acceptance':False}
(R/'evidence'/V/'facility_contact_check.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
