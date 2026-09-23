"""Replace only the measured storefront's stretched photo awning remnants."""
from pathlib import Path
import json,runpy,numpy as np
from shapely.geometry import Polygon
R=Path(__file__).resolve().parents[1];d=json.loads((R/'derived/haus_bellevue/build_input.json').read_text());f=d['frontage'];C=np.array(f['C'])+[2683775,1246700];right=np.array(f['right']);out=np.array(f['out'])
p=Polygon([C+right*u+out*v for u,v in [(f['u_min']-.08,1.35),(f['u_max']+.08,1.35),(f['u_max']+.08,-3.6),(f['u_min']-.08,-3.6)]])
runpy.run_path(str(R/'tools/prepare_bellevue_west_shelter_cut.py'),init_globals={'CUT_MASK':p,'CUT_UPPER':413.34,'CUT_LOWER':408.0,'CUT_BASE':'haus_frontage_photo_cut.json','CUT_OUTPUT':'haus_frontage_r1_photo_cut.json','CUT_STATS_KEY':'haus_remnant','CUT_DESCRIPTION':'Entry-camera rays identified stretched photo awning remnants in node36449 at outward distance0.526–0.836m, LN02 410.82–411.16m. Rebuilt storefront replacement band expanded to1.35m, only across the current30.6m frontage below413.34m; source upper floors and corner remain.'})
