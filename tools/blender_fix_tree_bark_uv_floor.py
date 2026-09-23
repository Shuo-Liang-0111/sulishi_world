"""Keep subsoil UVs on coarse bark; do not repeat the pale atlas top at the roots."""
import bpy,json
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_011r3';counts={}
for name in ['HB_TREE_119962_WOOD','BE_TREE_69773_WOOD']:
 me=bpy.data.objects[name].data;uv=me.uv_layers.active;count=0
 for p in me.polygons:
  if p.material_index==1:
   for li in p.loop_indices:
    if uv.data[li].uv.y<.001:uv.data[li].uv.y=.001;count+=1
 counts[name]=count
s['version']='G1_011r4';s.camera=bpy.data.objects['HB_QA_TREE_BASE'];native=R/'native/G1_011r4_haus_tree_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=s['version'],native=str(native),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2))
e=R/'evidence/G1_011r4';e.mkdir(exist_ok=True);(e/'root_uv_fix.json').write_text(json.dumps({'version':s['version'],'changed_loops':counts,'reason':'Actual near render revealed pale wraparound at negative trunk V; ground ray check showed bases already below soil. Correct UV, not ground height.','accepted':False},indent=2));print(json.dumps({'version':s['version'],'loops':counts}))
