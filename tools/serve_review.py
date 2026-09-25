"""Serve H viewer code and read legacy assets without exposing the workspace."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import json
from urllib.parse import unquote, urlsplit
from workspace_paths import ROOT, LEGACY_ROOT, write_path


def resolve_web_path(url):
    decoded = unquote(urlsplit(url).path)
    parts = [p for p in decoded.split('/') if p]
    if any(p.startswith('.') or ':' in p or '\\' in p or '\0' in p for p in parts):
        return None
    relative = Path(*parts) if parts else Path('.')
    candidates = [ROOT/'web'/relative]
    # Only runtime assets and installed browser dependencies fall back to F.
    if LEGACY_ROOT and parts and parts[0] in {'assets','node_modules'}:
        candidates.append(LEGACY_ROOT/'web'/relative)
    for path in candidates:
        base = ROOT/'web' if path.is_relative_to(ROOT) else LEGACY_ROOT/'web'
        if path.exists() and path.resolve().is_relative_to(base.resolve()):
            return path
    return None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'web'),**kwargs)
    def send_head(self):
        if resolve_web_path(self.path) is None:
            self.send_error(404,'File not found')
            return None
        return super().send_head()
    def translate_path(self,path):
        resolved=resolve_web_path(path)
        if resolved is None:raise ValueError('Unvalidated web path')
        return str(resolved)
    def list_directory(self,path):
        self.send_error(403,'Directory listing disabled')
        return None
    def end_headers(self):
        self.send_header('Cache-Control','no-cache')
        super().end_headers()
    def log_message(self,fmt,*args):pass
if __name__ == '__main__':
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    record={'url':f'http://127.0.0.1:{server.server_address[1]}/','directory':str(ROOT/'web'),
            'legacy_assets':str(LEGACY_ROOT/'web/assets') if LEGACY_ROOT else None,
            'viewer_is_latest_native':False}
    write_path('runtime/review_server.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record),flush=True)
    server.serve_forever()
