"""Build physical bridge lamps and the photographed southeast flag group.

All new geometry is local, editable and evidence-labelled. Original I3S data,
surveyed mast positions, bridge deck, camera conditions and libraries stay intact.
"""
from pathlib import Path
import hashlib,json,math,shutil,sys
import bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import ROOT,read_path,write_path
from blender_geometry_fingerprint import mesh_digest,object_state

scene=bpy.context.scene
assert scene['version']=='G1_027r3'
assert '44_BRIDGE_FITTINGS' not in bpy.data.collections
target=write_path('native/G1_027r4_bridge_fittings_working.blend')
assert not target.exists() and shutil.disk_usage(ROOT).free>2_000_000_000
spec_path=read_path('derived/bridge_fittings/build_input.json')
spec=json.loads(spec_path.read_text());assert spec['version']=='G1_027r4'
probe_path=read_path('derived/bridge_fittings/source_probe.json')
assert hashlib.sha256(probe_path.read_bytes()).hexdigest()==spec['source_probe_sha256']
probe=json.loads(probe_path.read_text());photos={o['name']:o for o in probe['context']}
baseline=json.loads(read_path('evidence/G1_027r3/checkpoint.json').read_text())
with Path(bpy.data.filepath).open('rb') as stream:
    assert hashlib.file_digest(stream,'sha256').hexdigest()==baseline['native_sha256']
before={o.name:object_state(o) for o in scene.objects}
data_before={o.name:o.data.as_pointer() if o.data else None for o in scene.objects}
original=bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE']
assert len(original.objects)==2039
original_before={o.name:o.data.as_pointer() for o in original.objects}

def asset_paths():
    return dict(images={im.name:str(Path(bpy.path.abspath(im.filepath,library=im.library)).resolve())
                for im in bpy.data.images if im.source=='FILE' and im.filepath and not im.packed_file},
        libraries={lib.name:str(Path(bpy.path.abspath(lib.filepath)).resolve()) for lib in bpy.data.libraries},
        fonts={f.name:str(Path(bpy.path.abspath(f.filepath,library=f.library)).resolve())
               for f in bpy.data.fonts if f.filepath and f.filepath!='<builtin>' and not f.packed_file})
assets=asset_paths()
assert all(Path(p).is_file() for group in assets.values() for p in group.values())
deps=bpy.context.evaluated_depsgraph_get()
for flag in spec['flags']:
    hit,point,normal,face,ob,matrix=scene.ray_cast(deps,Vector((*flag['xy'],15)),Vector((0,0,-1)),distance=8)
    assert hit and ob.name.startswith('UB_GROUND_') and normal.z>.8,(flag['id'],ob.name if hit else None)
    flag['ground_z']=float(point.z);flag['ground_object']=ob.name

# Check exact current face coordinates before performing any local replacement.
for row in spec['photo_removals']:
    ob=bpy.data.objects[row['object']];old=ob.data;ref=photos[ob.name]
    assert [list(p.vertices) for p in old.polygons]==ref['faces']
    assert np.array_equal(np.array([list(ob.matrix_world@v.co) for v in old.vertices]),ref['vertices'])
    assert np.array_equal(np.array([[list(old.uv_layers.active.data[i].uv) for i in p.loop_indices] for p in old.polygons]),ref['uv_faces'])
    assert max(row['face_ids'])<len(old.polygons) and min(row['face_ids'])>=0
    # material_index and sharp_face are built-ins copied through polygons below.
    assert all(a.data_type=='FLOAT2' or a.name.startswith('.') or a.name in {'position','sharp_face','material_index'} for a in old.attributes),ob.name

C=bpy.data.collections.new('44_BRIDGE_FITTINGS')
bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(C)
C['basis']='EWZ points + existing survey masts + source photo mesh; fabrication and flag anchors inferred.'
C['source_input_sha256']=hashlib.sha256(spec_path.read_bytes()).hexdigest()
C['runtime_collision_verified']=False
modifier_types={q.identifier for q in bpy.types.Modifier.bl_rna.properties['type'].enum_items}
assert {'BEVEL','SOLIDIFY'}.issubset(modifier_types)

