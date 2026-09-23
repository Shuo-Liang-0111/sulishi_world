"""Read cached survey/photo support for the complete AV24105 riverside sidewalk."""
from pathlib import Path
import json,struct,hashlib
import numpy as np
from shapely.geometry import Point,Polygon,shape,mapping,box
from shapely.strtree import STRtree
from shapely import contains_xy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R=Path(__file__).resolve().parents[1];D=R/'derived/bellevue/limmat_sidewalk';D.mkdir(exist_ok=True)
O=np.array([2683775.,1246700.,400.])
features=json.loads((R/'sources/features/av_bo_boflaeche_a.geojson').read_text())['features']
f=next(f for f in features if f['properties']['objectid']==24105);g=shape(f['geometry'])
window=g.buffer(8);x0,y0,x1,y1=window.bounds
adj=[p for p in features if p['id']!=f['id'] and shape(p['geometry']).distance(g)<.04]
trees=[t for t in json.loads((R/'sources/features/bauminventar.geojson').read_text())['features'] if shape(t['geometry']).distance(g)<15]
# Terrain triangles are official LN02 heights. Deduplicate overlapping WFS tiles.
terrain={}
for path in (R/'sources/terrain').glob('*.geojson'):
 for t in json.loads(path.read_text())['features']:
  if shape(t['geometry']).intersects(window):terrain[t['id']]=t
tt=np.array([t['geometry']['coordinates'][0][:3] for t in terrain.values()]);tt[:,:,:3]-=O
pg=[Polygon(t[:,:2]) for t in tt];idx=STRtree(pg)
def ground(xy):
 xy=np.asarray(xy)-O[:2];hits=idx.query(Point(xy),predicate='intersects')
 if not len(hits):return None
 vals=[]
 for i in hits:
  t=tt[i];a=t[0];uv=np.linalg.solve((t[1:,:2]-a[:2]).T,xy-a[:2]);vals.append(float(a[2]+uv@(t[1:,2]-a[2])))
 return float(np.median(vals))+O[2]

samples=[];manifest=json.loads((R/'sources/mesh/local_GEOZ_3DMesh_2_1/manifest.json').read_text())
for item in manifest['items']:
 m=np.array(item['mbs'])
 if Point(m[:2]).distance(window)>m[3]:continue
 raw=Path(item['geometry']).read_bytes();nv=struct.unpack_from('<I',raw)[0]
 t=(np.frombuffer(raw,dtype='<f4',count=nv*3,offset=8).reshape(-1,3)+m[:3]).reshape(-1,3,3)
 c=t.mean(axis=1);n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);length=np.linalg.norm(n,axis=1)
 sel=np.flatnonzero((c[:,0]>x0)&(c[:,0]<x1)&(c[:,1]>y0)&(c[:,1]<y1)&(abs(n[:,2])>length*.88)&(length>.003)&(c[:,2]>402)&(c[:,2]<413))
 for i in sel:
  if not window.contains(Point(c[i,:2])):continue
  z=ground(c[i,:2])
  if z is None:continue
  samples.append({'point_ln02':c[i].tolist(),'terrain_ln02':z,'photo_minus_tin_m':float(c[i,2]-z),'source_node':item['node'],'triangle_index':int(i),'area_m2':float(length[i]/2),'on_sidewalk':g.buffer(-.08).contains(Point(c[i,:2]))})
support=[p for p in samples if p['on_sidewalk'] and abs(p['photo_minus_tin_m'])<.35]
rec={'base_version':'G1_018r3','source':f,'origin':O.tolist(),'neighbors':adj,'trees':trees,'terrain_triangles_local':tt.tolist(),'terrain_source_ids':list(terrain),'photo_samples':samples,'candidate_ground_support':support,'basis':'Existing AV93 footprint, cached official TIN and original unmodified photographic triangles. Photo/TIN residual filtering is a diagnostic, not proof that every sample is ground. Trees: source XY/species/inventory height; individual morphology remains inferred.','external_requests':0}
(D/'context.json').write_text(json.dumps(rec,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
fig,ax=plt.subplots(figsize=(7,15),dpi=130)
im=plt.imread(R/'sources/references/swissimage-context.jpg');ax.imshow(im,extent=[2683420,2684200,1246300,1247110])
for p in [g,*[shape(x['geometry']) for x in adj]]:
 if p.geom_type!='Polygon':continue
 xx,yy=p.exterior.xy;ax.plot(xx,yy,color='#10cbe0' if p is g else '#eeee66',lw=1.1)
 for ring in p.interiors:ax.plot(*ring.xy,c='#f433dd',lw=1)
for t in trees:
 xy=t['geometry']['coordinates'];ax.scatter(*xy,s=9,c='white',edgecolor='black',linewidth=.5);ax.annotate(str(t['properties']['objectid']),xy,xytext=(3,2),textcoords='offset points',fontsize=6,c='white',bbox={'facecolor':'black','alpha':.55,'pad':.3})
if support:
 pp=np.array([p['point_ln02'] for p in support]);cc=np.array([p['photo_minus_tin_m'] for p in support]);sc=ax.scatter(pp[:,0],pp[:,1],c=cc,vmin=-.3,vmax=.3,cmap='coolwarm',s=8);fig.colorbar(sc,ax=ax,label='Photographic height minus official TIN (m)',fraction=.04)
ax.set_xlim(x0,x1);ax.set_ylim(y0,y1);ax.set_aspect('equal');ax.ticklabel_format(useOffset=False,style='plain');ax.tick_params(labelsize=7);ax.set_title('AV24105 | cached sources; no design geometry')
fig.tight_layout();fig.savefig(D/'source_ground_overlay.png');plt.close(fig)
bins=[]
for north in range(1246850,1246980,10):
 a=[p for p in support if north<=p['point_ln02'][1]<north+10]
 bins.append({'northing':north,'n':len(a),'z':np.quantile([p['point_ln02'][2] for p in a],[.1,.5,.9]).tolist() if a else None,'delta':np.quantile([p['photo_minus_tin_m'] for p in a],[.1,.5,.9]).tolist() if a else None})
print(json.dumps({'area':g.area,'holes':len(g.interiors),'terrain_triangles':len(tt),'photo_samples':len(samples),'near_ground_on_sidewalk':len(support),'height_bins':bins,'neighbors':[{'id':a['id'],'kind':a['properties']['art_txt']} for a in adj]},indent=2))
