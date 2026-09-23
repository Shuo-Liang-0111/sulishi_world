"""EGID302040350: surveyed envelope, dated-plan public WC, inferred fabrication.

Run once from G1_013r2 through the live Blender MCP. Not an interaction acceptance.
"""
import bpy,bmesh,json,math,ast,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_013r2'
d=json.loads((R/'derived/bellevue/south_service/input.json').read_text());g=json.loads((R/'derived/bellevue/south_service/build_input.json').read_text());root=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION']
assert '24_BELLEVUE_SERVICE_PAVILION' not in bpy.data.collections
building=bpy.data.collections.new('24_BELLEVUE_SERVICE_PAVILION');root.children.link(building)
C=np.array(d['center_lv95'])-np.array(d['origin'][:2]);right=np.array(d['axis_u']);front=np.array(d['axis_v']);FLOOR=g['floor_local_inferred'];H=11.384-FLOOR
tree=ast.parse((R/'tools/blender_build_bellevue.py').read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','triangles','box','lathe','tube','arc','P']],type_ignores=[]),'geometry','exec'))
source=ast.parse((R/'tools/blender_build_bellevue_west_fixtures.py').read_text());exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ['material','text_obj']],type_ignores=[]),'materials_and_labels','exec'))
def mat(name,color,rough=.5,metal=0,trans=0):
 m=material('SV | '+name,color,rough,metal);bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Transmission Weight'].default_value=trans;bs.inputs['IOR'].default_value=1.47;return m
ceramic=mat('warm glazed ceramic',(.71,.70,.673),.29);grout=mat('fine warm mortar',(.39,.385,.36),.89)
frame=mat('blue grey metal window profiles',(.125,.178,.201),.38,.62);seal=bpy.data.materials['BE | equipment black gasket'];metal=bpy.data.materials['BE | satin anodised aluminium']
paint=bpy.data.materials['CF | metre-scale satin coat'];roofmat=bpy.data.materials['BE | folded grey metal roof'];soffit=bpy.data.materials['BE | warm pale painted soffit'];wall=bpy.data.materials['HB | shop interior mineral paint']
glass=bpy.data.materials['BE | clear curved 12mm glass'];frost=mat('etched privacy glazing',(.74,.83,.82),.38,0,.84)
partition=mat('pale turquoise privacy panels',(.43,.61,.585),.39);floor_mat=mat('dark grey mineral floor tiles',(.116,.123,.12),.66);floor_grout=mat('floor joints',(.051,.055,.054),.93)
porcelain=bpy.data.materials['BE | warm porcelain'];counter=mat('charcoal composite basin',(.025,.030,.029),.34);mirror=mat('mirror silver',(.82,.84,.82),.055,1);white=bpy.data.materials['BE | equipment warm white'];ink=bpy.data.materials['BE | equipment dark ink'];wood=bpy.data.materials['oak_veneer_01']
# Existing original metre-scale surface maps, independent of building identity.
for m in [ceramic,frame,floor_mat,partition]:
 bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(R/'derived/materials/satin_grey_coat/normal_gl.png'),check_existing=True);tex.image.colorspace_settings.name='Non-Color';nn=m.node_tree.nodes.new('ShaderNodeNormalMap');nn.inputs['Strength'].default_value=.16 if m==ceramic else .3;m.node_tree.links.new(tex.outputs['Color'],nn.inputs['Color']);m.node_tree.links.new(nn.outputs['Normal'],bs.inputs['Normal']);m['surface_basis']='Original coating microtexture; physical fabrication inferred, not a scan of this building.'
def uv(ob,scale=1):
 if ob.type!='MESH':return
 layer=ob.data.uv_layers.active or ob.data.uv_layers.new(name='metre_scale')
 for face in ob.data.polygons:
  for li in face.loop_indices:
   p=ob.data.vertices[ob.data.loops[li].vertex_index].co;q=np.array(p[:2])-C
   first=float(q@right) if abs(face.normal.z)>.6 or abs(np.array(face.normal[:2])@front)>=abs(np.array(face.normal[:2])@right) else float(q@front)
   layer.data[li].uv=(first/scale,(float(q@front) if abs(face.normal.z)>.6 else p.z-FLOOR)/scale)
 return ob
