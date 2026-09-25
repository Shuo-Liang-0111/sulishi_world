"""Read source meshes around official bridge lighting points and flag clusters."""
import json,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import read_path,write_path

assert bpy.context.scene['version']=='G1_027r3'
plan=json.loads(read_path('derived/bellevue/bridge_deck/build_input.json').read_text())
origin=np.array(plan['origin']);masts=plan['masts']
lighting=json.loads(read_path('sources/features/bridge_fittings/ewz_brennstelle_p.geojson').read_text())['features']
locations=[]
for feature in lighting:
    xy=np.array(feature['geometry']['coordinates'])
    distance=[np.linalg.norm(xy-np.array(m['xy'])) for m in masts]
    index=int(np.argmin(distance))
    if distance[index]>.4:continue
    mast=masts[index]
    locations.append(dict(feature=feature,mast=mast,distance_to_mast_m=float(distance[index])))
assert len(locations)==13
centres=np.array([np.array(m['xy'])-origin[:2] for m in masts])
context=[];original=[]
for collection,output in [('04_RETAINED_PHOTO_CONTEXT',context),('03_I3S_PHOTOGRAPHIC_REFERENCE',original)]:
    for ob in bpy.data.collections[collection].objects:
        # Excluded reference objects have an unevaluated identity matrix_world.
        # Their source placement is the saved basis; do not enable or mutate them.
        assert ob.type=='MESH' and ob.parent is None and not ob.constraints
        transform=ob.matrix_basis if collection=='03_I3S_PHOTOGRAPHIC_REFERENCE' else ob.matrix_world
        bounds=np.array([transform@Vector(v) for v in ob.bound_box]);lo=bounds.min(0);hi=bounds.max(0)
        centre=(lo+hi)/2;radius=np.linalg.norm(hi-lo)/2
        flag_region=hi[0]>-292 and lo[0]<-250 and hi[1]>107 and lo[1]<180 and hi[2]>20
        lamp_region=np.min(np.linalg.norm(centres-centre[:2],axis=1))<radius+2 and hi[2]>12 and lo[2]<19
        if not (flag_region or lamp_region):continue
        mesh=ob.data;uv=mesh.uv_layers.active
        image_paths=[]
        for slot in ob.material_slots:
            if not slot.material or not slot.material.node_tree:continue
            for node in slot.material.node_tree.nodes:
                if node.type=='TEX_IMAGE' and node.image:
                    im=node.image
                    image_paths.append(dict(name=im.name,path=bpy.path.abspath(im.filepath,library=im.library),packed=bool(im.packed_file)))
        output.append(dict(name=ob.name,source_node=str(ob.get('source_node')),
            transform_basis='saved_local_basis_no_parent' if collection=='03_I3S_PHOTOGRAPHIC_REFERENCE' else 'evaluated_world',
            vertices=[list(transform@v.co) for v in mesh.vertices],
            faces=[list(p.vertices) for p in mesh.polygons],
            uv_faces=[[list(uv.data[i].uv) for i in p.loop_indices] for p in mesh.polygons],
            images=image_paths))
report=dict(base_version='G1_027r3',origin=origin.tolist(),lamps=locations,context=context,original=original)
write_path('derived/bridge_fittings/source_probe.json').write_text(json.dumps(report,separators=(',',':')),encoding='utf-8')
print(json.dumps(dict(lighting_points=len(locations),current_tiles=len(context),original_tiles=len(original),native_modified=False)))
