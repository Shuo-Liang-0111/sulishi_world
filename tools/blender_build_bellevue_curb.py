import bpy,json,numpy as np,hashlib
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene;assert scene['version']=='G1_007r1'
path=ROOT/'derived/bellevue/transport/curb_input.json';payload=json.loads(path.read_text())
col=bpy.data.collections['11_BELLEVUE_STREET_SURFACES']
concrete=bpy.data.materials['concrete_floor_01'];concrete.use_fake_user=True
concrete['source_url']='https://polyhaven.com/a/concrete_floor_01';concrete['license']='CC0';concrete['world_texture_size_m']=2.
assetdir=ROOT/'sources/textures/polyhaven/concrete_floor_01';assetdir.mkdir(parents=True,exist_ok=True)
receipts=[]
for node in concrete.node_tree.nodes:
    if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.18
    if node.type=='OUTPUT_MATERIAL':
        for link in list(node.inputs['Displacement'].links):concrete.node_tree.links.remove(link)
    if node.type=='TEX_IMAGE' and node.image:
        image=node.image;src=Path(bpy.path.abspath(image.filepath));target=assetdir/src.name
        if src.exists() and src.resolve()!=target.resolve():target.write_bytes(src.read_bytes())
        elif not target.exists() and image.packed_file:target.write_bytes(image.packed_file.data)
        assert target.exists(),f'Missing original or packed texture: {image.name}'
        image.filepath=str(target);image.pack();receipts.append({'file':str(target.relative_to(ROOT)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'size':list(image.size)})
(assetdir/'receipt.json').write_text(json.dumps({'asset':'concrete_floor_01','page':'https://polyhaven.com/a/concrete_floor_01','license':'CC0','author':'Rob Tuytel','maps':receipts,'use':'inferred weathered station curb finish; not on-site material scan'},indent=2))
joint=bpy.data.materials.new('BE | curb mineral mortar');joint.use_nodes=True;bs=joint.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.085,.081,.073,1);bs.inputs['Roughness'].default_value=.89
materials={'platform':bpy.data.materials['asphalt_03'],'curb_top':concrete,'curb_face':concrete,'curb_joint':joint}
objects=[]
for key,triangles in payload['parts'].items():
    t=np.array(triangles);me=bpy.data.meshes.new('BE_'+key+'_007r2');me.from_pydata(t.reshape(-1,3).tolist(),[],np.arange(t.size//3).reshape(-1,3).tolist());me.update();me.materials.append(materials[key])
    uv=me.uv_layers.new(name='real_world_texture_scale');uv.data.foreach_set('uv',np.array(payload['uv'][key],dtype=np.float32).reshape(-1))
    if key=='platform':ob=bpy.data.objects['BE_PUBLIC_PLATFORM'];ob.data=me
    else:ob=bpy.data.objects.new('BE_PLATFORM_'+key.upper(),me);col.objects.link(ob)
    ob['source_id']=payload['source_id'];ob['evidence_basis']=payload['top_height_basis']+' '+payload['material_basis'];ob['derived_source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();ob['quality_status']='edge closure working; ramp transition and public walking not accepted';objects.append(ob.name)
scene['version']='G1_007r2';scene.camera=bpy.data.objects['BE_QA_TRACK_NEAR'];bpy.context.view_layer.update()
native=ROOT/'native/G1_007r2_station_roads_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
record=json.loads((ROOT/'runtime/station_road_working.json').read_text());record.update(version=scene['version'],native=str(native),curb_input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),curb_objects=objects)
(ROOT/'runtime/station_road_working.json').write_text(json.dumps(record,indent=2));(ROOT/'evidence'/scene['version']).mkdir(exist_ok=True)
print(json.dumps(record))
