#!/usr/bin/env python3
"""Автономная сборка Markdown-презентации. Только стандартная библиотека Python."""
from __future__ import annotations
import argparse
import base64
import html
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'assets'))
import render_elements as elements
import package_materials
REGISTRY = ROOT / 'ARTIFACTS.md'
SLIDE = re.compile(r"^## Слайд (\d{2,})\. (.+)$", re.M)


def sections(text):
    matches = list(SLIDE.finditer(text))
    result = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[match.end():end]
        # Не включаем каркасы следующего блока и служебные разделы.
        body = re.split(r"^## (?!Слайд )", body, maxsplit=1, flags=re.M)[0]
        body = re.sub(r"\n---\s*$", "", body).strip()
        result.append((int(match[1]), match[2], body))
    if not result:
        raise ValueError("Не найдены заголовки '## Слайд NN. Название'")
    numbers = [number for number, _, _ in result]
    if numbers != list(range(1, len(numbers) + 1)):
        raise ValueError("Номера слайдов должны идти подряд, начиная с 01")
    return result


def inline(text, registry=REGISTRY):
    pattern = re.compile(r"`([^`]+)`|(!?)\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*")
    pieces, offset = [], 0
    for m in pattern.finditer(text):
        pieces.append(html.escape(text[offset:m.start()]))
        if m[1] is not None:
            pieces.append(f"<code>{html.escape(m[1])}</code>")
        elif m[3] is not None:
            url = m[4]
            scheme = urlsplit(url).scheme
            if m[2] == '!':
                if not url.startswith('artifact:'):
                    raise ValueError('Изображение должно ссылаться на artifact:ART-NNNN')
                pieces.append(elements.artifact_image(url.removeprefix('artifact:'), registry, m[3]))
            elif url == package_materials.NAME:
                data = base64.b64encode(package_materials.bundle_bytes()).decode('ascii')
                pieces.append(f'<a href="data:application/zip;base64,{data}" download="{package_materials.NAME}">{html.escape(m[3])}</a>')
            elif scheme in ('http', 'https', 'mailto'):
                pieces.append(f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(m[3])}</a>')
            elif url.startswith('#'):
                pieces.append(f'<a href="{html.escape(url, quote=True)}">{html.escape(m[3])}</a>')
            elif not scheme and not url.startswith('//'):
                # Ссылки для редактора остаются текстом в переносимом HTML.
                pieces.append(html.escape(m[3]))
            else:
                raise ValueError(f'Неподдерживаемая ссылка: {url}')
        else:
            pieces.append(f"<strong>{html.escape(m[5])}</strong>")
        offset = m.end()
    pieces.append(html.escape(text[offset:]))
    return "".join(pieces)


