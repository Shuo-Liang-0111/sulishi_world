"""Register files ready for review without promoting unobserved realtime output."""
from pathlib import Path
import json,urllib.request,datetime,argparse,re
parser=argparse.ArgumentParser();parser.add_argument('--version',required=True);args=parser.parse_args();V=args.version
assert re.fullmatch(r'G1_\d{3}(?:r\d+)?',V)
R=Path(__file__).resolve().parents[1];E=R/'evidence'/V;assets=R/'web/assets'
w=json.loads((R/'runtime/station_road_working.json').read_text());qa=json.loads((E/'roundtrip.json').read_text());encoding=json.loads((E/'runtime_encoding.json').read_text());meta=json.loads((assets/f'{V}_bellevue.json').read_text())
assert w['version']==qa['version']==encoding['version']==meta['version']==V
assert qa['native_reopen_verified'] and encoding['written_file_checked'] and qa['identities_verified']==meta['exported_authored_objects']
assert (assets/f'{V}_sky.hdr').is_file()
native_review=json.loads((E/'native_visual_review.json').read_text());assert native_review['version']==V and native_review['images_actually_inspected']
preview=json.loads((assets/'station_preview.json').read_text());preview.update(version=V,construction_version=V,quality='construction_candidate_native_reviewed_runtime_unverified',accepted=False)
(assets/'station_preview.json').write_text(json.dumps(preview,indent=2))
url=json.loads((R/'runtime/review_server.json').read_text())['url'];opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));checks=[]
for name in [meta['authored_runtime']['file'],*([meta['authored_runtime']['geometry_file']] if 'geometry_file' in meta['authored_runtime'] else []),f'{V}_context_patch.glb',f'{V}_bellevue.json',f'{V}_sky.hdr','station_preview.json']:
 try:
  with opener.open(urllib.request.Request(url+'assets/'+name,method='HEAD'),timeout=8) as r:checks.append({'file':name,'status':r.status,'length':int(r.headers.get('Content-Length',0))})
 except Exception as e:checks.append({'file':name,'error':str(e)})
(E/'http_ready.json').write_text(json.dumps({'version':V,'url':url+'?preview=station','checks':checks,'not_a_visual_or_runtime_acceptance':True},indent=2))
(E/'runtime_review.json').write_text(json.dumps({'version':V,'loading_verified':False,'candidate_can_replace_default':False,'reason':'Files registered for realtime review; visual rendering and actual use have not yet been verified for this candidate.','default_preserved':'G1_007r5','accepted':False},indent=2))
print(json.dumps({'version':V,'preview':url+'?preview=station','http_ready':all(x.get('status')==200 for x in checks),'default_unchanged':'G1_007r5','runtime_visual_review':False}))
