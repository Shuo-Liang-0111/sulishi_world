"""Acquire public VBZ physical infrastructure within the existing source envelope."""
import json,hashlib
from datetime import datetime,timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'sources/features/vbz';OUT.mkdir(exist_ok=True)
BBOX=[2683420,1246300,2684200,1247110]
ENDPOINT='https://www.ogd.stadt-zuerich.ch/wfs/geoportal/VBZ_Infrastruktur_OGD'
LAYERS=['strecke_gleisachse','strecke_schienen','strecke_radlenker','strecke_tr_weiche','strecke_tr_kreuzung','strecke_weichensignal','fahrleitungen_mast','fahrleitungen_fahrdraht','fahrleitungen_tragwerk_linie','fahrleitungen_mauerbolzen','haltestellen_blindenrillenplat','haltestellen_haltebalken','haltestellen_ticketautomat','haltestellen_dfi_anzeiger','haltestellen_infosystem','haltestellen_papierkorb','haltestellen_sitzgelegenheit','haltestellen_wartehalle','haltestellen_plakatstelle','haltestellen_ticketentwerter','haltestellen_elektroschrank','haltestellen_sipf']
def fetch(layer):
    path=OUT/(layer+'.geojson');receipt=OUT/(layer+'-receipt.json')
    if path.exists() and receipt.exists():return json.loads(receipt.read_text())
    params={'service':'WFS','version':'1.1.0','request':'GetFeature','typeName':layer,'bbox':','.join(map(str,BBOX))+',EPSG:2056','srsName':'EPSG:2056','outputFormat':'application/vnd.geo+json','maxFeatures':20000}
    r=requests.get(ENDPOINT,params=params,timeout=(12,70));r.raise_for_status();j=r.json()
    assert j['type']=='FeatureCollection' and len(j['features'])<20000
    path.write_bytes(r.content)
    rec={'layer':layer,'url':r.url,'catalogue':'https://data.stadt-zuerich.ch/dataset/geo_vbz_infrastruktur_ogd','utc':datetime.now(timezone.utc).isoformat(),'feature_count':len(j['features']),'bytes':len(r.content),'sha256':hashlib.sha256(r.content).hexdigest(),'bbox_epsg2056':BBOX,'crs':j.get('crs'),'license':'CC0','role':'source evidence, not automatically accepted geometry','caution':'Catalogue warns overhead contact-wire data reliability 20%, quality 50%; check against imagery. Update epoch is not a surveyed feature date.'}
    receipt.write_text(json.dumps(rec,ensure_ascii=False,indent=2));return rec
if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        for rec in pool.map(fetch,LAYERS):print(json.dumps({k:rec[k] for k in ['layer','feature_count','bytes']}),flush=True)
