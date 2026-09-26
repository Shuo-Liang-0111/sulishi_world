"""Actual low-slope ground and clear standing volume beside the west plinth."""
from sf1_common import *

def wall_join_check(C,build_bvh):
    body=build_bvh([o for o in C.objects if o.type=='MESH' and o.get('sf1_role') in {'facade','plinth'}])
    rows=[]
    for u in [-1.28,-1.26,-1.24,-1.22]:
        for z in [10.8,10.9,11.0,11.1,11.2]:
            p,_,_,dist=body.ray_cast(Vector(P(u,-.2,z)),Vector((*(-N),0)),.75)
            rows.append(dict(u=u,z=z,hit_v=float(Q(p)[1]) if p is not None else None,
                passed=p is not None))
    return dict(samples=rows,passed=all(r['passed'] for r in rows),
        scope='Twenty horizontal rays across the visually observed 77mm wall-foot/plinth corner joint; actual author solids, not retained photographic cover.')

def check(C, build_bvh):
    local=D.get('left_interface_ground')
    if not local:return dict(applicable=False,passed=True,samples=[])
    roles={'walk_surface','walk_support','step_support','step_surface','plinth'}
    author=[o for o in C.objects if o.type=='MESH' and o.get('sf1_role') in roles]
    photo=[o for o in bpy.data.objects if o.name.startswith('SF1_REF_CTX_')]
    floor=build_bvh(author+photo)
    solid=build_bvh([o for o in C.objects if o.type=='MESH']+photo)
    rows=[];cc=local['coefficients']
    for u in np.linspace(-3.44,-1.29,23):
        for v in np.linspace(-.35,1.46,20):
            p,n,_,_=floor.ray_cast(Vector(P(u,v,11.35)),Vector((0,0,-1)),1.2)
            expected=cc[0]+cc[1]*u+cc[2]*v
            delta=float(p.z-expected) if p is not None else None
            obstruction=None
            if p is not None:
                h,_,_,dist=solid.ray_cast(p+Vector((0,0,.075)),Vector((0,0,1)),1.875)
                if h is not None:obstruction=float(dist)
            passed=bool(p is not None and n.z>=.98 and abs(delta)<.022 and obstruction is None)
            rows.append(dict(uv=[float(u),float(v)],actual_z=float(p.z) if p is not None else None,
                normal_z=float(n.z) if n is not None else None,
                relative_flat_ground_plane_delta_m=delta,
                overhead_obstruction_m=obstruction,passed=passed))
    wall_rows=[]
    if bpy.data.objects.get('SF1_LEFT_WALL_FOOT_CONNECTION'):
        wall=build_bvh([bpy.data.objects['SF1_LEFT_WALL_FOOT_CONNECTION']])
        retained=build_bvh(photo)
        bed=build_bvh([bpy.data.objects['SF1_APRON_CONTINUOUS_SUBBASE']])
        for u in np.linspace(-3.49,-1.31,45):
            origin=Vector(P(u,-.30,11.403));direction=Vector((*(-N),0))
            h,_,_,_=wall.ray_cast(origin,direction,1.4)
            r,_,_,_=retained.ray_cast(origin,direction,1.4)
            overlap=float(Q(h)[1]-Q(r)[1]) if h is not None and r is not None else None
            uv=[u,-.80]
            bottom,_,_,_=wall.ray_cast(Vector(P(*uv,9.8)),Vector((0,0,1)),1.5)
            g,_,_,_=bed.ray_cast(Vector(P(*uv,11.3)),Vector((0,0,-1)),1.5)
            support=float(bottom.z-g.z) if bottom is not None and g is not None else None
            wall_rows.append(dict(u=float(u),author_minus_retained_front_v_m=overlap,
                wall_bottom_minus_ground_bed_m=support,
                passed=bool(overlap is not None and -.002<=overlap<.022
                    and support is not None and support<=.004)))
    join=wall_join_check(C,build_bvh)
    return dict(applicable=True,samples=rows,wall_connections=wall_rows,wall_plinth_join=join,
        passed=bool(all(r['passed'] for r in rows) and len(wall_rows)==45 and all(r['passed'] for r in wall_rows) and join['passed']),
        scope='Actual author and retained context ground beside west plinth; 75mm-to-1.95m standing band. This diagnostic detects the old 27-degree false scan ramp and does not establish public accessibility.')
