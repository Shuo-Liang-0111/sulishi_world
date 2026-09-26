"""Classify active material channels before exporting the complete current world.

Disconnected nodes must not cause unnecessary baking; linked procedural channels
must not be silently flattened by the glTF exporter. This is a routing inventory,
never a declaration that the remaining materials are visually equivalent.
"""
import hashlib
import json
import sys
from collections import Counter
from workspace_paths import read_path, write_path

version=sys.argv[1]
source=read_path(f'evidence/{version}/runtime_material_graphs.json')
graph=json.loads(source.read_text())
inventory=json.loads(read_path(f'evidence/{version}/runtime_inventory.json').read_text())
assert graph['native_sha256']==inventory['native_sha256'] and graph['version']==version
standard_nodes={'BSDF_PRINCIPLED','OUTPUT_MATERIAL','TEX_IMAGE','TEX_COORD','MAPPING','NORMAL_MAP','UVMAP','REROUTE'}
rows=[]
for material in graph['materials']:
    nodes={n['name']:n for n in material['nodes']}
    outputs=[n for n in nodes.values() if n['type']=='OUTPUT_MATERIAL' and n.get('is_active_output')]
    assert len(outputs)==1,(material['name'],'ambiguous material output')
    incoming={}
    for link in material['links']:
        key=(link['to_node'],link['to_socket_index']);assert key not in incoming
        incoming[key]=link
    def input_by_name(node,name):
        return next(s for s in node['inputs'] if s['name']==name)
    def ancestors(node_name,socket_index,seen=None):
        if seen is None:seen=set()
        link=incoming.get((node_name,socket_index))
        if not link:return seen
        name=link['from_node']
        if name in seen:return seen
        seen.add(name)
        for socket in nodes[name]['inputs']:
            if socket['linked']:ancestors(name,socket['index'],seen)
        return seen
    output=outputs[0];surface=input_by_name(output,'Surface')
    surface_link=incoming[(output['name'],surface['index'])]
    shader=nodes[surface_link['from_node']]
    assert shader['type']=='BSDF_PRINCIPLED' and not shader['mute'],material['name']
    channels=[]
    for socket in shader['inputs']:
        if not socket['enabled']:continue
        active=ancestors(shader['name'],socket['index'])
        active_types=sorted({nodes[n]['type'] for n in active})
        coordinates=[]
        for link in material['links']:
            n=nodes[link['from_node']]
            if n['name'] in active and n['type']=='TEX_COORD':
                coordinates.append(n['outputs'][link['from_socket_index']]['name'])
        procedural=sorted(set(active_types)-standard_nodes-{'VERTEX_COLOR'})
        non_uv_image=bool('TEX_IMAGE' in active_types and set(coordinates)-{'UV'})
        map_flags=[]
        for name in active:
            node=nodes[name]
            if node['type']=='MAPPING':
                defaults={s['name']:s.get('default') for s in node['inputs'] if not s['linked']}
                if node.get('vector_type')!='POINT':map_flags.append('non_POINT_mapping')
                rot=defaults.get('Rotation',[0,0,0])
                if abs(rot[0])+abs(rot[1])>1e-8:map_flags.append('3d_UV_rotation')
            if node['type']=='TEX_IMAGE' and node.get('projection')!='FLAT':map_flags.append('non_flat_projection')
        route='bake_or_runtime_graph' if procedural or non_uv_image or map_flags else 'gltf_candidate'
        if 'VERTEX_COLOR' in active_types:route='native_vertex_color'
        channels.append({'input':socket['name'],'linked':socket['linked'],'constant':socket.get('default'),
                         'active_nodes':sorted(active),'active_types':active_types,'coordinates':sorted(set(coordinates)),
                         'procedural_nodes':procedural,'mapping_flags':map_flags,'route':route})
    specials=[]
    values={s['name']:s.get('default') for s in shader['inputs'] if not s['linked']}
    if values.get('Subsurface Weight',0)>0:specials.append('subsurface_scattering')
    if values.get('Diffuse Roughness',0)>0:specials.append('diffuse_roughness')
    if input_by_name(output,'Volume')['linked']:specials.append('volume_output')
    if input_by_name(output,'Displacement')['linked']:specials.append('displacement_output')
    active_all=ancestors(output['name'],surface['index'])|{output['name']}
    for label in ['Volume','Displacement']:
        active_all|=ancestors(output['name'],input_by_name(output,label)['index'])
    rows.append({'material':material['name'],'objects':material['used_by'],'channels':channels,
                 'special_handling':specials,'inactive_nodes':sorted(set(nodes)-active_all),
                 'requires_channel_bake_or_graph':any(c['route']=='bake_or_runtime_graph' for c in channels),
                 'visually_verified':False})
assert {r['material'] for r in rows}=={m['name'] for m in inventory['materials']}
summary={'materials':len(rows),'gltf_candidates':sum(not r['requires_channel_bake_or_graph'] and not r['special_handling'] for r in rows),
         'channel_bake_or_graph':sum(r['requires_channel_bake_or_graph'] for r in rows),
         'special_materials':[{k:r[k] for k in ['material','special_handling']} for r in rows if r['special_handling']],
         'procedural_channel_counts':dict(Counter(c['input'] for r in rows for c in r['channels'] if c['route']=='bake_or_runtime_graph')),
         'affected_object_count':len({n for r in rows if r['requires_channel_bake_or_graph'] for n in r['objects']})}
out={'version':version,'native_sha256':graph['native_sha256'],'source_graph_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
     'summary':summary,'materials':rows,'export_ready':False,
     'limit':'Routes are based on actual connected nodes. glTF candidates still require actual exporter and rendered checks.'}
target=write_path(f'derived/runtime_current/{version}/material_routes.json')
assert not target.exists(),'Retain earlier routing evidence.'
target.write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({'path':str(target),**summary},ensure_ascii=False))
