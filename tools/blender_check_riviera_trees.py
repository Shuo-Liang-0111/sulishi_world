"""Source identity, pit openings, actual root/soil and image-dependency checks."""
from pathlib import Path
import json
import bpy
import numpy as np
from mathutils import Vector

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert str(s['version']).startswith(('G1_021','G1_022'))
p=json.loads((R/'derived/bellevue/riviera_quay/tree_build_input.json').read_text())
c=bpy.data.collections['34_RIVIERA_TREES'];soilcol=bpy.data.collections['35_RIVIERA_TREE_PITS']
assert len(c.objects)==27 and len(soilcol.objects)==9
assert {o['source_id'] for o in c.objects}=={e['source']['id'] for e in p['trees']}
records=[];missing=[]
for entry in p['trees']:
    ident=entry['source']['properties']['objectid'];base=entry['ground_ln02_m']-400
    objs=[bpy.data.objects[f'RQ_TREE_{ident}_{kind}'] for kind in ['WOOD','TWIGS','LEAVES']]
    world=[np.array([(o.matrix_world@v.co)[:] for v in o.data.vertices]) for o in objs]
    assert all(np.isfinite(v).all() for v in world)
    top=max(v[:,2].max() for v in world);assert abs(top-base-entry['height_m'])<.0001
    wood=world[0];root_center=wood[:49,:2].mean(0)
    # Duplicate seam vertex biases the average by a few millimetres; the two
    # opposite samples at the below-ground ring define the source trunk centre.
    root_center=(wood[0,:2]+wood[24,:2])/2
    assert np.linalg.norm(root_center-entry['xy_local'])<.06
    soil=bpy.data.objects[f'RQ_SOIL_{ident}'];xy=entry['xy_local']
    hit,point,_,_=soil.ray_cast(Vector((*xy,30)),Vector((0,0,-1)));assert hit
    assert abs(point.z-base)<.002,(ident,point.z,base)
    low=wood[wood[:,2]<base+.025]
    penetrations=[]
    for vertex in low[::max(1,len(low)//30)]:
        hit,q,_,_=soil.ray_cast(Vector((*vertex[:2],30)),Vector((0,0,-1)))
        assert hit,('Root outside soil',ident,vertex.tolist())
        penetrations.append(float(q.z-vertex[2]))
    assert max(penetrations)>.04
    for ob in bpy.data.collections['33_RIVIERA_QUAY'].objects:
        if ob.get('surface_role')!='asphalt':continue
        hit,_,_,_=ob.ray_cast(Vector((*xy,30)),Vector((0,0,-1)))
        assert not hit,('Pavement still caps soil opening',ident,ob.name)
    records.append({'source_id':entry['source']['id'],'height_m':float(top-base),'inventory_height_m':entry['height_m'],
                    'soil_height_local':float(point.z),'maximum_root_in_soil_m':max(penetrations),'pavement_open':True})
for ob in list(c.objects)+list(soilcol.objects):
    for slot in ob.material_slots:
        mat=slot.material
        if not mat or not mat.use_nodes:continue
        for n in mat.node_tree.nodes:
            if n.type=='TEX_IMAGE' and n.image and not n.image.packed_file:
                path=Path(bpy.path.abspath(n.image.filepath,library=n.image.library))
                if not path.is_file():missing.append(str(path))
assert not missing,missing
def area(ob):
    result=0
    for face in ob.data.polygons:
        if face.normal.z<.5:continue
        q=np.array([(ob.matrix_world@ob.data.vertices[i].co)[:] for i in face.vertices])
        for j in range(1,len(q)-1):result+=abs(np.cross(q[j]-q[0],q[j+1]-q[0])[2])/2
    return result
soil_area=sum(area(o) for o in soilcol.objects)
asphalt_area=sum(area(o) for o in bpy.data.collections['33_RIVIERA_QUAY'].objects if o.get('surface_role')=='asphalt')
assert abs(soil_area-p['soil_area_m2'])<.002
assert abs(asphalt_area+soil_area-p['paving_area_before_m2'])<.003
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
record={'version':s['version'],'inventory_trees_checked':records,'soil_area_m2':soil_area,'paved_area_m2':asphalt_area,
        'coverage_error_m2':asphalt_area+soil_area-p['paving_area_before_m2'],'missing_images':missing,
        'geometry_checks_passed':True,'actual_walking_verified':False,'visual_acceptance':False}
out=R/'evidence'/s['version'];out.mkdir(exist_ok=True)
(out/'tree_geometry_check.json').write_text(json.dumps(record,indent=2))
print(json.dumps({k:v for k,v in record.items() if k!='inventory_trees_checked'}),flush=True)
