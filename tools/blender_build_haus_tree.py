"""Build inventory tree119962, grounded pit details, and observed facade fixes."""
import bpy,bmesh,json,math,ast,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');sc=bpy.context.scene;assert sc['version']=='G1_010r3'
path=R/'derived/haus_bellevue/tree_119962_input.json';data=json.loads(path.read_text(encoding='utf-8'))
collection=bpy.data.collections.new('18_HAUS_BELLEVUE_TREE');bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(collection)
root=np.array([*data['source']['geometry']['coordinates'],data['ground_ln02_m']])-np.array(data['origin']);height=data['height_m'];radius=np.array(data['inferred']['crown_radius_m']);rng=np.random.default_rng(119962)
groups={k:{'v':[],'f':[],'uv':[],'colors':[]} for k in ['wood','twigs','leaves']};branch_count=0;leaf_count=0
oldtree=ast.parse((R/'tools/blender_build_bellevue_plane_tree.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in oldtree.body if isinstance(n,ast.FunctionDef) and n.name in ['unit','add_tube','curve']],type_ignores=[]),'tree_geometry','exec'))
bark=bpy.data.materials['bark_platanus'];twigmat=bpy.data.materials['BE | plane young twigs'];leafmat=bpy.data.materials['BE | plane summer leaf']
flaking=bark.copy();flaking.name='HB | inferred flaking plane bark';nodes=flaking.node_tree.nodes
image_roles={'Diffuse':'albedo','Rough':'roughness','nor_gl':'normal_gl'}
for n in nodes:
 if n.type=='TEX_IMAGE' and n.image:
  for key,filename in image_roles.items():
   if key in n.image.name:
    color_space=n.image.colorspace_settings.name;im=bpy.data.images.load(str(R/'derived/materials/platanus_flaking'/f'{filename}.png'),check_existing=True);im.colorspace_settings.name=color_space;n.image=im
 if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.55
flaking['basis']='Original periodic procedural bark maps; inferred smooth mottled Platanus upper bark, not this tree scanned.'

# Broad, unequal crown. Structural growth is scaled to this inventory tree;
# leaves keep biological dimensions rather than stretching a small whole tree.
trunk=np.array([[0,0,-.055],[.025,.01,.13],[.07,.01,.50],[.08,-.035,1.1],[.06,-.06,1.85],[.025,-.04,2.60],[.04,.03,3.25],[.13,.05,3.85],[.22,.10,4.40]])
add_tube(trunk,[.51,.46,.405,.36,.33,.30,.26,.225,.185],sides=48)
for i in range(8):
 a=2*np.pi*i/8+rng.uniform(-.12,.12);end=np.array([np.cos(a),np.sin(a),0])*rng.uniform(.72,1.04);end[2]=-.048
 add_tube(curve(np.array([.04,0,.38]),end,[0,0,.02],12),np.linspace(.15,.012,12),sides=14)
terminals=[]
for i in range(6):
 a=2*np.pi*i/6+rng.uniform(-.24,.24);start=trunk[6+i%3].copy();start[2]+=.05*i
 top=np.array([np.cos(a)*rng.uniform(1.7,2.8),np.sin(a)*rng.uniform(1.5,2.6),rng.uniform(10.2,12.0)])
 primary=curve(start,top,[-.22*np.cos(a),-.20*np.sin(a),.45],28);add_tube(primary,np.linspace(.155,.052,28),sides=24)
 for j in range(5):
  at=primary[8+j*3];az=a+(j-2)*.44+rng.uniform(-.16,.16);r=[4.3,5.2,5.55,4.55,3.1][j]+rng.uniform(-.25,.25);z=[7.5,9.9,12.15,14.4,15.8][j]+rng.uniform(-.38,.38)
  end=np.array([np.cos(az)*r,np.sin(az)*r*.89,z]);branch=curve(at,end,[-.08*np.cos(az),-.08*np.sin(az),.22],17);add_tube(branch,np.linspace(.056,.011,17),sides=13)
  for k in range(7):
   attach=branch[6+k];az2=az+(1 if k%2 else -1)*rng.uniform(.35,1.15);direction=unit([np.cos(az2),np.sin(az2),rng.uniform(.18,1.15)])
   end2=attach+direction*rng.uniform(.9,1.7);radial=np.linalg.norm(end2[:2]/radius)
   if radial>1:end2[:2]/=radial
   end2[2]=min(end2[2],16.60);secondary=curve(attach,end2,[0,0,.11],10);add_tube(secondary,np.linspace(.015,.0033,10),key='twigs',sides=7)
   for n in range(8):
    base=secondary[min(3+n//2,8)];theta=az2+(1 if n%2 else -1)*rng.uniform(.45,1.65);dest=base+unit([np.cos(theta),np.sin(theta),rng.uniform(-.3,.6)])*rng.uniform(.35,.74);dest[2]=max(dest[2],5.45)
    twig=curve(base,dest,[0,0,-.025],6);add_tube(twig,np.linspace(.0034,.00065,6),key='twigs',sides=5);terminals.append(twig)
# Reuse the already reviewed palmately lobed leaf construction, not the old crown.
start=next(i for i,n in enumerate(oldtree.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='outline' for t in n.targets))
end=next(i for i,n in enumerate(oldtree.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='allv' for t in n.targets))
exec(compile(ast.Module(body=oldtree.body[start:end],type_ignores=[]),'plane_leaves','exec'))
zscale=height/max(p[2] for g in groups.values() for p in g['v']);objects=[]
for key,material in [('wood',bark),('twigs',twigmat),('leaves',leafmat)]:
 g=groups[key];v=np.array(g['v']);v[:,2]*=zscale;v+=root;name='HB_TREE_119962_'+key.upper();me=bpy.data.meshes.new(name);me.from_pydata(v.tolist(),[],g['f']);me.update();me.materials.append(material)
 if key=='wood':me.materials.append(flaking)
 uv=me.uv_layers.new(name='physical_bark_metres' if key=='wood' else 'UVMap')
 for face in me.polygons:
  face.use_smooth=True
  z=sum(me.vertices[i].co.z-root[2] for i in face.vertices)/len(face.vertices)
  if key=='wood':
   x=sum(me.vertices[i].co.x-root[0] for i in face.vertices)/len(face.vertices);y=sum(me.vertices[i].co.y-root[1] for i in face.vertices)/len(face.vertices)
   face.material_index=int(z>1.70+.23*np.sin(x*10)+.14*np.cos(y*11))
  scale=1.5/2.4 if key=='wood' and face.material_index else 1
  for li in face.loop_indices:uv.data[li].uv=np.array(g['uv'][me.loops[li].vertex_index])*scale
 if key=='leaves':
  ca=me.color_attributes.new(name='LeafColor',type='FLOAT_COLOR',domain='POINT');ca.data.foreach_set('color',np.array(g['colors'],dtype=np.float32).reshape(-1))
 ob=bpy.data.objects.new(name,me);collection.objects.link(ob);objects.append(ob);ob['source_id']='bauminventar.119962';ob['evidence_basis']=data['basis'];ob['kind']='reconstructed_vegetation';ob['place']='Haus Bellevue west street corner';ob['collision_role']='solid_pending_runtime' if key=='wood' else 'visual_only';ob['quality_status']='working_not_accepted'

# Repair physically unsupported ends of the already built balconies.
d=json.loads((R/'derived/haus_bellevue/upper_input.json').read_text());f=d['frontage'];C=np.array(f['C']);rt=np.array(f['right']);out=np.array(f['out']);Z=f['floor_local'];stone=bpy.data.materials['beige_wall_001'];iron=bpy.data.materials['HU | forged iron balcony']
facade=bpy.data.collections['17_HAUS_BELLEVUE_UPPER'];fixed=[]
for ob in facade.objects:
 if not ob.name.startswith('HU_MAIN_'):continue
 if not any(ob.name.endswith(s) for s in ['_RAIL','_SLAB','_CORBEL']):continue
 count=0
 for vertex in ob.data.vertices:
  vv=float((np.array(vertex.co[:2])-C)@out)
  delta=-.14 if ob.name.endswith('_RAIL') and vv<.018 else -.20 if ob.name.endswith('_SLAB') and vv<.02 else -.24 if ob.name.endswith('_CORBEL') and vv<.085 else 0
  if delta:vertex.co.x+=float(out[0]*delta);vertex.co.y+=float(out[1]*delta);count+=1
 ob.data.update()
 if count:fixed.append({'object':ob.name,'changed_vertices':count})
env={'np':np,'math':math,'C':C,'rt':rt,'out':out,'Z':Z,'stone':stone,'iron':iron,'groups':{}}
upper=ast.parse((R/'tools/blender_build_haus_upper.py').read_text());names=['group','add','P','cube','tube','curved','baluster','tangent_frame']
exec(compile(ast.Module(body=[n for n in upper.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'facade_parts','exec'),env)
for i in [3,7]:
 u=sum(f['bays'][i])/2
 for z in [8.83,13.44]:
  for sign in [-1,1]:
   x=u+sign*.97
   for zz in [z+.18,z+.94]:
    env['cube']('HU_BALCONY_WALL_PLATES',(x,-.102,zz),(.095,.06,.105),iron,.003)
    for dx in [-.027,.027]:
     for dz in [-.031,.031]:env['tube']('HU_BALCONY_FIXING_BOLTS',[env['P'](x+dx,-.068,zz+dz),env['P'](x+dx,-.055,zz+dz)],.007,iron,6)
# The lower roof drum is articulated in the source photo by a recessed stone rail.
# This shallow exterior structure sits in front of the surveyed solid attic wall.
env['T']=np.array(d['corner']['center_local']);r=4.53;a0,a1=np.radians(d['corner']['visible_angles_deg'])
for z0,z1,r0,r1 in [(30.36,30.51,r-.24,r+.02),(31.03,31.17,r-.25,r+.025)]:env['curved']('HU_ROOF_DRUM_RAIL',z0-Z,z1-Z,r0,r1,a0,a1)
for a in np.arange(a0+.035,a1-.02,.065):env['baluster']('HU_ROOF_DRUM_BALUSTERS',env['T']+(r-.105)*np.array([np.cos(a),np.sin(a)]),30.49-Z,.55)
for (name,_),g in env['groups'].items():
 assert name not in bpy.data.objects
 me=bpy.data.meshes.new(name);me.from_pydata(g['v'],[],g['f']);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free();ob=bpy.data.objects.new(name,me);facade.objects.link(ob);me.materials.append(g['mat']);uv=me.uv_layers.new(name='metre_scale')
 for face in me.polygons:
  face.use_smooth=g['smooth'];axes=[i for i in range(3) if i!=int(np.argmax(abs(np.array(face.normal))))]
  for li in face.loop_indices:
   p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/3,p[axes[1]]/3)
 if g['bevel']:
  mod=ob.modifiers.new('Physical edge radius','BEVEL');mod.width=g['bevel'];mod.segments=2;ob.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 ob['egid']=9011202;ob['evidence_basis']='Balcony wall fixings inferred to close observed physical gaps; roof drum balustrade inferred from existing facade photograph.';ob['quality_status']='working_not_accepted';ob['collision_role']='solid_pending_runtime'

cutpath=R/'derived/bellevue/west_context/haus_tree_119962_photo_cut.json';cut=json.loads(cutpath.read_text());ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};orig={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for p in cut['overrides']:
 ob=ctx[str(p['node'])];src=orig[str(p['node'])];vv=np.array(p['vertices']);uvv=np.array(p['uv_source_v_unflipped']);me=bpy.data.meshes.new('HB_TREE_CONTEXT_'+str(p['node']));me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.astype(np.float32).reshape(-1));ob.data=me;ob['construction_mask']=cut['mask_basis']

for name,offset,target,lens in [('HB_QA_TREE',(10,-13),(0,0,7.3),26),('HB_QA_TREE_BASE',(3.8,-4),(0,0,1.25),32)]:
 xy=root[:2]+np.array(offset);ground=None
 for ob in bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].all_objects:
  if ob.type=='MESH' and (ob.name.startswith('BE_PAVING_') or ob.name in ['HB_SIDEWALK_ASPHALT','BE_WEST_PLATFORM']):
   hit,p,_,_=ob.ray_cast(ob.matrix_world.inverted()@Vector((*xy,60)),Vector((0,0,-1)));p=ob.matrix_world@p
   if hit and p.z<15:ground=p.z if ground is None else max(ground,p.z)
 assert ground is not None,(name,xy)
 cd=bpy.data.cameras.new(name);co=bpy.data.objects.new(name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(co);co.location=Vector((*xy,ground+1.65));co.rotation_euler=(Vector(root+np.array(target))-co.location).to_track_quat('-Z','Y').to_euler();cd.lens=lens;co['eye_height_m']=1.65;co['floor_height_local']=ground

sc['version']='G1_011';sc['photo_cut_file']=str(cutpath.relative_to(R));sc.camera=bpy.data.objects['HB_QA_TREE'];bpy.context.view_layer.update();bpy.ops.file.pack_all();native=R/'native/G1_011_haus_tree_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=sc['version'],native=str(native),source_cut_file=sc['photo_cut_file'],source_cut_nodes=len(cut['overrides']),source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),accepted=False,not_published=True,next='Inspect new tree119962, ground contacts, facade fixings and roof drum; repair observed artifacts before runtime review.');(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2))
e=R/'evidence/G1_011';e.mkdir(exist_ok=True);receipt={'version':sc['version'],'native':str(native),'tree_id':119962,'height_m':height,'crown_inferred':True,'leaf_count':leaf_count,'branch_tubes':branch_count,'tree_vertices':sum(len(o.data.vertices) for o in objects),'balcony_members_fixed':fixed,'new_facade_meshes':len(env['groups']),'accepted':False};(e/'construction.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
