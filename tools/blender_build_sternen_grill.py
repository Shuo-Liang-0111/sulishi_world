"""Rebuild the two public frontages of Theaterstrasse 22 and bridge scan remnants.

This is an editable architectural working batch, not an opened/interactive venue.
Measured shell, photographic articulation, and inferred fabrication are separate.
"""
from pathlib import Path
import hashlib,importlib,json,math,shutil,sys
import bpy,bmesh,numpy as np
from mathutils import Vector,Matrix
from mathutils.geometry import tessellate_polygon
sys.path.insert(0,str(Path(__file__).resolve().parent))
importlib.invalidate_caches()
from workspace_paths import ROOT,read_path,write_path
from blender_geometry_fingerprint import mesh_digest,object_state
from blender_photo_clip import cut_object,split

s=bpy.context.scene
assert s['version']=='G1_027r4' and '45_STERNEN_GRILL_FRONTAGES' not in bpy.data.collections
target=write_path('native/G1_027r5_sternen_frontages_working.blend')
assert not target.exists() and shutil.disk_usage(ROOT).free>3_000_000_000
specpath=read_path('derived/sternen_grill/build_input.json');d=json.loads(specpath.read_text())
checkpoint=json.loads(read_path('evidence/G1_027r4/checkpoint.json').read_text())
with Path(bpy.data.filepath).open('rb') as stream:
    assert hashlib.file_digest(stream,'sha256').hexdigest()==checkpoint['native_sha256']
