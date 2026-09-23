"""G1_019: complete source footprint with fifteen individually parameterized trees.

Resume is guarded by per-tree completion receipts. Native save occurs only after
all replacements and human-height camera support checks have succeeded.
"""
import bpy,json,math,ast,hashlib,traceback
import numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_018r3'
D=R/'derived/bellevue/limmat_sidewalk';p=json.loads((D/'ground_input.json').read_text(encoding='utf-8'));E=R/'evidence/G1_019';E.mkdir(exist_ok=True)
rootcol=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION']
def getcollection(name):
 col=bpy.data.collections.get(name)
 if col is None:col=bpy.data.collections.new(name);rootcol.children.link(col)
 return col
groundcol=getcollection('30_LIMMAT_SIDEWALK_GROUND');collection=getcollection('31_LIMMAT_SIDEWALK_TREES')
if not groundcol.get('complete',False):
 assert len(groundcol.objects)==0,'Inspect incomplete ground before resuming'
 mats={'asphalt':'asphalt_03','curb_top':'BE | fine mineral curb proxy','curb_face':'BE | fine mineral curb proxy','curb_joint':'BE | curb mineral mortar','soil':'HB | compacted granular tree soil','pit_edge':'asphalt_03','retaining_edge':'BE | fine mineral curb proxy'}
 for key,tris in p['parts'].items():
  if not tris:continue
  t=np.asarray(tris);name='LM_'+key.upper();me=bpy.data.meshes.new(name);me.from_pydata(t.reshape(-1,3).tolist(),[],np.arange(t.size//3).reshape(-1,3).tolist());me.update();me.materials.append(bpy.data.materials[mats[key]])
  uv=me.uv_layers.new(name='metre_scale');uv.data.foreach_set('uv',np.asarray(p['uv'][key],dtype=np.float32).ravel())
  ob=bpy.data.objects.new(name,me);groundcol.objects.link(ob);ob['source_id']='av_bo_boflaeche_a.24105';ob['quality_status']='working_not_accepted';ob['evidence_basis']=p['report']['basis'];ob['collision_role']='potential_walkable_not_runtime_enabled' if key in ['asphalt','curb_top','soil'] else 'pending_runtime';ob['construction_batch']='G1_019'
 groundcol['complete']=True

src=(R/'tools/blender_build_south_public_space.py').read_text(encoding='utf-8').replace('BS_TREE_','LM_TREE_');module=ast.parse(src)
start=next(i for i,n in enumerate(module.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='old' for t in n.targets));end=next(i for i,n in enumerate(module.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='cutpath' for t in n.targets))
plane_code=compile(ast.Module(body=module.body[start:end],type_ignores=[]),'limmat_plane_growth','exec')
old=ast.parse((R/'tools/blender_build_bellevue_plane_tree.py').read_text());helper=compile(ast.Module(body=[n for n in old.body if isinstance(n,ast.FunctionDef) and n.name in ['unit','add_tube','curve']],type_ignores=[]),'tree_helpers','exec');exec(helper)

def sophora_materials():
 name='LM | Sophora gray-brown furrowed bark'
 if name not in bpy.data.materials:
  mat=bpy.data.materials.new(name);mat.use_nodes=True;b=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');nodes=mat.node_tree.nodes;links=mat.node_tree.links
  for fn,socket in [('albedo','Base Color'),('roughness','Roughness'),('normal_gl',None)]:
   im=bpy.data.images.load(str(R/'derived/materials/sophora_bark'/f'{fn}.png'),check_existing=True)
   if fn!='albedo':im.colorspace_settings.name='Non-Color'
   tex=nodes.new('ShaderNodeTexImage');tex.image=im
   if socket:links.new(tex.outputs['Color'],b.inputs[socket])
   else:
    normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.52;links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],b.inputs['Normal'])
  mat['basis']='Original numerical gray-brown bark material; individual texture inferred';mat['texture_dimensions_m']=[1.2,4.0]
 for name,color,rough in [('LM | Sophora green young shoots',(.065,.081,.025),.78),('LM | Sophora compound leaf',(.043,.105,.016),.68)]:
  if name in bpy.data.materials:continue
  mat=bpy.data.materials.new(name);mat.use_nodes=True;b=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;mat.diffuse_color=(*color,1)
  if 'leaf' in name:
   vc=mat.node_tree.nodes.new('ShaderNodeVertexColor');vc.layer_name='LeafColor';mat.node_tree.links.new(vc.outputs['Color'],b.inputs['Base Color']);b.inputs['Subsurface Weight'].default_value=.04;b.inputs['Subsurface Scale'].default_value=.002;mat.use_backface_culling=False
 return [bpy.data.materials[n] for n in ['LM | Sophora gray-brown furrowed bark','LM | Sophora green young shoots','LM | Sophora compound leaf']]

