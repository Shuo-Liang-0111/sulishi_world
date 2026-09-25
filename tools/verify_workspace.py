"""Verify real read fallback, H writes, source syntax and loopback serving."""
from pathlib import Path
import ast
import hashlib
import http.client
import json
import os
import shutil
import threading
import uuid
from workspace_paths import ROOT, LEGACY_ROOT, CONFIG, read_path, write_path, validate_native
from serve_review import Handler, ThreadingHTTPServer

assert ROOT != LEGACY_ROOT
assert Path.cwd().resolve()==ROOT, 'Run through tools/python.ps1 from the active workspace.'
assert Path(os.environ['TEMP']).resolve().is_relative_to(ROOT)
syntax=[]
for path in sorted((ROOT/'tools').glob('*.py')):
    ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    syntax.append(path.name)
native=validate_native(CONFIG['working_native'])
with native.open('rb') as stream:native_hash=hashlib.file_digest(stream,'sha256').hexdigest()
checkpoint=json.loads(read_path('evidence/G1_027r2/checkpoint.json').read_text())
assert native_hash==checkpoint['native_sha256']
assert read_path('derived/bellevue/bridge_grade/027r2_refined_patch.npz').is_relative_to(LEGACY_ROOT)

name=f'runtime/migration/probe-{uuid.uuid4().hex}.bin'
probe=write_path(name)
data=os.urandom(512*1024)
try:
    with probe.open('xb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    assert probe.read_bytes()==data
    assert read_path(name)==probe
    assert not (LEGACY_ROOT/name).exists()
finally:
    if probe.is_file():probe.unlink()
for invalid in ['../outside.txt',ROOT.parent/'outside.txt']:
    try:write_path(invalid)
    except ValueError:pass
    else:raise AssertionError(f'Unsafe output accepted: {invalid}')

server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
checks=[]
try:
    targets=[('/',ROOT/'web/index.html'),('/viewer.js',ROOT/'web/viewer.js'),
             ('/node_modules/three/build/three.module.js',LEGACY_ROOT/'web/node_modules/three/build/three.module.js')]
    metadata=next(p for p in sorted((LEGACY_ROOT/'web/assets').glob('*.json')) if p.stat().st_size<1024*1024)
    targets.append(('/assets/'+metadata.name,metadata))
    for url,path in targets:
        connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=30)
        connection.request('GET',url);response=connection.getresponse();payload=response.read()
        assert response.status==200,(url,response.status)
        assert payload==path.read_bytes(),url
        checks.append({'url':url,'status':response.status,'source':str(path),'bytes':len(payload)})
        connection.close()
    for url in ['/../workspace.local.json','/%2e%2e/workspace.local.json','/assets/../../workspace.local.json','/.git/config','/assets/']:
        connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=30)
        connection.request('GET',url);response=connection.getresponse();response.read()
        assert response.status in (403,404),(url,response.status)
        checks.append({'url':url,'status':response.status});connection.close()
finally:
    server.shutdown();server.server_close();thread.join(timeout=5)

report={'workspace':str(ROOT),'legacy_asset_root':str(LEGACY_ROOT),'syntax_files':len(syntax),
        'write_roundtrip_bytes':len(data),'write_roundtrip_verified':True,'source_native_sha256':native_hash,
        'http_checks':checks,'disk_free':{str(p):shutil.disk_usage(p).free for p in (ROOT,LEGACY_ROOT)},
        'assets_copied':False,'scene_visual_acceptance':False}
write_path('runtime/migration/workspace_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
