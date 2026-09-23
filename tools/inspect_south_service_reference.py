from pathlib import Path
import json,hashlib
import pypdfium2 as pdfium
R=Path(__file__).resolve().parents[1];D=R/'sources/references/south_service';p=D/'Masterplan_ZueriWC_2015.pdf';pdf=pdfium.PdfDocument(str(p));hits=[]
for i in range(len(pdf)):
 text=pdf[i].get_textpage().get_text_range()
 if 'Bellevueplatz' in text and ('G01306' in text or '23.06' in text):
  image=D/f'WC_Bellevue_page_{i+1}.png';pdf[i].render(scale=2.5).to_pil().save(image);(D/f'WC_Bellevue_page_{i+1}.txt').write_text(text,encoding='utf-8');hits.append({'pdf_page_1based':i+1,'image':str(image),'text':text})
(D/'masterplan_receipt.json').write_text(json.dumps({'url':'https://disco-legacy-data.s3.eu-central-1.amazonaws.com/public/upload/5/6/56987.pdf','publisher':'Stadt Zuerich UGZ / IMMO,2015 (public mirrored PDF)','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'pages':len(pdf),'matched_pages':[h['pdf_page_1based'] for h in hits],'use':'Dated architectural reference, not proof of unchanged2026 interior or operating hours. Not used as distributed texture.'},indent=2))
print(json.dumps(hits,ensure_ascii=True))
