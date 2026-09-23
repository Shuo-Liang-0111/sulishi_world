"""Remove diagnosed remnants and set review eye levels from constructed sidewalk."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_009'
path=R/'derived/bellevue/west_context/haus_frontage_r1_photo_cut.json';cut=json.loads(path.read_text());ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};orig={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for p in cut['overrides']:
 ob=ctx[str(p['node'])];src=orig[str(p['node'])];vv=np.array(p['vertices']);uvv=np.array(p['uv_source_v_unflipped']);me=bpy.data.meshes.new('HB_R1_CONTEXT_'+str(p['node']));me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.astype(np.float32).reshape(-1));ob.data=me;ob['construction_mask']=cut['mask_basis']
d=json.loads((R/'derived/haus_bellevue/build_input.json').read_text());f=d['frontage'];C=np.array(f['C']);rt=np.array(f['right']);normal=np.array(f['out'])
def pos(u,v,z):return Vector((*list(C+u*rt+v*normal),z))
for name,u,v,target in [('HB_QA_ALONG',-1.3,3.3,(19,.05,10.39)),('HB_QA_ENTRY',16.1,3.8,(16.1,-.5,10.29)),('HB_QA_REVERSE',27.8,3.3,(6,.02,10.29))]:
 c=bpy.data.objects[name];xy=pos(u,v,50);hit,p,_,_=bpy.data.objects['HB_SIDEWALK_ASPHALT'].ray_cast(xy,Vector((0,0,-1)))
 assert hit, 'Review camera should stand on the authored sidewalk'
 c.location=Vector((xy.x,xy.y,p.z+1.65));c.rotation_euler=(pos(*target)-c.location).to_track_quat('-Z','Y').to_euler();c['floor_height_local']=p.z;c['eye_height_m']=1.65
 if name=='HB_QA_ENTRY':c.data.lens=24
s['version']='G1_009r1';s['photo_cut_file']=str(path.relative_to(R));s.camera=bpy.data.objects['HB_QA_ALONG'];bpy.context.view_layer.update();native=R/'native/G1_009r1_haus_frontage_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=s['version'],native=str(native),source_cut_file=s['photo_cut_file'],accepted=False,not_published=True,next='Review both sidewalk directions and doorway, export and compare actual runtime before publication');(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2))
out=R/'evidence/G1_009r1';out.mkdir(exist_ok=True);(out/'refinement.json').write_text(json.dumps({'version':s['version'],'source_remnants':cut['haus_remnant'],'actual_ground_sampled_camera_eyes':True,'accepted':False},indent=2))
print(json.dumps({'version':s['version'],'native':str(native),'accepted':False}))
