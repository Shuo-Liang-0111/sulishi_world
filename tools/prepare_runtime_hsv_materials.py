"""Package only proven, direct UV image -> neutral-hue HSV -> base-colour chains.

No image editing or re-encoding. More complicated chains remain unresolved.
"""
from pathlib import Path
import hashlib
import json
import shutil
from workspace_paths import read_path,write_path

version='G1_027r15'
graph=json.loads(read_path(f'evidence/{version}/runtime_material_graphs.json').read_text())
rows=[];excluded=[]
for material in graph['materials']:
    nodes={n['name']:n for n in material['nodes']};links=material['links']
    def source(node,index):
        found=[l for l in links if l['to_node']==node['name'] and l['to_socket_index']==index]
        assert len(found)<=1
        return nodes[found[0]['from_node']] if found else None
    def value(node,name):
        socket=next(v for v in node['inputs'] if v['name']==name)
        assert not socket['linked'];return socket['default']
    hsv=[n for n in nodes.values() if n['type']=='HUE_SAT']
    if not hsv:continue
    assert len(hsv)==1;hsv=hsv[0];bs=next(n for n in nodes.values() if n['type']=='BSDF_PRINCIPLED')
    if source(bs,0) is not hsv:
        excluded.append({'name':material['name'],'reason':'HSV is not the complete base-colour chain'});continue
    h,s,v,f=(value(hsv,k) for k in ['Hue','Saturation','Value','Fac'])
    assert h==.5 and 0<=s<=1 and 0<=v<=1 and f==1,material['name']
    texture=source(hsv,4);assert texture['type']=='TEX_IMAGE'
    assert texture['projection']=='FLAT' and texture['extension']=='REPEAT' and texture['interpolation']=='Linear'
    transform=source(texture,0);assert transform['type']=='MAPPING' and transform['vector_type']=='POINT'
    coords=source(transform,0);assert coords['type']=='TEX_COORD'
    coordinate_link=next(l for l in links if l['to_node']==transform['name'] and l['to_socket_index']==0)
    assert coords['outputs'][coordinate_link['from_socket_index']]['name']=='UV'
    location=value(transform,'Location');rotation=value(transform,'Rotation');scale=value(transform,'Scale')
    assert rotation[0]==rotation[1]==0 and scale[0]>0 and scale[1]>0
    image=texture['image'];assert image['colorspace']=='sRGB' and image['source']=='FILE'
    original=read_path(image['file']);digest=hashlib.sha256(original.read_bytes()).hexdigest()
    target=write_path(f'web/assets/{version}_hsv_sources/{digest}{original.suffix.lower()}')
    if not target.exists():shutil.copyfile(original,target)
    assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
    rows.append({'name':material['name'],'objects':len(material['used_by']),'image':'./assets/'+target.parent.name+'/'+target.name,
      'image_sha256':digest,'image_bytes':target.stat().st_size,'image_size':image['size'],'saturation':s,'value':v,
      'mapping':{'location':location,'rotation':rotation,'scale':scale},'alpha':value(bs,'Alpha'),
      'operation':'neutral_hue_saturation_value_in_linear_rgb','native_render_equivalence':False})
assert len(rows)==5 and len(excluded)==1
report={'version':version,'native_sha256':graph['native_sha256'],'materials':rows,'excluded':excluded,
        'source_image_bytes_unchanged':True,'native_render_equivalence':False,'full_runtime_published':False,
        'reference':'https://raw.githubusercontent.com/blender/blender/v4.5.3/source/blender/gpu/shaders/material/gpu_shader_material_hue_sat_val.glsl',
        'derivation':'For neutral hue, 0 <= saturation <= 1, factor 1 and non-negative RGB: value * (saturation * rgb + (1-saturation) * max(rgb)).'}
write_path(f'web/assets/{version}_hsv_materials.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({'materials':len(rows),'objects':sum(x['objects'] for x in rows),'excluded':excluded,'native_render_equivalence':False}))