class Batch:
 def __init__(self):self.v=[];self.f=[]
 def box(self,c,size):
  c=np.array(c);h=np.array(size)/2;k=len(self.v);self.v.extend([P(*(c+h*np.array(a))) for a in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]);self.f.extend([tuple(k+i for i in face) for face in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])
 def finish(self,name,mat,bevel=0):
  ob=mesh(name,self.v,self.f,mat)
  if bevel:
   mod=ob.modifiers.new('Glazed edge radius','BEVEL');mod.width=bevel;mod.segments=2;ob.modifiers.new('Weighted tile normals','WEIGHTED_NORMAL')
  uv(ob);return ob
tiles=Batch();ftiles=Batch();fasteners=Batch()
def tiledwall(name,u0,u1,v,z0,z1,depth=.18):
 box(name+'_SUBSTRATE',((u0+u1)/2,v,(z0+z1)/2),(u1-u0,depth,z1-z0),grout,.002)
 # Horizontal .20x.10m tiles: dimension inferred from the dated facade photo.
 for sign in [-1,1]:
  for a in np.arange(u0,u1,.20):
   for zz in np.arange(z0,z1,.10):
    du=min(.20,u1-a);dh=min(.10,z1-zz)
    if min(du,dh)<.008:continue
    tiles.box((a+du/2,v+sign*(depth/2+.004),zz+dh/2),(du-.003,.010,dh-.003))
def mullion(name,u,v,z0,z1,w=.052):return box(name,(u,v,(z0+z1)/2),(w,.085,z1-z0),frame,.003)
def window(name,u0,u1,v,z0,z1,privacy=True):
 box(name+'_GASKET',((u0+u1)/2,v,(z0+z1)/2),(u1-u0,.040,z1-z0),seal,.004)
 box(name+'_PANE',((u0+u1)/2,v-.027,(z0+z1)/2),(u1-u0-.07,.009,z1-z0-.07),frost if privacy else glass,.001)
 # The gasket is a perimeter, not an opaque rectangle behind the pane.
 ob=bpy.data.objects[name+'_GASKET'];bpy.data.objects.remove(ob,do_unlink=True)
 for u in [u0,u1]:mullion(name+'_JAMB_'+str(u),u,v,z0,z1)
 for z in [z0,z1]:box(name+'_RAIL_'+str(z),((u0+u1)/2,v,z),(u1-u0,.085,.050),frame,.003)
def door(name,u0,u1,v,privacy=True,angle=0,height=2.21):
 parts0=set(building.objects.keys());width=u1-u0
 for u in [u0-.03,u1+.03]:mullion(name+'_FRAME_'+str(u),u,v,0,height+.08,.07)
 box(name+'_HEADER',((u0+u1)/2,v,height+.045),(width+.13,.105,.07),frame,.003)
 parts0=set(building.objects.keys());window(name+'_LEAF',u0+.014,u1-.014,v-.01,.032,height,privacy)
 box(name+'_KICK',((u0+u1)/2,v-.061,.14),(width-.08,.021,.20),frame,.005)
 for z in [1.05,1.55]:box(name+'_MIDRAIL_'+str(z),((u0+u1)/2,v-.01,z),(width-.03,.075,.032),frame,.003)
 tube(name+'_PULL',[P(u1-.13,v-.115,.92),P(u1-.13,v-.145,.92),P(u1-.13,v-.145,1.18),P(u1-.13,v-.115,1.18)],.012,metal)
 for zz in [.25,1.08,1.94]:box(name+'_HINGE_'+str(zz),(u0+.016,v-.064,zz),(.025,.030,.092),metal,.003)
 parts=[ob for ob in building.objects if ob.name not in parts0];pivot=bpy.data.objects.new(name+'_HINGE_PIVOT',None);building.objects.link(pivot);pivot.location=P(u0, v, 0);bpy.context.view_layer.update()
 for ob in parts:ob.parent=pivot;ob.matrix_parent_inverse=pivot.matrix_world.inverted()
 pivot['interaction_role']='hinged_door';pivot['closed_rotation_z']=0.;pivot['open_rotation_z']=math.radians(angle or -90);pivot['state']='open' if angle else 'closed';pivot['clear_opening_m']=width-.075;pivot['runtime_enabled']=False;pivot.rotation_euler.z=math.radians(angle)
 return pivot
