"""Фактические HTTP и MCP → SMTP → входящие Mailpit. Без вызова языковой модели."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent


def request(url, method='GET'):
    req = Request(url, method=method, headers={'X-Demo-Action': 'complete'})
    with urlopen(req, timeout=3) as response:  # nosec B310
        return json.load(response)


def wait_ready(url):
    for _ in range(60):
        try:
            request(url)
            return
        except (OSError, URLError):
            time.sleep(.1)
    raise RuntimeError('Локальный сервер не запустился')


def value(result):
    if result.isError:
        raise RuntimeError(str(result.content))
    return result.structuredContent or json.loads(result.content[0].text)


async def mail_check():
    parameters = StdioServerParameters(command=sys.executable, args=['mail_mcp.py'], cwd=str(ROOT))
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            before = value(await session.call_tool('list_inbox'))
            draft = value(await session.call_tool('prepare_report'))
            assert draft['to'] == 'boss@example.test'
            assert len(value(await session.call_tool('list_inbox'))['messages']) == len(before['messages'])
            first = value(await session.call_tool('send_report', {'draft_id': draft['id'], 'confirmation': 'Отправить Боссу'}))
            repeat = value(await session.call_tool('send_report', {'draft_id': draft['id'], 'confirmation': 'Отправить Боссу'}))
            after = value(await session.call_tool('list_inbox'))
            assert first['status'] == 'received_locally'
            assert repeat['status'] == 'already_received_locally'
            assert len(after['messages']) == len(before['messages'])+1
            return {'tools': [t.name for t in tools.tools], 'recipient': draft['to'],
                    'draft_did_not_send': True, 'first': first, 'repeat': repeat,
                    'inbox_count_increase': 1, 'transport': 'MCP stdio → SMTP 127.0.0.1:1025 → Mailpit HTTP inbox',
                    'model_used': False, 'external_delivery': False}


def main():
    binary = os.environ.get('MAILPIT_BIN', 'mailpit')
    report = {'date': '2026-11-08', 'checks': {}}
    processes = []
    with tempfile.TemporaryDirectory(prefix='lecture-integration-') as tmp:
        tmp = Path(tmp)
        with (tmp/'services.log').open('w') as log:
            try:
                mail = subprocess.Popen([binary, '--listen', '127.0.0.1:8025', '--smtp', '127.0.0.1:1025',
                    '--database', str(tmp/'mail.db'), '--disable-version-check', '--smtp-disable-rdns',
                    '--ignore-duplicate-ids', '--smtp-allowed-recipients', r'^boss@example\.test$',
                    '--allowed-hosts', '127.0.0.1,localhost'], stdout=log, stderr=log,
                    env={k: os.environ[k] for k in ['PATH', 'TMPDIR'] if k in os.environ})  # nosec B603
                processes.append(mail)
                wait_ready('http://127.0.0.1:8025/api/v1/messages')
                app = subprocess.Popen([sys.executable, 'app.py', '--port', '18080', '--data', str(tmp/'tasks.json')], cwd=ROOT, stdout=log, stderr=log)  # nosec B603
                processes.append(app)
                wait_ready('http://127.0.0.1:18080/api/tasks')
                initial = request('http://127.0.0.1:18080/api/tasks')
                request('http://127.0.0.1:18080/api/tasks/1/complete', 'POST')
                result = request('http://127.0.0.1:18080/api/tasks')
                assert [t['done'] for t in initial] == [False, False]
                assert [t['done'] for t in result] == [True, False]
                request('http://127.0.0.1:18080/api/tasks/1/complete', 'POST')
                try:
                    request('http://127.0.0.1:18080/api/tasks/999/complete', 'POST')
                    raise AssertionError('Ожидался 404')
                except HTTPError as error:
                    assert error.code == 404
                assert request('http://127.0.0.1:18080/api/tasks') == result
                app.terminate(); app.wait(timeout=5)
                app = subprocess.Popen([sys.executable, 'app.py', '--port', '18080', '--data', str(tmp/'tasks.json')], cwd=ROOT, stdout=log, stderr=log)  # nosec B603
                processes.append(app)
                wait_ready('http://127.0.0.1:18080/api/tasks')
                assert request('http://127.0.0.1:18080/api/tasks') == result
                report['checks']['http'] = {'id_1_done': True, 'id_2_unchanged': True, 'unknown_404': True,
                                           'repeat_safe': True, 'persisted_after_restart': True}
                report['checks']['mail'] = asyncio.run(mail_check())
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=5)
                log.flush()
                report['service_log'] = (tmp/'services.log').read_text()
    (ROOT/'reports/integration.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
