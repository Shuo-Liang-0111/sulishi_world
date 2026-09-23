"""Export evaluated duplicates, leaving all native curves and source nodes editable."""
import bpy,json,hashlib,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene;V=scene['version']
sys.path.insert(0,str(ROOT/'tools'))
from runtime_occlusion_cache import RuntimeOcclusion
occlusion=RuntimeOcclusion(ROOT,V)
assert V in ['G1_005r4','G1_006','G1_006r1','G1_006r2','G1_007','G1_007r1','G1_007r2','G1_007r3','G1_007r4','G1_007r5','G1_008r4','G1_008r5','G1_008r8','G1_009','G1_009r1','G1_009r2','G1_009r3','G1_010','G1_010r1','G1_010r2','G1_010r3','G1_011','G1_011r1','G1_011r4','G1_012r4','G1_012r5','G1_013r2','G1_014r2','G1_014r3','G1_015r1','G1_015r2','G1_015r3','G1_016r1','G1_017','G1_017r1','G1_018r3']
building=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION']
background=bpy.data.collections['04_RETAINED_PHOTO_CONTEXT']
source=bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE']
cut=json.loads((ROOT/scene.get('photo_cut_file','derived/bellevue/photo_cut.json')).read_text())
changed={str(x['node']) for x in cut['overrides']}
assert len(source.objects)==2039
for ob in background.objects:
    if str(ob['source_node']) not in changed:
        origin=next(x for x in source.objects if x['source_node']==ob['source_node'])
        # Excluded source collections have unevaluated matrix_world after reopen.
        # Both nodes are unparented: persisted matrix_basis is authoritative.
        assert ob.parent is None and origin.parent is None
        assert ob.data is origin.data and ob.matrix_basis==origin.matrix_basis
temporary=bpy.data.collections.new('TEMP_BELLEVUE_EXPORT_ONLY');scene.collection.children.link(temporary)
created=[];created_meshes=[];deps=bpy.context.evaluated_depsgraph_get();normalized_materials={}

def preserve_legacy_waterline_factor(mesh):
    # Blender's glTF 4.5 factor extractor recognises RGBA Mix, not legacy MixRGB.
    # Replace this equivalent graph on an export-only material copy.
    for index,material in enumerate(list(mesh.materials)):
        if not material or not material.name.endswith('F59 | mineral waterline'):continue
        if material.name not in normalized_materials:
            result=material.copy();result.name='RTFIX_'+material.name
            nodes=result.node_tree.nodes;links=result.node_tree.links
            shader=nodes.get('Principled BSDF');legacy=shader.inputs['Base Color'].links[0].from_node
            assert legacy.type=='MIX_RGB' and legacy.blend_type=='MULTIPLY'
            assert legacy.inputs[0].default_value==1 and not legacy.inputs[2].is_linked
            source=legacy.inputs[1].links[0].from_socket;factor=list(legacy.inputs[2].default_value)
            assert max(abs(a-b) for a,b in zip(factor,[.62,.66,.51,1]))<1e-6
            mix=nodes.new('ShaderNodeMix');mix.data_type='RGBA';mix.blend_type='MULTIPLY'
            next(x for x in mix.inputs if x.name=='Factor' and x.type=='VALUE').default_value=1
            a=next(x for x in mix.inputs if x.name=='A' and x.type=='RGBA')
            b=next(x for x in mix.inputs if x.name=='B' and x.type=='RGBA');b.default_value=factor
            links.new(source,a);links.new(next(x for x in mix.outputs if x.type=='RGBA'),shader.inputs['Base Color'])
            nodes.remove(legacy);result['export_equivalence']='RGBA multiply equals native legacy MixRGB; constant colour factor preserved'
            normalized_materials[material.name]=result
        mesh.materials[index]=normalized_materials[material.name]
def copies(objects):
    mapping={}
    for ob in objects:
        if ob.type not in ['MESH','CURVE','FONT','EMPTY']:continue
        if ob.type=='EMPTY':dup=bpy.data.objects.new('RT_'+ob.name,None)
        else:
            if ob.type=='MESH' and ob.data.shape_keys:
                # Evaluating into a static mesh would silently discard water motion.
                # This native object has no modifiers; copy its exact keys/action.
                assert ob.name=='F59_WATER_SURFACE' and not ob.modifiers
                me=ob.data.copy()
                assert me.shape_keys and me.shape_keys.animation_data.action
            else:
                evaluated=ob.evaluated_get(deps)
                me=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=deps)
            occlusion.apply(ob.name,me)
            if V=='G1_018r3':preserve_legacy_waterline_factor(me)
            created_meshes.append(me);dup=bpy.data.objects.new('RT_'+ob.name,me)
        temporary.objects.link(dup);created.append(dup);mapping[ob]=dup
        for key,value in ob.items():dup[key]=value
        dup['native_object']=ob.name;dup['construction_version']=V
        dup.matrix_world=ob.matrix_world.copy()
    for ob,dup in mapping.items():
        if ob.parent in mapping:
            dup.parent=mapping[ob.parent];dup.matrix_parent_inverse=ob.matrix_parent_inverse.copy();dup.matrix_basis=ob.matrix_basis.copy()
    return list(mapping.values())
