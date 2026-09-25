"""Start the upstream MCP addon in the isolated Zurich Blender profile."""
import json
import os
import sys
from pathlib import Path
import bpy
import addon_utils

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from workspace_paths import CONFIG, validate_native
PORT = 19876
bpy.utils.refresh_script_paths()
addon_utils.modules_refresh()
addon_utils.enable('blender_mcp', default_set=True, persistent=True)
native = ROOT / 'native'
native.mkdir(exist_ok=True)
empty = native / 'G1_000_empty.blend'
restored = None
if os.environ.get('ZURICH_NATIVE_FILE') or CONFIG.get('working_native'):
    saved = validate_native(os.environ.get('ZURICH_NATIVE_FILE') or CONFIG['working_native'])
    if not saved.is_file():
        raise FileNotFoundError(f'Current scene is missing; refusing to replace it: {saved}')
    bpy.ops.wm.open_mainfile(filepath=str(saved))
    restored = saved
elif empty.exists():
    bpy.ops.wm.open_mainfile(filepath=str(empty))
    restored = empty
scene = bpy.context.scene
# This isolated author profile uses explicitly named, verified checkpoints.
# Factory startup otherwise re-enables full-scene autosaves on the nearly
# full project drive, duplicating hundreds of MB during every MCP session.
bpy.context.preferences.filepaths.use_auto_save_temporary_files = False
bpy.context.preferences.filepaths.save_version = 0
scene.blendermcp_port = PORT
scene.blendermcp_auto_start_server = True
for key in ['polyhaven', 'hyper3d', 'hunyuan3d', 'sketchfab', 'polypizza']:
    setattr(scene, 'blendermcp_use_' + key, False)
scene.blendermcp_use_polyhaven = True  # Public CC0 assets; no paid generation or model API.
if restored is None:
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene.name = 'Zurich_G1_Working'
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0
scene['project_root'] = str(ROOT)
if restored is None:
    scene['quality_status'] = 'empty_project_not_a_completed_scene'
scene['geographic_crs'] = 'EPSG:2056'
scene['vertical_crs'] = 'EPSG:5728'
if restored is None and not empty.exists():
    bpy.ops.wm.save_as_mainfile(filepath=str(empty))
devices = []
try:
    cp = bpy.context.preferences.addons['cycles'].preferences
    cp.compute_device_type = 'OPTIX'
    cp.get_devices()
    for d in cp.devices:
        d.use = d.type == 'OPTIX'
        devices.append({'name': d.name, 'type': d.type, 'use': d.use})
except Exception as exc:
    devices.append({'probe_error': str(exc)})
bpy.ops.wm.save_userpref()
report = {'pid': os.getpid(), 'blender': bpy.app.version_string,
          'project': str(ROOT), 'port': PORT, 'host': '127.0.0.1',
          'background': bpy.app.background, 'cycles_devices': devices,
          'addon_enabled': 'blender_mcp' in bpy.context.preferences.addons,
          'scene': scene.name, 'native': str(restored or empty)}
(ROOT / 'runtime' / 'blender_bootstrap.json').write_text(
    json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report), flush=True)
