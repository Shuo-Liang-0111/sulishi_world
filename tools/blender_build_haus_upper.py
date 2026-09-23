"""Reference-informed historic frontage, curved corner and source roof surfaces."""
import bpy,bmesh,json,math,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');sc=bpy.context.scene;assert sc['version']=='G1_009r3'
d=json.loads((R/'derived/haus_bellevue/upper_input.json').read_text());f=d['frontage'];C=np.array(f['C']);rt=np.array(f['right']);out=np.array(f['out']);Z=f['floor_local'];rng=np.random.default_rng(9011202)
colname='17_HAUS_BELLEVUE_UPPER';assert colname not in bpy.data.collections
col=bpy.data.collections.new(colname);bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(col)
stone=bpy.data.materials['beige_wall_001'];glass=bpy.data.materials['HB | clear shop glazing 8mm'];plinth=bpy.data.materials['HB | grey sandstone plinth'];roof=bpy.data.materials['roof_slates_03'];roof.use_fake_user=True
folder=R/'sources/textures/polyhaven/roof_slates_03';folder.mkdir(parents=True,exist_ok=True);receipts=[]
for n in roof.node_tree.nodes:
 if n.type=='TEX_IMAGE' and n.image:
  im=n.image;path=folder/Path(im.filepath).name;raw=bytes(im.packed_file.data) if im.packed_file else Path(bpy.path.abspath(im.filepath)).read_bytes();path.write_bytes(raw);im.filepath=str(path);receipts.append({'file':path.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
 if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.65
 if n.type=='OUTPUT_MATERIAL':
  for link in list(n.inputs['Displacement'].links):roof.node_tree.links.remove(link)
(folder/'receipt.json').write_text(json.dumps({'url':'https://polyhaven.com/a/roof_slates_03','author':'Rob Tuytel','license':'CC0','texture_size_m':3,'files':receipts},indent=2))
def material(name,color,rough=.7,metal=0):
 m=bpy.data.materials.new('HU | '+name);m.use_nodes=True;bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal;return m
wood=material('painted timber window frames',(.062,.052,.041),.36)
iron=material('forged iron balcony',(.025,.031,.03),.44,.58)
gasket=bpy.data.materials['HB | recessed glazing gaskets'];cavity=material('unopened upper room mineral wall',(.29,.27,.23),.91)
curtains=[material('linen '+str(i),c,.88) for i,c in enumerate([(.49,.46,.38),(.38,.37,.32),(.61,.59,.51)])]
zinc=material('weathered zinc flashing',(.235,.26,.265),.49,.63)
groups={}
def group(name,mat,bevel=0,smooth=False):
 key=(name,mat.name)
 if key not in groups:groups[key]={'v':[],'f':[],'mat':mat,'bevel':bevel,'smooth':smooth}
 return groups[key]
def add(name,verts,faces,mat,bevel=0,smooth=False):
 g=group(name,mat,bevel,smooth);start=len(g['v']);g['v'].extend([list(p) for p in verts]);g['f'].extend([tuple(start+i for i in face) for face in faces])
def P(u,v,z):
 p=C+rt*u+out*v;return np.array([p[0],p[1],Z+z])
def cube(name,center,dims,mat,bevel=.005,frame=None):
 du,dv,dz=np.array(dims)/2
 transform=frame or P
 vv=[transform(center[0]+i*du,center[1]+j*dv,center[2]+k*dz) for i,j,k in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
 add(name,vv,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,bevel)
def beam(name,a,b,width,depth,mat,face_normal=None):
 a,b=np.array(a),np.array(b);along=b-a;along/=np.linalg.norm(along);side=np.cross(along,[out[0],out[1],0] if face_normal is None else face_normal);side/=np.linalg.norm(side);normal=np.cross(side,along)
 vv=[p+side*width*i/2+normal*depth*j/2 for p in [a,b] for i,j in [(-1,-1),(1,-1),(1,1),(-1,1)]]
 add(name,vv,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,.004)
def tube(name,points,r,mat,sides=8):
 points=np.array(points);vv=[];ff=[]
 for j,p in enumerate(points):
  axis=points[min(len(points)-1,j+1)]-points[max(0,j-1)];axis/=np.linalg.norm(axis)
  a=np.cross(axis,[0,0,1] if abs(axis[2])<.95 else [0,1,0]);a/=np.linalg.norm(a);b=np.cross(axis,a)
  vv.extend([p+r*(np.cos(t)*a+np.sin(t)*b) for t in np.linspace(0,2*np.pi,sides,endpoint=False)])
 for j in range(len(points)-1):
  for k in range(sides):a=j*sides+k;b=j*sides+(k+1)%sides;ff.append((a,b,b+sides,a+sides))
 ff.extend([tuple(range(sides-1,-1,-1)),tuple((len(points)-1)*sides+k for k in range(sides))]);add(name,vv,ff,mat,smooth=True)
def baluster(name,point,z0,height=.65):
 profile=[(.048,0),(.053,.05),(.041,.10),(.035,.18),(.082,.40),(.078,.52),(.056,.68),(.033,.81),(.039,.92),(.058,.94),(.058,1)]
 vv=[];ff=[];N=16
 for r,z in profile:
  vv.extend([[point[0]+r*np.cos(a),point[1]+r*np.sin(a),Z+z0+z*height] for a in np.linspace(0,2*np.pi,N,endpoint=False)])
 for j in range(len(profile)-1):
  for k in range(N):a=j*N+k;b=j*N+(k+1)%N;ff.append((a,b,b+N,a+N))
 add(name,vv,ff,stone,smooth=True)
def ornament(name,u,v,z,size=.16,frame=None):
 transform=frame or P;vv=[];ff=[];N=32
 for r,depth in [(0,.028),(.32,.031),(.6,.06),(.9,.023),(1,0)]:
  for k in range(N):
   a=2*np.pi*k/N;rr=size*r*(1+.16*np.cos(8*a));vv.append(transform(u+rr*np.cos(a),v+depth,z+rr*np.sin(a)))
 for j in range(4):
  for k in range(N):a=j*N+k;b=j*N+(k+1)%N;ff.append((a,b,b+N,a+N))
 add(name,vv,ff,stone,smooth=True)
def window(name,u,width,sill,head,style,frame=None,seed=0):
 transform=frame or P;h=head-sill;mid=(head+sill)/2
 for side,x in [('L',u-width/2-.06),('R',u+width/2+.06)]:
  cube(name+'_STONE',(x,-.14,mid),(.135,.44,h+.13),stone,.006,transform)
  cube(name+'_STONE',(x+(-.061 if side=='L' else .061),.055,mid),(.045,.105,h+.28),stone,.005,transform)
 for z,dep,th in [(sill-.075,.54,.13),(head+.072,.34,.14)]:cube(name+'_STONE',(u,-.105,z),(width+.36,dep,th),stone,.006,transform)
 for x in [u-width/2+.045,u+width/2-.045,u]:
  cube(name+'_FRAME',(x,-.24,mid),(.073 if x==u else .066,.095,h-.06),wood,.003,transform)
 transom=head-h*.29
 for z in [sill+.05,transom,head-.045]:cube(name+'_FRAME',(u,-.228,z),(width,.095,.075),wood,.003,transform)
 for j,(z0,z1) in enumerate([(sill+.087,transom-.044),(transom+.043,head-.085)]):
  for sign in [-1,1]:cube(name+'_GLASS',(u+sign*width*.247,-.265,(z0+z1)/2),(width*.5-.094,.008,z1-z0),glass,0,transform)
 # Recess backing and interior returns give depth without claiming opened rooms.
 cube(name+'_ROOM',(u,-1.74,mid),(width+.09,.075,h+.22),cavity,.003,transform)
 for x in [u-width/2-.025,u+width/2+.025]:cube(name+'_ROOM',(x,-.98,mid),(.065,1.50,h+.2),cavity,.002,transform)
 for z in [sill-.055,head+.055]:cube(name+'_ROOM',(u,-.98,z),(width,1.50,.065),cavity,.002,transform)
 # Unequal curtain opening creates normal daily variation, independent of camera.
 if seed%4!=1:
  for sign in [-1,1]:
   w=width*(.34 if seed%4==0 else .20);start=u-width/2+.025 if sign<0 else u+width/2-w-.025;vv=[];ff=[];N=20
   for iz,z in enumerate([sill+.03,head-.07]):
    for k in range(N+1):vv.append(transform(start+w*k/N,-1.20+.035*math.sin(k/N*math.pi*9),z))
   for k in range(N):ff.append((k,k+1,k+N+2,k+N+1))
   add(name+'_CURTAIN',vv,ff,curtains[seed%3],smooth=True)
 if style in ['pediment','cornice']:
  cube(name+'_HEAD',(u,.10,head+.22),(width+.65,.47,.115),stone,.008,transform)
  for x in [u-width/2-.10,u+width/2+.10]:
   cube(name+'_BRACKET',(x,.079,head+.087),(.17,.36,.30),stone,.012,transform)
   ornament(name+'_BRACKET',x,.264,head+.03,.077,transform)
  if style=='pediment':
   for sign in [-1,1]:beam(name+'_PEDIMENT',transform(u+sign*(width/2+.30),.09,head+.26),transform(u,.09,head+.66),.105,.29,stone,transform(0,1,0)-transform(0,0,0))
   # A closed recessed triangular tympanum makes the pediment a construction.
   add(name+'_PEDIMENT', [transform(u-width/2-.24,-.015,head+.25),transform(u+width/2+.24,-.015,head+.25),transform(u,-.015,head+.61)],[(0,1,2)],stone)
   ornament(name+'_PEDIMENT',u,.02,head+.41,.09,transform)
 elif style=='small':cube(name+'_HEAD',(u,.058,head+.185),(width+.45,.31,.09),stone,.006,transform)
def balcony(name,u,w,z,stone_rail=False):
 cube(name+'_SLAB',(u,.49,z-.07),(w+.44,1.10,.18),stone,.012)
 for x in [u-w*.34,u+w*.34]:
  cube(name+'_CORBEL',(x,.33,z-.31),(.21,.55,.39),stone,.015)
  ornament(name+'_CORBEL',x,.62,z-.30,.11)
 if stone_rail:
  for zz,h in [(z+.11,.13),(z+.86,.14)]:cube(name+'_BALUSTRADE',(u,1.005,zz),(w+.38,.26,h),stone,.009)
  for x in np.arange(u-w/2+.15,u+w/2,.235):baluster(name+'_BALUSTERS',P(x,1.005,0)[:2],z+.19,.59)
 else:
  for zz,r in [(z+.18,.016),(z+.94,.022)]:
   tube(name+'_RAIL',[P(u-w/2,-.015,zz),P(u-w/2,1.005,zz),P(u+w/2,1.005,zz),P(u+w/2,-.015,zz)],r,iron)
  for x in np.linspace(u-w/2,u+w/2,max(5,int(w/.21))):tube(name+'_RAIL',[P(x,1.005,z+.17),P(x,1.005,z+.95)],.011,iron)
  for x in np.arange(u-w/2+.20,u+w/2-.05,.38):
   for sign in [-1,1]:
    ts=np.linspace(0,2*np.pi,24);pts=[P(x+sign*(.11-.055*t/(2*np.pi))*np.cos(t),1.014,z+.55+(.22-.13*t/(2*np.pi))*np.sin(t)) for t in ts];tube(name+'_SCROLL',pts,.008,iron,6)
# Main frontage: four distinct storeys, physical openings and projection hierarchy.
umin,umax=f['u_min'],f['u_max'];centers=[(a+b)/2 for a,b in f['bays']]
for li,L in enumerate(d['levels']):
 name='HU_MAIN_'+L['name'];openings=[]
 for i,u in enumerate(centers):
  width=1.28 if li==0 else 1.38
  if i==5:
   # Broad central axis is articulated as a paired opening above the portal.
   for off in [-.69,.69]:openings.append((u+off,.95,i))
  else:openings.append((u,width,i))
 for z0,z1 in [(L['bottom'],L['sill']),(L['head'],L['top'])]:cube(name+'_WALL',((umin+umax)/2,-.49,(z0+z1)/2),(umax-umin,.74,z1-z0),stone,.002)
 cursor=umin
 for wi,(u,w,source_i) in enumerate(openings):
  a,b=u-w/2,u+w/2
  if a>cursor:cube(name+'_WALL',((a+cursor)/2,-.49,(L['sill']+L['head'])/2),(a-cursor,.74,L['head']-L['sill']),stone,.002)
  cursor=b
  style='small' if li==0 else 'pediment' if li==1 else 'cornice' if li==2 else 'simple'
  window(name+f'_W{wi:02d}',u,w,L['sill'],L['head'],style,seed=li*13+wi)
 if cursor<umax:cube(name+'_WALL',((cursor+umax)/2,-.49,(L['sill']+L['head'])/2),(umax-cursor,.74,L['head']-L['sill']),stone,.002)
 # Sills and string courses are differentiated rather than repeating a kit.
 if li<3:
  for j,(dz,h,dep) in enumerate([(-.12,.075,.31),(-.045,.045,.37),(.005,.045,.28)]):cube(name+'_STRING',((umin+umax)/2,.025,L['top']+dz),(umax-umin,dep,h),stone,.006)
for i in [3,7]:
 for li,z in enumerate([8.83,13.44]):balcony(f'HU_MAIN_BALCONY_{i}_{li}',centers[i],1.94,z)
# Shallow fluted pilasters group windows and add vertical relief across upper storeys.
for j in [0,3,6,8]:
 u=(f['bays'][j][1]+(f['bays'][j+1][0] if j<8 else umax))/2;z0=8.31;z1=20.43
 cube('HU_MAIN_PILASTER',(u,.025,(z0+z1)/2),(.36,.25,z1-z0),stone,.004)
 for k in range(5):cube('HU_MAIN_FLUTES',(u-.135+k*.067,.162,(z0+z1)/2),(.038,.046,z1-z0-.31),stone,.011)
 for zz,w,h in [(z0,.49,.14),(z1,.60,.17),(z1-.18,.48,.15)]:cube('HU_MAIN_CAPITAL',(u,.082,zz),(w,.35,h),stone,.006)
 for a in [-.17,0,.17]:ornament('HU_MAIN_CAPITAL',u+a,.278,z1-.12,.105)
# Deep eave with dentils and brackets under the source roof edge (~LN02 430m).
for j,(zz,hh,dd) in enumerate([(20.55,.17,.30),(20.78,.25,.39),(20.99,.11,.60),(21.13,.17,.82),(21.285,.10,.92),(21.405,.14,.74),(21.53,.10,.77)]):cube('HU_MAIN_EAVE',((umin+umax)/2,.05,zz),(umax-umin+.08,dd,hh),stone,.006)
for u in np.arange(umin+.15,umax,.37):cube('HU_MAIN_DENTILS',(u,.38,21.02),(.15,.26,.16),stone,.007)
for u in np.arange(umin+.30,umax,1.27):cube('HU_MAIN_EAVE_BRACKETS',(u,.17,20.70),(.20,.51,.41),stone,.011)
# Curved corner uses the actual AV-fitted center/radius and source arc span.
T=np.array(d['corner']['center_local']);radius=d['corner']['radius_m'];a0,a1=np.radians(d['corner']['visible_angles_deg'])
def curved(name,z0,z1,r0,r1,aa,bb,mat=stone):
 if bb-aa<1e-7 or z1-z0<1e-7:return
 N=max(2,int(np.ceil((bb-aa)*48)));angles=np.linspace(aa,bb,N+1);vv=[]
 for z,r in [(z0,r0),(z0,r1),(z1,r1),(z1,r0)]:vv.extend([[*(T+r*np.array([np.cos(a),np.sin(a)])),Z+z] for a in angles])
 ff=[];n=N+1
 for j in range(4):
  for k in range(N):ff.append((j*n+k,j*n+k+1,((j+1)%4)*n+k+1,((j+1)%4)*n+k))
 ff.extend([(0,n,2*n,3*n),(n-1,4*n-1,3*n-1,2*n-1)]);add(name,vv,ff,mat,.002)
angles=np.radians([-64.42,-13.6,37.24])
def tangent_frame(a):
 normal=np.array([np.cos(a),np.sin(a)]);tangent=np.array([-normal[1],normal[0]]);base=T+normal*radius
 def transform(u,v,z):
  p=base+tangent*u+normal*v;return np.array([p[0],p[1],Z+z])
 return transform
corner_levels=[{'name':'GROUND','bottom':-.36,'top':4.95,'sill':.21,'head':4.38},*d['levels']]
for li,L in enumerate(corner_levels):
 name='HU_CORNER_'+L['name'];width=2.04 if li==0 else 1.26 if li==1 else 1.39;half=np.arcsin((width/2)/radius);cursor=a0
 for k,a in enumerate(angles):
  left,right=a-half,a+half
  if left>cursor:curved(name+'_WALL',L['sill'],L['head'],radius-.62,radius,cursor,left)
  cursor=right
  # Opening's straight frame sits in its measured curved wall; planar glass.
  transform=tangent_frame(a)
  for side,ang in [('L',left),('R',right)]:
   # Reveals close the small arc/chord offset beside the planar joinery.
   pass
  style='simple' if li==0 else 'small' if li==1 else 'pediment' if li==2 else 'cornice' if li==3 else 'simple'
  window(name+f'_W{k}',0,width,L['sill'],L['head'],style,transform,seed=li*17+k)
 for z0,z1 in [(L['bottom'],L['sill']),(L['head'],L['top'])]:curved(name+'_BANDS',z0,z1,radius-.65,radius,a0,a1)
 if cursor<a1:curved(name+'_WALL',L['sill'],L['head'],radius-.62,radius,cursor,a1)
 if li==0:
  for z in np.arange(.37,4.4,.35):curved(name+'_RUSTIC_JOINT',z,z+.021,radius+.001,radius+.003,a0,a1,plinth)
 else:
  for z,h,projection in [(L['top']-.11,.10,.13),(L['top']-.03,.055,.23)]:curved(name+'_COURSE',z,z+h,radius-.1,radius+projection,a0,a1)
# Stone curved balcony beneath the principal corner windows.
for z0,z1,r0,r1 in [(8.60,8.81,radius-.10,radius+.97),(8.94,9.06,radius+.70,radius+.95),(9.72,9.86,radius+.68,radius+.99)]:curved('HU_CORNER_BALCONY',z0,z1,r0,r1,a0,a1)
for a in np.arange(a0+.03,a1-.025,.056):baluster('HU_CORNER_BALUSTERS',T+(radius+.83)*np.array([np.cos(a),np.sin(a)]),9.04,.69)
for a in np.linspace(a0+.03,a1-.03,7):
 transform=tangent_frame(a);cube('HU_CORNER_BALCONY_POST',(0,.81,9.37),(.20,.27,.92),stone,.006,transform);cube('HU_CORNER_BALCONY_CORBEL',(0,.37,8.40),(.27,.80,.49),stone,.013,transform)
for z0,z1,rr in [(20.56,20.73,.22),(20.91,21.04,.36),(21.15,21.34,.53),(21.37,21.53,.45)]:curved('HU_CORNER_EAVE',z0,z1,radius-.1,radius+rr,a0,a1)
for a in np.arange(a0+.02,a1,.085):cube('HU_CORNER_DENTILS',(0,.29,21.03),(.16,.31,.21),stone,.006,tangent_frame(a))
# Build compact semantic meshes; each window/level remains separately editable.
for (name,_),g in groups.items():
 me=bpy.data.meshes.new(name);me.from_pydata(g['v'],[],g['f']);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free();ob=bpy.data.objects.new(name,me);col.objects.link(ob);me.materials.append(g['mat'])
 if g['smooth']:
  for p in me.polygons:p.use_smooth=True
 uv=me.uv_layers.new(name='metre_scale')
 for face in me.polygons:
  axis=int(np.argmax(abs(np.array(face.normal))));axes=[i for i in range(3) if i!=axis]
  for li in face.loop_indices:
   p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/3,p[axes[1]]/3)
 if g['bevel']:
  mod=ob.modifiers.new('Fine material edge radius','BEVEL');mod.width=g['bevel'];mod.segments=2;ob.modifiers.new('Weighted architectural normals','WEIGHTED_NORMAL')
 ob['source_id']='EGID9011202 / AV13983 / SPPA facade';ob['evidence_basis']=d['basis'];ob['quality_status']='working reconstruction';ob['collision_role']='solid_pending_runtime'
# Official roof triangles, with their own slope-aware texture coordinates.
for key in ['slate','roof_metal','dormer_wall']:
 ps=[p for p in d['roof_pieces'] if p['kind']==key]
 if not ps:continue
 vv=np.array([t for p in ps for t in p['triangles']]).reshape(-1,3);me=bpy.data.meshes.new('HU_SOURCE_ROOF_'+key.upper());me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update();uv=me.uv_layers.new(name='slope_metres');uv.data.foreach_set('uv',np.array([t for p in ps for t in p['uv']],dtype=np.float32).reshape(-1));me.materials.append({'slate':roof,'roof_metal':zinc,'dormer_wall':stone}[key]);ob=bpy.data.objects.new(me.name,me);col.objects.link(ob);ob['source_id']='bauten_dachmodell_3d EGID9011202';ob['evidence_basis']='Official source roof/wall surfaces clipped to reconstruction strip; source vertices retained, material is a CC0 visual proxy.'
 if key!='dormer_wall':mod=ob.modifiers.new('Roofing physical backing','SOLIDIFY');mod.thickness=.025;mod.offset=-1
cutpath=R/'derived/bellevue/west_context/haus_upper_corner_photo_cut.json';cut=json.loads(cutpath.read_text());ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};orig={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for p in cut['overrides']:
 ob=ctx[str(p['node'])];src=orig[str(p['node'])];vv=np.array(p['vertices']);uvv=np.array(p['uv_source_v_unflipped']);me=bpy.data.meshes.new('HU_CONTEXT_'+str(p['node']));me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.astype(np.float32).reshape(-1));ob.data=me;ob['construction_mask']=cut['mask_basis']
for ob in col.objects:ob['egid']=9011202;ob['place']='Haus Bellevue upper south and corner';ob['quality_status']='native candidate, not accepted'
# Eye-level cross-street inspection uses actual authored ground, not an aerial pose.
for name,u,v,target,lens in [('HB_QA_FULL_FACADE',13.5,23,(14,0,12.7),21),('HB_QA_CORNER',39,14,(31,-1.5,10.6),23)]:
 xy=P(u,v,40);z=None
 for ob in bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].all_objects:
  if ob.type=='MESH' and (ob.name.startswith('BE_PAVING_') or ob.name in ['BE_WEST_PLATFORM','HB_SIDEWALK_ASPHALT']):
   hit,pt,_,_=ob.ray_cast(Vector(xy),Vector((0,0,-1)))
   if hit and pt.z<15:z=pt.z if z is None else max(z,pt.z)
 assert z is not None, 'Review camera must be on built ground'
 cd=bpy.data.cameras.new(name);ob=bpy.data.objects.new(name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(ob);ob.location=Vector((xy[0],xy[1],z+1.65));ob.rotation_euler=(Vector(P(*target))-ob.location).to_track_quat('-Z','Y').to_euler();cd.lens=lens;ob['eye_height_m']=1.65;ob['floor_height_local']=z
sc['version']='G1_010';sc['photo_cut_file']=str(cutpath.relative_to(R));sc.camera=bpy.data.objects['HB_QA_FULL_FACADE'];bpy.context.view_layer.update();bpy.ops.file.pack_all();native=R/'native/G1_010_haus_upper_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=sc['version'],native=str(native),source_cut_file=sc['photo_cut_file'],source_cut_nodes=len(cut['overrides']),source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),accepted=False,not_published=True,next='Review actual eye-level facade/corner and roof joins, correct artifacts before runtime review');(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2))
e=R/'evidence/G1_010';e.mkdir(exist_ok=True);(e/'build.json').write_text(json.dumps({'version':sc['version'],'objects':len(col.objects),'roof_triangles':len(d['roof_pieces']),'native':str(native),'accepted':False,'basis':d['basis']},indent=2));print(json.dumps({'version':sc['version'],'objects':len(col.objects),'native':str(native),'accepted':False}))
