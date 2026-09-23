"""G1_020: source-sized Utoquai2f kiosk, bounded photographic replacement.

Opening assignment and unseen fabrication are recorded inference. This is native
authoring, not a claim of runtime interaction or entire-area visual acceptance.
"""
import bpy
import json
import math
import hashlib
import shutil
from pathlib import Path
import numpy as np
from mathutils import Vector, Matrix

ROOT = Path('F:/MyWorld/ZurichWorld')
DATA = ROOT/'derived/bellevue/utoquai_kiosk'
plan = json.loads((DATA/'build_input.json').read_text(encoding='utf-8'))
scene = bpy.context.scene
assert scene['version']=='G1_019r3'
assert '32_UTOQUAI_RIVIERA_KIOSK' not in bpy.data.collections
FLOOR, ROOF = plan['floor_local_inferred'], plan['roof_local']
HEIGHT = ROOF-FLOOR
ORIGIN = np.array(plan['source']['origin'])
CENTRE = np.array(plan['source']['centre_lv95'])-ORIGIN[:2]
ring = np.array(plan['source']['footprint_ccw_lv95']['coordinates'][0])[:-1]-ORIGIN[:2]
collection = bpy.data.collections.new('32_UTOQUAI_RIVIERA_KIOSK')
bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(collection)
collection['source_egid']=302020548
collection['basis']=plan['basis']
EVIDENCE=ROOT/'evidence/G1_020';EVIDENCE.mkdir(exist_ok=True)
materials={}

def material(name,color,rough=.5,metal=0,trans=0,micro=0):
    m=bpy.data.materials.new('UR | '+name);m.use_nodes=True
    b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value=(*color,1)
    b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
    b.inputs['Transmission Weight'].default_value=trans;b.inputs['IOR'].default_value=1.5
    m.diffuse_color=(*color,1)
    if micro:
        nodes,links=m.node_tree.nodes,m.node_tree.links
        coord=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value=780.;noise.inputs['Detail'].default_value=2
        links.new(coord.outputs['UV'],noise.inputs['Vector'])
        ramp=nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color=(max(.02,rough-.06),)*3+(1,)
        ramp.color_ramp.elements[1].color=(min(.98,rough+.06),)*3+(1,)
        links.new(noise.outputs['Fac'],ramp.inputs['Fac']);links.new(ramp.outputs['Color'],b.inputs['Roughness'])
        bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.15;bump.inputs['Distance'].default_value=micro
        links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],b.inputs['Normal'])
    m['basis']='Photo-informed generic physical finish; local wear and exact fabrication inferred.'
    materials[name]=m
    return m

