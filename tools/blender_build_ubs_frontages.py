"""Measured Theaterstrasse20 envelope, photo-guided street fronts and ground join.

G1_027r8 -> r9. Preserve the source scan, existing cafe, and all old cameras.
Only a shallow visual interior is inferred; this does not open a public bank.
"""
from pathlib import Path
import ast,hashlib,json,math,shutil,sys
import bpy,bmesh,numpy as np
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import ROOT,read_path,write_path
from blender_geometry_fingerprint import object_state,mesh_digest
from blender_photo_clip import cut_object,split

s=bpy.context.scene;assert s['version']=='G1_027r8'
version='G1_027r9';target=write_path('native/G1_027r9_ubs_frontages_working.blend')
assert not target.exists() and shutil.disk_usage(ROOT).free>3_000_000_000
assert '46_UBS_THEATERSTRASSE20' not in bpy.data.collections
cp=json.loads(read_path('evidence/G1_027r8/checkpoint.json').read_text())
with Path(bpy.data.filepath).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==cp['native_sha256']
specpath=read_path('derived/ubs_theaterstrasse20/build_input.json');d=json.loads(specpath.read_text())
for row in d['input_files']:assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
probe=json.loads(read_path('derived/ubs_theaterstrasse20/r8_geometry_probe.json').read_text())
before={o.name:object_state(o) for o in s.objects}
original={o.name:o.data.as_pointer() for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
cafe={o.name:mesh_digest(o.data) for o in bpy.data.collections['45_STERNEN_GRILL_FRONTAGES'].objects if o.type=='MESH'}
for row in probe['photo_objects']:
    o=bpy.data.objects[row['name']]
    xyz=np.empty(len(o.data.vertices)*3,dtype=np.float32);o.data.vertices.foreach_get('co',xyz)
    indices=np.empty(len(o.data.loops),dtype=np.int32);o.data.loops.foreach_get('vertex_index',indices)
    uv=np.empty(len(o.data.loops)*2,dtype=np.float32);o.data.uv_layers.active.data.foreach_get('uv',uv)
    assert hashlib.sha256(xyz.tobytes()+indices.tobytes()+uv.tobytes()).hexdigest()==row['vertex_loop_uv_sha256'],o.name
    matrix=np.array(o.matrix_world);assert matrix.tolist()==row['matrix_world']
    assert np.array_equal(xyz.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3],row['vertices_world']),o.name
    assert [list(f.vertices) for f in o.data.polygons]==row['triangles']

