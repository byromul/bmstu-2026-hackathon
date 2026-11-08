"""Локальное приложение для показа функции «отметить выполненной»."""
import argparse
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
from tasks import Store


def page(tasks):
    rows = ''.join(
        '<li><div><small>ID '+str(t['id'])+'</small><h2>'+html.escape(t['title'])+
        '</h2><span>'+('Выполнена' if t['done'] else 'Не выполнена')+'</span></div>'+
        '<button data-id="'+str(t['id'])+'" '+('disabled' if t['done'] else '')+'>'+
        ('Готово' if t['done'] else 'Отметить выполненной')+'</button></li>' for t in tasks
    )
    return '''<!doctype html><html lang="ru"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Задачи · учебное демо</title>
<style>body{margin:60px auto;max-width:1080px;padding:0 32px;background:#fafaf7;color:#17252b;font:26px Arial}
h1{font-size:54px}p,small{color:#59666c}ul{padding:0}li{list-style:none;padding:30px 0;border-top:1px solid #ccd8d3;display:flex;justify-content:space-between;align-items:center;gap:24px}h2{font-size:30px;margin:10px 0}small{font-size:18px}button{padding:18px 24px;border:0;border-radius:8px;background:#17615f;color:white;font-size:22px;cursor:pointer}button:disabled{background:#dde7e1;color:#47645b;cursor:default}#error{color:#a13f2d}footer{margin-top:50px;color:#59666c;font-size:20px}</style>
<h1>Список задач</h1><p>Одна функция: завершить задачу по её ID.</p><ul>'''+rows+'''</ul><p id="error" role="alert"></p>
<footer>Учебный проект · данные сохраняются в локальном JSON · без внешних сервисов</footer>
<script>document.querySelectorAll('button[data-id]').forEach(b=>b.onclick=async()=>{b.disabled=true;try{const r=await fetch('/api/tasks/'+b.dataset.id+'/complete',{method:'POST',headers:{'X-Demo-Action':'complete'}});if(!r.ok)throw Error((await r.json()).error);location.reload()}catch(e){document.querySelector('#error').textContent=e.message;b.disabled=false}});</script></html>'''


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, value, kind='application/json; charset=utf-8'):
            body = value.encode() if isinstance(value, str) else json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == '/':
                self.reply(200, page(store.load()), 'text/html; charset=utf-8')
            elif self.path == '/api/tasks':
                self.reply(200, store.load())
            else:
                self.reply(404, {'error': 'Страница не найдена'})

        def do_POST(self):
            match = re.fullmatch(r'/api/tasks/(\d+)/complete', self.path)
            if not match:
                return self.reply(404, {'error': 'Неизвестное действие'})
            # Пользовательская HTML-форма другого сайта не может поставить этот заголовок.
            if self.headers.get('X-Demo-Action') != 'complete':
                return self.reply(403, {'error': 'Нет заголовка учебного действия'})
            try:
                task = store.complete(int(match[1]))
            except KeyError:
                return self.reply(404, {'error': 'Задача не найдена'})
            except NotImplementedError:
                return self.reply(501, {'error': 'Функция ещё не реализована'})
            self.reply(200, task)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--data', type=Path, default=Path('.lab/tasks.json'))
    args = parser.parse_args()
    server = HTTPServer(('127.0.0.1', args.port), make_handler(Store(args.data)))
    print(f'Задачи: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
