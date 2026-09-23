"""008r4: retain protective glazing, restore transmitted light, and replace diagnosed DFI debris."""
import bpy,json,numpy as np,hashlib
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene
assert scene['version']=='G1_008r3'
data=json.loads((ROOT/'derived/bellevue/west_context/fixtures_input.json').read_text(encoding='utf-8'))
C=np.array(data['bench']['source_point_lv95'])-[2683775,1246700];right=np.array(data['bench']['axis']);front=np.array([-right[1],right[0]])
glass=bpy.data.materials['BE | clear curved 12mm glass'].copy();glass.name='BE | protective case glass 5mm'
n=next(n for n in glass.node_tree.nodes if n.type=='BSDF_PRINCIPLED');n.inputs['Base Color'].default_value=(.98,.99,.985,1);n.inputs['Roughness'].default_value=.05
glass['basis']='Inferred ordinary 5mm protective glazing; retains physical transmission and IOR1.47. No opacity or emission substitution.'
for ob in bpy.data.collections['14_BELLEVUE_WEST_FACILITIES'].objects:
 if '_GLASS_' in ob.name:
  ob.visible_shadow=True;ob.hide_render=False;ob.data.materials[0]=glass
  if 'thin_glass_shadow_approximation' in ob:del ob['thin_glass_shadow_approximation']
 if ob.name.startswith('BE_WEST_BENCH_') and ob.type=='MESH' and ob.data.materials and ob.data.materials[0].name=='oak_veneer_01':
  uv=ob.data.uv_layers.active
  for f in ob.data.polygons:
   for li in f.loop_indices:
    v=ob.data.vertices[ob.data.loops[li].vertex_index].co;q=np.array(v[:2])-C
    uv.data[li].uv=((v.z if abs(f.normal.z)<.6 else float(q@front))/2,float(q@right)/2)
  ob['wood_grain_axis']='longitudinal, actual image V axis; 2m scale'
# Disabling refractive caustics suppressed diffuse illumination seen through this
# glass-paper assembly. Shader replacement, shadow disabling and a 15mm air gap
# did not repair it. Restore the physical light path instead of brightening paper.
scene.cycles.caustics_refractive=True
for name in ['BE_QA_WEST_BENCH','BE_QA_WEST_TICKET']:bpy.data.objects[name].data.lens=28
cutpath=ROOT/'derived/bellevue/west_context/fixtures_photo_cut.json';cut=json.loads(cutpath.read_text())
base=json.loads((ROOT/'derived/bellevue/west_context/shelter_photo_cut.json').read_text());old={str(p['node']):p for p in base['overrides']}
context={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};originals={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects};changed=[]
for p in cut['overrides']:
 key=str(p['node'])
 if p==old.get(key):continue
 ob=context[key];origin=originals[key];assert ob.matrix_basis==origin.matrix_basis
 vv=np.array(p['vertices'],dtype=np.float32);uvv=np.array(p['uv_source_v_unflipped'],dtype=np.float32)
 me=bpy.data.meshes.new('BE_WEST_DFI_CONTEXT_'+key);me.from_pydata(vv.tolist(),[],np.arange(len(vv)).reshape(-1,3).tolist());me.update()
 for m in origin.data.materials:me.materials.append(m)
 uv=me.uv_layers.new(name='source_photo_uv');uvv[:,1]=1-uvv[:,1];uv.data.foreach_set('uv',uvv.flatten());ob.data=me;ob['construction_mask']=cut['mask_basis'];changed.append(key)
assert len(changed)==cut['dfi_stats']['nodes_changed']==2
scene['version']='G1_008r4';scene['photo_cut_file']=str(cutpath.relative_to(ROOT));scene.camera=bpy.data.objects['BE_QA_WEST_PLATFORM_REVERSE'];bpy.context.view_layer.update()
native=ROOT/'native/G1_008r4_west_facilities_working.blend';bpy.ops.wm.save_as_mainfile(filepath=str(native))
record=json.loads((ROOT/'runtime/station_road_working.json').read_text());record.update(version=scene['version'],native=str(native),source_cut_file=scene['photo_cut_file'],source_cut_sha256=hashlib.sha256(cutpath.read_bytes()).hexdigest(),accepted=False,not_published=True,published_as=None,next='Review all protective glazing, complete-fixture views and both station directions; remaining trees, facades and physical use incomplete')
(ROOT/'runtime/station_road_working.json').write_text(json.dumps(record,indent=2))
out=ROOT/'evidence/G1_008r4';out.mkdir(exist_ok=True)
(out/'fixture_repair.json').write_text(json.dumps({'version':scene['version'],'source_nodes_changed':changed,'dfi_cut':cut['dfi_stats'],'refractive_caustics':True,'all_covers_present':True,'all_covers_cast_shadow':True,'wood_axis_corrected':True,'diagnostics':['G1_008r3_glass_diagnostic','G1_008r3_glass_shader_diagnostic','G1_008r3_glass_caustics_diagnostic'],'accepted':False},indent=2))
print(json.dumps({'version':scene['version'],'native':str(native),'dfi_cut_nodes':changed,'accepted':False}))
