"""Build the nine missing source-positioned Sophora trees and their soil pits.

Run in021. The optional TREE_IDS global permits bounded batches; completed trees
are guarded by receipts, and no partial scene is written as a native checkpoint.
"""
from pathlib import Path
import ast, json, hashlib, math
import bpy
import numpy as np

R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene
assert s['version']=='G1_021'
D=R/'derived/bellevue/riviera_quay';p=json.loads((D/'tree_build_input.json').read_text())
E=R/'evidence/G1_021r1';E.mkdir(exist_ok=True)
parent=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION']
def collection(name):
    c=bpy.data.collections.get(name)
    if c is None:c=bpy.data.collections.new(name);parent.children.link(c)
    return c
treecol=collection('34_RIVIERA_TREES');soilcol=collection('35_RIVIERA_TREE_PITS')

def mesh(name,vertices,faces):
    # Weld exact repeated positions, preserving the material projection below.
    v=[];index={};remap=[]
    for point in vertices:
        key=tuple(round(x,7) for x in point)
        if key not in index:index[key]=len(v);v.append(point)
        remap.append(index[key])
    me=bpy.data.meshes.new(name);me.from_pydata(v,[],[[remap[i] for i in f] for f in faces]);me.update()
    uv=me.uv_layers.new(name='metre_scale')
    for face in me.polygons:
        axis=int(np.argmax(abs(np.array(face.normal))));axes=([1,2],[0,2],[0,1])[axis]
        for li in face.loop_indices:
            q=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(q[axes[0]],q[axes[1]])
    return me

if not soilcol.get('complete',False):
    assert len(soilcol.objects)==0, 'Inspect incomplete soil build before retry'
    for part in p['paving_replacements']:
        ob=bpy.data.objects['RQ_'+part['name']]
        assert abs(ob['source_plan_area_m2']-part['original_area_m2'])<1e-8
        materials=[slot.material for slot in ob.material_slots]
        me=mesh(ob.name+'_with_soil_openings',part['vertices'],part['faces'])
        for m in materials:me.materials.append(m)
        ob.data=me
        for i,m in enumerate(materials):ob.material_slots[i].material=m
        ob['area_before_soil_openings_m2']=part['original_area_m2'];ob['source_plan_area_m2']=part['area_m2']
        ob['tree_pits_source']='derived/bellevue/riviera_quay/tree_build_input.json'
    soilmat=bpy.data.objects['LM_SOIL'].material_slots[0].material
    for entry in p['trees']:
        ident=entry['source']['properties']['objectid'];q=entry['soil_mesh'];name=f'RQ_SOIL_{ident}'
        me=bpy.data.meshes.new(name);me.from_pydata(q['vertices'],[],q['faces']);me.update();me.materials.append(soilmat)
        uv=me.uv_layers.new(name='scan_metres');arr=np.asarray(q['uv'],dtype=np.float32)
        uv.data.foreach_set('uv',np.array([arr[l.vertex_index] for l in me.loops],dtype=np.float32).ravel())
        for face in me.polygons:face.use_smooth=True
        ob=bpy.data.objects.new(name,me);soilcol.objects.link(ob)
        ob['source_id']=entry['source']['id'];ob['source_plan_area_m2']=q['area_m2']
        ob['evidence_basis']=entry['basis'];ob['collision_role']='walkable_candidate';ob['construction_batch']='G1_021r1'
    soilcol['complete']=True;soilcol['soil_area_m2']=p['soil_area_m2']