def solid_door(name,u0,u1,v,height=2.15,angle=0):
 old=set(building.objects.keys());box(name+'_LEAF',((u0+u1)/2,v,height/2+.01),(u1-u0-.025,.04,height-.02),wall,.006)
 for z in [.22,1.0,1.88]:box(name+'_HINGE_'+str(z),(u0+.01,v-.025,z),(.023,.025,.075),metal,.002)
 tube(name+'_HANDLE',[P(u1-.10,v-.025,1.03),P(u1-.10,v-.080,1.03),P(u1-.25,v-.08,1.03)],.01,metal)
 box(name+'_LOCK',(u1-.10,v-.029,.94),(.027,.010,.048),metal,.003)
 pivot=bpy.data.objects.new(name+'_PIVOT',None);building.objects.link(pivot);pivot.location=P(u0,v,0);bpy.context.view_layer.update()
 for ob in list(building.objects):
  if ob.name not in old and ob!=pivot:ob.parent=pivot;ob.matrix_parent_inverse=pivot.matrix_world.inverted()
 pivot['interaction_role']='hinged_door';pivot['closed_rotation_z']=0.;pivot['open_rotation_z']=math.radians(angle or -80);pivot['state']='open' if angle else 'closed';pivot['runtime_enabled']=False;pivot.rotation_euler.z=math.radians(angle);return pivot
def loft(name,u,v,profiles,mat,axis='z',segments=56):
 verts=[];faces=[]
 for rx,ry,zz in profiles:
  for i in range(segments):
   a=2*math.pi*i/segments;x=rx*math.sin(a);y=ry*math.cos(a)
   verts.append(P(u+x,v+y,zz) if axis=='z' else P(u+x,v-zz,1.10+y))
 for j in range(len(profiles)-1):
  for i in range(segments):faces.append((j*segments+i,j*segments+(i+1)%segments,(j+1)*segments+(i+1)%segments,(j+1)*segments+i))
 return mesh(name,verts,faces,mat,True)
# Surveyed roofs and soffits: never flatten the central skylight or move cantilever.
for part in d['source_parts']:
 if part['kind']=='EO13':
  name={'GroundSurface':'SOFFIT','WallSurface':'FASCIA','RoofSurface':'CANOPY_ROOF'}[part['type']];triangles('SV_SOURCE_'+name,part['triangles'],soffit if name=='SOFFIT' else roofmat,'Exact official '+part['id'])
 if part['kind']=='BB04' and part['type']=='RoofSurface':
  t=np.array(part['triangles']);mask=t[:,:,2].max(1)>11.89;triangles('SV_SOURCE_FLAT_ROOF',t[~mask],roofmat,'Exact official '+part['id']);sky=triangles('SV_SOURCE_SKYLIGHT',t[mask],frost,'Official arch; translucent material inferred from dated interior photo');mod=sky.modifiers.new('Inferred glazing thickness','SOLIDIFY');mod.thickness=.018
 if part['kind']=='BB04' and part['type']=='WallSurface':
  t=np.array(part['triangles']);top=t[t[:,:,2].min(1)>11.88]
  if len(top):triangles('SV_SOURCE_SKYLIGHT_ENDS',top,soffit,'Official source upper arch end closure')
