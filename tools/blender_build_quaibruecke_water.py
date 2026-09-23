"""Build editable full bridge support and bounded water context in023r1."""
from pathlib import Path
import ast,hashlib,json,math
import bpy
import numpy as np
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/quaibruecke_water'
s=bpy.context.scene;assert s['version']=='G1_023r1'
assert Path(bpy.data.filepath).name=='G1_023r1_quaibruecke_portals_working.blend'
assert '39_BRIDGE_WATER_CONTEXT' not in bpy.data.collections
P=json.loads((D/'build_input.json').read_text(encoding='utf-8'))
B=json.loads((R/'derived/bellevue/quaibruecke_connection/build_input.json').read_text(encoding='utf-8'))
O=np.array(P['origin']);A=np.array(B['bridge_anchor']);T=np.array(B['bridge_along']);N=np.array(B['bridge_across'])
E=R/'evidence/G1_024';E.mkdir(exist_ok=True)
C=bpy.data.collections.new('39_BRIDGE_WATER_CONTEXT');bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(C)
source=ast.parse((R/'tools/blender_build_quaibruecke.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in {'mesh','beam','sweep','painted'}],type_ignores=[]),'bridge_mesh_helpers','exec'))
mats={'concrete':bpy.data.materials['QB | aged mineral structure'],
      'steel':bpy.data.materials['QB | grey bridge steel coating'],
      'rubber':painted('QW | bearing elastomer',(.012,.014,.013),0.,.82)}
stone=bpy.data.materials['QB | bank stone facing'].copy();stone.name='QW | pier mineral with waterline'
n=stone.node_tree.nodes;l=stone.node_tree.links;b=next(q for q in n if q.type=='BSDF_PRINCIPLED')
link=next((q for q in l if q.to_socket==b.inputs['Base Color']),None)
if link:
    color=link.from_socket;l.remove(link)
    geometry=n.new('ShaderNodeNewGeometry');sep=n.new('ShaderNodeSeparateXYZ');l.new(geometry.outputs['Position'],sep.inputs[0])
    ramp=n.new('ShaderNodeMapRange');ramp.inputs['From Min'].default_value=5.90;ramp.inputs['From Max'].default_value=6.23
    ramp.inputs['To Min'].default_value=.47;ramp.inputs['To Max'].default_value=1.;l.new(sep.outputs['Z'],ramp.inputs['Value'])
    mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
    l.new(color,mix.inputs[1]);l.new(ramp.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],b.inputs['Base Color'])
stone['evidence_basis']='AV pier outline,1985 pier photographs; exposed stone texture and waterline condition inferred.'
mats['pier']=stone

water=bpy.data.materials.new('QW | continuous lake and river water');water.use_nodes=True
n=water.node_tree.nodes;l=water.node_tree.links;b=next(q for q in n if q.type=='BSDF_PRINCIPLED');out=next(q for q in n if q.type=='OUTPUT_MATERIAL')
b.inputs['Base Color'].default_value=(.72,.84,.80,1);b.inputs['Metallic'].default_value=0
b.inputs['Roughness'].default_value=.10;b.inputs['IOR'].default_value=1.333;b.inputs['Transmission Weight'].default_value=.98
coord=n.new('ShaderNodeTexCoord');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3.6;noise.inputs['Detail'].default_value=3.2
l.new(coord.outputs['Object'],noise.inputs['Vector'])
wave=n.new('ShaderNodeTexWave');wave.wave_type='BANDS';wave.bands_direction='DIAGONAL'
wave.inputs['Scale'].default_value=1.9;wave.inputs['Distortion'].default_value=6.5;wave.inputs['Detail'].default_value=3
l.new(coord.outputs['Object'],wave.inputs['Vector'])
mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=.58
l.new(noise.outputs['Fac'],mix.inputs[1]);l.new(wave.outputs['Fac'],mix.inputs[2])
bump=n.new('ShaderNodeBump');bump.inputs['Distance'].default_value=.032;bump.inputs['Strength'].default_value=.45
l.new(mix.outputs[0],bump.inputs['Height']);l.new(bump.outputs[0],b.inputs['Normal'])
absorb=n.new('ShaderNodeVolumeAbsorption');absorb.inputs['Color'].default_value=(.12,.34,.27,1);absorb.inputs['Density'].default_value=.13
l.new(absorb.outputs['Volume'],out.inputs['Volume'])
water['evidence_basis']='Actual AV water/channel boundary. Historical mean406.00; water condition,depth,absorption and ripples inferred, no present gauge claim.'
mats['water']=water

created=[]
for part in P['parts']:
    ob=mesh(part['name'],part['vertices'],part['faces'],part['role'],part['source'],.003 if part['role']=='pier' else 0)
    ob['source_plan_area_m2']=part['area_m2'];ob['construction_batch']='G1_024'
    if part['role']=='water':
        ob['collision_role']='water_non_walkable';ob['inferred_depth_m']=11.
        for face in ob.data.polygons:face.use_smooth=face.normal.z>.5
    created.append(ob.name)

for girder in P['girders']:
    k=girder['index'];arr=np.array(girder['stations']);d=girder['across']
    for part,halfwidth in [('WEB',.010),('TOP_FLANGE',.26),('LOWER_FLANGE',.22)]:
        verts=[]
        for st,x,y,top,bottom in arr:
            lo,hi=(bottom,top) if part=='WEB' else ((top-.024,top) if part=='TOP_FLANGE' else (bottom,bottom+.028))
            p=np.array([x,y]);verts.extend([[*(p-N*halfwidth)-O[:2],lo-400],[*(p+N*halfwidth)-O[:2],lo-400],
                                           [*(p+N*halfwidth)-O[:2],hi-400],[*(p-N*halfwidth)-O[:2],hi-400]])
        faces=[[3,2,1,0],list(range((len(arr)-1)*4,len(arr)*4))]
        faces.extend([[i*4+j,i*4+(j+1)%4,(i+1)*4+(j+1)%4,(i+1)*4+j] for i in range(len(arr)-1) for j in range(4)])
        mesh(f'CONTINUOUS_GIRDER_{k}_{part}',verts,faces,'steel','AV four piers +1985 four-main-girder section; sizes inferred',.001)
    for j,st in enumerate(np.arange(23.,P['spans'][-1],1.5)):
        p=A+T*st+N*d;top=float(np.interp(st,arr[:,0],arr[:,3]));bottom=float(np.interp(st,arr[:,0],arr[:,4]))
        for side in [-1,1]:
            q=p+N*side*.075
            beam(f'WEST_GIRDER_{k}_STIFFENER_{j}_{side}',[*q,bottom+.028],[*q,top-.024],.018,.13,'steel','inferred continuation stiffener',.001,[*T,0])
        if j%4==0 and k<3:
            q=p+N*7.10
            beam(f'WEST_CROSS_DIAPHRAGM_{k}_{j}',[*p,top-.45],[*q,top-.45],.12,.64,'steel','1985 cross-girder relation, size inferred',.003)

# Visible continuous service pipes documented in the1985 underside photograph.
# Exact circuits and routing are not known; retain them as nonfunctional context.
for k,(d,radius) in enumerate([(8.1,.22),(9.0,.13),(15.0,.12)]):
    points=[]
    for st in np.linspace(1.,P['spans'][-1]-.6,90):
        p=A+T*st+N*d;z=float(np.array(B['bridge_deck_coefficients'])@[1,st,st*st,d])-.82
        points.append([*p,z])
    sweep(f'SERVICE_PIPE_{k}',points,radius,'steel','1985 visible utilities; route/circuit inferred')
    for j,st in enumerate(np.arange(2.,P['spans'][-1],4.5)):
        p=A+T*st+N*d;deck=float(np.array(B['bridge_deck_coefficients'])@[1,st,st*st,d])
        beam(f'PIPE_{k}_HANGER_{j}',[*p,deck-.41],[*p,deck-.82-radius-.045],.022,.028,'steel','inferred utility support',.001)

cutpath=R/'derived/bellevue/west_context/quaibruecke_water_structure_cut.json'
cut=json.loads(cutpath.read_text(encoding='utf-8'));prior=R/s['photo_cut_file']
assert cut['base_cut_sha256']==hashlib.sha256(prior.read_bytes()).hexdigest()
old={str(q['node']):q for q in json.loads(prior.read_text(encoding='utf-8'))['overrides']}
working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
changed=[]
for rec in cut['overrides']:
    key=str(rec['node'])
    if old.get(key)==rec:continue
    ob=working[key];materials=[slot.material for slot in ob.material_slots]
    v=np.array(rec['vertices']).reshape(-1,3);uv=np.array(rec['uv_source_v_unflipped']).reshape(-1,2);uv[:,1]=1-uv[:,1]
    me=bpy.data.meshes.new('QW_PHOTO_'+key);me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
    for mat in materials:me.materials.append(mat)
    layer=me.uv_layers.new(name='source_photo_uv');layer.data.foreach_set('uv',uv.astype(np.float32).ravel());ob.data=me
    for slot,mat in zip(ob.material_slots,materials):slot.material=mat
    ob['construction_mask']=cut['mask_basis'];changed.append(key)
assert set(changed)==set(cut['water_structure_changed_nodes'])
for ob in C.objects:ob['construction_batch']='G1_024'
s['version']='G1_024';s['photo_cut_file']=cutpath.relative_to(R).as_posix();bpy.context.view_layer.update()
(E/'construction.json').write_text(json.dumps(dict(version=s['version'],objects=len(C.objects),photo_nodes=changed,
    source_input_sha256=hashlib.sha256((D/'build_input.json').read_bytes()).hexdigest(),
    original_photography_retained=True,cameras_exposure_sky_sun_unchanged=True,
    g1_walking_scope_expanded=False,visual_acceptance=False,natural_use_verified=False),indent=2),encoding='utf-8')
print('BRIDGE_WATER_AUTHORED',json.dumps({'objects':len(C.objects),'photo_nodes':len(changed)}),flush=True)
