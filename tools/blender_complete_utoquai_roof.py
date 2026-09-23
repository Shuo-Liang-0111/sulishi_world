"""Complete the unsaved020r1 fabrication pass; roof cowl is explicit inference."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import bpy

root=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version']=='G1_020r1' and 'UR_ROOF_EXHAUST_COWL' not in bpy.data.objects
col=bpy.data.collections['32_UTOQUAI_RIVIERA_KIOSK']
plan=json.loads((root/'derived/bellevue/utoquai_kiosk/build_input.json').read_text())
roof=plan['roof_local'];floor=plan['floor_local_inferred']
duct=bpy.data.objects['UR_EXTRACT_DUCT']
xy=np.array([(duct.matrix_world@v.co)[:] for v in duct.data.vertices]).mean(0)[:2]
mat=bpy.data.materials['UR | satin aluminium extrusions'].copy();mat.name='UR | rooftop exhaust galvanised sheet'
bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
bsdf.inputs['Base Color'].default_value=(.42,.45,.44,1)
for link in list(bsdf.inputs['Roughness'].links):mat.node_tree.links.remove(link)
bsdf.inputs['Roughness'].default_value=.48
mat['basis']='Photo supports a rooftop ventilator silhouette. Dimensions, connections and sheet finish inferred.'

def lathe(name,centre,profile,reverse=False):
    n=64;v=[];rings=[];faces=[]
    for r,z in profile:
        ring=[]
        for k in range(1 if r==0 else n):
            ring.append(len(v));v.append([*(centre+[r*math.cos(k*math.tau/n),r*math.sin(k*math.tau/n)]),z])
        rings.append(ring)
    for a,b in zip(rings,rings[1:]):
        for k in range(n):
            if len(a)==1:face=(a[0],b[(k+1)%n],b[k])
            elif len(b)==1:face=(a[k],a[(k+1)%n],b[0])
            else:face=(a[k],a[(k+1)%n],b[(k+1)%n],b[k])
            faces.append(tuple(reversed(face)) if reverse else face)
    data=bpy.data.meshes.new(name);data.from_pydata(v,[],faces);data.materials.append(mat);data.update()
    uv=data.uv_layers.new(name='metre_scale')
    for p in data.polygons:
        p.use_smooth=True
        for li in p.loop_indices:
            q=data.vertices[data.loops[li].vertex_index].co;uv.data[li].uv=(q.x,q.z)
    ob=bpy.data.objects.new(name,data);col.objects.link(ob)
    ob['source_id']='av_bo_boflaeche_a.20161';ob['construction_batch']='G1_020r1';ob['fabrication_inferred']=True;ob['collision_role']='solid_pending_runtime'
    return ob
lathe('UR_ROOF_EXHAUST_PIPE',xy,[(.156,floor+2.49),(.16,floor+2.49),(.16,roof+.205),(.156,roof+.205),(.156,floor+2.49)])
lathe('UR_ROOF_EXHAUST_FLASHING',xy,[(.16,roof+.003),(.235,roof+.003),(.235,roof+.009),(.175,roof+.048),(.16,roof+.048),(.16,roof+.003)])
profile=[(0,.355),(.12,.351),(.22,.331),(.245,.285),(.255,.245),(.255,.225),(.252,.225),(.252,.244),(.242,.283),(.218,.328),(.119,.348),(0,.352)]
lathe('UR_ROOF_EXHAUST_COWL',xy,[(r,roof+z) for r,z in profile],reverse=True)
for j in range(3):
    angle=j*math.tau/3;centre=xy+np.array([math.cos(angle),math.sin(angle)])*.192
    lathe(f'UR_ROOF_COWL_STAY_{j}',centre,[(0,roof+.009),(.006,roof+.009),(.006,roof+.337),(0,roof+.337)])

path=root/'derived/bellevue/west_context/utoquai_kiosk_roof_cut.json';cut=json.loads(path.read_text())
basepath=root/scene['photo_cut_file'];base=json.loads(basepath.read_text());assert hashlib.sha256(basepath.read_bytes()).hexdigest()==cut['base_cut_sha256']
old={str(q['node']):q for q in base['overrides']}
work={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
refs={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
changed=[]
for q in cut['overrides']:
    key=str(q['node'])
    if old.get(key)==q:continue
    assert key=='34344';ob=work[key];src=refs[key];assert ob.matrix_basis==src.matrix_basis
    verts=np.array(q['vertices']).reshape(-1,3);uvs=np.array(q['uv_source_v_unflipped']).reshape(-1,2);uvs[:,1]=1-uvs[:,1]
    data=bpy.data.meshes.new('UR_ROOF_CONTEXT_'+key);data.from_pydata(verts.tolist(),[],np.arange(len(verts)).reshape(-1,3).tolist());data.update()
    for m in src.data.materials:data.materials.append(m)
    data.uv_layers.new(name='source_photo_uv').data.foreach_set('uv',uvs.astype(np.float32).ravel())
    previous=ob.data;ob.data=data
    if previous.users==0:bpy.data.meshes.remove(previous)
    ob['construction_mask']=cut['mask_basis'];changed.append(key)
assert changed==['34344'] and len(refs)==2039
scene['photo_cut_file']=str(path.relative_to(root));bpy.context.view_layer.update()
p=root/'evidence/G1_020r1/refinement.json';rec=json.loads(p.read_text())
rec['roof_completion']={'new_objects':6,'pipe_xy_local':xy.tolist(),'cowl_top_ln02_m':roof+.355+400,'basis':'Visible reference roof ventilator, inferred fabrication. Source roof slab remains411.255m; this separate rooftop fixture is not a change to survey roof height.','photo_cut':str(path.relative_to(root)),'actual_viewport_before_clearance':True}
rec['objects']=len(col.objects);p.write_text(json.dumps(rec,indent=2),encoding='utf-8')
print(json.dumps(rec['roof_completion']))
