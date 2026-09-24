"""Author the complete bridge deck and approach in026; no source mesh deletion."""
from pathlib import Path
import ast,hashlib,json,math
import bpy,bmesh
import numpy as np
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/bridge_deck';s=bpy.context.scene
assert s['version']=='G1_026' and Path(bpy.data.filepath).name=='G1_026_bridgehead_portal_working.blend'
assert '43_BRIDGE_DECK' not in bpy.data.collections
P=json.loads((D/'build_input.json').read_text());F=json.loads((D/'fittings.json').read_text());O=np.array(P['origin'])
digest=hashlib.sha256((D/'build_input.json').read_bytes()).hexdigest()
assert F['input_sha256']==digest
assert json.loads((D/'preparation_checks.json').read_text())['input_sha256']==digest
E=R/'evidence/G1_027';E.mkdir(exist_ok=True)
old={o.name:(o.data.as_pointer() if o.data else None,tuple(o.matrix_basis),o.hide_render,
     tuple(slot.material.as_pointer() if slot.material else None for slot in o.material_slots)) for o in s.objects}
C=bpy.data.collections.new('43_BRIDGE_DECK');bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(C)
bpy.context.preferences.filepaths.use_auto_save_temporary_files=False
source=ast.parse((R/'tools/blender_build_quaibruecke.py').read_text())
helper=ast.unparse(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','sweep','beam','painted']],type_ignores=[]))
exec(compile(helper.replace("'QB_'","'BD_'"),'bridge_deck_helpers','exec'))
raw_mesh=mesh
def mesh(*args,**kwargs):
    ob=raw_mesh(*args,**kwargs)
    bad=[p.index for p in ob.data.polygons if p.area<1e-11]
    if bad:
        # Very narrow source-bound quads can suffer float32 area cancellation
        # hundreds of metres from the local origin. Keep all vertices/UVs and
        # split those faces into triangles; do not erase a legitimate side.
        bm=bmesh.new();bm.from_mesh(ob.data);bm.faces.ensure_lookup_table()
        bmesh.ops.triangulate(bm,faces=[bm.faces[i] for i in bad]);bm.to_mesh(ob.data);bm.free();ob.data.update()
        assert all(p.area>1e-11 for p in ob.data.polygons),ob.name
        ob['numerically_triangulated_faces']=len(bad)
    return ob

def copy_mat(name,role):
    m=bpy.data.materials[name].copy();m.name='BD | '+role
    m['evidence_basis']='Source orthophoto material class; generic CC0 or inferred microstructure, not a local scan.'
    return m

mats={role:copy_mat('asphalt_03',role) for role in ['asphalt_walk','asphalt_road','asphalt_track']}
for role,m in mats.items():
    nodes=m.node_tree.nodes;links=m.node_tree.links;b=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    for link in list(links):
        if link.to_node.type=='OUTPUT_MATERIAL' and link.to_socket.name=='Displacement':links.remove(link)
    for n in nodes:
        if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.5
    connection=next(q for q in links if q.to_socket==b.inputs['Base Color'])
    color=connection.from_socket;links.remove(connection)
    coord=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value=.17;noise.inputs['Detail'].default_value=3
    links.new(coord.outputs['Object'],noise.inputs['Vector'])
    ramp=nodes.new('ShaderNodeValToRGB');factor=.95 if role=='asphalt_walk' else .78 if role=='asphalt_track' else .87
    for el,value in zip(ramp.color_ramp.elements,[factor*.9,factor*1.05]):el.color=(value,value,value,1)
    links.new(noise.outputs['Fac'],ramp.inputs[0])
    mix=nodes.new('ShaderNodeMixRGB')
    assert 'MULTIPLY' in {q.identifier for q in mix.bl_rna.properties['blend_type'].enum_items}
    mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
    links.new(color,mix.inputs[1]);links.new(ramp.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],b.inputs['Base Color'])
