"""Irregular coarse-to-flaking bark transition without a horizontal material cuff."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_011r1';flaking=bpy.data.materials['HB | inferred flaking plane bark'];reports=[]
for ident,name,path in [(119962,'HB_TREE_119962_WOOD','derived/haus_bellevue/tree_119962_input.json'),(69773,'BE_TREE_69773_WOOD','derived/bellevue/west_context/tree_69773_input.json')]:
 d=json.loads((R/path).read_text(encoding='utf-8'));root=np.array([*d['source']['geometry']['coordinates'],d['ground_ln02_m']])-np.array(d['origin']);ob=bpy.data.objects[name];me=ob.data;uv=me.uv_layers.active
 # Normalize old loop UV to the same physical base before interpolation.
 for p in me.polygons:
  if p.material_index:
   for li in p.loop_indices:uv.data[li].uv*=2.4/1.5
  p.material_index=0
 if flaking not in list(me.materials):me.materials.append(flaking)
 bm=bmesh.new();bm.from_mesh(me);edges=set()
 for f in bm.faces:
  p=np.array(f.calc_center_median())-root
  if -.15<p[2]<3.8 and np.linalg.norm(p[:2])<.70:edges.update(f.edges)
 bmesh.ops.subdivide_edges(bm,edges=list(edges),cuts=15,use_grid_fill=True)
 bm.to_mesh(me);bm.free();me.update();uv=me.uv_layers.active;counts=[0,0]
 for f in me.polygons:
  c=sum((me.vertices[i].co for i in f.vertices),start=__import__('mathutils').Vector())/len(f.vertices);x,y,z=np.array(c)-root
  weight=np.clip((z-.40)/2.85,0,1);weight=weight*weight*(3-2*weight)
  field=.5+.24*math.sin(9*x+4*y+3.7*z)+.14*math.sin(13*y-4.8*z)+.10*math.sin(17*x+7*y+8.2*z)
  f.material_index=1 if field>1-weight else 0;counts[f.material_index]+=1;f.use_smooth=True
  if f.material_index:
   for li in f.loop_indices:uv.data[li].uv*=1.5/2.4
 ob['bark_note']='Ragged coarse root bark to smoother flaking upper bark, original procedural upper maps; individual peel pattern is inferred.'
 reports.append({'tree':ident,'vertices':len(me.vertices),'coarse_faces':counts[0],'flaking_faces':counts[1]})
bpy.data.objects['HB_QA_TREE'].data.lens=22
s['version']='G1_011r2';s.camera=bpy.data.objects['HB_QA_TREE_BASE'];bpy.context.view_layer.update();native=R/'native/G1_011r2_haus_tree_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=s['version'],native=str(native),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2))
e=R/'evidence/G1_011r2';e.mkdir(exist_ok=True);(e/'bark_refinement.json').write_text(json.dumps({'version':s['version'],'trees':reports,'native':str(native),'accepted':False},indent=2));print(json.dumps({'version':s['version'],'trees':reports,'accepted':False}))
