"""r7 -> r8: correctly divided transoms, framed leaves, and physical thresholds.

Photographs constrain the front openings and joinery families. Hinge hardware,
the opening mechanism and unsurveyed dimensions are explicit design inference.
Only the third front bay has an operating native demonstration; this does not
open or accept the unsurveyed restaurant as a public runtime interior.
"""
from pathlib import Path
import ast, hashlib, json, math, shutil, sys
import bpy, bmesh, numpy as np
from mathutils import Vector, Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import ROOT,read_path,write_path
from blender_geometry_fingerprint import object_state

s=bpy.context.scene;assert s['version']=='G1_027r7'
version='G1_027r8';target=write_path('native/G1_027r8_sternen_entrance_joinery.blend')
assert not target.exists() and shutil.disk_usage(ROOT).free>3_000_000_000
cp=json.loads(read_path('evidence/G1_027r7/checkpoint.json').read_text())
with Path(bpy.data.filepath).open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==cp['native_sha256']
d=json.loads(read_path('derived/sternen_grill/build_input.json').read_text())
previous=json.loads(read_path('evidence/G1_027r7/build_report.json').read_text())
C=bpy.data.collections['45_STERNEN_GRILL_FRONTAGES']
before={o.name:object_state(o) for o in s.objects}
source_ids={o.name:o.data.as_pointer() for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
photo_ids={o.name:o.data.as_pointer() for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
A,U,N=(np.array(d[k]) for k in ['A','U','N'])
W,D,floor,zf=d['width'],d['depth'],d['floor_z'],d['balcony_floor_z']
groups={};helper_names={'P','Q','side','add','box','tube'}
builder=read_path('tools/blender_build_sternen_grill.py')
helpers=[n for n in ast.parse(builder.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in helper_names]
assert {n.name for n in helpers}==helper_names
exec(compile(ast.Module(body=helpers,type_ignores=[]),'sternen_joinery_helpers','exec'))
metal=bpy.data.materials['SG | dark bronze aluminium frames']
glass=bpy.data.materials['SG | clear double glazing']
steel=bpy.data.materials['SG | r6 brushed counter steel']
stone=bpy.data.materials['SG | grey threshold stone']
rubber=bpy.data.materials['SG | dark tile grout'] if 'SG | dark tile grout' in bpy.data.materials else bpy.data.materials['SG | r6 dark tile grout']

removed=['SG_FRONT_SHOP_FRAME','SG_FRONT_SHOP_GLASS','SG_LANE_SHOP_FRAME','SG_LANE_SHOP_GLASS',
         'SG_FRONT_ENTRANCE_PULLS','SG_FRONT_ENTRANCE_STANDOFF']
assert all(name in C.objects for name in removed)
for name in removed:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)

zhead=zf-.67;zrail=zhead-.47;finish=floor+.010
leaf_low=finish+.008;leaf_high=zrail-.037
controllers=[];leaves=[];transoms=[]
for side_name,length,frame in [('FRONT',W,P),('LANE',D,side)]:
    bay=length/4;ww=bay-.58
    for index in range(4):
        center=(index+.5)*bay;a=center-ww/2;b=center+ww/2
        prefix=f'SG_R8_{side_name}_BAY{index+1}'
        # Outer jambs continue up. The lower meeting stiles stop below the
        # transom rail, so the transom itself is a single sealed pane.
        for x in [a,b]:
            box(prefix+'_FIXED_JAMBS',(x,-.65,(finish+zhead)/2),(.061,.090,zhead-finish),metal,.002,frame)
        for z in [zrail,zhead]:
            box(prefix+'_FIXED_RAILS',(center,-.65,z),(ww,.09,.065),metal,.002,frame)
        box(prefix+'_TRANSOM_GLASS',(center,-.662,(zrail+zhead)/2),(ww-.064,.018,zhead-zrail-.064),glass,0,frame)
        transoms.append(prefix+'_TRANSOM_GLASS')
        for x in [a+.036,b-.036]:
            box(prefix+'_TRANSOM_GASKETS',(x,-.661,(zrail+zhead)/2),(.010,.025,zhead-zrail-.064),rubber,.001,frame)
        for z in [zrail+.035,zhead-.035]:
            box(prefix+'_TRANSOM_GASKETS',(center,-.661,z),(ww-.064,.025,.010),rubber,.001,frame)

        is_door=side_name=='FRONT' and index in [1,2]
        operating=side_name=='FRONT' and index==2
        if is_door:
            # The previous floor and threshold stopped55mm apart. A solid
            # rebate strip bridges them, and the door has no raised lower bar.
            box(prefix+'_THRESHOLD_BRIDGE',(center,-.690,finish-.035),(ww,.210,.070),stone,.002,frame)
        else:
            box(prefix+'_SILL',(center,-.65,finish+.05),(ww,.090,.065),metal,.002,frame)

        if operating:
            control=bpy.data.objects.new('SG_R8_RESTAURANT_DOOR_CONTROL',None);C.objects.link(control)
            control['open_fraction']=0.;control.id_properties_ui('open_fraction').update(min=0.,max=1.,description='Native door operation preview. Runtime public access remains unverified.')
            control['interaction_role']='paired_swing_door_control'
            control['public_runtime_enabled']=False
            control['evidence_basis']='Photographic third-bay location; paired outward mechanism and fabrication are inferred.'
            controllers.append(control.name)

        for side_id,direction in [('LEFT',1),('RIGHT',-1)]:
            x0=a+.039 if direction==1 else center+.004
            x1=center-.004 if direction==1 else b-.039
            low=leaf_low if is_door else finish+.086
            leafprefix=prefix+'_'+side_id
            for x in [x0+.023,x1-.023]:
                box(leafprefix+'_STILES',(x,-.650,(low+leaf_high)/2),(.046,.056,leaf_high-low),metal,.002,frame)
            for z,h in [(low+.040,.080),(leaf_high-.026,.052)]:
                box(leafprefix+'_RAILS',((x0+x1)/2,-.650,z),(x1-x0,.056,h),metal,.002,frame)
            box(leafprefix+'_GLASS',((x0+x1)/2,-.650,(low+.075+leaf_high-.046)/2),
                (x1-x0-.081,.018,leaf_high-low-.121),glass,0,frame)
            for x in [x0+.043,x1-.043]:
                box(leafprefix+'_GASKET',(x,-.652,(low+leaf_high)/2),(.009,.023,leaf_high-low-.09),rubber,.001,frame)
            if direction==1:
                box(leafprefix+'_MEETING_SEAL',(center,-.654,(low+leaf_high)/2),(.008,.018,leaf_high-low-.018),rubber,.001,frame)
            if is_door:
                handle_x=(x1-.135) if direction==1 else (x0+.135)
                for v in [-.553,-.747]:
                    tube(leafprefix+'_PULLS',[frame(handle_x,v,finish+1.01),frame(handle_x,v,finish+1.40)],.012,steel,12)
                    for z in [finish+1.04,finish+1.37]:
                        tube(leafprefix+'_STANDOFFS',[frame(handle_x,-.650,z),frame(handle_x,v,z)],.010,steel,10)
                box(leafprefix+'_BOTTOM_SEAL',((x0+x1)/2,-.650,low+.001),(x1-x0-.016,.034,.007),rubber,.001,frame)
            if operating:
                hinge_u=x0+.010 if direction==1 else x1-.010
                pivot=bpy.data.objects.new(leafprefix+'_PIVOT',None);C.objects.link(pivot)
                pivot.location=P(hinge_u,-.608,finish)
                pivot['interaction_role']='paired_swing_door_leaf'
                pivot['door_control']=control.name;pivot['closed_rotation_z']=0.
                pivot['open_angle_rad']=-direction*math.radians(90)
                pivot['runtime_collision_verified']=False
                curve=pivot.driver_add('rotation_euler',2);driver=curve.driver
                assert 'SCRIPTED' in {i.identifier for i in driver.bl_rna.properties['type'].enum_items}
                driver.type='SCRIPTED'
                variable=driver.variables.new();variable.name='fraction'
                variable.targets[0].id=control;variable.targets[0].data_path='["open_fraction"]'
                driver.expression=f'{pivot["open_angle_rad"]:.16f} * min(1.0,max(0.0,fraction))'
                for z in [finish+.26,finish+1.02,leaf_high-.17]:
                    tube(leafprefix+'_HINGE_KNUCKLES',[frame(hinge_u,-.608,z-.040),frame(hinge_u,-.608,z+.040)],.014,steel,16)
                    box(leafprefix+'_HINGE_PLATES',(hinge_u+direction*.030,-.617,z),(.067,.009,.066),steel,.001,frame)
                    box(prefix+'_FIXED_HINGE_PLATES',(hinge_u-direction*.025,-.612,z),(.042,.012,.065),steel,.001,frame)
                leaves.append(dict(pivot=pivot.name,prefix=leafprefix,hinge_u=hinge_u,hinge_v=-.608,
                    open_angle_rad=pivot['open_angle_rad'],bounds_closed=[x0,x1,low,leaf_high]))

modifier_types={q.identifier for q in bpy.types.Modifier.bl_rna.properties['type'].enum_items}
assert {'BEVEL','WEIGHTED_NORMAL'}.issubset(modifier_types)
bpy.context.view_layer.update();created=[]
for (name,_),g in groups.items():
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(g['v'],[],g['f']);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
    assert not mesh.validate(clean_customdata=False),name
    ob=bpy.data.objects.new(name,mesh);C.objects.link(ob);mesh.materials.append(g['mat'])
    for face in mesh.polygons:face.use_smooth=g['smooth']
    uv=mesh.uv_layers.new(name='metre_scale')
    for face in mesh.polygons:
        axes=[i for i in range(3) if i!=int(np.argmax(abs(np.array(face.normal))))]
        for li in face.loop_indices:
            p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]],p[axes[1]])
    if g['bevel']:
        mod=ob.modifiers.new('material edge','BEVEL');mod.width=g['bevel'];mod.segments=2
        ob.modifiers.new('architectural normals','WEIGHTED_NORMAL')
    for leaf in leaves:
        if name.startswith(leaf['prefix']+'_'):
            parent=bpy.data.objects[leaf['pivot']]
            # Transform actual vertices into the hinge's local frame. Identity
            # child transforms let exporters reproduce the same mechanism.
            mesh.transform(parent.matrix_world.inverted());ob.parent=parent;break
    ob['construction_batch']=version;ob['source_id']='EGID302060199 / AV50487'
    ob['evidence_basis']='Photograph-guided joinery with inferred dimensions and hardware; not a surveyed shop plan.'
    ob['collision_role']='solid_pending_runtime';created.append(ob.name)

