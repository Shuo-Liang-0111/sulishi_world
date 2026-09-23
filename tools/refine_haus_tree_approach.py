"""Clear observed tree69773 spill from the real approach, preserving nearby fixtures."""
from pathlib import Path
import json,runpy,numpy as np
from shapely.geometry import Point,mapping
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/west_context'
old=json.loads((D/'tree_69773_input.json').read_text(encoding='utf-8'));xy=np.array(old['source']['geometry']['coordinates']);g=old['ground_ln02_m']
mask=Point(xy).buffer(8.1,quad_segs=64)
protected=[{'id':'fahrleitungen_mast.1800','xy':[2683529.27,1246848.261],'radius':.80},
 {'id':'haltestellen_infosystem.1143+2584','xy':[2683531.597,1246849.243],'radius':1.05}]
for p in protected:mask=mask.difference(Point(p['xy']).buffer(p['radius'],quad_segs=32))
runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={
 'CUT_MASK':mask,'CUT_LOWER':g+.12,'CUT_UPPER':g+14.,'CUT_BASE':'haus_tree_119962_photo_cut.json','CUT_OUTPUT':'haus_trees_approach_refined_cut.json','CUT_STATS_KEY':'observed_tree_spill',
 'CUT_DESCRIPTION':'Same-camera G1_011 rays hit CTX_I3S34280 only1.6..1.8m ahead at localX-242.7..-241.7 Y149.7..150.6 Z10.25..11.24, outside old5.5m tree69773 envelope. Replace expanded8.1m tree envelope above soil+0.12 to soil+14, preserving mast1800 radius0.8m and information1143/2584 radius1.05m. These upright source fixtures are not claimed reconstructed.'})
(R/'derived/haus_bellevue/tree_approach_review.json').write_text(json.dumps({'observed_source_node':'34280','hits_local':[[-242.70953369,149.71128845,11.23799324],[-242.30599975,150.30279541,10.84173298],[-241.72140503,150.59504699,10.65176678]],'protected':protected,'mask_lv95':mapping(mask),'remaining':'Protected equipment still needs exact type interpretation and reconstruction; unbuilt adjacent ground retained.'},indent=2))
