"""G1_020r1: observed kiosk clearance, supported hatches and material wear.

Footprint, survey roof, floor, camera, light and exposure remain unchanged.
New fabrication and weathering are inferred, not an as-built survey.
"""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import bpy
from mathutils import Matrix, Vector

root=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version']=='G1_020'
col=bpy.data.collections['32_UTOQUAI_RIVIERA_KIOSK']
assert len(col.objects)==410
plan=json.loads((root/'derived/bellevue/utoquai_kiosk/build_input.json').read_text())
floor=plan['floor_local_inferred'];origin=np.array(plan['source']['origin'])
ring=np.array(plan['source']['footprint_ccw_lv95']['coordinates'][0])[:-1]-origin[:2]
steel=bpy.data.materials['UR | brushed stainless work surface']
aluminium=bpy.data.materials['UR | satin aluminium extrusions']
dark=bpy.data.materials['UR | dark appliance metal']
gasket=bpy.data.materials['UR | rubber seals and recess']
before_names={o.name for o in col.objects}
frozen={key:hashlib.sha256(np.array([v.co[:] for v in bpy.data.objects[key].data.vertices]).tobytes()).hexdigest() for key in ['UR_ROOF','UR_FLOOR','UR_FOUNDATION']}
camera_state={o.name:list(o.matrix_world) for o in bpy.data.collections['90_REVIEW_CAMERAS'].objects}
lighting=(scene.view_settings.exposure,tuple(bpy.data.objects['UR_INTERIOR_LIGHT'].location),bpy.data.objects['UR_INTERIOR_LIGHT'].data.energy)

class Edge:
    def __init__(self,i):
        self.a=ring[i];self.b=ring[(i+1)%8];self.length=np.linalg.norm(self.b-self.a)
        self.t=(self.b-self.a)/self.length;self.n=np.array([self.t[1],-self.t[0]])
        self.basis=np.array([[self.t[0],-self.n[0],0],[self.t[1],-self.n[1],0],[0,0,1]])
    def point(self,x,y,z):return np.r_[self.a+self.t*x-self.n*y,floor+z]
edges=[Edge(i) for i in range(8)]

def mesh(name,verts,faces,mat,smooth=False):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update();data.materials.append(mat)
    uv=data.uv_layers.new(name='metre_scale')
    for face in data.polygons:
        face.use_smooth=smooth
        axes=([1,2],[0,2],[0,1])[int(np.argmax(np.abs(face.normal)))]
        for li in face.loop_indices:
            p=data.vertices[data.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]],p[axes[1]])
    ob=bpy.data.objects.new(name,data);col.objects.link(ob)
    ob['source_id']='av_bo_boflaeche_a.20161';ob['construction_batch']='G1_020r1';ob['fabrication_inferred']=True
    ob['collision_role']='solid_pending_runtime'
    return ob

