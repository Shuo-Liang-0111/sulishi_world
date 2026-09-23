"""Editable, photo-informed fountain59. Execute through the live Blender MCP.

XY and approximate envelope are recorded facts. Cross section, three sculpted
backs, casting details and water motion are explicit reconstruction inferences.
"""
import bpy, bmesh, json, math, hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix

R=Path('F:/MyWorld/ZurichWorld'); D=R/'derived/bellevue/fountain59'
d=json.loads((D/'input.json').read_text()); scene=bpy.context.scene
assert scene['version']==d['base_version']
name='27_BELLEVUE_FOUNTAIN_59'; assert name not in bpy.data.collections
collection=bpy.data.collections.new(name); bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(collection)
root=bpy.data.objects.new('F59_ROOT',None); collection.objects.link(root)
root.location=(*list(np.array(d['centre_lv95'])-np.array(d['origin'][:2])),d['ground_local'])
root['source_id']=d['source_id']; root['evidence_basis']=d['reference_basis']
root['natural_state']='flowing municipal fountain; runtime interaction pending'

def material(name,color,rough,metal=0,trans=0,ior=1.45):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    p.inputs['Transmission Weight'].default_value=trans;p.inputs['IOR'].default_value=ior
    return m
def stone(kind):
    m=material('F59 | Castione visual proxy '+kind,(.3,.3,.28),.6);n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    for file,socket,colorspace in [(f'granite_{kind}_color.png','Base Color','sRGB'),(f'granite_{kind}_roughness.png','Roughness','Non-Color')]:
        node=n.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(D/'textures'/file),check_existing=True);node.image.colorspace_settings.name=colorspace
        l.new(node.outputs['Color'],p.inputs[socket])
    tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(D/'textures/granite_normal.png'),check_existing=True);tex.image.colorspace_settings.name='Non-Color'
    normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.45;l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],p.inputs['Normal'])
    m['basis']='Original generated1m texture; Castione-like mineral proxy, not actual stone scan';return m
dry,wet,under=stone('dry'),stone('wet'),stone('underside')
silver=material('F59 | weathered chromium silver',(.57,.59,.60),.235,.99)
recess=material('F59 | sheltered casting recess',(.23,.25,.255),.34,.97)
pipe_metal=material('F59 | worn polished outlet',(.65,.67,.68),.19,.99)
water=material('F59 | clear water IOR1.333',(.986,.995,1.),.028,0,1,1.333)
mortar=material('F59 | thin mineral bedding',(.13,.127,.112),.94)

def mesh(name,verts,faces,mat,uv=None,parent=root,smooth=True):
    me=bpy.data.meshes.new(name);me.from_pydata([tuple(p) for p in verts],[],faces);me.update()
    if uv is not None:
        layer=me.uv_layers.new(name='physical_metre_uv')
        for p in me.polygons:
            for li in p.loop_indices:layer.data[li].uv=uv[me.loops[li].vertex_index]
    ob=bpy.data.objects.new(name,me);collection.objects.link(ob);ob.parent=parent;me.materials.append(mat)
    for p in me.polygons:p.use_smooth=smooth
    ob['source_id']=d['source_id'];ob['evidence_basis']=d['reference_basis'];ob['quality_status']='working_not_accepted'
    ob['collision_role']='solid_pending_runtime';return ob

def lathe(name,profile,mat,steps=384,parent=root):
    v=[];uv=[];f=[];run=0
    for j,(r,z) in enumerate(profile):
        if j:run+=math.hypot(r-profile[j-1][0],z-profile[j-1][1])
        for i in range(steps+1):
            t=2*math.pi*i/steps;v.append((r*math.cos(t),r*math.sin(t),z));uv.append((t*max(r,.18),run))
    for j in range(len(profile)-1):
        for i in range(steps):
            a=j*(steps+1)+i;f.append((a,a+1,a+steps+2,a+steps+1))
    ob=mesh(name,v,f,mat,uv,parent)
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(ob.data);bm.free()
    return ob

