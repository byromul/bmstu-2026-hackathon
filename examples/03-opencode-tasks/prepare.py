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
    def rule(action, resource, effect):
        return {'action': action, 'resource': resource, 'effect': effect}
    permissions = [rule('*', '*', 'deny')]
    permissions += [rule(action, '*', 'allow') for action in ['read', 'glob', 'grep', 'list']]
    permissions += [rule('edit', pattern, 'allow') for pattern in ['tasks.py', '*/tasks.py', 'review.md', '*/review.md']]
    permissions += [rule('shell', '*', 'ask')]
    permissions += [rule('shell', command, 'allow') for command in ['git status *', 'git diff *', 'python check.py', 'python -m unittest *']]
    permissions += [rule('shell', command, 'deny') for command in ['git push *', 'git * push *']]
    permissions += [rule('skill', 'review-change', 'allow'), rule('external_directory', '*', 'deny'),
                    rule('mail_prepare_report', '*', 'allow'), rule('mail_list_inbox', '*', 'allow'),
                    rule('mail_send_report', '*', 'ask')]
    return {'$schema': 'https://opencode.ai/config.json',
            'model': 'lecture-glm/glm-4.5-flash', 'small_model': 'lecture-glm/glm-4.5-flash',
            'providers': {'lecture-glm': {'package': '@opencode/ai/providers/openai-compatible',
                'name': 'Z.ai — учебный API', 'env': ['ZAI_API_KEY'],
                'settings': {'baseURL': 'https://api.z.ai/api/paas/v4', 'apiKey': '{env:ZAI_API_KEY}'},
                'models': {'glm-4.5-flash': {'name': 'GLM-4.5-Flash',
                    'limit': {'context': 128000, 'output': 4096},
                    'settings': {'thinking': {'type': 'disabled'}}}}}},
            'permissions': permissions,
            'mcp': {'servers': {'mail': {'type': 'local', 'command': [str(python), 'mail_mcp.py'],
                'environment': {'ZAI_API_KEY': ''}, 'codemode': False, 'timeout': 15000}}}}


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
    print(f'Учебный репозиторий: {dest}\nСостояние: {args.state}\nOpenCode: 2.2.6, формат V2')
    print('Начальная версия сохранена локально; внешнего remote нет.')


if __name__ == '__main__':
    main()
