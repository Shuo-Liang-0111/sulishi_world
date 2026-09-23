"""Finish the current walking strip and replace a source-located contact-wire mast."""
import bpy,bmesh,ast,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_009r1'
building=bpy.data.collections['16_HAUS_BELLEVUE_STREET'];tree=ast.parse((R/'tools/blender_build_bellevue.py').read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','box','lathe','tube']],type_ignores=[]),'helpers','exec'))
record=json.loads((R/'derived/haus_bellevue/mast1794.json').read_text());p=record['properties'];C=np.array(record['geometry']['coordinates'][0])-[2683775,1246700];right=np.array([1.,0.]);front=np.array([0.,1.]);FLOOR=0
def P(u,v,z):return (C[0]+u,C[1]+v,z)
metal=bpy.data.materials.new('HB | painted grey infrastructure steel');metal.use_nodes=True;bs=next(n for n in metal.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.29,.32,.31,1);bs.inputs['Roughness'].default_value=.46;bs.inputs['Metallic'].default_value=.24
dark=bpy.data.materials['BE | dark structural metal'];ground=bpy.data.objects['HB_SIDEWALK_ASPHALT'].ray_cast(Vector((*C,40)),Vector((0,0,-1)));assert ground[0];z=ground[1].z;top=p['hoehemastok']-400
shaft=lathe('HB_MAST_1794_SHAFT',[(0,p['hoehemastuk']-400),(.174,p['hoehemastuk']-400),(.173,z+.13),(.143,z+.24),(.135,z+1.9),(.101,z+6.5),(.078,top-.08),(.078,top),(0,top)],metal,world_center=C.tolist(),steps=48)
for k,h in enumerate([.20,2.0,6.3,8.8]):
 radius=.178 if k==0 else .145 if k==1 else .108 if k==2 else .096
 lathe(f'HB_MAST_1794_BAND_{k}',[(radius-.006,z+h-.034),(radius+.006,z+h-.025),(radius+.006,z+h+.025),(radius-.006,z+h+.034)],metal,world_center=C.tolist(),steps=48)
cover=box('HB_MAST_1794_SERVICE_COVER',(0,-.132,z+.76),(.15,.018,.43),metal,.015)
for ob in [o for o in building.objects if o.name.startswith('HB_MAST_1794')]:ob['source_id']=record['id'];ob['place']='Haus Bellevue sidewalk';ob['evidence_basis']='Official VBZ XY and top420.2m/base408.22m. Ground follows reconstructed AV35946. Taper, cover, bands and finish inferred.';ob['collision_role']='solid_pending_runtime';ob['quality_status']='working'
cutpath=R/'derived/bellevue/west_context/haus_walk_mast_photo_cut.json';cut=json.loads(cutpath.read_text());ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};orig={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for p in cut['overrides']:
 ob=ctx[str(p['node'])];src=orig[str(p['node'])];vv=np.array(p['vertices']);uvv=np.array(p['uv_source_v_unflipped']);me=bpy.data.meshes.new('HB_R2_CONTEXT_'+str(p['node']));me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.astype(np.float32).reshape(-1));ob.data=me;ob['construction_mask']=cut['mask_basis']
s['version']='G1_009r2';s['photo_cut_file']=str(cutpath.relative_to(R));s.camera=bpy.data.objects['HB_QA_ALONG'];bpy.context.view_layer.update();native=R/'native/G1_009r2_haus_frontage_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=s['version'],native=str(native),source_cut_file=s['photo_cut_file'],accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2))
out=R/'evidence/G1_009r2';out.mkdir(exist_ok=True);(out/'refinement.json').write_text(json.dumps({'version':s['version'],'mast':record['id'],'mast_ground_ln02':z+400,'mast_top_ln02':top+400,'photo_replacement':cut['haus_mast'],'remaining':'Original upper facade, corner tower, neighboring fronts and tree119962 are not rebuilt or accepted.','accepted':False},indent=2));print(json.dumps({'version':s['version'],'native':str(native),'accepted':False}))
