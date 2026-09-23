"""Save official catalogue metadata and service capabilities for G1 planning."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import requests
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'sources'/'catalogue'
OUT.mkdir(parents=True, exist_ok=True)
API = 'https://data.stadt-zuerich.ch/api/3/action/'
PACKAGES = ['geo_bauten___dachmodell', 'geo_fuss__und_velowegnetz',
            'geo_brunnen', 'geo_bauminventar', 'geo_digitales_terrainmodell__tin_',
            'geo_kunstbauteninventar']

def save(url, path):
    if path.exists():
        data=path.read_bytes()
        return data, {'url':url, 'cache':True, 'bytes':len(data),
                      'sha256':hashlib.sha256(data).hexdigest()}
    r=requests.get(url, timeout=(10,45))
    r.raise_for_status()
    data=r.content
    path.write_bytes(data)
    return data, {'url':r.url,'utc':datetime.now(timezone.utc).isoformat(),
                  'http':r.status_code,'bytes':len(data),
                  'sha256':hashlib.sha256(data).hexdigest()}

def one(name):
    receipts=[]
    try:
        raw, receipt=save(API+'package_show?id='+name, OUT/(name+'.json'))
        receipts.append(receipt)
        j=json.loads(raw)
        if not j.get('success'): raise ValueError(str(j.get('error')))
        p=j['result']
        resources=[{'name':r.get('name'),'format':r.get('format'),'url':r.get('url')}
                   for r in p.get('resources',[])]
        result={'package':name,'title':p.get('title'),'license':p.get('license_id'),
                'resources':resources,'capabilities':[]}
        for i,r in enumerate(resources):
            if 'wfs' not in (str(r['format'])+' '+str(r['name'])).lower(): continue
            try:
                url=r['url']
                if 'getcapabilities' not in url.lower():
                    url += ('&' if '?' in url else '?')+'service=WFS&request=GetCapabilities'
                data,rec=save(url, OUT/f'{name}-wfs-{i}.xml')
                receipts.append(rec)
                xml=ET.fromstring(data)
                types=[]
                for e in xml.iter():
                    if e.tag.split('}')[-1]=='FeatureType':
                        types.append({c.tag.split('}')[-1]:c.text for c in e
                                      if c.tag.split('}')[-1] in ['Name','Title','DefaultSRS','DefaultCRS']})
                formats=[e.text for e in xml.iter() if e.tag.split('}')[-1]=='OutputFormat']
                result['capabilities'].append({'url':url,'types':types,'formats':formats})
            except Exception as e:
                result['capabilities'].append({'error':str(e),'url':r['url']})
    except Exception as e: result={'package':name,'error':str(e)}
    result['receipts']=receipts
    (OUT/(name+'-summary.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'package':name,'ok':'error' not in result,
                      'types':[t['Name'] for c in result.get('capabilities',[]) for t in c.get('types',[])]},ensure_ascii=False),flush=True)
    return result

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(one,PACKAGES))
    raw, receipt=save(API+'package_search?q=Amtliche%20Vermessungsdaten&rows=15',OUT/'survey-search.json')
    search=json.loads(raw)
    print(json.dumps({'survey_candidates':[(p['name'],p['title']) for p in search.get('result',{}).get('results',[])]},ensure_ascii=False))
    (OUT/'index.json').write_text(json.dumps({'packages':results,'survey_receipt':receipt},ensure_ascii=False,indent=2),encoding='utf-8')
