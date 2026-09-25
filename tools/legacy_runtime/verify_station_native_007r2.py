import bpy,json,hashlib
from pathlib import Path
root=Path('F:/MyWorld/ZurichWorld');record=json.loads((root/'runtime/station_road_working.json').read_text());bpy.ops.wm.open_mainfile(filepath=record['native']);scene=bpy.context.scene
assert scene['version']=='G1_007r2'
col=bpy.data.collections['10_BELLEVUE_RECONSTRUCTION'];missing=[];images=set()
for ob in col.all_objects:
 if not hasattr(ob.data,'materials'):continue
 for mat in ob.data.materials:
  if not mat or not mat.use_nodes:continue
  for n in mat.node_tree.nodes:
   if n.type=='TEX_IMAGE' and n.image:
    im=n.image;images.add(im.name)
    if not im.packed_file and not Path(bpy.path.abspath(im.filepath)).is_file():missing.append(im.name)
assert not missing,missing
ctx={str(o['source_node']):o for o in bpy.data.collections['04_RETAINED_PHOTO_CONTEXT'].objects};original={str(o['source_node']):o for o in bpy.data.collections['03_I3S_PHOTOGRAPHIC_REFERENCE'].objects}
cut=json.loads((root/scene['photo_cut_file']).read_text());ids={str(p['node']) for p in cut['overrides']};unmodified=[]
for k,ob in original.items():
 assert ctx[k].matrix_basis==ob.matrix_basis,k
 if k not in ids:
  assert ctx[k].data==ob.data,k
  unmodified.append(k)
result={'version':scene['version'],'native':record['native'],'missing_authored_images':missing,'authored_images':len(images),'exportable_objects':len([o for o in col.all_objects if o.type in ['MESH','CURVE','FONT']]),'source_objects':len(original),'changed_working_copies':len(ids),'unchanged_working_copies':len(unmodified),'source_transforms_preserved':True,'curb_objects':record['curb_objects'],'visual_review':'007r2 TRACK_NEAR actually inspected; previous open platform edge no longer exposes background. Road material/markings, other islands and whole-world quality remain incomplete.','quality_accepted':False,'walking_accepted':False}
(root/'evidence/G1_007r2/native_reopen.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