# A cantilevered bowl, not a solid four-metre cylinder.
profile=[(0,.169),(.56,.169)]
profile += [(float(r),.17+.485*(r/1.98)**2.65) for r in np.linspace(.60,1.98,42)]
profile += [(1.991,.677),(1.998,.708),(2.,.748),(1.998,.767),(1.991,.778),(1.981,.78),(1.85,.78),(1.838,.776),(1.830,.766),(1.825,.735)]
inner_start=len(profile)-1
profile += [(float(r),.308+.421*(r/1.825)**2.65) for r in np.linspace(1.824,0,42)]
profile += [(0,.169)]
basin=lathe('F59_GRANITE_BASIN',profile,dry)
basin.data.materials.append(wet);basin.data.materials.append(under)
for face in basin.data.polygons:
    strip=face.index//384
    if strip>=inner_start:face.material_index=1
    elif strip<36:face.material_index=2
basin['recorded_envelope_m']='diameter4.0, rim0.78 above centre grade; approximate official dimensions'
pedestal=lathe('F59_GRANITE_PEDESTAL',[(0,-.045),(.54,-.045),(.552,.006),(.555,.027),(.553,.058),(.542,.070),(.53,.075),(.53,.17),(0,.17)],under,192)
# Underside extends below highest actual sloping paving at the support perimeter.
bedding=lathe('F59_MINERAL_FOOT_BEDDING',[(.542,-.026),(.562,-.026),(.562,.005),(.547,.010),(.542,-.026)],mortar,192)

def unit(a):
    a=np.asarray(a,dtype=float);return a/max(np.linalg.norm(a),1e-10)
def add_tube(v,f,points,radii,sides=10,closed=False):
    points=np.asarray(points);radii=np.broadcast_to(radii,len(points));start=len(v)
    for j,(p,r) in enumerate(zip(points,radii)):
        tangent=unit(points[min(j+1,len(points)-1)]-points[max(0,j-1)])
        q=unit(np.cross(tangent,[0,1,0] if abs(tangent[1])<.9 else [0,0,1]));b=np.cross(tangent,q)
        for k in range(sides):v.append(p+r*(q*math.cos(2*math.pi*k/sides)+b*math.sin(2*math.pi*k/sides)))
    for j in range(len(points)-1):
        for k in range(sides):a=start+j*sides+k;b=start+j*sides+(k+1)%sides;f.append((a,b,b+sides,a+sides))
    f.extend([tuple(start+k for k in reversed(range(sides))),tuple(start+(len(points)-1)*sides+k for k in range(sides))])
def tube_object(name,points,radius,mat,parent=root,sides=12):
    v=[];f=[];add_tube(v,f,points,radius,sides);return mesh(name,v,f,mat,parent=parent)
def ellipsoid(v,f,centre,radii,angle=0):
    start=len(v);co=math.cos(angle);si=math.sin(angle)
    for j in range(17):
        lat=math.pi*j/16
        for k in range(32):
            a=2*math.pi*k/32;q=np.array([radii[0]*math.sin(lat)*math.cos(a),radii[1]*math.sin(lat)*math.sin(a),radii[2]*math.cos(lat)])
            q=np.array([co*q[0]+si*q[2],q[1],-si*q[0]+co*q[2]]);v.append(q+centre)
    for j in range(16):
        for k in range(32):a=start+j*32+k;b=start+j*32+(k+1)%32;f.append((a,b,b+32,a+32))
def cubic(points,n=24):
    p=np.asarray(points);t=np.linspace(0,1,n)[:,None]
    return (1-t)**3*p[0]+3*(1-t)**2*t*p[1]+3*(1-t)*t*t*p[2]+t**3*p[3]

fish_profile=np.array([[-.305,.139,.001,.003],[-.290,.132,.019,.021],[-.267,.116,.039,.047],[-.230,.100,.056,.065],[-.175,.083,.061,.062],[-.10,.076,.060,.057],[0,.075,.052,.047],[.10,.075,.043,.038],[.185,.079,.024,.027],[.248,.086,.012,.014],[.270,.089,.010,.010]])
def fish_radius(x):
    return [float(np.interp(x,fish_profile[:,0],fish_profile[:,i])) for i in [1,2,3]]
