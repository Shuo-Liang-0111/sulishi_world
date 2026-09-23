"""Bounded cleanup for photo remnants around the reconstructed curved balcony."""
from pathlib import Path
import json, runpy, numpy as np
from shapely.geometry import Polygon
R=Path(__file__).resolve().parents[1]
d=json.loads((R/'derived/haus_bellevue/upper_input.json').read_text())
c=np.array(d['corner']['center_local'])+np.array([2683775,1246700])
r=d['corner']['radius_m']+1.9
angles=np.radians(np.linspace(-100,55,130))
mask=Polygon([c,*[c+r*np.array([np.cos(a),np.sin(a)]) for a in angles]])
runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={
 'CUT_MASK':mask,'CUT_LOWER':416.4,'CUT_UPPER':419.0,
 'CUT_BASE':'haus_upper_corner_photo_cut.json','CUT_OUTPUT':'haus_upper_balcony_refined_cut.json',
 'CUT_STATS_KEY':'haus_balcony_remnants',
 'CUT_DESCRIPTION':'Eye-level render exposed old photo fragments above the rebuilt curved balcony. Remove only this corner wedge within LN02 416.4..419.0; neighboring facades, reference originals, and other heights retained.'})
