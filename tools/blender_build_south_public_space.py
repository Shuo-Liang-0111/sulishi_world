"""Author AV3573 ground and two individually grown source-located plane trees."""
import bpy,bmesh,json,math,ast,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_012r5';D=R/'derived/bellevue/south_context';p=json.loads((D/'platform_input.json').read_text(encoding='utf-8'));td=json.loads((D/'tree_inputs.json').read_text(encoding='utf-8'));rootcol=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'];assert '21_BELLEVUE_SOUTH_GROUND' not in bpy.data.collections
groundcol=bpy.data.collections.new('21_BELLEVUE_SOUTH_GROUND');rootcol.children.link(groundcol);collection=bpy.data.collections.new('22_BELLEVUE_SOUTH_TREES');rootcol.children.link(collection)
mats={'asphalt':bpy.data.materials['asphalt_03'],'curb_top':bpy.data.materials['BE | fine mineral curb proxy'],'curb_face':bpy.data.materials['BE | fine mineral curb proxy'],'curb_joint':bpy.data.materials['BE | curb mineral mortar'],'soil':bpy.data.materials['HB | compacted granular tree soil']}
for key,tris in p['parts'].items():
 t=np.array(tris);name='BS_'+key.upper();me=bpy.data.meshes.new(name);me.from_pydata(t.reshape(-1,3).tolist(),[],np.arange(t.size//3).reshape(-1,3).tolist());me.update();me.materials.append(mats[key]);uv=me.uv_layers.new(name='metre_scale');uv.data.foreach_set('uv',np.array(p['uv'][key],dtype=np.float32).reshape(-1));ob=bpy.data.objects.new(name,me);groundcol.objects.link(ob);ob['source_id']='av_bo_boflaeche_a.3573';ob['evidence_basis']=p['report']['basis'];ob['quality_status']='working_not_accepted';ob['collision_role']='potential_walkable_not_runtime_enabled' if key in ['asphalt','curb_top'] else 'not_runtime_enabled'
old=ast.parse((R/'tools/blender_build_bellevue_plane_tree.py').read_text(encoding='utf-8'))
helper=compile(ast.Module(body=[n for n in old.body if isinstance(n,ast.FunctionDef) and n.name in ['unit','add_tube','curve']],type_ignores=[]),'tree_geometry','exec')
start=next(i for i,n in enumerate(old.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='outline' for t in n.targets));end=next(i for i,n in enumerate(old.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='allv' for t in n.targets));leafcode=compile(ast.Module(body=old.body[start:end],type_ignores=[]),'plane_leaves','exec')
woodmat=bpy.data.materials['HB | inferred flaking plane bark'];atlas=bpy.data.materials['HB | continuous plane trunk atlas'];twigmat=bpy.data.materials['BE | plane young twigs'];leafmat=bpy.data.materials['BE | plane summer leaf'];reports=[]
for data in td['trees']:
 ident=data['source']['properties']['objectid'];rng=np.random.default_rng(ident);root=np.array([*data['source']['geometry']['coordinates'],data['ground_ln02_m']])-np.array(data['origin']);height=data['height_m'];radius=np.array(data['inferred']['crown_radius_m']);girth=data['inferred']['trunk_diameter_m'];clearance=data['inferred']['branch_clearance_m'];groups={k:{'v':[],'f':[],'uv':[],'colors':[]} for k in ['wood','twigs','leaves']};branch_count=0;leaf_count=0;exec(helper)
 # One continuous buttressed collar rather than separate conical root spokes.
 g=groups['wood'];sides=80;zs=np.r_[np.linspace(-.075,.75,27),np.linspace(.82,clearance+.5,41)];phase=rng.uniform(0,6.28);lean=np.array([rng.uniform(-.12,.12),rng.uniform(-.13,.13)])
 for z in zs:
  centre=lean*(max(z,0)/(clearance+.5))**1.4;rad=girth*.5*(1-.45*np.clip(z/(clearance+.5),0,1))
  for k in range(sides+1):
   a=2*math.pi*k/sides;lobes=(.5+.5*math.cos(7*a+phase+.15*math.sin(3*a)))**3;flare=(.025+girth*.45*lobes)*math.exp(-max(z,0)/.25);rr=rad+flare+.004*math.sin(5*a+z)
   g['v'].append(np.r_[centre+rr*np.array([math.cos(a),math.sin(a)]),z]);g['uv'].append((k/sides*math.pi*girth/2.5,max(.001,z/4.5)))
 for j in range(len(zs)-1):
  for k in range(sides):
   a=j*(sides+1)+k;g['f'].append((a,a+1,a+sides+2,a+sides+1))
 trunk_faces=len(g['f']);trunk_vertices=len(g['v']);terminals=[];scaffolds=5 if ident==68441 else 6
 for i in range(scaffolds):
  a=phase+2*np.pi*i/scaffolds+rng.uniform(-.22,.22);z0=clearance-.6+(i%3)*.30;startp=np.r_[lean*(z0/(clearance+.5))**1.4,z0];top=np.array([np.cos(a)*radius[0]*rng.uniform(.30,.46),np.sin(a)*radius[1]*rng.uniform(.3,.47),height*rng.uniform(.60,.71)]);primary=curve(startp,top,[-.24*np.cos(a),-.21*np.sin(a),.32],27);add_tube(primary,np.linspace(girth*.19,.052 if ident==68441 else .065,27),sides=22)
  for j in range(5):
   at=primary[7+j*3];az=a+(j-2)*.43+rng.uniform(-.23,.23);spread=[.80,.96,1.,.80,.54][j]+rng.uniform(-.045,.035);z=clearance+(height-clearance)*[.24,.43,.61,.79,.91][j]+rng.uniform(-.3,.3);ep=np.array([np.cos(az)*radius[0]*spread,np.sin(az)*radius[1]*spread,z]);branch=curve(at,ep,[-.07*np.cos(az),-.07*np.sin(az),rng.uniform(.12,.38)],17);add_tube(branch,np.linspace(girth*.075,.010,17),sides=12)
   for k in range(7):
    attach=branch[6+k];az2=az+(1 if k%2 else -1)*rng.uniform(.36,1.17);direction=unit([np.cos(az2),np.sin(az2),rng.uniform(.10,1.02)]);ep2=attach+direction*rng.uniform(.95,1.65);radial=np.linalg.norm(ep2[:2]/radius)
    if radial>1:ep2[:2]/=radial
    ep2[2]=min(ep2[2],height-.45);secondary=curve(attach,ep2,[0,0,.12],10);add_tube(secondary,np.linspace(.014,.0033,10),key='twigs',sides=7)
    for n in range(8):
     base=secondary[min(3+n//2,8)];theta=az2+(1 if n%2 else -1)*rng.uniform(.4,1.65);dest=base+unit([np.cos(theta),np.sin(theta),rng.uniform(-.4,.55)])*rng.uniform(.35,.78);twig=curve(base,dest,[0,0,-.035],6);add_tube(twig,np.linspace(.0032,.00065,6),key='twigs',sides=5);terminals.append(twig)
 exec(leafcode)
 maxz=max(v[2] for gg in groups.values() for v in gg['v']);stretch=(height-clearance)/(maxz-clearance);objects=[]
 for key,material in [('wood',woodmat),('twigs',twigmat),('leaves',leafmat)]:
  gg=groups[key];v=np.array(gg['v']);above=v[:,2]>clearance;v[above,2]=clearance+(v[above,2]-clearance)*stretch;v+=root;name=f'BS_TREE_{ident}_{key.upper()}';me=bpy.data.meshes.new(name);me.from_pydata(v.tolist(),[],gg['f']);me.update();me.materials.append(material)
  if key=='wood':me.materials.append(atlas)
  uv=me.uv_layers.new(name='physical_bark' if key=='wood' else 'UVMap')
  for face in me.polygons:
   face.use_smooth=True;is_trunk=key=='wood' and face.index<trunk_faces;face.material_index=1 if is_trunk else 0
   for li in face.loop_indices:
    val=np.array(gg['uv'][me.loops[li].vertex_index]);uv.data[li].uv=val*(1.5/2.4 if key=='wood' and not is_trunk else 1)
  if key=='leaves':
   ca=me.color_attributes.new(name='LeafColor',type='FLOAT_COLOR',domain='POINT');ca.data.foreach_set('color',np.array(gg['colors'],dtype=np.float32).reshape(-1))
  ob=bpy.data.objects.new(name,me);collection.objects.link(ob);ob['source_id']=data['source']['id'];ob['evidence_basis']=data['basis'];ob['quality_status']='working_not_accepted';ob['collision_role']='solid_pending_runtime' if key=='wood' else 'visual_only';objects.append(ob)
 reports.append({'source_id':data['source']['id'],'height_m':height,'ground_ln02_m':data['ground_ln02_m'],'leaf_count':leaf_count,'branch_tubes':branch_count,'crown_shape_inferred':True,'vertices':sum(len(o.data.vertices) for o in objects)})
cutpath=R/td['source_cut_file'];cut=json.loads(cutpath.read_text());ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};orig={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for item in cut['overrides']:
 ob=ctx[str(item['node'])];src=orig[str(item['node'])];v=np.array(item['vertices']);uvs=np.array(item['uv_source_v_unflipped']);me=bpy.data.meshes.new('BS_CONTEXT_'+str(item['node']));me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvs[:,1]=1-uvs[:,1];uv.data.foreach_set('uv',uvs.astype(np.float32).reshape(-1));ob.data=me;ob['construction_mask']=cut['mask_basis']
bpy.context.view_layer.update()
for name,xy,target,lens in [('BE_QA_SOUTH_APPROACH',[2683543,1246832],[2683559,1246811,414],26),('BE_QA_SOUTH_WALK',[2683552,1246816],[2683574,1246804,409.9],32),('BE_QA_SOUTH_TREE_BASE',[2683558,1246816],[2683554.766,1246817.624,409.65],32)]:
 xy=np.array(xy)-[2683775,1246700];levels=[]
 for ob in rootcol.all_objects:
  if ob.type=='MESH' and (ob.name.startswith('BE_PAVING_') or ob.name in ['BS_ASPHALT','BS_SOIL','BE_WEST_PLATFORM','BE_PUBLIC_PLATFORM','BE_PLATFORM_CURB_TOP']):
   inv=ob.matrix_world.inverted();hit,v,_,_=ob.ray_cast(inv@Vector((*xy,30)),inv.to_3x3()@Vector((0,0,-1)))
   if hit:levels.append((ob.matrix_world@v).z)
 assert levels,(name,xy);floor=max(levels);cd=bpy.data.cameras.new(name);co=bpy.data.objects.new(name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(co);co.location=(*xy,floor+1.65);co.rotation_euler=(Vector(np.array(target)-[2683775,1246700,400])-co.location).to_track_quat('-Z','Y').to_euler();cd.lens=lens;co['eye_height_m']=1.65;co['floor_height_local']=floor
s['version']='G1_013';s['photo_cut_file']=td['source_cut_file'];s.camera=bpy.data.objects['BE_QA_SOUTH_APPROACH'];bpy.context.view_layer.update();bpy.ops.file.pack_all();native=R/'native/G1_013_south_public_space_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native));w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=s['version'],native=str(native),source_cut_file=td['source_cut_file'],source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2));E=R/'evidence/G1_013';E.mkdir(exist_ok=True);report={'version':s['version'],'native':str(native),'ground':p['report'],'trees':reports,'source_nodes_retained':len(orig),'accepted':False};(E/'construction.json').write_text(json.dumps(report,indent=2));print(json.dumps({'version':s['version'],'ground_area_m2':p['report']['area_m2'],'new_objects':len(groundcol.objects)+len(collection.objects),'trees':reports}))
