"""Replace spoked tube roots with a continuous buttressed root collar and PBR atlas."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_011r2'
bark=bpy.data.materials['bark_platanus'];flaking=bpy.data.materials['HB | inferred flaking plane bark']
def atlasmat(name,directory,strength):
 m=bark.copy();m.name=name
 for n in m.node_tree.nodes:
  if n.type=='TEX_IMAGE' and n.image:
   for role,filename in [('Diffuse','albedo'),('Rough','roughness'),('nor_gl','normal_gl')]:
    if role in n.image.name:
     space=n.image.colorspace_settings.name;im=bpy.data.images.load(str(R/directory/(filename+'.png')),check_existing=True);im.colorspace_settings.name=space;n.image=im;n.interpolation='Linear'
  if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=strength
 return m
atlas=atlasmat('HB | continuous plane trunk atlas','derived/materials/plane_trunk',.45)
soil=atlasmat('HB | compacted granular tree soil','derived/materials/tree_soil',.60)
source=R/'native/G1_011r1_haus_tree_working.blend'
records=[(119962,'HB_TREE_119962_WOOD','HB_TREE_119962_WOOD',441+8*180,48,9,'derived/haus_bellevue/tree_119962_input.json'),(69773,'BE_TREE_69773_WOOD','BE_TREE_69773_WOOD.001',369+7*117,40,9,'derived/bellevue/west_context/tree_69773_input.json')]
report=[]
for ident,objname,meshname,skip,sides,rows,ip in records:
 d=json.loads((R/ip).read_text());root=np.array([*d['source']['geometry']['coordinates'],d['ground_ln02_m']])-np.array(d['origin']);ob=bpy.data.objects[objname]
 with bpy.data.libraries.load(str(source),link=False) as (a,b):b.meshes=[meshname]
 old=b.meshes[0];assert old is not None
 # Original vertex ordering: first the trunk, then separate spoke roots, then crown branches.
 ov=np.array([v.co[:] for v in old.vertices]);rings=ov[:rows*(sides+1)].reshape(rows,sides+1,3);centers=rings[:,:sides].mean(axis=1)-root;rad=np.mean(np.linalg.norm(rings[:,:sides,:2]-rings[:,:sides,:2].mean(axis=1)[:,None,:],axis=2),axis=1)
 assert abs(centers[-1,2])<5 and skip<len(ov)
 remap={i:j for j,i in enumerate(range(skip,len(ov)))};vv=ov[skip:].tolist();faces=[];uvs=[];materials=[]
 for p in old.polygons:
  if all(i>=skip for i in p.vertices):
   faces.append(tuple(remap[i] for i in p.vertices));scale=1 if p.material_index else 1.5/2.4
   uvs.append([tuple(old.uv_layers.active.data[li].uv*scale) for li in p.loop_indices]);materials.append(0)
 # Smooth connected root flare; the broad base sits just below the existing soil.
 angles=128;zs=np.r_[np.linspace(-.065,.8,36),np.linspace(.86,centers[-1,2],56)];base=len(vv);girth=2*math.pi*(.36 if ident==119962 else .295)
 for j,z in enumerate(zs):
  cen=np.array([np.interp(z,centers[:,2],centers[:,i]) for i in range(2)]);rr=float(np.interp(z,centers[:,2],rad));rr=min(rr,.425 if ident==119962 else .365) if z<.15 else rr
  for k in range(angles+1):
   a=2*math.pi*k/angles;lobes=(.5+.5*math.cos(7*a+.2*math.sin(3*a)))**3
   flare=(.07+.34*lobes)*math.exp(-max(z,0)/.255)*(1 if ident==119962 else .8)
   radius=rr+flare+.006*math.sin(5*a+1.8*z)*math.exp(-max(z,0)/2)
   vv.append((root+np.r_[cen+radius*np.array([math.cos(a),math.sin(a)]),z]).tolist())
 for j in range(len(zs)-1):
  for k in range(angles):
   a=base+j*(angles+1)+k;faces.append((a,a+1,a+angles+2,a+angles+1));materials.append(1)
   uvs.append([(k/angles*girth/2.5,zs[j]/4.5),((k+1)/angles*girth/2.5,zs[j]/4.5),((k+1)/angles*girth/2.5,zs[j+1]/4.5),(k/angles*girth/2.5,zs[j+1]/4.5)])
 me=bpy.data.meshes.new(objname+'_continuous_root');me.from_pydata(vv,[],faces);me.update();me.materials.append(flaking);me.materials.append(atlas);uv=me.uv_layers.new(name='physical_bark')
 for p,coords,mi in zip(me.polygons,uvs,materials):
  p.material_index=mi;p.use_smooth=True
  for li,co in zip(p.loop_indices,coords):uv.data[li].uv=co
 ob.data=me;ob['root_bark_note']='Continuous buttressed root collar and pixel-resolution ragged bark atlas; individual form inferred, surveyed XY and height retained.'
 if old.users==0:bpy.data.meshes.remove(old)
 report.append({'tree':ident,'wood_vertices':len(me.vertices),'old_spoked_root_vertices_removed':skip,'atlas_dimensions_m':[2.5,4.5]})
for name in ['BE_WEST_TREE_SOIL','HB_SIDEWALK_SOIL']:
 ob=bpy.data.objects[name];ob.data.materials.clear();ob.data.materials.append(soil);uv=ob.data.uv_layers.active or ob.data.uv_layers.new(name='soil_metres')
 for p in ob.data.polygons:
  p.material_index=0
  for li in p.loop_indices:
   v=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(v.x,v.y)
 ob['surface_basis']='Inferred compacted granular soil, original procedural 1m material; surveyed tree position retained.'
s['version']='G1_011r3';s.camera=bpy.data.objects['HB_QA_TREE_BASE'];bpy.context.view_layer.update();bpy.ops.file.pack_all();native=R/'native/G1_011r3_haus_tree_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=s['version'],native=str(native),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2))
e=R/'evidence/G1_011r3';e.mkdir(exist_ok=True);(e/'root_bark_refinement.json').write_text(json.dumps({'version':s['version'],'trees':report,'soil_pits':2,'accepted':False},indent=2));print(json.dumps({'version':s['version'],'trees':report}))
