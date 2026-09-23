"""Author the source-constrained Riviera promenade, steps and parapets in020r4."""
from pathlib import Path
import json,math,hashlib
import numpy as np
import bpy
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/riviera_quay'
P=json.loads((D/'build_input.json').read_text());s=bpy.context.scene
assert s['version']=='G1_020r4'
assert '33_RIVIERA_QUAY' not in bpy.data.collections
C=bpy.data.collections.new('33_RIVIERA_QUAY');bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(C)
E=R/'evidence/G1_021';E.mkdir(exist_ok=True)
O=np.array(P['origin']);A=np.array(P['anchor']);T=np.array(P['along']);N=np.array(P['across'])

asphalt=bpy.data.materials['asphalt_03'].copy();asphalt.name='RQ | continuous promenade asphalt'
stone=bpy.data.materials['concrete_floor_worn_001'].copy();stone.name='RQ | fine cast stair mineral'
for m in [asphalt,stone]:
    m['evidence_basis']='Existing CC0 material proxy at metric UV scale; material class from aerial/reference. Local surface and wear inferred.'
    for node in list(m.node_tree.nodes):
        if node.type=='DISPLACEMENT':m.node_tree.nodes.remove(node)
    for node in m.node_tree.nodes:
        if node.type=='MAPPING':node.inputs['Scale'].default_value=(1/3,)*3
        if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.72
parapet=stone.copy();parapet.name='RQ | cast parapet mineral'
# Restrained wetting at the exposed low band, continuous across adjacent pieces.
nodes=parapet.node_tree.nodes;links=parapet.node_tree.links
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
base_link=next((l for l in links if l.to_node==bsdf and l.to_socket==bsdf.inputs['Base Color']),None)
if base_link:
    original=base_link.from_socket;links.remove(base_link)
    geom=nodes.new('ShaderNodeNewGeometry');sep=nodes.new('ShaderNodeSeparateXYZ');links.new(geom.outputs['Position'],sep.inputs[0])
    ramp=nodes.new('ShaderNodeMapRange');ramp.inputs['From Min'].default_value=5.75;ramp.inputs['From Max'].default_value=6.27
    ramp.inputs['To Min'].default_value=.59;ramp.inputs['To Max'].default_value=1.;ramp.clamp=True;links.new(sep.outputs['Z'],ramp.inputs['Value'])
    mix=nodes.new('ShaderNodeMixRGB');valid=[e.identifier for e in mix.bl_rna.properties['blend_type'].enum_items]
    assert 'MULTIPLY' in valid;mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
    links.new(original,mix.inputs[1]);links.new(ramp.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],bsdf.inputs['Base Color'])
materials={'asphalt':asphalt,'stair':stone,'stair_stringer':stone,'parapet':parapet}

def build(part):
    # Weld repeated coordinates before beveling: disconnected coplanar triangles
    # must not generate artificial diagonal edge grooves.
    v=[];lookup={};remap=[]
    for point in part['vertices']:
        key=tuple(round(q,6) for q in point)
        if key not in lookup:lookup[key]=len(v);v.append(point)
        remap.append(lookup[key])
    faces=[[remap[i] for i in face] for face in part['faces']]
    me=bpy.data.meshes.new('RQ_'+part['name']);me.from_pydata(v,[],faces);me.update()
    me.materials.append(materials[part['role']]);uv=me.uv_layers.new(name='metre_scale')
    for face in me.polygons:
        axis=int(np.argmax(np.abs(face.normal)));axes=([1,2],[0,2],[0,1])[axis]
        for li in face.loop_indices:
            q=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=(q[axes[0]],q[axes[1]])
    ob=bpy.data.objects.new('RQ_'+part['name'],me);C.objects.link(ob)
    ob['source_id']=part['source'];ob['construction_batch']='G1_021';ob['surface_role']=part['role']
    ob['inferred_height_and_fabrication']=True;ob['quality_status']='working_not_accepted'
    ob['collision_role']='walkable_candidate' if part['role'] in ['asphalt','stair'] else 'solid_pending_runtime'
    ob['source_plan_area_m2']=part['area_m2']
    if part['role'] in ['stair','parapet']:
        bev=ob.modifiers.new('Millimetre mineral edge','BEVEL');bev.width=.0025;bev.segments=3
        choices=[e.identifier for e in bev.bl_rna.properties['limit_method'].enum_items]
        assert 'ANGLE' in choices;bev.limit_method='ANGLE'
        ob.modifiers.new('Face weighted normals','WEIGHTED_NORMAL')
    return ob