triangles('SV_INTERIOR_CEILING',g['parts']['ceiling'],wall,'Ceiling under retained roof; skylight opening preserved')
old=bpy.data.objects['BS_ASPHALT'];new=triangles('SV_TEMP_GROUND',g['parts']['outside_asphalt'],bpy.data.materials['asphalt_03'],g['basis']);old.data=new.data;bpy.data.objects.remove(new,do_unlink=True);uv(old,2.05)
uv(triangles('SV_LANDING_ASPHALT',g['parts']['apron'],bpy.data.materials['asphalt_03'],g['basis']),2.05)
base=np.array(g['parts']['floor']);base[:,:,2]-=.009;uv(triangles('SV_INTERIOR_FLOOR',base,floor_grout,g['basis']))
# Tiles clipped to the AV polygon are prepared outside Blender, avoiding Shapely dependency.
tiles_ob=triangles('SV_FLOOR_TILES',[tri for tile in g['floor_tiles'] for tri in tile['triangles']],floor_mat,'Inferred 600mm mineral tile, AV-clipped perimeter');md=tiles_ob.modifiers.new('8mm tile thickness','SOLIDIFY');md.thickness=.008;md=tiles_ob.modifiers.new('Tile edge radius','BEVEL');md.width=.0008;md.segments=2
# Straight north wall: solid privacy plinth, six source-located advertising cases.
tiledwall('SV_NORTH',-7.68,7.68,3.685,.0,2.18)
for i in range(14):window('SV_NORTH_CLERESTORY_'+str(i),-7.68+i*1.097,-7.68+(i+1)*1.097,3.69,2.21,H-.04,True)
# Front bay positions proportioned from the 2015 municipal plan, not surveyed openings.
openings=[(-7.50,-6.24,'ACCESSIBLE'),(-4.02,-2.84,'WOMEN'),(.76,2.04,'MEN'),(4.28,5.48,'SERVICE')]
piers=[-7.68,-6.08,-4.18,-2.66,-1.05,.55,2.22,3.98,5.68,7.68]
for i,u in enumerate(piers):tiledwall('SV_FRONT_PIER_'+str(i),u-.085,u+.085,-3.685,0,H)
for i,(a,b) in enumerate(zip(piers[:-1],piers[1:])):
 overlap=next((x for x in openings if x[0]>=a-.2 and x[1]<=b+.2),None)
 if overlap:
  u0,u1,role=overlap
  for l,r in [(a+.085,u0-.06),(u1+.06,b-.085)]:
   if r>l+.01:tiledwall('SV_FRONT_INFILL_'+str(i)+'_'+str(l),l,r,-3.685,0,2.23)
  door('SV_ENTRY_'+role,u0,u1,-3.70,True,angle=-62 if role=='WOMEN' else 0)
 else:
  tiledwall('SV_FRONT_SILL_'+str(i),a+.085,b-.085,-3.685,0,.73)
  window('SV_FRONT_WINDOW_'+str(i),a+.10,b-.10,-3.70,.77,2.22,True)
 window('SV_FRONT_UPPER_'+str(i),a+.10,b-.10,-3.70,2.27,H-.04,False)
# Curved ends follow the official footprint radius; each pane has thickness and joints.
for side,uc,start in [('E',7.68,0),('W',-7.68,180)]:
 arc('SV_'+side+'_CURVED_PLINTH',3.60,3.775,0,.75,start,start+180,ceramic,center=(uc,0),step=1)
 for i in range(12):
  a0=start+i*15;a1=a0+15;arc('SV_'+side+'_GLAZING_'+str(i),3.712,3.724,.80,H-.06,a0+.5,a1-.5,glass,center=(uc,0),step=1)
  a=math.radians(a0);uu=uc+3.733*math.sin(a);vv=3.733*math.cos(a);lathe('SV_'+side+'_CURVE_MULLION_'+str(i),[(.028,.74),(.028,H-.035)],frame,(uu,vv),steps=16)
 for zz in [.77,2.21,H-.035]:arc('SV_'+side+'_CURVE_RAIL_'+str(zz),3.69,3.78,zz-.024,zz+.024,start,start+180,frame,center=(uc,0),step=1)
 for zz in np.arange(.1,.75,.1):arc('SV_'+side+'_TILE_COURSE_'+str(zz),3.775,3.777,zz-.0014,zz+.0014,start,start+180,grout,center=(uc,0),step=1)
 # Service end bays are visually enclosed but not claimed to be open current tenancies.
 box('SV_'+side+'_SERVICE_SCREEN',(uc,0,1.45),(.12,7.3,2.90),wall,.008)
