"""Continuous AV35946 ground plus deep, editable Haus Bellevue shopfront construction."""
import bpy,bmesh,json,ast,math,hashlib,random
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path('F:/MyWorld/ZurichWorld');sc=bpy.context.scene
assert sc['version']=='G1_008r8', 'Use the saved predecessor; do not duplicate an incomplete pass.'
path=ROOT/'derived/haus_bellevue/build_input.json';d=json.loads(path.read_text());f=d['frontage'];rng=random.Random(9011202)
name='16_HAUS_BELLEVUE_STREET'
assert name not in bpy.data.collections
building=bpy.data.collections.new(name);bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(building)
tree=ast.parse((ROOT/'tools/blender_build_bellevue.py').read_text());defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','box','tube','lathe']];exec(compile(ast.Module(body=defs,type_ignores=[]),'reusable_geometry','exec'))
C=np.array(f['C']);right=np.array(f['right']);front=np.array(f['out']);FLOOR=f['floor_local']
def P(u,v,z):
 xy=C+u*right+v*front;return (*xy,FLOOR+z)
def mat(name,color,rough=.5,metal=0,trans=0):
 m=bpy.data.materials.new('HB | '+name);m.use_nodes=True;n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal;n.inputs['Transmission Weight'].default_value=trans;n.inputs['IOR'].default_value=1.48;return m