for path,digest in d['sources'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
before={ob.name:object_state(ob) for ob in s.objects}
original=bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE']
original_meshes={o.name:o.data.as_pointer() for o in original.objects};assert len(original_meshes)==2039
base_cameras={o.name:(list(o.location),list(o.rotation_euler),o.data.lens) for o in s.objects if o.type=='CAMERA'}
for cut in d['bridge_residual_cuts']:
    assert json.loads(json.dumps(mesh_digest(bpy.data.objects[cut['object']].data)))==cut['mesh_digest']
photo_probe=json.loads(read_path('derived/sternen_grill/context_probe.json').read_text())
for row in photo_probe['rows']:
    ob=bpy.data.objects[row['name']]
    assert [list(p.vertices) for p in ob.data.polygons]==row['faces']
    assert np.array_equal([list(ob.matrix_world@v.co) for v in ob.data.vertices],row['vertices'])

C=bpy.data.collections.new('45_STERNEN_GRILL_FRONTAGES')
bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(C)
C['source_id']='AV50487 / EGID302060199 / Theaterstrasse22'
C['basis']=d['basis'];C['runtime_interaction_verified']=False
A=np.array(d['A']);U=np.array(d['U']);N=np.array(d['N']);W=d['width'];D=d['depth'];floor=d['floor_z']
def P(u,v,z):return np.r_[A+U*u+N*v,z]
def Q(p):return np.array([(p[:2]-A)@U,(p[:2]-A)@N,p[2]])
def side(u,v,z):return P(W+v,-u,z)
groups={}
def add(name,verts,faces,mat,bevel=0,smooth=False):
    key=(name,mat.name)
    g=groups.setdefault(key,dict(v=[],f=[],mat=mat,bevel=bevel,smooth=smooth))
    start=len(g['v']);g['v'].extend([list(v) for v in verts]);g['f'].extend([tuple(start+i for i in f) for f in faces])
def box(name,c,sz,mat,bevel=.004,frame=P):
    points=[frame(c[0]+i*sz[0]/2,c[1]+j*sz[1]/2,c[2]+k*sz[2]/2) for i,j,k in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    add(name,points,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,bevel)
def tube(name,points,r,mat,sides=10):
    points=np.array(points);verts=[];faces=[]
    for j,p in enumerate(points):
        axis=points[min(j+1,len(points)-1)]-points[max(0,j-1)];axis/=np.linalg.norm(axis)
        seed=[0,0,1] if abs(axis[2])<.95 else [1,0,0]
        x=np.cross(axis,seed);x/=np.linalg.norm(x);y=np.cross(axis,x)
        verts.extend([p+r*(x*np.cos(a)+y*np.sin(a)) for a in np.arange(sides)*math.tau/sides])
    for j in range(len(points)-1):
        for k in range(sides):a=j*sides+k;b=j*sides+(k+1)%sides;faces.append((a,b,b+sides,a+sides))
    faces.extend([tuple(range(sides-1,-1,-1)),tuple((len(points)-1)*sides+k for k in range(sides))])
    add(name,verts,faces,mat,smooth=True)
def mat(name,color,rough=.6,metal=0,micro=.00012):
    m=bpy.data.materials.new('SG | '+name);m.use_nodes=True
    nodes=m.node_tree.nodes;links=m.node_tree.links;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
    if micro:
        c=nodes.new('ShaderNodeTexCoord');n=nodes.new('ShaderNodeTexNoise');n.inputs['Scale'].default_value=110;n.inputs['Detail'].default_value=3
        links.new(c.outputs['Object'],n.inputs['Vector']);b=nodes.new('ShaderNodeBump');b.inputs['Distance'].default_value=micro;b.inputs['Strength'].default_value=.21
        links.new(n.outputs['Fac'],b.inputs['Height']);links.new(b.outputs['Normal'],bs.inputs['Normal'])
    m['evidence_basis']='Photographic material family; measured optical properties unavailable.'
    return m
stones=[mat('pale fine-grained limestone '+str(i),tuple(np.array([.54,.505,.44])*(.97+i*.008)),.68,micro=.00020) for i in range(8)]
joint=mat('recessed dry stone joints',(.18,.17,.15),.9)
metal=mat('dark bronze aluminium frames',(.052,.048,.039),.34,.62)
seal=mat('EPDM glazing gasket',(.012,.014,.013),.8)
glass=mat('clear double glazing',(.86,.92,.94),.11,0,0)
bs=next(n for n in glass.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Transmission Weight'].default_value=1;bs.inputs['IOR'].default_value=1.45
inner=mat('unopened interior plaster',(.36,.335,.285),.91)
ceiling=mat('balcony mineral soffit',(.46,.44,.39),.86)
linen=[mat('interior blind '+str(i),c,.85) for i,c in enumerate([(.39,.43,.40),(.54,.53,.47),(.29,.31,.29)])]
red=mat('folded burgundy awning',(.19,.023,.024),.87,micro=.00015)
roofmat=bpy.data.materials['roof_slates_03'];zinc=mat('weathered zinc roof flashing',(.23,.25,.26),.45,.66)
gold=mat('brass building lettering',(.49,.31,.087),.31,.77)
floor_mat=mat('grey threshold stone',(.26,.265,.25),.77,micro=.00025)

def panel_rect(name,x0,x1,z0,z1,frame=P,depth=-.24):
    if x1-x0<.006 or z1-z0<.006:return
    # Backing closes joints; separate slabs have their own fine edges.
    box(name+'_BACKING',((x0+x1)/2,depth-.016,(z0+z1)/2),(x1-x0,.43,z1-z0),joint,.001,frame)
    n=max(1,int(np.ceil((z1-z0)/1.08)))
    for i in range(n):
        a=z0+(z1-z0)*i/n;b=z0+(z1-z0)*(i+1)/n
        idx=(int(round(x0*13))+i*3+int(z0*7))%len(stones)
        box(name+'_STONE',((x0+x1)/2,depth,(a+b)/2),(x1-x0-.003,.48,b-a-.003),stones[idx],.0018,frame)

def window(name,u,w,z0,z1,frame=P,index=0):
    h=z1-z0;mid=(z0+z1)/2
    # Deep tapered stone reveals, frame and gasket are separate solids.
    for sign in [-1,1]:
        outer=u+sign*w/2;inside=outer-sign*.095
        verts=[frame(outer,.005,z0-.012),frame(outer,.005,z1+.012),frame(inside,-.31,z1-.07),frame(inside,-.31,z0+.07)]
        add(name+'_REVEAL',verts,[(0,1,2,3)],stones[(index+2)%8])
    box(name+'_SILL',(u,-.12,z0-.035),(w+.09,.41,.075),stones[index%8],.003,frame)
    box(name+'_LINTEL',(u,-.13,z1+.024),(w+.06,.40,.055),stones[(index+1)%8],.002,frame)
    for x in [u-w/2+.12,u+w/2-.12,u]:
        box(name+'_FRAME',(x,-.328,mid),(.050 if x==u else .058,.07,h-.14),metal,.002,frame)
    for z in [z0+.105,z1-.105]:box(name+'_FRAME',(u,-.328,z),(w-.20,.07,.055),metal,.002,frame)
    for sign in [-1,1]:
        x=u+sign*(w-.24)/4
        gw=(w-.24)/2-.047;gh=h-.219
        for edge in [-1,1]:
            box(name+'_GASKET',(x+edge*(gw/2+.004),-.367,mid),(.012,.025,gh+.022),seal,.001,frame)
            box(name+'_GASKET',(x,-.367,mid+edge*(gh/2+.004)),(gw,.025,.012),seal,.001,frame)
        box(name+'_GLASS',(x,-.373,mid),(gw,.016,gh),glass,0,frame)
    # Inset room returns prevent a flat opaque billboard behind glass.
    box(name+'_ROOM',(u,-1.65,mid),(w+.04,.10,h+.04),inner,.002,frame)
    for x in [u-w/2,u+w/2]:box(name+'_ROOM',(x,-1.01,mid),(.08,1.25,h+.06),inner,.002,frame)
    for z in [z0,z1]:box(name+'_ROOM',(u,-1.01,z),(w,1.25,.06),inner,.002,frame)
    # Genuine shallow vertical blind geometry, different draw state per room.
    if index%5!=1:
        extent=w*(.35 if index%3==0 else .75);start=u-w/2+.16
        for j in range(max(2,int(extent/.10))):
            x=start+j*.105;twist=.018 if index%2 else -.025
            verts=[frame(x,-1.32,z0+.08),frame(x+.084,-1.32+twist,z0+.08),frame(x+.084,-1.32+twist,z1-.1),frame(x,-1.32,z1-.1)]
            add(name+'_BLIND',verts,[(0,1,2,3)],linen[index%3])

for side_id,length,centers,frame in [('FRONT',W,d['front_centers'],P),('LANE',D,d['side_centers'],side)]:
    w=d['window_width']
    for li,L in enumerate(d['levels']):
        name='SG_'+side_id+'_LEVEL'+str(li+2)
        cursor=0.
        for wi,u in enumerate(centers):
            panel_rect(name,cursor,u-w/2,L['sill'],L['head'],frame)
            # Divide spandrels at pier centres, matching full-height stone joints.
            a=0 if wi==0 else (centers[wi-1]+u)/2
            b=length if wi==len(centers)-1 else (u+centers[wi+1])/2
            for za,zb in [(L['bottom'],L['sill']),(L['head'],L['top'])]:panel_rect(name,a,b,za,zb,frame)
            window(name+'_W'+str(wi),u,w,L['sill'],L['head'],frame,index=li*9+wi+(20 if side_id=='LANE' else 0))
            cursor=u+w/2
        panel_rect(name,cursor,length,L['sill'],L['head'],frame)
    # First-floor restaurant has a continuous inset glazed band and balcony.
    zf=d['balcony_floor_z'];zu=d['upper_start_z']
    box('SG_'+side_id+'_BALCONY_FLOOR',(length/2,.08,zf-.11),(length+(.07 if side_id=='FRONT' else 0),1.45,.22),floor_mat,.01,frame)
    panel_rect('SG_'+side_id+'_BALCONY_FASCIA',0,length,zf-.63,zf+.01,frame,depth=.57)
    box('SG_'+side_id+'_BALCONY_CAP',(length/2,.595,zf+.028),(length,.24,.07),stones[3],.005,frame)
    for z,r in [(zf+.15,.012),(zf+.54,.014),(zf+.91,.023)]:tube('SG_'+side_id+'_BALCONY_RAIL',[frame(0,.66,z),frame(length,.66,z)],r,metal,12)
    for x in np.linspace(.08,length-.08,9):tube('SG_'+side_id+'_BALCONY_POST',[frame(x,.66,zf+.035),frame(x,.66,zf+.915)],.017,metal,10)
    box('SG_'+side_id+'_SOFFIT',(length/2,-.46,zu-.095),(length,1.43,.18),ceiling,.003,frame)
    for j in range(5):
        a=length*j/5;b=length*(j+1)/5
        box('SG_'+side_id+'_RESTAURANT_GLAZING',((a+b)/2,-.93,(zf+zu)/2),(b-a-.09,.018,zu-zf-.32),glass,0,frame)
        box('SG_'+side_id+'_RESTAURANT_MULLION',(a+.025,-.88,(zf+zu)/2),(.064,.09,zu-zf-.11),metal,.002,frame)
        box('SG_'+side_id+'_AWNING_CASSETTE',((a+b)/2,.01,zu-.18),(b-a-.025,.18,.16),metal,.003,frame)
        box('SG_'+side_id+'_AWNING_FABRIC',((a+b)/2,.09,zu-.255),(b-a-.05,.21,.035),red,.003,frame)
    for z in [zf+.11,zu-.15]:box('SG_'+side_id+'_RESTAURANT_RAIL',(length/2,-.88,z),(length,.09,.064),metal,.003,frame)
    box('SG_'+side_id+'_RESTAURANT_BACK',(length/2,-1.76,(zf+zu)/2),(length,.10,zu-zf),inner,.002,frame)
    # Street-level piers and recessed display/entrance joinery.
    bay=length/4
    for i in range(5):
        width=.54 if i not in [0,4] else .43
        box('SG_'+side_id+'_GROUND_PIER',(i*bay,-.24,(floor+zf-.60)/2),(width,.80,zf-.60-floor),stones[(i+2)%8],.005,frame)
        box('SG_'+side_id+'_GROUND_PLINTH',(i*bay,-.19,floor+.17),(width+.015,.86,.34),floor_mat,.004,frame)
    for i in range(4):
        u=(i+.5)*bay;ww=bay-.58;z0=floor+.10;z1=zf-.67
        for x in [u-ww/2,u,u+ww/2]:box('SG_'+side_id+'_SHOP_FRAME',(x,-.65,(z0+z1)/2),(.061,.09,z1-z0),metal,.002,frame)
        for z in [z0,z1,z1-.47]:box('SG_'+side_id+'_SHOP_FRAME',(u,-.65,z),(ww,.09,.065),metal,.002,frame)
        for sign in [-1,1]:
            box('SG_'+side_id+'_SHOP_GLASS',(u+sign*ww/4,-.695,(z0+z1)/2),(ww/2-.069,.020,z1-z0-.07),glass,0,frame)
        box('SG_'+side_id+'_SHOP_BACK',(u,-1.77,(z0+z1)/2),(ww,.12,z1-z0),inner,.001,frame)
        box('SG_'+side_id+'_SHOP_FLOOR',(u,-1.09,floor+.025),(ww,1.39,.10),floor_mat,.003,frame)
        box('SG_'+side_id+'_SHOP_CEILING',(u,-1.09,z1+.045),(ww,1.39,.09),ceiling,.003,frame)
        for x in [u-ww/2,u+ww/2]:box('SG_'+side_id+'_SHOP_RETURN',(x,-1.2,(z0+z1)/2),(.09,1.1,z1-z0),inner,.002,frame)
        if side_id=='FRONT' and i in [1,2]:
            for sign in [-1,1]:
                x=u+sign*.16
                tube('SG_FRONT_ENTRANCE_PULLS',[frame(x,-.57,floor+1.02),frame(x,-.57,floor+1.40)],.017,metal,12)
                for z in [floor+1.05,floor+1.37]:tube('SG_FRONT_ENTRANCE_STANDOFF',[frame(x,-.65,z),frame(x,-.57,z)],.012,metal,10)
    # A continuous stone threshold under the recessed street joinery.
    box('SG_'+side_id+'_THRESHOLD',(length/2,-.15,floor-.04),(length,.99,.10),floor_mat,.004,frame)
    # Projecting eave and sloped zinc cap are tied to the source eave level.
    box('SG_'+side_id+'_EAVE',(length/2,.015,d['eave_z']-.035),(length+.04,.49,.10),stones[4],.004,frame)

# Source roof geometry: no flattened guessed lid; keep measured slopes and vents.
roof_audit=d['roof_triangulation_audit']
for triangle in d['roof_triangles']:
    raw=np.array(triangle['vertices'])
    clipped,_=split([np.r_[p,p] for p in raw],2,25.16,True)
    if len(clipped)<3:continue
    # A clipped triangle is convex; no API-dependent tessellation is needed.
    vv=[np.array(p[:3]) for p in clipped]
    for j in range(1,len(vv)-1):
        points=[vv[0],vv[j],vv[j+1]]
        normal=np.cross(points[1]-points[0],points[2]-points[0])
        if np.linalg.norm(normal)<1e-8:continue
        normal/=np.linalg.norm(normal)
        material=roofmat if triangle['type']=='RoofSurface' and abs(normal[2])<.98 else zinc
        add('SG_OFFICIAL_ROOF_'+triangle['source'].split('.')[-1],points,[(0,1,2)],material)
# Front and lane roof terrace rail; inferred fabrication following visible photos.
for side_id,length,frame in [('FRONT',W-.86,P),('LANE',D,side)]:
    for z in [27.22,28.12]:tube('SG_'+side_id+'_ROOF_HANDRAIL',[frame(.05,-.98,z),frame(length,-.98,z)],.021,metal,12)
    for x in np.arange(.10,length,.14):tube('SG_'+side_id+'_ROOF_BALUSTER',[frame(x,-.98,27.22),frame(x,-.98,28.12)],.009,metal,8)

# The projecting brass star is modelled as a folded solid, not a photo decal.
u=W-.43;z=18.42;verts=[P(u,.64,z)]
for i in range(10):
    a=math.pi/2+i*math.tau/10;r=.68 if i%2==0 else .27
    verts.append(P(u+r*math.cos(a),.10,z+r*math.sin(a)))
verts.append(P(u,-.02,z))
faces=[]
for i in range(10):faces.extend([(0,1+i,1+(i+1)%10),(11,1+(i+1)%10,1+i)])
add('SG_BRASS_STAR',verts,faces,gold,.003)

modifier_types={q.identifier for q in bpy.types.Modifier.bl_rna.properties['type'].enum_items}
assert {'BEVEL','WEIGHTED_NORMAL'}.issubset(modifier_types)
created=[]
for (name,_),g in groups.items():
    me=bpy.data.meshes.new(name);me.from_pydata(g['v'],[],g['f']);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
    assert not me.validate(clean_customdata=False),name
    ob=bpy.data.objects.new(name,me);C.objects.link(ob);me.materials.append(g['mat'])
    for p in me.polygons:p.use_smooth=g['smooth']
    uv=me.uv_layers.new(name='metre_scale')
    for face in me.polygons:
        axes=[i for i in range(3) if i!=int(np.argmax(abs(np.array(face.normal))))]
        for li in face.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]]/3,p[axes[1]]/3)
    if g['bevel']:
        mod=ob.modifiers.new('material edge','BEVEL');mod.width=g['bevel'];mod.segments=2
        ob.modifiers.new('architectural normals','WEIGHTED_NORMAL')
    ob['construction_batch']='G1_027r5';ob['source_id']='EGID302060199 / AV50487'
    ob['evidence_basis']=d['basis'];ob['collision_role']='solid_pending_runtime'
    ob['interaction_state']='Facade working model; glazing and entry closed, no door interaction implemented.'
    created.append(ob.name)

