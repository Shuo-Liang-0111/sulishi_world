"""Validate actual float32 tree geometry and soil contact, not visual acceptance."""
import bpy,json,numpy as np
from mathutils import Vector
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;V=s['version'];assert V.startswith('G1_015')
td=json.loads((R/'derived/bellevue/south_remaining/trees_input.json').read_text(encoding='utf-8'))
results=[]
bpy.context.view_layer.update()
for entry in td['trees']:
    ident=entry['source']['properties']['objectid']
    p=np.array([*entry['source']['geometry']['coordinates'],entry['ground_ln02_m']])-entry['origin']
    obs=[bpy.data.objects[f'BS_TREE_{ident}_{role}'] for role in ['WOOD','TWIGS','LEAVES']]
    maxz=max(v.co.z for ob in obs for v in ob.data.vertices)
    err=abs(maxz-p[2]-entry['height_m']);assert err<.0001
    collar=np.array([obs[0].data.vertices[i].co[:] for i in range(80)])
    centerr=float(np.linalg.norm(collar[:,:2].mean(0)-p[:2]));assert centerr<.003
    contact=[]
    for pt in collar:
        hit,q,_,_=bpy.data.objects['BS_SOIL'].ray_cast(Vector((pt[0],pt[1],30)),Vector((0,0,-1)))
        assert hit,('Root lies outside source-aligned tree pit',ident)
        contact.append(pt[2]-q.z)
    assert max(contact)<0 and min(contact)>-.16,(ident,min(contact),max(contact))
    results.append({'id':ident,'height_error_m':float(err),'root_center_error_m':centerr,
                    'root_below_soil_m':[float(min(contact)),float(max(contact))],
                    'vertices':sum(len(o.data.vertices) for o in obs),'individual_form_inferred':True})
pit=json.loads((R/'derived/bellevue/south_context/platform_input.json').read_text(encoding='utf-8'))
ids=[p['source']['properties']['objectid'] for p in pit['pits']]
assert all(f'BS_TREE_{i}_WOOD' in bpy.data.objects for i in ids)
originals=bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'];assert len(originals.objects)==2039
report={'version':V,'trees':results,'island_inventory_trees_authored':len(ids),
        'original_photo_nodes_retained':len(originals.objects),'visual_acceptance':False,
        'collision_or_natural_use_verified':False}
(R/'evidence'/V/'geometry_check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
