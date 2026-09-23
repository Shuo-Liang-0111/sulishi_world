"""Evidence-only plan overlay: distinguish surveyed rail centre lines and ground regions."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from shapely.geometry import shape,box
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'derived/bellevue/transport';OUT.mkdir(exist_ok=True)
bounds=(2683500,1246765,2683650,1246910);area=box(*bounds)
cad=json.loads((ROOT/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features']
lines=json.loads((ROOT/'sources/features/av_ei_linienelement.geojson').read_text())['features']
roads=[f for f in cad if shape(f['geometry']).intersects(area)]
rails=[f for f in lines if f['properties']['art_txt']=='Bahngeleise' and shape(f['geometry']).intersects(area)]
image=np.array(Image.open(ROOT/'sources/references/swissimage-context.jpg'))
fig,axes=plt.subplots(1,2,figsize=(18,9),layout='constrained')
for ax in axes:
    ax.imshow(image,extent=[2683420,2684200,1246300,1247110]);ax.set_xlim(bounds[0],bounds[2]);ax.set_ylim(bounds[1],bounds[3]);ax.set_aspect('equal');ax.ticklabel_format(style='plain',useOffset=False)
for f in roads:
    g=shape(f['geometry']).intersection(area)
    for part in (g.geoms if hasattr(g,'geoms') else [g]):
        if part.geom_type!='Polygon':continue
        xy=np.array(part.exterior.coords);axes[1].plot(xy[:,0],xy[:,1],c='#00f7ff',lw=.7)
for i,f in enumerate(rails):
    xy=np.array(f['geometry']['coordinates']);axes[1].plot(xy[:,0],xy[:,1],c='#ff803b',lw=1)
    g=shape(f['geometry']).intersection(area);p=g.interpolate(.5,normalized=True)
    axes[1].text(p.x,p.y,str(i),fontsize=6,color='white',bbox=dict(fc='black',alpha=.65,pad=.5))
axes[0].set_title('Official SWISSIMAGE: unchanged context')
axes[1].set_title('AV 2025: ground boundaries (cyan), Bahngeleise (orange)')
fig.savefig(OUT/'source_overlay.png',dpi=150)
(OUT/'source_features.json').write_text(json.dumps({'bounds':bounds,'rail_lines':rails,'ground_regions':roads},ensure_ascii=False))
print(json.dumps({'rail_records':len(rails),'ground_regions':len(roads),'output':str(OUT/'source_overlay.png')}))