jets=[];assemblies=[]
for number,deg in enumerate([12,132,252]):
    rad=math.radians(deg);anchor=np.array([1.924*math.cos(rad),1.924*math.sin(rad),.78])
    ob=bpy.data.objects.new(f'F59_SCULPTURE_{number+1}',None);collection.objects.link(ob);ob.parent=root;ob.location=anchor
    # Tangential placement with a small inward turn, inferred from overall view.
    ob.rotation_euler.z=rad+math.pi/2+.14
    ob['basis']='Photo-informed three cast assemblies. Hidden relief, individual pose and rotation inferred; not a scan.'
    assemblies.append(ob)
    base=lathe(f'F59_{number}_CAST_FOOT',[(0,0),(.118,0),(.120,.003),(.116,.013),(0,.014)],pipe_metal,96,ob);base.scale.y=.49
    fv=[];ff=[]
    for x in np.linspace(-.305,.270,150):
        z,ry,rz=fish_radius(x)
        for k in range(65):
            a=2*math.pi*k/64;fv.append((x,ry*math.sin(a),z+rz*math.cos(a)))
    for j in range(149):
        for k in range(64):a=j*65+k;ff.append((a,a+1,a+66,a+65))
    fish=mesh(f'F59_{number}_FISH_CAST',fv,ff,silver,parent=ob)
    # Raised overlapping scale edges; constructed relief, not printed fish skin.
    sv=[];sf=[]
    for row in range(26):
        x=-.145+row*.015
        for col in range(17):
            theta=2*math.pi*(col+(row%2)*.5)/17;points=[]
            for t in np.linspace(-math.pi/2,math.pi/2,9):
                xx=x+.0075*math.cos(t);a=theta+.19*math.sin(t);zz,ry,rz=fish_radius(xx)
                points.append((xx,(ry+.0006)*math.sin(a),zz+(rz+.0006)*math.cos(a)))
            add_tube(sv,sf,points,.00043,5)
    mesh(f'F59_{number}_SCALE_RELIEF',sv,sf,silver,parent=ob)
    # Eyes, lip and gill relief follow the tapered head.
    vv=[];faces=[]
    for sign in [-1,1]:
        ellipsoid(vv,faces,[-.249,sign*.041,.135],[.011,.004,.012])
        points=[(-.200,sign*(.052+.004*math.sin(t)),.105+.042*math.cos(t)) for t in np.linspace(0,math.pi,30)]
        add_tube(vv,faces,points,.0014,8)
    mesh(f'F59_{number}_FISH_HEAD_RELIEF',vv,faces,pipe_metal,parent=ob)
    # Thin, double-sided cast fins, with individual fluting.
    v=[];f=[]
    tail=[(.254,0,.088),(.303,0,.159),(.330,0,.156),(.319,0,.122),(.302,0,.093),(.322,0,.052),(.327,0,.013),(.307,0,.010)]
    for side in [-1,1]:
        for x,y,z in tail:v.append((x,y+side*.002,z))
    f.extend([tuple(reversed(range(8))),tuple(range(8,16))])
    for k in range(8):f.append((k,(k+1)%8,(k+1)%8+8,k+8))
    for sign in [-1,1]:
        pts=[(-.14,sign*.044,.045),(-.11,sign*.100,.006),(-.050,sign*.088,.010),(-.06,sign*.044,.05)]
        st=len(v)
        for off in [-.001,.001]:v.extend([(x,y,z+off) for x,y,z in pts])
        f.extend([(st,st+3,st+2,st+1),(st+4,st+5,st+6,st+7)])
        for k in range(4):f.append((st+k,st+(k+1)%4,st+(k+1)%4+4,st+k+4))
    fins=mesh(f'F59_{number}_CAST_FINS',v,f,silver,parent=ob)
    v=[];f=[]
    for sign in [-1,1]:
        for z in np.linspace(.022,.146,13):add_tube(v,f,[(.261,sign*.0025,.087),(.285,sign*.003,.088+.3*(z-.088)),(.310,sign*.003,z)],.00060,6)
    mesh(f'F59_{number}_FIN_FLUTING',v,f,pipe_metal,parent=ob)
    # A connected, softly sculpted child. Photo pose is retained in silhouette;
    # reverse anatomy is an explicitly inferred continuation.
    v=[];f=[]
    for c,r,a in [([.011,0,.143],[.030,.032,.026],0),([-.018,0,.177],[.029,.027,.044],-.25),([-.039,0,.208],[.025,.033,.018],0),([-.052,0,.225],[.014,.016,.020],-.15),([-.063,0,.251],[.032,.027,.036],-.13),([-.090,-.002,.249],[.010,.012,.013],-.20),([-.096,0,.255],[.009,.006,.007],0),([-.085,0,.235],[.009,.012,.007],0)]:ellipsoid(v,f,c,r,a)
    limbs=[([[-.040,-.027,.204],[-.072,-.046,.186],[-.084,-.047,.174],[-.106,-.029,.212]],[.012,.008]),
           ([[-.037,.027,.205],[.003,.045,.207],[.022,.040,.185],[.010,.029,.154]],[.013,.008]),
           ([[.01,-.022,.141],[.041,-.042,.149],[.080,-.041,.142],[.102,-.040,.133]],[.023,.017]),
           ([[.102,-.040,.133],[.128,-.050,.120],[.166,-.048,.119],[.204,-.049,.125]],[.017,.010]),
           ([[.015,.020,.143],[.039,.049,.160],[.071,.049,.178],[.089,.044,.165]],[.021,.016]),
           ([[.089,.044,.165],[.086,.041,.150],[.056,.033,.135],[.033,.031,.141]],[.015,.010])]
    if number==1:limbs[0][0][-1][2]-=.012
    if number==2:limbs[1][0][1][2]+=.01
    for points,radii in limbs:add_tube(v,f,cubic(points),np.linspace(*radii,24),14)
    for c,r in [([.213,-.052,.126],[.017,.014,.008]),([.025,.030,.145],[.017,.012,.007]),([-.107,-.029,.214],[.006,.010,.010]),([.007,.029,.151],[.012,.009,.006]),([-.058,-.028,.252],[.009,.005,.014]),([-.058,.028,.252],[.009,.005,.014])]:ellipsoid(v,f,c,r)
    child=mesh(f'F59_{number}_CHILD_CAST',v,f,silver,parent=ob)
    bpy.ops.object.select_all(action='DESELECT');child.select_set(True);bpy.context.view_layer.objects.active=child
    rm=child.modifiers.new('Continuous cast anatomical surface','REMESH');rm.mode='VOXEL';rm.voxel_size=.00125;rm.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=rm.name)
    sm=child.modifiers.new('Sculpted transitions','SMOOTH');sm.factor=.45;sm.iterations=4;bpy.ops.object.modifier_apply(modifier=sm.name)
    # Hair waves and small facial/finger details remain editable geometry.
    v=[];f=[]
    for row in range(8):
        t0=.19+row*.14
        points=[]
        for a in np.linspace(-1.30,1.45,32):
            points.append((-.059+.031*math.cos(a)*math.sin(t0),.028*math.sin(a)*math.sin(t0),.251+.0358*math.cos(t0)+.0008*math.sin(a*8+row)))
        add_tube(v,f,points,.00105,7)
    for sign in [-1,1]:
        points=[(-.088+.002*math.sin(t),sign*(.010+.004*math.cos(t)),.263+.0015*math.sin(t)) for t in np.linspace(0,math.pi,13)]
        add_tube(v,f,points,.0007,6)
    for k in range(4):
        add_tube(v,f,[(-.112,-.034+k*.003,.211),(-.114,-.034+k*.003,.221),(-.109,-.034+k*.003,.224)],.00125,8)
        add_tube(v,f,[(.003+k*.003,.035,.154),(.004+k*.003,.037,.147),(.010+k*.003,.034,.145)],.00125,8)
    mesh(f'F59_{number}_CAST_FINE_RELIEF',v,f,silver,parent=ob)
    # Actual visible back pipe; a hollow nozzle with an outer rolled rim.
    nozzle=lathe(f'F59_{number}_BACK_NOZZLE',[(.007,0),(.010,0),(.010,.093),(.013,.094),(.013,.099),(.010,.101),(.007,.100),(.007,0)],pipe_metal,40,ob)
    nozzle.location=(.023,.004,.156);nozzle.rotation_euler.y=-.20
    nozzle['interaction_role']='continuously_flowing_water_outlet_pending_runtime'
    mouth=tube_object(f'F59_{number}_FISH_NOZZLE',[[-.301,0,.136],[-.310,0,.145]],.0037,pipe_metal,ob,20)
    bpy.context.view_layer.update()
    for suffix,origin in [('MOUTH',Vector((-.310,0,.145))),('BACK',nozzle.matrix_basis@Vector((0,0,.101)))]:
        local=ob.matrix_basis@origin
        direction=unit([-local.x,-local.y,0]); vz=1.40 if suffix=='MOUTH' else 1.18; vh=2.05 if suffix=='MOUTH' else 1.42
        t_end=(vz+math.sqrt(vz*vz+2*9.81*(local.z-.707)))/9.81
        times=np.linspace(0,t_end,81);points=[]
        for t in times:
            p=np.array(local)+direction*vh*t;p[2]+=vz*t-4.905*t*t
            points.append(p)
        radius=.0023*(1+.1*np.sin(times*75+number))
        tube_object(f'F59_JET_{number}_{suffix}',points,radius,water,sides=10)['collision_role']='water_flow_visual_pending_runtime'
        jets.append({'object':f'F59_JET_{number}_{suffix}','origin':list(local),'horizontal_velocity':(direction*vh).tolist(),'vertical_velocity':vz,'gravity':9.81,'impact':points[-1].tolist(),'flow_radius_m':.0023})

