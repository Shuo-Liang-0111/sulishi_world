"""Serve only the review directory on localhost, without exposing the workspace."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import json
ROOT=Path(__file__).resolve().parents[1]
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'web'),**kwargs)
    def end_headers(self):
        self.send_header('Cache-Control','no-cache')
        super().end_headers()
    def log_message(self,fmt,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
record={'url':f'http://127.0.0.1:{server.server_address[1]}/','directory':str(ROOT/'web')}
(ROOT/'runtime/review_server.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record),flush=True)
server.serve_forever()