all_reports=[]
for entry in p['pits']:
 ident=entry['source']['properties']['objectid'];names=[f'LM_TREE_{ident}_{role}' for role in ['WOOD','TWIGS','LEAVES']]
 if any(n in bpy.data.objects for n in names):
  assert all(n in bpy.data.objects for n in names) and collection.get(f'complete_{ident}',False),'Incomplete tree needs inspection'
  all_reports.append(json.loads(collection[f'report_{ident}']));continue
 if 'Platanus' in entry['source']['properties']['baumart_lat']:
  td={'trees':[entry]};exec(plane_code);rec=reports[0]
  me=bpy.data.objects[names[0]].data;layer=me.uv_layers.active;ids=[i for i,m in enumerate(me.materials) if m.name=='HB | continuous plane trunk atlas'];loops=[li for f in me.polygons if f.material_index in ids for li in f.loop_indices];vmax=max(layer.data[li].uv.y for li in loops)
  if vmax>.998:
   for li in loops:
    vv=layer.data[li].uv.y
    if vv>.65:layer.data[li].uv.y=.65+(vv-.65)*(.998-.65)/(vmax-.65)
  assert max(layer.data[li].uv.y for li in loops)<.999
 else:
  mats=sophora_materials();rng=np.random.default_rng(ident);root=np.array([*entry['source']['geometry']['coordinates'],entry['ground_ln02_m']])-np.array(entry['origin']);height=entry['height_m'];radius=np.array(entry['inferred']['crown_radius_m']);diam=entry['inferred']['trunk_diameter_m'];clearance=entry['inferred']['branch_clearance_m']
  groups={key:{'v':[],'f':[],'uv':[],'colors':[]} for key in ['wood','twigs','leaves']};branch_count=0;leaf_count=0;compound_count=0
  phase=rng.uniform(0,2*np.pi);lean=rng.uniform(-.09,.09,2);sides=48;zs=np.r_[np.linspace(-.065,.5,19),np.linspace(.55,clearance+.6,29)];gg=groups['wood']
  for z in zs:
   centre=lean*max(z,0)/(clearance+.6);r=diam*.5*(1-.4*np.clip(z/(clearance+.6),0,1))
   for k in range(sides+1):
    a=k/sides*2*np.pi;lobe=(.5+.5*np.cos(5*a+phase+.17*np.sin(a*2)))**3;rr=r+(.012+diam*.25*lobe)*np.exp(-max(z,0)/.19)+.002*np.sin(4*a+z)
    gg['v'].append(np.r_[centre+rr*np.array([np.cos(a),np.sin(a)]),z]);gg['uv'].append((k/sides*np.pi*diam/1.5,z/1.5))
  for j in range(len(zs)-1):
   for k in range(sides):
    a=j*(sides+1)+k;gg['f'].append((a,a+1,a+sides+2,a+sides+1))
  terminals=[];scaffolds=5
  for i in range(scaffolds):
   a=phase+2*np.pi*i/scaffolds+rng.uniform(-.30,.30);z0=clearance-.40+(i%3)*.19;startp=np.r_[lean*z0/(clearance+.6),z0];endp=np.array([np.cos(a)*radius[0]*.38,np.sin(a)*radius[1]*.36,height*rng.uniform(.67,.76)]);primary=curve(startp,endp,[0,0,.15],20);add_tube(primary,np.linspace(diam*.17,.028,20),sides=16)
   for j in range(5):
    at=primary[6+j*2];az=a+(j-2)*.47+rng.uniform(-.24,.24);spread=[.77,.99,1.,.77,.46][j];z=clearance+(height-clearance)*[.29,.45,.64,.80,.91][j]+rng.uniform(-.18,.18);endp=np.array([np.cos(az)*radius[0]*spread,np.sin(az)*radius[1]*spread,z]);branch=curve(at,endp,[0,0,.15],15);add_tube(branch,np.linspace(diam*.065,.006,15),sides=10)
    for k in range(6):
     at=branch[5+k];az2=az+(1 if k%2 else -1)*rng.uniform(.40,1.15);endp=at+unit([np.cos(az2),np.sin(az2),rng.uniform(-.10,.90)])*rng.uniform(.50,.95);r=np.linalg.norm(endp[:2]/radius)
     if r>1:endp[:2]/=r
     endp[2]=min(endp[2],height-.25);secondary=curve(at,endp,[0,0,.07],9);add_tube(secondary,np.linspace(.008,.002,9),key='twigs',sides=6)
     for k2 in range(6):
      base=secondary[3+k2//2];aa=az2+(1 if k2%2 else -1)*rng.uniform(.45,1.5);dest=base+unit([np.cos(aa),np.sin(aa),rng.uniform(-.42,.45)])*rng.uniform(.25,.49);twig=curve(base,dest,[0,0,-.025],5);add_tube(twig,np.linspace(.0021,.0006,5),key='twigs',sides=4);terminals.append(twig)
  # Alternate pinnately compound leaves: rachis + opposite/subopposite leaflets
  # and one terminal leaflet. Size7..13 leaflets, entire ovate/lanceolate outline.
  outline=np.array([[0,0],[-.21,.18],[-.29,.42],[-.22,.67],[0,1],[.23,.68],[.29,.43],[.20,.18]])
  for twig in terminals:
   for j in range(5 if height>=11 else 4):
    along=.13+.80*j/(4 if height>=11 else 3);f=along*(len(twig)-1);k=int(f);anchor=twig[k]*(1-(f-k))+twig[min(k+1,len(twig)-1)]*(f-k);tangent=unit(twig[-1]-twig[0]);side=unit(np.cross([0,0,1],tangent))*(1 if j%2 else -1);axis=unit(.75*side+.35*tangent+[0,0,rng.uniform(-.48,.30)]);length=rng.uniform(.18,.27);tip=anchor+axis*length
    rachis=curve(anchor,tip,[0,0,-.014],7);add_tube(rachis,np.linspace(.00072,.00025,7),key='twigs',sides=3);normal=unit([rng.uniform(-.4,.4),rng.uniform(-.4,.4),1]);side=unit(np.cross(axis,normal));pairs=int(rng.integers(3,7));sites=[]
    for pair in range(pairs):
     t=.18+.66*pair/max(1,pairs-1)
     for direction in [-1,1]:
      tt=min(.94,t+(0.018 if direction==1 else 0));q=tt*6;k=int(q);base=rachis[k]*(1-(q-k))+rachis[min(k+1,6)]*(q-k);leafaxis=unit(side*direction*.82+axis*.40+[0,0,rng.uniform(-.22,.22)]);sites.append((base,leafaxis))
    sites.append((rachis[-1],axis));compound_count+=1
    for base,leafaxis in sites:
     width=unit(np.cross(leafaxis,normal));nn=unit(np.cross(width,leafaxis));le=rng.uniform(.028,.052);variation=rng.uniform(.77,1.17);col=(.041*variation,.103*variation,.016*variation,1);gg=groups['leaves'];first=len(gg['v'])
     for xx,yy in np.vstack([[0,.43],outline]):
      gg['v'].append(base+leafaxis*yy*le+width*xx*le+nn*(abs(xx)*.095+np.sin(yy*np.pi)*.012)*le);gg['uv'].append((xx+.5,yy));gg['colors'].append(col)
     for q in range(len(outline)):gg['f'].append((first,first+q+1,first+(q+1)%len(outline)+1))
     leaf_count+=1
  maxz=max(v[2] for gg in groups.values() for v in gg['v']);stretch=(height-clearance)/(maxz-clearance);objects=[]
  for key,mat in zip(['wood','twigs','leaves'],mats):
   gg=groups[key];v=np.array(gg['v']);above=v[:,2]>clearance;v[above,2]=clearance+(v[above,2]-clearance)*stretch;v+=root;name=f'LM_TREE_{ident}_{key.upper()}';me=bpy.data.meshes.new(name);me.from_pydata(v.tolist(),[],gg['f']);me.update();me.materials.append(mat);uv=me.uv_layers.new(name='physical_bark' if key=='wood' else 'UVMap');arr=np.asarray(gg['uv'],dtype=np.float32)
   if key=='wood':arr*=np.array([1.5/1.2,1.5/4.])
   uv.data.foreach_set('uv',np.array([arr[l.vertex_index] for l in me.loops],dtype=np.float32).ravel())
   for face in me.polygons:face.use_smooth=True
   if key=='leaves':
    ca=me.color_attributes.new(name='LeafColor',type='FLOAT_COLOR',domain='POINT');ca.data.foreach_set('color',np.asarray(gg['colors'],dtype=np.float32).ravel())
   ob=bpy.data.objects.new(name,me);collection.objects.link(ob);ob['source_id']=entry['source']['id'];ob['evidence_basis']=entry['basis'];ob['quality_status']='working_not_accepted';ob['collision_role']='solid_pending_runtime' if key=='wood' else 'visual_only';objects.append(ob)
  rec={'source_id':entry['source']['id'],'height_m':height,'ground_ln02_m':entry['ground_ln02_m'],'leaflet_count':leaf_count,'compound_leaves':compound_count,'branch_tubes':branch_count,'vertices':sum(len(o.data.vertices) for o in objects),'morphology_reference':'https://plants.ces.ncsu.edu/plants/styphnolobium-japonicum/','individual_form_inferred':True}
 for name in names:bpy.data.objects[name]['construction_batch']='G1_019'
 collection[f'complete_{ident}']=True;collection[f'report_{ident}']=json.dumps(rec);all_reports.append(rec)
 (E/'tree_build_progress.json').write_text(json.dumps({'base':'G1_018r3','trees':all_reports,'native_checkpoint_written':False},indent=2));print('TREE_COMPLETE',ident,flush=True)
 # Discard construction arrays between trees; keep only the native meshes.
 for key in ['groups','gg','v','arr','allv','terminals']:
  globals().pop(key,None)

cutpath=R/'derived/bellevue/west_context/limmat_sidewalk_photo_cut.json';cut=json.loads(cutpath.read_text());before={str(x['node']):x for x in json.loads((R/s['photo_cut_file']).read_text())['overrides']};working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};originals={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects};changed=[]
for q in cut['overrides']:
 key=str(q['node'])
 if before.get(key)==q:continue
 ob,src=working[key],originals[key];assert ob.matrix_basis==src.matrix_basis;vv=np.asarray(q['vertices']).reshape(-1,3);tex=np.asarray(q['uv_source_v_unflipped']).reshape(-1,2);me=bpy.data.meshes.new('LM_CONTEXT_'+key);me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');tex[:,1]=1-tex[:,1];uv.data.foreach_set('uv',tex.astype(np.float32).ravel());oldmesh=ob.data;ob.data=me
 if oldmesh.users==0:bpy.data.meshes.remove(oldmesh)
 ob['construction_mask']=cut['mask_basis'];changed.append(key)