# Clear basin volume and a mildly disturbed surface: millimetres, not ocean waves.
v=[(0,0,.707)];uv=[(0,0)];faces=[];rings=96;steps=384
def wave(x,y,phase):
    z=.00075*math.sin(18*x+9*y+phase)+.00045*math.sin(-23*y+5*x-phase*.8)
    for jet in jets:
        q=jet['impact'];r=math.hypot(x-q[0],y-q[1]);z+=.0015*math.cos(55*r-phase*2)*math.exp(-r*2.8)
    return z
for row in range(1,rings+1):
    r=1.796*row/rings
    for col in range(steps):
        t=2*math.pi*col/steps;x=r*math.cos(t);y=r*math.sin(t);v.append((x,y,.707+wave(x,y,0)));uv.append((x,y))
for k in range(steps):faces.append((0,1+k,1+(k+1)%steps))
for row in range(rings-1):
    for k in range(steps):a=1+row*steps+k;b=1+row*steps+(k+1)%steps;faces.append((a,a+steps,b+steps,b))
surface=mesh('F59_WATER_SURFACE',v,faces,water,uv);surface['collision_role']='water_surface_not_solid';surface['water_level_local']=.707
surface.shape_key_add(name='Basis');key=surface.shape_key_add(name='Wind and jet ripples')
for point in key.data:point.co.z=.707+wave(point.co.x,point.co.y,math.pi)
for frame,value in [(1,0),(41,1),(81,0)]:key.value=value;key.keyframe_insert(data_path='value',frame=frame)
surface['animation_basis']='Small analytic ripple approximation; not fluid simulation'
water_body=lathe('F59_WATER_VOLUME',[(1.796,.707),(1.795,.704),(1.62,.558),(1.30,.443),(.85,.347),(.32,.313),(0,.311)],water,256)
water_body['collision_role']='water_volume_not_solid'