C=bpy.data.collections.new('46_UBS_THEATERSTRASSE20');bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(C)
C['source_id']='AV23105 / EGID2372625 / Theaterstrasse20';C['public_interior_selected']=False
C['evidence_basis']='Official envelope, MML front reference; unsurveyed joinery and side openings are inference.'
A,U,N=(np.array(d[k]) for k in ['A','U','N']);SU,SN=(np.array(d[k]) for k in ['side_U','side_N'])
W=d['street_width_m'];D=d['side_length_m'];floor=d['floor_z']
def P(u,v,z):return np.r_[A+U*u+N*v,z]
def S(u,v,z):return np.r_[A+SU*u+SN*v,z]
def Q(p):return np.r_[(p[:2]-A)@U,(p[:2]-A)@N,p[2]]
def QS(p):return np.r_[(p[:2]-A)@SU,(p[:2]-A)@SN,p[2]]
groups={};helper=read_path('tools/blender_build_sternen_grill.py')
helpers=[n for n in ast.parse(helper.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in {'add','box','tube'}]
assert len(helpers)==3
exec(compile(ast.Module(body=helpers,type_ignores=[]),'ubs_geometry_helpers','exec'))

def material(name,color,rough=.6,metal=0):
    m=bpy.data.materials.new('UF | '+name);m.use_nodes=True
    b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
    m['evidence_basis']='Photo-guided material family; optical parameters are inferred.'
    return m
stones=[]
for i in range(6):
    m=material('warm mottled limestone '+str(i),(.60,.566,.476),.68)
    ns=m.node_tree.nodes;ls=m.node_tree.links;b=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
    coord=ns.new('ShaderNodeTexCoord');noise=ns.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=4.8
    noise.inputs['Detail'].default_value=5;noise.inputs['Roughness'].default_value=.74
    ls.new(coord.outputs['Object'],noise.inputs['Vector']);ramp=ns.new('ShaderNodeValToRGB')
    ramp.color_ramp.interpolation='EASE'
    ramp.color_ramp.elements[0].position=.25;ramp.color_ramp.elements[0].color=(*[x*(.975+i*.009) for x in [.39,.345,.25]],1)
    ramp.color_ramp.elements[1].position=.61;ramp.color_ramp.elements[1].color=(*[x*(.975+i*.009) for x in [.67,.632,.54]],1)
    ls.new(noise.outputs['Fac'],ramp.inputs[0]);ls.new(ramp.outputs['Color'],b.inputs['Base Color'])
    fine=ns.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=180;fine.inputs['Detail'].default_value=2
    ls.new(coord.outputs['Object'],fine.inputs['Vector']);bump=ns.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.00022;bump.inputs['Strength'].default_value=.25
    ls.new(fine.outputs['Fac'],bump.inputs['Height']);ls.new(bump.outputs['Normal'],b.inputs['Normal']);stones.append(m)
joint=material('recessed stone joints',(.18,.167,.137),.87)
metal=material('anthracite anodised frames',(.061,.067,.066),.31,.72)
seal=material('glazing gaskets',(.008,.01,.009),.80)
zinc=material('weathered zinc roof',(.24,.258,.26),.49,.72)
steel=material('brushed stainless fittings',(.43,.46,.45),.34,.87)
glass=material('clear office glazing',(.88,.94,.97),.045)
b=next(n for n in glass.node_tree.nodes if n.type=='BSDF_PRINCIPLED');b.inputs['Transmission Weight'].default_value=1;b.inputs['IOR'].default_value=1.46
plaster=material('shallow room plaster',(.44,.427,.387),.85)
floor_mat=material('fine grey threshold stone',(.285,.28,.26),.78)
blind=material('ivory roller blinds',(.64,.619,.54),.91)
red=material('red UBS letters',(.52,.006,.01),.37,.12)
orange=material('orange Coop letters',(.83,.22,.012),.39,.10)
warm=material('interior light diffuser',(.68,.61,.47),.4)
b=next(n for n in warm.node_tree.nodes if n.type=='BSDF_PRINCIPLED');b.inputs['Emission Color'].default_value=(1,.80,.57,1);b.inputs['Emission Strength'].default_value=2.8

def wall(name,a,b,z0,z1,frame=P,depth=-.23):
    if b-a<.01 or z1-z0<.01:return
    box(name+'_JOINT',((a+b)/2,depth-.018,(z0+z1)/2),(b-a,.424,z1-z0),joint,.001,frame)
    nx=max(1,math.ceil((b-a)/1.12));nz=max(1,math.ceil((z1-z0)/.9))
    for ix in range(nx):
        x0=a+(b-a)*ix/nx;x1=a+(b-a)*(ix+1)/nx
        for iz in range(nz):
            za=z0+(z1-z0)*iz/nz;zb=z0+(z1-z0)*(iz+1)/nz
            box(name+'_STONE',((x0+x1)/2,depth,(za+zb)/2),(x1-x0-.003,.46,zb-za-.003),stones[(ix+2*iz+round(a*7))%6],.0013,frame)

openings=[]
def window(name,a,b,z0,z1,panes,frame=P,depth=-.27,index=0,room_depth=1.53,blinds=True):
    width=b-a;height=z1-z0;mid=(z0+z1)/2;center=(a+b)/2
    for x in [a,b]:box(name+'_REVEAL',(x,depth/2,mid),(.060,abs(depth)+.06,height+.04),stones[index%6],.002,frame)
    for z in [z0,z1]:box(name+'_STONE_LEDGE',(center,depth/2,z),(width+.09,abs(depth)+.13,.07),stones[(index+1)%6],.003,frame)
    for j in range(panes+1):box(name+'_FRAME',(a+j*width/panes,depth,mid),(.054 if j in [0,panes] else .043,.095,height),metal,.002,frame)
    transom=z0+.32 if height>1.5 else z0+.20
    for z in [z0,z1,transom]:box(name+'_FRAME',(center,depth,z),(width,.095,.051),metal,.002,frame)
    for j in range(panes):
        x0=a+j*width/panes+.024;x1=a+(j+1)*width/panes-.024
        for za,zb in [(z0+.026,transom-.025),(transom+.025,z1-.026)]:
            box(name+'_GLASS',((x0+x1)/2,depth-.012,(za+zb)/2),(x1-x0,.014,zb-za),glass,0,frame)
            for x in [x0,x1]:box(name+'_GASKET',(x,depth+.01,(za+zb)/2),(.009,.023,zb-za),seal,.0007,frame)
    box(name+'_ROOM_BACK',(center,-room_depth,mid),(width,.06,height+.14),plaster,.002,frame)
    for x in [a,b]:box(name+'_ROOM_RETURN',(x,(-room_depth+depth)/2,mid),(.055,room_depth+depth,height+.10),plaster,.001,frame)
    for z in [z0-.06,z1+.06]:box(name+'_ROOM_RETURN',(center,(-room_depth+depth)/2,z),(width,room_depth+depth,.06),plaster,.001,frame)
    if blinds:
        for j in range(panes):
            coverage=[.12,.22,.42,.08,.57][(j+index*2)%5]
            if (index+j)%7==0:coverage=.88
            box(name+'_BLIND',(a+(j+.5)*width/panes,depth-.13,z1-height*coverage/2),(width/panes-.068,.018,height*coverage),blind,.001,frame)
    box(name+'_BLIND_CASSETTE',(center,depth-.10,z1-.029),(width,.16,.075),metal,.003,frame)
    openings.append(dict(name=name,frame='front' if frame is P else 'side',a=a,b=b,z0=z0,z1=z1,depth=depth,panes=panes))

# True openings between stone piers and spandrels, retaining the real floor rhythm.
for li,L in enumerate(d['levels']):
    cursor=0.;bays=d['main_bays']+[dict(a=d['bow_bay']['a'],b=d['bow_bay']['b'],panes=6)]
    for wi,bay in enumerate(bays):
        a,b=bay['a'],bay['b'];name=f'UF_FRONT_L{li+1}_W{wi+1}'
        wall(name+'_PIER',cursor,a,L['bottom'],L['top'])
        if wi<3:
            wall(name+'_SILL_PANEL',a,b,L['bottom'],L['sill']);wall(name+'_HEAD_PANEL',a,b,L['head'],L['top'])
            window(name,a,b,L['sill'],L['head'],bay['panes'],index=li*4+wi)
        cursor=b
    wall(f'UF_FRONT_L{li+1}_END',cursor,W,L['bottom'],L['top'])
    box(f'UF_FRONT_L{li+1}_HORIZONTAL_FLASHING',(W/2,.015,L['bottom']),(W,.055,.026),metal,.001)

# Bow window is a shallow convex six-facet volume with continuous vertical ribs.
ba,bb=d['bow_bay']['a'],d['bow_bay']['b'];bx=np.linspace(ba,bb,7);by=.06+.44*np.sin(np.linspace(0,math.pi,7))
bow_levels=d['levels']+[dict(bottom=25.22,top=28.06,sill=25.42,head=27.78)]
for li,L in enumerate(bow_levels):
    for j in range(6):
        def facet(u,v,z,j=j):
            t=u/(bx[j+1]-bx[j]);return P(bx[j]+u,by[j]*(1-t)+by[j+1]*t+v,z)
        width=bx[j+1]-bx[j]
        # Thin opaque infill between floors, glazed upper/lower panes as pictured.
        for za,zb in [(L['bottom'],L['sill']),(L['head'],L['top'])]:
            box(f'UF_BOW_L{li+1}_SPANDREL',(width/2,-.035,(za+zb)/2),(width,.072,zb-za),metal,.002,facet)
        for z in [L['bottom'],L['sill'],L['head'],L['top']]:box(f'UF_BOW_L{li+1}_RAIL',(width/2,.008,z),(width,.080,.055),metal,.002,facet)
        box(f'UF_BOW_L{li+1}_GLASS',(width/2,-.011,(L['sill']+L['head'])/2),(width-.046,.014,L['head']-L['sill']-.065),glass,0,facet)
        if li in [0,1,2]:box(f'UF_BOW_L{li+1}_BLIND',(width/2,-.15,(L['sill']+L['head'])/2),(width-.071,.018,L['head']-L['sill']-.12),blind,.001,facet)
    if li==0:
        for x,y in zip(bx,by):box('UF_BOW_VERTICAL_RIB',(x,y+.015,(11.82+28.08)/2),(.055,.13,28.08-11.82),metal,.003)
    box(f'UF_BOW_L{li+1}_ROOM_BACK',((ba+bb)/2,-1.35,(L['bottom']+L['top'])/2),(bb-ba,.07,L['top']-L['bottom']),plaster,.001)

# The actual angled Sternen side is not snapped to an orthogonal generic box.
side_bays=[(1.25,4.10),(5.05,8.25),(9.20,12.40),(13.4,16.55)]
for li,L in enumerate(d['levels']):
    cursor=0.
    for wi,(a,b) in enumerate(side_bays):
        name=f'UF_LANE_L{li+1}_W{wi+1}';wall(name+'_PIER',cursor,a,L['bottom'],L['top'],S)
        wall(name+'_LOW',a,b,L['bottom'],L['sill'],S);wall(name+'_HIGH',a,b,L['head'],L['top'],S)
        window(name,a,b,L['sill'],L['head'],4,S,index=li*5+wi+2);cursor=b
    wall(f'UF_LANE_L{li+1}_END',cursor,D,L['bottom'],L['top'],S)

# Four ground bays: articulated shopfronts and closed glazed doors.
ground_bays=[(1.42,5.01),(5.96,10.81),(11.70,15.43),(16.55,20.70)]
for tag,length,frame,bays in [('FRONT',W,P,ground_bays),('LANE',D,S,side_bays)]:
    cursor=0.
    for j,(a,b) in enumerate(bays):
        name=f'UF_{tag}_GROUND{j+1}';center=(a+b)/2;width=b-a
        wall(name+'_PIER',cursor,a,8.43,11.82,frame);wall(name+'_FASCIA',a,b,11.26,11.82,frame)
        # Enclosure is shallow and closed; not a fabricated traversable bank plan.
        window(name,a+.03,b-.03,floor+.08,11.24,4 if width>4 else 3,frame,depth=-.43,index=j,room_depth=1.65,blinds=False)
        if tag=='FRONT':
            box(name+'_THRESHOLD',(center,-.32,floor-.042),(width,.99,.084),floor_mat,.002,frame)
            if j in [1,3]:
                for x in [center-.09,center+.09]:
                    tube(name+'_DOOR_PULL',[frame(x,-.335,floor+.94),frame(x,-.335,floor+1.39)],.013,steel,12)
                    for z in [floor+1.00,floor+1.33]:tube(name+'_HANDLE_STANDOFF',[frame(x,-.43,z),frame(x,-.335,z)],.009,steel,10)
            # Pitched glass rain canopies with visible steel bracket construction.
            for x in [a+.12,b-.12]:
                tube(name+'_CANOPY_BRACKET',[frame(x,-.04,11.26),frame(x,1.13,11.51)],.027,metal,12)
                tube(name+'_CANOPY_TIE',[frame(x,-.02,11.65),frame(x,.92,11.47)],.009,steel,10)
            for v,z in [(.02,11.29),(1.13,11.52)]:tube(name+'_CANOPY_RAIL',[frame(a-.06,v,z),frame(b+.06,v,z)],.028,metal,12)
            for k in range(max(2,round(width/.8))):
                c0=a+(b-a)*k/max(2,round(width/.8));c1=a+(b-a)*(k+1)/max(2,round(width/.8))
                add(name+'_CANOPY_GLASS',[frame(c0+.018,.04,11.31),frame(c1-.018,.04,11.31),frame(c1-.018,1.10,11.53),frame(c0+.018,1.10,11.53)],[(0,1,2,3)],glass)
            # A few built-in visual cues follow the documented bank reception.
            if j==1:
                box(name+'_RECEPTION',(center,-1.28,floor+.52),(1.45,.44,1.02),plaster,.009,frame)
                box(name+'_RECEPTION_TOP',(center,-1.28,floor+1.05),(1.52,.50,.045),stones[4],.004,frame)
            box(name+'_CEILING_LIGHT',(center,-1.01,11.17),(.70,.36,.025),warm,.001,frame)
        cursor=b
    wall(f'UF_{tag}_GROUND_END',cursor,length,8.43,11.82,frame)
    # Base courses follow a practical lower datum while the pavement grades.
    box(f'UF_{tag}_STONE_PLINTH',(length/2,-.14,8.54),(length,.32,.18),floor_mat,.003,frame)

# Recessed attic terraces, thick soffit, piers and guardrails; no flat glass strip.
for tag,length,frame in [('FRONT',16.52,P),('LANE',D,S)]:
    box('UF_'+tag+'_ATTIC_FLOOR',(length/2,-.46,25.24),(length,1.48,.15),floor_mat,.004,frame)
    box('UF_'+tag+'_EAVE_SOFFIT',(length/2,.06,28.01),(length+.12,2.43,.18),zinc,.005,frame)
    for x in np.linspace(.12,length-.12,5):box('UF_'+tag+'_ATTIC_PIER',(x,-.08,26.67),(.26,.52,2.70),zinc,.004,frame)
    for j in range(6):
        a=length*j/6+.06;b=length*(j+1)/6-.06
        window(f'UF_{tag}_ATTIC_W{j+1}',a,b,25.42,27.70,3,frame,depth=-1.10,index=j+2,room_depth=1.71)
    for z in [25.55,26.14,26.25]:tube('UF_'+tag+'_ATTIC_RAIL',[frame(.05,.12,z),frame(length-.05,.12,z)],.018,steel,12)
    for x in np.arange(.1,length,.98):tube('UF_'+tag+'_ATTIC_POST',[frame(x,.12,25.28),frame(x,.12,26.26)],.019,metal,10)

# Exact official triangles above the source eave. Do not invent a flattened roof.
roof_faces=0
for row in d['envelope_triangles']:
    if row['surface_type']=='GroundSurface':continue
    poly,_=split([np.r_[p,p] for p in row['vertices']],2,27.95,True)
    if len(poly)<3:continue
    for j in range(1,len(poly)-1):
        points=[poly[0][:3],poly[j][:3],poly[j+1][:3]]
        if np.linalg.norm(np.cross(points[1]-points[0],points[2]-points[0]))<1e-8:continue
        add('UF_OFFICIAL_ENVELOPE_'+row['source'].split('.')[-1],points,[(0,1,2)],zinc)
        roof_faces+=1
for z in np.arange(28.42,31.26,.19):
    t=(z-28.108)/(31.373-28.108);v=-2.140*t+.045;a=2.195*t
    box('UF_FRONT_ROOF_LOUVERS',((a+W)/2,v,z),(W-a,.21,.047),metal,.002)

asphalt=bpy.data.objects['SG_R7_CONTINUOUS_STREET_APPROACH'].data.materials[0]
add('UF_CONTINUOUS_STREET_APPROACH',d['pavement']['vertices'],d['pavement']['faces'],asphalt)
assert {'BEVEL','WEIGHTED_NORMAL'}.issubset({i.identifier for i in bpy.types.Modifier.bl_rna.properties['type'].enum_items})
created=[]
for (name,_),g in groups.items():
    me=bpy.data.meshes.new(name);me.from_pydata(g['v'],[],g['f']);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
    assert not me.validate(clean_customdata=False),name
    ob=bpy.data.objects.new(name,me);C.objects.link(ob);me.materials.append(g['mat'])
    for face in me.polygons:face.use_smooth=g['smooth']
    uv=me.uv_layers.new(name='metre_scale')
    for face in me.polygons:
        axes=[i for i in range(3) if i!=int(np.argmax(abs(np.array(face.normal))))]
        for li in face.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]],p[axes[1]])
    if g['bevel']:
        mod=ob.modifiers.new('material edge','BEVEL');mod.width=g['bevel'];mod.segments=2
        ob.modifiers.new('architectural normals','WEIGHTED_NORMAL')
    ob['construction_batch']=version;ob['source_id']='AV23105 / EGID2372625'
    ob['evidence_basis']=d['detail_basis'];ob['collision_role']='solid_pending_runtime'
    ob['public_interior_selected']=False;created.append(ob.name)

