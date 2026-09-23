import bpy,bmesh,json,numpy as np,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene;assert scene['version']=='G1_007'
path=ROOT/'derived/bellevue/transport/road_input.json';payload=json.loads(path.read_text())
for part in payload['pieces']:
    ob=bpy.data.objects.get('BE_ROAD_'+part['id'])
    if ob is None:assert not part['triangles'];continue
    mat=ob.data.materials[0];tt=np.asarray(part['triangles']);me=bpy.data.meshes.new(ob.name+'_grade_r1')
    me.from_pydata(tt.reshape(-1,3).tolist(),[],np.arange(tt.size//3).reshape(-1,3).tolist());me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=.000001);bm.to_mesh(me);bm.free();me.materials.append(mat)
    if part['kind']=='road_asphalt':
        uv=me.uv_layers.new(name='real_scale_2.05m')
        for l in me.loops:
            v=me.vertices[l.vertex_index].co;uv.data[l.index].uv=(v.x/2.05,v.y/2.05)
    ob.data=me;ob['evidence_basis']=payload['report']['height_basis']+' Local plane gradients regularised to regional grade in underdetermined narrow/occluded areas.'
    ob['derived_source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
# A true track-side eye-level view complements the canopy-front and overview views.
cd=bpy.data.cameras.new('BE_QA_TRACK_NEAR');cam=bpy.data.objects.new('BE_QA_TRACK_NEAR',cd);bpy.data.collections['90_REVIEW_CAMERAS'].objects.link(cam)
cam.location=(2683544-2683775,1246841-1246700,9.95);cd.lens=32
target=Vector((2683562-2683775,1246853-1246700,8.65));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
scene['version']='G1_007r1';scene.camera=cam
native=ROOT/'native/G1_007r1_station_roads_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
record=json.loads((ROOT/'runtime/station_road_working.json').read_text());record.update(version=scene['version'],native=str(native),road_input_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
(ROOT/'runtime/station_road_working.json').write_text(json.dumps(record,indent=2))
out=ROOT/'evidence'/scene['version'];out.mkdir(exist_ok=True);(out/'road_support.json').write_text(json.dumps(payload['report'],indent=2))
print(json.dumps(record))