stone=bpy.data.materials['beige_wall_001'];stone.use_fake_user=True
texdir=ROOT/'sources/textures/polyhaven/beige_wall_001';texdir.mkdir(parents=True,exist_ok=True);receipts=[]
for n in stone.node_tree.nodes:
 if n.type=='TEX_IMAGE' and n.image:
  im=n.image;out=texdir/Path(im.filepath).name
  raw=bytes(im.packed_file.data) if im.packed_file else Path(bpy.path.abspath(im.filepath)).read_bytes();out.write_bytes(raw);im.filepath=str(out)
  receipts.append({'file':out.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
 if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.32
 if n.type=='OUTPUT_MATERIAL':
  for link in list(n.inputs['Displacement'].links):stone.node_tree.links.remove(link)
stone['source_url']='https://polyhaven.com/a/beige_wall_001';stone['license']='CC0';stone['world_texture_size_m']=3.;stone['basis']='Fine mineral painted finish used as a visual proxy; not sampled from this building.'
(texdir/'receipt.json').write_text(json.dumps({'url':stone['source_url'],'author':'Dimitrios Savva, Rico Cilliers','license':'CC0','files':receipts},indent=2))
bronze=mat('dark bronze storefront metal',(.081,.067,.045),.28,.78)
gasket=mat('recessed glazing gaskets',(.009,.011,.010),.68)
glass=mat('clear shop glazing 8mm',(.965,.985,.975),.075,0,1)
mortar=mat('mineral joint shadow',(.29,.27,.235),.87)
plinth=mat('grey sandstone plinth',(.27,.26,.235),.77)
brass=mat('brushed brass handle',(.48,.325,.13),.25,.8)
linen=mat('warm linen curtain',(.49,.445,.355),.92)
red=mat('faded dark red awning canvas',(.27,.019,.021),.86)
white=mat('warm ivory lettering',(.80,.765,.65),.59)
plaster=mat('shop interior mineral paint',(.57,.545,.48),.86)
ceiling=mat('shop ceiling',(.66,.635,.57),.86)
wood=bpy.data.materials['oak_veneer_01'];dark=bpy.data.materials['BE | dark structural metal'];asphalt=bpy.data.materials['asphalt_03'];curbmat=bpy.data.materials['concrete_floor_01'];soil=bpy.data.materials['BE | west tree pit soil']
def uv_box(ob,size=3,offset=None):
 uv=ob.data.uv_layers.new(name='metre_scale');offs=offset if offset is not None else (rng.random()*3,rng.random()*3)
 for poly in ob.data.polygons:
  normal=np.array(poly.normal);nx=abs(np.dot(normal[:2],right));ny=abs(np.dot(normal[:2],front))
  for li in poly.loop_indices:
   p=ob.data.vertices[ob.data.loops[li].vertex_index].co;q=np.array(p[:2])-C;u=q@right;v=q@front;z=p.z-FLOOR
   uv.data[li].uv=((u if nx<ny or abs(normal[2])>.5 else v)/size+offs[0],(v if abs(normal[2])>.5 else z)/size+offs[1])
 return ob
def bx(name,center,dims,material,bevel=.006):
 ob=box('HB_'+name,center,dims,material,bevel)
 if material in [stone,curbmat,wood,asphalt]:uv_box(ob,2 if material is wood else 3)
 return ob
for key,tt in d['parts'].items():
 vv=np.array(tt).reshape(-1,3);ob=mesh('HB_SIDEWALK_'+key.upper(),vv.tolist(),np.arange(len(vv)).reshape(-1,3).tolist(),{'asphalt':asphalt,'curb_top':curbmat,'curb_face':curbmat,'curb_joint':mortar,'soil':soil}[key])
 uv=ob.data.uv_layers.new(name='metre_scale');uv.data.foreach_set('uv',np.array(d['uv'][key],dtype=np.float32).reshape(-1));ob['source_id']='av_bo_boflaeche_a.35946';ob['collision_role']='walkable_surface' if key in ['asphalt','curb_top'] else 'solid'
# Real wall mass and reveals. Piers are placed between measured facade recesses;
# a single broad backing slab is never used across the window/door openings.
umin,umax=f['u_min'],f['u_max'];H=f['top_local']-FLOOR;bays=f['bays'];solid=[];cursor=umin
for a,b in bays:
 if a>cursor:solid.append((cursor,a))
 cursor=b
solid.append((cursor,umax))
for j,(a,b) in enumerate(solid):
 w=b-a;u=(a+b)/2
 bx(f'PIER_{j:02d}_MASS',(u,-.37,H/2-.16),(w,.74,H+.32),mortar,.0)
 bx(f'PIER_{j:02d}_PLINTH',(u,.028,-.035),(w+.026,.20,.73),plinth,.008)
 # Recessed joints have actual depth; block edges retain small stone radii.
 for k in range(12):
  z0=.345+k*.347;z1=min(z0+.329,4.50)
  if z1<=z0:continue
  ob=bx(f'PIER_{j:02d}_COURSE_{k:02d}',(u,.032,(z0+z1)/2),(w-.004,.21,z1-z0),stone,.011)
 bx(f'PIER_{j:02d}_CAP',(u,.052,4.56),(w+.022,.28,.135),stone,.007)
# Continuous cornice is a stack of distinct solid profiles, not painted stripes.
for k,(z,h,dep) in enumerate([(4.645,.055,.20),(4.717,.088,.25),(4.793,.038,.34),(4.842,.057,.37),(4.911,.08,.29)]):
 bx(f'CORNICE_{k}',((umin+umax)/2,.035,z),(umax-umin,dep,h),stone,.008)
def text(name,body,u,v,z,size,material):
 cu=bpy.data.curves.new('HB_'+name,'FONT');cu.body=body;cu.size=size;cu.extrude=.001;cu.bevel_depth=.0005;cu.align_y='BOTTOM_BASELINE';cu.resolution_u=6
 font=Path('C:/Windows/Fonts/georgia.ttf')
 if font.exists():cu.font=bpy.data.fonts.load(str(font))
 ob=bpy.data.objects.new('HB_'+name,cu);building.objects.link(ob);ob.location=P(u,v,z);x=Vector((*right,0));y=Vector((0,0,1));ob.rotation_euler=Matrix((x,y,x.cross(y))).transposed().to_euler();cu.materials.append(material);return ob
for i,(a,b) in enumerate(bays):
 w=b-a;mid=(a+b)/2;door=(i==f['entry_bay_index']);sill=.025 if door else .21;head=4.48
 # Thick jambs, reveal returns, flush stone sill and outer moulding.
 for side,u in [('L',a+.06),('R',b-.06)]:
  bx(f'BAY_{i}_{side}_REVEAL',(u,-.28,(sill+head)/2),(.12,.63,head-sill),stone,.005)
 bx(f'BAY_{i}_LINTEL',(mid,-.28,4.46),(w,.63,.18),stone,.007)
 bx(f'BAY_{i}_SILL',(mid,-.10,sill-.03),(w,.84,.09),plinth,.008)
 # Each glazed frame has 8 mm glass, a recessed gasket and slim bronze profiles.
 gv=-.245
 for side,u in [('L',a+.15),('R',b-.15)]:
  bx(f'BAY_{i}_{side}_GASKET',(u,gv-.017,(sill+head)/2),(.058,.10,head-sill-.05),gasket,.002)
  bx(f'BAY_{i}_{side}_FRAME',(u,gv+.025,(sill+head)/2),(.065,.095,head-sill),bronze,.003)
 for k,z in enumerate([sill+.052,2.66,2.93,4.38]):
  bx(f'BAY_{i}_RAIL_{k}',(mid,gv+.027,z),(w-.24,.10,.056),bronze,.003)
 if not door:
  for k,(z0,z1) in enumerate([(sill+.09,2.627),(2.961,4.344)]):
   bx(f'BAY_{i}_GLASS_{k}',(mid,gv-.014,(z0+z1)/2),(w-.37,.008,z1-z0),glass,.0)
  bx(f'BAY_{i}_SIGN_BAND',(mid,gv+.012,2.795),(w-.34,.022,.216),white if i<4 else bronze,.003)
  if i<4:
   word=['CAFE FELIX','CONFISERIE','KONDITOREI','AM BELLEVUE'][i];ob=text(f'CAFE_LABEL_{i}',word,a+.27,gv+.029,2.748,.13,bronze);ob['evidence_basis']='Cafe identity supported; lettering layout and typeface inferred, not a surveyed logo.'
 else:
  # The broad measured portal contains a double door and fixed sidelights.
  clear=1.64
  for side,sgn in [('L',-1),('R',1)]:
   leafw=clear/2;hinge=mid+sgn*leafw;center=mid+sgn*leafw/2
   pivot=bpy.data.objects.new('HB_ENTRY_HINGE_'+side,None);building.objects.link(pivot);pivot.location=P(hinge,gv,0)
   leaf=[]
   for u in [center-leafw/2+.027,center+leafw/2-.027]:leaf.append(bx(f'ENTRY_{side}_STILE_{u:.2f}',(u,gv+.016,1.335),(.054,.084,2.60),bronze,.003))
   for z in [.065,2.61]:leaf.append(bx(f'ENTRY_{side}_RAIL_{z:.2f}',(center,gv+.016,z),(leafw,.084,.07),bronze,.003))
   leaf.append(bx(f'ENTRY_{side}_GLASS',(center,gv-.014,1.34),(leafw-.10,.008,2.47),glass,0))
   leaf.append(bx(f'ENTRY_{side}_KICK',(center,gv+.028,.16),(leafw-.08,.023,.20),bronze,.003))
   hu=mid+sgn*.105
   leaf.append(tube('HB_ENTRY_'+side+'_HANDLE',[P(hu,gv+.071,.94),P(hu,gv+.14,.97),P(hu,gv+.14,1.43),P(hu,gv+.071,1.46)],.012,brass))
   bpy.context.view_layer.update()
   for ob in leaf:ob.parent=pivot;ob.matrix_parent_inverse=pivot.matrix_world.inverted()
   pivot['interaction_role']='hinged_door_leaf';pivot['closed_rotation_z']=0.;pivot['open_rotation_z']=sgn*math.radians(78);pivot['state']='closed';pivot['function_status']='modeled mechanism only; runtime use not implemented'
   outer=a+.18 if sgn<0 else b-.18;inner=mid+sgn*clear/2;sw=abs(outer-inner)-.06
   bx(f'ENTRY_{side}_FIXED_GLASS',((outer+inner)/2,gv-.014,1.34),(sw,.008,2.53),glass,0)
  bx('ENTRY_TOP_GLASS',(mid,gv-.014,3.65),(w-.37,.008,1.386),glass,0)
  text('ENTRY_ADDRESS','5',a+.25,.148,1.57,.13,bronze)
 # Retracted red fabric cassette: thin folded fabric and an actual metal end cap.
 if i<4:
  bx(f'AWNING_{i}_HOUSING',(mid,.105,4.24),(w-.19,.31,.14),bronze,.012)
  bx(f'AWNING_{i}_FOLDED_CANVAS',(mid,.276,4.176),(w-.24,.047,.116),red,.008)
  for z in [4.151,4.179,4.207]:tube(f'HB_AWNING_{i}_FOLD_{z}',[P(a+.14,.302,z),P(b-.14,.302,z)],.007,red)
 # A physical shallow shop/vestibule volume; deeper rooms are intentionally not
 # presented as a reproduced cafe interior or currently public/opened space.
 bx(f'BAY_{i}_INNER_FLOOR',(mid,-1.82,-.045),(w,3.12,.09),plinth,.002)
 bx(f'BAY_{i}_INNER_CEILING',(mid,-1.82,4.45),(w,3.12,.10),ceiling,.003)
 for u in [a+.02,b-.02]:bx(f'BAY_{i}_INNER_SIDE_{u:.2f}',(u,-1.81,2.19),(.075,3.18,4.46),plaster,.004)
 bx(f'BAY_{i}_INNER_BACK',(mid,-3.33,2.19),(w,.10,4.46),plaster,.004)
 if not door:
  # Folded textile supplies depth and variable grazing highlights without
  # inventing a detailed shop programme. Central view remains partially open.
  for side,u0 in [('L',a+.11),('R',b-.11-.36)]:
   vv=[];ff=[];nx=36;nz=12
   for iz in range(nz+1):
    z=.12+iz*2.40/nz
    for ix in range(nx+1):
     u=u0+ix*.36/nx;v=-2.43+.035*math.cos(ix/nx*math.pi*8)+.01*math.sin(iz*.3);vv.append(P(u,v,z))
   for iz in range(nz):
    for ix in range(nx):j=iz*(nx+1)+ix;ff.append((j,j+1,j+nx+2,j+nx+1))
   mesh(f'HB_BAY_{i}_CURTAIN_{side}',vv,ff,linen,True)
  bx(f'BAY_{i}_DISPLAY_PLINTH',(mid,-1.07,.31),(w-.53,.66,.62),wood,.012)
  bx(f'BAY_{i}_DISPLAY_STONE',(mid,-1.07,.635),(w-.48,.71,.035),plinth,.006)
 # Modest interior illumination, physically lit surfaces rather than bright glass.
 ld=bpy.data.lights.new(f'HB_BAY_{i}_CEILING_LIGHT','AREA');ld.energy=45 if not door else 32;ld.color=(1,.84,.64);ld.shape='DISK';ld.size=.55
 lo=bpy.data.objects.new(ld.name,ld);building.objects.link(lo);lo.location=P(mid,-1.15,4.23)
# Apply bounded cut to a working copy, preserving all original survey meshes.
cutpath=ROOT/'derived/bellevue/west_context/haus_frontage_photo_cut.json';cut=json.loads(cutpath.read_text());ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};orig={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for p in cut['overrides']:
 ob=ctx[str(p['node'])];src=orig[str(p['node'])];vv=np.array(p['vertices']);uvv=np.array(p['uv_source_v_unflipped']);me=bpy.data.meshes.new('HB_CONTEXT_'+str(p['node']));me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.astype(np.float32).reshape(-1));ob.data=me;ob['construction_mask']=cut['mask_basis']
for ob in building.objects:
 ob['place']='Haus Bellevue south streetfront';ob['egid']=9011202;ob['quality_status']='construction candidate; not final realism or natural-use acceptance'
 if not ob.get('source_id'):ob['source_id']='av_bo_boflaeche_a.13983 / SPPA exterior reference'
 if not ob.get('evidence_basis'):ob['evidence_basis']='Measured plan/bay rhythm, reference-informed construction. Fabrication, material proxy, vertical dimensions and shallow display fit-out inferred.'
 if ob.type=='MESH' and not ob.get('collision_role'):ob['collision_role']='solid_pending_runtime'
def camera(name,u,v,target,lens=28):
 cd=bpy.data.cameras.new(name);ob=bpy.data.objects.new(name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(ob);ob.location=P(u,v,1.65);ob.rotation_euler=(Vector(P(*target))-ob.location).to_track_quat('-Z','Y').to_euler();cd.lens=lens;ob['eye_height_m']=1.65
camera('HB_QA_ALONG',-1.3,3.3,(19,.05,2.0),28)
camera('HB_QA_ENTRY',16.1,3.2,(16.1,-.5,1.9),27)
camera('HB_QA_REVERSE',27.8,3.3,(6,.02,1.9),28)
sc['version']='G1_009';sc['photo_cut_file']=str(cutpath.relative_to(ROOT));sc.camera=bpy.data.objects['HB_QA_ENTRY'];bpy.context.view_layer.update();bpy.ops.file.pack_all()
native=ROOT/'native/G1_009_haus_frontage_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((ROOT/'runtime/station_road_working.json').read_text());rec.update(version=sc['version'],native=str(native),source_cut_file=sc['photo_cut_file'],accepted=False,not_published=True,next='Inspect actual human-eye facade renders and correct construction/material/seam problems before runtime integration')
(ROOT/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2));out=ROOT/'evidence/G1_009';out.mkdir(exist_ok=True)
(out/'build.json').write_text(json.dumps({'version':sc['version'],'native':str(native),'objects':len(building.objects),'frontage_length_m':umax-umin,'sidewalk':d['report'],'cut':cut['haus_frontage'],'accepted':False},indent=2))
print(json.dumps({'version':sc['version'],'objects':len(building.objects),'native':str(native),'accepted':False}))
