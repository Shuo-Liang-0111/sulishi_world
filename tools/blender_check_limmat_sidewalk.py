"""Physical construction checks for the native G1_019 batch; not use acceptance."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT as WORKSPACE, read_path, write_path, validate_native
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
R=WORKSPACE;s=bpy.context.scene;assert s['version'].startswith(('G1_019','G1_020','G1_021','G1_022','G1_023','G1_024','G1_025','G1_026','G1_027'))
p=json.loads((read_path(R/'derived/bellevue/limmat_sidewalk/ground_input.json')).read_text(encoding='utf-8'));E=R/'evidence'/s['version'];E.mkdir(parents=True,exist_ok=True)
ground=bpy.data.collections['30_LIMMAT_SIDEWALK_GROUND'];trees=bpy.data.collections['31_LIMMAT_SIDEWALK_TREES'];assert len(trees.objects)==45
area=0
for key in ['ASPHALT','CURB_TOP','SOIL']:
 ob=bpy.data.objects['LM_'+key];t=np.asarray([v.co[:] for v in ob.data.vertices])[np.asarray([f.vertices[:] for f in ob.data.polygons])];area+=abs(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0])[:,2]).sum()/2
assert abs(area-p['report']['area_m2'])<.01,(area,p['report']['area_m2'])
soil=bpy.data.objects['LM_SOIL'];report=[]
for entry in p['pits']:
 ident=entry['source']['properties']['objectid'];obs=[bpy.data.objects[f'LM_TREE_{ident}_{part}'] for part in ['WOOD','TWIGS','LEAVES']];root=np.array([*entry['source']['geometry']['coordinates'],entry['ground_ln02_m']])-p['origin'];top=max(v.co.z for o in obs for v in o.data.vertices);assert abs(top-root[2]-entry['height_m'])<.0002
 wood=obs[0];vertices=np.asarray([v.co[:] for v in wood.data.vertices]);base=vertices[vertices[:,2]<root[2]-.05];assert len(base)>30
 gaps=[]
 for v in base:
  hit,q,_,_=soil.ray_cast(Vector((v[0],v[1],15)),Vector((0,0,-1)));assert hit,(ident,v.tolist());gaps.append(float(v[2]-q.z))
 assert max(gaps)<.002,(ident,max(gaps))
 leaves=obs[2];assert leaves.data.color_attributes.get('LeafColor')
 assert all(o['source_id']==entry['source']['id'] for o in obs)
 report.append({'id':entry['source']['id'],'height_m':float(top-root[2]),'ground_ln02_m':entry['ground_ln02_m'],'root_sample_count':len(base),'root_below_soil_range_m':[min(gaps),max(gaps)],'all_material_images_present':True})
missing=[]
for col in [ground,trees]:
 for o in col.objects:
  for m in o.data.materials:
   if not m or not m.use_nodes:continue
   for n in m.node_tree.nodes:
    if n.type=='TEX_IMAGE' and n.image and not n.image.packed_file and not Path(bpy.path.abspath(n.image.filepath,library=n.image.library)).exists():missing.append(n.image.name)
assert not missing,missing
assert len(bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects)==2039
rec={'version':s['version'],'ground_plan_area_m2':float(area),'source_area_m2':p['report']['area_m2'],'trees':report,'original_photo_nodes':2039,'missing_material_images':missing,'native_geometry_checks_passed':True,'visual_acceptance':False,'runtime_use_verified':False}
(write_path(E/'geometry_check.json')).write_text(json.dumps(rec,indent=2));print(json.dumps({'version':s['version'],'trees':len(report),'ground_area_m2':float(area),'geometry_checks':'passed'}),flush=True)