def material(name,color,metal=0,rough=.5):
    mat=bpy.data.materials.new('BF | '+name);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links
    b=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value=(*color,1)
    b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough
    coord=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value=170;noise.inputs['Detail'].default_value=2
    links.new(coord.outputs['Object'],noise.inputs['Vector'])
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.00015
    links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],b.inputs['Normal'])
    mat['evidence_basis']='Photo-guided material family; inferred microstructure, not sampled paint specification.'
    return mat

mats=dict(housing=material('satin weathered cast aluminium',(.31,.325,.33),.65,.43),
    steel=material('galvanized brackets',(.37,.39,.40),.77,.36),
    rubber=material('dark seal and cable',(.012,.014,.014),0,.73),
    lens=material('prismatic protective diffuser',(.54,.59,.60),.04,.24),
    pole=material('light grey coated flag mast',(.52,.54,.535),.36,.44),
    rope=material('off-white braided halyard',(.49,.48,.435),0,.82),
    socket=material('flush cast socket',(.24,.245,.237),.45,.62))
next(n for n in mats['lens'].node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Transmission Weight'].default_value=.16

def mesh(name,vertices,faces,mat,bevel=0,smooth=False,role='fitting'):
    data=bpy.data.meshes.new('BF_'+name);data.from_pydata(vertices,[],faces);data.update()
    assert not data.validate(clean_customdata=False),name
    assert all(p.area>1e-10 for p in data.polygons),name
    ob=bpy.data.objects.new('BF_'+name,data);C.objects.link(ob);data.materials.append(mat)
    for p in data.polygons:p.use_smooth=smooth
    if bevel:
        mod=ob.modifiers.new('manufactured edge','BEVEL');mod.width=bevel;mod.segments=3
    ob['construction_batch']='G1_027r4';ob['role']=role
    ob['collision_role']='solid_pending_runtime' if role not in ['cloth','rope'] else 'visual_deformable_nonwalkable'
    return ob

def tube(name,a,b,radius,mat,sides=16,radius_end=None,role='fitting'):
    a=np.array(a,float);b=np.array(b,float);axis=b-a;axis/=np.linalg.norm(axis)
    seed=np.array([0.,0.,1.]) if abs(axis[2])<.9 else np.array([1.,0.,0.])
    x=np.cross(axis,seed);x/=np.linalg.norm(x);y=np.cross(axis,x)
    radius_end=radius if radius_end is None else radius_end
    vertices=[(centre+r*(math.cos(i*math.tau/sides)*x+math.sin(i*math.tau/sides)*y)).tolist()
              for centre,r in [(a,radius),(b,radius_end)] for i in range(sides)]
    faces=[list(range(sides-1,-1,-1)),list(range(sides,2*sides))]
    faces += [[i,(i+1)%sides,(i+1)%sides+sides,i+sides] for i in range(sides)]
    return mesh(name,vertices,faces,mat,smooth=True,role=role)

def box(name,centre,size,mat,angle=0,bevel=.006):
    c=np.array(centre);cs=math.cos(angle);sn=math.sin(angle);v=[]
    for z in [-.5,.5]:
        for x,y in [(-.5,-.5),(.5,-.5),(.5,.5),(-.5,.5)]:
            xx=x*size[0];yy=y*size[1];v.append((c+[cs*xx-sn*yy,sn*xx+cs*yy,z*size[2]]).tolist())
    return mesh(name,v,[[3,2,1,0],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]],mat,bevel)

