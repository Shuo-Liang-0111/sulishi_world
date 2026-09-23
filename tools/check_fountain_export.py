"""Check actual exported material factors, deformation and native animation samples."""
import json, mmap, struct
from pathlib import Path
import numpy as np

R=Path(__file__).resolve().parents[1]; V='G1_018r3'; E=R/'evidence'/V
reference=json.loads((E/'runtime_preparation.json').read_text())
path=R/'web/assets'/f'{V}_bellevue.glb'
with path.open('rb') as f:
    magic,version,total=struct.unpack('<4sII',f.read(12)); assert magic==b'glTF' and version==2
    length,tag=struct.unpack('<II',f.read(8)); assert tag==0x4E4F534A
    j=json.loads(f.read(length)); size,tag=struct.unpack('<II',f.read(8)); assert tag==0x004E4942
    binary=f.tell(); assert binary+size==total
    raw=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
    dtypes={5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}
    widths={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
    def view_array(view_index,offset,count,dtype,width):
        view=j['bufferViews'][view_index]; dt=np.dtype(dtype)
        return np.ndarray((count,width),dtype=dt,buffer=raw,
            offset=binary+view.get('byteOffset',0)+offset,
            strides=(view.get('byteStride',dt.itemsize*width),dt.itemsize)).copy()
    def accessor(index):
        a=j['accessors'][index]; width=widths[a['type']]; dtype=dtypes[a['componentType']]
        if 'bufferView' in a: value=view_array(a['bufferView'],a.get('byteOffset',0),a['count'],dtype,width)
        else: value=np.zeros((a['count'],width),dtype=dtype)
        if 'sparse' in a:
            sparse=a['sparse']; ix=sparse['indices']; v=sparse['values']
            ids=view_array(ix['bufferView'],ix.get('byteOffset',0),sparse['count'],dtypes[ix['componentType']],1).ravel()
            value[ids]=view_array(v['bufferView'],v.get('byteOffset',0),sparse['count'],dtype,width)
        return value
    nodes=[(i,n) for i,n in enumerate(j['nodes']) if n.get('extras',{}).get('native_object')=='F59_WATER_SURFACE']
    assert len(nodes)==1
    node_index,node=nodes[0]; mesh=j['meshes'][node['mesh']]
    assert len(mesh['primitives'])==1
    primitive=mesh['primitives'][0]; assert len(primitive['targets'])==1
    p=accessor(primitive['attributes']['POSITION']); delta=accessor(primitive['targets'][0]['POSITION'])
    assert p.shape==delta.shape and np.isfinite(p).all() and np.isfinite(delta).all()
    # Blender Z-up -> glTF Y-up; preserve the stationary water boundary and floor.
    horizontal=float(np.max(np.abs(delta[:,[0,2]])))
    boundary=np.linalg.norm(p[:,[0,2]],axis=1)>1.7839
    assert horizontal<1e-7 and np.max(np.abs(delta[boundary]))<1e-7
    displacement=float(np.max(np.abs(delta[:,1])))
    assert abs(displacement-reference['max_displacement_m'])<1e-7
    water=j['materials'][primitive['material']]; extensions=water['extensions']
    assert abs(extensions['KHR_materials_ior']['ior']-1.333)<1e-6
    assert extensions['KHR_materials_transmission']['transmissionFactor']==1
    assert abs(water['pbrMetallicRoughness']['roughnessFactor']-.028)<1e-6
    line=next(m for m in j['materials'] if m['name'].endswith('F59 | mineral waterline'))
    color=line['pbrMetallicRoughness']; assert 'baseColorTexture' in color
    factor=color.get('baseColorFactor',[1,1,1,1])
    assert np.max(np.abs(np.asarray(factor)-[.62,.66,.51,1]))<1e-6,('Lost waterline material factor',factor)
    casting=next(m for m in j['materials'] if m['name']=='F59 | weathered chromium silver')
    assert 'metallicRoughnessTexture' in casting['pbrMetallicRoughness']
    animation=next(a for a in j['animations'] if a['name']=='F59_CONTINUOUS_WATER')
    channels=[c for c in animation['channels'] if c['target']['node']==node_index and c['target']['path']=='weights']
    assert len(channels)==1
    channel=channels[0]; sampler=animation['samplers'][channel['sampler']]
    assert sampler.get('interpolation','LINEAR')=='LINEAR'
    times=accessor(sampler['input']).ravel(); weights=accessor(sampler['output']).ravel()
    assert len(times)==len(weights) and abs(times[0])<1e-7
    expected_duration=80/reference['fps']; assert abs(times[-1]-expected_duration)<1e-6
    differences=[]
    for item in reference['weights']:
        t=(item['frame']-1)/reference['fps']; value=float(np.interp(t,times,weights))
        error=abs(value-item['weight']); assert error<1e-6
        differences.append({'frame':item['frame'],'weight_error':error})
    assert 'NORMAL' in primitive['targets'][0], 'Animated normals missing'
    report={'version':V,'actual_glb':path.name,'water_vertices_after_export':len(p),
        'max_displacement_m':displacement,'horizontal_displacement_m':horizontal,'boundary_stationary':True,
        'normal_morph_present':True,'native_keyframe_comparisons':differences,
        'animation_duration_s':float(times[-1]),'exported_water_ior':extensions['KHR_materials_ior']['ior'],
        'mineral_waterline_factor':factor,'casting_roughness_texture_preserved':True,
        'runtime_visual_accepted':False,'natural_use_accepted':False}
    raw.close()
(E/'fountain_export_check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
