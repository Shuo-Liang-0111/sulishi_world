"""Actual float32 meshes, source roof alignment, contacts, and opening identities."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;V=s['version'];assert V.startswith('G1_014');d=json.loads((R/'derived/bellevue/south_service/input.json').read_text());g=json.loads((R/'derived/bellevue/south_service/build_input.json').read_text());td=json.loads((R/'derived/bellevue/south_service/trees_input.json').read_text(encoding='utf-8'));report={'version':V,'trees':[],'roofs':[],'door_openings':[],'accepted':False,'runtime_use_verified':False};s.view_layers[0].update()
for t in td['trees']:
 ident=t['source']['properties']['objectid'];root=np.array([*t['source']['geometry']['coordinates'],t['ground_ln02_m']])-np.array(t['origin']);obs=[bpy.data.objects[f'BS_TREE_{ident}_{role}'] for role in ['WOOD','TWIGS','LEAVES']];top=max(v.co.z for ob in obs for v in ob.data.vertices);err=abs(top-root[2]-t['height_m']);assert err<.0001
 vv=np.array([obs[0].data.vertices[i].co[:] for i in range(80)]);xyerr=float(np.linalg.norm(vv[:,:2].mean(0)-root[:2]));assert xyerr<.003;contacts=[]
 for pt in vv:
  hit,q,_,_=bpy.data.objects['BS_SOIL'].ray_cast(Vector((pt[0],pt[1],30)),Vector((0,0,-1)));assert hit;contacts.append(pt[2]-q.z)
 assert max(contacts)<0 and min(contacts)>-.14
 report['trees'].append({'id':ident,'source_height_m':t['height_m'],'height_error_m':float(err),'root_center_error_m':xyerr,'root_below_soil_m':[float(min(contacts)),float(max(contacts))]})
for role,typ in [('SOFFIT','GroundSurface'),('FASCIA','WallSurface'),('CANOPY_ROOF','RoofSurface')]:
 source=np.array(next(p for p in d['source_parts'] if p['type']==typ and p['kind']=='EO13')['triangles']).reshape(-1,3);actual=np.array([v.co[:] for v in bpy.data.objects['SV_SOURCE_'+role].data.vertices]);error=float(max(np.linalg.norm(source-v,axis=1).min() for v in actual));assert error<.00005
 report['roofs'].append({'name':role,'largest_vertex_source_distance_m':error})
me=bpy.data.objects['SV_LANDING_ASPHALT'].data;v=np.array([v.co[:] for v in me.vertices]);tt=np.array([list(p.vertices) for p in me.polygons]);a=v[tt];n=np.cross(a[:,1]-a[:,0],a[:,2]-a[:,0]);areas=abs(n[:,2])/2;slopes=np.linalg.norm(n[:,:2],axis=1)/np.maximum(abs(n[:,2]),1e-20);valid=areas>1e-6;tiny=(areas>1e-10)&~valid
report['landing']={'projected_area_m2':float(areas.sum()),'source_target_area_m2':g['apron_area_m2'],'maximum_slope_faces_over_1mm2':float(slopes[valid].max()),'slope_quantiles':np.quantile(slopes[valid],[.5,.9,.99,1]).tolist(),'tiny_faces':int(tiny.sum()),'tiny_total_area_m2':float(areas[tiny].sum()),'tiny_max_slope':float(slopes[tiny].max()) if tiny.any() else None};assert abs(areas.sum()-g['apron_area_m2'])<.01
for ob in bpy.data.collections['24_BELLEVUE_SERVICE_PAVILION'].objects:
 if ob.get('interaction_role')=='hinged_door':report['door_openings'].append({'name':ob.name,'opening_m':ob.get('clear_opening_m'),'state':ob.get('state'),'children':len(ob.children),'runtime_enabled':ob.get('runtime_enabled',False)});assert len(ob.children)>0
report['original_source_nodes']=len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects);assert report['original_source_nodes']==2039
report['empty_working_photo_nodes']=[o.get('source_node') for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects if len(o.data.vertices)==0]
(R/'evidence'/V/'geometry_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
