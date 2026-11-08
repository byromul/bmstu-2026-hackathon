"""Запуск OpenCode с отдельными настройками; значение ключа не печатается."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--opencode', default='opencode')
    parser.add_argument('--key-file', type=Path, default=Path.home()/'.glm_token')
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    project = args.project.resolve()
    env = {key: os.environ[key] for key in ['PATH', 'TMPDIR', 'LANG', 'SYSTEMROOT', 'COMSPEC', 'PATHEXT'] if key in os.environ}
    base = project/'.lab/opencode-user'
    for kind in ['CONFIG', 'DATA', 'CACHE', 'STATE']:
        env[f'XDG_{kind}_HOME'] = str(base/kind.lower())
    env.update(OPENCODE_DISABLE_CLAUDE_CODE='1', OPENCODE_DISABLE_DEFAULT_PLUGINS='1',
               OPENCODE_DISABLE_AUTOUPDATE='1')
    # Передаётся только дочернему OpenCode; не в аргументах команды и не в JSON проекта.
    if args.key_file.exists():
        key = args.key_file.read_text().strip()
        if not key or '\n' in key:
            raise SystemExit('Нужен файл с одним API-ключом; значение не выводится')
        env['ZAI_API_KEY'] = key
    command = args.arguments
    if command[:1] == ['--']:
        command = command[1:]
    # Не выводите debug config с действующим ключом: он может раскрыть подстановку.
    if command[:2] == ['debug', 'config']:
        env.pop('ZAI_API_KEY', None)
    return subprocess.run([args.opencode, *command], cwd=project, env=env, check=False).returncode  # nosec B603


if __name__ == '__main__':
    raise SystemExit(main())