lamp_records=[]
for lamp in spec['lamps']:
    start=set(C.objects);ident=lamp['id'];xy=np.array(lamp['xy']);d=np.array(lamp['direction']);z=lamp['head_z']
    angle=math.atan2(d[1],d[0]);side=np.array([-d[1],d[0]])
    # Two collars and a braced short arm connect the body to the surveyed mast.
    for j,dz in enumerate([-.10,.18]):
        tube(f'L{ident}_COLLAR_{j}',[*xy,z+dz-.026],[*xy,z+dz+.026],.149,mats['steel'],24)
    center=xy+d*.88
    tube(f'L{ident}_ARM',[*(xy+d*.12),z+.12],[*(center-d*.30),z+.02],.035,mats['housing'])
    tube(f'L{ident}_BRACE',[*(xy+d*.12),z-.12],[*(center-d*.42),z+.02],.023,mats['steel'])
    # Layered eight-sided housing, perimeter gasket and inset diffuser, all with thickness.
    length,width,_=lamp['body_dimensions_m']
    outline=np.array([[-.50,-.32],[-.39,-.5],[.37,-.5],[.5,-.25],[.5,.25],[.37,.5],[-.39,.5],[-.5,.32]])*[length,width]
    vertices=[]
    for dz,scale in [(-.066,.92),(.045,1),(.095,.78)]:
        for x,y in outline*scale:vertices.append([*(center+d*x+side*y),z+dz])
    faces=[list(range(7,-1,-1)),list(range(16,24))]
    faces += [[k*8+i,k*8+(i+1)%8,(k+1)*8+(i+1)%8,(k+1)*8+i] for k in range(2) for i in range(8)]
    mesh(f'L{ident}_HOUSING',vertices,faces,mats['housing'],.008)
    box(f'L{ident}_GASKET',[*center,z-.064],[.99,.347,.024],mats['rubber'],angle,.012)
    box(f'L{ident}_DIFFUSER',[*center,z-.081],[.95,.309,.022],mats['lens'],angle,.011)
    for j,t in enumerate([-.36,.36]):
        p=center+d*t
        box(f'L{ident}_RETAINER_{j}',[*p,z-.09],[.021,.333,.014],mats['steel'],angle,.003)
    for j in [-1,1]:
        p=center+side*.188*j-d*.39
        tube(f'L{ident}_LATCH_{j}',[*p,z-.016],[*p,z+.047],.019,mats['steel'],8)
    names=[]
    for ob in set(C.objects)-start:
        ob['source_id']=lamp['official_feature']['id'];ob['mount_mast']=lamp['mast']['id']
        ob['evidence_basis']=lamp['height_basis']+' '+lamp['body_basis']
        ob['light_state']='daylight_off';names.append(ob.name)
    lamp_records.append(dict(id=ident,objects=sorted(names),head_center=[*center,z],mount_xy=xy.tolist(),height_above_mast_foot=z-lamp['mast']['base_ln02_m']+400))

def flag_material(kind):
    mat=material('woven flag '+kind,(.8,.79,.75),0,.79)
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;b=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    b.inputs['Sheen Weight'].default_value=.25
    coord=nodes.new('ShaderNodeTexCoord');sep=nodes.new('ShaderNodeSeparateXYZ');links.new(coord.outputs['UV'],sep.inputs[0])
    def mathnode(op,a,b=None):
        n=nodes.new('ShaderNodeMath');assert op in {v.identifier for v in n.bl_rna.properties['operation'].enum_items};n.operation=op
        for i,x in enumerate([a,b]):
            if x is None:continue
            if isinstance(x,(int,float)):n.inputs[i].default_value=x
            else:links.new(x,n.inputs[i])
        return n.outputs[0]
    u,v=sep.outputs['X'],sep.outputs['Y']
    if kind=='ZH':mask=mathnode('GREATER_THAN',mathnode('ADD',u,v),1.0);base=(.013,.19,.41,1)
    else:
        u=mathnode('ABSOLUTE',mathnode('SUBTRACT',u,.5));v=mathnode('ABSOLUTE',mathnode('SUBTRACT',v,.5))
        horizontal=mathnode('MULTIPLY',mathnode('LESS_THAN',u,.3125),mathnode('LESS_THAN',v,.09375))
        vertical=mathnode('MULTIPLY',mathnode('LESS_THAN',u,.09375),mathnode('LESS_THAN',v,.3125))
        mask=mathnode('MAXIMUM',horizontal,vertical);base=(.50,.013,.020,1)
    mix=nodes.new('ShaderNodeMixRGB');mix.inputs[1].default_value=base;mix.inputs[2].default_value=(.79,.78,.74,1)
    links.new(mask,mix.inputs[0]);links.new(mix.outputs[0],b.inputs['Base Color'])
    return mat