panel=material('aged warm pale enamel',(.59,.61,.575),.43,micro=.00016)
inside=material('warm pale interior lining',(.60,.565,.45),.58,micro=.00009)
aluminium=material('satin aluminium extrusions',(.49,.515,.52),.32,1,micro=.00006)
steel=material('brushed stainless work surface',(.43,.46,.465),.26,1,micro=.000055)
darksteel=material('dark appliance metal',(.027,.032,.033),.34,.67)
gasket=material('rubber seals and recess',(.008,.009,.008),.79)
roofmat=material('weathered mineral roof cap',(.022,.024,.021),.91,micro=.0007)
concrete=material('grey plinth mineral',(.22,.225,.206),.86,micro=.0009)
floor_mat=material('kitchen anti-slip grey floor',(.15,.16,.145),.79,micro=.00025)
ink=material('printed charcoal',(.018,.023,.019),.75)
menu=material('matte off-white menu',(.77,.755,.68),.85)
glass=material('neutral6mm glass',(.955,.973,.961),.055,0,1)
wood=material('warm worn shelf laminate',(.25,.145,.061),.48,micro=.00012)
porcelain=material('pale ceramic vessel',(.66,.66,.61),.26)
amber=material('amber bottle glass',(.19,.075,.012),.22,0,.83)
lightmat=material('diffused work light',(.78,.74,.59),.55)
b=next(n for n in lightmat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
b.inputs['Emission Color'].default_value=(1,.89,.68,1);b.inputs['Emission Strength'].default_value=2.6

def mesh(name,vertices,faces,mat,smooth=False,uvs=None):
    data=bpy.data.meshes.new('UR_'+name);data.from_pydata(vertices,[],faces);data.update()
    if mat:data.materials.append(mat)
    layer=data.uv_layers.new(name='metre_scale')
    for face in data.polygons:
        face.use_smooth=smooth
        axis=int(np.argmax(np.abs(face.normal)))
        axes=([1,2],[0,2],[0,1])[axis]
        for li in face.loop_indices:
            vi=data.loops[li].vertex_index;p=data.vertices[vi].co
            layer.data[li].uv=uvs[vi] if uvs is not None else (p[axes[0]],p[axes[1]])
    ob=bpy.data.objects.new('UR_'+name,data);collection.objects.link(ob)
    ob['source_id']='av_bo_boflaeche_a.20161';ob['source_egid']=302020548
    ob['construction_batch']='G1_020';ob['quality_status']='working_not_accepted'
    ob['collision_role']='solid_pending_runtime';ob['fabrication_inferred']=True
    return ob

def box(name,centre,size,mat,basis=None,bevel=0):
    centre=np.asarray(centre);basis=np.eye(3) if basis is None else np.asarray(basis)
    signs=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]])
    v=centre+(signs*np.asarray(size)/2)@basis.T
    ob=mesh(name,v.tolist(),[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
    if bevel:
        mod=ob.modifiers.new('Fabricated edge radius','BEVEL');mod.width=bevel;mod.segments=3
        ob.modifiers.new('Weighted face normals','WEIGHTED_NORMAL')
    return ob

def tube(name,a,b,radius,mat,segments=16):
    a,b=np.asarray(a),np.asarray(b);z=(b-a)/np.linalg.norm(b-a)
    x=np.cross(z,[0,0,1] if abs(z[2])<.95 else [1,0,0]);x/=np.linalg.norm(x);y=np.cross(z,x)
    v=[(c+radius*(x*np.cos(q*2*np.pi/segments)+y*np.sin(q*2*np.pi/segments))).tolist() for c in [a,b] for q in range(segments)]
    faces=[(i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments)]
    faces+=[tuple(range(segments-1,-1,-1)),tuple(range(segments,2*segments))]
    return mesh(name,v,faces,mat,True)

def prism(name,poly,z0,z1,mat):
    n=len(poly);v=[[*q,z] for z in [z0,z1] for q in poly]
    f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return mesh(name,v,f,mat)

class Edge:
    def __init__(self,i):
        self.i=i;self.a=ring[i];self.b=ring[(i+1)%8];self.length=np.linalg.norm(self.b-self.a)
        self.t=(self.b-self.a)/self.length;self.n=np.array([self.t[1],-self.t[0]])
        self.basis=np.array([[self.t[0],-self.n[0],0],[self.t[1],-self.n[1],0],[0,0,1]])
    def p(self,x,y,z):return np.r_[self.a+self.t*x-self.n*y,FLOOR+z]
    def box(self,name,c,size,mat,bevel=0):return box(name,self.p(*c),size,mat,self.basis,bevel)
    def tube(self,name,a,b,r,mat,segments=16):return tube(name,self.p(*a),self.p(*b),r,mat,segments)

edges=[Edge(i) for i in range(8)]

def countertop(e,name,z,mat,opening=False):
    # Mitred inner corners follow the eight-sided envelope rather than letting
    # rectangular countertops/cupboards interpenetrate at every corner.
    L=e.length;near,far=-.015,.665;inset=.055
    outer=np.array([[inset+near*.414214,near],[L-inset-near*.414214,near],[L-inset-far*.414214,far],[inset+far*.414214,far]])
    rings=[outer]
    if opening:rings.append(np.array([[L/2-.275,.17],[L/2+.275,.17],[L/2+.275,.53],[L/2-.275,.53]]))
    v=[e.p(x,y,z+zz).tolist() for zz in [.018,-.018] for r in rings for x,y in r]
    stride=4*len(rings);f=[]
    if opening:
        for i in range(4):
            j=(i+1)%4;f.extend([(i,j,4+j,4+i),(stride+i,stride+4+i,stride+4+j,stride+j),(4+i,4+j,stride+4+j,stride+4+i)])
    else:f.extend([(0,1,2,3),(stride+3,stride+2,stride+1,stride)])
    for i in range(4):j=(i+1)%4;f.append((i,stride+i,stride+j,j))
    ob=mesh(name,v,f,mat);bevel=ob.modifiers.new('Folded sheet edge','BEVEL');bevel.width=.002;bevel.segments=3
    ob.modifiers.new('Sheet normals','WEIGHTED_NORMAL')
    return ob
font_path=Path('C:/Windows/Fonts/timesi.ttf')
font=bpy.data.fonts.load(str(font_path)) if font_path.exists() else None

def label(name,text,edge,x,y,z,size,mat,max_width=None,italic=False):
    curve=bpy.data.curves.new('UR_'+name,'FONT');curve.body=text;curve.size=size
    curve.align_x='CENTER';curve.align_y='CENTER';curve.extrude=.00015
    if italic and font:curve.font=font
    ob=bpy.data.objects.new('UR_'+name,curve);collection.objects.link(ob);curve.materials.append(mat)
    axes=np.column_stack([np.r_[edge.t,0],[0,0,1],np.r_[edge.n,0]])
    ob.matrix_world=Matrix(axes.tolist()).to_4x4();ob.location=edge.p(x,y,z)
    bpy.context.view_layer.update()
    if max_width:
        width=max(v[0] for v in ob.bound_box)-min(v[0] for v in ob.bound_box)
        if width>max_width:ob.scale.x*=max_width/width
    data=bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    transform=ob.matrix_world.copy();bpy.data.objects.remove(ob,do_unlink=True)
    if curve.users==0:bpy.data.curves.remove(curve)
    out=bpy.data.objects.new('UR_'+name,data);collection.objects.link(out);out.matrix_world=transform
    out['source_id']='av_bo_boflaeche_a.20161';out['construction_batch']='G1_020';out['collision_role']='visual_only'
    out['basis']='Native vector outlines; sign text/photo-informed typography approximate; font file is not distributed.'
    return out

# Ground contact and flat floor follow the retained footprint; the sloping
# perimeter remains untouched. The staff entrance uses the higher south edge.
prism('FOUNDATION',ring,FLOOR-.31,FLOOR-.045,concrete)
floor_ob=prism('FLOOR',ring,FLOOR-.045,FLOOR,floor_mat)
roof_ob=prism('ROOF',ring,ROOF-.04,ROOF,roofmat)
prism('CEILING',CENTRE+(ring-CENTRE)*.986,FLOOR+2.51,FLOOR+2.55,inside)
roof_ob['source_id']='bauten_dachmodell_3d.101628';roof_ob['fabrication_inferred']=False
for i,q in enumerate(ring):
    delta=CENTRE-q;delta/=np.linalg.norm(delta)
    box(f'CORNER_POST_{i}',np.r_[q+delta*.046,FLOOR+(HEIGHT-.055)/2],(.082,.082,HEIGHT-.055),aluminium,edges[i].basis,.003)

def perimeter_frames(e):
    L=e.length
    e.box(f'E{e.i}_SILL',(L/2,.025,.955),(L-.08,.105,.043),aluminium,.002)
    e.box(f'E{e.i}_HEADER',(L/2,.025,2.185),(L-.08,.105,.055),aluminium,.002)
    for xx in [.075,L-.075]:e.box(f'E{e.i}_JAMB_{xx:.2f}',(xx,.025,1.57),(.048,.095,1.22),aluminium,.002)
    e.box(f'E{e.i}_UPPER_PANEL',(L/2,.034,(2.22+HEIGHT-.055)/2),(L-.085,.066,HEIGHT-.055-2.22),panel,.0018)
    e.box(f'E{e.i}_CAP_TRIM',(L/2,-.008,HEIGHT-.046),(L+.013,.085,.035),darksteel,.002)
    e.box(f'E{e.i}_BOTTOM_CHANNEL',(L/2,.017,.075),(L-.08,.08,.06),aluminium,.002)

def parent_at_frame(name,edge,x,y,z,parts,axis,open_angle,state):
    p=bpy.data.objects.new('UR_'+name,None);collection.objects.link(p)
    p.matrix_world=Matrix(edge.basis.tolist()).to_4x4();p.location=edge.p(x,y,z);bpy.context.view_layer.update()
    for ob in parts:
        ob.parent=p;ob.matrix_parent_inverse=p.matrix_world.inverted()
    p['interaction_role']='service_hatch' if axis=='X' else 'staff_door'
    p['hinge_axis']=axis;p['closed_angle_radians']=0.;p['open_angle_radians']=open_angle
    p['state']=state;p['runtime_enabled']=False;p['source_id']='av_bo_boflaeche_a.20161'
    if state=='open':p.rotation_euler.x=open_angle
    return p

hatches=[]
for e in edges:
    i,L=e.i,e.length;perimeter_frames(e)
    if i==plan['staff_door_edge_inferred']:
        door_width=.89;x0=(L-door_width)/2;x1=x0+door_width
        for a,bx in [(.054,x0-.033),(x1+.033,L-.054)]:
            e.box(f'STAFF_SIDE_{a:.2f}',((a+bx)/2,.035,1.11),(bx-a,.08,2.22),panel,.002)
        for x in [x0-.023,x1+.023]:e.box(f'STAFF_JAMB_{x:.2f}',(x,.016,1.075),(.04,.105,2.15),aluminium,.002)
        e.box('STAFF_FRAME_TOP',(L/2,.016,2.17),(door_width+.086,.105,.046),aluminium,.002)
        e.box('STAFF_TRANSOM_INFILL',(L/2,.035,2.21),(door_width+.075,.075,.042),panel,.001)
        e.box('STAFF_THRESHOLD',(L/2,-.014,.009),(door_width+.02,.17,.018),aluminium,.002)
        parts0=set(collection.objects)
        e.box('STAFF_DOOR_LEAF',(L/2,.020,1.077),(door_width-.02,.044,2.12),panel,.004)
        e.box('STAFF_DOOR_KICK',(L/2,-.005,.13),(door_width-.065,.014,.205),steel,.002)
        for z in [.26,1.05,1.89]:e.tube(f'STAFF_HINGE_{z}',(x0+.012,-.015,z-.04),(x0+.012,-.015,z+.04),.012,aluminium)
        e.box('STAFF_LOCK',(x1-.10,-.012,1.04),(.05,.019,.15),steel,.002)
        e.tube('STAFF_HANDLE_STEM',(x1-.10,-.023,1.065),(x1-.10,-.072,1.065),.01,steel)
        e.tube('STAFF_HANDLE_LEVER',(x1-.10,-.072,1.065),(x1-.25,-.072,1.065),.01,steel)
        parts=[o for o in collection.objects if o not in parts0]
        door=parent_at_frame('STAFF_DOOR_PIVOT',e,x0,0,0,parts,'Z',math.radians(-90),'closed')
        door['clear_width_m']=door_width-.06
        notice=label('STAFF_NOTICE','Personal',e,L/2,-.0023,1.66,.066,ink,max_width=.45)
        notice.parent=door;notice.matrix_parent_inverse=door.matrix_world.inverted()
        # Do not leave a window sill crossing the full-height door aperture.
        for suffix in ['SILL','HEADER']:
            ob=bpy.data.objects[f'UR_E{i}_{suffix}'];bpy.data.objects.remove(ob,do_unlink=True)
        continue
    e.box(f'E{i}_LOWER_PANEL',(L/2,.041,.517),(L-.09,.076,.84),panel,.003)
    e.box(f'E{i}_INSIDE_LINER',(L/2,.083,.525),(L-.115,.011,.82),inside,.001)
    if i in plan['service_edges_inferred']:
        parts0=set(collection.objects)
        centre_z=plan['hatch_top_z_relative']-plan['hatch_height_m']/2
        e.box(f'HATCH_{i}_SKIN',(L/2,-.012,centre_z),(L-.16,.025,plan['hatch_height_m']),panel,.002)
        for xx in [.085,L-.085]:e.box(f'HATCH_{i}_SIDE_{xx:.2f}',(xx,-.01,centre_z),(.027,.05,plan['hatch_height_m']),aluminium,.002)
        for zz in [plan['hatch_top_z_relative']-.018,plan['hatch_top_z_relative']-plan['hatch_height_m']+.018]:
            e.box(f'HATCH_{i}_RAIL_{zz:.2f}',(L/2,-.01,zz),(L-.16,.05,.035),aluminium,.002)
        e.box(f'HATCH_{i}_INNER_LINING',(L/2,.004,centre_z),(L-.22,.008,plan['hatch_height_m']-.065),inside,.001)
        h=parent_at_frame(f'HATCH_{i}_PIVOT',e,0,-.01,plan['hatch_top_z_relative'],[o for o in collection.objects if o not in parts0],'X',math.radians(plan['hatch_open_degrees']),'open');hatches.append(h)
        for xx in [.19,L-.19]:
            e.tube(f'HATCH_{i}_FIXED_HINGE_{xx:.2f}',(xx-.07,-.006,2.16),(xx+.07,-.006,2.16),.014,aluminium)
        countertop(e,f'COUNTER_{i}_WORKTOP',.922,steel)
        e.box(f'COUNTER_{i}_FRONT_LEDGE',(L/2,-.20,.903),(L-.12,.36,.03),steel,.003)
        e.box(f'COUNTER_{i}_LEDGE_LIP',(L/2,-.377,.895),(L-.12,.018,.047),aluminium,.002)
        for xx in [.26,L-.26]:
            e.box(f'COUNTER_{i}_SUPPORT_{xx:.2f}',(xx,-.125,.79),(.022,.32,.028),aluminium,.002)
            e.tube(f'COUNTER_{i}_BRACE_{xx:.2f}',(xx,.017,.65),(xx,-.28,.783),.010,aluminium)
        # Front sheet remains an actual panel behind the independent print.
        e.box(f'MENU_{i}_BOARD',(L/2,-.004,.66),(L-.24,.012,.38),menu,.002)
        label(f'MENU_{i}_TITLE','Imbiss Riviera',e,L/2,-.0103,.77,.072,ink,L-.32,True)
        for row,text in enumerate(['Bratwurst   Pommes frites','Panini   Hot-Dog   Getränke']):
            label(f'MENU_{i}_ROW_{row}',text,e,L/2,-.0103,.673-row*.067,.036,ink,L-.36)
        label(f'SIGN_{i}','Imbiss Riviera',e,L/2,.0007,2.437,.127,ink,L-.22,True)
    elif i in plan['closed_window_edges_inferred']:
        e.box(f'E{i}_WINDOW_GLASS',(L/2,.027,1.57),(L-.20,.006,1.16),glass,.0006)
        e.box(f'E{i}_WINDOW_MIDRAIL',(L/2,.009,1.57),(.039,.049,1.17),aluminium,.002)
    else:
        e.box(f'E{i}_OPAQUE_WALL',(L/2,.035,1.575),(L-.10,.078,1.195),panel,.002)
        e.box(f'E{i}_WALL_INNER',(L/2,.082,1.575),(L-.13,.012,1.16),inside,.001)
        # A utilitarian back with ventilation and seams, not a repeated shopfront.
        if i==7:
            e.box('UTILITY_VENT_RECESS',(L/2,-.009,.57),(.64,.015,.38),gasket,.003)
            for j in range(11):e.box(f'UTILITY_VENT_SLAT_{j}',(L/2,-.022,.411+j*.030),(.615,.041,.018),aluminium,.001)

# Panel fasteners, drip joint and toe wear use restrained physical detail.
for e in edges:
    if e.i==1:continue
    for xx in [.12,e.length-.12]:
        for zz in [.13,.89,2.25,HEIGHT-.09]:e.tube(f'FASTENER_{e.i}_{xx:.2f}_{zz:.2f}',(xx,-.003,zz),(xx,-.007,zz),.0035,steel,)
    e.box(f'E{e.i}_TOP_SEAM',(e.length/2,-.001,HEIGHT-.065),(e.length-.08,.009,.008),gasket,.001)

# Continuous, supported kitchen fittings; the middle remains a usable staff aisle.
for idx in [2,3,4,6,7]:
    e=edges[idx];L=e.length;cabinet_width=L-.69
    cabinet_top=.904 if idx in [2,3,4] else .842
    cabinet_bottom=.060;cabinet_height=cabinet_top-cabinet_bottom
    for xx in [L/2-cabinet_width/2+.011,L/2+cabinet_width/2-.011]:
        e.box(f'CABINET_{idx}_SIDE_{xx:.2f}',(xx,.36,(cabinet_top+cabinet_bottom)/2),(.022,.56,cabinet_height),darksteel,.002)
    e.box(f'CABINET_{idx}_BACK',(L/2,.091,(cabinet_top+cabinet_bottom)/2),(cabinet_width-.042,.022,cabinet_height),darksteel,.002)
    e.box(f'CABINET_{idx}_BOTTOM',(L/2,.36,.075),(cabinet_width-.042,.52,.03),darksteel,.002)
    e.box(f'CABINET_{idx}_PLINTH',(L/2,.39,.07),(cabinet_width-.04,.48,.14),gasket,.008)
    for j in range(2):
        xx=L/2-cabinet_width/2+cabinet_width*(j+.5)/2
        door_height=cabinet_top-.154
        e.box(f'CABINET_{idx}_DOOR_{j}',(xx,.646,.125+door_height/2),((cabinet_width-.035)/2,.021,door_height),steel,.006)
        e.tube(f'CABINET_{idx}_HANDLE_{j}',(xx-.11,.677,cabinet_top-.145),(xx+.11,.677,cabinet_top-.145),.009,aluminium)
    if idx in [6,7]:countertop(e,f'BACK_WORKTOP_{idx}',.86,steel,opening=idx==7)

# Refrigerator is freestanding at the rear; louvers and seals distinguish its
# construction from an unarticulated textured cuboid.
e=edges[0];cx=e.length/2
e.box('FRIDGE_BODY',(cx,.47,.99),(.69,.71,1.86),panel,.024)
e.box('FRIDGE_GASKET',(cx,.833,1.13),(.638,.027,1.47),gasket,.005)
e.box('FRIDGE_DOOR',(cx,.851,1.13),(.612,.044,1.448),steel,.015)
for x in [cx-.25,cx+.25]:
    for y in [.18,.75]:e.box(f'FRIDGE_FOOT_{x}_{y}',(x,y,.048),(.054,.054,.096),gasket,.008)
e.tube('FRIDGE_HANDLE',(cx+.24,.909,.93),(cx+.24,.909,1.43),.012,aluminium)
for j in range(7):e.box(f'FRIDGE_VENT_{j}',(cx,.85,.152+j*.026),(.58,.018,.010),gasket,.002)

# Grill and extractor: dimensional sheet construction, racks, controls, hood.
e=edges[6];L=e.length
e.box('GRILL_CHASSIS',(L/2,.37,1.0155),(.95,.49,.275),steel,.012)
e.box('GRILL_HOTPLATE',(L/2,.37,1.162),(.88,.45,.018),darksteel,.004)
for j in range(20):e.box(f'GRILL_RIB_{j}',(L/2-.42+j*.044,.37,1.1755),(.012,.422,.009),darksteel,.0015)
for xx in [L/2-.27,L/2+.27]:e.tube('GRILL_KNOB_'+str(xx),(xx,.62,1.005),(xx,.651,1.005),.021,gasket)
e.box('GRILL_GREASE_DRAWER',(L/2,.630,.94),(.80,.02,.049),steel,.002)
e.tube('GRILL_DRAWER_PULL',(L/2-.13,.666,.94),(L/2+.13,.666,.94),.007,aluminium)
hood_poly=[[-.55,.02,1.89],[.55,.02,1.89],[.55,.70,1.89],[-.55,.70,1.89],[-.39,.10,2.11],[.39,.10,2.11],[.39,.54,2.11],[-.39,.54,2.11]]
mesh('EXTRACTOR_HOOD',[e.p(x+L/2,y,z).tolist() for x,y,z in hood_poly],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],steel)
for j in range(12):e.box(f'HOOD_FILTER_{j}',(L/2-.48+j*.087,.34,1.883),(.039,.52,.012),darksteel,.001)
e.box('EXTRACT_DUCT',(L/2,.27,2.32),(.34,.32,.40),steel,.008)

# Wash bowl has an open rim and sloping bowl interior; not a solid rectangle.
e=edges[7];L=e.length;verts=[];faces=[]
profiles=[(.58,.39,.882),(.55,.36,.879),(.42,.25,.70),(.035,.035,.695)]
for w,d,z in profiles:
    for xx,yy in [(-1,-1),(1,-1),(1,1),(-1,1)]:verts.append(e.p(L/2+xx*w/2,.35+yy*d/2,z).tolist())
for j in range(3):
    for k in range(4):faces.append((j*4+k,j*4+(k+1)%4,(j+1)*4+(k+1)%4,(j+1)*4+k))
faces.append((12,13,14,15));mesh('WASH_BOWL',verts,faces,steel)
# The worktop was built with the matching through-hole and an overlapping rim.
e.tube('TAP_FOOT',(L/2+.20,.15,.875),(L/2+.20,.15,.901),.022,steel,24)
tap=[e.p(L/2+.20,.15,z) for z in [.888,1.00,1.14]]
tap+=[e.p(L/2+.20,.15+t*.17,1.14+.055*math.sin(t*math.pi)) for t in np.linspace(.1,1,9)]
tap+=[e.p(L/2+.20,.32,1.095)]
for j in range(len(tap)-1):tube(f'TAP_CURVE_{j}',tap[j],tap[j+1],.010,steel,20)
e.tube('TAP_HANDLE',(L/2+.20,.15,.974),(L/2+.28,.15,1.025),.007,steel)
bpy.data.objects['UR_WASH_BOWL']['facility_role']='staff_wash_sink_pending_runtime'

# Modest original shelf/counter contents are everyday construction detail, not
# task objects. Food photography, human figures and invented prices are absent.
e=edges[5];L=e.length
for zz in [1.20,1.57]:
    e.box(f'SHELF_{zz}',(L/2,.165,zz),(L-.22,.24,.027),wood,.002)
    e.box(f'SHELF_BACK_RAIL_{zz}',(L/2,.074,zz-.0235),(L-.08,.072,.022),aluminium,.002)
    for xx in [.24,L-.24]:e.box(f'SHELF_BRACKET_{zz}_{xx:.2f}',(xx,.16,zz-.0245),(.021,.205,.022),steel,.002)
for j in range(7):
    x=.22+j*.218;z0=1.5835
    e.tube(f'BOTTLE_{j}_BODY',(x,.18,z0),(x,.18,z0+.154),.032,amber,20)
    e.tube(f'BOTTLE_{j}_SHOULDER',(x,.18,z0+.15),(x,.18,z0+.183),.026,amber,20)
    e.tube(f'BOTTLE_{j}_NECK',(x,.18,z0+.18),(x,.18,z0+.246),.011,amber,16)
    e.tube(f'BOTTLE_{j}_CAP',(x,.18,z0+.246),(x,.18,z0+.258),.013,darksteel,16)
e=edges[3];L=e.length
e.box('POS_BASE',(L*.72,.43,.968),(.21,.18,.036),darksteel,.009)
e.box('POS_STAND',(L*.72,.49,1.059),(.045,.045,.16),aluminium,.006)
e.box('POS_SCREEN',(L*.72,.47,1.157),(.236,.035,.167),darksteel,.006)
e.box('POS_DISPLAY',(L*.72,.450,1.157),(.203,.003,.137),ink,.002)
e=edges[2]
e.box('NAPKIN_HOLDER',(e.length*.26,.27,1.02),(.17,.13,.135),steel,.008)
e.box('NAPKIN_STACK',(e.length*.26,.262,1.092),(.147,.095,.035),menu,.004)
for j in range(3):
    profiles=[(.032,.94),(.037,.947),(.039,1.028),(.036,1.030),(.033,.948)];vv=[];ff=[];segments=32
    for radius,zz in profiles:
        for k in range(segments):
            angle=k*math.tau/segments;vv.append(e.p(.93+j*.12+radius*math.cos(angle),.28+radius*math.sin(angle),zz).tolist())
    for p in range(len(profiles)-1):
        for k in range(segments):ff.append((p*segments+k,p*segments+(k+1)%segments,(p+1)*segments+(k+1)%segments,(p+1)*segments+k))
    ff.extend([tuple(range(segments-1,-1,-1)),tuple(range(4*segments,5*segments))]);mesh(f'CUP_{j}',vv,ff,porcelain,True)

# Flush ceiling light retains a visible fitting and a restrained interior source.
for y in [-.48,.48]:
    box(f'LIGHT_BODY_{y}',np.r_[CENTRE+[0,y],FLOOR+2.484],(1.07,.095,.049),aluminium,bevel=.006)
    box(f'LIGHT_DIFFUSER_{y}',np.r_[CENTRE+[0,y],FLOOR+2.457],(.96,.065,.013),lightmat,bevel=.004)
ld=bpy.data.lights.new('UR_INTERIOR_LIGHT','AREA');ld.energy=38;ld.color=(1,.94,.82);ld.size=1.6
lo=bpy.data.objects.new('UR_INTERIOR_LIGHT',ld);collection.objects.link(lo);lo.location=(*CENTRE,FLOOR+2.42)
lo['basis']='Low interior worklight inferred; no scene exposure change.'

# Sole construction changes outside this collection are bounded photo working
# meshes. Exact original I3S meshes and the adjacent wall remain available.
bpy.context.view_layer.update()
cutpath=ROOT/'derived/bellevue/west_context/utoquai_kiosk_photo_cut.json'
cut=json.loads(cutpath.read_text());old=json.loads((ROOT/scene['photo_cut_file']).read_text())
previous={str(r['node']):r for r in old['overrides']}
working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
originals={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
changed=[]
for rec in cut['overrides']:
    key=str(rec['node'])
    if previous.get(key)==rec:continue
    ob,src=working[key],originals[key]
    assert ob.matrix_basis==src.matrix_basis
    v=np.asarray(rec['vertices']).reshape(-1,3);uv=np.asarray(rec['uv_source_v_unflipped']).reshape(-1,2);uv[:,1]=1-uv[:,1]
    me=bpy.data.meshes.new('UR_CONTEXT_'+key);me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
    for m in src.data.materials:me.materials.append(m)
    layer=me.uv_layers.new(name='source_photo_uv');layer.data.foreach_set('uv',uv.astype(np.float32).ravel())
    oldmesh=ob.data;ob.data=me
    if oldmesh.users==0:bpy.data.meshes.remove(oldmesh)
    ob['construction_mask']=cut['mask_basis'];changed.append(key)

cameras=[('UR_QA_COUNTER',[2683506.8,1246868.1],[2683503.8,1246868.1,409.97],30),('UR_QA_NORTH',[2683504.8,1246873.2],[2683502.3,1246868.3,409.95],27),('UR_QA_STAFF',[2683502.1,1246863.8],[2683502.15,1246867.6,409.92],28)]
for name,xy,target,lens in cameras:
    local=np.array(xy)-ORIGIN[:2];ground=[]
    for key in ['LM_ASPHALT','LM_CURB_TOP','LM_SOIL']:
        hit,p,_,_=bpy.data.objects[key].ray_cast(Vector((*local,30)),Vector((0,0,-1)))
        if hit:ground.append(p.z)
    assert ground,('Camera lacks rebuilt public ground',name)
    data=bpy.data.cameras.new(name);ob=bpy.data.objects.new(name,data);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(ob)
    ob.location=(*local,max(ground)+1.65);ob.rotation_euler=(Vector(np.array(target)-ORIGIN)-ob.location).to_track_quat('-Z','Y').to_euler();data.lens=lens;ob['eye_height_m']=1.65

if font and font.users==0:bpy.data.fonts.remove(font)
scene['version']='G1_020';scene['photo_cut_file']=str(cutpath.relative_to(ROOT));scene.camera=bpy.data.objects['UR_QA_NORTH']
bpy.context.view_layer.update()
collection['construction_complete']=True
record={'version':'G1_020','base':'G1_019r3','object_count':len(collection.objects),'material_count':len(materials),'source_egid':302020548,'floor_local_inferred':FLOOR,'roof_local':ROOF,'footprint_area_m2':plan['source']['area_m2'],'service_hatches':[h.name for h in hatches],'staff_door':door.name,'changed_photo_nodes':changed,'photo_originals_retained':len(originals),'evidence_basis':plan['basis'],'visual_acceptance':False,'runtime_enabled':False,'native_saved':False}
(EVIDENCE/'construction.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record))
