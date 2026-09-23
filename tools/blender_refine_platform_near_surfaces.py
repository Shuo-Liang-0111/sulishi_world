"""Keep the accepted layout; repair observed photo remnants and material scale."""
import bpy,json,numpy as np,math,hashlib
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');s=bpy.context.scene;assert s['version']=='G1_012r4'
# The photographed exposed-aggregate material is a proxy, not a site scan. Its
# former two-metre mapping made individual granules read like large pebbles.
curb=bpy.data.materials['concrete_floor_01'].copy();curb.name='BE | fine mineral curb proxy'
for n in curb.node_tree.nodes:
 if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.12
curb['basis']='Same retained CC0 concrete_floor_01 maps, finer aggregate proxy at inferred0.667m tile; not surveyed granite mineralogy.'
curbs=[]
for name in ['BE_PLATFORM_CURB_TOP','BE_PLATFORM_CURB_FACE','BE_WEST_CURB_TOP','BE_WEST_CURB_FACE']:
 ob=bpy.data.objects[name];ob.data.materials.clear();ob.data.materials.append(curb)
 for p in ob.data.polygons:p.material_index=0
 for p in ob.data.uv_layers.active.data:p.uv*=3
 curbs.append(name)
old=bpy.data.materials['CF | aged satin grey painted steel'];coat=old.copy();coat.name='CF | metre-scale satin coat'
ns=coat.node_tree.nodes;links=coat.node_tree.links;bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
for role,socket in [('albedo','Base Color'),('roughness','Roughness'),('normal_gl','Normal')]:
 tex=ns.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(R/'derived/materials/satin_grey_coat'/f'{role}.png'),check_existing=True)
 if role!='albedo':tex.image.colorspace_settings.name='Non-Color'
 if role=='normal_gl':
  n=ns.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=.65;links.new(tex.outputs['Color'],n.inputs['Color']);links.new(n.outputs['Normal'],bs.inputs[socket])
 else:links.new(tex.outputs['Color'],bs.inputs[socket])
coat['basis']='Original subtle coating microstructure and roughness; UVs in metres. No site-specific damage asserted.'
painted=[]
for prefix,ident,xy in [('CF',1800,[-245.73,148.261]),('CF2',1793,[-208.21,166.798])]:
 # Use cylindrical UVs for the shaft, unwrapping each polygon across its seam.
 ob=bpy.data.objects[f'{prefix}_MAST_{ident}_SHAFT'];me=ob.data;uv=me.uv_layers.new(name='coat_metres');center=np.array(xy);me.materials.clear();me.materials.append(coat)
 for face in me.polygons:
  pp=np.array([ob.matrix_world@me.vertices[me.loops[li].vertex_index].co for li in face.loop_indices]);rel=pp[:,:2]-center;angles=np.arctan2(rel[:,1],rel[:,0]);angles=np.unwrap(angles);rr=np.linalg.norm(rel,axis=1)
  # Constant circumference reference keeps coating grain size stable vertically.
  for li,a,p in zip(face.loop_indices,angles,pp):uv.data[li].uv=(float(a*.14),float(p[2]))
 painted.append(ob.name)
cutpath=R/'derived/bellevue/west_context/corner_fragment_cleanup.json';cut=json.loads(cutpath.read_text());ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};orig={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
for p in cut['overrides']:
 ob=ctx[str(p['node'])];src=orig[str(p['node'])];vv=np.array(p['vertices']);uvv=np.array(p['uv_source_v_unflipped']);me=bpy.data.meshes.new('CF_CLEAN_CONTEXT_'+str(p['node']));me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for mat in src.data.materials:me.materials.append(mat)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.astype(np.float32).reshape(-1));ob.data=me;ob['construction_mask']=cut['mask_basis']
s['version']='G1_012r5';s['photo_cut_file']=str(cutpath.relative_to(R));s.camera=bpy.data.objects['BE_QA_CORNER_FIXTURES'];bpy.context.view_layer.update();bpy.ops.file.pack_all();native=R/'native/G1_012r5_platform_surfaces_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
rec=json.loads((R/'runtime/station_road_working.json').read_text());rec.update(version=s['version'],native=str(native),source_cut_file=s['photo_cut_file'],source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),source_cut_nodes=len(cut['overrides']),accepted=False,not_published=True);(R/'runtime/station_road_working.json').write_text(json.dumps(rec,indent=2))
e=R/'evidence/G1_012r5';e.mkdir(exist_ok=True);report={'version':s['version'],'curb_material_scale_changed':curbs,'metre_scale_coating':painted,'cleared_photo_area_m2':json.loads((R/'derived/bellevue/west_context/corner_fragment_cleanup_basis.json').read_text())['area_m2'],'layout_changed':False,'accepted':False};(e/'surface_refinement.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
