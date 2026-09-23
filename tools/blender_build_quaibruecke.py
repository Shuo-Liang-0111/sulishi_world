"""Build the whole source-shaped public underpass connection in022r2.

This creates editable physical solids. Its concealed floor profile and detailed
fabrication are explicitly inferred; visual/runtime acceptance remain separate.
"""
from pathlib import Path
import hashlib
import json
import math
import bpy
import numpy as np
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/quaibruecke_connection'
P=json.loads((D/'build_input.json').read_text());O=np.array(P['origin'])
s=bpy.context.scene
assert s['version']=='G1_022r2' and '37_QUAIBRUECKE_CONNECTION' not in bpy.data.collections
assert Path(bpy.data.filepath).name=='G1_022r2_riviera_object_continuity.blend'
bpy.context.preferences.filepaths.use_auto_save_temporary_files=False
E=R/'evidence/G1_023';E.mkdir(exist_ok=True)
C=bpy.data.collections.new('37_QUAIBRUECKE_CONNECTION')
bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(C)
old_objects=set(o.name for o in s.objects)
prior_signature={o.name:(list(o.matrix_world),o.data) for o in s.objects if o.type=='MESH' and not o.name.startswith('PHOTO_')}


def copy_mat(source,name):
    m=bpy.data.materials[source].copy();m.name=name
    m['evidence_basis']='Photograph/reference-guided material class; generic CC0/procedural surface, not a local scan.'
    return m


mats={'paving':copy_mat('RL | fine outdoor low deck','QB | fine sheltered asphalt'),
      'concrete':copy_mat('RL | river cast mineral','QB | aged mineral structure'),
      'coping':copy_mat('RL | river cast mineral','QB | dark dressed coping'),
      'abutment':copy_mat('RQ | fine cast stair mineral','QB | bank stone facing'),
      'steel':copy_mat('RL | weathered zinc steel','QB | steel access stair'),
      'wood':copy_mat('RL | weathered bank slats','QB | lake bank slats')}
for key in ['coping','abutment']:
    m=mats[key];nodes=m.node_tree.nodes;links=m.node_tree.links
    b=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    link=next((l for l in links if l.to_socket==b.inputs['Base Color']),None)
    if link:
        src=link.from_socket;links.remove(link)
        hs=nodes.new('ShaderNodeHueSaturation');hs.inputs['Saturation'].default_value=.24
        hs.inputs['Value'].default_value=.43 if key=='coping' else .78
        links.new(src,hs.inputs['Color']);links.new(hs.outputs[0],b.inputs['Base Color'])


def painted(name,color,metallic,roughness):
    m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links
    b=next(q for q in n if q.type=='BSDF_PRINCIPLED')
    b.inputs['Metallic'].default_value=metallic;b.inputs['Roughness'].default_value=roughness
    tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=2.4;tex.inputs['Detail'].default_value=3
    coord=n.new('ShaderNodeTexCoord');l.new(coord.outputs['Object'],tex.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB')
    for el,fac in zip(ramp.color_ramp.elements,[.68,1.06]):el.color=(*[v*fac for v in color],1)
    l.new(tex.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],b.inputs['Base Color'])
    micro=n.new('ShaderNodeTexNoise');micro.inputs['Scale'].default_value=460.;micro.inputs['Detail'].default_value=2
    l.new(coord.outputs['Object'],micro.inputs['Vector'])
    bump=n.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.00038;bump.inputs['Strength'].default_value=.18
    l.new(micro.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],b.inputs['Normal'])
    m['evidence_basis']='Actual underpass photo supports colour/material family. Wear and coating fabrication inferred.'
    return m


