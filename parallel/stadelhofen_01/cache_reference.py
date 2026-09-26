from pathlib import Path
import urllib.request, pypdfium2, json, hashlib, datetime
OUT=Path(__file__).resolve().parent
url='https://odb.zh.ch/odbwiki/mediawiki/files/pdfs/Zuerich-Inventar_8349_1-festgesetzt_2020.pdf'
path=OUT/'sources/zh_heritage_stadelhofen_2020.pdf'
if not path.exists():
    with urllib.request.urlopen(url,timeout=50) as response: data=response.read()
    assert data.startswith(b'%PDF')
    path.write_bytes(data)
pdf=pypdfium2.PdfDocument(path)
for i in [5,6]:
    pdf[i].render(scale=2).to_pil().save(OUT/'sources'/f'heritage_page_{i+1}.png')
(OUT/'sources/heritage_text.txt').write_text('\n'.join(p.get_textpage().get_text_range() for p in pdf),encoding='utf-8')
(OUT/'sources/heritage_receipt.json').write_text(json.dumps(dict(url=url,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),use='Primary cantonal heritage inventory; photographic and construction reference, never used as texture',pages=len(pdf)),indent=2))
print('reference PDF cached',len(pdf),'pages',flush=True)
