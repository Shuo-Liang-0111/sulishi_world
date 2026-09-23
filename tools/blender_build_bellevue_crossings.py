import bpy,json,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene;assert scene['version']=='G1_007r4'
path=ROOT/'derived/bellevue/transport/crossings_input.json';data=json.loads(path.read_text())
assert data['report']['road_input_sha256']==hashlib.sha256((ROOT/'derived/bellevue/transport/road_input.json').read_bytes()).hexdigest()
col=bpy.data.collections['11_BELLEVUE_STREET_SURFACES']
# A failed unsaved camera check can leave this bounded paint pass in memory.
# Replace only its named objects; no source geometry or previous native is removed.
for item in data['items']:
    old=bpy.data.objects.get(item['id'])
    if old:
        assert old.get('surface_role')=='crossing_paint'
        bpy.data.objects.remove(old,do_unlink=True)
mat=bpy.data.materials.get('BE | Swiss yellow crossing paint') or bpy.data.materials.new('BE | Swiss yellow crossing paint');mat.use_nodes=True
bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.72,.51,.025,1);bs.inputs['Roughness'].default_value=.77
mat['evidence_basis']='Yellow crossing bars observed in SWISSIMAGE; reflectance and roughness inferred, no photography projected onto road'
mat['source_image']='sources/references/swissimage-bellevue-detail.jpg'
for item in data['items']:
    t=np.array(item['triangles']);me=bpy.data.meshes.new(item['id']);me.from_pydata(t.reshape(-1,3).tolist(),[],np.arange(t.size//3).reshape(-1,3).tolist());me.update();me.materials.append(mat)
    ob=bpy.data.objects.new(item['id'],me);col.objects.link(ob)
    for k,v in item['properties'].items():ob[k]=v
    ob['evidence_basis']=item['properties']['plan_basis'];ob['source_id']=item['properties']['route_id'];ob['surface_role']='crossing_paint';ob['collision_role']='visual_coating_not_a_separate_obstacle';ob['quality_status']=data['report']['status']
road=json.loads((ROOT/'derived/bellevue/transport/road_input.json').read_text());tt=np.array([t for p in road['pieces'] if p['kind']=='road_asphalt' for t in p['triangles']]);xy=np.array([2683512-2683775,1246854-1246700]);order=np.argsort(np.linalg.norm(tt[:,:,:2].mean(axis=1)-xy,axis=1));floor=None
for idx in order[:30]:
    t=tt[idx];a=(t[1:,:2]-t[0,:2]).T
    if abs(np.linalg.det(a))<1e-10:continue
    w=np.linalg.solve(a,xy-t[0,:2])
    if min(w)>=-1e-5 and sum(w)<=1.00001:floor=t[0,2]+w@(t[1:,2]-t[0,2]);break
assert floor is not None,'Human review camera must stand over authored surface'
cd=bpy.data.cameras.new('BE_QA_CROSSING_WEST');ob=bpy.data.objects.new(cd.name,cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(ob);ob.location=(*xy,float(floor+1.65));cd.lens=32
target=Vector((2683525-2683775,1246858-1246700,float(floor+1.35)));ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
scene.camera=ob;scene['version']='G1_007r5';native=ROOT/'native/G1_007r5_station_roads_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
record=json.loads((ROOT/'runtime/station_road_working.json').read_text());record.update(version=scene['version'],native=str(native),crossing_input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),crossing_report=data['report'])
(ROOT/'runtime/station_road_working.json').write_text(json.dumps(record,indent=2));(ROOT/'evidence'/scene['version']).mkdir(exist_ok=True)
print(json.dumps({'version':scene['version'],'paint_bars':len(data['items']),'native':str(native)}))