# Perforated overflow strainer: genuine holes through a thin curved sheet.
sv=[];sf=[];radius=.061;thick=.0015;cols=18;rows=3;height=.054
for j in range(rows):
    for k in range(cols):
        center_u=(k+.5)/cols*2*math.pi;cz=.704+(j+.5)*height/rows;start=len(sv)
        for rr in [radius,radius-thick]:
            for boundary in ['outer','hole']:
                for i in range(16):
                    a=2*math.pi*i/16;du=math.cos(a);dz=math.sin(a)
                    if boundary=='outer':scale=1/max(abs(du)/(math.pi/cols),abs(dz)/(.5*height/rows));u=center_u+du*scale;z=cz+dz*scale
                    else:u=center_u+du*.0052/radius;z=cz+dz*.0052
                    sv.append((rr*math.cos(u),rr*math.sin(u),z))
        for i in range(16):
            ni=(i+1)%16
            sf.extend([(start+i,start+ni,start+16+ni,start+16+i),(start+32+i,start+48+i,start+48+ni,start+32+ni),(start+16+i,start+16+ni,start+48+ni,start+48+i)])
strainer=mesh('F59_OVERFLOW_PERFORATED_SHELL',sv,sf,pipe_metal);strainer['real_perforations']=rows*cols
lathe('F59_OVERFLOW_ROLLED_TOP',[(.057,.755),(.062,.755),(.063,.759),(.061,.762),(.057,.762),(.057,.755)],pipe_metal,96)
# Domed perforated cap: top holes made as a single boolean operation.
cap=lathe('F59_OVERFLOW_CAP',[(0,.758),(.058,.758),(.059,.760),(.058,.762),(0,.764),(0,.758)],pipe_metal,96)
cv=[];cf=[]
for ring,count in [(.022,8),(.044,14)]:
    for k in range(count):
        a=k*2*math.pi/count;add_tube(cv,cf,[(ring*math.cos(a),ring*math.sin(a),.750),(ring*math.cos(a),ring*math.sin(a),.776)],.0025,12)
