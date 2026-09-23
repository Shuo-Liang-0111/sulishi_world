"""Respond to actual interior image: continuous basin assembly, finish, grounded benches."""
import bpy,bmesh,json,math,ast,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_014r1';d=json.loads((R/'derived/bellevue/south_service/input.json').read_text());g=json.loads((R/'derived/bellevue/south_service/build_input.json').read_text());C=np.array(d['center_lv95'])-np.array(d['origin'][:2]);right=np.array(d['axis_u']);front=np.array(d['axis_v']);FLOOR=g['floor_local_inferred'];building=bpy.data.collections['24_BELLEVUE_SERVICE_PAVILION'];H=11.384-FLOOR
src=ast.parse((R/'tools/blender_build_bellevue.py').read_text());exec(compile(ast.Module(body=[n for n in src.body if isinstance(n,ast.FunctionDef) and n.name in ['mesh','triangles','box','P']],type_ignores=[]),'geometry','exec'))
wall=bpy.data.materials['HB | shop interior mineral paint'].copy();wall.name='SV | public interior pale mineral finish';bs=next(n for n in wall.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
for link in list(bs.inputs['Base Color'].links):wall.node_tree.links.remove(link)
bs.inputs['Base Color'].default_value=(.68,.685,.66,1);bs.inputs['Roughness'].default_value=.79
for ob in building.objects:
 if ob.type=='MESH':
  for i,m in enumerate(ob.data.materials):
   if m.name=='HB | shop interior mineral paint':ob.data.materials[i]=wall
 if ob.type=='LIGHT':ob.data.energy=105;ob.data.color=(1,.965,.91)
counter=bpy.data.materials['SV | charcoal composite basin'];repairs=[]
for p in json.loads((R/'derived/bellevue/south_service/countertops.json').read_text()):
 tt=[[P(a,b,.858) for a,b in t] for t in p['triangles_uv']];ob=triangles('SV_CONTINUOUS_BASIN_TOP_'+p['side'],tt,counter,'Dated interior photo shows continuous charcoal counter; exact fabrication inferred');mod=ob.modifiers.new('20mm counter thickness','SOLIDIFY');mod.thickness=.020;mod=ob.modifiers.new('Soft composite edge','BEVEL');mod.width=.003;mod.segments=3
 u0,v0,u1,v1=p['uv_bounds'];outward=u0 if p['sg']<0 else u1;box('SV_CONTINUOUS_BASIN_FACE_'+p['side'],(outward,(v0+v1)/2,.733),(.026,v1-v0,.23),counter,.006)
 for v in [v0,v1]:box('SV_CONTINUOUS_BASIN_END_'+p['side']+str(v),((u0+u1)/2,v,.733),(u1-u0,.026,.23),counter,.006)
for ob in building.objects:
 if ob.name.startswith('SV_BENCH_') and ob.type in ['MESH','CURVE']:
  name='_'.join(ob.name.split('_')[:3]);repairs.append(name)
# Seat/frames move as one assembly to the highest supporting foot, extending each
# foot down to the actual local grade where necessary; no hovering feet.
apron=bpy.data.objects['SV_LANDING_ASPHALT'];ground=bpy.data.objects['BS_ASPHALT'];bpy.context.view_layer.update();contacts=[]
for prefix in sorted(set(repairs)):
 obs=[o for o in building.objects if o.name.startswith(prefix+'_')];feet=[o for o in obs if '_FOOT_' in o.name];pts=[]
 for foot in feet:
  vv=np.array([v.co[:] for v in foot.data.vertices]);xy=vv[:,:2].mean(0);hits=[]
  for surface in [apron,ground]:
   hit,pt,_,_=surface.ray_cast(Vector((*xy,30)),Vector((0,0,-1)))
   if hit:hits.append(pt.z)
  assert hits,foot.name;pts.append((foot,xy,max(hits),float(vv[:,2].min())))
 dz=max(p[2]-p[3] for p in pts)
 for ob in obs:ob.location.z+=dz
 for foot,xy,z,oldbase in pts:
  gap=oldbase+dz-z
  if gap>.001:
   uv=(xy-C)@np.array([right,front]).T;ob=box(foot.name+'_LEVEL_PACK',(uv[0],uv[1],z-FLOOR+gap/2),(.089,.099,gap),bpy.data.materials['SV | blue grey metal window profiles'],.0008);ob['support_basis']='Small inferred metal leveling pack to eliminate surveyed-grade floating; not measured site hardware.'
  contacts.append({'name':foot.name,'ground_z':z,'original_gap_m':oldbase-z,'assembly_shift_m':dz,'level_pack_m':max(0,gap)})
# Floor tile batches retain physical joints; use restrained per-tile tone variation.
ob=bpy.data.objects['SV_FLOOR_TILES'];base=ob.data.materials[0];rng=np.random.default_rng(350)
for val in [.974,.990,1.010,1.025]:
 m=base.copy();m.name='SV | mineral floor shade '+str(val);bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');col=np.array(bs.inputs['Base Color'].default_value);col[:3]*=val;bs.inputs['Base Color'].default_value=col;ob.data.materials.append(m)
for face in ob.data.polygons:
 co=face.center;pt=(np.array(co[:2])-C)@np.array([right,front]).T;i=int(math.floor(pt[0]/.6));j=int(math.floor((pt[1]+4.2)/.6));face.material_index=(i*37+j*13)%5
for ob in building.objects:
 if ob.name.startswith(('SV_CONTINUOUS_','SV_BENCH_')):ob['place']='Bellevueplatz_2_service_pavilion';ob['egid']=302040350;ob['quality_status']='construction_unaccepted';ob['collision_role']='pending_runtime'
bpy.context.view_layer.update();s['version']='G1_014r2';bpy.ops.file.pack_all();native=R/'native/G1_014r2_service_details_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native));w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=s['version'],native=str(native),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2));E=R/'evidence'/s['version'];E.mkdir(exist_ok=True);(E/'refinement.json').write_text(json.dumps({'version':s['version'],'native':str(native),'bench_contact_repairs':contacts,'basin_assembly':'continuous charcoal counter per inspected dated interior photograph','light_power_W':105,'accepted':False},indent=2));print(json.dumps({'version':s['version'],'native':str(native),'bench_contacts':contacts}))
