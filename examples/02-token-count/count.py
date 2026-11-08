"""Локальный подсчёт текста; модель и API не вызываются."""
import hashlib
import json
from pathlib import Path
import platform
from importlib.metadata import version
import tiktoken

HERE = Path(__file__).resolve().parent
TEXTS = {
    'ru': 'Добавь в Python-проект импорт оценок из CSV. Меняй только модуль импорта и его тесты. Не добавляй зависимости. Пустой файл должен вызывать понятную ошибку. Запусти проверки и покажи результаты.',
    'en': 'Add CSV grade import to the Python project. Change only the import module and its tests. Do not add dependencies. An empty file must produce a clear error. Run the checks and show the results.',
}

def measure():
    encoding = tiktoken.encoding_for_model('gpt-4o')
    return {
        'date': '2026-11-08', 'model_for_tokenizer': 'gpt-4o',
        'encoding': encoding.name, 'tiktoken': version('tiktoken'),
        'python': platform.python_version(), 'platform': platform.platform(),
        'method': 'encode_ordinary; text only; no chat envelope, API or model execution',
        'texts': {lang: {'text': text, 'sha256': hashlib.sha256(text.encode()).hexdigest(),
                         'tokens': len(encoding.encode_ordinary(text))}
                  for lang, text in TEXTS.items()},
    }

if __name__ == '__main__':
    result = measure()
    (HERE/'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