bpy.context.view_layer.update()
cameras=[('BE_QA_LIMMAT_SOUTH',[2683506,1246864],[2683501,1246885,412],28),('BE_QA_LIMMAT_NORTH',[2683494.4,1246919],[2683483,1246955,410],30),('BE_QA_LIMMAT_REVERSE',[2683487.0,1246944],[2683504,1246880,410],30),('BE_QA_LIMMAT_PLANE_ROOT',[2683503,1246879],[2683500.389,1246880.130,408.55],42),('BE_QA_LIMMAT_SOPHORA_ROOT',[2683495,1246915],[2683497.723,1246913.817,408.5],45)]
camera_records=[]
for name,xy,target,lens in cameras:
 local=np.array(xy)-p['origin'][:2];levels=[]
 for ob in groundcol.objects:
  if ob.name not in ['LM_ASPHALT','LM_CURB_TOP','LM_SOIL']:continue
  hit,point,_,_=ob.ray_cast(Vector((*local,30)),Vector((0,0,-1)))
  if hit:levels.append(point.z)
 assert levels,('Camera not on authored ground',name,xy)
 floor=max(levels);co=bpy.data.objects.get(name)
 if co is None:
  cd=bpy.data.cameras.new(name);co=bpy.data.objects.new(name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(co)
 co.location=(*local,floor+1.65);co.rotation_euler=(Vector(np.array(target)-p['origin'])-co.location).to_track_quat('-Z','Y').to_euler();co.data.lens=lens;co['eye_height_m']=1.65;co['floor_height_local']=floor;camera_records.append({'name':name,'floor_local':floor,'eye_height_m':1.65})
s['version']='G1_019';s['photo_cut_file']=str(cutpath.relative_to(R));s.camera=bpy.data.objects['BE_QA_LIMMAT_SOUTH'];bpy.context.view_layer.update();bpy.ops.file.pack_all()
native=R/'native/G1_019_limmat_sidewalk_working.blend';assert not native.exists();bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=s['version'],native=str(native),source_cut_file=s['photo_cut_file'],source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True,next='Inspect all new sidewalk cameras and both species; fix surface/contact/canopy defects, then export and actually review runtime. Defaults remain007r5.')
(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2))
(E/'construction.json').write_text(json.dumps({'version':s['version'],'native':str(native),'ground':p['report'],'trees':all_reports,'changed_photo_nodes':changed,'original_photo_nodes':len(originals),'camera_grounding':camera_records,'new_objects':len(groundcol.objects)+len(collection.objects),'native_checkpoint_written':True,'accepted':False,'runtime_exported':False,'natural_use_verified':False},indent=2))
print('G1_019_NATIVE_SAVED',native,flush=True)
