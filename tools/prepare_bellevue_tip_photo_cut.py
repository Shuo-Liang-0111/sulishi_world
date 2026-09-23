"""Clear the already rebuilt walking strip beside the roof's narrow end."""
from pathlib import Path
import json,runpy
from shapely.geometry import shape,box,Point,mapping

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'derived/bellevue/west_context'
platform=shape(json.loads((OUT/'platform_input.json').read_text())['geometry_lv95'])
mask=platform.intersection(box(2683556,1246860,2683563.5,1246866))
# Preserve the nearby recorded information mast. This is a bounded walking strip,
# not an expanding circle that erases neighbouring sources to clean one camera.
assert mask.distance(Point(2683564.245,1246865.361))>.70
ray_hits=[[2683559.47966,1246863.01155,409.22134],[2683559.35803,1246863.44408,409.48726],
          [2683559.58638,1246862.92131,408.86736],[2683559.25354,1246863.53723,409.12474]]
assert all(mask.covers(Point(p[:2])) for p in ray_hits)
record={'source':'av_bo_boflaeche_a.459','mask_lv95':mapping(mask),'area_m2':mask.area,'upper_ln02_m':412.1,
        'camera':'BE_QA_WEST_PLATFORM_REVERSE','observed_ray_hits_G1_008r4':ray_hits,
        'evidence':'Source orthophoto, actual native ray hits, official facility positions. Authored platform/DFI present; nearest other info mast outside mask.',
        'uncertainty':'Original low photo mass identity not established; its removal restores inferred normal walking space, not a surveyed detailed historic state.',
        'accepted':False}
(OUT/'tip_photo_cut_basis.json').write_text(json.dumps(record,indent=2))
runpy.run_path(str(ROOT/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={
 'CUT_MASK':mask,'CUT_UPPER':412.10,'CUT_BASE':'fixtures_photo_cut.json',
 'CUT_OUTPUT':'platform_tip_photo_cut.json','CUT_STATS_KEY':'tip_stats',
 'CUT_DESCRIPTION':'Bounded replacement of the already rebuilt AV459 walking strip alongside the narrow roof end (source polygon intersect E2683556..2683563.5/N1246860..1246866), below LN02 412.10m. Source DFI rebuilt; adjacent info mast at E2683564.245/N1246865.361 excluded. See tip_photo_cut_basis.json for observed ray hits and uncertain artifact identity.',
})
