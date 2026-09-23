"""Replace material regions on the existing road triangles without changing grades."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version']=='G1_007r2'
path=ROOT/'derived/bellevue/transport/paving_input.json';payload=json.loads(path.read_text())
assert payload['report']['source_road_input_sha256']==hashlib.sha256((ROOT/'derived/bellevue/transport/road_input.json').read_bytes()).hexdigest()
col=bpy.data.collections['11_BELLEVUE_STREET_SURFACES']
old=[o for o in col.objects if o.get('surface_role')=='road_asphalt']
assert len(old)==11
concrete=bpy.data.materials['concrete_floor_01'].copy();concrete.name='BE | station concrete track paving'
concrete['evidence_basis']='SWISSIMAGE material segmentation; generic CC0 mineral finish, not on-site texture'
for node in concrete.node_tree.nodes:
    if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.12
joint=bpy.data.materials.new('BE | track paving sealed joint');joint.use_nodes=True
bs=joint.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.042,.04,.037,1);bs.inputs['Roughness'].default_value=.86
materials={'asphalt':bpy.data.materials['asphalt_03'],'concrete':concrete,'joint':joint}
created=[]
for part in payload['parts']:
    t=np.array(part['triangles']);me=bpy.data.meshes.new('BE_PAVING_'+part['id'])
    me.from_pydata(t.reshape(-1,3).tolist(),[],np.arange(t.size//3).reshape(-1,3).tolist());me.update();me.materials.append(materials[part['kind']])
    uv=me.uv_layers.new(name='metre_based_paving');size=2.05 if part['kind']=='asphalt' else 2.
    uv.data.foreach_set('uv',(t[:,:,:2].reshape(-1,2)/size).astype(np.float32).reshape(-1))
    ob=bpy.data.objects.new('BE_PAVING_'+part['id'],me);col.objects.link(ob)
    ob['source_id']=part['source_id'];ob['surface_role']='road_'+part['kind'];ob['place']='Bellevue_station_streets'
    ob['evidence_basis']='AV footprint and preserved photo-derived grade; SWISSIMAGE interpreted finish; masked boundaries/joints inferred'
    ob['derived_source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();ob['quality_status']='material segmentation review; walking not accepted'
    created.append(ob.name)
for ob in old:bpy.data.objects.remove(ob,do_unlink=True)
scene['version']='G1_007r3';scene.camera=bpy.data.objects['BE_QA_TRACK_NEAR'];bpy.context.view_layer.update()
native=ROOT/'native/G1_007r3_station_roads_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
record=json.loads((ROOT/'runtime/station_road_working.json').read_text());record.update(version=scene['version'],native=str(native),paving_input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),paving_report=payload['report'],paving_objects=created)
(ROOT/'runtime/station_road_working.json').write_text(json.dumps(record,indent=2));(ROOT/'evidence'/scene['version']).mkdir(exist_ok=True)
print(json.dumps({'version':scene['version'],'new_paving_objects':len(created),'native':str(native)}))
