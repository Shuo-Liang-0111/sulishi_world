"""Independent r16 component, support, wall closure and preservation audit."""
from pathlib import Path
import hashlib,json,math,os,sys
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path
from blender_geometry_fingerprint import mesh_digest,object_state


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


s=bpy.context.scene;version=s['version'];assert version=='G1_027r16'
cp=json.loads(read_path(f'evidence/{version}/checkpoint.json').read_text())
assert sha(bpy.data.filepath)==cp['native_sha256']
r=json.loads(read_path(f'evidence/{version}/wallfoot_build_report.json').read_text())
spec_path=read_path(r.get('specification_file','derived/stadelhofen_joint/G1_027r16/construction.json'))
assert sha(spec_path)==r['specification_sha256']
d=json.loads(spec_path.read_text())
A,U,N=[np.asarray(d['frame'][k]) for k in ['A','U','N']]


def P(u,v,z):return Vector((*list(A+U*u+N*v),z))
def Q(a):
    p=np.asarray(a);return np.c_[(p[:,:2]-A)@U,(p[:,:2]-A)@N,p[:,2]]
def inside(p,coords):
    yes=False;x,y=p
    for a,b in zip(coords,coords[1:]+coords[:1]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:yes=not yes
    return yes
_plan_bounds={}
def in_plan(p,plan):
    rings=plan['coordinates']
    key=id(plan)
    if key not in _plan_bounds:
        points=np.asarray(rings[0]);_plan_bounds[key]=(points.min(axis=0)-.00001,points.max(axis=0)+.00001)
    low,high=_plan_bounds[key]
    if p[0]<low[0] or p[0]>high[0] or p[1]<low[1] or p[1]>high[1]:return False
    # The cutter was stored in float32 world coordinates. Its converted edge
    # can be a few micrometres from the nominal local polygon. Boundary faces
    # are part of the planned cut, not protected external samples.
    for ring in rings:
        for a,b in zip(ring,ring[1:]+ring[:1]):
            a=np.asarray(a);b=np.asarray(b);edge=b-a
            if np.dot(edge,edge)<1e-18:continue
            t=np.clip(np.dot(np.asarray(p)-a,edge)/np.dot(edge,edge),0,1)
            if np.linalg.norm(np.asarray(p)-(a+t*edge))<.00001:return True
    return inside(p,rings[0]) and not any(inside(p,rr) for rr in rings[1:])

def in_patch(p):return in_plan(p,d['patch'])


state_differences=[]
for n,state in r['old_object_states'].items():
    current=object_state(bpy.data.objects[n])
    if current!=state:
        state_differences.append({'object':n,'fields':{k:{'before':state[k],'after':current[k]} for k in state if state[k]!=current[k]}})
write_path(f'evidence/{version}/wallfoot_state_readback.json').write_text(json.dumps(state_differences,indent=2),encoding='utf-8')
assert not state_differences,state_differences[:3]
sf1=json.loads(read_path('evidence/G1_027r15/sf1_merge_report.json').read_text())
preserved=0
for n,old in sf1['author_meshes'].items():
    expected=r['changed_old_meshes'][n]['after'] if n in r['changed_old_meshes'] else old
    assert json.loads(json.dumps(mesh_digest(bpy.data.objects[n].data)))==expected,n
    preserved+=n not in r['changed_old_meshes']
for n,expected in r['new_object_meshes'].items():
    assert json.loads(json.dumps(mesh_digest(bpy.data.objects[n].data)))==expected,n
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
if r.get('adjacent_photo_repair_file'):
    from blender_check_wallfoot_context import check as check_context
    check_context()
deps=bpy.context.evaluated_depsgraph_get()


def triangles(name,with_normals=False):
    ob=bpy.data.objects[name];ev=ob.evaluated_get(deps);me=ev.to_mesh(preserve_all_data_layers=True,depsgraph=deps);me.calc_loop_triangles()
    xyz=np.asarray([ev.matrix_world@v.co for v in me.vertices],float)
    indices=np.asarray([t.vertices[:] for t in me.loop_triangles],int)
    tris=xyz[indices]
    normals=None
    if with_normals:
        normal_matrix=np.asarray(ev.matrix_world.to_3x3().inverted().transposed(),float)
        normals=np.asarray([me.corner_normals[i].vector[:] for t in me.loop_triangles for i in t.loops]).reshape(-1,3,3)@normal_matrix.T
        normals/=np.maximum(np.linalg.norm(normals,axis=2,keepdims=True),1e-20)
    ev.to_mesh_clear()
    return tris,normals


def tree(names):
    tt=np.concatenate([triangles(n)[0] for n in names])
    return BVHTree.FromPolygons(tt.reshape(-1,3).tolist(),np.arange(len(tt)*3).reshape(-1,3).tolist(),all_triangles=True)


manifest=json.loads(read_path('web/assets/G1_027r15_current_r01/manifest.json').read_text())
chunk=next(c for c in manifest['chunks'] if c['collection']=='SF1_AUTHOR_ENTRANCE')
assert sha(chunk['expected_file'])==chunk['expected_sha256']
arrays=np.load(chunk['expected_file'],allow_pickle=False)


def old_triangles(name):
    row=next(g for g in chunk['geometry'] if g['name']==name);k=row['key']
    mat=arrays[k+'_matrix'];p=arrays[k+'_positions']@mat[:3,:3].T+mat[:3,3]
    return p[arrays[k+'_triangles']],row,k


retained=[]
for stone in d['stones']:
    original,row,key=old_triangles(stone['old_object'])
    expected=np.delete(original,stone['remove_evaluated_triangle_indices'],axis=0)
    actual,normals=triangles(stone['old_object'],True)
    assert actual.shape==expected.shape
    pe=float(abs(actual-expected).max());assert pe<.00002,(stone['old_object'],'retained positions',pe)
    old_n=arrays[key+'_corner_normals'][arrays[key+'_triangle_loops']]
    assert old_n.shape==original.shape
    old_n=np.delete(old_n,stone['remove_evaluated_triangle_indices'],axis=0)
    # All accepted SF1 slab objects have identity transforms.
    mat=arrays[key+'_matrix'];assert np.max(abs(mat-np.eye(4)))<1e-8
    length=np.linalg.norm(old_n,axis=2);valid=length>1e-12
    assert np.array_equal(valid,np.linalg.norm(normals,axis=2)>1e-12),'Undefined-normal locations changed'
    old_n=old_n[valid]/length[valid,None]
    angle=np.degrees(np.arccos(np.clip((old_n*normals[valid]).sum(axis=1),-1,1)))
    assert float(angle.max())<.05,('Retained stone normals',float(angle.max()))
    retained.append({'object':stone['old_object'],'triangles':len(actual),'max_position_m':pe,'max_normal_angle_deg':float(angle.max()),
                     'unchanged_undefined_normal_corners':int((~valid).sum())})

# Actual original base triangles outside the repair still lie on the new solid.
old_base,_,_=old_triangles('SF1_APRON_CONTINUOUS_SUBBASE')
base_tree=tree(['SF1_APRON_CONTINUOUS_SUBBASE'])
base_mesh=bpy.data.objects['SF1_APRON_CONTINUOUS_SUBBASE'].data
base_bm=bmesh.new();base_bm.from_mesh(base_mesh)
base_nonmanifold=sum(not e.is_manifold for e in base_bm.edges)
base_volume=base_bm.calc_volume(signed=True);base_bm.free()
assert base_nonmanifold==0 and base_volume>0,('Invalid surviving subbase solid',base_nonmanifold,base_volume)
cheek_tree=tree(['SF1_CHEEK_1_MASONRY'])
cut_mesh=d['cutter']
cut_tree=BVHTree.FromPolygons([P(*v) for v in cut_mesh['vertices_uvz']],cut_mesh['faces'],all_triangles=False)
centres=old_base.mean(axis=1);q=Q(centres)
errors=[];buried_points=[]
for xyz,uvz in zip(centres,q):
    if in_patch(uvz[:2]):continue
    in_new_cut=False
    if d.get('base_cut_inside_cheek_m',0) and in_plan(uvz[:2],d['base_cut_plan']):
        cut_bottom,_,_,_=cut_tree.ray_cast(P(*uvz[:2],5),Vector((0,0,1)),10)
        cut_top,_,_,_=cut_tree.ray_cast(P(*uvz[:2],15),Vector((0,0,-1)),10)
        in_new_cut=cut_bottom is not None and cut_top is not None and cut_bottom.z-.00001<=uvz[2]<=cut_top.z+.00001
    if in_new_cut:
        # Every newly exempted original-base sample must really be inside the
        # unchanged solid masonry, not merely labelled hidden in a plan.
        bottom,_,_,_=cheek_tree.ray_cast(P(*uvz[:2],10.0),Vector((0,0,1)),2)
        top,_,_,_=cheek_tree.ray_cast(P(*uvz[:2],11.3),Vector((0,0,-1)),2)
        assert bottom and top and bottom.z<uvz[2]<top.z,('Cut delta outside actual solid cheek',uvz.tolist())
        buried_points.append(uvz.tolist())
        continue
    hit,normal,idx,distance=base_tree.find_nearest(Vector(xyz),.001)
    assert hit is not None,('Lost old base outside patch',uvz.tolist())
    errors.append(float(distance))
assert max(errors)<.00003,('Outside patch base geometry changed',max(errors))
buried_current_surfaces=[]
if d.get('base_cut_inside_cheek_m',0):
    # Original r15 triangle centroids need not land in a 10 mm repair band.
    # Inspect the actual current base surfaces in that band as well. This
    # proves the new recessed boundary is within solid masonry, independently
    # of the exact-preservation check on the coarse original surface samples.
    current_base,_=triangles('SF1_APRON_CONTINUOUS_SUBBASE')
    for xyz,uvz in zip(current_base.mean(axis=1),Q(current_base.mean(axis=1))):
        if in_patch(uvz[:2]) or not in_plan(uvz[:2],d['base_cut_plan']):continue
        low,_,_,_=cheek_tree.ray_cast(P(*uvz[:2],10.0),Vector((0,0,1)),2)
        high,_,_,_=cheek_tree.ray_cast(P(*uvz[:2],11.3),Vector((0,0,-1)),2)
        assert low and high and low.z<uvz[2]<high.z,('Current recessed base outside actual cheek',uvz.tolist())
        buried_current_surfaces.append(uvz.tolist())
    assert buried_current_surfaces, 'No actual recessed boundary samples were checked'
    import runpy
    runpy.run_path(str(Path(__file__).parent/'blender_probe_wallfoot_overlap.py'),
                   init_globals={'REQUIRE_CLEAR_WALL':True},run_name='__main__')

# A same-plane Boolean left thin old base sheets on the exterior termination.
# Inspect actual triangles there, independent of support rays within the stone.
base_triangles,_=triangles('SF1_APRON_CONTINUOUS_SUBBASE')
local_base=Q(base_triangles.reshape(-1,3)).reshape(-1,3,3)
outer_faces=[]
for idx,t in enumerate(local_base):
    centre=t.mean(axis=0)
    if abs(centre[0]-13.25)<.00002 and -.645<centre[1]<.43:
        outer_faces.append(idx)
assert not outer_faces,('Residual old outer base sheets',outer_faces[:20])

support=tree(['SJ_RIGHT_PAVING_BED'])
stone_tree=tree(['SJ_RIGHT_STONE_123','SJ_RIGHT_STONE_132'])
new_surface=tree(['SJ_RIGHT_STONE_123','SJ_RIGHT_STONE_132','SJ_RIGHT_PAVING_JOINTS'])
wall=tree(['SJ_RIGHT_PLINTH_CORE','SJ_RIGHT_PLINTH_COURSE_0','SJ_RIGHT_PLINTH_COURSE_1'])
top_samples=[]
for u in np.linspace(13.161,13.244,16):
    for v in np.linspace(-.645,.43,61):
        p,n,_,_=stone_tree.ray_cast(P(u,v,11.3),Vector((0,0,-1)),.9)
        if p is None:continue
        b,bn,_,_=stone_tree.ray_cast(P(u,v,10.2),Vector((0,0,1)),1.1)
        h,hn,_,_=support.ray_cast(P(u,v,11.3),Vector((0,0,-1)),1.1)
        assert b is not None and h is not None
        thickness=p.z-b.z;gap=b.z-h.z
        assert abs(thickness-.043)<.002 and abs(gap)<.0015,(u,v,thickness,gap)
        assert n.z>.996,('Unexpected steep stone top',u,v,list(n))
        top_samples.append({'u':float(u),'v':float(v),'top_z':float(p.z),'stone_thickness_m':float(thickness),'support_gap_m':float(gap),'normal_z':float(n.z)})
assert len(top_samples)>800
closures=[]
for u in np.linspace(12.80,13.24,9):
    for z in np.linspace(10.89,11.26,26):
        h,n,idx,dist=wall.ray_cast(P(u,-.50,z),Vector((*(-N),0)),.5)
        assert h is not None,('Lower wall opening',u,z)
        closures.append({'u':float(u),'z':float(z),'front_v':float((np.asarray(h)[:2]-A)@N)})
west=[]
for v in np.linspace(-.812,-.754,15):
    low,_,_,_=wall.ray_cast(P(12.78,v,10.0),Vector((0,0,1)),2.)
    high,_,_,_=wall.ray_cast(P(12.78,v,11.27),Vector((0,0,-1)),2.)
    assert low and high and low.z<10.84 and high.z>11.24
    west.append({'v':float(v),'lower_z':float(low.z),'upper_z':float(high.z)})
# Old stairs, plinths, west standing strip and door geometry are hash-identical.
# Exercise the actual drivers in this process and restore saved closed state.
door=bpy.data.objects['SF1_DOOR_CENTRE_CONTROL'];door_states=[]
for f in [0.,.25,.5,.75,1.,0.]:
    door['open_fraction']=f;door.update_tag();s.frame_set(s.frame_current);bpy.context.view_layer.update()
    angles=[bpy.data.objects['SF1_BAY2_'+label+'_PIVOT'].rotation_euler.z for label in ['LEFT','RIGHT']]
    assert all(abs(a-b)<1e-5 for a,b in zip(angles,[-f*math.radians(95),f*math.radians(95)]))
    door_states.append({'fraction':f,'angles':angles})
assert sha(bpy.data.filepath)==cp['native_sha256']
report={'version':version,'native_sha256':cp['native_sha256'],'process_id':os.getpid(),'passed':True,
        'preserved_sf1_meshes':preserved,'old_states_preserved':len(r['old_object_states']),
        'retained_stone_components':retained,'unchanged_base_samples':len(errors),'unchanged_base_max_distance_m':max(errors),
        'old_exterior_base_sheet_triangles':len(outer_faces),
        'surviving_base_nonmanifold_edges':base_nonmanifold,'surviving_base_volume_m3':base_volume,
        'additional_base_samples_in_cut_volume_and_actual_masonry':buried_points,
        'current_recessed_base_surface_samples_inside_actual_masonry':buried_current_surfaces,
        'new_stone_support_samples':top_samples,'wall_closure_samples':closures,'west_old_seam_inside_continuous_wall':west,
        'door_states':door_states,'visual_acceptance':False,'natural_use_verified':False,'sf2_accepted':False,
        'limits':['Lower wall and buried layer construction are inferred.',
                  'Original neighbouring source mesh quality is not certified by this local support audit.',
                  'The existing narrow edge is not designated as an accessible walking route.']}
write_path(f'evidence/{version}/wallfoot_fresh_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('WALLFOOT_CHECKED',json.dumps({k:report[k] for k in ['passed','preserved_sf1_meshes','unchanged_base_samples','unchanged_base_max_distance_m']}),flush=True)