mats.update(rail=copy_mat('BE | worn tram rail head','rail running face'),
    drain=copy_mat('BE | recessed rail groove','recessed track channel'),
    curb=copy_mat('QB | aged mineral structure','modular mineral curb'),
    foundation=copy_mat('QB | aged mineral structure','mast foundation'),
    guard=copy_mat('RL | weathered zinc steel','galvanized guard'),
    mast=copy_mat('RL | weathered zinc steel','tapered infrastructure mast'))
mats['paint']=painted('BD | worn pale road marking',(.62,.615,.57),0.,.78)
mats['wire']=painted('BD | dark contact metal',(.035,.030,.024),.72,.44)
mats['insulator']=painted('BD | dark glazed insulator',(.042,.039,.034),.02,.26)
for material in mats.values():
    material['evidence_basis']='Bridge orthophoto material class; generic CC0 or inferred surface/fabrication, not an exact local scan.'
for p in P['parts']:
    ob=mesh(p['name'],p['vertices'],p['faces'],p['role'],p['source'],.0018 if p['role']=='curb' else 0)
    ob['construction_batch']='G1_027';ob['source_plan_area_m2']=p['area_m2']
    ob['collision_role']='walkable_candidate' if p['role'].startswith('asphalt') or p['role']=='rail' else 'solid_pending_runtime'

# Combine only repeated guard infill within a short panel. Individual source
# positions and every bar are kept; this avoids thousands of empty objects.
groups={}
for b in P['beams']:
    if 'INFILL_' not in b['name']:
        ob=beam(b['name'],b['a'],b['b'],b['width'],b['depth'],b['role'],b['source']);ob['construction_batch']='G1_027'
        continue
    prefix,index=b['name'].rsplit('_',1);key=prefix+'_'+str(int(index)//12)
    record=groups.setdefault(key,dict(vertices=[],faces=[],source=b['source']))
    a=np.array(b['a']);end=np.array(b['b']);cross=np.array([1.,0,0]);up=np.array([0.,-1,0])
    off=len(record['vertices'])
    record['vertices'].extend([p+cross*b['width']*u/2+up*b['depth']*v/2-O for p in [a,end] for u,v in [(-1,-1),(1,-1),(1,1),(-1,1)]])
    record['faces'].extend([[off+i for i in f] for f in [[3,2,1,0],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]])
for name,p in groups.items():
    ob=mesh(name,p['vertices'],p['faces'],'guard',p['source'],.0006);ob['construction_batch']='G1_027'
for p in P['pipes']:
    ob=sweep(p['name'],p['points'],p['radius'],p['role'],p['source']);ob['construction_batch']='G1_027'

def turned(name,xy,levels,role,source_id):
    sides=20;v=[]
    for z,radius in levels:
        v.extend([[xy[0]+radius*math.cos(i*2*math.pi/sides)-O[0],xy[1]+radius*math.sin(i*2*math.pi/sides)-O[1],z-O[2]] for i in range(sides)])
    f=[list(range(sides-1,-1,-1)),list(range((len(levels)-1)*sides,len(levels)*sides))]
    f.extend([[k*sides+i,k*sides+(i+1)%sides,(k+1)*sides+(i+1)%sides,(k+1)*sides+i] for k in range(len(levels)-1) for i in range(sides)])
    ob=mesh(name,v,f,role,source_id)
    for face in list(ob.data.polygons)[2:]:face.use_smooth=True
    ob['construction_batch']='G1_027';return ob

for m in P['masts']:
    ident=m['id'].split('.')[-1];xy=m['xy'];base=m['base_ln02_m'];top=m['top_ln02_m'];ground=m['ground_interpreted_ln02_m']
    turned('MAST_'+ident,xy,[(base,.165),(max(base,ground)+.4,.15),(top-.06,.075),(top,.072)],'mast',m['id'])
    foundation_top=max(ground+.045,base+.025)
    turned('MAST_FOUNDATION_'+ident,xy,[(ground-.14,.27),(foundation_top,.27)],'foundation',m['id']+'; foundation inferred')
    turned('MAST_FLANGE_'+ident,xy,[(foundation_top-.005,.23),(foundation_top+.018,.23)],'mast',m['id']+'; flange inferred')
    for k in range(4):
        a=math.pi/4+k*math.pi/2;p=np.array(xy)+.19*np.array([math.cos(a),math.sin(a)])
        turned(f'MAST_ANCHOR_{ident}_{k}',p,[(foundation_top+.01,.017),(foundation_top+.038,.017)],'guard',m['id']+'; anchor inferred')
for q in F['clamps']:
    p=q['point'];turned(q['name'],p[:2],[(p[2]-.035,.12),(p[2]+.035,.12)],'guard',q['mast']+'; support collar inferred')
for q in F['insulators']:
    ob=sweep(q['name'],[q['a'],q['b']],.035,'insulator',q['source']);ob['construction_batch']='G1_027'
for q in F['attachments']:
    ob=sweep(q['name'],[q['low'],q['high']],.009,'wire',q['source']);ob['construction_batch']='G1_027'

# Viewpoints are additions. Existing inspection cameras and light remain fixed.
frame=json.loads((R/'derived/bellevue/quaibruecke_connection/build_input.json').read_text())
A=np.array(frame['bridge_anchor']);T=np.array(frame['bridge_along']);N=np.array(frame['bridge_across']);coef=np.array(frame['bridge_deck_coefficients'])
def position(st,d,height):return np.r_[A+T*st+N*d,float(coef@[1,st,st*st,d])+height]-O
for name,start,target in [('BD_QA_WEST',(8,2.2,1.80),(45,7,1.3)),('BD_QA_EAST',(35,2.2,1.80),(-6,8,1.35)),('BD_QA_RAIL',(9,12,1.68),(20,14,0))]:
    data=bpy.data.cameras.new(name);ob=bpy.data.objects.new(name,data);bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].objects.link(ob)
    ob.location=Vector(position(*start));ob.rotation_euler=(Vector(position(*target))-ob.location).to_track_quat('-Z','Y').to_euler();data.lens=35
    ob['review_eye_height_over_surface_m']=1.68
