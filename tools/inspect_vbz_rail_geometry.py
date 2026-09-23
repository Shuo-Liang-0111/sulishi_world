import json
from pathlib import Path
import numpy as np
from shapely.geometry import shape,box,Point
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'derived/bellevue/transport'
area=box(2683500,1246765,2683650,1246910)
load=lambda n:json.loads((ROOT/'sources/features/vbz'/f'{n}.geojson').read_text())['features']
axes=[shape(f['geometry']).intersection(area) for f in load('strecke_gleisachse') if shape(f['geometry']).intersects(area)]
rail=[f for f in load('strecke_schienen') if shape(f['geometry']).intersects(area)]
axis=unary_union(axes)
fig,ax=plt.subplots(figsize=(13,12),layout='constrained')
ax.imshow(Image.open(ROOT/'sources/references/swissimage-context.jpg'),extent=[2683420,2684200,1246300,1247110])
for g in axes:
    for ln in (g.geoms if hasattr(g,'geoms') else [g]):
        xy=np.array(ln.coords);ax.plot(xy[:,0],xy[:,1],c='cyan',lw=.5)
d=[]
for f in rail:
    g=shape(f['geometry']).intersection(area)
    for ln in (g.geoms if hasattr(g,'geoms') else [g]):
        if ln.geom_type!='LineString':continue
        xy=np.array(ln.coords);ax.plot(xy[:,0],xy[:,1],c='orange',lw=.55)
        d.extend([axis.distance(ln.interpolate(t)) for t in np.arange(0,ln.length,.5)])
ax.set_xlim(2683510,2683630);ax.set_ylim(1246795,1246880);ax.set_aspect('equal');ax.ticklabel_format(style='plain',useOffset=False)
ax.set_title('VBZ actual rails orange / axes cyan: source geometry, no invented network')
fig.savefig(OUT/'vbz_rail_overlay.png',dpi=160)
report={'local_rail_features':len(rail),'rail_to_nearest_axis_distance_quantiles_m':np.quantile(d,[0,.1,.25,.5,.75,.9,1]).tolist(),'interpretation':'Distances near .5m support rails as individual rail lines, not metre-gauge track axes; inspect crossings separately.'}
(OUT/'vbz_rail_interpretation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
