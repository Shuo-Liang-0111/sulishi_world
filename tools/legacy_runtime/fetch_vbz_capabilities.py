import requests,json,xml.etree.ElementTree as ET
from pathlib import Path
p=Path('sources/catalogue');u='https://www.ogd.stadt-zuerich.ch/wfs/geoportal/VBZ_Infrastruktur_OGD'
r=requests.get(u,params={'service':'WFS','request':'GetCapabilities','version':'1.1.0'},timeout=(12,45));r.raise_for_status();(p/'vbz_infrastructure_capabilities.xml').write_bytes(r.content)
e=ET.fromstring(r.content)
ns={'wfs':'http://www.opengis.net/wfs'}
print(json.dumps([{'name':x.find('wfs:Name',ns).text,'title':x.find('wfs:Title',ns).text} for x in e.findall('.//wfs:FeatureType',ns)],ensure_ascii=False))