mats['blue_lining']=painted('QB | weathered teal trough lining',(.018,.155,.185),0.,.83)
mats['girder']=painted('QB | grey bridge steel coating',(.20,.205,.20),.32,.60)
mats['drain']=painted('QB | recessed drain iron',(.024,.027,.027),.75,.63)
mat=mats['blue_lining'];n=mat.node_tree.nodes;l=mat.node_tree.links;b=next(q for q in n if q.type=='BSDF_PRINCIPLED')
link=next(q for q in l if q.to_socket==b.inputs['Base Color']);base=link.from_socket;l.remove(link)
att=n.new('ShaderNodeAttribute');att.attribute_name='height_above_path'
fade=n.new('ShaderNodeMapRange');fade.inputs['From Min'].default_value=.03;fade.inputs['From Max'].default_value=.27
fade.inputs['To Min'].default_value=.52;fade.inputs['To Max'].default_value=1
l.new(att.outputs['Fac'],fade.inputs['Value'])
mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
l.new(base,mix.inputs[1]);l.new(fade.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],b.inputs['Base Color'])

route=np.array(P['route']);steps=np.linalg.norm(np.diff(route,axis=0),axis=1)
accum=np.r_[0,np.cumsum(steps)]


def floor_at(p):
    d=route[1:]-route[:-1];u=np.clip(np.einsum('ij,ij->i',p-route[:-1],d)/(steps*steps),0,1)
    near=route[:-1]+u[:,None]*d;i=int(np.argmin(np.linalg.norm(near-p,axis=1)))
    sta=accum[i]+u[i]*steps[i]
    return float(np.interp(sta,P['report']['floor_profile_stations_m'],P['report']['floor_profile_ln02_m']))


def mesh(name,vertices,faces,role,source,bevel=0,uv_axes=None):
    remap=[];lookup={};v=[]
    for q in vertices:
        # Weld at the actual Blender float32 coordinates. Source intersections
        #can contain sub-ULP slivers that become zero-area faces on import.
        key=tuple(float(x) for x in np.asarray(q,dtype=np.float32))
        if key not in lookup:lookup[key]=len(v);v.append(key)
        remap.append(lookup[key])
    f=[]
    for face in faces:
        ids=list(dict.fromkeys(remap[i] for i in face))
        if len(ids)<3:continue
        pts=np.array([v[i] for i in ids]);area=sum(np.linalg.norm(np.cross(pts[i]-pts[0],pts[i+1]-pts[0]))/2 for i in range(1,len(ids)-1))
        if area>1e-11:f.append(ids)
    me=bpy.data.meshes.new('QB_'+name);me.from_pydata(v,[],f);me.update();me.materials.append(mats[role])
    uv=me.uv_layers.new(name='metre_scale')
    for face in me.polygons:
        axes=([1,2],[0,2],[0,1])[int(np.argmax(np.abs(face.normal)))]
        frame=None
        if uv_axes:
            a=int(np.argmax([abs(Vector(q).dot(face.normal)) for q in uv_axes]))
            frame=[q for k,q in enumerate(uv_axes) if k!=a]
        for li in face.loop_indices:
            q=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=(Vector(frame[0]).dot(q),Vector(frame[1]).dot(q)) if frame else (q[axes[0]],q[axes[1]])
    if role=='blue_lining':
        height=me.attributes.new('height_above_path','FLOAT','POINT')
        height.data.foreach_set('value',np.array([p[2]+400-floor_at(np.array(p[:2])+O[:2]) for p in v],dtype=np.float32))
    ob=bpy.data.objects.new('QB_'+name,me);C.objects.link(ob)
    ob['source_id']=source;ob['construction_batch']='G1_023';ob['surface_role']=role
    ob['profile_or_fabrication_inferred']=True
    ob['collision_role']='walkable_candidate' if role=='paving' else 'solid_pending_runtime'
    if bevel:
        mod=ob.modifiers.new('Real edge radius','BEVEL');mod.width=bevel;mod.segments=2
        assert 'ANGLE' in {q.identifier for q in mod.bl_rna.properties['limit_method'].enum_items};mod.limit_method='ANGLE'
        ob.modifiers.new('Face weighted normals','WEIGHTED_NORMAL')
    return ob


