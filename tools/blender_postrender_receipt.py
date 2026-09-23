import bpy,json,hashlib
from pathlib import Path
ROOT=Path('F:/MyWorld/ZurichWorld');scene=bpy.context.scene;V=scene['version']
path=ROOT/f'evidence/{V}/BE_QA_ENTRY.png'
assert V=='G1_005r4' and path.exists()
record={'version':V,'image':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'camera':scene.camera.name,'samples':scene.cycles.samples,'native_alive':True,
        'render_seconds_from_blender_log':293.6,'mcp_render_reply':'timed out while rendering; completed PNG and subsequent scene read verified',
        'visual_findings':'Flat display and curved pane normals corrected. Interior still dark; caustics increase did not solve overall daylight. Not accepted.'}
(ROOT/'evidence'/V/'entry_render_receipt.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))
