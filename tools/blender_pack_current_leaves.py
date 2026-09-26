"""Pack any compatible saved-native leaf mesh with exact positions and normals.

No affine approximation, source edits, thinning or source reference duplication.
Unknown topology/shading is rejected for explicit treatment, never silently lost.
"""
import hashlib
import json
import math
import numpy as np


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pack_leaf(ob, folder, version, native_sha):
    assert ob.type=='MESH' and ob.parent is None and not ob.constraints
    assert not ob.modifiers and not ob.data.shape_keys and not ob.data.has_custom_normals,ob.name
    me=ob.data
    assert len(ob.material_slots)==1 and all(len(p.vertices)==3 and p.use_smooth for p in me.polygons),ob.name
    me.calc_loop_triangles()
    faces=np.empty(len(me.loops),np.int32);me.loops.foreach_get('vertex_index',faces);faces=faces.reshape(-1,3)
    fcount=int(np.flatnonzero(faces[:,0]!=faces[0,0])[0]);vcount=int(faces[fcount].min())
    count=len(me.vertices)//vcount
    assert count*vcount==len(me.vertices) and count*fcount==len(faces),ob.name
    template_indices=faces[:fcount]
    assert np.array_equal(faces.reshape(count,fcount,3),template_indices+np.arange(count)[:,None,None]*vcount),ob.name
    positions=np.empty(len(me.vertices)*3,np.float32);me.vertices.foreach_get('co',positions);positions=positions.reshape(-1,3)
    normals=np.empty(len(me.vertices)*3,np.float32);me.vertices.foreach_get('normal',normals);normals=normals.reshape(-1,3)
    corners=np.empty(len(me.corner_normals)*3,np.float32);me.corner_normals.foreach_get('vector',corners)
    assert np.max(abs(corners.reshape(-1,3)-normals[faces.ravel()]))<1e-6,ob.name
    assert np.all(np.linalg.norm(normals,axis=-1)>.99)
    p=normals/np.abs(normals).sum(axis=-1,keepdims=True)
    octa=p[:,:2].copy();low=p[:,2]<0
    octa[low]=(1-np.abs(octa[low,::-1]))*np.where(octa[low]>=0,1,-1)
    decoded=np.c_[octa.astype(np.float64),1-np.abs(octa.astype(np.float64)).sum(axis=-1)]
    t=np.maximum(-decoded[:,2],0);decoded[:,:2]+=np.where(decoded[:,:2]>=0,-t[:,None],t[:,None])
    decoded/=np.linalg.norm(decoded,axis=-1,keepdims=True)
    source_normals=normals.astype(np.float64);source_normals/=np.linalg.norm(source_normals,axis=-1,keepdims=True)
    angle=float(np.degrees(np.arccos(np.clip((decoded*source_normals).sum(-1),-1,1))).max())
    assert angle<.0001,(ob.name,angle)
    material=ob.material_slots[0].material
    assert {n.type for n in material.node_tree.nodes}=={'OUTPUT_MATERIAL','BSDF_PRINCIPLED','VERTEX_COLOR'},material.name
    color_node=next(n for n in material.node_tree.nodes if n.type=='VERTEX_COLOR')
    color_attr=me.color_attributes[color_node.layer_name]
    assert color_attr.domain=='POINT' and color_attr.data_type=='FLOAT_COLOR'
    colors=np.empty(len(color_attr.data)*4,np.float32);color_attr.data.foreach_get('color',colors);colors=colors.reshape(count,vcount,4)
    assert np.all(colors[:,:,3]==1) and np.all(colors[0,0,:3]>0)
    template_color=(colors[0,:,:3]/colors[0,0,:3]).astype(np.float32);instance_color=colors[:,0,:3].copy()
    color_error=float(np.max(abs(template_color[None]*instance_color[:,None]-colors[:,:,:3])))
    assert color_error<1e-6,(ob.name,color_error)
    width=1024;height=math.ceil(len(positions)/width)
    position_tex=np.zeros((width*height,4),np.float32);position_tex[:len(positions),:3]=positions
    normal_tex=np.zeros((width*height,2),np.float32);normal_tex[:len(positions)]=octa
    assert np.array_equal(position_tex[:len(positions),:3],positions)
    arrays={'template_positions':positions[:vcount], 'template_normals':normals[:vcount],
            'template_indices':template_indices.astype(np.uint16),'template_colors':template_color,
            'instance_colors':instance_color,'exact_native_position_texture':position_tex,'native_normal_oct_texture':normal_tex}
    blob=bytearray();descriptions={}
    for key,values in arrays.items():
        values=np.ascontiguousarray(values)
        while len(blob)%4:blob.append(0)
        data=values.tobytes();descriptions[key]={'offset':len(blob),'bytes':len(data),'dtype':values.dtype.str,'shape':list(values.shape),'sha256':sha(data)}
        blob.extend(data)
    folder.mkdir(parents=True,exist_ok=True)
    binary=folder/(ob.name+'.bin');metadata=folder/(ob.name+'.json')
    assert not binary.exists() and not metadata.exists(),'Never overwrite a previous pack.'
    binary.write_bytes(blob);assert sha(binary.read_bytes())==sha(blob)
    bs=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    out={'version':version,'native_sha256':native_sha,'native_object':ob.name,'format':'exact_native_leaf_runtime_v1',
         'position_policy':'exact_native_texture','file':binary.name,'bytes':len(blob),'sha256':sha(blob),'arrays':descriptions,
         'leaves':count,'vertices_per_leaf':vcount,'faces_per_leaf':fcount,'object_matrix_world':[list(r) for r in ob.matrix_world],
         'native_local_bounds':[positions.min(axis=0).tolist(),positions.max(axis=0).tolist()],
         'normal_texture_dimensions':[width,height], 'maximum_normal_angle_error_degrees':angle,'maximum_color_error':color_error,
         'source_position_sha256':sha(positions.tobytes()),'source_triangle_sha256':sha(faces.astype(np.uint32).tobytes()),
         'source_vertex_count':len(positions),'source_triangle_count':len(faces),
         'native_material':{'name':material.name,'roughness':bs.inputs['Roughness'].default_value,
                            'metallic':bs.inputs['Metallic'].default_value,'native_subsurface_weight':bs.inputs['Subsurface Weight'].default_value},
         'native_unmodified':True,'native_material_equivalence':False,'full_runtime_published':False}
    metadata.write_text(json.dumps(out,indent=2),encoding='utf-8')
    return out
