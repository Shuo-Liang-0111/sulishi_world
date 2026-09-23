"""Preserve remaining temporary-origin packed images as exact permanent files."""
from pathlib import Path
import hashlib
import json
import bpy

root = Path('F:/MyWorld/ZurichWorld')
scene = bpy.context.scene
assert scene['version'] == 'G1_020r4'
expected = {asset + '_' + role for asset in ['asphalt_03', 'oak_veneer_01']
            for role in ['Diffuse', 'Displacement', 'nor_gl', 'Rough']}
images = [image for image in bpy.data.images if image.packed_file and image.library is None]
assert {image.name for image in images} == expected
records = []
for image in images:
    asset = next(asset for asset in ['asphalt_03', 'oak_veneer_01'] if image.name.startswith(asset+'_'))
    filename = Path(image.filepath.replace('\\', '/')).name
    assert filename == image.name+'_4k.jpg'
    destination = root/'sources/textures/polyhaven'/asset/filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    assert destination.resolve().is_relative_to((root/'sources/textures/polyhaven').resolve())
    encoded = bytes(image.packed_file.data)
    sha256 = hashlib.sha256(encoded).hexdigest()
    previous_path = image.filepath
    metadata = {'size': list(image.size), 'colorspace': image.colorspace_settings.name,
                'alpha_mode': image.alpha_mode}
    if destination.exists():
        assert hashlib.sha256(destination.read_bytes()).hexdigest() == sha256
    else:
        with destination.open('xb') as output:
            output.write(encoded)
    assert hashlib.sha256(destination.read_bytes()).hexdigest() == sha256
    image.filepath = str(destination)
    image.unpack(method='REMOVE')
    image.filepath = bpy.path.relpath(str(destination), start=str(root/'native'))
    assert not image.packed_file
    assert Path(bpy.path.abspath(image.filepath)).resolve() == destination.resolve()
    assert list(image.size) == metadata['size']
    assert image.colorspace_settings.name == metadata['colorspace']
    assert image.alpha_mode == metadata['alpha_mode']
    records.append({'image': image.name, 'previous_temporary_origin': previous_path,
                    'permanent_file': str(destination.relative_to(root)),
                    'encoded_sha256': sha256, 'encoded_bytes': len(encoded), **metadata})
evidence = root/'evidence/G1_020r4'
evidence.mkdir(exist_ok=True)
record = {'version': scene['version'], 'images': records,
          'encoded_bytes_identical': True, 'pixels_not_reencoded_or_resized': True,
          'old_checkpoints_untouched': True, 'bytes_not_repacked_per_new_checkpoint': sum(r['encoded_bytes'] for r in records)}
(evidence/'permanent_surface_images.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('PACKED_SURFACES_PRESERVED', json.dumps({'images': len(records), 'bytes': record['bytes_not_repacked_per_new_checkpoint']}), flush=True)
