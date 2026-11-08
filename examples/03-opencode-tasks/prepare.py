"""Собрать отдельный учебный репозиторий; существующий каталог не перезаписывать."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
START = '''def complete_task(tasks, task_id):
    """Завершение ещё предстоит реализовать агенту."""
    raise NotImplementedError('Реализуйте по SPEC.md')
'''
BUG = '''def complete_task(tasks, task_id):
    """Намеренный дефект: ID подставлен как индекс."""
    tasks[task_id]['done'] = True
    return tasks[task_id]
'''


def config(python):
    return {'$schema': 'https://opencode.ai/config.json',
            'model': 'lecture-glm/glm-4.7-flash', 'small_model': 'lecture-glm/glm-4.7-flash',
            'provider': {'lecture-glm': {'npm': '@ai-sdk/openai-compatible', 'name': 'Z.ai — учебный API',
                'options': {'baseURL': 'https://api.z.ai/api/paas/v4', 'apiKey': '{env:ZAI_API_KEY}'},
                'models': {'glm-4.7-flash': {'name': 'GLM-4.7-Flash', 'tool_call': True,
                    'limit': {'context': 200000, 'output': 4096},
                    'options': {'thinking': {'type': 'disabled'}}}}}},
            'share': 'disabled', 'autoupdate': False,
            'plugin': ['./.opencode/plugins/guard.mjs'],
            'permission': {
                '*': 'deny', 'read': 'allow', 'glob': 'allow', 'grep': 'allow', 'list': 'allow',
                'edit': {'*': 'allow', '.opencode/*': 'deny', '*/.opencode/*': 'deny',
                         'check.py': 'deny', 'mail_mcp.py': 'deny', 'tests/*': 'deny'},
                'bash': {'*': 'ask', 'git status*': 'allow', 'git diff*': 'allow',
                         'python check.py': 'allow', 'python -m unittest*': 'allow',
                         'git push*': 'deny', 'git * push*': 'deny'},
                'skill': {'review-change': 'allow'}, 'external_directory': 'deny',
                'mail_prepare_report': 'allow', 'mail_list_inbox': 'allow', 'mail_send_report': 'ask'},
            'mcp': {'mail': {'type': 'local', 'command': [str(python), 'mail_mcp.py'],
                             'enabled': True, 'timeout': 15000, 'environment': {'ZAI_API_KEY': ''}}}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--state', choices=['start', 'bug', 'ready'], default='start')
    args = parser.parse_args()
    dest = args.destination.resolve()
    if dest.exists():
        raise SystemExit('Каталог уже существует: выберите новый, существующий не удаляется')
    dest.mkdir(parents=True)
    names = ['tasks.py', 'app.py', 'mail_mcp.py', 'check.py', 'pyproject.toml', 'requirements-lock.txt',
             'SPEC.md', 'PLAN.md', 'AGENTS.md', '.gitignore', 'tests', '.opencode']
    for name in names:
        src = ROOT/name
        if src.is_dir():
            shutil.copytree(src, dest/name, ignore=shutil.ignore_patterns('__pycache__', 'node_modules'))
        else:
            shutil.copy2(src, dest/name)
    if args.state != 'ready':
        path = dest/'tasks.py'
        text = path.read_text()
        a = text.index('def complete_task(')
        b = text.index('\n\nclass Store:', a)
        path.write_text(text[:a]+(START if args.state == 'start' else BUG)+text[b:])
    (dest/'opencode.json').write_text(json.dumps(config(sys.executable), ensure_ascii=False, indent=2)+'\n')
    for cmd in [['git', 'init', '-q'], ['git', 'add', '.'],
                ['git', '-c', 'user.name=Lecture Demo', '-c', 'user.email=demo@example.test',
                 'commit', '-qm', 'Исходное состояние учебного проекта']]:
        subprocess.run(cmd, cwd=dest, check=True)  # nosec B603
    print(f'Учебный репозиторий: {dest}\nСостояние: {args.state}\nOpenCode: 1.14.48, формат V1')
    print('Начальная версия сохранена локально; внешнего remote нет.')


if __name__ == '__main__':
    main()
