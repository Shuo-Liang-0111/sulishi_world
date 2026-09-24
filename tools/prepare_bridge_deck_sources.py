"""Fetch only the missing west bridge infrastructure and one bounded orthophoto."""
from pathlib import Path
import argparse, datetime, hashlib, io, json, shutil, urllib.parse, urllib.request
from PIL import Image

R = Path(__file__).resolve().parents[1]
D = R/'sources/features/quaibruecke_deck'
D.mkdir(parents=True,exist_ok=True)
assert shutil.disk_usage(R).free > 200_000_000
parser=argparse.ArgumentParser()
parser.add_argument('--cached-only',action='store_true')
args=parser.parse_args()
receipt_path=D/'receipt.json'
previous=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
previous_files={q['file']:q for q in previous.get('files',[])}
bounds = [2683358, 1246776, 2683506, 1246852]
records = []
def fetch(url, path, kind):
    name=path.relative_to(R).as_posix();cached=path.exists()
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    if path.exists():
        body = path.read_bytes()
        record=previous_files.get(name)
        assert record and record['url']==url,'Cached source URL is unverified: '+name
        assert hashlib.sha256(body).hexdigest()==record['sha256'],'Cached source changed: '+name
        obtained_at=record.get('retrieved_at',previous.get('retrieved_at'))
    else:
        assert not args.cached_only,'Missing cached source: '+name
        req = urllib.request.Request(url, headers={'User-Agent':'ZurichWorld local scene reconstruction'})
        with urllib.request.urlopen(req, timeout=40) as response:
            body = response.read(8_000_001)
        obtained_at=now
    assert len(body) < 8_000_000
    if kind == 'geojson':
        data = json.loads(body)
        assert data['type'] == 'FeatureCollection' and len(data['features']) < 1000
    else:
        with Image.open(io.BytesIO(body)) as im: im.verify()
    if not cached:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(body)
    records.append(dict(file=name,url=url,bytes=len(body),retrieved_at=obtained_at,
                        reused_cache=cached,sha256=hashlib.sha256(body).hexdigest()))

for layer in ['fahrleitungen_mast','fahrleitungen_fahrdraht','fahrleitungen_tragwerk_linie']:
    query=dict(service='WFS',version='1.1.0',request='GetFeature',typeName=layer,
               bbox=','.join(map(str,bounds))+',EPSG:2056',srsName='EPSG:2056',
               outputFormat='application/vnd.geo+json',maxFeatures=1000)
    url='https://www.ogd.stadt-zuerich.ch/wfs/geoportal/VBZ_Infrastruktur_OGD?'+urllib.parse.urlencode(query)
    fetch(url,D/(layer+'.geojson'),'geojson')

Q=R/'sources/references/quaibruecke'
query=dict(service='WMS',request='GetMap',version='1.3.0',layers='ch.swisstopo.swissimage',
           styles='',crs='EPSG:2056',bbox=','.join(map(str,bounds)),width=2220,height=1140,format='image/jpeg')
fetch('https://wms.geo.admin.ch/?'+urllib.parse.urlencode(query),Q/'swissimage-bridge-deck.jpg','image')
receipt=dict(checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
             bounds_lv95=bounds,orthophoto_size=[2220,1140],orthophoto_flight_date_verified=False,
             bbox_extension_is_background_not_g1_expansion=True,files=records,
             source_caution='VBZ wire data reliability is limited; positions are source evidence, missing heights and fabrication need interpretation.')
(D/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(dict(files=len(records),bytes=sum(q['bytes'] for q in records),counts={p.name:len(json.loads(p.read_text())['features']) for p in D.glob('*.geojson')})))
