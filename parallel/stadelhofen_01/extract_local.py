"""Append only 53 context tiles from the approved base; preserve it byte-for-byte."""
import sys,json,hashlib,math,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.path.insert(0,'H:/MyWorld/ZurichWorld/tools')
from sf1_common import *
from blender_geometry_fingerprint import mesh_digest,object_state
assert sha(D['base_native'])==D['base_sha256']
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
context=collection(D['context_collection']);context['merge_policy']='Reference-only local crop. Never append this collection into full city.'
selected=['CTX_I3S_'+n for n in D['context_nodes']]
with bpy.data.libraries.load(D['base_native'],link=False) as (src,dst):
    missing=set(selected)-set(src.objects);assert not missing,missing
    dst.objects=selected
source=[]
for ob in dst.objects:
    context.objects.link(ob);ob.hide_render=False;ob.hide_viewport=False
bpy.context.view_layer.update()
for ob in dst.objects:
    row=dict(original_name=ob.name,object_state=object_state(ob),mesh_digest=mesh_digest(ob.data))
    ob['sf1_original_name']=ob.name;ob.name='SF1_REF_'+ob.name;row['local_name']=ob.name;source.append(row)
# Retain source RGB exactly in this isolated evidence project. No source photos are
# repurposed as author materials. Absolute library/image paths retain F read dependencies.
for lib in bpy.data.libraries:
    lib.filepath=bpy.path.abspath(lib.filepath)
for im in bpy.data.images:
    if im.filepath:im.filepath=bpy.path.abspath(im.filepath,library=im.library)
s=configure_render();s['sf1_version']='SF1_baseline';s['origin_lv95_ln02']=D['origin'];s['base_sha256']=D['base_sha256']
s.world=bpy.data.worlds.new('SF1_QA_DAYLIGHT');s.world.use_nodes=True
s.world.node_tree.nodes['Background'].inputs[0].default_value=(.42,.52,.65,1)
s.world.node_tree.nodes['Background'].inputs[1].default_value=.8
lc=collection('SF1_QA_LIGHTS_DO_NOT_MERGE');sun=bpy.data.lights.new('SF1_QA_SUN','SUN');sun.energy=2.0;sun.angle=math.radians(4)
o=bpy.data.objects.new('SF1_QA_SUN',sun);lc.objects.link(o);o.rotation_euler=(math.radians(35),math.radians(-22),math.radians(-30))
make_cameras();s.camera=bpy.data.objects['SF1_QA_ENTRY']
native=OUT/'native/SF1_baseline_local.blend';assert not native.exists()
bpy.ops.wm.save_as_mainfile(filepath=str(native),compress=True)
write('derived/native_context_inventory.json',dict(base_native=D['base_native'],base_sha256=D['base_sha256'],local_native=str(native),local_sha256=sha(native),objects=source,blender=bpy.app.version_string,process_id=os.getpid(),context_only=True,images=[dict(name=i.name,path=bpy.path.abspath(i.filepath,library=i.library),packed=bool(i.packed_file)) for i in bpy.data.images if i.source=='FILE']))
render('SF1_QA_ENTRY','evidence/baseline',16)
render('SF1_QA_APPROACH','evidence/baseline',16)
assert sha(D['base_native'])==D['base_sha256']
print('SF1_BASELINE_COMPLETE',str(native),flush=True)