def box(name,e,c,size,mat):
    signs=np.array([[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]])
    v=e.point(*c)+(signs*np.array(size)/2)@e.basis.T
    ob=mesh(name,v.tolist(),[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
    mod=ob.modifiers.new('Folded metal radius','BEVEL');mod.width=.0015;mod.segments=2
    ob.modifiers.new('Fabrication normals','WEIGHTED_NORMAL')
    return ob

def tube(name,a,b,r,mat):
    a,b=np.asarray(a),np.asarray(b);axis=(b-a)/np.linalg.norm(b-a)
    x=np.cross(axis,[0,0,1] if abs(axis[2])<.95 else [1,0,0]);x/=np.linalg.norm(x);y=np.cross(axis,x)
    v=[(c+r*(x*math.cos(t*math.tau/20)+y*math.sin(t*math.tau/20))).tolist() for c in [a,b] for t in range(20)]
    faces=[(k,(k+1)%20,(k+1)%20+20,k+20) for k in range(20)]+[tuple(range(19,-1,-1)),tuple(range(20,40))]
    return mesh(name,v,faces,mat,True)

# Six side stays, mounted to existing jambs and moving hatch rails. The saved
# open state is constructed; runtime extension/contraction is not yet enabled.
stays=[]
for i in [2,3,4]:
    e=edges[i];pivot=bpy.data.objects[f'UR_HATCH_{i}_PIVOT']
    closed=Matrix(e.basis.tolist()).to_4x4();closed.translation=Vector(e.point(0,-.01,2.16))
    motion=pivot.matrix_world@closed.inverted()
    for side,x in enumerate([.09,e.length-.09]):
        a=e.point(x,-.034,1.58);b=np.array(motion@Vector(e.point(x,-.01,1.56)));d=b-a
        prefix=f'UR_STAY_{i}_{side}'
        box(prefix+'_WALL_PLATE',e,(x,-.028,1.58),(.064,.012,.095),aluminium)
        tube(prefix+'_BARREL',a,a+d*.61,.013,dark)
        tube(prefix+'_ROD',a+d*.56,b,.0055,steel)
        for kind,point in [('WALL_PIN',a),('HATCH_PIN',b)]:
            tangent=np.r_[e.t,0];tube(prefix+'_'+kind,point-tangent*.022,point+tangent*.022,.012,aluminium)
        record={'hatch':pivot.name,'wall_anchor_local':a.tolist(),'hatch_anchor_closed_local':e.point(x,-.01,1.56).tolist(),'hatch_anchor_open_local':b.tolist(),'open_length_m':float(np.linalg.norm(d)),'runtime_enabled':False}
        pivot[f'stay_{side}']=json.dumps(record)
        stays.append(record)
    bpy.data.objects[f'UR_HATCH_{i}_INNER_LINING'].data.materials[0]=steel

# Door stops meet the leaf's rear face, retaining the real threshold/opening.
e=edges[1];x0=(e.length-.89)/2;x1=x0+.89
for x in [x0+.003,x1-.003]:box(f'UR_STAFF_GASKET_{x:.3f}',e,(x,.048,1.077),(.020,.012,2.12),gasket)
box('UR_STAFF_GASKET_TOP',e,(e.length/2,.048,2.135),(.89,.012,.020),gasket)

# Exact adjacent-edge offsets replace approximate regular-octagon mitres with
# a2mm fabrication seam. The opening and all cabinet support levels remain.
indices=[2,3,4,6,7];seams=[]
def intersection(a,b,depth):
    p=a.a-a.n*depth;q=b.a-b.n*depth
    t=np.linalg.solve(np.column_stack([a.t,-b.t]),q-p)[0]
    return p+a.t*t
for i in indices:
    e=edges[i];name=f'UR_COUNTER_{i}_WORKTOP' if i in [2,3,4] else f'UR_BACK_WORKTOP_{i}'
    ob=bpy.data.objects[name];m=ob.data;stride=len(m.vertices)//2
    near,far=-.015,.665
    outer=np.array([[.055+near*.414214,near],[e.length-.055-near*.414214,near],[e.length-.055-far*.414214,far],[.055+far*.414214,far]])
    for previous,corner_ids,sign in [(True,[0,3],1),(False,[1,2],-1)]:
        j=(i-1)%8 if previous else (i+1)%8
        if j not in indices:continue
        for k in corner_ids:
            depth=outer[k,1];hit=intersection(e,edges[j],depth)
            outer[k,0]=np.dot(hit-e.a,e.t)+sign*.001
        if not previous:seams.append([i,j])
    for layer in [0,stride]:
        for k,(x,y) in enumerate(outer):
            z=float(m.vertices[layer+k].co.z)-floor
            m.vertices[layer+k].co=e.point(x,y,z)
    m.update()
    for face in m.polygons:
        axes=([1,2],[0,2],[0,1])[int(np.argmax(np.abs(face.normal)))]
        for li in face.loop_indices:
            p=m.vertices[m.loops[li].vertex_index].co;m.uv_layers.active.data[li].uv=(p[axes[0]],p[axes[1]])

# Reuse the existing original one-metre dry-ground stainless maps; don't alter
# shared images or retexture any other scene material using those maps.
nodes,links=steel.node_tree.nodes,steel.node_tree.links
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
coord=nodes.new('ShaderNodeTexCoord')
for kind,file in [('rough','roughness.png'),('normal','normal_gl.png')]:
    image=bpy.data.images.load(str(root/'derived/materials/ground_stainless'/file),check_existing=True)
    spaces={v.identifier for v in image.colorspace_settings.bl_rna.properties['name'].enum_items}
    assert 'Non-Color' in spaces
    image.colorspace_settings.name='Non-Color'
    node=nodes.new('ShaderNodeTexImage');node.image=image;links.new(coord.outputs['UV'],node.inputs['Vector'])
    if kind=='rough':
        scale=nodes.new('ShaderNodeMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=.72
        links.new(node.outputs['Color'],scale.inputs[0]);links.new(scale.outputs[0],bsdf.inputs['Roughness'])
    else:
        normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.6
        links.new(node.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bsdf.inputs['Normal'])
bsdf.inputs['Anisotropic'].default_value=.25
steel['finish_basis']='Original1m fine-ground stainless maps reused; generic wear inference, not local scan.'

# Runoff concentrates under upper seams and at the lower splash zone instead
# of overlaying a uniform dirt noise. Bump remains the restrained paint grain.
old_paint=bpy.data.materials['UR | aged warm pale enamel']
paint=old_paint.copy();paint.name='UR | exterior enamel with seam runoff'
exterior=[]
for ob in col.objects:
    if ob.type!='MESH':continue
    name=ob.name
    outside=(name.startswith('UR_E') and name.endswith(('_LOWER_PANEL','_UPPER_PANEL','_OPAQUE_WALL'))) or name.startswith('UR_STAFF_SIDE_') or name in ['UR_STAFF_DOOR_LEAF','UR_STAFF_TRANSOM_INFILL'] or (name.startswith('UR_HATCH_') and name.endswith('_SKIN'))
    if outside:
        for slot in ob.material_slots:
            if slot.material==old_paint:slot.material=paint;exterior.append(name)
assert len(exterior)>20 and bpy.data.objects['UR_FRIDGE_BODY'].data.materials[0]==old_paint
nodes,links=paint.node_tree.nodes,paint.node_tree.links
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
coord=nodes.new('ShaderNodeTexCoord');sep=nodes.new('ShaderNodeSeparateXYZ');links.new(coord.outputs['Generated'],sep.inputs[0])
def mathnode(op,a,b):
    n=nodes.new('ShaderNodeMath');n.operation=op
    for k,x in enumerate([a,b]):
        if isinstance(x,(int,float)):n.inputs[k].default_value=x
        else:links.new(x,n.inputs[k])
    return n.outputs[0]
top=mathnode('POWER',sep.outputs['Z'],6)
bottom=mathnode('MULTIPLY',mathnode('POWER',mathnode('SUBTRACT',1,sep.outputs['Z']),12),.43)
band=mathnode('MAXIMUM',top,bottom)
stretch=nodes.new('ShaderNodeVectorMath');stretch.operation='MULTIPLY';stretch.inputs[1].default_value=(18,18,1.3);links.new(coord.outputs['Generated'],stretch.inputs[0])
noise=nodes.new('ShaderNodeTexNoise');noise.noise_dimensions='3D';noise.inputs['Scale'].default_value=2;noise.inputs['Detail'].default_value=3;links.new(stretch.outputs[0],noise.inputs['Vector'])
streak=mathnode('MAXIMUM',mathnode('SUBTRACT',mathnode('MULTIPLY',noise.outputs['Fac'],3),1.1),0)
factor=mathnode('MINIMUM',mathnode('MULTIPLY',band,streak),1)
color=nodes.new('ShaderNodeValToRGB');color.color_ramp.elements[0].color=(.59,.61,.575,1);color.color_ramp.elements[1].color=(.265,.282,.234,1)
links.new(factor,color.inputs[0]);links.new(color.outputs['Color'],bsdf.inputs['Base Color'])
rough=mathnode('ADD',.44,mathnode('MULTIPLY',factor,.30));links.new(rough,bsdf.inputs['Roughness'])
paint['finish_basis']='Reference shows seam runoff and worn panels. This inferred directional stain pattern is not copied photography; exposure/light unchanged. Bake equivalent textures before runtime export.'

# Apply the evidence-bounded working-context replacement; untouched nodes and
# immutable reference data keep their datablocks.
path=root/'derived/bellevue/west_context/utoquai_kiosk_clearance_cut.json'
cut=json.loads(path.read_text());basepath=root/scene['photo_cut_file'];base=json.loads(basepath.read_text())
assert cut['base_cut_sha256']==hashlib.sha256(basepath.read_bytes()).hexdigest()
old={str(r['node']):r for r in base['overrides']};working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
originals={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects};changed=[]
for rec in cut['overrides']:
    key=str(rec['node'])
    if old.get(key)==rec:continue
    assert key=='34344'
    ob,src=working[key],originals[key];assert ob.matrix_basis==src.matrix_basis
    v=np.asarray(rec['vertices']).reshape(-1,3);uv=np.asarray(rec['uv_source_v_unflipped']).reshape(-1,2);uv[:,1]=1-uv[:,1]
    data=bpy.data.meshes.new('UR_CLEARANCE_'+key);data.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());data.update()
    for mat in src.data.materials:data.materials.append(mat)
    layer=data.uv_layers.new(name='source_photo_uv');layer.data.foreach_set('uv',uv.astype(np.float32).ravel())
    prior=ob.data;ob.data=data
    if prior.users==0:bpy.data.meshes.remove(prior)
    ob['construction_mask']=cut['mask_basis'];changed.append(key)
assert len(originals)==2039 and changed==['34344']
for key,digest in frozen.items():assert hashlib.sha256(np.array([v.co[:] for v in bpy.data.objects[key].data.vertices]).tobytes()).hexdigest()==digest
assert lighting==(scene.view_settings.exposure,tuple(bpy.data.objects['UR_INTERIOR_LIGHT'].location),bpy.data.objects['UR_INTERIOR_LIGHT'].data.energy)
assert camera_state=={o.name:list(o.matrix_world) for o in bpy.data.collections['90_REVIEW_CAMERAS'].objects}
scene['version']='G1_020r1';scene['photo_cut_file']=str(path.relative_to(root));bpy.context.view_layer.update()
evidence=root/'evidence/G1_020r1';evidence.mkdir(exist_ok=True)
record={'version':scene['version'],'base':'G1_020','added_objects':sorted(o.name for o in col.objects if o.name not in before_names),'objects':len(col.objects),'stays':stays,'counter_seams':seams,'weathered_exterior_panels':exterior,'fridge_coating_unchanged':True,'changed_photo_nodes':changed,'source_photo_nodes_retained':2039,'roof_floor_foundation_vertex_hashes_unchanged':frozen,'lighting_cameras_unchanged':True,'native_saved':False,'runtime_enabled':False,'visual_acceptance':False}
(evidence/'refinement.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({'version':scene['version'],'added_objects':len(record['added_objects']),'photo_nodes':changed,'stays':len(stays),'counter_seams':seams}))
