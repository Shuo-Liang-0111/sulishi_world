"""Derive page UVs from actual mesh coordinates, independent of bmesh loop order."""
import bpy,json,numpy as np
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_012r2';d=json.loads((R/'derived/bellevue/corner_fixtures/input.json').read_text());C=np.array(d['information'][0]['geometry']['coordinates'][0])-np.array(d['origin'][:2]);floor=d['info_ground_local'];checks=[]
for prefix,axis,mid,z in [('CF_INFO_MAIN_NOTICE',np.array(d['u']),.35,1.65),('CF_INFO_RETURN_NOTICE',np.array(d['v']),.36,1.53)]:
 for suffix in ['', '_REVERSE']:
  ob=bpy.data.objects[prefix+'_PRINT'+suffix];me=ob.data;uv=me.uv_layers.active
  for loop in me.loops:
   p=me.vertices[loop.vertex_index].co;along=float((np.array(p[:2])-C)@axis);uv.data[loop.index].uv=(.5-(along-mid)/(.627-.056),.5+(p.z-floor-z)/(.97-.056))
  vals=np.array([x.uv[:] for x in uv.data]);assert vals.min()>-.0001 and vals.max()<1.0001;checks.append(ob.name)
s['version']='G1_012r3';s.camera=bpy.data.objects['BE_QA_CORNER_FIXTURES'];native=R/'native/G1_012r3_corner_fixtures_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native));rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=s['version'],native=str(native),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2));e=R/'evidence/G1_012r3';e.mkdir(exist_ok=True);(e/'map_uv_fix.json').write_text(json.dumps({'version':s['version'],'fixed_objects':checks,'reason':'Actual render showed rotated map: bmesh helper changed polygon loop order. Recompute UV by geometric panel axes, not assumed index order.','accepted':False},indent=2));print(json.dumps({'version':s['version'],'map_faces':len(checks)}))
