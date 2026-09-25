"""Release only invisible reference copies in a disposable render process.

Uses the same verified procedure as render_native_checkpoint. Never save the
render process afterward; all visible meshes and original pixels are preserved.
"""
from pathlib import Path
import bpy
from workspace_paths import ROOT as R, read_path, write_path


def prepare_review_memory(camera):
    s=bpy.context.scene
    REVIEW_CAMERA=camera
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
        if not im.packed_file or not im.filepath or im.library:continue
        external=Path(bpy.path.abspath(im.filepath,library=im.library))
        if not external.is_file():continue
        method=im.bl_rna.functions['unpack'].parameters['method']
        valid={item.identifier for item in method.enum_items}
        if 'REMOVE' not in valid:continue
        packed=bytes(im.packed_file.data)
        if hashlib.sha256(packed).hexdigest()!=hashlib.sha256(read_path(external).read_bytes()).hexdigest():continue
        count=len(packed);del packed
        im.unpack(method='REMOVE');released.append({'image':im.name,'bytes':count,'external':str(external)})
    gc.collect()
    (write_path(R/'evidence'/s['version']/f'{REVIEW_CAMERA}_render_memory.json')).write_text(json.dumps({'exact_encoded_image_copies_released':released,'bytes_released':sum(x['bytes'] for x in released),'invisible_reference_meshes_unloaded':hidden_refs,'visible_mesh_counts_identical':True,'native_file_modified':False,'render_pixels_downscaled':False,'visible_geometry_removed':False},indent=2))
    print('EXACT_IMAGE_COPIES_RELEASED',sum(x['bytes'] for x in released),flush=True)
