"""Build the main r16 wall-foot candidate from r15, never editing SF1 archive."""
from pathlib import Path
import hashlib, json, os, shutil, sys
import bpy, bmesh, numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import ROOT, read_path, write_path
from blender_geometry_fingerprint import mesh_digest, object_state


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


s=bpy.context.scene
assert s['version']=='G1_027r15'
spec_path=read_path('derived/stadelhofen_joint/G1_027r16/construction.json')
d=json.loads(spec_path.read_text())
cp=json.loads(read_path('evidence/G1_027r15/checkpoint.json').read_text())
assert sha(bpy.data.filepath)==d['base_native_sha256']==cp['native_sha256']
for r in d['source_files']:assert sha(r['path'])==r['sha256'],r['path']
lease=json.loads(read_path('runtime/coordination/blender_lease.json').read_text(encoding='utf-8-sig'))
assert lease['owner_role']=='main' and not lease['secondary_may_launch']
target=write_path('native/G1_027r16_stadelhofen_wallfoot_candidate_r04.blend')
assert not target.exists() and shutil.disk_usage(ROOT).free>3_000_000_000
A,U,N=[np.asarray(d['frame'][k]) for k in ['A','U','N']]


def P(p):return [*(A+U*p[0]+N*p[1]),p[2]]


C=bpy.data.collections['SF1_AUTHOR_ENTRANCE']
before={o.name:object_state(o) for o in s.objects}
pointers={o.name:o.data.as_pointer() for o in s.objects if o.type=='MESH'}
source_pointers={o.name:o.data.as_pointer() for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
changed={r['old_object'] for r in d['stones']}|{'SF1_APRON_CONTINUOUS_SUBBASE'}
old_meshes={n:mesh_digest(bpy.data.objects[n].data) for n in changed}
made=[]


def mesh_object(name,mesh,material=None,role='construction',bevel=0):
    me=bpy.data.meshes.new(name+'_mesh')
    me.from_pydata([P(p) for p in mesh['vertices_uvz']],[],mesh['faces']);me.update()
    bm=bmesh.new();bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    assert all(e.is_manifold for e in bm.edges),(name,'Open construction solid')
    bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);C.objects.link(ob)
    if material:me.materials.append(bpy.data.materials[material])
    ob['sf1_role']=role;ob['main_revision']='G1_027r16'
    ob['construction_basis']='Main inferred lower wall/paving assembly; dimensions constrained by retained upper wall and actual neighbouring ground.'
    ob['public_runtime_enabled']=False
    if bevel:
        mod=ob.modifiers.new('manufactured_edge_radius','BEVEL');mod.width=bevel;mod.segments=2
        mod.affect='EDGES';mod.limit_method='ANGLE'
        mod=ob.modifiers.new('area_weighted_normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=30
    made.append(name)
    return ob


def remove_evaluated_component(row):
    """Retained evaluated triangles and their normals stay fixed, not rebeveled.

    Applying this mesh's already accepted bevel avoids propagating its weighted
    normal calculation to unrelated disconnected stones when one is removed.
    Original editable modifier input remains in r15 and the frozen SF1 package.
    """
    ob=bpy.data.objects[row['old_object']]
    persistent_materials=[slot.material for slot in ob.material_slots]
    assert all(mat is not None and not mat.is_evaluated for mat in persistent_materials)
    assert mesh_digest(ob.data)['sha256']==row['old_component']['raw_mesh_digest']['sha256']
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get())
    me.calc_loop_triangles();assert len(me.loop_triangles)==row['expected_triangle_count']
    remove=set(row['remove_evaluated_triangle_indices'])
    keep=[t for t in me.loop_triangles if t.index not in remove]
    removed_vertices={v for t in me.loop_triangles if t.index in remove for v in t.vertices}
    assert removed_vertices.isdisjoint({v for t in keep for v in t.vertices})
    old_positions=np.asarray([[me.vertices[i].co[:] for i in t.vertices] for t in keep],float)
    old_normals=np.asarray([[me.corner_normals[i].vector[:] for i in t.loops] for t in keep],float)
    # Preserve original polygons and custom-normal spaces. Rebuilding their
    # triangulation changed shading by 1.21 degrees in candidate02; rejected.
    new=me.copy();new.name=ob.name+'_r16_retained_evaluated'
    bm=bmesh.new();bm.from_mesh(new);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.verts[i] for i in sorted(removed_vertices)],context='VERTS')
    bm.to_mesh(new);bm.free();new.update();new.calc_loop_triangles()
    actual_positions=np.asarray([[new.vertices[i].co[:] for i in t.vertices] for t in new.loop_triangles],float)
    actual_normals=np.asarray([[new.corner_normals[i].vector[:] for i in t.loops] for t in new.loop_triangles],float)
    assert old_positions.shape==actual_positions.shape and np.max(abs(old_positions-actual_positions))<1e-7
    length_old=np.linalg.norm(old_normals,axis=2);length_new=np.linalg.norm(actual_normals,axis=2)
    valid=length_old>1e-12
    assert np.array_equal(valid,length_new>1e-12),'Undefined-normal locations changed'
    unit_old=old_normals[valid]/length_old[valid,None]
    unit_new=actual_normals[valid]/length_new[valid,None]
    angle=np.degrees(np.arccos(np.clip((unit_old*unit_new).sum(axis=1),-1,1)))
    assert float(angle.max())<.05,('Retained polygon-normal spaces changed',ob.name,float(angle.max()))
    new.materials.clear()
    # Evaluated material IDs look valid in this process but are temporary;
    # serializing them yielded null slots in the first candidate's fresh load.
    for mat in persistent_materials:new.materials.append(mat)
    # Exact positions, ordered triangles and preserved loop normals are checked
    # again from the independently reopened file, against sealed r15 arrays.
    report={'object':ob.name,'removed_triangles':sorted(remove),'retained_triangles':len(keep),
            'old_modifiers_applied':[m.type for m in ob.modifiers],
            'preserved_polygon_topology':True,'retained_max_normal_angle_deg':float(angle.max()),
            'unchanged_undefined_normal_corners':int((~valid).sum())}
    ev.to_mesh_clear();ob.modifiers.clear();ob.data=new
    return report


