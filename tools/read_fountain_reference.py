"""Read the one public art inventory page for fountain59; no internal photo host."""
import json,re,sys,urllib.request
from pathlib import Path
from html.parser import HTMLParser
sys.stdout.reconfigure(encoding='utf-8')
url='https://kbsz.zetcom.net/de/collection/item/556/'
html=urllib.request.urlopen(url,timeout=20).read().decode()
class Images(HTMLParser):
    def __init__(self):super().__init__();self.nodes=[];self.scripts=[];self.capture=False;self.part=''
    def handle_starttag(self,tag,attrs):
        data=dict(attrs)
        if tag in ['img','source'] or any('image' in str(v) or '.jpg' in str(v) for k,v in attrs if k in ['style','src','data-src']):self.nodes.append({'tag':tag,**data})
        if tag=='script' and data.get('id')=='__NEXT_DATA__':self.capture=True
    def handle_data(self,data):
        if self.capture:self.part+=data
    def handle_endtag(self,tag):
        if tag=='script' and self.capture:self.capture=False;self.scripts.append(json.loads(self.part));self.part=''
parser=Images();parser.feed(html)
def find_images(value,path=''):
    if isinstance(value,dict):
        for k,v in value.items():yield from find_images(v,path+'/'+k)
    elif isinstance(value,list):
        for i,v in enumerate(value):yield from find_images(v,path+'/'+str(i))
    elif isinstance(value,str) and any(x in value.lower() for x in ['.jpg','.jpeg','.png']):yield {'path':path,'value':value}
data={'source_url':url,'image_elements':parser.nodes,'structured_image_links':list(find_images(parser.scripts))}
R=Path(__file__).resolve().parents[1];D=R/'sources/references/bellevue_fountain59';D.mkdir(exist_ok=True)
(D/'public_page.html').write_text(html,encoding='utf-8');(D/'image_links.json').write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(data,ensure_ascii=False,indent=2)[:8000])