# Ceiling-to-floor interior boundaries and dated public hall organization.
for u in [-7.53,-4.2,.55,3.96,5.66]:box('SV_PARTITION_LONG_'+str(u),(u,0,H/2),(.12,7.22,H),wall,.005)
# Opening in the shared service/women partition for the changing room.
ob=bpy.data.objects['SV_PARTITION_LONG_-4.2'];bpy.data.objects.remove(ob,do_unlink=True)
for v0,v1 in [(-3.58,-.87),(.17,3.60)]:box('SV_CHANGE_ROOM_WALL_'+str(v0),(-4.2,(v0+v1)/2,H/2),(.12,v1-v0,H),wall,.005)
box('SV_CHANGE_ROOM_HEADER',(-4.2,-.35,(2.2+H)/2),(.12,1.04,H-2.2),wall,.005)
for v in [-1.73,-.55,1.05,2.69]:box('SV_SERVICE_DIVISION_'+str(v),(-5.865,v,1.19),(3.20,.11,2.38),wall,.005)
for a,b in [(-4.12,-.28),(.67,3.88)]:
 box('SV_HALL_LOWER_SCREEN_'+str(a),((a+b)/2,-1.66,1.1),(b-a,.12,2.2),wall,.005)
 # Leave an actual one-metre route around the screen on the west side.
 ob=bpy.data.objects['SV_HALL_LOWER_SCREEN_'+str(a)];ob.location+=Vector((*right*.48,0));ob.scale.x=1 # shorten mesh in world basis below
 vv=np.array([v.co[:] for v in ob.data.vertices]);q=(vv[:,:2]-C)@right;newq=a+1.0+(q-a)*(b-a-1.0)/(b-a);vv[:,:2]+=(newq-q)[:,None]*right;ob.location=(0,0,0);ob.data.vertices.foreach_set('co',vv.ravel());ob.data.update()
for j,(a,b) in enumerate(zip([-4.14,-2.98,-1.82,-.66,.50,1.66,2.82],[-2.98,-1.82,-.66,.50,1.66,2.82,3.90])):
 center=(a+b)/2
 if j==0:box('SV_CUBICLE_SIDE_FIRST',(a,2.73,1.11),(.085,1.75,2.22),wall,.006)
 box('SV_CUBICLE_SIDE_'+str(j),(b,2.73,1.11),(.085,1.75,2.22),wall,.006)
 for l,r in [(a+.045,a+.18),(b-.16,b-.045)]:box('SV_CUBICLE_FRONT_'+str(j)+'_'+str(l),((l+r)/2,1.84,1.11),(r-l,.06,2.22),wall,.006)
 solid_door('SV_CUBICLE_'+str(j),a+.18,b-.16,1.84,height=2.1,angle=-24 if j==0 else 0)
 # Wall-hung porcelain pan: open bowl, inner well and separate oval seat.
 loft('SV_WC_'+str(j)+'_PAN',center,3.14,[(.05,.055,.21),(.14,.19,.24),(.185,.265,.40),(.188,.267,.43),(.141,.209,.425),(.106,.165,.27),(.045,.055,.24)],porcelain)
 loft('SV_WC_'+str(j)+'_SEAT',center,3.14,[(.192,.271,.432),(.192,.271,.45),(.139,.202,.456),(.138,.202,.433),(.192,.271,.432)],white)
 box('SV_WC_'+str(j)+'_WALL_SUPPORT',(center,3.48,.33),(.23,.20,.19),porcelain,.03)
 box('SV_WC_'+str(j)+'_FLUSH',(center,3.584,1.0),(.24,.012,.16),metal,.013)
 for k,dx in enumerate([-.048,.048]):box('SV_WC_'+str(j)+'_BUTTON_'+str(k),(center+dx,3.574,1.0),(.079,.01,.10),paint,.01)
 tube('SV_WC_'+str(j)+'_ROLL_ARM',[P(b-.11,2.62,.73),P(b-.24,2.62,.73),P(b-.24,2.77,.73)],.009,metal)
 box('SV_WC_'+str(j)+'_ROLL_BOX',(b-.09,2.63,.85),(.12,.24,.23),metal,.02)
 # Tiny wall gap and support are explicit; no floating fixture.
 # Flush buttons will become semantic controls during the interaction pass.
 bpy.data.objects['SV_WC_'+str(j)+'_FLUSH']['interaction_role']='flush_control_pending_runtime'
