"""Construction diagnostics from already acquired sources; no additional survey fetch."""
from pathlib import Path
import json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import shape,Point
from inspect_platform_road_join import Surface,road
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'derived/haus_bellevue'
d=json.loads((D/'context.json').read_text());O=np.array(d['origin']);g=shape(d['sidewalk']['geometry']);b=shape(d['building_footprint']['geometry']);bottom=Surface(road)
fig,ax=plt.subplots(figsize=(14,9))
for f in d['adjacent_surfaces']+[d['sidewalk']]:
 p=shape(f['geometry']);a=np.array(p.exterior.coords)-O[:2]
 ax.fill(*a.T,alpha=.18);ax.plot(*a.T,lw=.7)
 c=np.array(p.representative_point().coords[0])-O[:2]
 ax.text(*c,str(f['properties']['objectid']),fontsize=9)
s=[x for x in d['ground_samples'] if x['initial_height_support']];p=np.array([x['point_ln02'] for x in s])-O
im=ax.scatter(p[:,0],p[:,1],c=p[:,2]+400,s=25,cmap='viridis');fig.colorbar(im,label='LN02 m')
for f in d['trees']:
 xy=np.array(shape(f['geometry']).coords[0][:2])-O[:2];ax.plot(*xy,'go',ms=12);ax.text(*xy,'tree '+str(f['id']))
for f in d['walking_links']:
 p=shape(f['geometry']);a=np.array(p.coords)[:,:2]-O[:2];ax.plot(*a.T,'r:',lw=1)
a=np.array(g.exterior.coords)-O[:2]
for i,p in enumerate(a):
 if i%3==0:ax.text(*p,str(i),fontsize=7,color='darkred')
ax.set(xlim=(-270,-195),ylim=(148,213),aspect='equal',xlabel='E local m',ylabel='N local m');ax.grid(alpha=.2)
fig.tight_layout();fig.savefig(D/'surface_diagnostic.png',dpi=130)
fit=d['robust_ground_fit'];c=np.array(fit['coefficients']);center=np.array(fit['xy_center_local']);joins=[]
for i,p in enumerate(a):
 z=float((p-center)@c[:2]+c[2]);rz,dist=bottom.sample(p)
 if dist<.08:joins.append({'vertex':i,'xy':p.tolist(),'height':z,'road':rz,'curb_upstand':z-rz,'distance':dist})
(D/'sidewalk_join_diagnostic.json').write_text(json.dumps({'boundary':a.tolist(),'road_joins':joins},indent=2))
print(json.dumps({'road_upstand_quantiles':np.quantile([j['curb_upstand'] for j in joins],[0,.1,.5,.9,1]).tolist(),'road_join_count':len(joins),'tree_properties':[f['properties'] for f in d['trees']],'boundary_vertices':len(a)}))
