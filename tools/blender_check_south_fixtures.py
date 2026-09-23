"""Contacts, surveyed tops and real bin aperture; no runtime-use claims."""
import bpy,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_013r2';D=R/'derived/bellevue/south_context';d=json.loads((D/'fixtures_input.json').read_text());info=json.loads((D/'info/input.json').read_text());out={'version':s['version'],'masts':[],'bin':{},'ground_microfaces':{},'accepted':False,'runtime_collision_or_use_checked':False};bpy.context.view_layer.update()
def verts(ob):
 ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();v=np.array([ob.matrix_world@p.co for p in me.vertices]);ev.to_mesh_clear();return v
for src,z in [(info['mast'],info['mast_ground_local']),(d['mast2']['source'],d['mast2']['ground_local'])]:
 ident=src['properties']['objectid'];v=verts(bpy.data.objects[f'BSF_MAST_{ident}_SHAFT']);top=float(v[:,2].max());err=abs(top+400-src['properties']['hoehemastok']);assert err<.005
 out['masts'].append({'source_id':src['id'],'top_error_m':err,'nominal_ground_local':z,'source_bottom_ln02':src['properties']['hoehemastuk'],'ground_minus_source_bottom_m':z+400-src['properties']['hoehemastuk']})
c=np.array(d['bin']['source']['geometry']['coordinates'][0])-[2683775,1246700];floor=d['bin']['ground_local'];theta=math.radians(float(d['bin']['source']['properties']['orientierung']));front=np.array([math.sin(theta),math.cos(theta)]);shell=bpy.data.objects['BSF_BIN631_SHEET_SHELL'];hits=[]
for z,expected in [(.84,.775),(.951,1.222)]:
 start=Vector((*c+front,floor+z));hit,p,n,idx=shell.ray_cast(start,Vector((*-front,0)));assert hit;dist=(p-start).length;assert abs(dist-expected)<.005,(z,dist);hits.append({'height_above_ground':z,'shell_ray_distance_m':dist})
vs=np.concatenate([verts(o) for o in bpy.data.collections['23_BELLEVUE_SOUTH_FIXTURES'].objects if o.name.startswith('BSF_BIN631_')]);height=float(vs[:,2].max()-vs[:,2].min());assert abs(height-1.089)<.0001
hit,p,n,i=bpy.data.objects['BS_ASPHALT'].ray_cast(Vector((*c,30)),Vector((0,0,-1)));assert hit;contact=float(vs[:,2].min()-p.z);assert abs(contact)<.001
out['bin']={'source_id':d['bin']['source']['id'],'overall_height_m':height,'base_contact_error_m':contact,'shell_aperture_rays':hits,'nominal_shell_diameter_m':.45,'lid_diameter_m':.454,'variant_inferred':True}
tiny=[];large=[]
for name in ['BS_ASPHALT','BS_CURB_TOP','BS_SOIL']:
 ob=bpy.data.objects[name]
 for f in ob.data.polygons:
  v=np.array([ob.data.vertices[i].co[:] for i in f.vertices]);n=np.cross(v[1]-v[0],v[2]-v[0]);area=abs(n[2])*.5
  if area<1e-12:continue
  slope=float(np.linalg.norm(n[:2])/abs(n[2]));(tiny if area<1e-6 else large).append((area,slope))
out['ground_microfaces']={'area_threshold_m2':1e-6,'microface_count':len(tiny),'microface_area_m2':sum(x[0] for x in tiny),'max_nonmicroface_slope':max(x[1] for x in large),'max_microface_slope':max(x[1] for x in tiny),'note':'Float32 triangulation normals on microscopic slivers; not an accessibility assessment.'}
out['source_nodes_retained']=len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects);assert out['source_nodes_retained']==2039
(R/'evidence'/s['version']/'fixture_geometry_check.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