flag_mats={kind:flag_material(kind) for kind in ['ZH','CH']}
flag_records=[]
for flag in spec['flags']:
    start=set(C.objects);ident=flag['id'];xy=np.array(flag['xy']);ground=flag['ground_z'];top=flag['top_z']
    pole=tube(ident+'_POLE',[*xy,ground-.09],[*xy,top],.112,mats['pole'],32,.048)
    pole['placement_basis']=flag['placement_basis'];pole['ground_object']=flag['ground_object']
    tube(ident+'_SOCKET',[*xy,ground-.025],[*xy,ground+.03],.17,mats['socket'],32)
    tube(ident+'_CAP',[*xy,top-.018],[*xy,top+.05],.068,mats['steel'],24,.025)
    box(ident+'_ACCESS_HATCH',[*(xy+np.array([.104,0])),ground+.42],[.015,.095,.24],mats['housing'],bevel=.004)
    # Cloth is a sewn 4m square in rest coordinates, posed as a slack folded sheet.
    n=64;vertices=[];uvs=[];phase=flag['phase'];direction=np.array([-.45,-.893]);side=np.array([.893,-.45])
    for j in range(n+1):
        v=j/n;pos=np.zeros(2)
        for i in range(n+1):
            u=i/n
            if i:
                mid=(i-.5)/n
                angle=1.18*math.sin(math.tau*1.25*mid+.25*math.sin(math.pi*v+phase))+.22*math.sin(math.tau*3*mid+v*2+phase)
                pos+=(direction*math.cos(angle)+side*math.sin(angle))*(4/n)
            ripple=.07*math.sin(math.tau*2*u+v*3+phase)*u
            pxy=xy+direction*.12+pos+side*ripple
            z=top-.14-4*(1-v)-.30*u+.09*math.sin(math.tau*1.1*u+phase)*u
            vertices.append([*pxy,z]);uvs.append([u,v])
    faces=[[j*(n+1)+i,j*(n+1)+i+1,(j+1)*(n+1)+i+1,(j+1)*(n+1)+i] for j in range(n) for i in range(n)]
    cloth=mesh(ident+'_CLOTH',vertices,faces,flag_mats[flag['kind']],smooth=True,role='cloth')
    uv=cloth.data.uv_layers.new(name='Rest cloth square')
    for poly in cloth.data.polygons:
        for loop in poly.loop_indices:uv.data[loop].uv=uvs[cloth.data.loops[loop].vertex_index]
    mod=cloth.modifiers.new('fabric thickness','SOLIDIFY');mod.thickness=.0012
    cloth['rest_cloth_size_m']=[4.,4.];cloth['pose_basis']='Inferred static low-wind cloth pose; no cloth dynamics claim.'
    # Continuous halyard and three hoist ties, physically reaching the mast.
    for side_id,dx in enumerate([-.066,.066]):
        tube(f'{ident}_HALYARD_{side_id}',[*(xy+side*dx+direction*.075),ground+1.15],[*(xy+side*dx+direction*.075),top-.08],.004,mats['rope'],8,role='rope')
    for j,dz in enumerate([-.14,-2.14,-4.14]):
        tube(f'{ident}_HOIST_TIE_{j}',[*(xy+direction*.04),top+dz],[*(xy+direction*.13),top+dz],.009,mats['steel'],8)
    tube(ident+'_CLEAT',[*(xy+direction*.11+side*.05),ground+1.12],[*(xy+direction*.11-side*.05),ground+1.25],.012,mats['steel'],10)
    names=[]
    for ob in set(C.objects)-start:
        ob['source_id']='City official flag instructions, Quaibruecke page 9/2; I3S southeast source cluster'
        ob['evidence_basis']=flag['construction_basis'];ob['display_state_basis']=flag['state_basis'];names.append(ob.name)
    flag_records.append(dict(**flag,objects=sorted(names),cloth=cloth.name))