data=bpy.data.cameras.new('BD_QA_JUNCTION');ob=bpy.data.objects.new(data.name,data)
bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].objects.link(ob)
ob.location=(-275.6635096,120.1669612,9.4315968+1.68)
ob.rotation_euler=(Vector((-281.1,121.1,9.15))-ob.location).to_track_quat('-Z','Y').to_euler();data.lens=28
ob['review_eye_height_over_surface_m']=1.68;ob['purpose']='Inspect unresolved road/upper-walk elevation difference, not an accepted entry.'
assert all((bpy.data.objects[name].data.as_pointer() if bpy.data.objects[name].data else None,tuple(bpy.data.objects[name].matrix_basis),bpy.data.objects[name].hide_render,
            tuple(slot.material.as_pointer() if slot.material else None for slot in bpy.data.objects[name].material_slots))==sig for name,sig in old.items())
C['input_sha256']=digest;C['fittings_sha256']=hashlib.sha256((D/'fittings.json').read_bytes()).hexdigest();C['geometry_complete']=True
s['version']='G1_027';s.camera=bpy.data.objects['BD_QA_EAST'];bpy.context.view_layer.update()
(E/'construction.json').write_text(json.dumps(dict(version=s['version'],objects=len(s.objects),new_meshes=len(C.objects),old_objects_unchanged=len(old),
    input_sha256=digest,photo_cut_applied=False,visual_acceptance=False,natural_use_verified=False),indent=2),encoding='utf-8')
print('BRIDGE_DECK_AUTHORED',len(C.objects),len(s.objects),flush=True)
