"""020r2: repair rejected repeated rain bands and keep interior faces clean."""
from pathlib import Path
import hashlib
import json
import re
import bpy
import numpy as np

root=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version']=='G1_020r1'
plan=json.loads((root/'derived/bellevue/utoquai_kiosk/build_input.json').read_text())
record=json.loads((root/'evidence/G1_020r1/refinement.json').read_text())
clean=bpy.data.materials['UR | aged warm pale enamel']
paint=clean.copy();paint.name='UR | exterior enamel bounded physical runoff'
nodes,links=paint.node_tree.nodes,paint.node_tree.links
bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
uv=nodes.new('ShaderNodeUVMap');uv.uv_map='UR_weather_runoff'
sep=nodes.new('ShaderNodeSeparateXYZ');links.new(uv.outputs[0],sep.inputs[0])
coord=nodes.new('ShaderNodeTexCoord');gen=nodes.new('ShaderNodeSeparateXYZ');links.new(coord.outputs['Generated'],gen.inputs[0])

def mathnode(op,a,b=None):
    n=nodes.new('ShaderNodeMath');n.operation=op
    for i,v in enumerate([a,b]):
        if v is None:continue
        if isinstance(v,(int,float)):n.inputs[i].default_value=v
        else:links.new(v,n.inputs[i])
    return n.outputs[0]
def noise_at(scale):
    stretch=nodes.new('ShaderNodeVectorMath');stretch.operation='MULTIPLY';stretch.inputs[1].default_value=scale;links.new(uv.outputs[0],stretch.inputs[0])
    noise=nodes.new('ShaderNodeTexNoise');noise.noise_dimensions='3D';noise.inputs['Scale'].default_value=1;noise.inputs['Detail'].default_value=2
    links.new(stretch.outputs[0],noise.inputs['Vector']);return noise.outputs['Fac']

# Distance below the actual top seam is in metres, not object-normalized height.
# Broad variation changes the length of each narrow trace; no full-door stripes.
length=mathnode('ADD',.015,mathnode('MULTIPLY',noise_at((1.3,0,0)),.10))
fade=mathnode('EXPONENT',mathnode('MULTIPLY',mathnode('DIVIDE',sep.outputs['Y'],length),-1))
amplitude=mathnode('MINIMUM',mathnode('MAXIMUM',mathnode('MULTIPLY',mathnode('SUBTRACT',noise_at((14,2.2,1)),.42),3.8),0),1)
runoff=mathnode('MULTIPLY',mathnode('MULTIPLY',fade,amplitude),.60)
splash=mathnode('MULTIPLY',mathnode('POWER',mathnode('SUBTRACT',1,gen.outputs['Z']),24),.06)
factor=mathnode('MINIMUM',mathnode('ADD',runoff,splash),.65)
color=nodes.new('ShaderNodeValToRGB');color.color_ramp.elements[0].color=(.59,.61,.575,1);color.color_ramp.elements[1].color=(.265,.282,.234,1)
links.new(factor,color.inputs[0]);links.new(color.outputs['Color'],bsdf.inputs['Base Color'])
rough=mathnode('ADD',.44,mathnode('MULTIPLY',factor,.16));links.new(rough,bsdf.inputs['Roughness'])
paint['finish_basis']='020r1 actual staff/counter images rejected repetitive full-height streaks and dirty interior faces. Use exterior faces only, actual metres below seams, varying short runoff and very weak lower splash. Inferred wear, not a scan.'

changes=[]
for name in record['weathered_exterior_panels']:
    ob=bpy.data.objects[name];data=ob.data
    before=hashlib.sha256(np.array([v.co[:] for v in data.vertices]).tobytes()).hexdigest()
    if name.startswith('UR_STAFF_'):idx=1
    elif name.startswith('UR_E'):idx=int(re.match(r'UR_E(\d)_',name).group(1))
    else:idx=int(re.match(r'UR_HATCH_(\d)_',name).group(1))
    e=plan['source']['edges'][idx];normal=np.r_[e['outward_xy'],0]
    a=np.array(e['a_lv95'])-np.array(plan['source']['origin'][:2]);b=np.array(e['b_lv95'])-np.array(plan['source']['origin'][:2]);t=(b-a)/np.linalg.norm(b-a)
    zmax=max(v.co.z for v in data.vertices)
    phase=int(hashlib.sha256(name.encode()).hexdigest()[:8],16)/0xffffffff*9
    layer=data.uv_layers.new(name='UR_weather_runoff')
    for loop in data.loops:
        p=data.vertices[loop.vertex_index].co
        layer.data[loop.index].uv=(float(np.dot(np.array(p[:2])-a,t)+phase),float(zmax-p.z))
    data.uv_layers.active_index=0;data.uv_layers[0].active_render=True
    data.materials.clear();data.materials.append(paint);data.materials.append(clean)
    exterior=[];inside=[]
    for face in data.polygons:
        outside=np.dot(np.array(face.normal),normal)>.85
        face.material_index=0 if outside else 1
        (exterior if outside else inside).append(face.index)
    assert exterior and inside
    assert hashlib.sha256(np.array([v.co[:] for v in data.vertices]).tobytes()).hexdigest()==before
    changes.append({'object':name,'weathered_exterior_faces':exterior,'clean_other_faces':inside,'metre_based_runoff_uv':layer.name,'vertex_sha256_unchanged':before})
assert bpy.data.objects['UR_FRIDGE_BODY'].data.materials[0]==clean
scene['version']='G1_020r2';bpy.context.view_layer.update()
evidence=root/'evidence/G1_020r2';evidence.mkdir(exist_ok=True)
(evidence/'coating_repair.json').write_text(json.dumps({'version':'G1_020r2','base':'G1_020r1','changes':changes,'reason':'Actual staff/counter/north views reveal repeated long vertical streaks and inappropriate weathering on the indoor door face.','all_geometric_positions_unchanged':True,'lights_cameras_unchanged':True,'natural_use_verified':False,'native_saved':False,'visual_acceptance':False},indent=2),encoding='utf-8')
print(json.dumps({'version':scene['version'],'revised_panels':len(changes),'interior_faces_clean':True,'geometry_unchanged':True}))