def beam(name,a,b,width,depth,role,source,bevel=.001,side_axis=None):
    a=np.array(a);b=np.array(b);t=(b-a)/np.linalg.norm(b-a)
    cross=np.cross(t,[0,0,1.])
    if np.linalg.norm(cross)<.01:cross=np.array([1.,0,0])
    if side_axis is not None:cross=np.array(side_axis,dtype=float)
    cross/=np.linalg.norm(cross);up=np.cross(cross,t)
    vertices=[p+cross*width*u/2+up*depth*w/2-O for p in [a,b] for u,w in [(-1,-1),(1,-1),(1,1),(-1,1)]]
    return mesh(name,vertices,[[3,2,1,0],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]],role,source,bevel,[t,cross,up])


def sweep(name,points,radius,role,source):
    p=np.array(points);verts=[];sides=12
    for i,point in enumerate(p):
        t=p[min(i+1,len(p)-1)]-p[max(0,i-1)];t/=np.linalg.norm(t)
        a=np.cross(t,[0,0,1.])
        if np.linalg.norm(a)<.01:a=np.array([1.,0,0])
        a/=np.linalg.norm(a);b=np.cross(t,a)
        verts.extend([point+radius*(a*math.cos(k*2*math.pi/sides)+b*math.sin(k*2*math.pi/sides))-O for k in range(sides)])
    faces=[list(range(sides-1,-1,-1)),list(range((len(p)-1)*sides,len(p)*sides))]
    faces.extend([[i*sides+k,i*sides+(k+1)%sides,(i+1)*sides+(k+1)%sides,(i+1)*sides+k]
                 for i in range(len(p)-1) for k in range(sides)])
    ob=mesh(name,verts,faces,role,source)
    for face in list(ob.data.polygons)[2:]:face.use_smooth=True
    return ob


for part in P['parts']:
    ob=mesh(part['name'],part['vertices'],part['faces'],part['role'],part['source'],
            .0025 if part['role'] in ['blue_lining','coping','abutment'] else 0)
    ob['source_plan_area_m2']=part['area_m2']

# Curved I girders with separate flange solids, webs and supported stiffeners.
A=np.array(P['bridge_anchor']);T=np.array(P['bridge_along']);N=np.array(P['bridge_across'])
for girder in P['girders']:
    k=girder['index'];arr=np.array(girder['stations']);d=girder['across']
    for part,halfwidth in [('WEB',.010),('TOP_FLANGE',.26),('LOWER_FLANGE',.22)]:
        vertices=[]
        for st,x,y,top,bottom in arr:
            zlo,zhi=(bottom,top) if part=='WEB' else ((top-.024,top) if part=='TOP_FLANGE' else (bottom,bottom+.028))
            p=np.array([x,y])
            vertices.extend([[*(p-N*halfwidth)-O[:2],zlo-400],[*(p+N*halfwidth)-O[:2],zlo-400],
                             [*(p+N*halfwidth)-O[:2],zhi-400],[*(p-N*halfwidth)-O[:2],zhi-400]])
        faces=[[3,2,1,0],list(range((len(arr)-1)*4,len(arr)*4))]
        faces.extend([[i*4+j,i*4+(j+1)%4,(i+1)*4+(j+1)%4,(i+1)*4+j] for i in range(len(arr)-1) for j in range(4)])
        ob=mesh(f'GIRDER_{k}_{part}',vertices,faces,'girder','KUBA502;1985 steel section',.001)
        ob['shape_basis']='4 main girders/arched lower flange referenced; section dimensions/profile interpreted.'
    for j,st in enumerate(np.arange(.5,22.625,1.5)):
        p=A+T*st+N*d;top=float(np.interp(st,arr[:,0],arr[:,3]));bottom=float(np.interp(st,arr[:,0],arr[:,4]))
        for side in [-1,1]:
            q=p+N*side*.075
            beam(f'GIRDER_{k}_STIFFENER_{j}_{side}',[*q,bottom+.028],[*q,top-.024],.018,.13,'girder','reference_guided_steel_fabrication',.001,[*T,0])
        if j%4==0 and k<3:
            q=p+N*7.10
            beam(f'CROSS_DIAPHRAGM_{k}_{j}',[*p,top-.45],[*q,top-.45],.12,.64,'girder','1985 bridge underside',.003)