# Women/men basin counters along their shared wall; source photo shows charcoal units.
for side,us in [('W',.34),('M',.77)]:
 sg=-1 if side=='W' else 1
 for j,v in enumerate([-.8,.1,1.0]):
  u=us+sg*.24
  bowl=loft('SV_BASIN_'+side+str(j),u,v,[(.31,.28,.78),(.31,.28,.85),(.225,.195,.86),(.17,.14,.72),(.06,.055,.705),(.31,.28,.78)],counter)
  box('SV_BASIN_'+side+str(j)+'_BACK',(us+sg*.015,v,.77),(.17,.62,.24),counter,.015)
  tube('SV_BASIN_'+side+str(j)+'_SPOUT',[P(us+sg*.06,v,.85),P(us+sg*.06,v,1.01),P(us+sg*.26,v,1.01),P(us+sg*.26,v,.98)],.015,metal)
  bpy.data.objects['SV_BASIN_'+side+str(j)+'_SPOUT']['interaction_role']='tap_pending_runtime'
  box('SV_BASIN_'+side+str(j)+'_MIRROR',(us,v,1.54),(.014,.62,.70),mirror,.004)
  box('SV_BASIN_'+side+str(j)+'_SOAP',(us+sg*.085,v+.34,1.13),(.12,.13,.22),metal,.013)
# Three wall urinals and turquoise privacy screens, according to dated plan/photo.
for j,v in enumerate([-.91,.04,.99]):
 # Sculpt in a local Z-facing profile, then rotate about the vertical axis to east wall.
 old=set(building.objects.keys());ob=loft('SV_URINAL_'+str(j),0,0,[(.045,.055,.065),(.16,.285,.12),(.22,.38,.22),(.18,.33,.235),(.09,.20,.105),(.045,.055,.065)],porcelain,axis='y')
 vv=np.array([vtx.co[:] for vtx in ob.data.vertices]);rel=vv[:,:2]-C;uu=rel@right;vvv=rel@front;new_u=3.875+vvv;new_v=v-uu;vv[:,:2]=C+new_u[:,None]*right+new_v[:,None]*front;ob.data.vertices.foreach_set('co',vv.ravel());ob.data.update()
 box('SV_URINAL_'+str(j)+'_FLUSH',(3.881,v,1.63),(.014,.15,.18),metal,.012)
 if j<2:box('SV_URINAL_SCREEN_'+str(j),(3.52,v+.46,1.10),(.70,.018,1.17),partition,.014)
# Wheelchair WC fixture and grab rails in the dated south-west room.
loft('SV_ACCESSIBLE_PAN',-5.16,-2.28,[(.11,.14,.12),(.16,.23,.30),(.20,.28,.46),(.146,.21,.46),(.10,.15,.30),(.055,.06,.27)],porcelain)
for u in [-5.52,-4.81]:tube('SV_ACCESSIBLE_RAIL_'+str(u),[P(u,-1.90,.79),P(u,-2.53,.79),P(u,-2.59,.75),P(u,-2.59,.44)],.016,metal)
box('SV_ACCESSIBLE_BACK_CISTERN',(-5.16,-1.88,.83),(.38,.16,.51),porcelain,.05)
loft('SV_ACCESSIBLE_BASIN',-6.65,-2.07,[(.29,.22,.76),(.29,.22,.82),(.235,.16,.83),(.17,.11,.69),(.04,.035,.675)],porcelain)
tube('SV_ACCESSIBLE_TAP',[P(-6.65,-1.91,.82),P(-6.65,-1.91,.98),P(-6.65,-2.08,.98)],.014,metal)
box('SV_CHANGING_TABLE',(-5.74,-.43,.89),(1.11,.58,.072),white,.035)
for u in [-6.16,-5.32]:tube('SV_CHANGING_SUPPORT_'+str(u),[P(u,-.50,.90),P(u,-.48,.41),P(u,-.1,.71)],.015,metal)
# Entry turnstiles are dimensional objects now; actual enabled movement is a later pass.
for name,u in [('W',-3.50),('M',1.30)]:
 box('SV_GATE_'+name+'_BODY',(u+.42,-1.72,.86),(.26,.42,.42),metal,.025)
 tube('SV_GATE_'+name+'_LEG',[P(u+.42,-1.72,0),P(u+.42,-1.72,.69)],.052,metal)
 for a in [0,120,240]:
  t=math.radians(a);tube('SV_GATE_'+name+'_ARM_'+str(a),[P(u+.29,-1.72,.85),P(u-.18,-1.72+.19*math.sin(t),.85+.19*math.cos(t))],.015,metal)
 # Separate return railing, no barrier drawn across the public exterior pavement.
 tube('SV_GATE_'+name+'_RETURN',[P(u-.44,-1.15,0),P(u-.44,-1.15,.92),P(u-.44,-2.16,.92),P(u-.44,-2.16,0)],.017,metal)