for part in P['parts']:build(part)

# Work on local replacement meshes and actual object material overrides. The
# immutable020r2 linked mesh library and2039 photographic originals are retained.
cutpath=R/'derived/bellevue/west_context/riviera_quay_photo_cut.json'
cut=json.loads(cutpath.read_text());old=json.loads((R/s['photo_cut_file']).read_text())
previous={str(r['node']):r for r in old['overrides']}
working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
changed=[]
for rec in cut['overrides']:
    key=str(rec['node'])
    if previous.get(key)==rec:continue
    ob=working[key];mats=[slot.material for slot in ob.material_slots]
    vertices=np.asarray(rec['vertices']).reshape(-1,3);uvs=np.asarray(rec['uv_source_v_unflipped']).reshape(-1,2);uvs[:,1]=1-uvs[:,1]
    me=bpy.data.meshes.new('RQ_CONTEXT_'+key);me.from_pydata(vertices.tolist(),[],np.arange(len(vertices)).reshape(-1,3).tolist());me.update()
    for m in mats:me.materials.append(m)
    uv=me.uv_layers.new(name='source_photo_uv');uv.data.foreach_set('uv',uvs.astype(np.float32).ravel())
    ob.data=me
    for i,m in enumerate(mats):ob.material_slots[i].material=m
    ob['construction_mask']=cut['mask_basis'];changed.append(key)

bpy.context.view_layer.update()
def floor_at(sd):
    pos=A+T*sd[0]+N*sd[1]-O[:2];hits=[]
    for ob in C.objects:
        if ob.get('surface_role') not in ['asphalt','stair']:continue
        hit,p,_,_=ob.ray_cast(Vector((*pos,30)),Vector((0,0,-1)))
        if hit:hits.append(p.z)
    assert hits,('No authored floor',sd)
    return pos,max(hits)
cameras=[('RQ_QA_ALONG',[7,4],[50,7,407.4],32),('RQ_QA_REVERSE',[96,4],[48,7,407.4],32),
         ('RQ_QA_STAIR',[20,8.4],[29,9.8,406.6],36)]
camera_records=[]
for name,sd0,target,lens in cameras:
    pos,floor=floor_at(sd0);targetxy=A+T*target[0]+N*target[1]-O[:2]
    cd=bpy.data.cameras.new(name);co=bpy.data.objects.new(name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(co)
    co.location=(*pos,floor+1.65);co.rotation_euler=(Vector((*targetxy,target[2]-400))-co.location).to_track_quat('-Z','Y').to_euler();cd.lens=lens
    co['eye_height_m']=1.65;co['floor_height_local']=floor;camera_records.append({'camera':name,'ground_local':floor,'eye_height_m':1.65})
s['version']='G1_021';s['photo_cut_file']=str(cutpath.relative_to(R));s.camera=bpy.data.objects['RQ_QA_ALONG']
C['source_scope']='AV145 promenade, AV35398 source-lined staircase and eight adjoining wall footprints'
C['build_input_sha256']=hashlib.sha256((D/'build_input.json').read_bytes()).hexdigest()
C['construction_complete']=True
bpy.context.view_layer.update()
record={'version':s['version'],'base':'G1_020r4','new_objects':len(C.objects),'plan':P['report'],'changed_photo_nodes':changed,
        'original_photo_nodes':len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects),'camera_grounding':camera_records,
        'native_saved':False,'visual_acceptance':False,'runtime_use_verified':False}
(E/'construction.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
for w in bpy.context.window_manager.windows:
    for area in w.screen.areas:
        if area.type=='VIEW_3D':
            region=area.spaces.active.region_3d
            if 'CAMERA' in [e.identifier for e in region.bl_rna.properties['view_perspective'].enum_items]:region.view_perspective='CAMERA'
print(json.dumps(record),flush=True)
