"""Replace patchy triangle UVs and build physically open roof oculi."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');sc=bpy.context.scene;assert sc['version']==globals().get('BASE_VERSION','G1_010r1');V=globals().get('VERSION','G1_010r2')
d=json.loads((R/'derived/haus_bellevue/roof_details_input.json').read_text());base=json.loads((R/'derived/haus_bellevue/upper_input.json').read_text());C=np.array(base['corner']['center_local'])
col=bpy.data.collections['17_HAUS_BELLEVUE_UPPER']
for old in list(col.objects):
 if old.name.startswith('HU_OCULUS_'):bpy.data.objects.remove(old,do_unlink=True)
stone=bpy.data.materials['beige_wall_001'];slate=bpy.data.materials['roof_slates_03'];metal=bpy.data.materials['HU | weathered zinc flashing'];glass=bpy.data.materials['HB | clear shop glazing 8mm'];seal=bpy.data.materials['HB | recessed glazing gaskets'];room=bpy.data.materials['HU | unopened upper room mineral wall']

def mesh(name,verts,faces,materials,uvcoords=None,smooth=False):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new(name,me);col.objects.link(ob)
 for m in materials:me.materials.append(m)
 uv=me.uv_layers.new(name='continuous_roof_metres')
 for p in me.polygons:
  p.use_smooth=smooth
  for li in p.loop_indices:
   vi=me.loops[li].vertex_index;v=me.vertices[vi].co;uv.data[li].uv=uvcoords[vi] if uvcoords is not None else (v.x/3,v.z/3)
 ob['egid']=9011202;ob['place']='Haus Bellevue roof';ob['evidence_basis']=d['basis'];ob['quality_status']='native candidate, not accepted';ob['collision_role']='solid_pending_runtime'
 return ob

for kind in ['slate','roof_metal','dormer_wall']:
 name='HU_SOURCE_ROOF_'+kind.upper();old=bpy.data.objects.get(name)
 if old:bpy.data.objects.remove(old,do_unlink=True)
 pieces=[p for p in d['pieces'] if p['kind']==kind];vv=np.array([p['vertices'] for p in pieces]).reshape(-1,3);uv=np.array([p['uv'] for p in pieces]).reshape(-1,2)
 mat={'slate':slate,'roof_metal':metal,'dormer_wall':stone}[kind]
 ob=mesh(name,vv.tolist(),np.arange(len(vv)).reshape(-1,3).tolist(),[mat,slate,metal],uv)
 # Official WallSurface includes dome upstands. Only its upper dome patches
 # receive slate and its top rim receives zinc; the lower attic stays masonry.
 if kind=='dormer_wall':
  for p in ob.data.polygons:
   v=np.array([ob.data.vertices[i].co[:] for i in p.vertices]);r=np.linalg.norm(v[:,:2]-C,axis=1)
   if r.max()<5.75 and v[:,2].mean()>31.49:p.material_index=2 if v[:,2].mean()>35.78 else 1
 # Weld coincident source triangle vertices for coherent dome shading; UV seams
 # stay loop based and coordinates do not move.
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=.000015);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(ob.data);bm.free();ob.data.update()
 if kind=='slate':
  for p in ob.data.polygons:
   v=np.array([ob.data.vertices[i].co[:] for i in p.vertices]);p.use_smooth=np.linalg.norm(v[:,:2]-C,axis=1).max()<5.75
 if kind!='dormer_wall':
  mod=ob.modifiers.new('Roofing physical backing','SOLIDIFY');mod.thickness=.025;mod.offset=-1

for i,w in enumerate(d['windows']):
 c=np.array(w['center']);n=np.array(w['normal']);right=np.array(w['right']);up=np.array(w['up']);N=96
 def ellipse(rx,ry,depth):return [c+right*rx*np.cos(t)+up*ry*np.sin(t)+n*depth for t in np.linspace(0,2*np.pi,N,endpoint=False)]
 # Closed profiled stone surround and separate metal flashing, gasket, glass.
 profile=[(.445,.705,-.08),(.445,.705,.11),(.475,.735,.16),(.522,.782,.14),(.553,.813,.055),(.553,.813,-.05)]
 verts=[p.tolist() for a,b,dep in profile for p in ellipse(a,b,dep)];faces=[]
 for j in range(len(profile)):
  for k in range(N):faces.append((j*N+k,j*N+(k+1)%N,((j+1)%len(profile))*N+(k+1)%N,((j+1)%len(profile))*N+k))
 mesh(f'HU_OCULUS_{i}_STONE',verts,faces,[stone],smooth=True)
 for suffix,prof,mat in [('FLASHING',[(.555,.815,-.025),(.605,.865,-.025),(.605,.865,-.040),(.555,.815,-.040)],metal),('SEAL',[(.406,.65,-.030),(.444,.704,-.030),(.444,.704,-.052),(.406,.65,-.052)],seal)]:
  vv=[p.tolist() for a,b,dep in prof for p in ellipse(a,b,dep)];ff=[]
  for j in range(len(prof)):
   for k in range(N):ff.append((j*N+k,j*N+(k+1)%N,((j+1)%len(prof))*N+(k+1)%N,((j+1)%len(prof))*N+k))
  mesh(f'HU_OCULUS_{i}_{suffix}',vv,ff,[mat],smooth=True)
 vv=[p.tolist() for dep in [-.040,-.048] for p in ellipse(.408,.652,dep)]
 ff=[tuple(range(N-1,-1,-1)),tuple(range(N,2*N))]+[(k,(k+1)%N,(k+1)%N+N,k+N) for k in range(N)]
 pane=mesh(f'HU_OCULUS_{i}_GLASS',vv,ff,[glass]);bm=bmesh.new();bm.from_mesh(pane.data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(pane.data);bm.free()
 # Closed reveal well behind glazing; this is a depth cue, not an opened room.
 vv=[p.tolist() for dep in [-.055,-.66] for p in ellipse(.43,.685,dep)]
 ff=[tuple(range(N,2*N))]+[(k,(k+1)%N,(k+1)%N+N,k+N) for k in range(N)]
 mesh(f'HU_OCULUS_{i}_REVEAL',vv,ff,[room])

sc['version']=V;bpy.context.view_layer.update();bpy.ops.file.pack_all();native=R/'native'/f'{V}_haus_upper_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=sc['version'],native=str(native),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2))
e=R/'evidence'/V;e.mkdir(exist_ok=True);(e/'roof_refinement.json').write_text(json.dumps({'version':sc['version'],'windows':d['windows'],'basis':d['basis'],'roof_source_nonplanarity_m':.0327104,'native':str(native),'accepted':False},indent=2))
print(json.dumps({'version':sc['version'],'upper_objects':len(col.objects),'native':str(native),'accepted':False}))
