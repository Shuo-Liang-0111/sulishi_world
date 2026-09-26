"""Refresh the complete author-root inventory and read material graphs, without saving."""
from pathlib import Path
import runpy
import sys
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_paths import ROOT

assert bpy.context.scene['version'] == 'G1_027r15'
for name in ['blender_runtime_inventory.py','blender_runtime_material_graphs.py']:
    runpy.run_path(str(ROOT/'tools'/name), run_name='__main__')
print('COMPLETE_AUTHOR_SCOPE_READ_NOT_EXPORTED', flush=True)
