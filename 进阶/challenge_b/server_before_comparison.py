import argparse, importlib, json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT=Path(__file__).parent
DATA=json.loads((ROOT/'data.json').read_text(encoding='utf-8'))
ENGINE=None

class Handler(BaseHTTPRequestHandler):
    def reply(self, status, value, mime='application/json; charset=utf-8'):
        raw=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store')
        self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/': self.reply(200,(ROOT/'index.html').read_bytes(),'text/html; charset=utf-8')
        elif self.path=='/api/cases': self.reply(200,DATA)
        else: self.reply(404,{'error':'not_found'})
    def do_POST(self):
        if self.path!='/api/run': return self.reply(404,{'error':'not_found'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=32768: raise ValueError('invalid_size')
            body=json.loads(self.rfile.read(length))
            case=next(c for c in DATA['cases'] if c['id']==body['case_id'])
            if body.get('reset'): ENGINE.cache.clear()
            self.reply(200,ENGINE.evaluate(case['request'],DATA['corpus'],case['draft']))
        except (ValueError,KeyError,StopIteration,TypeError) as e: self.reply(400,{'error':str(e) or 'invalid_case'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8766)
    p.add_argument('--engine',default='challenge:Engine');a=p.parse_args()
    module,name=a.engine.split(':');ENGINE=getattr(importlib.import_module(module),name)()
    print('Offline replay: http://127.0.0.1:'+str(a.port),flush=True)
    HTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
