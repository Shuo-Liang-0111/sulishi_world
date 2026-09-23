"""Correct diagnosed old-wall closure and public-passage photo headroom."""
from pathlib import Path
import ast,hashlib,json,math
import numpy as np
import bpy
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/quaibruecke_connection'
s=bpy.context.scene;assert s['version']=='G1_023'
P=json.loads((D/'build_input.json').read_text());O=np.array(P['origin'])
C=bpy.data.collections['37_QUAIBRUECKE_CONNECTION']
E=R/'evidence/G1_023r1';E.mkdir(exist_ok=True)
source=ast.parse((R/'tools/blender_build_quaibruecke.py').read_text())
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in {'mesh','beam'}],type_ignores=[]),'qb_mesh_helpers','exec'))
mats={'wall':bpy.data.materials['RL | cast retaining wall'],'girder':bpy.data.materials['QB | grey bridge steel coating']}
changes=[]
for part in json.loads((D/'opening_input.json').read_text())['replacements']:
    old=bpy.data.objects[part['name']];before=len(old.data.polygons)
    temp=mesh('OPENING_TEMP',part['vertices'],part['faces'],'wall',part['source_id'])
    old.data=temp.data;bpy.data.objects.remove(temp,do_unlink=True)
    old['public_underpass_opening']='Source AV39461 crosses AV20735. Cap/XY retained;2.12m lintel clearance inferred.'
    old['inferred_lintel_clearance_m']=2.12
    changes.append(dict(name=old.name,faces_before=before,faces_after=len(old.data.polygons),
                        opening_plan_m2=part['opening_plan_m2'],cap_preserved_ln02_m=part['cap_preserved_ln02_m']))

cutpath=R/'derived/bellevue/west_context/quaibruecke_opening_cut.json';cut=json.loads(cutpath.read_text())
prior=R/s['photo_cut_file'];assert cut['base_cut_sha256']==hashlib.sha256(prior.read_bytes()).hexdigest()
previous={str(q['node']):q for q in json.loads(prior.read_text())['overrides']}
working={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};photo=[]
for rec in cut['overrides']:
    key=str(rec['node'])
    if previous.get(key)==rec:continue
    ob=working[key];materials=[slot.material for slot in ob.material_slots]
    v=np.array(rec['vertices']).reshape(-1,3);uv=np.array(rec['uv_source_v_unflipped']).reshape(-1,2);uv[:,1]=1-uv[:,1]
    me=bpy.data.meshes.new('QB_OPENING_PHOTO_'+key);me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
    for mat in materials:me.materials.append(mat)
    layer=me.uv_layers.new(name='source_photo_uv');layer.data.foreach_set('uv',uv.astype(np.float32).ravel());ob.data=me
    for slot,mat in zip(ob.material_slots,materials):slot.material=mat
    ob['construction_mask']=cut['mask_basis'];photo.append(key)
assert set(photo)==set(cut['opening_changed_nodes'])

# The2015 refurbishment records lighting, but its exact fixture type/count are
#not known. Three ordinary ceiling fittings make normal use credible without
#changing exposure, cameras, sky or adding view-dependent invisible fill lights.
lightcol=bpy.data.collections.new('38_QUAIBRUECKE_LIGHTING')
bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'].children.link(lightcol)
glass=bpy.data.materials.new('QB | linear opal diffuser');glass.use_nodes=True
b=next(n for n in glass.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
b.inputs['Base Color'].default_value=(.73,.74,.70,1);b.inputs['Roughness'].default_value=.44
b.inputs['Emission Color'].default_value=(.89,.91,1,1);b.inputs['Emission Strength'].default_value=2.2
glass['evidence_basis']='Daily lighting provision supported by2015 refurbishment; this housing/type/count is inferred.'
mats['diffuser']=glass
A=np.array(P['bridge_anchor']);T=np.array(P['bridge_along']);N=np.array(P['bridge_across']);coef=np.array(P['bridge_deck_coefficients'])
fixtures=[]
assert 'AREA' in {e.identifier for e in bpy.types.BlendDataLights.bl_rna.functions['new'].parameters['type'].enum_items}
for i,d in enumerate([7.9,14.9,22.0]):
    st=4.9;p=A+T*st+N*d;deck=float(coef@[1,st,st*st,d]);z=deck-.445
    beam(f'CEILING_LIGHT_{i}_HOUSING',[*p-T*.61,z],[*p+T*.61,z],.14,.08,'girder','inferred everyday underpass luminaire',.003)
    beam(f'CEILING_LIGHT_{i}_DIFFUSER',[*p-T*.57,z-.043],[*p+T*.57,z-.043],.10,.014,'diffuser','inferred everyday underpass luminaire',.002)
    light=bpy.data.lights.new(f'QB_CEILING_LIGHT_{i}','AREA');light.energy=18.;light.color=(.89,.91,1.)
    assert 'RECTANGLE' in {e.identifier for e in light.bl_rna.properties['shape'].enum_items}
    light.shape='RECTANGLE';light.size=1.14;light.size_y=.10
    ob=bpy.data.objects.new(light.name,light);lightcol.objects.link(ob);ob.location=(*p-O[:2],z-.052-400)
    ob.rotation_euler.z=math.atan2(T[1],T[0]);ob['inferred_fixture']=True
    fixtures.append(dict(name=ob.name,energy_w=18.,location_local=list(ob.location)))
s['version']='G1_023r1';s['photo_cut_file']=cutpath.relative_to(R).as_posix();bpy.context.view_layer.update()
(E/'portal_revision.json').write_text(json.dumps(dict(old_wall_changes=changes,changed_photo_nodes=photo,
    fixtures=fixtures,existing_camera_exposure_sky_sun_unchanged=True,visual_acceptance=False,natural_use_verified=False),indent=2))
print('PORTAL_REVISION_APPLIED',json.dumps({'walls':changes,'photo_nodes':photo,'fixtures':fixtures}),flush=True)
