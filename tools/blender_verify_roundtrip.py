"""Verify actual Blender -> GLB -> Blender transforms in a disposable scene."""
import bpy,json
from pathlib import Path
import numpy as np
ROOT=Path('F:/MyWorld/ZurichWorld')
record=json.loads((ROOT/'runtime/current_scene.json').read_text())
original=bpy.context.scene
targets=['SURVEY_TERRAIN','EGID_2376968','EGID_140627']
targets += ['EGID_'+x for x in ['2368227','9011662','2372316','159256','2369518',
            '302008593','2372576','9011202','156044','159254','140622']]
def bounds(obj):
    vs=[]
    for o in [obj,*obj.children_recursive]:
        if o.type=='MESH':
            vs.extend([list(o.matrix_world@v.co) for v in o.data.vertices])
    a=np.array(vs);return [*a.min(axis=0).tolist(),*a.max(axis=0).tolist()]
expected={name:bounds(bpy.data.objects[name]) for name in targets}
before=set(bpy.data.objects)
qa=bpy.data.scenes.new('TEMP_G1_EXPORT_QA')
bpy.context.window.scene=qa
try:
    bpy.ops.import_scene.gltf(filepath=record['survey_glb'])
    bpy.context.view_layer.update()
    imported=list(set(bpy.data.objects)-before)
    results=[]
    for name,old in expected.items():
        candidates=[o for o in imported if o.name==name or o.name.startswith(name+'.')]
        # Material splits live under the root with source metadata.
        candidates=[o for o in candidates if 'kind' in o]
        if len(candidates)!=1:raise RuntimeError(f'Ambiguous imported source identity {name}: {len(candidates)}')
        new=bounds(candidates[0]);error=float(np.max(np.abs(np.array(old)-new)))
        results.append({'id':name,'native_bounds':old,'reimport_bounds':new,'max_error_m':error})
        if error>0.002:raise RuntimeError(f'Unexpected transform drift: {name}, {error} metres')
    report={'version':record['version'],'stage':'source_geometry_roundtrip_only',
            'matches':results,'max_error_m':max(r['max_error_m'] for r in results),
            'interactivity_validated':False,'visual_quality_accepted':False}
finally:
    bpy.context.window.scene=original
    for o in list(set(bpy.data.objects)-before):bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.scenes.remove(qa)
# Reopen the persisted city rather than a disposable cube.
bpy.ops.wm.open_mainfile(filepath=record['native'])
assert bpy.context.scene['version']==record['version']
assert bpy.context.scene.blendermcp_port==19876
report['native_reopen_verified']=True
report['reopened_objects']=len(bpy.context.scene.objects)
(ROOT/'evidence'/record['version']).mkdir(exist_ok=True,parents=True)
(ROOT/'evidence'/record['version']/'roundtrip.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
