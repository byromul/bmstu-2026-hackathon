"""Учебный комплект из явного списка файлов; без ключей, .lab и сырой истории."""
from io import BytesIO
from pathlib import Path
import re
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
NAME = 'lecture-materials.zip'
PROJECT = 'examples/03-opencode-tasks/'
FILES = tuple(PROJECT + name for name in (
    'README.md', 'SPEC.md', 'PLAN.md', 'AGENTS.md', '.gitignore',
    'app.py', 'tasks.py', 'mail_mcp.py', 'check.py', 'prepare.py',
    'run_agent.py', 'integration_check.py', 'verify_guard.mjs',
    'requirements-lock.txt', 'pyproject.toml',
    'tests/test_tasks.py', 'tests/test_mail.py',
    '.opencode/plugins/guard.js', '.opencode/plugins/package.json',
    '.opencode/skills/review-change/SKILL.md',
)) + (
    'examples/02-token-count/README.md',
    'examples/02-token-count/count.py',
    'examples/02-token-count/result.json',
    'prompts/ART-0035-practice-tasks-v01.md',
)

START = '''# Материалы для первого запуска

Распакуйте архив целиком. Эта папка заменяет корень репозитория лекции в командах ниже.

- [Практический проект](examples/03-opencode-tasks/README.md): начните с установки до самостоятельного повторения, затем подготовьте отдельную рабочую папку. На лекции установка не требуется. В комплекте исходники, тесты, инструкции, skill и защитный плагин.
- [Стартовый промпт](starter-prompt.txt): скопируйте текст и замените поля в квадратных скобках. Это учебный черновик, ещё не испытанный на выбранной модели. Настройте реальные права до реализации.
- [Пара русской и английской инструкций](examples/02-token-count/result.json) и [метод подсчёта](examples/02-token-count/README.md): воспроизведите 52 и 40 токенов. Эти числа относятся только к данной паре входных текстов.

Практика проверялась на macOS; запуск на Windows и чистая установка остаются непроверенными. Для модели нужен собственный ключ Z.ai и доступная квота. Ключей и окружений в архиве нет. Mailpit принимает учебную почту локально, внешней доставки нет.

Состояние ready, которое создаёт prepare.py, содержит заранее подготовленный результат: не считайте его новой работой агента. Применение skill к дефекту и исправному варианту проверяйте отдельно. Сырые журналы подготовки в комплект не включены; их упоминания в инструкции не являются результатом вашего запуска.
'''


def bundle_bytes(root=ROOT):
    root = Path(root).resolve()
    files = {}
    for name in FILES:
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f'Недопустимый путь комплекта: {name}')
        files[name] = path.read_bytes()
    prompt = (root / 'prompts/ART-0011-agent-start-v02.md').read_text()
    match = re.search(r'## Точный текст\s+```text\n(.*?)\n```', prompt, re.S)
    if not match:
        raise ValueError('Не найден полный стартовый промпт')
    files['starter-prompt.txt'] = (match[1] + '\n').encode()
    files['START-HERE.md'] = START.encode()
    files[PROJECT + 'reports/README.md'] = '# Результаты ваших запусков\n\nЗдесь integration_check.py сохранит integration.json. Журналы подготовки лектора в комплект не включены.\n'.encode()
    # Документы подготовки за пределами комплекта не должны давать битые ссылки.
    # Тексты и команды инструкции сохраняются; убирается только недоступная ссылка.
    for name, data in list(files.items()):
        if not name.endswith('.md'):
            continue
        def link(match):
            label, target = match.groups()
            if re.match(r'^[a-zA-Z][\w+.-]*:', target) or target.startswith('#'):
                return match[0]
            resolved = (root / name).parent.joinpath(target.split('#')[0]).resolve()
            if resolved.is_relative_to(root) and resolved.relative_to(root).as_posix() in files:
                return match[0]
            return label
        files[name] = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, data.decode()).encode()
    result = BytesIO()
    with ZipFile(result, 'w', ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = ZipInfo(name, (2026, 11, 8, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    return result.getvalue()


if __name__ == '__main__':
    output = ROOT / NAME
    output.write_bytes(bundle_bytes())
    print(f'Учебный комплект: {output} ({output.stat().st_size} байт)')
