"""UV-only evaluated proxy; join duplicate positions before lightmap unwrapping.

Neither editable objects nor their primary material UVs are changed or saved.
Loop ordering is checked geometrically before mapping UV1 back to each object.
"""
import bpy,json,hashlib,math,numpy as np
from pathlib import Path
from collections import defaultdict
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;V=s['version'];assert V in ['G1_016r1','G1_018r3']
D=R/'derived/runtime_occlusion'/V;previous=json.loads((D/'manifest.json').read_text());old_uv=np.load(R/previous['uv_file'])
deps=bpy.context.evaluated_depsgraph_get();vertices=[];faces=[];smooth=[];records=[];loop_points=[];offset=0;loop_start=0
for item in previous['receivers']:
    ob=bpy.data.objects[item['name']];ev=ob.evaluated_get(deps);me=ev.to_mesh()
    v=np.empty(len(me.vertices)*3,np.float32);me.vertices.foreach_get('co',v)
    ids=np.empty(len(me.loops),np.int32);me.loops.foreach_get('vertex_index',ids)
    assert hashlib.sha256(v.tobytes()+ids.tobytes()).hexdigest()==item['topology_sha256']
    matrix=np.asarray(ob.matrix_world,dtype=np.float64);world=v.reshape(-1,3)@matrix[:3,:3].T+matrix[:3,3]
    vertices.append(world);loop_points.append(world[ids]);faces.extend(tuple(int(i)+offset for i in p.vertices) for p in me.polygons)
    smooth.extend(p.use_smooth for p in me.polygons);record=dict(item);record['loop_start']=loop_start;records.append(record)
    offset+=len(me.vertices);loop_start+=len(me.loops);ev.to_mesh_clear()
vertices=np.concatenate(vertices);expected_loops=np.concatenate(loop_points)
# Construction triangulation stores each triangle independently. Weld this
# temporary UV proxy only, with sub-micrometre rounding, to expose adjacency.
unique,inverse=np.unique(np.round(vertices,6),axis=0,return_inverse=True)
new_faces=[tuple(int(inverse[i]) for i in face) for face in faces]
me=bpy.data.meshes.new('TEMP_CONTIGUOUS_LIGHT_UV');me.from_pydata(unique.tolist(),[],new_faces);me.update();me.polygons.foreach_set('use_smooth',smooth)
ids=np.empty(len(me.loops),np.int32);me.loops.foreach_get('vertex_index',ids)
assert len(ids)==loop_start
error=float(np.max(np.abs(unique[ids]-expected_loops)));assert error<.000001
ob=bpy.data.objects.new('TEMP_CONTIGUOUS_LIGHT_UV',me);s.collection.objects.link(ob)
me.uv_layers.new(name='runtime_indirect_occlusion')
for other in s.objects:other.select_set(False)
ob.select_set(True);bpy.context.view_layer.objects.active=ob
rna=bpy.ops.uv.smart_project.get_rna_type();assert 'margin_method' in rna.properties
assert 'FRACTION' in {i.identifier for i in rna.properties['margin_method'].enum_items}
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(70),island_margin=8/4096,margin_method='FRACTION',area_weight=.5,correct_aspect=True,scale_to_bounds=True)
bpy.ops.object.mode_set(mode='OBJECT')
values=np.empty(len(me.loops)*2,np.float32);me.uv_layers.active.data.foreach_get('uv',values);values=values.reshape(-1,2)
assert np.isfinite(values).all() and values.min()>=-.00001 and values.max()<=1.00001
packed={};checks={}
for item in records:
    start=item['loop_start'];end=start+item['loops'];uv=values[start:end];packed[item['uv_key']]=uv
    if item['name'] not in ['BS_SOIL','BS_ASPHALT']:continue
    points=expected_loops[start:end].reshape(-1,3,3);current=uv.reshape(-1,3,2);old=old_uv[item['uv_key']].reshape(-1,3,2)
    edges=defaultdict(list)
    for i,t in enumerate(points):
        for a,b in [(0,1),(1,2),(2,0)]:
            first=tuple(np.round(t[a],6));second=tuple(np.round(t[b],6));order=(a,b) if first<second else (b,a)
            edges[tuple(sorted([first,second]))].append((i,order))
    old_jumps=[];new_jumps=[]
    for entries in edges.values():
        if len(entries)!=2:continue
        (i,a),(j,b)=entries
        old_jumps.append(float(np.linalg.norm(old[i,list(a)]-old[j,list(b)],axis=1).max()*4096))
        new_jumps.append(float(np.linalg.norm(current[i,list(a)]-current[j,list(b)],axis=1).max()*4096))
    assert new_jumps
    checks[item['name']]={'shared_geometric_edges':len(new_jumps),'old_uv_discontinuities_over_1px':sum(x>1 for x in old_jumps),'new_uv_discontinuities_over_1px':sum(x>1 for x in new_jumps),'new_max_jump_px':max(new_jumps)}
    if item['name']=='BS_SOIL':assert sum(x>1 for x in new_jumps)<len(new_jumps)*.02,checks[item['name']]
np.savez_compressed(D/'receiver_uv_contiguous.npz',**packed)
# Neutral scalar image references UV1 in standard glTF. It adds no baked AO;
# fresh diffuse transport is produced separately on these checked charts.
image=bpy.data.images.new('TEMP_NEUTRAL_OCCLUSION',width=1,height=1,alpha=False)
image.pixels=[1,1,1,1];image.file_format='PNG';image.filepath_raw=str(D/'neutral_occlusion.png');image.save()
manifest=dict(previous);manifest.update(uv_file=str((D/'receiver_uv_contiguous.npz').relative_to(R)),image=str((D/'neutral_occlusion.png').relative_to(R)),image_sha256=hashlib.sha256((D/'neutral_occlusion.png').read_bytes()).hexdigest(),receivers=records,distance_m=0,invalid_scalar_ao_receivers=[],inherited_scalar_ao_from=None,
    layout_inherited_from=None,limitation='Neutral scalar carrier for UV1; no scalar AO bake. New contiguous light charts from an evaluated welded UV-only proxy; fresh diffuse transport is separate. Native primary UVs and editable geometry remain unchanged.')
(D/'manifest_fragmented_rejected.json').write_text(json.dumps(previous,indent=2));(D/'manifest.json').write_text(json.dumps(manifest,indent=2))
report={'version':V,'source_vertices':len(vertices),'uv_proxy_unique_vertices':len(unique),'loop_order_position_error_m':error,'receivers':len(records),'packing_margin_texels':8,'shared_edge_checks':checks,'native_saved':False,'primary_material_uvs_changed':False}
(R/'evidence'/V/'contiguous_light_uv.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
