"""Cache first-party reference photographs for local modelling review, not texture redistribution."""
from pathlib import Path
import json,hashlib
from datetime import datetime,timezone
import concurrent.futures
import requests
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'sources/references/architecture';OUT.mkdir(exist_ok=True)
BASE='https://images.squarespace-cdn.com/content/v1/5923e966e3df28823047d68b/'
SOURCES=[
 ('belcafe-exterior.jpg',BASE+'1502296124668-GKWAE2S4LO6T3N5W2RXV/Belcafe_am_Bellevue-Rondell_Architektur_Stadt_Zuerich_Amt_fuer_Hochbauten_','https://www.belcafe.ch/architektur'),
 ('belcafe-interior.jpg',BASE+'1502296588969-LA58UFMEF00GCUKJD50E/belcafe-bellvue-rondell-stadt-zuerich-architektur','https://www.belcafe.ch/architektur'),
 ('belcafe-ceiling.jpg',BASE+'1502297478008-UDINY9KQBF1PVODZIQKO/belcafe-bellevue-rondell-windrose-stadt-zuerich-architektur','https://www.belcafe.ch/architektur'),
 ('belcafe-angle-3.jpg',BASE+'1502296636372-Z0USNPUYFDRDXYZJDX6X/belcafe-bellevue-rondell-stadt-zuerich-architektur','https://www.belcafe.ch/architektur'),
 ('belcafe-windrose.jpg',BASE+'1502297780921-KWGC7N4WWGCZNAY2DAA9/belcafe-bellevue-rondell-stadt-zuerich-architektur-windrose','https://www.belcafe.ch/architektur'),
 ('belcafe-angle-4.jpg',BASE+'1502297921609-O6VWV4WVI79ZD44D36YI/belcafe-bellevue-rondell-stadt-zuerich-architektur','https://www.belcafe.ch/architektur'),
]
def one(item):
    name,url,page=item;p=OUT/name
    if not p.exists():
        r=requests.get(url,timeout=(10,40));r.raise_for_status();p.write_bytes(r.content)
    return {'file':name,'url':url,'page':page,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
            'use':'local architectural reference only; not a model texture or redistributed asset',
            'acquisition_utc':datetime.now(timezone.utc).isoformat(),'photo_date':'unresolved; page discusses 2005 renovation'}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:receipts=list(pool.map(one,SOURCES))
(OUT/'receipts.json').write_text(json.dumps(receipts,indent=2),encoding='utf-8')
print(json.dumps({'cached':len(receipts)}))
