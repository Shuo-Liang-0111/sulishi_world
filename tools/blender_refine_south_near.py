"""Fix observed cylindrical shading and old tree-sheet seams; keep survey anchors."""
import bpy,json,math,hashlib,numpy as np
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_013r1';D=R/'derived/bellevue/south_context';d=json.loads((D/'canopy_refinement.json').read_text());td=json.loads((D/'tree_inputs.json').read_text(encoding='utf-8'))
for t in td['trees']:
 ident=t['source']['properties']['objectid'];c=np.array(t['source']['geometry']['coordinates'])-[2683775,1246700];z=t['ground_ln02_m']-400;scale=np.array(d['crown_xy_scale'][str(ident)])
 for role in ['WOOD','TWIGS','LEAVES']:
  ob=bpy.data.objects[f'BS_TREE_{ident}_{role}'];vv=np.empty(len(ob.data.vertices)*3);ob.data.vertices.foreach_get('co',vv);vv=vv.reshape(-1,3);blend=np.clip((vv[:,2]-z-1.5)/(t['inferred']['branch_clearance_m']-1.5),0,1);blend=blend*blend*(3-2*blend);vv[:,:2]=c+(vv[:,:2]-c)*(1+(scale-1)*blend[:,None]);ob.data.vertices.foreach_set('co',vv.ravel());ob.data.update();ob['crown_xy_scale_inferred']=scale.tolist();ob['evidence_basis']=t['basis']+' '+d['basis']
f=json.loads((D/'fixtures_input.json').read_text());c=np.array(f['bin']['source']['geometry']['coordinates'][0])-[2683775,1246700];ob=bpy.data.objects['BSF_BIN631_SHEET_SHELL'];me=ob.data;normals=[None]*len(me.loops)
for face in me.polygons:
 rr=[np.linalg.norm(np.array(me.vertices[i].co[:2])-c) for i in face.vertices];cylinder=max(rr)-min(rr)<.0001
 for li in face.loop_indices:
  if cylinder:
   q=np.array(me.vertices[me.loops[li].vertex_index].co[:2])-c;q/=np.linalg.norm(q);n=(float(q[0]),float(q[1]),0);normals[li]=n if np.mean(rr)>.2235 else tuple(-x for x in n)
  else:normals[li]=tuple(face.normal)
me.normals_split_custom_set(normals);me.update()
mat=bpy.data.materials['BSF | ground stainless bin shell'];bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');ns=mat.node_tree.nodes;links=mat.node_tree.links
for role,socket in [('roughness','Roughness'),('normal_gl','Normal')]:
 tex=ns.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(R/'derived/materials/ground_stainless'/f'{role}.png'),check_existing=True);tex.image.colorspace_settings.name='Non-Color'
 if role=='normal_gl':
  n=ns.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=.55;links.new(tex.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Normal'],bs.inputs[socket])
 else:links.new(tex.outputs['Color'],bs.inputs[socket])
mat['surface_basis']='Original metre-scale dry-ground stainless microstructure, not a photographed site surface; restrained microrelief, no invented damage.'
# Cylindrical shell mapping is metric; avoid wrapping a polygon across the seam.
theta=math.radians(float(f['bin']['source']['properties']['orientierung']));front=np.array([math.sin(theta),math.cos(theta)]);right=np.array([-front[1],front[0]])
for ob in bpy.data.collections['23_BELLEVUE_SOUTH_FIXTURES'].objects:
 if not ob.name.startswith('BSF_BIN631_') or ob.type!='MESH' or mat not in list(ob.data.materials):continue
 uv=ob.data.uv_layers.active
 for face in ob.data.polygons:
  pts=np.array([ob.data.vertices[ob.data.loops[li].vertex_index].co[:] for li in face.loop_indices]);xy=pts[:,:2]-c;angles=np.unwrap(np.arctan2(xy@right,xy@front))
  for k,li in enumerate(face.loop_indices):
   uv.data[li].uv=(float(xy[k]@right),float(xy[k]@front)) if ob.name.endswith('LID') else (float(angles[k]*.225),float(pts[k,2]-f['bin']['ground_local']))
cutpath=R/d['cut_file'];cut=json.loads(cutpath.read_text());ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};orig={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for p in cut['overrides']:
 ob=ctx[str(p['node'])];src=orig[str(p['node'])];v=np.array(p['vertices']);uvv=np.array(p['uv_source_v_unflipped']);me=bpy.data.meshes.new('BS_REVIEW_CONTEXT_'+str(p['node']));me.from_pydata(v.tolist(),[],np.arange(len(v)).reshape(-1,3).tolist());me.update()
 for m in src.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.astype(np.float32).reshape(-1));ob.data=me;ob['construction_mask']=cut['mask_basis']
s['version']='G1_013r2';s['photo_cut_file']=d['cut_file'];bpy.context.view_layer.update();bpy.ops.file.pack_all();native=R/'native/G1_013r2_south_near_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native));w=json.loads((R/'runtime/station_road_working.json').read_text());w.update(version=s['version'],native=str(native),source_cut_file=d['cut_file'],source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(w,indent=2));e=R/'evidence'/s['version'];e.mkdir(exist_ok=True);(e/'refinement.json').write_text(json.dumps({'version':s['version'],'crown_xy_scale_inferred':d['crown_xy_scale'],'source_positions_and_heights_unchanged':True,'bin_custom_radial_normals':True,'steel_maps_metres':[1,1],'accepted':False},indent=2));print(json.dumps({'version':s['version'],'native':str(native)}))
