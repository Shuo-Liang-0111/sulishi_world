"""Inspect already cached aerial evidence and source identities, without fetching."""
from pathlib import Path
import json,numpy as np
from shapely.geometry import shape
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/south_context';d=json.loads((D/'ground_support.json').read_text(encoding='utf-8'));g=shape(d['av']['geometry']);fig,ax=plt.subplots(figsize=(14,9),layout='constrained');ax.imshow(Image.open(R/'sources/references/swissimage-bellevue-detail.jpg'),extent=[2683500,2683650,1246765,1246910])
for ring in [g.exterior,*g.interiors]:
 xy=np.array(ring.coords);ax.plot(*xy.T,color='#00efff',lw=1.2)
for t in d['trees']:
 xy=t['geometry']['coordinates'];ax.plot(*xy,'o',color='yellow',ms=4);ax.annotate(t['id'].split('.')[-1]+f"/{t['properties']['hoehe']:g}m",xy,xytext=(3,3),textcoords='offset points',color='yellow',fontsize=8,bbox={'facecolor':'black','alpha':.65,'pad':1})
for f in d['facilities']:
 p=shape(f['geometry']).centroid;ax.plot(p.x,p.y,'+',color='#ff66cc',ms=6)
for f in json.loads((R/'sources/features/tbl_routennetz.geojson').read_text())['features']:
 line=shape(f['geometry'])
 if not line.intersects(g):continue
 for l in ([line] if line.geom_type=='LineString' else line.geoms):
  xy=np.array(l.coords);ax.plot(*xy[:,:2].T,color='#ff9933',alpha=.7,lw=1)
ax.set_xlim(g.bounds[0]-5,g.bounds[2]+5);ax.set_ylim(g.bounds[1]-4,g.bounds[3]+4);ax.set_aspect('equal');ax.set_title('AV3573: existing cadastral plan / tree identities / VBZ points / walking network');fig.savefig(D/'source_overlay.png',dpi=150)
print(json.dumps({'area_m2':g.area,'interior_rings':len(g.interiors),'image':str(D/'source_overlay.png')}))
