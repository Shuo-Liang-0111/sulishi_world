"""Reimport the current construction export and check native reopen separately."""
import bpy
import contextlib
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld');V=bpy.context.scene['version']
assert V in ['G1_015r1','G1_015r2','G1_015r3','G1_016r1','G1_017','G1_017r1','G1_018r3']
if V=='G1_018r3':
    exec(compile((R/'tools/check_fountain_export.py').read_text(encoding='utf-8'),'check_fountain_export','exec'))
with (R/'runtime/logs'/f'{V}_roundtrip_details.log').open('w',encoding='utf-8') as log:
    with contextlib.redirect_stdout(log):
        exec(compile((R/'tools/blender_verify_bellevue_export.py').read_text(encoding='utf-8'),'verify_native_export','exec'))
print('NATIVE_ROUNDTRIP_FINISHED',V,flush=True)