# Source-positioned posters and benches: assembly anchors preserved, details inferred.
poster_mats=[bpy.data.materials['BE | inferred poster '+key] for key in ['teal','coral','blue']]
for i,f in enumerate(g['facilities']):
 xy=np.array(f['geometry']['coordinates'])
 if xy.ndim>1:xy=xy[0]
 xy=xy[:2]-np.array(d['origin'][:2])-C;u=float(xy@right);v=float(xy@front);old=set(building.objects.keys())
 if 'plakatstelle' in f['id']:
  base='SV_AD_'+f['id'].split('.')[-1];box(base+'_BACK',(u,v+.045,1.39),(1.195,.060,1.78),paint,.008)
  box(base+'_ART',(u,v+.078,1.39),(1.135,.003,1.72),poster_mats[i%3],.001)
  box(base+'_GLASS',(u,v+.083,1.39),(1.14,.005,1.725),glass,.001)
  for sign in [-1,1]:box(base+'_FRAME_V'+str(sign),(u+sign*.582,v+.085,1.39),(.030,.022,1.78),metal,.002)
  for zz in [.515,2.265]:box(base+'_FRAME_H'+str(zz),(u,v+.085,zz),(1.19,.022,.030),metal,.002)
  for j,line in enumerate([['Zürich','am Wasser'],['Zu Fuss','durch die Stadt'],['Wege','verbinden']][i%3]):text_obj(base+'_TEXT_'+str(j),line,u+.47,v+.081,2.02-j*.17,.115,white,side=-1)
  for j in range(7):tube(base+'_ART_LINE_'+str(j),[P(u-.44+k*.044,v+.081,.72+j*.10+.045*math.sin(k*.38+j)) for k in range(21)],.0012,white)
  text_obj(base+'_FOOT','Stadt. Wege. Begegnungen.',u+.47,v+.081,.60,.035,white,side=-1)
 else:
  base='SV_BENCH_'+f['id'].split('.')[-1];seat=v+.44
  for j in range(6):uv(box(base+'_SLAT_'+str(j),(u,seat-.23+j*.094,.46),(2.65,.081,.042),wood,.007),2)
  for j in range(4):uv(box(base+'_BACK_'+str(j),(u,v+.15+j*.013,.625+j*.084),(2.65,.036,.071),wood,.007),2)
  for k,du in enumerate([-.99,.99]):
   tube(base+'_FRAME_'+str(k),[P(u+du,v+.75,.014),P(u+du,v+.71,.41),P(u+du,v+.21,.41),P(u+du,v+.14,.90)],.019,frame)
   tube(base+'_REAR_LEG_'+str(k),[P(u+du,v+.24,.42),P(u+du,v+.21,.014)],.019,frame)
   tube(base+'_ARM_'+str(k),[P(u+du,v+.18,.70),P(u+du,v+.60,.70),P(u+du,v+.71,.66)],.016,metal)
   for dv in [.21,.75]:box(base+'_FOOT_'+str(k)+str(dv),(u+du,v+dv,.010),(.09,.10,.018),frame,.002)
 for ob in building.objects:
  if ob.name not in old:ob['source_id']=f['id'];ob['source_anchor_lv95']=json.dumps(f['geometry']['coordinates']);ob['assembly_offset_basis']='Inventory anchor; wall panels offset to exterior face, seating set forward of wall. Format, wood, hardware, artwork inferred.'
# Modest dated-use signage, with no current hours, prices or retailer identity invented.
for role,u,label in [('WOMEN',-3.43,'WC  Damen'),('MEN',1.40,'WC  Herren'),('ACCESSIBLE',-6.87,'WC')]:
 box('SV_SIGN_'+role,(u,-3.761,2.34),(1.02,.014,.115),frame,.003);text_obj('SV_SIGN_TEXT_'+role,label,u-.42,-3.77,2.309,.068,white)