component_changes=[remove_evaluated_component(row) for row in d['stones']]
base=bpy.data.objects['SF1_APRON_CONTINUOUS_SUBBASE']
assert len(base.modifiers)==0
base_xy=np.asarray([(base.matrix_world@v.co)[:2] for v in base.data.vertices])
base_local_u=(base_xy-A)@U;base_local_v=(base_xy-A)@N
base_edge_band=base_local_u[(base_local_v>=-.82001)&(base_local_v<=.44001)]
assert float(base_edge_band.max())<13.25001, 'Exterior cutter overrun would affect an unreviewed region'
cutter=mesh_object('SJ_TEMP_SUBBASE_CUTTER',d['cutter'])
mod=base.modifiers.new('main_wallfoot_patch_only','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
bpy.context.view_layer.objects.active=base;base.select_set(True)
assert 'FINISHED' in bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(cutter,do_unlink=True);made.remove('SJ_TEMP_SUBBASE_CUTTER')
mesh_object('SJ_RIGHT_PAVING_BED',d['bed'],'SF1_MAT_recessed_mineral_joints','walk_support')
mesh_object('SJ_RIGHT_PAVING_JOINTS',d['joint'],'SF1_MAT_recessed_mineral_joints','walk_surface')
for row in d['stones']:
    mesh_object('SJ_RIGHT_STONE_%d'%row['part_index'],row['mesh'],row['material'],'walk_surface',row['edge_radius_m'])
mesh_object('SJ_RIGHT_PLINTH_CORE',d['wall_core'],'SF1_MAT_recessed_mineral_joints','facade')
for row in d['wall_courses']:
    mesh_object(row['name'],row['mesh'],row['material'],'facade',row['edge_radius_m'])

camera_collection=bpy.data.collections.new('SJ_MAIN_QA_CAMERAS');s.collection.children.link(camera_collection)
for name,at,aim,lens in [('SJ_QA_WALLFOOT',(14.00,1.10,12.385),(13.12,-.33,10.99),46),
                         ('SJ_QA_SIDE',(14.35,-.25,12.36),(12.86,-.49,11.16),40)]:
    ca=bpy.data.cameras.new(name);ob=bpy.data.objects.new(name,ca);camera_collection.objects.link(ob)
    ob.location=P(at);ob.rotation_euler=(Vector(P(aim))-ob.location).to_track_quat('-Z','Y').to_euler()
    ca.lens=lens;ca.clip_start=.04;ca.clip_end=500
    ob['purpose']='Wallfoot diagnostic at approximately human eye height; not a validated walking spawn.'

bpy.context.view_layer.update()
assert all(object_state(bpy.data.objects[n])==state for n,state in before.items())
assert all(bpy.data.objects[n].data.as_pointer()==ptr for n,ptr in pointers.items() if n not in changed)
assert source_pointers=={o.name:o.data.as_pointer() for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
report={'version':d['version'],'base_native_sha256':cp['native_sha256'],'specification_sha256':sha(spec_path),
        'process_id':os.getpid(),'changed_old_meshes':{n:{'before':old_meshes[n],'after':mesh_digest(bpy.data.objects[n].data)} for n in changed},
        'removed_stone_components':component_changes,'new_objects':made,
        'new_object_meshes':{n:mesh_digest(bpy.data.objects[n].data) for n in made},
        'old_object_states':before,'unchanged_object_count':len(before)-len(changed),
        'source_photo_preserved':2039,'frozen_sf1_written':False,'sf2_accepted':False,
        'fresh_reopen_verified':False,'visual_acceptance':False,'natural_use_verified':False}
write_path('evidence/G1_027r16/wallfoot_build_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
# Carry the original facts forward, including the old SF1 meshes as a baseline.
# The independent r16 audit applies explicit component exceptions; historical
# reports are not silently changed to say that these meshes never changed.
for name in ['build_report.json','ubs_build_report.json','nearfront_build_report.json','sf1_merge_report.json',
             'bank_shelter_build_report.json','bank_shelter_repair_report.json','bank_curvature_build_report.json','upper_residual_build_report.json']:
    r=json.loads(read_path('evidence/G1_027r15/'+name).read_text())
    r['version']='G1_027r16';r['preserved_report_base']='G1_027r15'
    write_path('evidence/G1_027r16/'+name).write_text(json.dumps(r,indent=2),encoding='utf-8')
s['version']='G1_027r16';s['latest_construction']='Main candidate: continuous Stadelhofen right lower return and whole paving components; SF2 unaccepted.'
bpy.ops.wm.save_as_mainfile(filepath=str(target),check_existing=False,compress=True)
receipt={k:cp[k] for k in ['storage_sharing_applied','required_immutable_libraries','shared_meshes','shared_objects']}
receipt.update(version='G1_027r16',native=str(target),native_sha256=sha(target),native_bytes=target.stat().st_size,objects=len(s.objects),
               native_fresh_reopen_verified=False,visual_acceptance=False,runtime_exported=False,natural_use_verified=False,approved_as_working_native=False)
write_path('evidence/G1_027r16/checkpoint.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WALLFOOT_CANDIDATE_SAVED',json.dumps({k:receipt[k] for k in ['native','native_sha256','native_bytes','objects']}),flush=True)
import runpy
runpy.run_path(str(ROOT/'tools/blender_export_wallfoot_ground.py'),run_name='__main__')