def lettering(name,text,u,v,z,size):
    curve=bpy.data.curves.new(name,'FONT');curve.body=text;curve.size=size;curve.extrude=.004;curve.align_x='CENTER';curve.space_character=1.2
    ob=bpy.data.objects.new(name,curve);C.objects.link(ob)
    ob.location=P(u,v,z);ob.rotation_euler=Matrix((Vector((*U,0)),Vector((0,0,1)),Vector((*N,0)))).transposed().to_euler()
    curve.materials.append(gold);bpy.context.view_layer.update()
    deps=bpy.context.evaluated_depsgraph_get();mesh=bpy.data.meshes.new_from_object(ob.evaluated_get(deps))
    transform=ob.matrix_world.copy();bpy.data.objects.remove(ob,do_unlink=True)
    ob=bpy.data.objects.new(name,mesh);C.objects.link(ob);ob.matrix_world=transform
    ob['source_id']='PSP reference photography: physical site lettering';ob['collision_role']='visual_nonblocking';created.append(ob.name)
lettering('SG_RESTAURANT_LETTERING','STERNEN GRILL',W*.52,-.588,11.31,.165)
for j,ch in enumerate('VORDERER STERNEN'):
    if ch!=' ':lettering('SG_BUILDING_LETTER_'+str(j),ch,W-.35,.021,24.25-j*.287,.16)