for i,h in enumerate(P['hangers']):
    p=np.array(h['xy']);height=h['top']-h['bottom'];assert height>.4
    beam(f'TROUGH_HANGER_{i}',[*p,h['bottom']],[*p,h['top']],.08,.035,'girder','reference-guided trough suspension',.001,[*T,0])
    for end,z in [('LOW',h['bottom']),('HIGH',h['top'])]:
        beam(f'HANGER_{i}_{end}_PLATE',[*p-T*.12,z],[*p+T*.12,z],.18,.025,'girder','inferred connection plate',.001)

# The source steel side stair remains open mesh, not a dark solid ramp.
bound=np.array(P['stair_boundaries']);base=P['report']['south_stair_low_ln02_m'];rise=P['report']['south_stair_rise_m']
for tread in P['treads']:
    i=tread['index'];a=np.array(tread['lower_edge']);b=np.array(tread['upper_edge']);z=tread['z']
    for label,pa,pb in [('NOSE',a[0],a[1]),('BACK',b[0],b[1]),('LEFT',a[0],b[0]),('RIGHT',a[1],b[1])]:
        beam(f'STAIR_{i:02}_{label}',[*pa,z-.027],[*pb,z-.027],.025,.055,'steel',tread['source'])
    for j,t in enumerate(np.linspace(.06,.94,7)):
        pa=a[0]*(1-t)+b[0]*t;pb=a[1]*(1-t)+b[1]*t
        beam(f'STAIR_{i:02}_BAR_{j}',[*pa,z-.016],[*pb,z-.016],.009,.033,'steel',tread['source'],.0008)
for side in [0,1]:
    rail=[]
    for i,p in enumerate(bound[:,side]):
        z=base+i*rise;rail.append([*p,z+1.0])
        if i in [0,4,8,13]:
            sweep(f'STAIR_POST_{side}_{i}',[[*p,z-.10],[*p,z+1.0]],.022,'steel','AV6191 inferred guard')
        if i:
            q=bound[i-1,side]
            beam(f'STAIR_STRINGER_{side}_{i}',[*q,z-rise-.16],[*p,z-.16],.07,.25,'steel','AV6191 inferred stringer')
    for label,h,rad in [('HAND',0,.022),('MID',-.50,.014)]:
        sweep(f'STAIR_{label}_{side}',[[q[0],q[1],q[2]+h] for q in rail],rad,'steel','AV6191 inferred guard')

# Lake-side bank seating uses the same referenced pier/slat construction as the
#Riviera; the number and fabrication details are not survey-inventory claims.
seats=P['bank_seats']
for i,rec in enumerate(seats):
    p=np.array(rec['xy']);n=np.array(rec['inward']);t=np.array(rec['along']);z=rec['floor'];q=p+n*.36
    beam(f'BANK_PIER_{i:02}',[*q,z-.24],[*q,z+.74],.32,.67,'concrete','reference-guided lake bank seat',.007,[*t,0])
    if i==len(seats)-1:continue
    nxt=seats[i+1];pp=np.array(nxt['xy']);nn=np.array(nxt['inward']);zz=nxt['floor'];tt=pp-p;tt/=np.linalg.norm(tt)
    for j,offset in enumerate(np.linspace(.15,.59,6)):
        pa=p+n*offset+tt*.07;pb=pp+nn*offset-tt*.07
        beam(f'BANK_SEAT_{i:02}_{j}',[*pa,z+.46],[*pb,zz+.46],.064,.047,'wood','reference-guided bank seating',.0035)
    for j,h in enumerate([.13,.73]):
        pa=p+n*.10+tt*.15;pb=pp+nn*.10-tt*.15
        beam(f'BANK_RAIL_{i:02}_{j}',[*pa,z+h],[*pb,zz+h],.055,.10,'wood','reference-guided bank seating',.003)

