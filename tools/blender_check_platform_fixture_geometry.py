"""Check actual world transforms, source tops, platform footing and two-sided print orientation."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_012r4';s.view_layers[0].update();deps=bpy.context.evaluated_depsgraph_get();platform=bpy.data.objects['BE_WEST_PLATFORM'];report={'version':s['version'],'masts':[],'footings':[],'labels':[],'accepted':False}
for pref,ident,ip in [('CF',1800,'corner_fixtures'),('CF2',1793,'west_end_fixtures')]:
 d=json.loads((R/f'derived/bellevue/{ip}/input.json').read_text());ob=bpy.data.objects[f'{pref}_MAST_{ident}_SHAFT'];vv=np.array([list(ob.matrix_world@v.co) for v in ob.data.vertices]);xy=np.array(d['mast']['geometry']['coordinates'][0])-np.array(d['origin'][:2]);center=(vv[:,:2].max(0)+vv[:,:2].min(0))/2;zmax=vv[:,2].max();err=float(np.linalg.norm(center-xy));zerr=abs(zmax-(d['mast']['properties']['hoehemastok']-400));assert err<.001 and zerr<.001
 report['masts'].append({'id':ident,'xy_center_error_m':err,'top_error_m':float(zerr),'source_base_to_reconstructed_ground_m':d['mast']['properties']['hoehemastuk']-400-d['mast_ground_local']})
 for i in range(3):
  ob=bpy.data.objects[f'{pref}_INFO_GROUND_SLEEVE_{i}'];ev=ob.evaluated_get(deps);me=ev.to_mesh();vv=np.array([list(ob.matrix_world@v.co) for v in me.vertices]);ev.to_mesh_clear();center=vv[:,:2].mean(0);hit,p,_,_=platform.ray_cast(Vector((*center,40)),Vector((0,0,-1)));assert hit;bottom=vv[:,2].min()-p.z;top=vv[:,2].max()-p.z;assert bottom<.001 and top>0
  report['footings'].append({'name':ob.name,'sleeve_bottom_relative_ground_m':float(bottom),'sleeve_top_relative_ground_m':float(top)})
 for suffix in ['INFO_NAME_TEXT','INFO_MODE_TEXT','INFO_RETURN_TITLE']:
  a=bpy.data.objects[pref+'_'+suffix];b=bpy.data.objects[pref+'_'+suffix+'_REVERSE'];na=a.matrix_world.to_quaternion()@Vector((0,0,1));nb=b.matrix_world.to_quaternion()@Vector((0,0,1));dot=na.dot(nb);assert dot<-.999;report['labels'].append({'name':a.name,'opposing_normals_dot':dot})
report['source_nodes_retained']=len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects);report['not_runtime_collision_or_accessibility_acceptance']=True
(R/'evidence'/s['version']/'geometry_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
