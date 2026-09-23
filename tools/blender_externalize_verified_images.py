"""Use identical existing project image files instead of redundant packed bytes.

Call externalize(root) before saving a NEW native checkpoint. This does not save
the scene, write image files, alter pixels/materials, or modify old checkpoints.
Every dependency must resolve to an existing non-cache file inside the project.
"""
from pathlib import Path
import hashlib
import json
import os
import bpy


def externalize(root):
    root=Path(root).resolve()
    assert Path(bpy.data.filepath).resolve().parent==root/'native'
    native_dir=root/'native'
    records=[];skipped=[];file_hashes={}
    for image in list(bpy.data.images):
        if not image.packed_file or not image.filepath or image.library:
            continue
        path=Path(bpy.path.abspath(image.filepath)).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            skipped.append({'image':image.name,'reason':'no existing local project file'});continue
        relative=path.relative_to(root)
        if relative.parts[0] in {'.cache','runtime','.venv'} or len(image.packed_files)!=1:
            skipped.append({'image':image.name,'reason':'volatile file or multiple packed tiles'});continue
        method=image.bl_rna.functions['unpack'].parameters['method']
        assert 'REMOVE' in {item.identifier for item in method.enum_items}
        if path not in file_hashes:
            digest=hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda:stream.read(4*1024*1024),b''):digest.update(chunk)
            file_hashes[path]=digest.hexdigest()
        packed=bytes(image.packed_file.data)
        digest=hashlib.sha256(packed).hexdigest();size=len(packed)
        if digest!=file_hashes[path]:
            skipped.append({'image':image.name,'reason':'encoded content differs; keep packed original'});continue
        state=(tuple(image.size),image.colorspace_settings.name,image.alpha_mode)
        image.unpack(method='REMOVE')
        image.filepath='//'+os.path.relpath(path,native_dir).replace('\\','/')
        assert Path(bpy.path.abspath(image.filepath)).resolve()==path
        assert not image.packed_file
        assert state==(tuple(image.size),image.colorspace_settings.name,image.alpha_mode)
        records.append({'image':image.name,'relative_to_project':relative.as_posix(),'relative_to_native':image.filepath,'sha256':digest,'encoded_bytes':size,'dimensions':list(state[0]),'color_space':state[1],'alpha_mode':state[2]})
        del packed
    result={'version':bpy.context.scene['version'],'dependencies':records,'skipped':skipped,'packed_bytes_released':sum(r['encoded_bytes'] for r in records),'existing_image_files_only':True,'image_pixels_changed':False,'native_saved_by_this_step':False}
    evidence=root/'evidence'/bpy.context.scene['version'];evidence.mkdir(exist_ok=True)
    (evidence/'verified_image_dependencies.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'images_externalized':len(records),'skipped':len(skipped),'packed_bytes_released':result['packed_bytes_released']}),flush=True)
    return result
