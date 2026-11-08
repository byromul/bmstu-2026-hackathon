"""Клиент проверочного API OpenCode; служебный пароль не печатается."""
import base64
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen


class LabAPI:
    def __init__(self, url, log_path):
        if not re.fullmatch(r'http://127\.0\.0\.1:\d+', url):
            raise ValueError('Только отдельный loopback-сервер учебной проверки')
        self.url = url
        text = Path(log_path).read_text()
        match = re.search(r'server password (\S+)', text)
        if not match:
            raise ValueError('Временный пароль сервера не найден')
        self.authorization = 'Basic '+base64.b64encode(('opencode:'+match[1]).encode()).decode()

    def call(self, path, data=None, method=None):
        if not path.startswith('/api/'):
            raise ValueError('Только пути API')
        headers = {'Authorization': self.authorization, 'Content-Type': 'application/json'}
        request = Request(self.url+path, data=None if data is None else json.dumps(data).encode(),
                          headers=headers, method=method)
        with urlopen(request, timeout=20) as response:  # nosec B310
            payload = response.read()
            return json.loads(payload) if payload else None
