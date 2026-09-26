"""Export individually verifiable current-native components, without publishing."""
from pathlib import Path
import json
import runpy
import sys
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workspace_paths import ROOT,read_path

version=bpy.context.scene['version']
assert version=='G1_027r15'
checkpoint=json.loads(read_path(f'evidence/{version}/checkpoint.json').read_text())
assert checkpoint['native_fresh_reopen_verified'] and checkpoint['approved_as_working_native']
for name in ['blender_export_leaf_diagnostic.py','blender_runtime_inventory.py',
             'blender_export_context_delta.py','blender_export_review_sky.py']:
    print('CURRENT_COMPONENT_START',name,flush=True)
    runpy.run_path(str(ROOT/'tools'/name),run_name='__main__')
print('CURRENT_RUNTIME_COMPONENTS_EXPORTED_NOT_PUBLISHED',version,flush=True)