# Clip current working photo data only, retaining originals and exact unaffected UVs.
cuts=[]
for row in photo_probe['rows']:
    ob=bpy.data.objects[row['name']]
    result=cut_object(ob,Q,d['photo_cut_boxes']+[d['roof_cut_box']])
    if result:ob['sternen_replacement']='G1_027r5 two street frontages and upper roof';cuts.append(result)
for row in d['bridge_residual_cuts']:
    ob=bpy.data.objects[row['object']];result=cut_object(ob,lambda p:p,[],row['faces'])
    assert result and not result['clipped_faces'] and len(result['removed_faces'])==len(row['faces'])
    ob['residual_cleanup']='G1_027r5 bounded detached sheets; physical bridge fixtures already present';cuts.append(result)
assert {o.name:o.data.as_pointer() for o in original.objects}==original_meshes
changed={r['object'] for r in cuts}
unchanged_errors=[name for name,state in before.items() if name not in changed and object_state(bpy.data.objects[name])!=state]
assert not unchanged_errors,unchanged_errors[:10]
assert all((list(bpy.data.objects[name].location),list(bpy.data.objects[name].rotation_euler),bpy.data.objects[name].data.lens)==values for name,values in base_cameras.items())

camera_rows=[];bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
for name,eye,look,lens in [('SG_QA_FRONT',P(W/2,23,10.2),P(W/2,-.3,16.6),27),
                          ('SG_QA_CORNER',P(W+7,9,10.2),P(W-1.2,-3.5,16.0),24),
                          ('SG_QA_ENTRY',P(W*.52,4.8,10.2),P(W*.52,-.5,10.65),31)]:
    hit,ground,n,face,ob,m=s.ray_cast(deps,Vector((eye[0],eye[1],10.0)),Vector((0,0,-1)),distance=5)
    assert hit and n.z>.5,(name,ob.name if hit else 'no floor')
    eye[2]=ground.z+1.7;cam=bpy.data.cameras.new(name);obj=bpy.data.objects.new(name,cam)
    bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(obj);obj.location=eye;obj.rotation_euler=(Vector(look)-obj.location).to_track_quat('-Z','Y').to_euler();cam.lens=lens;cam.clip_end=1600
    camera_rows.append(dict(name=name,eye=eye.tolist(),look=look.tolist(),lens=lens,floor=ob.name,eye_height_m=1.7))

