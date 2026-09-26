"""Replay reviewed world-space face cuts without recreating an old source tile."""
import json
import bpy
import numpy as np
from blender_geometry_fingerprint import mesh_digest


def apply(ob, row):
    assert ob.name == row['object']
    assert json.loads(json.dumps(mesh_digest(ob.data))) == row['source_mesh_digest'], ob.name
    assert [list(r) for r in ob.matrix_world] == row['source_matrix_world'], ob.name
    old = ob.data
    assert len(old.polygons) == row['source_faces'] and all(len(p.vertices) == 3 for p in old.polygons)
    assert not ob.modifiers
    changes = {r['source_face']: r for r in row['replacements']}
    assert len(changes) == len(row['replacements'])
    verts = [list(v.co) for v in old.vertices]
    faces, smooth, mats, uv_values = [], [], [], [[] for _ in old.uv_layers]
    kept = []
    for p in old.polygons:
        uv = [np.array([layer.data[i].uv[:] for i in p.loop_indices]) for layer in old.uv_layers]
        if p.index not in changes:
            kept.append(len(faces)); faces.append(list(p.vertices)); smooth.append(p.use_smooth); mats.append(p.material_index)
            for dst, src in zip(uv_values, uv): dst.extend(src.tolist())
            continue
        source = np.array([old.vertices[i].co for i in p.vertices])
        for values in changes[p.index]['kept_barycentric_triangles']:
            w = np.array(values)
            assert w.shape == (3, 3) and w.min() >= -1e-7 and np.max(abs(w.sum(1)-1)) < 1e-7
            offset = len(verts); verts.extend((w @ source).tolist())
            faces.append([offset, offset+1, offset+2]); smooth.append(p.use_smooth); mats.append(p.material_index)
            for dst, src in zip(uv_values, uv): dst.extend((w @ src).tolist())
    me = bpy.data.meshes.new('BST_RETAINED_' + ob.name)
    me.from_pydata(verts, [], faces); me.update()
    for material in old.materials: me.materials.append(material)
    me.polygons.foreach_set('use_smooth', np.array(smooth, dtype=np.bool_))
    me.polygons.foreach_set('material_index', np.array(mats, dtype=np.int32))
    for old_uv, values in zip(old.uv_layers, uv_values):
        uv = me.uv_layers.new(name=old_uv.name)
        uv.data.foreach_set('uv', np.array(values, dtype=np.float32).ravel())
        uv.active_render, uv.active_clone = old_uv.active_render, old_uv.active_clone
    me.uv_layers.active_index = old.uv_layers.active_index
    assert not me.validate(clean_customdata=False)
    for before, after_index in zip([p for p in old.polygons if p.index not in changes], kept):
        after = me.polygons[after_index]
        assert list(before.vertices) == list(after.vertices)
        for a, b in zip(old.uv_layers, me.uv_layers):
            assert [a.data[i].uv[:] for i in before.loop_indices] == [b.data[i].uv[:] for i in after.loop_indices]
    ob.data = me
    return dict(object=ob.name, before=row['source_mesh_digest'], after=mesh_digest(me),
                unchanged_faces_exact=len(kept), changed_faces=len(changes),
                removed_area_m2=row['removed_area_m2'], retained_uvs_exact=True)
