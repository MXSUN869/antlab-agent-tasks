from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json, argparse, secrets
from runner import cases, load_config, execute
BASE=Path(__file__).resolve().parents[1]
TOKEN=secrets.token_urlsafe(24)
class Handler(BaseHTTPRequestHandler):
    def reply(self,code,obj):
        raw=json.dumps(obj,ensure_ascii=False).encode();self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if self.path=='/':
            raw=(BASE/'starter/index.html').read_text(encoding='utf-8').replace('__SESSION_TOKEN__',TOKEN).encode()
            self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        elif self.path=='/api/cases':
            self.reply(200,[{'id':c['id'],'split':c['split'],'question':c['question']} for c in cases()])
        else:self.reply(404,{'error':'not found'})
    def do_POST(self):
        if self.path!='/api/run':return self.reply(404,{'error':'not found'})
        if self.headers.get('X-Assessment-Session')!=TOKEN:return self.reply(403,{'error':'会话不匹配'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<20000:raise ValueError('请求长度不合法')
            obj=json.loads(self.rfile.read(n))
            mode=obj.get('mode','dry')
            if mode not in ('dry','mock','paid'):raise ValueError('未知模式')
            if mode=='paid' and not self.server.allow_paid:raise ValueError('服务未启用--allow-paid')
            r=execute(obj['case_id'],obj['condition'],obj['variant'],self.server.config,
                      mock=mode=='mock',dry=mode=='dry')
            self.reply(200,r)
        except (ValueError,KeyError,TypeError,NotImplementedError) as e:self.reply(400,{'error':str(e)})
        except Exception as e:self.reply(500,{'error':type(e).__name__,'detail':'请检查服务端与输入，不将此结果当实验成功'})
    def log_message(self,*args):pass
def main():
    p=argparse.ArgumentParser();p.add_argument('--config',default=str(BASE/'config.example.json'))
    p.add_argument('--port',type=int,default=8765);p.add_argument('--allow-paid',action='store_true');a=p.parse_args()
    s=ThreadingHTTPServer(('127.0.0.1',a.port),Handler);s.config=load_config(a.config);s.allow_paid=a.allow_paid
    print(f'http://127.0.0.1:{a.port}  paid={a.allow_paid}',flush=True)
    try:s.serve_forever()
    except KeyboardInterrupt:pass
    finally:s.server_close()
if __name__=='__main__':main()
