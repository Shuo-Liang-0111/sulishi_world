"""Bounded, UV-preserving subtraction from existing working photo triangles.

Never reads the untouched source collection to recreate a working tile. Kept
faces retain their indices/UVs; clipped parts interpolate UVs on the same plane.
"""
import numpy as np
import bpy


def split(poly, axis, value, keep_greater):
    """Split a convex attribute polygon, first 3 coordinates are clipping space."""
    inside=[];outside=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[axis]-value)*(1 if keep_greater else -1)
        db=(b[axis]-value)*(1 if keep_greater else -1)
        ia=da>=-1e-9;ib=db>=-1e-9
        (inside if ia else outside).append(a)
        if ia!=ib:
            t=da/(da-db);p=a+(b-a)*t
            inside.append(p);outside.append(p)
    return inside,outside


def subtract_box(poly, bounds):
    outside=[];current=poly
    for axis,value,greater in [(0,bounds[0],True),(0,bounds[1],False),
            (1,bounds[2],True),(1,bounds[3],False),(2,bounds[4],True),(2,bounds[5],False)]:
        if len(current)<3:break
        current,part=split(current,axis,value,greater)
        if len(part)>=3:outside.append(part)
    return outside,current


def area(poly):
    if len(poly)<3:return 0.
    v=np.array([p[:3] for p in poly]);return sum(np.linalg.norm(np.cross(v[j]-v[0],v[j+1]-v[0]))/2 for j in range(1,len(v)-1))


def cut_object(ob, to_clip, boxes, remove_faces=()):
    old=ob.data
    assert all(len(p.vertices)==3 for p in old.polygons), ob.name
    assert all(a.data_type=='FLOAT2' or a.name.startswith('.') or a.name in {'position','sharp_face','material_index'} for a in old.attributes),ob.name
    remove_faces=set(remove_faces);vertices=[list(v.co) for v in old.vertices]
    world=[np.array(ob.matrix_world@v.co) for v in old.vertices]
    local=[np.array(to_clip(p)) for p in world]
    layers=list(old.uv_layers);faces=[];uvs=[[] for _ in layers];smooth=[];materials=[]
    kept=[];removed=[];clipped=[];removed_area=0.;max_residual=0.
    def append(ids,layer_uv,source):
        faces.append(ids);smooth.append(source.use_smooth);materials.append(source.material_index)
        for target,uv in zip(uvs,layer_uv):target.extend(uv)
    inv=ob.matrix_world.inverted()
    from mathutils import Vector
    for face in old.polygons:
        uv_values=[np.array([layer.data[i].uv[:] for i in face.loop_indices]) for layer in layers]
        poly=[np.r_[local[index],world[index],*[uv[k] for uv in uv_values]] for k,index in enumerate(face.vertices)]
        original_area=area(poly);parts=[poly]
        if face.index in remove_faces:parts=[]
        else:
            for box in boxes:
                nxt=[]
                for part in parts:
                    outside,inside=subtract_box(part,box);nxt.extend(p for p in outside if area(p)>1e-10)
                parts=nxt
        remaining=sum(area(p) for p in parts)
        if abs(remaining-original_area)<1e-9:
            append(list(face.vertices),uv_values,face);kept.append(face.index);continue
        assert remaining<=original_area+1e-7,(ob.name,face.index)
        removed_area+=original_area-remaining
        if not parts:removed.append(face.index);continue
        clipped.append(face.index)
        for part in parts:
            for j in range(1,len(part)-1):
                tri=[part[0],part[j],part[j+1]]
                if area(tri)<1e-10:continue
                ids=[]
                for p in tri:
                    ids.append(len(vertices));vertices.append(list(inv@Vector(p[3:6])))
                append(ids,[[p[6+2*k:8+2*k] for p in tri] for k in range(len(layers))],face)
        # Orthogonal frame preserves area, used as a consistency check.
        wp=np.array([p[3:6] for p in poly]);world_area=np.linalg.norm(np.cross(wp[1]-wp[0],wp[2]-wp[0]))/2
        max_residual=max(max_residual,abs(original_area-world_area))
    if not removed and not clipped:return None
    me=bpy.data.meshes.new('SG_RETAINED_'+str(ob.get('source_node',ob.name)))
    me.from_pydata(vertices,[],faces);me.update()
    for mat in old.materials:me.materials.append(mat)
    me.polygons.foreach_set('material_index',np.array(materials,dtype=np.int32))
    me.polygons.foreach_set('use_smooth',np.array(smooth,dtype=np.bool_))
    for layer,values in zip(layers,uvs):
        uv=me.uv_layers.new(name=layer.name)
        uv.data.foreach_set('uv',np.array(values,dtype=np.float32).ravel())
        uv.active_render=layer.active_render;uv.active_clone=layer.active_clone
    me.uv_layers.active_index=old.uv_layers.active_index
    assert not me.validate(clean_customdata=False)
    # Every unaffected triangle and UV must survive exactly.
    by_indices={tuple(p.vertices):p for p in me.polygons if max(p.vertices)<len(old.vertices)}
    for index in kept:
        p=old.polygons[index];q=by_indices[tuple(p.vertices)]
        for a,b in zip(old.uv_layers,me.uv_layers):
            assert [a.data[i].uv[:] for i in p.loop_indices]==[b.data[i].uv[:] for i in q.loop_indices]
    ob.data=me
    return dict(object=ob.name,source_faces=len(old.polygons),kept_exact=len(kept),
        removed_faces=removed,clipped_faces=clipped,new_faces=len(me.polygons),
        removed_area_m2=removed_area,max_rotation_area_residual_m2=max_residual,
        retained_vertices_exact=True,retained_uvs_exact=True)
