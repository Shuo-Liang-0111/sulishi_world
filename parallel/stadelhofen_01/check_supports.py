"""Actual mesh contact and continuous door/rail separating-plane checks."""
from sf1_common import *
from mathutils.bvhtree import BVHTree

def evaluated_parts(ob):
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
    verts=[ev.matrix_world@v.co for v in me.vertices];faces=[list(p.vertices) for p in me.polygons]
    root=list(range(len(verts)))
    def find(i):
        while root[i]!=i:root[i]=root[root[i]];i=root[i]
        return i
    for f in faces:
        for i in f[1:]:root[find(i)]=find(f[0])
    groups={}
    for f in faces:groups.setdefault(find(f[0]),[]).append(f)
    result=[]
    for ff in groups.values():
        ix=sorted(set(i for f in ff for i in f));mapping={x:i for i,x in enumerate(ix)}
        vv=[verts[i] for i in ix];tt=[[mapping[i] for i in f] for f in ff]
        result.append(dict(vertices=vv,faces=tt,bvh=BVHTree.FromPolygons(vv,tt,all_triangles=False)))
    ev.to_mesh_clear();return result

def check(C,ground,build_bvh):
    railobs=[o for o in C.objects if o.name.startswith('SF1_STAIR_CONTINUOUS_HANDRAILS')]
    rails=build_bvh(railobs);plates=build_bvh([o for o in C.objects if o.name.startswith('SF1_HANDRAIL_BASEPLATES')])
    bedobs=[o for o in C.objects if o.get('sf1_role')=='anchor_bedding']
    bedtree=build_bvh(bedobs) if bedobs else None
    posts=[];errors=[]
    for ob in C.objects:
        if not ob.name.startswith('SF1_STAIR_HANDRAIL_POSTS'):continue
        for part in evaluated_parts(ob):
            q=np.array([Q(v) for v in part['vertices']]);u,v=q[:,:2].mean(axis=0)
            rail_contacts=len(part['bvh'].overlap(rails));plate_contacts=len(part['bvh'].overlap(plates));supports=[]
            for du,dv in [(0,0),(-.025,-.023),(.025,-.023),(-.025,.023),(.025,.023)]:
                xy=P(u+du,v+dv,12.0);gh,_,_,_=ground.ray_cast(Vector(xy),Vector((0,0,-1)),2)
                bedtop=bedbottom=None;contact=True
                if bedtree is not None and gh is not None:
                    bedtop,_,_,_=bedtree.ray_cast(Vector(xy),Vector((0,0,-1)),2)
                    bedbottom,_,_,_=bedtree.ray_cast(Vector(P(u+du,v+dv,float(gh.z)-.04)),Vector((0,0,1)),.10)
                    contact=bedtop is not None and bedbottom is not None and bedbottom.z<=gh.z+.001 and bedtop.z>=gh.z-.001
                support_z=float(bedtop.z) if bedtop is not None else (float(gh.z) if gh is not None else None)
                ph,_,_,_=plates.ray_cast(Vector(P(u+du,v+dv,support_z-.025 if support_z is not None else 10.0)),Vector((0,0,1)),.08)
                gap=float(ph.z-support_z) if ph is not None and support_z is not None else None
                supports.append(dict(uv=[float(u+du),float(v+dv)],ground_z=float(gh.z) if gh else None,bedding_z_range=[float(bedbottom.z),float(bedtop.z)] if bedtop is not None and bedbottom is not None else None,bedding_intersects_actual_ground=contact,support_z=support_z,baseplate_bottom_z=float(ph.z) if ph else None,gap_m=gap,okay=contact and gap is not None and -.005<=gap<=.004))
            row=dict(uv=[float(u),float(v)],post_z_range=[float(q[:,2].min()),float(q[:,2].max())],actual_post_rail_intersecting_triangles=rail_contacts,actual_post_baseplate_intersecting_triangles=plate_contacts,baseplate_ground_samples=supports,passed=bool(rail_contacts and plate_contacts and all(r['okay'] for r in supports)))
            posts.append(row)
            if not row['passed']:errors.append(row)
    if len(posts)!=8:errors.append(dict(expected_post_count=8,actual=len(posts)))
    # Exact extrema of u(theta) for every evaluated closed leaf vertex. A strict
    # u interval separation from each rail component proves nonintersection for
    # the full 0..95-degree motion with these static rails, not just sample poses.
    railcomponents=[part for ob in C.objects if ob.get('sf1_role')=='handrail' for part in evaluated_parts(ob)]
    railbounds=[]
    for p in railcomponents:
        qq=np.array([Q(v) for v in p['vertices']]);railbounds.append([float(qq[:,0].min()),float(qq[:,0].max())])
    control=bpy.data.objects['SF1_DOOR_CENTRE_CONTROL'];control['open_fraction']=0.;control.update_tag();bpy.context.scene.frame_set(bpy.context.scene.frame_current);bpy.context.view_layer.update()
    groundroles={'walk_surface','walk_support','step_support','step_surface','plinth','anchor_bedding'}
    ground_top=[]
    for ob in C.objects:
        if ob.type!='MESH' or not (ob.get('sf1_role') in groundroles or (ob.get('sf1_role')=='closed_interior' and 'FLOOR' in ob.name)):continue
        ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
        ground_top.extend(float((ev.matrix_world@p.co).z) for p in me.vertices);ev.to_mesh_clear()
    maximum_ground_z=max(ground_top);sweep=[];floorproof=[]
    for side,label in [(-1,'LEFT'),(1,'RIGHT')]:
        pivot=bpy.data.objects['SF1_BAY2_'+label+'_PIVOT'];pivotu=Q(pivot.matrix_world.translation)[0]
        values=[];heights=[];lo,hi=sorted([0,side*math.radians(95)])
        for ob in C.objects:
            if ob.type!='MESH' or ob.parent!=pivot:continue
            for part in evaluated_parts(ob):
                for p in part['vertices']:
                    heights.append(float(p.z))
                    delta=p-pivot.matrix_world.translation;a=float(U[0]*delta.x+U[1]*delta.y);b=float(-U[0]*delta.y+U[1]*delta.x)
                    critical=math.atan2(b,a);angles=[lo,hi]+[critical+k*math.pi for k in range(-2,3) if lo<=critical+k*math.pi<=hi]
                    values.extend([pivotu+a*math.cos(t)+b*math.sin(t) for t in angles])
        interval=[min(values),max(values)];separations=[max(r[0]-interval[1],interval[0]-r[1]) for r in railbounds]
        row=dict(leaf=label,continuous_rotation_degrees=[0,side*95],actual_leaf_swept_u_interval=interval,rail_component_u_intervals=railbounds,minimum_u_separation_m=min(separations),passed=all(v>.01 for v in separations));sweep.append(row)
        if not row['passed']:errors.append(dict(door_rail_sweep=row))
        z_only=abs(pivot.rotation_euler.x)<1e-8 and abs(pivot.rotation_euler.y)<1e-8
        clearance=min(heights)-maximum_ground_z
        floorrow=dict(leaf=label,rotation_axis_is_world_vertical=z_only,minimum_evaluated_leaf_z=min(heights),maximum_all_authored_ground_vertex_z=maximum_ground_z,continuous_vertical_clearance_lower_bound_m=clearance,passed=z_only and clearance>.005)
        floorproof.append(floorrow)
        if not floorrow['passed']:errors.append(dict(continuous_door_floor_clearance=floorrow))
    return dict(posts=posts,continuous_door_rail_separation=sweep,continuous_door_floor_clearance=floorproof,errors=errors,passed=not errors,limits='Continuous separating planes cover the moving leaves versus fixed rails and authored ground only; not a person or the entire scene. Vertical rotation preserves leaf z, so the maximum ground vertex elevation gives a conservative floor-clearance bound.')