# All image/library links are made absolute before saving into a new H-native.
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and not im.library:
        im.filepath=bpy.path.abspath(im.filepath)
for lib in bpy.data.libraries:lib.filepath=bpy.path.abspath(lib.filepath)
for font in bpy.data.fonts:
    if font.filepath and font.filepath!='<builtin>' and not font.library:font.filepath=bpy.path.abspath(font.filepath)
missing=[bpy.path.abspath(im.filepath,library=im.library) for im in bpy.data.images if im.source=='FILE' and im.filepath and not im.packed_file and not Path(bpy.path.abspath(im.filepath,library=im.library)).is_file()]
assert not missing,missing[:3]
s['version']='G1_027r5';s['latest_construction']='Theaterstrasse22 physical front/lane facade and roof; bridge residual correction'
s.camera=bpy.data.objects['SG_QA_FRONT']
report=dict(version=s['version'],base_native=checkpoint['native'],base_native_sha256=checkpoint['native_sha256'],
    spec_sha256=hashlib.sha256(specpath.read_bytes()).hexdigest(),created_objects=created,
    photo_cuts=cuts,original_source_meshes_unchanged=2039,unrelated_objects_unchanged=len(before)-len(changed),
    old_cameras_unchanged=True,cameras=camera_rows,roof_polygons=roof_audit,missing_images=missing,
    limits=['No complete interior or natural door use yet','Rear facade remains source mesh','Source inference is not architectural survey','Full-area realism and same-version runtime not accepted'])
write_path('evidence/G1_027r5/build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(target),check_existing=False,compress=True)
with target.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
receipt={k:checkpoint[k] for k in ['storage_sharing_applied','required_immutable_libraries','shared_meshes','shared_objects']}
receipt.update(dict(version=s['version'],native=str(target),native_sha256=digest,native_bytes=target.stat().st_size,
    objects=len(s.objects),native_fresh_reopen_verified=False,visual_acceptance=False,runtime_exported=False,natural_use_verified=False))
write_path('evidence/G1_027r5/checkpoint.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in receipt.items() if k not in ['shared_meshes','shared_objects']}),flush=True)
