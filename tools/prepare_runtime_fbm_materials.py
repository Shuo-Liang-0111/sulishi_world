"""Extract the simple, explicitly connected native FBM material families."""
from pathlib import Path
import hashlib
import json
from workspace_paths import read_path,write_path

version='G1_027r15'
graph_path=read_path(f'evidence/{version}/runtime_material_graphs.json');graph=json.loads(graph_path.read_text())
sem=json.loads(read_path(f'evidence/{version}/runtime_material_semantics.json').read_text())
assert sem['native_sha256']==graph['native_sha256'] and sem['graph_sha256']==hashlib.sha256(graph_path.read_bytes()).hexdigest()
proof=json.loads(read_path(f'evidence/{version}/fbm_browser_report.json').read_text());assert proof['passed'] and proof['native_sha256']==graph['native_sha256']
semantics={m['material']:{n['name']:n for n in m['nodes']} for m in sem['materials']}
allowed={'BUMP','TEX_COORD','TEX_NOISE','VALTORGB','BSDF_PRINCIPLED','OUTPUT_MATERIAL'}
recipes=[]
for material in graph['materials']:
    if len(material['nodes'])<=2 or any(n['type'] not in allowed for n in material['nodes']):continue
    name=material['name'];nodes={n['name']:n for n in material['nodes']};links={(l['to_node'],l['to_socket_index']):l for l in material['links']}
    bs=next(n for n in material['nodes'] if n['type']=='BSDF_PRINCIPLED')
    assert not any(n['mute'] for n in material['nodes'])
    assert {s['name'] for s in bs['inputs'] if s['linked']} <= {'Base Color','Roughness','Normal'}
    def input_value(node,label):
        socket=next(s for s in node['inputs'] if s['name']==label);assert not socket['linked'];return socket['default']
    def upstream(node,label):
        socket=next(s for s in node['inputs'] if s['name']==label);link=links[(node['name'],socket['index'])]
        source=nodes[link['from_node']];return source,source['outputs'][link['from_socket_index']]['name']
    def noise_recipe(noise):
        assert noise['type']=='TEX_NOISE'
        properties=semantics[name][noise['name']]
        assert properties['noise_type']=='FBM' and properties['noise_dimensions']=='3D'
        mapping=properties['texture_mapping']
        assert mapping['translation']==mapping['rotation']==[0.,0.,0.] and mapping['scale']==[1.,1.,1.]
        assert [mapping['mapping_x'],mapping['mapping_y'],mapping['mapping_z']]==['X','Y','Z'] and not mapping['use_min'] and not mapping['use_max']
        assert input_value(noise,'Distortion')==0
        coord,output=upstream(noise,'Vector');assert coord['type']=='TEX_COORD' and output in ['Object','UV']
        assert semantics[name][coord['name']]['object'] is None and not semantics[name][coord['name']]['from_instancer']
        return {'coordinate':output,'scale':input_value(noise,'Scale'),'detail':input_value(noise,'Detail'),
            'roughness':input_value(noise,'Roughness'),'lacunarity':input_value(noise,'Lacunarity'),'normalize':properties['normalize']}
    recipe={'name':name,'objects':material['used_by'],'ramp':None,'bump':None,'base':next(s['default'] for s in bs['inputs'] if s['name']=='Base Color'),
        'roughness':next(s['default'] for s in bs['inputs'] if s['name']=='Roughness')}
    for socket in bs['inputs']:
        if not socket['linked']:continue
        source,output=upstream(bs,socket['name'])
        if socket['name'] in ['Base Color','Roughness']:
            assert recipe['ramp'] is None and source['type']=='VALTORGB' and output=='Color'
            ramp=source['color_ramp'];assert ramp['mode']=='RGB' and ramp['interpolation'] in ['LINEAR','EASE'] and len(ramp['elements'])==2
            if socket['name']=='Roughness':assert all(max(e['color'][:3])-min(e['color'][:3])<1e-7 for e in ramp['elements'])
            noise,output=upstream(source,'Fac');assert output=='Fac'
            recipe['ramp']={'channel':socket['name'],'noise':noise_recipe(noise),**ramp}
        elif socket['name']=='Normal':
            assert source['type']=='BUMP' and output=='Normal' and not source['invert']
            assert not next(s for s in source['inputs'] if s['name']=='Normal')['linked']
            noise,output=upstream(source,'Height');assert output=='Fac'
            recipe['bump']={'noise':noise_recipe(noise),'strength':input_value(source,'Strength'),'distance':input_value(source,'Distance'),'filter_width':input_value(source,'Filter Width')}
    recipes.append(recipe)
assert len(recipes)==89
out={'version':version,'native_sha256':graph['native_sha256'],'graph_sha256':sem['graph_sha256'],
 'materials':recipes,'noise_scalar_verified':True,'bump_lighting_native_equivalence':False,'source_geometry_unchanged':True}
write_path(f'web/assets/{version}_fbm_materials.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
write_path(f'derived/runtime_current/{version}/fbm_material_recipes.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({'materials':len(recipes),'object_material_uses':sum(len(r['objects']) for r in recipes),'full_materials_verified':False}))