cutter=mesh('TEMP_F59_OVERFLOW_HOLES',cv,cf,pipe_metal)
bpy.context.view_layer.objects.active=cap;mod=cap.modifiers.new('22 drilled holes','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(cutter,do_unlink=True);cap['real_perforations']=22

# Apply only the locally replaced photographic volume; original source remains.
cutpath=R/d['source_cut_file'];assert hashlib.sha256(cutpath.read_bytes()).hexdigest()==d['source_cut_sha256']
cut=json.loads(cutpath.read_text());old=json.loads((R/scene['photo_cut_file']).read_text());oldmap={str(r['node']):r for r in old['overrides']}
context={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};originals={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects};changed=[]
assert len(originals)==2039
for record in cut['overrides']:
    node=str(record['node'])
    if oldmap.get(node)==record:continue
    obj=context[node];src=originals[node];vv=np.asarray(record['vertices']).reshape(-1,3);me=bpy.data.meshes.new('F59_CONTEXT_'+node)
    me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
    for mat in src.data.materials:me.materials.append(mat)
    layer=me.uv_layers.new(name='source_photo_uv');uvs=np.asarray(record['uv_source_v_unflipped']).reshape(-1,2);uvs[:,1]=1-uvs[:,1];layer.data.foreach_set('uv',uvs.astype(np.float32).ravel())
    obj.data=me;obj['construction_mask']=cut['mask_basis'];changed.append(node)

ground=bpy.data.objects['BS_ASPHALT'];camera_names=[];camera_report=[]
for suffix,offset,target,lens in [('OVERVIEW',(3.7,-3.0),(.0,.0,.50),34),('REVERSE',(-3.8,2.5),(0,0,.55),34),('RIM',(2.9,.1),(1.8,0,.80),56)]:
    xy=root.location+Vector((*offset,0));hit,p,_,_=ground.ray_cast(Vector((xy.x,xy.y,40)),Vector((0,0,-1)));assert hit
    name='BE_QA_FOUNTAIN_'+suffix;cd=bpy.data.cameras.new(name);cam=bpy.data.objects.new(name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(cam)
    cam.location=(xy.x,xy.y,p.z+1.65);cam.rotation_euler=(root.location+Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();cd.lens=lens;cam['eye_height_m']=1.65;camera_names.append(name)
    camera_report.append({'name':name,'position':list(cam.location),'eye_above_ground_m':1.65,'lens_mm':lens})
scene.frame_set(1);scene['version']=d['version'];scene['photo_cut_file']=d['source_cut_file'];scene.camera=bpy.data.objects[camera_names[0]]
bpy.context.view_layer.update()
E=R/'evidence'/d['version'];E.mkdir(exist_ok=True)
report={'version':d['version'],'source_id':d['source_id'],'new_objects':len(collection.objects),'photo_nodes_changed':changed,'original_photo_nodes_preserved':2039,
 'basin_diameter_m':max(v.co.x for v in basin.data.vertices)-min(v.co.x for v in basin.data.vertices),'rim_height_m':max(v.co.z for v in basin.data.vertices),
 'material_basis':'Original metre-scale granite maps; smooth metal reflects actual native surroundings. Stone wear and casting details inferred.',
 'sculpture_limit':'Photo-informed editable approximate sculpture; backside anatomy and pose variations inferred. Requires close visual review; not a scanned artwork.',
 'jets':jets,'cameras':camera_report,'natural_use_accepted':False,'runtime_exported':False,'visual_accepted':False}
(E/'construction.json').write_text(json.dumps(report,indent=2));(D/'water_state.json').write_text(json.dumps({'version':d['version'],'water_level_m':.707,'jets':jets,'flowing':True,'runtime_implemented':False},indent=2))
native=R/'native/G1_018_fountain59_working.blend';bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=d['version'],native=str(native),source_cut_file=d['source_cut_file'],source_cut_sha256=d['source_cut_sha256'],accepted=False,not_published=True,next='Native multi-angle fountain surface/shape review; new runtime pipeline and natural use still pending.')
(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['jets','cameras']}))
