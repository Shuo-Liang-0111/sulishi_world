"""Fresh-process Cycles review; native construction remains untouched."""
import bpy
from pathlib import Path
import sys
R=Path('F:/MyWorld/ZurichWorld')
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
assert len(args) in [1,2]
REVIEW_CAMERA=args[0]
REVIEW_DEVICE='CPU'
if len(args)==2:
    assert args[1]=='surface-check'
    REVIEW_SAMPLES=24
    REVIEW_RESOLUTION=(1280,840)
    if REVIEW_CAMERA in ['BE_QA_FOUNTAIN_RIM','BE_QA_FOUNTAIN_OVERFLOW']:
        REVIEW_SAMPLES=48
        REVIEW_RESOLUTION=(1600,1050)
s=bpy.context.scene
assert s['version'].startswith(('G1_015','G1_016','G1_017','G1_018','G1_019','G1_020','G1_021','G1_022','G1_023','G1_024','G1_025','G1_026','G1_027'))
s.render.threads_mode='FIXED';s.render.threads=10
s.render.use_sequencer=False
s.render.use_compositing=False
s.render.use_persistent_data=False
if hasattr(s.cycles,'denoising_use_gpu'):
    s.cycles.denoising_use_gpu=False
print('CPU_DENOISING',getattr(s.cycles,'denoising_use_gpu','property_absent'),flush=True)
bpy.context.view_layer.update()
if s['version'] in ['G1_015r1','G1_015r2','G1_015r3','G1_016','G1_016r1','G1_017','G1_017r1']:
    exec(compile((R/'tools/blender_check_pit_edges.py').read_text(encoding='utf-8'),'check_pit_seams','exec'))
if s['version'].startswith(('G1_016','G1_017')):
    exec(compile((R/'tools/blender_check_east_facilities.py').read_text(encoding='utf-8'),'check_east_contacts','exec'))
if s['version'].startswith('G1_018r'):
    exec(compile((R/'tools/blender_check_fountain59.py').read_text(encoding='utf-8'),'check_fountain_connections','exec'))
if s['version'].startswith(('G1_020','G1_021','G1_022','G1_023','G1_024','G1_025','G1_026','G1_027')):
    import runpy
    runpy.run_path(str(R/'tools/blender_check_utoquai_kiosk.py'))
if s['version'].startswith(('G1_021','G1_022','G1_023','G1_024','G1_025','G1_026','G1_027')):
    runpy.run_path(str(R/'tools/blender_check_riviera_quay.py'))
    if '34_RIVIERA_TREES' in bpy.data.collections:
        runpy.run_path(str(R/'tools/blender_check_riviera_trees.py'))
if s['version'].startswith(('G1_023','G1_024','G1_025','G1_026','G1_027')):
    runpy.run_path(str(R/'tools/blender_check_quaibruecke.py'))
if s['version'].startswith(('G1_024','G1_025','G1_026','G1_027')):
    runpy.run_path(str(R/'tools/blender_check_quaibruecke_water.py'))
if s['version'].startswith(('G1_025','G1_026','G1_027')):
    runpy.run_path(str(R/'tools/blender_check_bridgehead_bank.py'))
if s['version'].startswith(('G1_026','G1_027')):
    runpy.run_path(str(R/'tools/blender_verify_bank_sharing.py'))
    runpy.run_path(str(R/'tools/blender_check_bridgehead_portal.py'))
if s['version']=='G1_027':
    runpy.run_path(str(R/'tools/blender_check_bridge_deck.py'))
if s['version'].startswith(('G1_022','G1_023','G1_024','G1_025','G1_026','G1_027')):
    runpy.run_path(str(R/'tools/blender_check_riviera_lower.py'))
if s['version'].startswith(('G1_019','G1_020','G1_021','G1_022','G1_023','G1_024','G1_025','G1_026','G1_027')):
    exec(compile((R/'tools/blender_check_limmat_sidewalk.py').read_text(encoding='utf-8'),'check_limmat_geometry','exec'))
    # Temporary render process only: release encoded image copies only when an
    # external file has exactly identical bytes. Pixel data/resolution, all
    # visible geometry and sampling remain unchanged; never save this session.
    import hashlib,gc,json
    visible=set()
    def visible_collection(col,parent_hidden=False):
        hidden=parent_hidden or col.hide_render
        if not hidden:
            visible.update(ob for ob in col.objects if not ob.hide_render)
        for child in col.children:visible_collection(child,hidden)
    visible_collection(s.collection)
    visible_meshes={ob.name:(len(ob.data.vertices),len(ob.data.polygons)) for ob in visible if ob.type=='MESH'}
    hidden_objects=[ob for ob in s.objects if ob not in visible and ob.type=='MESH' and not ob.children]
    hidden_refs=[ob.name for ob in hidden_objects]
    hidden_meshes=set(ob.data for ob in hidden_objects)
    print('RENDER_PREP_RELEASE_INVISIBLE',len(hidden_objects),flush=True)
    # One dependency update for the same invisible IDs avoids thousands of
    # repeated scene invalidations. Visible IDs and mesh counts are checked.
    if hasattr(bpy.data,'batch_remove'):
        bpy.data.batch_remove(ids=hidden_objects)
        bpy.data.batch_remove(ids=[mesh for mesh in hidden_meshes if mesh.users==0])
    else:
        for ob in hidden_objects:bpy.data.objects.remove(ob,do_unlink=True)
        for mesh in hidden_meshes:
            if mesh.users==0:bpy.data.meshes.remove(mesh)
    assert visible_meshes=={name:(len(bpy.data.objects[name].data.vertices),len(bpy.data.objects[name].data.polygons)) for name in visible_meshes}
    print('RENDER_PREP_VERIFY_PACKED_IMAGES',flush=True)
    released=[]
    for im in bpy.data.images:
        if not im.packed_file or not im.filepath:continue
        external=Path(bpy.path.abspath(im.filepath))
        if not external.is_file():continue
        method=im.bl_rna.functions['unpack'].parameters['method']
        valid={item.identifier for item in method.enum_items}
        if 'REMOVE' not in valid:continue
        packed=bytes(im.packed_file.data)
        if hashlib.sha256(packed).hexdigest()!=hashlib.sha256(external.read_bytes()).hexdigest():continue
        count=len(packed);del packed
        im.unpack(method='REMOVE');released.append({'image':im.name,'bytes':count,'external':str(external)})
    gc.collect()
    (R/'evidence'/s['version']/f'{REVIEW_CAMERA}_render_memory.json').write_text(json.dumps({'exact_encoded_image_copies_released':released,'bytes_released':sum(x['bytes'] for x in released),'invisible_reference_meshes_unloaded':hidden_refs,'visible_mesh_counts_identical':True,'native_file_modified':False,'render_pixels_downscaled':False,'visible_geometry_removed':False},indent=2))
    print('EXACT_IMAGE_COPIES_RELEASED',sum(x['bytes'] for x in released),flush=True)
exec(compile((R/'tools/blender_render_bellevue.py').read_text(encoding='utf-8'),'fresh_native_review','exec'))
print('FRESH_REVIEW_FINISHED',s['version'],REVIEW_CAMERA,flush=True)