def lettering(name,text,u,v,z,size,mat,fontpath):
    curve=bpy.data.curves.new(name,'FONT');curve.body=text;curve.size=size;curve.extrude=.007;curve.align_x='CENTER'
    curve.font=bpy.data.fonts.load(fontpath,check_existing=True);curve.materials.append(mat)
    ob=bpy.data.objects.new(name,curve);C.objects.link(ob);ob.location=P(u,v,z)
    ob.rotation_euler=Matrix((Vector((*U,0)),Vector((0,0,1)),Vector((*N,0)))).transposed().to_euler();bpy.context.view_layer.update()
    mesh=bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()));matrix=ob.matrix_world.copy()
    bpy.data.objects.remove(ob,do_unlink=True);ob=bpy.data.objects.new(name,mesh);C.objects.link(ob);ob.matrix_world=matrix
    ob['evidence_basis']='MML photographic site lettering, inferred dimensions';ob['collision_role']='visual_nonblocking';created.append(ob.name)
lettering('UF_ROOF_UBS','UBS',6.4,-.83,29.55,1.42,red,'C:/Windows/Fonts/timesbd.ttf')
lettering('UF_ROOF_COOP','coop city',17.0,-.86,29.62,.98,orange,'C:/Windows/Fonts/arialbd.ttf')
lettering('UF_BANK_ENTRANCE_SIGN','UBS',8.38,-.012,11.35,.25,red,'C:/Windows/Fonts/timesbd.ttf')
lettering('UF_STORE_ENTRANCE_SIGN','coop city',18.60,-.012,11.35,.29,orange,'C:/Windows/Fonts/arialbd.ttf')

