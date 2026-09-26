"""Independent saved-native checks: actual evaluated solids, contacts and door sweep."""
import sys,os,math,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,'H:/MyWorld/ZurichWorld/tools')
from sf1_common import *
import bmesh
from mathutils.bvhtree import BVHTree
from blender_geometry_fingerprint import mesh_digest

def bvh(objects):
    v=[];f=[];deps=bpy.context.evaluated_depsgraph_get()
    for ob in objects:
        if ob.type!='MESH':continue
        ev=ob.evaluated_get(deps);me=ev.to_mesh();n=len(v)
        v.extend([ev.matrix_world@p.co for p in me.vertices]);f.extend([[n+i for i in p.vertices] for p in me.polygons]);ev.to_mesh_clear()
    return BVHTree.FromPolygons(v,f,all_triangles=False)

def run():
    s=bpy.context.scene;assert s.get('sf1_version')==D['version'];tag=D['version'].split('_')[-1]
    C=bpy.data.collections[D['import_collection']];native=Path(bpy.data.filepath);errors=[];rows=[]
    for ob in C.objects:
        assert ob.name.startswith('SF1_')
        if ob.type!='MESH':continue
        bm=bmesh.new();bm.from_mesh(ob.data)
        row=dict(name=ob.name,vertices=len(bm.verts),faces=len(bm.faces),boundary_edges=sum(e.is_boundary for e in bm.edges),nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),degenerate_faces=sum(f.calc_area()<1e-10 for f in bm.faces),signed_volume_m3=bm.calc_volume(signed=True));bm.free()
        vv=np.array([v.co[:] for v in ob.data.vertices]);row['finite']=bool(np.isfinite(vv).all());rows.append(row)
        if row['nonmanifold_edges'] or row['degenerate_faces'] or not row['finite'] or row['signed_volume_m3']<0:errors.append(row)
    groundroles={'walk_surface','walk_support','step_support','step_surface','plinth'}
    ground=bvh([o for o in C.objects if o.get('sf1_role') in groundroles or (o.get('sf1_role')=='closed_interior' and 'FLOOR' in o.name)])
    route=[]
    for u in [D['width_m']/2-.4,D['width_m']/2,D['width_m']/2+.4]:
        # Probe 5mm inside the finite patch edge; an exact boundary ray is unstable
        # after LV95-local float32 projection, and the external seam is checked below.
        for v in np.linspace(-1.7,7.995,98):
            hit,normal,idx,dist=ground.ray_cast(Vector(P(u,v,12.2)),Vector((0,0,-1)),3)
            route.append(dict(u=u,v=float(v),z=float(hit.z) if hit is not None else None))
            if hit is None:errors.append(dict(missing_route_ground=[u,float(v)]))
    # The measured four-step profile appears as the expected four levels.
    stair=[]
    for v,expected in [(3.02,D['steps'][0]['top_z']),(2.64,D['steps'][1]['top_z']),(2.32,D['steps'][2]['top_z']),(1.9,D['landing_z'])]:
        hit,normal,idx,dist=ground.ray_cast(Vector(P(W/2+.12,v,12.2)),Vector((0,0,-1)),3)
        delta=float(hit.z-expected) if hit is not None else None;stair.append(dict(v=v,expected=expected,actual=float(hit.z) if hit is not None else None,residual=delta))
        if delta is None or abs(delta)>.007:errors.append(dict(stair_mismatch=stair[-1]))
    seam=[]
    for u in np.linspace(D['scope_local']['u'][0]+.005,D['scope_local']['u'][1]-.005,25):
        v=7.995;hit,_,_,_=ground.ray_cast(Vector(P(u,v,12.2)),Vector((0,0,-1)),3)
        seam.append(dict(u=float(u),v=v,support_z=float(hit.z) if hit is not None else None,grade_z=grade(u,v),delta=float(hit.z-grade(u,v)) if hit is not None else None))
        if hit is None or abs(hit.z-grade(u,v))>.006:errors.append(dict(pavement_elevation_self_check=seam[-1]))
    from probe_boundary import run as probe_boundary
    external=probe_boundary()
    if not external['summary']['passed']:errors.append(dict(actual_external_boundary=external['summary']))
    from check_supports import check as check_supports
    supports=check_supports(C,ground,bvh)
    if not supports['passed']:errors.append(dict(handrail_contacts_and_door_separation=supports['errors']))
    from check_returns import check as check_returns
    returns=check_returns(C,bvh)
    if not returns['passed']:errors.append(dict(side_masonry_returns=[r for r in returns['samples'] if not r['blocked_gap']]))
    from check_foundations import check as check_foundations
    foundations=check_foundations(C,bvh)
    if not foundations['passed']:errors.append(dict(plinth_foundations=dict(maximum_gap_m=foundations['maximum_gap_m'],missing=foundations['missing'],failed=sum(not r['passed'] for r in foundations['samples']))))
    from check_left_interface import check as check_left_interface
    left_interface=check_left_interface(C,bvh)
    if not left_interface['passed']:errors.append(dict(left_interface=dict(
        ground=[r for r in left_interface['samples'] if not r['passed']],
        wall_connections=[r for r in left_interface.get('wall_connections',[]) if not r['passed']],
        wall_plinth_join=left_interface.get('wall_plinth_join'))))
    control=bpy.data.objects['SF1_DOOR_CENTRE_CONTROL'];doorchecks=[]
    try:
        for fraction in [0,.25,.5,.75,1.0]:
            control['open_fraction']=fraction;control.update_tag();s.frame_set(s.frame_current);bpy.context.view_layer.update()
            moving=[o for o in C.objects if o.type=='MESH' and o.parent and o.parent.name.startswith('SF1_BAY2_')]
            deps=bpy.context.evaluated_depsgraph_get();clearances=[];corners=[]
            for ob in moving:
                if not ob.name.endswith('LEAF_STILES'):continue
                ev=ob.evaluated_get(deps);me=ev.to_mesh();pts=[ev.matrix_world@p.co for p in me.vertices];ev.to_mesh_clear()
                for p in pts:
                    if p.z>D['landing_z']+.025:continue
                    hit,_,_,_=ground.ray_cast(p+Vector((0,0,.015)),Vector((0,0,-1)),.30)
                    if hit is not None:clearances.append(float(p.z-hit.z));corners.append(list(p))
            solid=bvh([o for o in C.objects if o.type=='MESH' and o.get('sf1_role') not in ['signage']])
            rays=[]
            for off in [-.40,0,.40]:
                for z in [.25,.85,1.55,1.90]:
                    a=Vector(P(W/2+off,1.05,D['landing_z']+z));vec=Vector(P(W/2+off,-.75,D['landing_z']+z))-a
                    hit,_,_,dist=solid.ray_cast(a,vec.normalized(),vec.length)
                    rays.append(dict(offset=off,height=z,blocked=hit is not None,hit_distance=float(dist) if hit is not None else None))
            row=dict(fraction=fraction,leaf_bottom_samples=len(clearances),minimum_floor_clearance=min(clearances) if clearances else None,clearance_points=corners,passage_rays=rays)
            doorchecks.append(row)
            if not clearances or min(clearances)<-.002:errors.append(dict(door_floor_failure=row))
            if fraction==1 and any(r['blocked'] for r in rays):errors.append(dict(open_door_obstructed=row))
    finally:
        control['open_fraction']=0.;control.update_tag();s.frame_set(s.frame_current);bpy.context.view_layer.update()
    inv=json.loads((OUT/'derived/native_context_inventory.json').read_text());changed=set(D['candidate_old_objects']);unchanged=[]
    verified=json.loads((OUT/'derived/verified_source_transforms.json').read_text());expected={r['original_name']:r['state']['matrix_world'] for r in verified['objects']};transforms=[]
    for r in inv['objects']:
        ob=bpy.data.objects[r['local_name']]
        same_transform=[float(x) for row in ob.matrix_world for x in row]==expected[r['original_name']]
        transforms.append(dict(name=r['original_name'],same_as_independently_evaluated_r8=same_transform))
        if not same_transform:errors.append(dict(context_transform_changed=r['original_name']))
        if r['original_name'] in changed:continue
        okay=json.loads(json.dumps(mesh_digest(ob.data)))==r['mesh_digest'];unchanged.append(dict(name=r['original_name'],same=okay))
        if not okay:errors.append(dict(unexpected_context_change=r['original_name']))
    deps=[]
    for lib in bpy.data.libraries:
        path=Path(bpy.path.abspath(lib.filepath));deps.append(dict(kind='library',path=str(path),exists=path.is_file()))
    for im in bpy.data.images:
        if im.source=='FILE' and im.filepath and not im.packed_file:
            path=Path(bpy.path.abspath(im.filepath,library=im.library));deps.append(dict(kind='image',path=str(path),exists=path.is_file()))
    for r in deps:
        if not r['exists']:errors.append(dict(missing_dependency=r))
    # Camera elevation is checked against actual current author/context ground,
    # not an extrapolated grade function. Stepped close cameras use actual stair.
    from probe_boundary import mesh_bvh
    photo,_=mesh_bvh([o for o in bpy.data.objects if o.name.startswith('SF1_REF_CTX_')],True)
    cameras=[]
    for name in ['SF1_QA_ENTRY','SF1_QA_REVERSE','SF1_QA_APPROACH','SF1_QA_CONTEXT','SF1_QA_DOOR_DETAIL','SF1_QA_DOOR_OPEN']:
        ob=bpy.data.objects[name];pos=ob.matrix_world.translation;hits=[]
        for tree in [ground,photo]:
            h,_,_,_=tree.ray_cast(pos,Vector((0,0,-1)),3)
            if h is not None:hits.append(float(h.z))
        actual=pos.z-max(hits) if hits else None
        row=dict(camera=name,position=list(pos),ground_z=max(hits) if hits else None,actual_eye_height_m=actual,within_15mm=actual is not None and abs(actual-1.65)<.015);cameras.append(row)
        if not row['within_15mm']:errors.append(dict(camera_grounding=row))
    result=dict(version=s['sf1_version'],native=str(native),native_sha256=sha(native),process_id=os.getpid(),geometry=rows,ground_route=route,stair_levels=stair,pavement_elevation_self_check=seam,actual_external_boundary=external['summary'],handrail_support_and_door_separation=supports,side_masonry_returns=returns,plinth_foundations=foundations,left_interface=left_interface,camera_grounding=cameras,door_sweep=doorchecks,untouched_context=unchanged,context_transforms=transforms,dependencies=deps,errors=errors,
        passed=not errors,limits=['Door movement and manufacturing inferred, saved closed; no public runtime enabled','Ray tests do not prove full swept-body collision or accessibility','Behind-door depth only a closed shallow reference recess, no station concourse built','Landing and source ground have stated survey/photo uncertainties','Independent visual review and main full-scene integration still required'])
    write(f'evidence/{tag}/fresh_geometry_checks.json',result)
    print('SF1_GEOMETRY_CHECKS',json.dumps(dict(errors=len(errors),authored_meshes=len(rows),route_rays=len(route),door_states=len(doorchecks),untouched_context=len(unchanged))),flush=True)
    if errors:print(json.dumps(errors[:8]),flush=True)
    assert not errors,'See fresh_geometry_checks.json'
    return result

if __name__=='__main__':run()
