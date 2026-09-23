"""Editable, source-positioned Platanus prototype; all branch and leaf forms are inferred."""
import bpy,json,math,hashlib
import numpy as np
from mathutils import Vector
from pathlib import Path

ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version']==globals().get('BASE_VERSION','G1_008r5')
VERSION=globals().get('OUTPUT_VERSION','G1_008r6');SCULPT_CANOPY=globals().get('SCULPT_CANOPY',False)
path=ROOT/'derived/bellevue/west_context/tree_69773_input.json';data=json.loads(path.read_text(encoding='utf-8'))
name='15_BELLEVUE_TREES'
if globals().get('REPLACE_TREE',False):
 oldcol=bpy.data.collections.get(name);assert oldcol is not None
 assert set(o.name for o in oldcol.objects)=={'BE_TREE_69773_WOOD','BE_TREE_69773_TWIGS','BE_TREE_69773_LEAVES'}
 for ob in list(oldcol.objects):
  oldmesh=ob.data;bpy.data.objects.remove(ob,do_unlink=True)
  if oldmesh.users==0:bpy.data.meshes.remove(oldmesh)
 bpy.data.collections.remove(oldcol)
 for key in ['BE | plane young twigs','BE | plane summer leaf']:
  oldmat=bpy.data.materials.get(key)
  if oldmat:bpy.data.materials.remove(oldmat)
assert not bpy.data.collections.get(name),'Restore formal predecessor after a failed partial build.'
collection=bpy.data.collections.new(name);bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(collection)
rng=np.random.default_rng(data['inferred']['seed'])
root=np.array([*data['source']['geometry']['coordinates'],data['ground_ln02_m']])-np.array(data['origin'])
height=data['height_m'];radius=np.array(data['inferred']['crown_radius_m'])

def unit(v):
 v=np.array(v,dtype=float);return v/max(np.linalg.norm(v),1e-12)

def mat(name,color,rough=.7):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;m.diffuse_color=(*color,1)
 return m,b

bark=bpy.data.materials['bark_platanus'];bark.use_fake_user=True
for n in bark.node_tree.nodes:
 if n.type=='MAPPING':n.inputs['Scale'].default_value=(1,1,1)
 if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.32
 if n.type=='OUTPUT_MATERIAL':
  for link in list(n.inputs['Displacement'].links):bark.node_tree.links.remove(link)
bark['world_texture_size_m']=1.5;bark['source_url']='https://polyhaven.com/a/bark_platanus';bark['license']='CC0'
twigmat,_=mat('BE | plane young twigs',(.12,.105,.064),.83)
leafmat,bs=mat('BE | plane summer leaf',(.055,.13,.015),.63)
vc=leafmat.node_tree.nodes.new('ShaderNodeVertexColor');vc.layer_name='LeafColor'
leafmat.node_tree.links.new(vc.outputs['Color'],bs.inputs['Base Color'])
bs.inputs['Subsurface Weight'].default_value=.045;bs.inputs['Subsurface Radius'].default_value=(.12,.2,.045);bs.inputs['Subsurface Scale'].default_value=.003
leafmat.use_backface_culling=False
leafmat['basis']='Original modeled palmately lobed leaf geometry and vertex variation, not a copied photograph. Species morphology reference: Cal Poly SelecTree1099.'

# Separate meshes for trunk/branches, thin twigs and leaves remain editable and
# portable. Every leaf is anchored by a petiole to a modeled terminal branch.
groups={k:{'v':[],'f':[],'uv':[],'colors':[]} for k in ['wood','twigs','leaves']}
branch_count=0;leaf_count=0
def add_tube(points,radii,key='wood',sides=9):
 global branch_count
 g=groups[key];base=len(g['v']);points=np.array(points);dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
 for j,(p,r) in enumerate(zip(points,radii)):
  tangent=unit(points[min(j+1,len(points)-1)]-points[max(0,j-1)])
  x=unit(np.cross(tangent,[0,1,0] if abs(tangent[1])<.95 else [1,0,0]));y=np.cross(tangent,x)
  for k in range(sides+1):
   a=2*math.pi*k/sides;flute=1+.045*math.cos(5*a+.3*j)+.025*math.sin(3*a-.17*j)
   g['v'].append(p+r*flute*(x*math.cos(a)+y*math.sin(a)))
   g['uv'].append((2*math.pi*r*k/sides/1.5,dist[j]/1.5))
 for j in range(len(points)-1):
  for k in range(sides):
   a=base+j*(sides+1)+k;b=a+sides+1;g['f'].append((a,a+1,b+1,b))
 g['f'].extend([tuple(base+k for k in range(sides,-1,-1)),tuple(base+(len(points)-1)*(sides+1)+k for k in range(sides+1))]);branch_count+=1

def curve(a,b,bend,steps=10):
 t=np.linspace(0,1,steps)[:,None];return (1-t)*a+t*b+4*t*(1-t)*bend

