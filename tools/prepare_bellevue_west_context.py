"""Resolve the next continuous near-ground area from source identities, not generic props."""
import json,hashlib,datetime,urllib.request,urllib.parse
from pathlib import Path
from collections import Counter
from shapely.geometry import shape,box,mapping
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'derived/bellevue/west_context';OUT.mkdir(parents=True,exist_ok=True)
B=[2683490,1246805,2683575,1246905];area=box(*B)
layers={
 'surfaces':'sources/features/av_bo_boflaeche_a.geojson',
 'trees':'sources/features/bauminventar.geojson',
 'walking':'sources/features/tbl_routennetz.geojson',
}
selected={};receipts={}
for name,rel in layers.items():
 p=ROOT/rel;fs=json.loads(p.read_text())['features'];keep=[]
 for f in fs:
  g=shape(f['geometry'])
  if not g.intersects(area):continue
  if name=='surfaces' and f['properties'].get('status_txt')!='real':continue
  if name=='walking' and not f['properties'].get('fuss'):continue
  keep.append(f)
 selected[name]=keep
 receipts[name]={'file':rel,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'count':len(keep)}
 # Retain entire source features; the rectangle is an investigation window,
 # never permission to create a new physical edge through a real island.
 (OUT/f'{name}.geojson').write_text(json.dumps({'type':'FeatureCollection','crs':{'type':'name','properties':{'name':'EPSG:2056'}},'features':keep},ensure_ascii=False))

ref=ROOT/'sources/references/swissimage-bellevue-west.jpg'
params={'service':'WMS','request':'GetMap','version':'1.3.0','layers':'ch.swisstopo.swissimage','styles':'','crs':'EPSG:2056','bbox':','.join(map(str,B)),'width':1275,'height':1500,'format':'image/jpeg'}
url='https://wms.geo.admin.ch/?'+urllib.parse.urlencode(params)
receipt=ref.with_suffix('.json')
if not ref.exists():
 with urllib.request.urlopen(url,timeout=60) as r:raw=r.read()
 import io
 im=Image.open(io.BytesIO(raw));im.verify();ref.write_bytes(raw)
 receipt.write_text(json.dumps({'url':url,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'bounds_lv95':B,'size_px':[1275,1500],'sha256':hashlib.sha256(raw).hexdigest(),'acquisition_date':None,'note':'Requested sampling is not source ground resolution; investigation reference only'},indent=2))
else:
 assert json.loads(receipt.read_text())['sha256']==hashlib.sha256(ref.read_bytes()).hexdigest()

fig,ax=plt.subplots(figsize=(10,11));ax.imshow(Image.open(ref),extent=[B[0],B[2],B[1],B[3]],origin='upper')
colors={'befestigt.Trottoir':'#25f7ec','befestigt.Verkehrsinsel':'#ff59e4','befestigt.Strasse_Weg.Velo_Fussweg':'#80d3ff'}
for f in selected['surfaces']:
 color=colors.get(f['properties'].get('art_txt'))
 if color is None:continue
 g=shape(f['geometry']).intersection(area)
 for p in ([g] if g.geom_type=='Polygon' else getattr(g,'geoms',[])):
  if p.geom_type!='Polygon':continue
  x,y=p.exterior.xy;ax.plot(x,y,color=color,linewidth=1.2)
  for h in p.interiors:ax.plot(*h.xy,color=color,linewidth=.8)
  q=p.representative_point();ax.text(q.x,q.y,f['id'].split('.')[-1],fontsize=7,color='white',bbox={'facecolor':'black','alpha':.65,'pad':1})
for f in selected['walking']:
 g=shape(f['geometry']).intersection(area)
 for line in ([g] if g.geom_type=='LineString' else getattr(g,'geoms',[])):
  if line.geom_type=='LineString':ax.plot(*line.xy,color='white',alpha=.65,linewidth=.7,linestyle='--')
for f in selected['trees']:
 x,y=f['geometry']['coordinates'];p=f['properties'];ax.plot(x,y,'o',ms=4,mfc='#fff132',mec='black')
 ax.text(x+.5,y+.7,f"{f['id'].split('.')[-1]} / {p.get('hoehe')}m",fontsize=6,color='#ffff78',bbox={'facecolor':'black','alpha':.7,'pad':1})
ax.set(xlim=[B[0],B[2]],ylim=[B[1],B[3]],aspect='equal',title='Bellevue west: source surface boundaries, walking links and measured tree identities')
ax.ticklabel_format(style='plain',useOffset=False);ax.tick_params(labelsize=7);fig.tight_layout();fig.savefig(OUT/'source_overlay.png',dpi=180);plt.close(fig)
report={'bounds_lv95':B,'scope_role':'Investigation window, not completed construction','sources':receipts,'tree_species':dict(Counter(f['properties'].get('baumart_lat') for f in selected['trees'])),'tree_position_quality':dict(Counter(f['properties'].get('genauigkeit') for f in selected['trees'])),'image':str(ref.relative_to(ROOT)),'next':['Inspect photo and source footprint connectivity before choosing complete surface pieces','Sample ground, raised curbs and crossing ramps separately; no constant generic island height','Reconstruct matching Platanus habit and leaf/bark type at source positions; crown dimensions and branch geometry remain inferred','Remove photo working-copy vegetation only inside reviewed replacement volumes; retain originals'],'accepted':False}
(OUT/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));print(json.dumps(report,ensure_ascii=False))
