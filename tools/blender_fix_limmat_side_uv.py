"""Repair one inferred tree opening and collapsed side UVs; tree/source geometry stays."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_019';p=json.loads((R/'derived/bellevue/limmat_sidewalk/ground_input.json').read_text(encoding='utf-8'));reports=[]
tree_counts={o.name:len(o.data.vertices) for o in bpy.data.collections['31_LIMMAT_SIDEWALK_TREES'].objects}
for key,tris in p['parts'].items():
 ob=bpy.data.objects['LM_'+key.upper()];oldmesh=ob.data;old=np.asarray([u.uv[:] for u in oldmesh.uv_layers.active.data]).reshape(-1,3,2);data=np.asarray(p['uv'][key],dtype=np.float32)
 def areas(a):return abs(np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]))/2
 oldarea=areas(old);newarea=areas(data)
 if key in ['curb_face','retaining_edge','pit_edge']:assert min(newarea)>1e-12,(key,float(min(newarea)))
 t=np.asarray(tris);me=bpy.data.meshes.new(ob.name+'_root_clearance_uv');me.from_pydata(t.reshape(-1,3).tolist(),[],np.arange(t.size//3).reshape(-1,3).tolist());me.update()
 for mat in oldmesh.materials:me.materials.append(mat)
 layer=me.uv_layers.new(name='metre_scale');layer.data.foreach_set('uv',data.ravel());ob.data=me
 if oldmesh.users==0:bpy.data.meshes.remove(oldmesh)
 reports.append({'object':ob.name,'triangles_before':len(old),'triangles_after':len(tris),'collapsed_uv_before':int((oldarea<1e-12).sum()),'collapsed_uv_after':int((newarea<1e-12).sum())})
assert tree_counts=={o.name:len(o.data.vertices) for o in bpy.data.collections['31_LIMMAT_SIDEWALK_TREES'].objects}
s['version']='G1_019r1';bpy.context.view_layer.update();native=R/'native/G1_019r1_limmat_surface_working.blend';assert not native.exists();bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
E=R/'evidence/G1_019r1';E.mkdir(exist_ok=True);(E/'uv_repair.json').write_text(json.dumps({'version':s['version'],'native':str(native),'repairs':reports,'basis':'Native ray checks found19 lower-root vertices outside the inferred soil opening for72765; all were within the surveyed sidewalk. Widen only that opening toward the road, retain6cm edge, clip mortar joints away from soil. No source position, footprint or tree geometry moved. Also correct collapsed side UVs with continuous stationing and a nonzero pit tangent.','visual_acceptance':False},indent=2))
w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=s['version'],native=str(native),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2))
print('LIMMAT_UV_REPAIRED',json.dumps(reports),flush=True)