trunk=np.array([[0,0,-.035],[.01,.015,.10],[.04,.02,.37],[.065,0,.8],[.08,-.045,1.4],[.06,-.08,2.05],[.02,-.05,2.65],[.04,.015,3.22],[.1,.04,3.7]])
add_tube(trunk,[.46,.41,.325,.295,.275,.25,.215,.20,.175],sides=40)
for i in range(7):
 a=2*math.pi*i/7+.17;r=.64+rng.uniform(-.08,.08);end=np.array([r*math.cos(a),r*math.sin(a),-.035])
 pts=curve(np.array([.02,0,.29]),end,np.array([0,0,.025]),9);add_tube(pts,np.linspace(.13,.013,9),sides=12)

# Five unequal scaffold axes, then successive attached lateral growth; no
# randomly scattered floating leaf cloud and no repeated stock tree instances.
terminals=[]
for i in range(5):
 a=2*math.pi*i/5+rng.uniform(-.24,.24);start=trunk[-3+i%3].copy();start[2]+=.07*i
 top=np.array([math.cos(a)*rng.uniform(1.0,1.8),math.sin(a)*rng.uniform(.9,1.5),rng.uniform(7.1,8.0)])
 pts=curve(start,top,np.array([math.cos(a)*-.18,math.sin(a)*-.14,.25]),24)
 add_tube(pts,np.linspace(.145 if i else .17,.056,len(pts)),sides=24)
 for j in range(5):
  at=pts[(7+j*3) if SCULPT_CANOPY else (11+j*2)];az=a+(j-2)*.42+rng.uniform(-.16,.16);r=rng.uniform(2.75,4.05)
  end_z=rng.uniform(8.35,10.95)
  if SCULPT_CANOPY:
   r=[3.95,4.45,4.40,3.5,2.55][j]+rng.uniform(-.30,.30)
   end_z=[5.70,7.0,8.4,9.8,10.95][j]+rng.uniform(-.42,.42)
  end=np.array([math.cos(az)*r,math.sin(az)*r*.87,end_z])
  branch=curve(at,end,np.array([math.cos(az)*-.08,math.sin(az)*-.08,rng.uniform(.05,.26)]),15)
  add_tube(branch,np.linspace(.050,.013,len(branch)),sides=12)
  for k in range(7):
   attach=branch[5+k];az2=az+(1 if k%2 else -1)*rng.uniform(.35,1.15)
   direction=unit(np.array([math.cos(az2),math.sin(az2),rng.uniform(.45,1.4)]))
   end2=attach+direction*rng.uniform(.8,1.6)
   radial=np.linalg.norm(end2[:2]/radius)
   if radial>1:end2[:2]/=radial
   end2[2]=min(end2[2],11.60)
   secondary=curve(attach,end2,np.array([0,0,.10]),9)
   add_tube(secondary,np.linspace(.014,.0033,len(secondary)),key='twigs',sides=7)
   for n in range(8):
    base=secondary[min(2+n//2,7)];theta=az2+(1 if n%2 else -1)*rng.uniform(.4,1.7)
    dest=base+unit([math.cos(theta),math.sin(theta),rng.uniform(-.15,.65)])*rng.uniform(.33,.72)
    dest[2]=max(dest[2],4.45)
    twig=curve(base,dest,np.array([0,0,-.02]),6)
    add_tube(twig,np.linspace(.0032,.00065,len(twig)),key='twigs',sides=5);terminals.append(twig)

# Five-lobed, modestly serrated leaf silhouette; actual surface geometry, not a
# camera-facing alpha billboard. Fold, twist, size and pigmentation vary per leaf.
outline=np.array([[0,0],[-.13,.12],[-.36,.15],[-.31,.24],[-.53,.39],[-.42,.43],[-.34,.61],[-.23,.55],[-.14,.72],[-.095,.84],[0,1],[.09,.83],[.14,.72],[.24,.57],[.34,.64],[.40,.47],[.55,.40],[.38,.30],[.41,.22],[.25,.20],[.12,.105]])
for twig in terminals:
 for j in range(16):
  t=.14+.84*j/15;f=t*(len(twig)-1);q=int(f);anchor=twig[q]*(1-(f-q))+twig[min(q+1,len(twig)-1)]*(f-q)
  tangent=unit(twig[-1]-twig[0]);side=unit(np.cross([0,0,1],tangent))*(1 if j%2 else -1)
  axis=unit(.8*side+.25*tangent+np.array([0,0,rng.uniform(-.5,.6)]))
  origin=anchor+axis*rng.uniform(.035,.07);add_tube([anchor,origin],[.00085,.00055],key='twigs',sides=4)
  normal=unit(np.array([rng.uniform(-.6,.6),rng.uniform(-.6,.6),rng.uniform(.6,1.0)]))
  width=unit(np.cross(axis,normal));normal=unit(np.cross(width,axis))
  length=rng.uniform(.135,.215);scale=rng.uniform(.90,1.13);g=groups['leaves'];base=len(g['v'])
  coords=np.vstack([[0,.40],outline]);variation=rng.uniform(.76,1.15);hue=rng.uniform(-.004,.005)
  for x,y in coords:
   fold=(abs(x)*.13+math.sin(y*math.pi)*.022)*length
   g['v'].append(origin+width*x*length*scale+axis*y*length+normal*fold)
   g['uv'].append((x+.55,y));factor=1.12 if abs(x)<.015 else 1
   g['colors'].append((max(.012,(.050+hue)*variation*factor),.124*variation*factor,.013*variation,1))
  for k in range(len(outline)):g['f'].append((base,base+1+k,base+1+(k+1)%len(outline)))
  leaf_count+=1

allv=np.vstack([g['v'] for g in groups.values()]);top=float(allv[:,2].max());zscale=height/top
# Keep supporting trunk base, source XY and nominal survey height unchanged.
objects=[]
for key,material in [('wood',bark),('twigs',twigmat),('leaves',leafmat)]:
 g=groups[key];v=np.array(g['v']);v[:,2]*=zscale;v+=root
 me=bpy.data.meshes.new('BE_TREE_69773_'+key.upper());me.from_pydata(v.tolist(),[],g['f']);me.update()
 uv=me.uv_layers.new(name='UVMap');uv.data.foreach_set('uv',np.array([g['uv'][l.vertex_index] for l in me.loops],dtype=np.float32).reshape(-1))
 if key=='leaves':
  col=me.color_attributes.new(name='LeafColor',type='FLOAT_COLOR',domain='POINT');col.data.foreach_set('color',np.array(g['colors'],dtype=np.float32).reshape(-1))
 for p in me.polygons:p.use_smooth=True
 ob=bpy.data.objects.new('BE_TREE_69773_'+key.upper(),me);collection.objects.link(ob);me.materials.append(material)
 ob['source_id']=data['id'];ob['kind']='reconstructed_vegetation';ob['place']='Bellevue_Raemistrasse_platform';ob['quality_status']='working_not_accepted'
 ob['evidence_basis']='Surveyed XY/species/12m inventory height; branch form, girth and summer leaves inferred; tree_69773_input.json'
 ob['collision_role']='solid' if key=='wood' else 'visual_only';objects.append(ob)

# Apply only bounded working-copy changes; original photos and other objects stay.
cutpath=ROOT/'derived/bellevue/west_context'/globals().get('CUT_FILENAME','tree_69773_photo_cut.json');cut=json.loads(cutpath.read_text());old=json.loads((ROOT/'derived/bellevue/west_context/platform_tip_photo_cut.json').read_text());before={str(p['node']):p for p in old['overrides']}
context={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};originals={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects};changed=[]
for p in cut['overrides']:
 key=str(p['node'])
 if p==before.get(key):continue
 ob=context[key];src=originals[key];assert ob.matrix_basis==src.matrix_basis
 vv=np.array(p['vertices'],dtype=np.float32);uvv=np.array(p['uv_source_v_unflipped'],dtype=np.float32)
 me=bpy.data.meshes.new('BE_TREE_69773_CONTEXT_'+key);me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.reshape(-1));ob.data=me;ob['construction_mask']=cut['mask_basis'];changed.append(key)

co=bpy.data.objects.get('BE_QA_WEST_TREE')
if co is None:
 camera=bpy.data.cameras.new('BE_QA_WEST_TREE');camera.lens=27
 co=bpy.data.objects.new(camera.name,camera);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(co)
 co.location=(root[0]+9,root[1]-10,root[2]+1.65);target=Vector(root+[0,0,5]);co.rotation_euler=(target-co.location).to_track_quat('-Z','Y').to_euler()
 co['eye_height_m']=1.65;co['ground_note']='Review ground near road; actual support to be checked before walking use.'
scene['version']=VERSION;scene['photo_cut_file']=str(cutpath.relative_to(ROOT));scene.camera=co;bpy.context.view_layer.update()
native=ROOT/f'native/{VERSION}_west_tree_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
record=json.loads((ROOT/'runtime/station_road_working.json').read_text());record.update(version=scene['version'],native=str(native),source_cut_file=scene['photo_cut_file'],source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),accepted=False,not_published=True,published_as=None,next='Actually inspect the source-located tree at human height, ground/trunk and foliage silhouette, then correct before applying elsewhere')
(ROOT/'runtime/station_road_working.json').write_text(json.dumps(record,indent=2))
out=ROOT/'evidence'/VERSION;out.mkdir(exist_ok=True)
receipt={'version':scene['version'],'tree_source':data['id'],'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'height_m':height,'leaf_count':leaf_count,'branch_tube_count':branch_count,'geometry_vertices':sum(len(o.data.vertices) for o in objects),'source_nodes_changed':changed,'accepted':False,'morphology':'Inferred, pending actual visual review, not individual tree scan'}
receipt['sculpt_canopy']=SCULPT_CANOPY
(out/'tree_construction.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
