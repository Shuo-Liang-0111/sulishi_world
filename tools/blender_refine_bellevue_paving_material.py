"""Match fine cast concrete seen in operator ground photos; retain earlier curb finish."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene;assert scene['version']=='G1_007r3'
mat=bpy.data.materials['concrete_floor_worn_001'];mat.use_fake_user=True
assetdir=ROOT/'sources/textures/polyhaven/concrete_floor_worn_001';assetdir.mkdir(parents=True,exist_ok=True);files=[]
for node in mat.node_tree.nodes:
    if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.15
    if node.type=='OUTPUT_MATERIAL':
        for link in list(node.inputs['Displacement'].links):mat.node_tree.links.remove(link)
    if node.type=='TEX_IMAGE' and node.image:
        image=node.image;src=Path(bpy.path.abspath(image.filepath));target=assetdir/src.name
        if src.exists() and src.resolve()!=target.resolve():target.write_bytes(src.read_bytes())
        elif not target.exists() and image.packed_file:target.write_bytes(image.packed_file.data)
        assert target.exists();image.filepath=str(target);image.pack();files.append({'file':str(target.relative_to(ROOT)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'size':list(image.size)})
mat['source_url']='https://polyhaven.com/a/concrete_floor_worn_001';mat['license']='CC0';mat['world_texture_size_m']=3.
mat['evidence_basis']='Fine cast surface constrained by belcafe operator photograph; generic CC0 material, not an on-site scan'
for ob in bpy.data.collections['11_BELLEVUE_STREET_SURFACES'].objects:
    if ob.get('surface_role')=='road_concrete':
        ob.data.materials.clear();ob.data.materials.append(mat)
        coords=np.empty(len(ob.data.uv_layers.active.data)*2,dtype=np.float32);ob.data.uv_layers.active.data.foreach_get('uv',coords);ob.data.uv_layers.active.data.foreach_set('uv',coords*2/3)
receipt={'asset':'concrete_floor_worn_001','page':mat['source_url'],'license':'CC0','authors':['Dimitrios Savva','Rico Cilliers'],'maps':files,'use':'inferred fine cast tram track slab finish; not on-site scan','scale_m':3.,'normal_strength':.15,'displacement_enabled':False}
(assetdir/'receipt.json').write_text(json.dumps(receipt,indent=2))
scene['version']='G1_007r4';native=ROOT/'native/G1_007r4_station_roads_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
record=json.loads((ROOT/'runtime/station_road_working.json').read_text());record.update(version=scene['version'],native=str(native),paving_material=receipt['asset'])
(ROOT/'runtime/station_road_working.json').write_text(json.dumps(record,indent=2));(ROOT/'evidence'/scene['version']).mkdir(exist_ok=True)
print(json.dumps({'version':scene['version'],'native':str(native)}))
