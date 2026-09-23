"""Export the saved G1_019r2 soil for prepare_limmat_soil_relief.py; read only."""
import json
from pathlib import Path
import bpy

root = Path('F:/MyWorld/ZurichWorld')
assert bpy.context.scene['version'] == 'G1_019r2'
assert Path(bpy.data.filepath).name == 'G1_019r2_limmat_clearance_working.blend'
obj = bpy.data.objects['LM_SOIL']
assert len(obj.data.vertices) == 8862 and len(obj.data.polygons) == 2954
out = root / 'derived/bellevue/limmat_sidewalk/soil_native_019r2.json'
out.write_text(json.dumps({'vertices': [list(v.co) for v in obj.data.vertices], 'faces': [list(f.vertices) for f in obj.data.polygons], 'matrix_world': [list(row) for row in obj.matrix_world]}), encoding='utf-8')
print(str(out))