def markdown(text, registry=REGISTRY):
    """Поддерживаемые блоки: абзацы, заголовки, списки, таблицы, код, цитаты, смысловые JSON-блоки."""
    lines, output, i = text.splitlines(), [], 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line == '---':
            i += 1; continue
        if line.startswith('```'):
            language = line[3:].strip(); code = []; i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]); i += 1
            if i == len(lines): raise ValueError("Незакрытый блок кода")
            if language in {'diagram', 'table', 'image', 'logos', 'callout', 'cover', 'result', 'caption'}:
                output.append(elements.render(language, '\n'.join(code), registry))
            elif language == 'mermaid':
                raise ValueError('Mermaid не подключён: используйте diagram или подготовленный артефакт изображения')
            else:
                output.append(f'<pre><code class="language-{html.escape(language)}">{html.escape(chr(10).join(code))}</code></pre>')
            i += 1; continue
        if re.search(r'<[!/?a-zA-Z][^>]*>', line):
            raise ValueError('HTML в Markdown запрещён; используйте смысловые блоки')
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-{3,}:?', c) for c in cells): rows.append(cells)
                i += 1
            width = len(rows[0])
            if any(len(r) != width for r in rows): raise ValueError("Разное число столбцов в таблице")
            output.append('<table><thead><tr>' + ''.join(f'<th scope="col">{inline(c, registry)}</th>' for c in rows[0]) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{inline(c, registry)}</td>' for c in row) + '</tr>' for row in rows[1:]) + '</tbody></table>')
            continue
        if line.startswith('- ') or re.match(r'^\d+\. ', line):
            ordered = bool(re.match(r'^\d+\. ', line))
            prefix = r'^\d+\. ' if ordered else r'^- '
            items = []
            while i < len(lines) and re.match(prefix, lines[i].strip()):
                items.append('<li>' + inline(re.sub(prefix, '', lines[i].strip()), registry) + '</li>'); i += 1
            tag = 'ol' if ordered else 'ul'
            output.append(f'<{tag}>' + ''.join(items) + f'</{tag}>'); continue
        heading = re.match(r'^(#{1,6})\s+(.+)', line)
        if heading:
            level = min(6, len(heading[1])); output.append(f'<h{level}>{inline(heading[2], registry)}</h{level}>'); i += 1; continue
        if line.startswith('> '):
            quote = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote.append(re.sub(r'^> ?', '', lines[i].strip())); i += 1
            output.append('<blockquote>' + markdown('\n'.join(quote), registry) + '</blockquote>'); continue
        paragraph = [line]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#|\||<|```|- |>)', lines[i].strip()):
            paragraph.append(lines[i].strip()); i += 1
        output.append('<p>' + inline(' '.join(paragraph), registry) + '</p>')
    return '\n'.join(output)


class ResourceCheck(HTMLParser):
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a':
            href = attrs.get('href', '')
            if attrs.get('download') == package_materials.NAME and re.fullmatch(r'data:application/zip;base64,[A-Za-z0-9+/]+={0,2}', href):
                return
            if href and not href.startswith(('#', 'https://', 'http://', 'mailto:')):
                raise ValueError(f'Локальная ссылка в HTML: {href}')
            return
        for key in ('src', 'href', 'srcset', 'poster'):
            value = attrs.get(key, '')
            if value and not value.startswith(('data:', '#')):
                raise ValueError(f"Внешний ресурс в HTML: {tag} {key}={value}")


def build(source, notes_path, output, registry=REGISTRY, selected_block=None):
    if output in (source, notes_path, ROOT/'assets/deck.css', ROOT/'assets/deck.js', ROOT/'assets/render_elements.py', registry, Path(__file__).resolve()):
        raise ValueError('Результат сборки не должен перезаписывать исходники')
    slides = sections(source.read_text(encoding='utf-8'))
    notes = sections(notes_path.read_text(encoding='utf-8'))
    if [(n, t) for n, t, _ in slides] != [(n, t) for n, t, _ in notes]:
        raise ValueError('Номера и названия слайдов и сценария различаются')
    css = (ROOT / 'assets/deck.css').read_text(encoding='utf-8')
    js = (ROOT / 'assets/deck.js').read_text(encoding='utf-8')
    if re.search(r'@import|url\(', css, re.I):
        raise ValueError('CSS должен быть автономным: @import и url() запрещены')
    seen_urls = set(); rendered = []; note_blocks = []
    previous_end = 0
    previous_block = 1
    total_seconds = 0
    rendered_count = 0
    for (number, title, body), (_, _, note) in zip(slides, notes):
        meta_match = re.search(r'^```slide\n(.*?)\n```', body, re.M | re.S)
        if not meta_match:
            raise ValueError(f'Слайд {number}: нужен блок slide с layout и time')
        meta = elements.object_data(meta_match[1])
        elements.check_fields(meta, {'layout', 'time', 'footer_note', 'block'}, {'layout', 'time'})
        block_number = meta.get('block', 1)
        if type(block_number) is not int or block_number not in (1, 2):
            raise ValueError('block: допустимы 1 и 2')
        if block_number != previous_block:
            if block_number != previous_block + 1:
                raise ValueError('Блоки должны идти по порядку')
            previous_end = 0
            previous_block = block_number
        layout = meta['layout']
        if not re.fullmatch(r'[a-z-]+', layout):
            raise ValueError('Некорректное имя layout')
        timing = re.fullmatch(r'(\d{2}):([0-5]\d)–(\d{2}):([0-5]\d)', meta['time'])
        if not timing:
            raise ValueError(f'Слайд {number}: неверный формат тайминга')
        a, b, c, d = map(int, timing.groups())
        start, end = a*60+b, c*60+d
        if start != previous_end or end <= start:
            raise ValueError(f'Слайд {number}: разрыв тайминга')
        body = body[:meta_match.start()] + body[meta_match.end():]
        previous_end = end
        if selected_block is not None and block_number != selected_block:
            continue
        total_seconds += end-start
        rendered_count += 1
        refs = re.findall(r'^Источники: (.+)$', body, re.M)
        for url in re.findall(r'\]\((https?://[^)]+)\)', body):
            if url in seen_urls: raise ValueError(f'Повтор ссылки в слайдах: {url}')
            seen_urls.add(url)
        body = re.sub(r'^Источники: .+$', '', body, flags=re.M)
        rendered_body = markdown(body, registry)
        source_html = inline(' · '.join(refs), registry)
        if meta.get('footer_note'):
            source_html = f'<span class="footer-note">{html.escape(meta["footer_note"])}</span>' + source_html
        rendered.append(f'<section class="slide {layout}" id="slide-{number:02d}" aria-labelledby="title-{number:02d}" data-block="{block_number}" data-seconds="{end-start}"><h1 id="title-{number:02d}">{html.escape(title)}</h1><div class="body">{rendered_body}</div><footer class="sources">{source_html}</footer><div class="page">{number:02d}</div></section>')
        note_html = markdown(note, registry)
        note_blocks.append(f'<section class="note"><h2>{number:02d}. {html.escape(title)}</h2>{note_html}</section>')
    if not rendered_count:
        raise ValueError('В выбранном блоке нет слайдов')
    markup = f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Использование ИИ-агентов для быстрого программирования</title><style>{css}</style></head>
<body><main id="stage" aria-label="Презентация">{''.join(rendered)}</main><aside class="notes-panel" aria-label="Сценарий лектора">{''.join(note_blocks)}</aside><nav id="controls" aria-label="Управление презентацией"><button id="previous" aria-label="Предыдущий слайд">←</button><span id="counter"></span><button id="next" aria-label="Следующий слайд">→</button><button id="fullscreen" aria-label="Полноэкранный режим">⛶</button></nav><div id="live-status" aria-live="polite"></div><script>{js}</script></body></html>'''
    ResourceCheck().feed(markup)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markup, encoding='utf-8')
    print(f'Собрано {rendered_count} слайдов, {total_seconds//60}:{total_seconds%60:02d} по плану: {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'slides.md')
    parser.add_argument('--notes', type=Path, default=ROOT/'script.md')
    parser.add_argument('--artifacts', type=Path, default=REGISTRY)
    parser.add_argument('--output', type=Path, default=ROOT/'lecture.html')
    parser.add_argument('--block', type=int, choices=(1, 2), help='Собрать один самостоятельный блок')
    args = parser.parse_args()
    try: build(args.source.resolve(), args.notes.resolve(), args.output.resolve(), args.artifacts.resolve(), args.block)
    except (OSError, ValueError) as error:
        print(f'Ошибка сборки: {error}', file=sys.stderr); return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
