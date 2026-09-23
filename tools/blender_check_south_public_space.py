"""Verify actual saved-source dimensions and contacts; not runtime walk acceptance."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version'].startswith('G1_013');d=json.loads((R/'derived/bellevue/south_context/tree_inputs.json').read_text(encoding='utf-8'));report={'version':s['version'],'trees':[],'ground':{},'cameras':[],'accepted':False}
soil=bpy.data.objects['BS_SOIL'];s.view_layers[0].update()
for item in d['trees']:
 ident=item['source']['properties']['objectid'];root=np.array([*item['source']['geometry']['coordinates'],item['ground_ln02_m']])-np.array(item['origin']);obs=[bpy.data.objects[f'BS_TREE_{ident}_{role}'] for role in ['WOOD','TWIGS','LEAVES']];top=max(v.co.z for ob in obs for v in ob.data.vertices);error=abs(top-root[2]-item['height_m']);assert error<.0001
 wood=obs[0];base=np.array([wood.data.vertices[i].co[:] for i in range(80)]);center=base[:,:2].mean(0);xyerr=float(np.linalg.norm(center-root[:2]));assert xyerr<.003,xyerr
 contacts=[]
 for point in base:
  hit,p,_,_=soil.ray_cast(Vector((point[0],point[1],30)),Vector((0,0,-1)));assert hit;contacts.append(point[2]-p.z)
 assert max(contacts)<0 and min(contacts)>-.14
 uv=wood.data.uv_layers.active;assert all(uv.data[li].uv.y>=0 for p in wood.data.polygons if p.material_index==1 for li in p.loop_indices)
 report['trees'].append({'source_id':item['source']['id'],'height_error_m':float(error),'root_ring_center_error_m':xyerr,'root_base_below_soil_range_m':[float(min(contacts)),float(max(contacts))],'contact_samples':len(contacts),'form_inferred':True})
areas=[];slopes=[]
for name in ['BS_ASPHALT','BS_CURB_TOP','BS_SOIL']:
 ob=bpy.data.objects[name];me=ob.data
 for p in me.polygons:
  v=np.array([me.vertices[i].co[:] for i in p.vertices]);n=np.cross(v[1]-v[0],v[2]-v[0]);areas.append(abs(n[2])/2)
  if abs(n[2])>1e-8:slopes.append(float(np.linalg.norm(n[:2])/abs(n[2])))
expected=json.loads((R/'derived/bellevue/south_context/platform_input.json').read_text(encoding='utf-8'))['report']['area_m2'];assert abs(sum(areas)-expected)<.01
report['ground']={'projected_area_m2':sum(areas),'source_area_m2':expected,'slope_quantiles':np.quantile(slopes,[.5,.9,.99,1]).tolist(),'note':'Float32 mesh includes tiny sliver faces; peak normal needs review separately from area-wide grade.'}
for name in ['BE_QA_SOUTH_APPROACH','BE_QA_SOUTH_WALK','BE_QA_SOUTH_TREE_BASE']:
 ob=bpy.data.objects[name];report['cameras'].append({'name':name,'eye_height_m':ob['eye_height_m'],'stored_ground_local':ob['floor_height_local']});assert ob['eye_height_m']==1.65
report['source_nodes_retained']=len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects);assert report['source_nodes_retained']==2039;report['not_visual_or_collision_acceptance']=True
(R/'evidence'/s['version']/'geometry_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