# Drain gratings are integrated in the floor, with no invented trigger/task.
for i,p in enumerate([route[1]*.8+route[2]*.2,route[1]*.2+route[2]*.8]):
    z=floor_at(p)
    for j in range(12):
        q=p+T*(j-5.5)*.018
        beam(f'DRAIN_{i}_{j}',[*q-N*.18,z-.007],[*q+N*.18,z-.007],.008,.014,'drain','inferred surface drainage',.0006)

# Texture/object overrides are preserved. The original2039 source meshes and
#all non-replaced photographic objects stay available in their source collection.
cutpath=R/'derived/bellevue/west_context/quaibruecke_connection_cut.json';cut=json.loads(cutpath.read_text())
oldpath=R/s['photo_cut_file'];assert cut['base_cut_sha256']==hashlib.sha256(oldpath.read_bytes()).hexdigest()
previous={str(q['node']):q for q in json.loads(oldpath.read_text())['overrides']}
working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
changed=[]
for rec in cut['overrides']:
    key=str(rec['node'])
    if previous.get(key)==rec:continue
    ob=working[key];materials=[slot.material for slot in ob.material_slots]
    v=np.array(rec['vertices']).reshape(-1,3);uv=np.array(rec['uv_source_v_unflipped']).reshape(-1,2);uv[:,1]=1-uv[:,1]
    me=bpy.data.meshes.new('QB_PHOTO_'+key);me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
    for mat in materials:me.materials.append(mat)
    layer=me.uv_layers.new(name='source_photo_uv');layer.data.foreach_set('uv',uv.astype(np.float32).ravel());ob.data=me
    for slot,mat in zip(ob.material_slots,materials):slot.material=mat
    ob['construction_mask']=cut['mask_basis'];changed.append(key)
assert set(changed)==set(cut['quaibruecke_changed_nodes'])
s['version']='G1_023';s['photo_cut_file']=cutpath.relative_to(R).as_posix()
bpy.context.view_layer.update()

camera_records=[]
for name,xy,target,lens in [
    ('QB_QA_NORTH',[2683489.08,1246847.55],[2683481.6,1246838.4,406.75],28),
    ('QB_QA_INTERIOR',[2683483.70,1246829.0],[2683487.30,1246816.8,406.80],28),
    ('QB_QA_BEAMS',[2683483.70,1246829.0],[2683467.1,1246823.5,407.2],30),
    ('QB_QA_SOUTH',[2683503.6,1246810.1],[2683491.7,1246815.3,407.10],30),
    ('QB_QA_STAIR',[2683507.7,1246806.9],[2683512.25,1246803.3,408.05],32),
]:
    local=np.array(xy)-O[:2];hits=[]
    for ob in C.objects:
        if ob.get('surface_role')!='paving':continue
        hit,p,_,_=ob.ray_cast(Vector((*local,20)),Vector((0,0,-1)))
        if hit:hits.append(p.z)
    assert hits,('camera misses constructed floor',name)
    z=max(hits);cd=bpy.data.cameras.new(name);co=bpy.data.objects.new(name,cd)
    bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(co);co.location=(*local,z+1.65)
    co.rotation_euler=(Vector(np.array(target)-O)-co.location).to_track_quat('-Z','Y').to_euler();cd.lens=lens
    co['eye_height_m']=1.65;co['floor_height_local']=z;camera_records.append(dict(name=name,floor=z+400,eye_height_m=1.65))
s.camera=bpy.data.objects['QB_QA_INTERIOR']
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_perspective='CAMERA'
C['build_input_sha256']=hashlib.sha256((D/'build_input.json').read_bytes()).hexdigest()
C['source_scope']='AV39461/KUBA477 public connection; AV6191 stair; KUBA502 eastern bridge underside. Separate structural void remains closed.'
record=dict(version=s['version'],objects=len(C.objects),source_report=P['report'],changed_photo_nodes=changed,
            cameras=camera_records,native_saved=False,visual_acceptance=False,natural_use_verified=False)
(E/'construction.json').write_text(json.dumps(record,indent=2))
print('UNDERPASS_AUTHORED',json.dumps({k:record[k] for k in ['version','objects','changed_photo_nodes','cameras']}),flush=True)
