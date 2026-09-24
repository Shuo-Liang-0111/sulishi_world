"""Ray-check the prospective027r1 patch before mutation, or its actual meshes.

Uses saved topology and BVH intersections, independently of the fitting code.
"""
from pathlib import Path
import hashlib,json,sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/bridge_grade'
s=bpy.context.scene;assert s['version'] in ['G1_027','G1_027r1']
prospective=s['version']=='G1_027'
patch=json.loads((D/'027r1_patch.json').read_text());arrays=np.load(D/'027r1_vertex_patch.npz')
old_arrays=np.load(D/'027_target_vertices.npz')
assert hashlib.sha256((D/'027r1_vertex_patch.npz').read_bytes()).hexdigest()==patch['patch_sha256']
for name,digest in patch['inputs'].items():
    assert hashlib.sha256((D/name).read_bytes()).hexdigest()==digest,name
if not prospective:
    sys.path.insert(0,str(R/'tools'))
    from blender_geometry_fingerprint import mesh_digest
    built=json.loads((R/'evidence/G1_027r1/construction.json').read_text())
    for row in built['after_fingerprints']:
        actual=json.loads(json.dumps(mesh_digest(bpy.data.objects[row['name']].data)))
        assert actual==row['mesh_fingerprint'],row['name']
byname={q['name']:q['key'] for q in patch['objects']}
def vertices(ob):
    if prospective and ob.name in byname:return arrays[byname[ob.name]]
    return np.array([ob.matrix_world@v.co for v in ob.data.vertices])
def bvh(objects):
    v=[];f=[]
    for ob in objects:
        start=len(v);v.extend(Vector(p) for p in vertices(ob))
        f.extend([[start+i for i in face.vertices] for face in ob.data.polygons])
    return BVHTree.FromPolygons(v,f,all_triangles=False)
def cast(tree,xy):
    hit,_,_,_=tree.ray_cast(Vector((*xy,30)),Vector((0,0,-1)),30)
    assert hit is not None,xy
    return float(hit.z)
C=bpy.data.collections['43_BRIDGE_DECK']
new=bvh([o for o in C.objects if o.get('surface_role') in ['asphalt_walk','asphalt_road','asphalt_track','rail']])
joins=json.loads((R/'derived/bellevue/bridge_deck/join_probes.json').read_text())
old=bvh([bpy.data.objects[n] for n in joins['old_objects']])
rows=[];same=[];transitions=[]
for row in joins['samples']:
    a=cast(new,row['new_xy']);b=cast(old,row['old_xy']);item=dict(**row,new_z=a,old_z=b,difference_m=a-b)
    rows.append(item)
    (same if row['old_raised']==row['new_raised'] else transitions).append(abs(a-b))
slopes=[];steep=[]
for name in byname:
    ob=bpy.data.objects[name]
    if ob.get('surface_role') not in ['road_asphalt','road_concrete','road_joint','asphalt_walk','asphalt_road','asphalt_track']:continue
    ob.data.calc_loop_triangles();v=vertices(ob);indices=np.array([q.vertices[:] for q in ob.data.loop_triangles]);t=v[indices]
    # Closed paving objects also have vertical side walls. Identify original
    # upper faces before applying a patch, rather than accepting bad new slopes.
    original=np.array([ob.matrix_world@v.co for v in ob.data.vertices])
    if not prospective and name in byname:
        original=old_arrays[byname[name]]
    before=original[indices];normal=np.cross(before[:,1]-before[:,0],before[:,2]-before[:,0])
    n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);ok=(normal[:,2]>.85*np.linalg.norm(normal,axis=1))&(normal[:,2]>1e-5)
    if ok.any():
        values=np.linalg.norm(n[ok,:2],axis=1)/n[ok,2];slopes.extend(values.tolist())
        for i,value in zip(np.flatnonzero(ok),values):
            if value>.25:steep.append(dict(name=name,triangle=int(i),new_slope=float(value),
                old_slope=float(np.linalg.norm(normal[i,:2])/normal[i,2]),area_xy=float(normal[i,2]/2),before=before[i].tolist(),after=t[i].tolist()))
result=dict(version='G1_027r1',prospective=prospective,same_level_probes=len(same),max_same_level_difference_m=max(same),
    level_transitions=len(transitions),max_level_transition_m=max(transitions),
    all_joins=rows,slope_quantiles=np.quantile(slopes,[.5,.95,.99,1]).tolist(),steep_triangles=steep,
    visual_acceptance=False,natural_use_verified=False)
name='prospective_geometry.json' if prospective else 'actual_geometry.json'
(D/name).write_text(json.dumps(result,indent=2),encoding='utf-8')
print('GRADE_GEOMETRY',json.dumps({k:v for k,v in result.items() if k not in ['all_joins','steep_triangles']}),flush=True)
assert max(same)<.025,max(same)
assert max(transitions)<.17,max(transitions)
assert max(slopes)<.25,max(slopes)