def export(objects,path,materials):
    for ob in scene.objects:ob.select_set(False)
    for ob in objects:ob.select_set(True)
    animation_options={}
    if V=='G1_018r3':
        animation_options=dict(export_animations=materials=='EXPORT',export_morph=True,
            export_animation_mode='ACTIVE_ACTIONS',export_frame_range=False,
            export_anim_slide_to_zero=True,
            export_nla_strips_merged_animation_name='F59_CONTINUOUS_WATER',
            export_force_sampling=True,export_frame_step=1)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
      export_extras=True,export_yup=True,export_apply=False,export_materials=materials,
      export_cameras=False,export_lights=False,export_tangents=True,**animation_options)
    return {'file':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
out=ROOT/'web/assets';report={'version':V,'accepted':False,'source_base':'G1_004r2','unedited_source_nodes_verified':len(background.objects)-len(changed)}
try:
    authored=copies(list(building.all_objects))
    report['authored']=export(authored,out/f'{V}_bellevue.glb','EXPORT')
    patch=copies([ob for ob in background.objects if str(ob['source_node']) in changed])
    report['context_patch']=export(patch,out/f'{V}_context_patch.glb','NONE')
    report['context_empty_nodes']=sorted(str(ob['source_node']) for ob in background.objects if str(ob['source_node']) in changed and len(ob.data.vertices)==0)
    report['changed_nodes']=sorted(changed);report['exported_authored_objects']=len(authored)
    report['native_curves_retained']=sum(o.type=='CURVE' for o in building.all_objects)
    report['cameras']={}
    def yup(p):return [p.x,p.z,-p.y]
    report['sun_lights']=[{'name':o.name,'direction_to_sun':yup(o.matrix_basis.to_quaternion()@Vector((0,0,1))),
                          'color':list(o.data.color),'energy':o.data.energy}
                         for o in scene.objects if o.type=='LIGHT' and o.data.type=='SUN']
    report['native_view_settings']={'view_transform':scene.view_settings.view_transform,'exposure':scene.view_settings.exposure,'gamma':scene.view_settings.gamma}
    for ob in bpy.data.collections['90_REVIEW_CAMERAS'].objects:
        if ob.name.startswith(('BE_QA_','HB_QA_')):
            # These review cameras can be excluded from the current viewport.
            # Reopening leaves matrix_world unevaluated; persisted basis is valid.
            assert ob.parent is None and not ob.constraints
            forward=ob.matrix_basis.to_quaternion()@Vector((0,0,-1))
            report['cameras'][ob.name]={'position':yup(ob.location),'target':yup(ob.location+forward*8),'fov':ob.data.angle_y*180/3.141592653589793}
    report['lights']=[]
    for ob in scene.objects:
        if ob.type=='LIGHT' and ob.name.startswith(('BE_INTERIOR_','HB_BAY_','SV_INTERIOR_')):
            report['lights'].append({'name':ob.name,'position':yup(ob.location),'color':list(ob.data.color),'power_W':ob.data.energy,'diameter_m':ob.data.size,'type':'AREA_RECTANGLE' if ob.data.shape=='RECTANGLE' else 'AREA_DISK','width_m':ob.data.size,'height_m':ob.data.size_y if ob.data.shape=='RECTANGLE' else ob.data.size})
    report['door_positions']={o.name:list(o.rotation_euler) for o in building.objects if o.get('interaction_role')=='curved_sliding_door_leaf'}
    report['indirect_occlusion']=occlusion.evidence()
    if V=='G1_018r3':
        state=json.loads((ROOT/'derived/bellevue/fountain59'/V/'water_state.json').read_text())
        report['fountain_water']={**state,'animation_clip':'F59_CONTINUOUS_WATER',
            'runtime_implemented':False,'natural_use_accepted':False,
            'limitation':'Native water deformation approximation; no fluid solver or water-contact interaction yet.'}
finally:
    for ob in created:bpy.data.objects.remove(ob,do_unlink=True)
    for me in created_meshes:
        if me.users==0:bpy.data.meshes.remove(me)
    bpy.data.collections.remove(temporary)
evidence=ROOT/'evidence'/V;evidence.mkdir(exist_ok=True)
(evidence/'export.json').write_text(json.dumps(report,indent=2))
(out/f'{V}_bellevue.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