# Same existing eye and lens, so open/closed images differ only by door state.
camera=bpy.data.objects['SG_QA_ENTRY'].copy();camera.data=camera.data.copy();camera.name='SG_QA_DOOR_OPEN'
bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(camera)
camera['review_state']='SG_R8_RESTAURANT_DOOR_CONTROL.open_fraction=1; native default remains closed'

bpy.context.view_layer.update()
assert not [name for name,state in before.items() if name not in removed and object_state(bpy.data.objects[name])!=state]
assert source_ids=={o.name:o.data.as_pointer() for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
assert photo_ids=={o.name:o.data.as_pointer() for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects}
s['version']=version;s['latest_construction']='Sternen transoms, paired door joinery, hinge control and closed threshold connection'
report=dict(previous)
report.update(version=version,base_native=cp['native'],base_native_sha256=cp['native_sha256'],
    created_objects=sorted(o.name for o in C.objects),added_objects=created+controllers+[r['pivot'] for r in leaves],
    removed_objects=removed,incremental_photo_cuts=[],photo_meshes_unchanged=True,
    cameras=previous['cameras']+[dict(next(r for r in previous['cameras'] if r['name']=='SG_QA_ENTRY'),name='SG_QA_DOOR_OPEN')],
    joinery=dict(transoms=transoms,control=controllers[0],leaves=leaves,finish_z=finish,
        leaf_bottom_z=leaf_low,leaf_top_z=leaf_high,transom_rail_z=zrail,head_z=zhead,
        preview_camera='SG_QA_DOOR_OPEN',mechanism_inferred=True,default_open_fraction=0.),
    helper_source_sha256=hashlib.sha256(builder.read_bytes()).hexdigest(),
    limits=['Mechanism and hardware dimensions are inferred from the facade category, not surveyed.',
            'Only the third front bay has a native operating preview; the unsurveyed interior is not accepted for public access.',
            'Adjacent scan geometry and wider G1 still require reconstruction.',
            'Native articulation is not runtime collision or natural-use acceptance.'])
write_path(f'evidence/{version}/build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
# Check the actual operated geometry before committing a native checkpoint.
from blender_check_sternen_doors import verify_doors
operation=verify_doors();assert operation['restored_closed']
write_path(f'evidence/{version}/door_author_checks.json').write_text(json.dumps(operation,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(target),check_existing=False,compress=True)
with target.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
receipt={k:cp[k] for k in ['storage_sharing_applied','required_immutable_libraries','shared_meshes','shared_objects']}
receipt.update(version=version,native=str(target),native_sha256=digest,native_bytes=target.stat().st_size,
    objects=len(s.objects),native_fresh_reopen_verified=False,visual_acceptance=False,runtime_exported=False,natural_use_verified=False)
write_path(f'evidence/{version}/checkpoint.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('STERNEN_JOINERY_SAVED',json.dumps({k:receipt[k] for k in ['version','native','native_bytes','native_sha256','objects']}),flush=True)
