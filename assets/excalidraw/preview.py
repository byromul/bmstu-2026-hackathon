#!/usr/bin/env python3
"""Собрать пробный слайд из разделов slides.md и script.md штатным конвертором."""
from pathlib import Path
import json
import re
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import build

heading='## Проба визуализации. Агентский цикл'
content=(ROOT/'slides.md').read_text(encoding='utf-8').split(heading,1)[1]
notes=(ROOT/'script.md').read_text(encoding='utf-8').split(heading,1)[1]
match=re.search(r'```diagram\n(.*?)\n```',content,re.S)
if not match:
    raise SystemExit('Не найден diagram в разделе пробы')
claim=re.search(r'^Ключевой вывод: (.+)$',content,re.M)[1]
meta={'layout':'agent-loop','time':'00:00–01:00','footer_note':'Проба оформления в Excalidraw'}
callout={'text':claim[0].upper()+claim[1:],'tone':'key'}
with tempfile.TemporaryDirectory(prefix='excalidraw-slide-') as folder:
    source=Path(folder)/'slides.md'; script=Path(folder)/'script.md'
    source.write_text('## Слайд 01. Агентский цикл\n\n```slide\n'+json.dumps(meta,ensure_ascii=False)+'\n```\n\n'+match[0]+'\n\n```callout\n'+json.dumps(callout,ensure_ascii=False)+'\n```\n',encoding='utf-8')
    script.write_text('## Слайд 01. Агентский цикл\n'+notes,encoding='utf-8')
    build.build(source,script,Path(__file__).with_name('preview.html'))
