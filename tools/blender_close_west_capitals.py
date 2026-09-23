"""Seat each curved column head against the actual tessellated soffit."""
import bpy,json,math,numpy as np
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene;assert scene['version']=='G1_008r1'
soffit=bpy.data.objects['BE_WEST_SHELTER_SOFFIT'];me=soffit.data;me.calc_loop_triangles();vv=np.array([v.co[:] for v in me.vertices]);tt=np.array([vv[list(t.vertices)] for t in me.loop_triangles]);centres=tt[:,:,:2].mean(axis=1)
def ceiling(xy):
 for i in np.argsort(np.linalg.norm(centres-xy,axis=1))[:50]:
  tri=tt[i];a=(tri[1:,:2]-tri[0,:2]).T
  if abs(np.linalg.det(a))<1e-10:continue
  w=np.linalg.solve(a,xy-tri[0,:2])
  if min(w)>-1e-5 and sum(w)<1.00001:return float(tri[0,2]+w@(tri[1:,2]-tri[0,2]))
 raise ValueError('Column head outside roof')
data=json.loads((ROOT/'derived/bellevue/west_context/canopy_input.json').read_text());rows=[]
for k,xy in enumerate(data['support_centres_local']):
 ob=bpy.data.objects[f'BE_WEST_COLUMN_FLARE_{k:02d}'];old=ob.data;vertices=[];n=80
 profile=[(.20,11.37),(.217,11.45),(.25,11.52),(.32,11.61),(.43,11.70),(.56,11.76),(.69,None)]
 for r,z in profile:
  for i in range(n):
   t=2*math.pi*i/n;x=xy[0]+r*math.cos(t);y=xy[1]+r*math.sin(t);vertices.append([x,y,z if z is not None else ceiling([x,y])+.003])
 faces=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(len(profile)-1) for i in range(n)]
 new=bpy.data.meshes.new(ob.name+'_seated');new.from_pydata(vertices,[],faces);new.update();new.materials.append(old.materials[0]);ob.data=new
 for p in new.polygons:p.use_smooth=True
 errors=[v[2]-ceiling(v[:2]) for v in vertices[-n:]];assert min(errors)>.0029 and max(errors)<.0031
 ob['roof_connection']='Head ring follows actual soffit triangles with 3mm embedded overlap; shape remains photograph-informed inference';rows.append({'object':ob.name,'overlap_range_m':[min(errors),max(errors)]})
for p in bpy.data.objects['BE_WEST_SHELTER_FASCIA'].data.polygons:p.use_smooth=True
scene['version']='G1_008r2';scene.camera=bpy.data.objects['BE_QA_WEST_PLATFORM_REVERSE'];bpy.context.view_layer.update()
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.region_3d.view_perspective='CAMERA'
native=ROOT/'native/G1_008r2_west_shelter_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native));record=json.loads((ROOT/'runtime/station_road_working.json').read_text());record.update(version=scene['version'],native=str(native),published_as=None,accepted=False,not_published=True)
(ROOT/'runtime/station_road_working.json').write_text(json.dumps(record,indent=2));out=ROOT/'evidence/G1_008r2';out.mkdir(exist_ok=True);(out/'capital_join.json').write_text(json.dumps({'version':scene['version'],'matches':rows,'accepted':False},indent=2));print(json.dumps({'version':scene['version'],'native':str(native),'capital_connections':rows}))
