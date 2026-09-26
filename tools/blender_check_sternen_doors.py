"""Operate the actual native door and inspect aperture, sweep, and floor support.

No runtime collision or public-interior acceptance is inferred from these rays.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,math,os,sys
import bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path


def set_door_fraction(value):
    control=bpy.data.objects['SG_R8_RESTAURANT_DOOR_CONTROL']
    control['open_fraction']=float(value);control.update_tag()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    bpy.context.view_layer.update()


def verify_doors():
    s=bpy.context.scene;assert s['version'] in ['G1_027r8','G1_027r9']
    data=json.loads(read_path('derived/sternen_grill/build_input.json').read_text())
    A,U,N=(np.array(data[k]) for k in ['A','U','N']);W=data['width'];floor=data['floor_z']
    center=W*2.5/4;finish=floor+.010
    def P(u,v,z):return Vector((*list(A+U*u+N*v),z))
    def Q(point):
        p=np.array(point);return np.r_[(p[:2]-A)@U,(p[:2]-A)@N,p[2]]
    control=bpy.data.objects['SG_R8_RESTAURANT_DOOR_CONTROL']
    assert float(control['open_fraction'])==0. and control['public_runtime_enabled']==False
    parents=[o for o in bpy.data.collections['45_STERNEN_GRILL_FRONTAGES'].objects
             if o.get('interaction_role')=='paired_swing_door_leaf']
    assert len(parents)==2 and all(len(p.children)>=7 for p in parents)
    meshes=[o for p in parents for o in p.children if o.type=='MESH']
    before={o.name:[list(row) for row in o.matrix_world] for o in meshes}
    # All eight upper panes must physically cross their bay center; no hidden
    # center seam survives the removal of the old continuous vertical member.
    transoms=[]
    for side,length in [('FRONT',W),('LANE',data['depth'])]:
        for i in range(4):
            ob=bpy.data.objects[f'SG_R8_{side}_BAY{i+1}_TRANSOM_GLASS']
            points=np.array([Q(ob.matrix_world@v.co) for v in ob.data.vertices])
            along=points[:,0] if side=='FRONT' else -points[:,1]
            span=length/4-.58
            assert abs(np.ptp(along)-(span-.064))<.0001
            assert points[:,2].min()>data['balcony_floor_z']-.67-.47+.03
            transoms.append(ob.name)
    sign=bpy.data.objects['SG_RESTAURANT_LETTERING']
    sign_points=np.array([Q(sign.matrix_world@v.co) for v in sign.data.vertices])
    upper=bpy.data.objects['SG_R8_FRONT_BAY3_TRANSOM_GLASS']
    pane=np.array([Q(upper.matrix_world@v.co) for v in upper.data.vertices])
    assert sign_points[:,0].min()>pane[:,0].min() and sign_points[:,0].max()<pane[:,0].max()
    assert sign_points[:,2].min()>pane[:,2].min() and sign_points[:,2].max()<pane[:,2].max()
    states=[]
    try:
        for fraction in [0.,.25,.5,.75,1.]:
            set_door_fraction(fraction);deps=bpy.context.evaluated_depsgraph_get()
            support=[];angles=[]
            for parent in parents:
                evaluated=parent.evaluated_get(deps)
                angle=evaluated.matrix_world.to_euler().z
                assert abs(angle-parent['open_angle_rad']*fraction)<1e-6
                angles.append(dict(pivot=parent.name,rotation_z=angle))
                # Sample below the lower rail along its actual swept positions.
                rail=next(o for o in parent.children if o.name.endswith('_RAILS'))
                ev=rail.evaluated_get(deps)
                coords=np.array([list(ev.matrix_world@v.co) for v in ev.data.vertices])
                bottom=coords[np.isclose(coords[:,2],coords[:,2].min(),atol=.0001)]
                # Projected rail corners rather than hand-authored path points.
                left=bottom[np.argmin([Q(p)[0] for p in bottom])]
                right=bottom[np.argmax([Q(p)[0] for p in bottom])]
                for t in np.linspace(.03,.97,7):
                    xy=(left*(1-t)+right*t)[:2]
                    start=Vector((*xy,finish+.004))
                    hit,p,n,face,ob,m=s.ray_cast(deps,start,Vector((0,0,-1)),distance=.3)
                    assert hit and n.z>.95 and p.z<=finish+.001,(fraction,parent.name,list(start),ob.name if hit else None)
                    support.append(dict(point=list(p),object=ob.name,leaf_bottom_gap_m=float(coords[:,2].min()-p.z)))
            assert min(p['leaf_bottom_gap_m'] for p in support)>.003
            rays=[]
            for dx in [-.45,-.22,0,.22,.45]:
                for z in [finish+.15,finish+.95,finish+1.82]:
                    hit,p,n,face,ob,m=s.ray_cast(deps,P(center+dx,1.12,z),Vector((*list(-N),0)),distance=3.6)
                    rays.append(dict(u=center+dx,z=z,hit=ob.name if hit else None))
                    if fraction==0:assert hit and ob.name.startswith('SG_R8_FRONT_BAY3_'),rays[-1]
                    if fraction==1:assert not hit,('open central aperture blocked',rays[-1])
            states.append(dict(open_fraction=fraction,pivots=angles,floor_support=support,aperture_rays=rays))
        # The doorway strip must reach both the old pavement and interior floor.
        support=[];deps=bpy.context.evaluated_depsgraph_get()
        for u in np.linspace(center-.45,center+.45,5):
            last=None
            for v in [.45,.12,-.55,-.63,-.67,-.72,-.78,-1.0,-1.7,-2.35]:
                hit,p,n,face,ob,m=s.ray_cast(deps,P(u,v,finish+.045),Vector((0,0,-1)),distance=.20)
                assert hit and n.z>.95 and abs(p.z-finish)<.035,(u,v,ob.name if hit else None)
                if last is not None:assert abs(p.z-last)<.025
                support.append(dict(u=float(u),v=v,object=ob.name,height=p.z));last=p.z
    finally:
        set_door_fraction(0.)
    assert all(np.allclose(before[o.name],o.matrix_world,rtol=0,atol=1e-6) for o in meshes)
    return dict(version=s['version'],transom_panes=transoms,sign_inside_continuous_transom=True,
        operation_states=states,continuous_threshold_probes=support,
        central_open_corridor_width_tested_m=.9,restored_closed=True,
        native_public_interior_accepted=False,runtime_collision_verified=False,natural_use_verified=False)


if __name__=='__main__':
    report=verify_doors()
    native=Path(bpy.data.filepath)
    with native.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    report.update(native=str(native),native_sha256=digest,process_id=os.getpid(),
                  checked_utc=datetime.now(timezone.utc).isoformat())
    write_path(f"evidence/{report['version']}/door_fresh_checks.json").write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('STERNEN_DOOR_OPERATION_CHECKED',json.dumps(dict(states=len(report['operation_states']),
        transoms=len(report['transom_panes']),threshold_probes=len(report['continuous_threshold_probes']),
        restored_closed=report['restored_closed'],natural_use_verified=False)),flush=True)
