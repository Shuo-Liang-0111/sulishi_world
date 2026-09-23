"""Author the source-shaped Riviera low promenade in the verified021r3 scene."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import bpy
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/riviera_lower'
P=json.loads((D/'build_input.json').read_text());O=np.array(P['origin']);s=bpy.context.scene
assert s['version']=='G1_021r3' and '36_RIVIERA_LOWER_APPROACH' not in bpy.data.collections
assert (R/'evidence/G1_021r3/shared_geometry_reopen.json').is_file()
bpy.context.preferences.filepaths.use_auto_save_temporary_files=False
C=bpy.data.collections.new('36_RIVIERA_LOWER_APPROACH');bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(C)
E=R/'evidence/G1_022';E.mkdir(exist_ok=True)

def material_copy(source,name):
    m=bpy.data.materials[source].copy();m.name=name
    m['evidence_basis']='Reference-guided/inferred fabrication; existing CC0 material proxy, not a local scan.'
    return m
paving=material_copy('RQ | continuous promenade asphalt','RL | fine outdoor low deck')
concrete=material_copy('RQ | fine cast stair mineral','RL | river cast mineral')
wallmat=material_copy('RQ | fine cast stair mineral','RL | cast retaining wall')
wood=material_copy('oak_veneer_01','RL | weathered bank slats')
for m in [paving,concrete,wallmat,wood]:
    for node in list(m.node_tree.nodes):
        if node.type=='DISPLACEMENT':m.node_tree.nodes.remove(node)
    for node in m.node_tree.nodes:
        if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.58
    bsdf=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    if m==wood:
        bsdf.inputs['Roughness'].default_value=.74
        for link in list(m.node_tree.links):
            if link.to_socket==bsdf.inputs['Roughness']:m.node_tree.links.remove(link)
        colorlink=next((l for l in m.node_tree.links if l.to_socket==bsdf.inputs['Base Color']),None)
        if colorlink:
            source=colorlink.from_socket;m.node_tree.links.remove(colorlink)
            desat=m.node_tree.nodes.new('ShaderNodeHueSaturation');desat.inputs['Saturation'].default_value=.36;desat.inputs['Value'].default_value=.66
            m.node_tree.links.new(source,desat.inputs['Color']);m.node_tree.links.new(desat.outputs[0],bsdf.inputs['Base Color'])
        for node in m.node_tree.nodes:
            if node.type=='MAPPING':node.inputs['Scale'].default_value=(1.1,1.1,1.1)

metal=bpy.data.materials.new('RL | weathered zinc steel');metal.use_nodes=True
n=metal.node_tree.nodes;l=metal.node_tree.links;b=next(q for q in n if q.type=='BSDF_PRINCIPLED')
b.inputs['Base Color'].default_value=(.30,.32,.33,1);b.inputs['Metallic'].default_value=.82;b.inputs['Roughness'].default_value=.44
tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=330;tex.inputs['Detail'].default_value=2.2
coord=n.new('ShaderNodeTexCoord');l.new(coord.outputs['Object'],tex.inputs['Vector'])
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.13;bump.inputs['Distance'].default_value=.00018
l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],b.inputs['Normal'])
metal['evidence_basis']='Steel stair described by original authors; zinc finish and microsurface inferred.'
mats={'paving':paving,'concrete':concrete,'wall':wallmat,'steel':metal,'wood':wood}

def mesh(name,verts,faces,role,source,bevel=0,uv_axes=None):
    lookup={};v=[];remap=[]
    for q in verts:
        key=tuple(round(float(x),6) for x in q)
        if key not in lookup:lookup[key]=len(v);v.append(q)
        remap.append(lookup[key])
    f=[[remap[i] for i in face] for face in faces]
    me=bpy.data.meshes.new('RL_'+name);me.from_pydata(v,[],f);me.update();me.materials.append(mats[role])
    uv=me.uv_layers.new(name='metre_scale')
    for face in me.polygons:
        axis=int(np.argmax(np.abs(face.normal)));axes=([1,2],[0,2],[0,1])[axis]
        frame=None
        if uv_axes:
            normal_axis=int(np.argmax([abs(Vector(a).dot(face.normal)) for a in uv_axes]))
            frame=[a for k,a in enumerate(uv_axes) if k!=normal_axis]
        for li in face.loop_indices:
            q=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=(float(Vector(frame[0]).dot(q)),float(Vector(frame[1]).dot(q))) if frame else (q[axes[0]],q[axes[1]])
    ob=bpy.data.objects.new('RL_'+name,me);C.objects.link(ob)
    ob['source_id']=source;ob['construction_batch']='G1_022';ob['surface_role']=role
    ob['fabrication_inferred']=True;ob['collision_role']='walkable_candidate' if role=='paving' else 'solid_pending_runtime'
    if bevel:
        mod=ob.modifiers.new('Physical edge radius','BEVEL');mod.width=bevel;mod.segments=3
        assert 'ANGLE' in {a.identifier for a in mod.bl_rna.properties['limit_method'].enum_items};mod.limit_method='ANGLE'
        ob.modifiers.new('Face weighted normals','WEIGHTED_NORMAL')
    return ob

def beam(name,a,b,width,depth,role,source,bevel=.002,side_axis=None):
    a=np.array(a);b=np.array(b);t=(b-a)/np.linalg.norm(b-a)
    cross=np.cross(t,[0,0,1.])
    if np.linalg.norm(cross)<.01:cross=np.array([1.,0,0])
    if side_axis is not None:cross=np.array(side_axis,dtype=float)
    cross/=np.linalg.norm(cross);up=np.cross(cross,t);v=[]
    for p in [a,b]:
        v.extend([p+cross*width*u/2+up*depth*w/2-O for u,w in [(-1,-1),(1,-1),(1,1),(-1,1)]])
    return mesh(name,v,[[3,2,1,0],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]],role,source,bevel,uv_axes=[t,cross,up])

def tube(name,a,b,radius,source,sides=12):
    a=np.array(a);b=np.array(b);t=(b-a)/np.linalg.norm(b-a);cross=np.cross(t,[0,0,1.])
    if np.linalg.norm(cross)<.01:cross=np.array([1.,0,0])
    cross/=np.linalg.norm(cross);up=np.cross(cross,t)
    v=[p+radius*(cross*math.cos(k*2*math.pi/sides)+up*math.sin(k*2*math.pi/sides))-O for p in [a,b] for k in range(sides)]
    faces=[list(range(sides-1,-1,-1)),list(range(sides,sides*2))]
    faces.extend([[k,(k+1)%sides,(k+1)%sides+sides,k+sides] for k in range(sides)])
    ob=mesh(name,v,faces,'steel',source)
    for face in list(ob.data.polygons)[2:]:face.use_smooth=True
    return ob

for part in P['parts']:
    ob=mesh(part['name'],part['vertices'],part['faces'],part['role'],part['source'],.003 if part['role'] in ['wall','concrete'] else .001)
    ob['source_plan_area_m2']=part['area_m2']

# Separate narrow bars make each steel tread open, supported and readable below.
stairsource='av_ei_flaechenelement_a.47309';tread_support=[]
for i,rec in enumerate(P['treads']):
    a=np.array(rec['inner_edge']);b=np.array(rec['outer_edge']);z=rec['z_ln02_m']
    # Tread perimeter and intermediate transverse bars; all ends meet the frame.
    for label,start,end in [('inner',a[0],a[1]),('outer',b[0],b[1]),('nose',a[0],b[0]),('back',a[1],b[1])]:
        beam(f'TREAD_{i:02}_{label}',[*start,z-.028],[*end,z-.028],.026,.055,'steel',stairsource,.001)
    for j,t in enumerate(np.linspace(.06,.94,7)):
        q=a[0]*(1-t)+a[1]*t;r=b[0]*(1-t)+b[1]*t
        beam(f'TREAD_{i:02}_BAR_{j}',[*q,z-.018],[*r,z-.018],.008,.035,'steel',stairsource,.0008)
    tread_support.append({'name':f'RL_TREAD_{i:02}_nose','height_ln02_m':z,'source_riser':rec['upper_riser_source']})

bounds=np.array(P['stairs_boundaries']);rise=P['stair_rise_m'];base=P['floor_ln02_m']
for side in [0,1]:
    for i in range(len(bounds)-1):
        a=bounds[i,side];b=bounds[i+1,side]
        za=base+i*rise-.16;zb=base+(i+1)*rise-.16
        beam(f'STAIR_STRINGER_{side}_{i:02}',[*a,za],[*b,zb],.075,.24,'steel',stairsource,.002)
    for i in [0,4,8,13]:
        p=bounds[i,side];z=base+i*rise
        tube(f'STAIR_POST_{side}_{i}',[*p,z-.08],[*p,z+1.0],.022,stairsource)
    for i in range(len(bounds)-1):
        a=bounds[i,side];b=bounds[i+1,side]
        for h,label,r in [(1.0,'HAND',.022),(.50,'MID',.014)]:
            tube(f'STAIR_{label}_{side}_{i:02}',[*a,base+i*rise+h],[*b,base+(i+1)*rise+h],r,stairsource)
    for i in [0,13]:
        p=bounds[i,side];z=base+i*rise
        beam(f'STAIR_BASEPLATE_{side}_{i}',[p[0]-.07,p[1],z-.011],[p[0]+.07,p[1],z-.011],.12,.018,'steel',stairsource,.001)

benches=P['benches']
for i,rec in enumerate(benches):
    p=np.array(rec['edge_xy']);n=np.array(rec['inward']);t=np.array(rec['along']);z=rec['z_ln02_m'];centre=p+n*.36
    beam(f'BANK_PIER_{i:02}',[*centre,z-.25],[*centre,z+.75],.32,.67,'concrete','av_bo_boflaeche_a.40750',.007,side_axis=[*t,0])
    if i==len(benches)-1:continue
    nxt=benches[i+1];q=np.array(nxt['edge_xy']);nn=np.array(nxt['inward']);zz=nxt['z_ln02_m']
    tt=q-p;tt/=np.linalg.norm(tt)
    for j,offset in enumerate(np.linspace(.15,.59,6)):
        pa=p+n*offset+tt*.12;pb=q+nn*offset-tt*.12
        beam(f'BANK_SEAT_{i:02}_{j}',[*pa,z+.46],[*pb,zz+.46],.064,.047,'wood','reference_guided_bank_seating',.0035)
    # Two seaward rails, shaped as slats rather than a featureless solid bench.
    for k,h in enumerate([.13,.73]):
        pa=p+n*.10+tt*.15;pb=q+nn*.10-tt*.15
        beam(f'BANK_OUTER_RAIL_{i:02}_{k}',[*pa,z+h],[*pb,zz+h],.055,.10,'wood','reference_guided_bank_seating',.003)

rail=P['upper_wall_rail']
for i,rec in enumerate(rail):
    p=rec['xy'];z=rec['z']
    beam(f'WALL_PICKET_{i:03}',[*p,z+.07],[*p,z+1.045],.018,.025,'steel','av_ei_flaechenelement_a.20735',.001,side_axis=[*rec['along'],0])
    if i and rec['station']-rail[i-1]['station']<.20:
        prev=rail[i-1]
        for label,h,w,d in [('TOP',1.06,.050,.035),('LOW',.13,.025,.027)]:
            beam(f'WALL_RAIL_{label}_{i:03}',[*prev['xy'],prev['z']+h],[*p,z+h],w,d,'steel','av_ei_flaechenelement_a.20735',.0015)
    if i%16==0:
        beam(f'WALL_MAIN_POST_{i:03}',[*p,z-.045],[*p,z+1.06],.042,.050,'steel','av_ei_flaechenelement_a.20735',.002)

# Full-resolution source photography is only replaced inside the authored volumes.
path=R/'derived/bellevue/west_context/riviera_lower_approach_cut.json';cut=json.loads(path.read_text())
oldpath=R/s['photo_cut_file'];assert cut['base_cut_sha256']==hashlib.sha256(oldpath.read_bytes()).hexdigest()
old={str(q['node']):q for q in json.loads(oldpath.read_text())['overrides']}
working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};changed=[]
for rec in cut['overrides']:
    key=str(rec['node'])
    if old.get(key)==rec:continue
    ob=working[key];materials=[slot.material for slot in ob.material_slots]
    v=np.asarray(rec['vertices']).reshape(-1,3);tex=np.asarray(rec['uv_source_v_unflipped']).reshape(-1,2);tex[:,1]=1-tex[:,1]
    me=bpy.data.meshes.new('RL_PHOTO_'+key);me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
    for m in materials:me.materials.append(m)
    uv=me.uv_layers.new(name='source_photo_uv');uv.data.foreach_set('uv',tex.astype(np.float32).ravel());ob.data=me
    for slot,m in zip(ob.material_slots,materials):slot.material=m
    ob['construction_mask']=cut['mask_basis'];changed.append(key)
assert set(changed)==set(cut['lower_approach_changed_nodes'])
s['version']='G1_022';s['photo_cut_file']=str(path.relative_to(R))
bpy.context.view_layer.update()

camera_records=[]
for name,xy,target,lens in [
    ('RL_QA_NORTH',[2683495.45,1246864.6],[2683491.2,1246886.4,407.6],30),
    ('RL_QA_SOUTH',[2683491.20,1246883.5],[2683496.2,1246859.0,407.6],30),
    ('RL_QA_STAIR',[2683493.58,1246854.75],[2683497.75,1246859.30,408.3],34),
    ('RL_QA_SEAT',[2683496.28,1246869.90],[2683494.04,1246871.76,407.05],43)]:
    hits=[];pos=np.array(xy)-O[:2]
    for ob in C.objects:
        if ob.get('surface_role')!='paving':continue
        hit,q,_,_=ob.ray_cast(Vector((*pos,30)),Vector((0,0,-1)))
        if hit:hits.append(q.z)
    assert hits,('Camera outside authored floor',name)
    floorz=max(hits);cd=bpy.data.cameras.new(name);co=bpy.data.objects.new(name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(co)
    co.location=(*pos,floorz+1.65);co.rotation_euler=(Vector(np.array(target)-O)-co.location).to_track_quat('-Z','Y').to_euler();cd.lens=lens
    co['eye_height_m']=1.65;co['floor_height_local']=floorz;camera_records.append({'name':name,'floor_local':floorz,'eye_height_m':1.65})
s.camera=bpy.data.objects['RL_QA_NORTH']
C['source_scope']='AV40750, AV20735, AV47309; northern approach only, bridge underpass pending'
C['build_input_sha256']=hashlib.sha256((D/'build_input.json').read_bytes()).hexdigest()
C['construction_complete']=True
record={'version':s['version'],'new_objects':len(C.objects),'source_report':P['report'],'tread_support':tread_support,
        'cameras':camera_records,'changed_photo_nodes':changed,'native_saved':False,
        'visual_acceptance':False,'natural_use_verified':False}
(E/'construction.json').write_text(json.dumps(record,indent=2))
print(json.dumps({k:record[k] for k in ['version','new_objects','changed_photo_nodes','cameras']}),flush=True)