tiles.finish('SV_CERAMIC_FACE_TILES',ceramic,.0012)
# Small overhead fittings in the real rooms: construction equipment, not dramatic lighting.
for i,(u,v) in enumerate([(-2.3,-.4),(2.2,-.4),(-5.9,-2.8)]):
 box('SV_LIGHT_'+str(i),(u,v,H-.044),(.75,.105,.050),white,.012)
 ld=bpy.data.lights.new('SV_INTERIOR_'+str(i),'AREA');ld.energy=48;ld.color=(1,.945,.84);ld.shape='RECTANGLE';ld.size=.74;ld.size_y=.10;lo=bpy.data.objects.new(ld.name,ld);building.objects.link(lo);lo.location=P(u,v,H-.09)
# Explicit bounded photographic replacement only after all nine guarded fixtures exist.
cutpath=R/g['photo_cut_file'];cut=json.loads(cutpath.read_text());ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};orig={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for item in cut['overrides']:
 ob=ctx[str(item['node'])];src=orig[str(item['node'])];vv=np.array(item['vertices']);uvs=np.array(item['uv_source_v_unflipped']);me=bpy.data.meshes.new('SV_CONTEXT_'+str(item['node']));me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 layer=me.uv_layers.new(name='source_photo_uv');uvs[:,1]=1-uvs[:,1];layer.data.foreach_set('uv',uvs.astype(np.float32).ravel());ob.data=me;ob['construction_mask']=cut['mask_basis']
for ob in building.objects:
 ob['place']='Bellevueplatz_2_service_pavilion';ob['egid']=302040350;ob['quality_status']='construction_unaccepted';ob['evidence_basis']=d['basis']+' '+g['basis'] if not ob.name.startswith('SV_SOURCE_') else ob.get('evidence_basis','official source surface')
 if ob.type=='MESH':uv(ob,2.05 if ob.name=='SV_LANDING_ASPHALT' else (2 if wood in list(ob.data.materials) else 1))
 if 'collision_role' not in ob:ob['collision_role']='pending_runtime'
building['reference_date']='Municipal2015 WC layout/photo; official geometry2025; fine construction inferred, not current as-built certification'
bpy.context.view_layer.update()
for name,pos,target,lens in [('BE_QA_SERVICE_FRONT',(-12,-13,1.65),(0,-2.8,1.50),35),('BE_QA_SERVICE_NORTH',(9,12,1.65),(0,3.8,1.45),35),('BE_QA_SERVICE_ENTRY',(-5.0,-7.2,1.65),(-3.4,-2.7,1.55),35),('BE_QA_SERVICE_INTERIOR',(-3.45,-.9,1.65),(-1.3,2.0,1.25),26)]:
 cd=bpy.data.cameras.new(name);ob=bpy.data.objects.new(name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(ob);ob.location=P(*pos);ob.rotation_euler=(Vector(P(*target))-ob.location).to_track_quat('-Z','Y').to_euler();cd.lens=lens;ob['eye_height_m']=1.65;ob['grade_check_pending']=True
s['version']='G1_014';s['photo_cut_file']=g['photo_cut_file'];s.camera=bpy.data.objects['BE_QA_SERVICE_FRONT'];bpy.context.view_layer.update();bpy.ops.file.pack_all();native=R/'native/G1_014_south_service_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native));w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=s['version'],native=str(native),source_cut_file=g['photo_cut_file'],source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2));E=R/'evidence'/s['version'];E.mkdir(exist_ok=True);(E/'construction.json').write_text(json.dumps({'version':s['version'],'egid':302040350,'native':str(native),'new_objects':len(building.objects),'floor_local_inferred':FLOOR,'apron_max_slope_double_precision':g['apron_max_slope'],'dated_plan':2015,'public_cubicles':7,'accessible_wc':1,'urinals':3,'mapped_ads':6,'mapped_benches':3,'runtime_enabled':False,'accepted':False},indent=2));print(json.dumps({'version':s['version'],'new_objects':len(building.objects),'native':str(native)}))