removed=[]
for row in spec['photo_removals']:
    ob=bpy.data.objects[row['object']];old=ob.data;remove=set(row['face_ids']);kept=[p for p in old.polygons if p.index not in remove]
    data=bpy.data.meshes.new('BRIDGE_FITTING_CUT_'+str(ob['source_node']))
    data.from_pydata([v.co[:] for v in old.vertices],[],[tuple(p.vertices) for p in kept]);data.update()
    for mat in old.materials:data.materials.append(mat)
    data.polygons.foreach_set('material_index',np.array([p.material_index for p in kept],dtype=np.int32))
    data.polygons.foreach_set('use_smooth',np.array([p.use_smooth for p in kept],dtype=np.bool_))
    for old_uv in old.uv_layers:
        new=data.uv_layers.new(name=old_uv.name)
        new.data.foreach_set('uv',np.array([old_uv.data[i].uv[:] for p in kept for i in p.loop_indices],dtype=np.float32).ravel())
        new.active_render=old_uv.active_render;new.active_clone=old_uv.active_clone
    data.uv_layers.active_index=old.uv_layers.active_index
    assert not data.validate(clean_customdata=False)
    ob.data=data;ob['fittings_replacement']='G1_027r4; bounded elevated fixture/flag components only'
    removed.append(dict(object=ob.name,removed_faces=len(remove),after_fingerprint=mesh_digest(data)))

def camera(name,xy,target,lens):
    hit,point,normal,face,floor,matrix=scene.ray_cast(bpy.context.evaluated_depsgraph_get(),Vector((*xy,13.5)),Vector((0,0,-1)),distance=8)
    assert hit and floor.name.startswith('BD_SURFACE_') and normal.z>.9
    eye=[*xy,point.z+1.7]
    data=bpy.data.cameras.new(name);data.lens=lens;data.clip_end=1500
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=eye
    ob.rotation_euler=(Vector(target)-Vector(eye)).to_track_quat('-Z','Y').to_euler()
    ob['construction_batch']='G1_027r4';ob['floor_source']=floor.name;ob['eye_height_m']=1.7;return ob
camera('BF_QA_LAMP',[-311.1,108.7],[-304.1,109.0,14.4],42)
camera('BF_QA_FLAGS',[-295,112.8],[-266.5,115.2,17.0],34)
bpy.context.view_layer.update()
assert all(object_state(bpy.data.objects[name])==state for name,state in before.items())
changed={r['object'] for r in spec['photo_removals']}
assert all((bpy.data.objects[name].data.as_pointer() if bpy.data.objects[name].data else None)==data for name,data in data_before.items() if name not in changed)
assert {o.name:o.data.as_pointer() for o in original.objects}==original_before
assert asset_paths()==assets
record=dict(version=spec['version'],base_version=spec['base_version'],input_sha256=C['source_input_sha256'],
    lamps=lamp_records,flags=flag_records,photo_replacements=removed,source_originals_preserved=True,
    old_authored_geometry_cameras_lighting_unchanged=True,unresolved_official_fixture=37745,
    geometry={o.name:mesh_digest(o.data) for o in C.objects if o.type=='MESH'},
    visual_acceptance=False,natural_use_verified=False,runtime_exported=False)
write_path('evidence/G1_027r4/construction.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
scene['version']=spec['version'];scene['bridge_fittings_file']='derived/bridge_fittings/build_input.json'
scene.camera=bpy.data.objects['BD_QA_EAST']
bpy.context.preferences.filepaths.save_version=0;bpy.context.preferences.filepaths.use_auto_save_temporary_files=False
result=bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True,relative_remap=True)
assert 'FINISHED' in result and asset_paths()==assets
with target.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
baseline.update(version=spec['version'],native=target.relative_to(ROOT).as_posix(),native_bytes=target.stat().st_size,
    native_sha256=digest,objects=len(scene.objects),visual_acceptance=False,natural_use_verified=False,runtime_exported=False,
    native_fresh_reopen_verified=False,asset_paths=assets,bridge_fittings=record,
    local_cleanup_visual_reviewed=False,pre_save_checks=['Exact prior coordinates/UVs checked; originals and other objects unchanged','Same resolved external assets before/after save'])
baseline.pop('visual_review',None)
write_path('evidence/G1_027r4/checkpoint.json').write_text(json.dumps(baseline,indent=2),encoding='utf-8')
print('BRIDGE_FITTINGS_SAVED',json.dumps(dict(native=str(target),sha256=digest,bytes=target.stat().st_size,
    objects=len(scene.objects),added=len(C.objects),lamps=len(lamp_records),flags=len(flag_records),removed_faces=sum(r['removed_faces'] for r in removed))),flush=True)
