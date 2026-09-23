"""Specific source-position, ground-contact and facade-connection checks."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_011r4';trees=[]
for ident,prefix,soilname,ip in [(119962,'HB_TREE_119962','HB_SIDEWALK_SOIL','derived/haus_bellevue/tree_119962_input.json'),(69773,'BE_TREE_69773','BE_WEST_TREE_SOIL','derived/bellevue/west_context/tree_69773_input.json')]:
 d=json.loads((R/ip).read_text());root=np.array([*d['source']['geometry']['coordinates'],d['ground_ln02_m']])-np.array(d['origin']);obs=[bpy.data.objects[prefix+'_'+x] for x in ['WOOD','TWIGS','LEAVES']];top=max(v.co.z for o in obs for v in o.data.vertices);error=abs(top-root[2]-d['height_m']);assert error<1e-4
 wood=obs[0];soil=bpy.data.objects[soilname];lo=min(v.co.z for v in wood.data.vertices);gap=[]
 for v in wood.data.vertices:
  if abs(v.co.z-lo)<.001:
   hit,p,_,_=soil.ray_cast(Vector((v.co.x,v.co.y,20)),Vector((0,0,-1)));assert hit;gap.append(v.co.z-p.z)
 assert max(gap)<0
 uv=wood.data.uv_layers.active;negative=[li for p in wood.data.polygons if p.material_index==1 for li in p.loop_indices if uv.data[li].uv.y<0];assert not negative
 trees.append({'tree':ident,'height_error_m':error,'root_base_below_soil_range_m':[min(gap),max(gap)],'root_samples':len(gap),'negative_trunk_v_count':len(negative),'individual_form_inferred':True})
d=json.loads((R/'derived/haus_bellevue/upper_input.json').read_text());f=d['frontage'];C=np.array(f['C']);out=np.array(f['out']);fixed={}
for ob in bpy.data.collections['17_HAUS_BELLEVUE_UPPER'].objects:
 if ob.name.startswith('HU_MAIN_') and any(ob.name.endswith(x) for x in ['_RAIL','_SLAB','_CORBEL']):
  back=min(float((np.array(v.co[:2])-C)@out) for v in ob.data.vertices);assert back<-.12;fixed[ob.name]=back
report={'version':s['version'],'trees':trees,'balcony_members_reaching_wall':fixed,'source_objects_retained':len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects),'not_collision_or_visual_acceptance':True}
(R/'evidence'/s['version']/'geometry_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
