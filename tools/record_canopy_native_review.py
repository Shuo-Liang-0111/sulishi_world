"""Record the three actual native views inspected after continuous canopy repair."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1];V='G1_017r1';E=R/'evidence'/V
views=['BE_QA_SOUTH_EAST_INFO_WIDE','BE_QA_SERVICE_NORTH','BE_QA_SOUTH_EAST_REVERSE_WIDE'];images=[]
for name in views:
    p=E/(name+'.png');settings=json.loads((E/(name+'_render_settings.json')).read_text())
    assert settings['version']==V and not settings['authored_textures_downscaled']
    images.append({'file':str(p.relative_to(R)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
record={'version':V,'images_actually_inspected':images,
 'local_repairs_verified':['Near upper floating photo scraps gone in east same-camera view','Merged source crown above service canopy removed in north view','Reverse frame, trees, roof line and street connection retained'],
 'limitations':['Distant source foliage and temporary tent still unfinished','Other buildings remain distorted source meshes','Static surfaces and native image quality are not natural-use acceptance','Runtime geometry and illumination must still be refreshed'],
 'accepted':False,'full_G1_complete':False}
(E/'native_visual_review.json').write_text(json.dumps(record,indent=2))
print('Three actual native images recorded; wholeG1 and natural-use acceptance remain false.')
