"""Запустить предусмотренные проверки и связать результаты с хешами исходников."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
FILES = ['tasks.py', 'app.py', 'mail_mcp.py']


def hashes():
    paths = [ROOT/name for name in FILES] + sorted((ROOT/'tests').glob('test_*.py'))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    checks = [
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
        [sys.executable, '-m', 'ruff', 'check', 'tasks.py', 'app.py', 'mail_mcp.py', 'tests'],
        [sys.executable, '-m', 'bandit', '-q', 'tasks.py', 'app.py', 'mail_mcp.py'],
    ]
    before = hashes()
    results = []
    for command in checks:
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)  # nosec B603: фиксированные аргументы без shell
        results.append({'command': ['python', *command[1:]], 'exit_code': run.returncode,
                        'output': run.stdout+run.stderr})
        print(' '.join(results[-1]['command']), '->', run.returncode)
        print(results[-1]['output'])
    passed = all(r['exit_code'] == 0 for r in results) and before == hashes()
    report = {'passed': passed, 'source_hashes': before, 'python': platform.python_version(),
              'platform': platform.platform(), 'checks': results,
              'limits': 'Автоматические проверки; браузер и решение человека о приёмке отдельно.'}
    (ROOT/'.lab').mkdir(exist_ok=True)
    (ROOT/'.lab/checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