# Replace only rebuilt volumes. Higher street shelters remain until identified.
cuts=[]
for row in probe['photo_objects']:
    ob=bpy.data.objects[row['name']]
    for label,frame,boxes in [('front',Q,d['front_cut_boxes']),('side',QS,d['side_cut_boxes']),('roof',Q,d['roof_cut_boxes'])]:
        result=cut_object(ob,frame,boxes)
        if result:result['pass']=label;cuts.append(result)
    verts=np.array([ob.matrix_world@v.co for v in ob.data.vertices]);indices=np.array([list(f.vertices) for f in ob.data.polygons])
    if len(indices):
        t=verts[indices];cross=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);norm=np.linalg.norm(cross,axis=1)
        eligible=np.flatnonzero((norm>1e-8)&(cross[:,2]>norm*.96)&(t[:,:,2].min(1)>8.18)&(t[:,:,2].max(1)<8.91))
        result=cut_object(ob,Q,d['ground_cut_boxes'],eligible_faces=eligible)
        if result:result['pass']='ground_only';cuts.append(result)
assert original=={o.name:o.data.as_pointer() for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
assert all(mesh_digest(bpy.data.objects[name].data)==digest for name,digest in cafe.items())
changed={r['object'] for r in cuts}
assert not [name for name,state in before.items() if object_state(bpy.data.objects[name])!=state]
bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
cameras=[]
for name,eye,look,lens in [('UF_QA_FRONT',P(10.5,24,10),P(10.5,-.2,17.8),27),('UF_QA_ENTRY',P(8.3,3.8,10),P(8.35,-.35,10.15),29),('UF_QA_LANE',S(4.5,2.3,10),S(10.2,-.12,16.7),24)]:
    hit,p,n,fi,ob,m=s.ray_cast(deps,Vector((eye[0],eye[1],9.5)),Vector((0,0,-1)),distance=3)
    assert hit and n.z>.5,(name,ob.name if hit else None)
    eye[2]=p.z+1.7;cam=bpy.data.cameras.new(name);obj=bpy.data.objects.new(name,cam);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(obj)
    obj.location=eye;obj.rotation_euler=(Vector(look)-obj.location).to_track_quat('-Z','Y').to_euler();cam.lens=lens;cam.clip_end=1600
    cameras.append(dict(name=name,eye=eye.tolist(),look=look.tolist(),lens=lens,floor=ob.name,eye_height_m=1.7))

for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and not im.library:im.filepath=bpy.path.abspath(im.filepath)
for lib in bpy.data.libraries:lib.filepath=bpy.path.abspath(lib.filepath)
missing=[bpy.path.abspath(im.filepath,library=im.library) for im in bpy.data.images if im.source=='FILE' and im.filepath and not im.packed_file and not Path(bpy.path.abspath(im.filepath,library=im.library)).is_file()]
assert not missing,missing[:5]
s['version']=version;s['latest_construction']='Theaterstrasse20 bank/store front, side and measured roof with continuous corner pavement';s.camera=bpy.data.objects['UF_QA_FRONT']
report=dict(version=version,base_native=cp['native'],base_native_sha256=cp['native_sha256'],spec_sha256=hashlib.sha256(specpath.read_bytes()).hexdigest(),
    created_objects=created,photo_cuts=cuts,final_photo_counts={r['name']:len(bpy.data.objects[r['name']].data.polygons) for r in probe['photo_objects']},
    original_source_meshes_unchanged=len(original),existing_cafe_meshes_unchanged=len(cafe),unrelated_object_states_unchanged=len(before),cameras=cameras,openings=openings,
    official_upper_envelope_triangles=roof_faces,missing_images=missing,ground_anchors=d['pavement']['outer_anchors'],cafe_edge_anchors=d['pavement']['cafe_edge_anchors'],limits=d['limits'])
write_path(f'evidence/{version}/ubs_build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
previous=json.loads(read_path('evidence/G1_027r8/build_report.json').read_text());previous.update(version=version,preserved_sternen_report_version='G1_027r8',subsequent_photo_counts=report['final_photo_counts'])
write_path(f'evidence/{version}/build_report.json').write_text(json.dumps(previous,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(target),check_existing=False,compress=True)
with target.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
receipt={k:cp[k] for k in ['storage_sharing_applied','required_immutable_libraries','shared_meshes','shared_objects']}
receipt.update(version=version,native=str(target),native_sha256=digest,native_bytes=target.stat().st_size,objects=len(s.objects),native_fresh_reopen_verified=False,visual_acceptance=False,runtime_exported=False,natural_use_verified=False)
write_path(f'evidence/{version}/checkpoint.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('UBS_FRONTAGES_SAVED',json.dumps({k:receipt[k] for k in ['version','native','native_bytes','native_sha256','objects']}),flush=True)
