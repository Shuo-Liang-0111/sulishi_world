"""Sequential fresh-process export; all temporary objects are discarded on exit."""
import bpy
import contextlib
from pathlib import Path
R=Path('F:/MyWorld/ZurichWorld')
V=bpy.context.scene['version'];assert V in ['G1_015r1','G1_015r2','G1_015r3','G1_016r1','G1_017','G1_017r1','G1_018r3']
with (R/'runtime/logs'/f'{V}_export_details.log').open('w',encoding='utf-8') as log:
    with contextlib.redirect_stdout(log):
        exec(compile((R/'tools/blender_export_bellevue.py').read_text(encoding='utf-8'),'native_export','exec'))
        exec(compile((R/'tools/blender_export_review_sky.py').read_text(encoding='utf-8'),'native_sky','exec'))
print('NATIVE_EXPORT_FINISHED',V,flush=True)