# Reuse the already inspected compound-leaf construction, not repeated mesh
# instances. Independent source-ID seeds determine every crown and shoot.
original=R/'tools/blender_build_limmat_sidewalk.py';module=ast.parse(original.read_text())
loop=next(n for n in module.body if isinstance(n,ast.For) and ast.unparse(n.target)=='entry')
branch=next(n for n in loop.body if isinstance(n,ast.If) and 'Platanus' in ast.unparse(n.test))
code=ast.unparse(ast.Module(body=branch.orelse,type_ignores=[])).replace('LM_TREE_','RQ_TREE_')
changes={
 'phase = rng.uniform(0, 2 * np.pi)': 'phase = rng.uniform(0, 2 * np.pi)\nroot_axes = rng.uniform(0, 2*np.pi, 6)\nroot_weights = rng.uniform(.30, 1., 6)\nroot_widths = rng.uniform(.17, .34, 6)',
 'lobe = (0.5 + 0.5 * np.cos(5 * a + phase + 0.17 * np.sin(a * 2))) ** 3': 'lobe = sum(w*np.exp(-((np.arctan2(np.sin(a-aa),np.cos(a-aa)))/width)**2) for aa,w,width in zip(root_axes,root_weights,root_widths))',
 'rr = r + (0.012 + diam * 0.25 * lobe) * np.exp(-max(z, 0) / 0.19) + 0.002 * np.sin(4 * a + z)': 'rr = r + (.009 + diam*.15*lobe)*np.exp(-max(z,0)/.23) + .0015*np.sin(3*a+z+phase)',
 'scaffolds = 5':'scaffolds = 5 + ident % 2'
}
for before,after in changes.items():
    assert code.count(before)==1,before;code=code.replace(before,after)
growth=compile(code,'riviera_sophora_growth','exec')
helper_path=R/'tools/blender_build_bellevue_plane_tree.py';helper_source=ast.parse(helper_path.read_text())
helper=compile(ast.Module(body=[n for n in helper_source.body if isinstance(n,ast.FunctionDef) and n.name in ['unit','curve','add_tube']],type_ignores=[]),'riviera_branch_helpers','exec')
bark=bpy.data.materials['bark_brown_02'];twig=bpy.data.materials['LM | Sophora green young shoots'];leaf=bpy.data.materials['LM | Sophora compound leaf']
targets=set(globals().get('TREE_IDS',[e['source']['properties']['objectid'] for e in p['trees']]))
for entry in p['trees']:
    ident=entry['source']['properties']['objectid']
    if ident not in targets:continue
    names=[f'RQ_TREE_{ident}_{role}' for role in ['WOOD','TWIGS','LEAVES']]
    if treecol.get(f'complete_{ident}',False):
        assert all(n in bpy.data.objects for n in names);continue
    assert not any(n in bpy.data.objects for n in names), 'Inspect partial tree before retry'
    ns={'np':np,'math':math,'bpy':bpy,'R':R,'entry':entry,'ident':ident,'collection':treecol,
        'sophora_materials':lambda:[bark,twig,leaf]}
    exec(helper,ns);exec(growth,ns)
    ob=bpy.data.objects[names[0]];uv=ob.data.uv_layers.active
    values=np.array([u.uv[:] for u in uv.data])*[1.2,4.0]
    phase=(ident%997)/997*2*np.pi
    values[:,0]+=.028*np.sin(values[:,1]*.78+phase)+(ident%107)/107
    values[:,1]+=(ident%89)/89;uv.data.foreach_set('uv',values.astype(np.float32).ravel())
    for name in names:bpy.data.objects[name]['construction_batch']='G1_021r1'
    treecol[f'complete_{ident}']=True;treecol[f'report_{ident}']=json.dumps(ns['rec'])
    del ns
    print('RIVIERA_TREE_COMPLETE',ident,flush=True)
reports=[json.loads(treecol[k]) for k in treecol.keys() if k.startswith('report_')]
record={'version':'G1_021r1','base':'G1_021','trees':reports,'soil_area_m2':p['soil_area_m2'],
        'source_code_sha256':{q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in [original,helper_path,Path(__file__)]},
        'original_photo_nodes':len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects),
        'tree_form_and_pit_size_inferred':True,'native_saved':False,'visual_acceptance':False}
(E/'trees_build.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
bpy.context.view_layer.update()
print(json.dumps({'trees_done':len(reports),'target':9,'soil_objects':len(soilcol.objects)}),flush=True)
