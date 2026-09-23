"""Resume after three trees existed but a completely replaced photo node was empty."""
import bpy,json,math,ast,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_014';td=json.loads((R/'derived/bellevue/south_service/trees_input.json').read_text(encoding='utf-8'));rootcol=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'];collection=bpy.data.collections['25_BELLEVUE_SERVICE_TREES'];reports=[]
expected={f'BS_TREE_{t["source"]["properties"]["objectid"]}_{role}' for t in td['trees'] for role in ['WOOD','TWIGS','LEAVES']};assert set(collection.objects.keys())==expected
for t in td['trees']:
 ident=t['source']['properties']['objectid'];obs=[bpy.data.objects[f'BS_TREE_{ident}_{role}'] for role in ['WOOD','TWIGS','LEAVES']];assert all(len(o.data.vertices)>1000 for o in obs)
 reports.append({'source_id':t['source']['id'],'height_m':t['height_m'],'ground_ln02_m':t['ground_ln02_m'],'vertices':sum(len(o.data.vertices) for o in obs),'crown_shape_inferred':True,'resumed_after_empty_context_patch':True})
src=ast.parse((R/'tools/blender_build_service_trees.py').read_text());start=next(i for i,n in enumerate(src.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='cutpath' for t in n.targets));exec(compile(ast.Module(body=src.body[start:],type_ignores=[]),'resume_context_and_checkpoint','exec'))
