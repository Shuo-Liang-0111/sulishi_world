"""Register the verified candidate, never mark graphics or natural use accepted."""
import datetime, hashlib, json
from pathlib import Path
R=Path(__file__).resolve().parents[1]; V='G1_018r3'; E=R/'evidence'/V; A=R/'web/assets'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
pipeline=read(E/'runtime_pipeline.json'); geometry=read(E/'roundtrip.json')
cpu=read(E/'water_runtime_cpu_check.json'); materials=read(E/'fountain_export_check.json')
encoded=read(E/'runtime_encoding.json'); external=read(E/'runtime_externalization.json')
visual=read(E/'native_visual_review.json'); reflections=read(E/'reflection_visual_review.json')
metadata=read(A/f'{V}_bellevue.json')
assert pipeline['status']=='complete' and pipeline['version']==V
assert geometry['native_reopen_verified'] and not geometry['missing_images']
assert cpu['loopAndPauseVerified'] and not cpu['runtimeVisualAccepted']
assert materials['casting_roughness_texture_preserved'] and materials['boundary_stationary']
assert all(i['decoded_pixels_identical'] for i in encoded['images'])
assert external['geometry_byte_identity_verified']
assert len(visual['actual_images_viewed'])==3 and len(reflections['images'])==5
assert len(metadata['local_reflection_probes'])==5
assert metadata['indirect_occlusion']['receivers_verified']==565
assert hashlib.sha256((A/metadata['authored_runtime']['file']).read_bytes()).hexdigest()==metadata['authored_runtime']['sha256']
default_before=(A/'current.json').read_bytes()
candidate=read(A/'station_preview.json');assert candidate['version'] in ['G1_017r1',V]
candidate.update(version=V,construction_version=V,
    quality='construction_candidate_native_reviewed_geometry_animation_verified_graphics_pending',
    accepted=False,runtime_visual_accepted=False,natural_use_accepted=False)
(A/'station_preview.json').write_text(json.dumps(candidate,indent=2))
assert (A/'current.json').read_bytes()==default_before
working=read(R/'runtime/fountain_working.json')
working.update(runtime_exported=True,runtime_geometry_animation_verified=True,
    runtime_visual_accepted=False,natural_use_accepted=False,
    runtime_candidate='web/assets/station_preview.json',
    next='Actual browser material/animation review when available; adjacent continuous ground, tree and facility reconstruction meanwhile.')
(R/'runtime/fountain_working.json').write_text(json.dumps(working,indent=2))
pipeline['candidate_registered']=True;pipeline['candidate_registered_at']=datetime.datetime.now().isoformat()
(E/'runtime_pipeline.json').write_text(json.dumps(pipeline,indent=2))
report={'version':V,'native_identity_count':geometry['identities_verified'],
    'bounds_checked':len(geometry['matches']),'max_bounds_error_m':max(x['max_error_m'] for x in geometry['matches']),
    'decoded_images_unchanged':len(encoded['images']),'geometry_hash':encoded['geometry_runtime_hash'],
    'native_actual_views':len(visual['actual_images_viewed']),'native_local_probes_viewed':5,
    'cpu_animation_verified':True,'browser_tool':'nodeRepl.fetch request failed; no UI inventory available',
    'runtime_visual_accepted':False,'natural_use_accepted':False,'whole_G1_complete':False,
    'default_unchanged':True,'candidate_registered':True}
(E/'checkpoint_summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
