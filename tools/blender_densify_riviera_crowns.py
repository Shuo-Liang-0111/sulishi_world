"""Correct the visibly sparse021r1 crowns with more attached compound leaves.

Source tree positions and inventory heights remain fixed. Growth is regenerated
with the same source-ID seeds; no loose leaves or opaque canopy blobs are added.
"""
from pathlib import Path
import ast,json,math,hashlib
import bpy
import numpy as np

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_021r1'
E=R/'evidence/G1_021r2';E.mkdir(exist_ok=True)
p=json.loads((R/'derived/bellevue/riviera_quay/tree_build_input.json').read_text())
treecol=bpy.data.collections['34_RIVIERA_TREES']
author=R/'tools/blender_build_riviera_trees.py';module=ast.parse(author.read_text())
def assignment(n,key):return isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==key for t in n.targets)
start=next(i for i,n in enumerate(module.body) if assignment(n,'original'))
end=next(i for i,n in enumerate(module.body) if assignment(n,'targets'))
setup={'R':R,'ast':ast,'bpy':bpy,'np':np}
exec(compile(ast.Module(body=module.body[start:end],type_ignores=[]),str(author),'exec'),setup)
code=setup['code']
changes={'for j in range(5 if height >= 11 else 4):':'for j in range(9 if height >= 11 else 7):',
         'along = 0.13 + 0.8 * j / (4 if height >= 11 else 3)':'along = 0.13 + 0.8 * j / (8 if height >= 11 else 6)',
         'le = rng.uniform(0.028, 0.052)':'le = rng.uniform(0.032, 0.056)'}
for a,b in changes.items():assert code.count(a)==1,a;code=code.replace(a,b)
growth=compile(code,'riviera_connected_foliage_revision','exec')
targets=set(globals().get('TREE_IDS',[e['source']['properties']['objectid'] for e in p['trees']]))
for entry in p['trees']:
    ident=entry['source']['properties']['objectid']
    if ident not in targets or treecol.get(f'dense_{ident}',False):continue
    names=[f'RQ_TREE_{ident}_{role}' for role in ['WOOD','TWIGS','LEAVES']]
    assert all(n in bpy.data.objects for n in names)
    prior=json.loads(treecol[f'report_{ident}'])
    for name in names:
        ob=bpy.data.objects[name];me=ob.data;assert me.library is None
        bpy.data.objects.remove(ob,do_unlink=True)
        if me.users==0:bpy.data.meshes.remove(me)
    ns={'np':np,'math':math,'bpy':bpy,'R':R,'entry':entry,'ident':ident,'collection':treecol,
        'sophora_materials':lambda:[setup['bark'],setup['twig'],setup['leaf']]}
    exec(setup['helper'],ns);exec(growth,ns)
    ob=bpy.data.objects[names[0]];uv=ob.data.uv_layers.active
    values=np.array([u.uv[:] for u in uv.data])*[1.2,4.0];phase=(ident%997)/997*2*np.pi
    values[:,0]+=.028*np.sin(values[:,1]*.78+phase)+(ident%107)/107;values[:,1]+=(ident%89)/89
    uv.data.foreach_set('uv',values.astype(np.float32).ravel())
    for name in names:bpy.data.objects[name]['construction_batch']='G1_021r2'
    record=ns['rec'];record['previous_leaflet_count']=prior['leaflet_count']
    record['foliage_revision']='More attached compound leaves per terminal shoot; leaflet length32..56mm inferred. Source XY and final inventory height retained.'
    treecol[f'report_{ident}']=json.dumps(record);treecol[f'dense_{ident}']=True
    del ns
    print('RIVIERA_CROWN_REVISED',ident,flush=True)
reports=[json.loads(treecol[f'report_{e["source"]["properties"]["objectid"]}']) for e in p['trees']]
(E/'foliage_revision.json').write_text(json.dumps({'base':'G1_021r1','trees':reports,
  'completed':sum(bool(treecol.get(f'dense_{e["source"]["properties"]["objectid"]}',False)) for e in p['trees']),
  'author_dependency_sha256':hashlib.sha256(author.read_bytes()).hexdigest(),'native_saved':False,'visual_acceptance':False},indent=2))
bpy.context.view_layer.update()
