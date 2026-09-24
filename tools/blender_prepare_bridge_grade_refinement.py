"""Capture adaptively refined original027 geometry without touching the scene.

The027r1 grade changed only vertices, which left some long triangles spanning
the curved transition and burying painted lines. Refine the same footprints
before applying that source-supported field. UVs interpolate through BMesh.
"""
from pathlib import Path
import hashlib,json,sys
import bpy,bmesh
import numpy as np

R=Path('F:/MyWorld/ZurichWorld');D=R/'derived/bellevue/bridge_grade'
assert bpy.context.scene['version']=='G1_027r1'
sys.path.insert(0,str(R/'tools'))
from blender_geometry_fingerprint import mesh_digest
patch=json.loads((D/'027r1_patch.json').read_text())
old=np.load(D/'027_target_vertices.npz')
record=json.loads((R/'evidence/G1_027r1/construction.json').read_text())
expected={q['name']:q['mesh_fingerprint'] for q in record['after_fingerprints']}
roles={'asphalt_walk','asphalt_road','asphalt_track','road_asphalt','road_concrete',
       'road_joint','rail','rail_steel','drain','groove_floor','groove_wall','curb','paint','crossing_paint'}
arrays={};rows=[]
for row in patch['objects']:
    if row['role'] not in roles:continue
    ob=bpy.data.objects[row['name']]
    assert json.loads(json.dumps(mesh_digest(ob.data)))==expected[ob.name]
    assert ob.data.users==1 and not ob.data.library
    assert np.allclose(ob.matrix_world,np.eye(4),atol=1e-10)
    # The two interleaved cadastral sliver pieces destabilize at a second
    # subdivision: near-coincident float32 vertices create inverted slivers.
    # Keep their verified40cm tessellation; other pieces use20cm. Both remain
    # subject to the same slope, seam, and actual paint-surface checks.
    edge_target=.40 if ob.name in {'BD_SURFACE_5943_009_0','BD_SURFACE_5943_010_0'} else .20
    me=ob.data.copy();bm=None
    try:
        me.vertices.foreach_set('co',old[row['key']].astype(np.float32).ravel());me.update()
        bm=bmesh.new();bm.from_mesh(me)
        for iteration in range(12):
            edges=[e for e in bm.edges if e.calc_length()>edge_target and
                   min(v.co.x for v in e.verts)<-254 and max(v.co.x for v in e.verts)>-297 and
                   min(v.co.y for v in e.verts)<155 and max(v.co.y for v in e.verts)>110]
            if not edges:break
            bmesh.ops.subdivide_edges(bm,edges=edges,cuts=1,use_grid_fill=True)
            assert len(bm.verts)<350000,ob.name
        else:raise AssertionError(('Subdivision not converged',ob.name))
        bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.normal_update()
        # Avoid inheriting long sliver diagonals through an otherwise smooth
        # curved grade. Only internal upper-face diagonals rotate; footprints
        # and their source coordinates are unchanged.
        top=[f for f in bm.faces if f.normal.z>.85]
        top_set=set(top)
        inner=[e for e in bm.edges if len(e.link_faces)==2 and all(f in top_set for f in e.link_faces)]
        bmesh.ops.beautify_fill(bm,faces=top,edges=inner)
        bm.to_mesh(me);me.update()
        face_count=len(me.polygons);vertex_count=len(me.vertices)
        distinct={tuple(sorted(p.vertices)) for p in me.polygons}
        duplicates=face_count-len(distinct)
        if duplicates:
            # The legacy union rail includes coincident triangles. Blender's
            # validator drops only duplicates here and keeps interpolated UVs.
            assert me.validate(clean_customdata=False)
            assert len(me.vertices)==vertex_count and len(me.polygons)==len(distinct)
        key=row['key'];v=np.empty(len(me.vertices)*3,np.float32);me.vertices.foreach_get('co',v)
        faces=np.empty(len(me.loops),np.int32);me.loops.foreach_get('vertex_index',faces)
        arrays[key]=v.reshape(-1,3);arrays[key+'_faces']=faces.reshape(-1,3)
        for prop,dtype in [('material_index',np.int32),('use_smooth',np.bool_)]:
            a=np.empty(len(me.polygons),dtype);me.polygons.foreach_get(prop,a);arrays[key+'_'+prop]=a
        for i,layer in enumerate(me.uv_layers):
            uv=np.empty(len(layer.data)*2,np.float32);layer.data.foreach_get('uv',uv)
            arrays[key+'_uv_'+str(i)]=uv.reshape(-1,2)
        rows.append(dict(name=ob.name,key=key,role=row['role'],before_fingerprint=expected[ob.name],
                         uv_names=[u.name for u in me.uv_layers],vertices_before=len(ob.data.vertices),
                         vertices_refined=len(me.vertices),faces_refined=len(me.polygons),iterations=iteration,
                         edge_target_m=edge_target,duplicate_faces_removed=duplicates))
    finally:
        if bm:bm.free()
        bpy.data.meshes.remove(me)
np.savez_compressed(D/'027r2_refined_reference.npz',**arrays)
out=dict(base_version='G1_027r1',original_grade_source='G1_027',edge_target_m=.20,
         bounds_local=[-297,110,-254,155],objects=rows,scene_mutated=False,
         reference_sha256=hashlib.sha256((D/'027r2_refined_reference.npz').read_bytes()).hexdigest())
(D/'027r2_refined_objects.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('GRADE_REFINED_REFERENCE',len(rows),sum(r['vertices_refined'] for r in rows),flush=True)
