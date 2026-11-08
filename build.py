#!/usr/bin/env python3
"""Автономная сборка Markdown-презентации. Только стандартная библиотека Python."""
from __future__ import annotations
import argparse
import base64
import html
from html.parser import HTMLParser
import mimetypes
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
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


def inline(text):
    pattern = re.compile(r"`([^`]+)`|(!?)\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*")
    pieces, offset = [], 0
    for m in pattern.finditer(text):
        pieces.append(html.escape(text[offset:m.start()]))
        if m[1] is not None:
            pieces.append(f"<code>{html.escape(m[1])}</code>")
        elif m[3] is not None:
            url = m[4]
            scheme = urlsplit(url).scheme
            if scheme and scheme not in ("http", "https", "mailto"):
                raise ValueError(f"Неподдерживаемая ссылка: {url}")
            if m[2] == '!':
                pieces.append(f'<img src="{html.escape(url, quote=True)}" alt="{html.escape(m[3], quote=True)}">')
            else:
                pieces.append(f'<a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(m[3])}</a>')
        else:
            pieces.append(f"<strong>{html.escape(m[5])}</strong>")
        offset = m.end()
    pieces.append(html.escape(text[offset:]))
    return "".join(pieces)


def markdown(text):
    """Поддерживаемые блоки: абзацы, заголовки, списки, таблицы, код, цитаты, HTML."""
    lines, output, i = text.splitlines(), [], 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line == '---' or line.startswith('<!--'):
            i += 1; continue
        if line.startswith('```'):
            language = line[3:].strip(); code = []; i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]); i += 1
            if i == len(lines): raise ValueError("Незакрытый блок кода")
            output.append(f'<pre><code class="language-{html.escape(language)}">{html.escape(chr(10).join(code))}</code></pre>')
            i += 1; continue
        if line.startswith('<'):
            block = []
            while i < len(lines) and lines[i].strip():
                block.append(lines[i]); i += 1
            output.append('\n'.join(block)); continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-{3,}:?', c) for c in cells): rows.append(cells)
                i += 1
            width = len(rows[0])
            if any(len(r) != width for r in rows): raise ValueError("Разное число столбцов в таблице")
            output.append('<table><thead><tr>' + ''.join(f'<th scope="col">{inline(c)}</th>' for c in rows[0]) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in row) + '</tr>' for row in rows[1:]) + '</tbody></table>')
            continue
        if line.startswith('- ') or re.match(r'^\d+\. ', line):
            ordered = bool(re.match(r'^\d+\. ', line))
            prefix = r'^\d+\. ' if ordered else r'^- '
            items = []
            while i < len(lines) and re.match(prefix, lines[i].strip()):
                items.append('<li>' + inline(re.sub(prefix, '', lines[i].strip())) + '</li>'); i += 1
            tag = 'ol' if ordered else 'ul'
            output.append(f'<{tag}>' + ''.join(items) + f'</{tag}>'); continue
        heading = re.match(r'^(#{1,6})\s+(.+)', line)
        if heading:
            level = min(6, len(heading[1])); output.append(f'<h{level}>{inline(heading[2])}</h{level}>'); i += 1; continue
        if line.startswith('> '):
            quote = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote.append(re.sub(r'^> ?', '', lines[i].strip())); i += 1
            output.append('<blockquote>' + markdown('\n'.join(quote)) + '</blockquote>'); continue
        paragraph = [line]; i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#|\||<|```|- |>)', lines[i].strip()):
            paragraph.append(lines[i].strip()); i += 1
        output.append('<p>' + inline(' '.join(paragraph)) + '</p>')
    return '\n'.join(output)


def embed_images(fragment, base):
    def convert(m):
        src = html.unescape(m[2])
        if src.startswith('data:'): return m[0]
        if urlsplit(src).scheme or src.startswith('//'):
            raise ValueError(f"Изображение должно быть локальным: {src}")
        image = (base / unquote(src)).resolve()
        if not image.is_file(): raise ValueError(f"Не найдено изображение: {image}")
        mime = mimetypes.guess_type(image.name)[0] or 'application/octet-stream'
        data = base64.b64encode(image.read_bytes()).decode()
        return f'{m[1]}"data:{mime};base64,{data}"'
    return re.sub(r'(\bsrc=)["\']([^"\']+)["\']', convert, fragment)


class ResourceCheck(HTMLParser):
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a': return
        for key in ('src', 'href', 'srcset', 'poster'):
            value = attrs.get(key, '')
            if value and not value.startswith(('data:', '#')):
                raise ValueError(f"Внешний ресурс в HTML: {tag} {key}={value}")


def rebase_links(fragment, source_dir, output_dir):
    """Сохраняем локальные ссылки при сборке в другой каталог."""
    import os
    def convert(match):
        url = html.unescape(match[1])
        if urlsplit(url).scheme or url.startswith(('#', '//')):
            return match[0]
        path, separator, anchor = url.partition('#')
        target = (source_dir / unquote(path)).resolve()
        if not target.exists():
            raise ValueError(f'Не найдена цель ссылки: {url}')
        relative = Path(os.path.relpath(target, output_dir.resolve())).as_posix()
        return f'href="{html.escape(relative + separator + anchor, quote=True)}"'
    return re.sub(r'href="([^"]+)"', convert, fragment)


def build(source, notes_path, output):
    if output in (source, notes_path, ROOT/'assets/deck.css', ROOT/'assets/deck.js', Path(__file__).resolve()):
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
    for (number, title, body), (_, _, note) in zip(slides, notes):
        layout_match = re.search(r'<!-- layout: ([a-z-]+); time: (\d\d):(\d\d)–(\d\d):(\d\d) -->', body)
        if not layout_match: raise ValueError(f'Слайд {number}: нужны layout и time')
        layout, a, b, c, d = layout_match.groups()
        start, end = int(a)*60+int(b), int(c)*60+int(d)
        if start != previous_end or end <= start: raise ValueError(f'Слайд {number}: разрыв тайминга')
        previous_end = end
        refs = re.findall(r'^Источники: (.+)$', body, re.M)
        for url in re.findall(r'\]\((https?://[^)]+)\)', body):
            if url in seen_urls: raise ValueError(f'Повтор ссылки в слайдах: {url}')
            seen_urls.add(url)
        body = re.sub(r'^Источники: .+$', '', body, flags=re.M)
        rendered_body = rebase_links(embed_images(markdown(body), source.parent), source.parent, output.parent)
        source_html = rebase_links(inline(' · '.join(refs)), source.parent, output.parent)
        rendered.append(f'<section class="slide {layout}" id="slide-{number:02d}" aria-labelledby="title-{number:02d}" data-seconds="{end-start}"><h1 id="title-{number:02d}">{html.escape(title)}</h1><div class="body">{rendered_body}</div><footer class="sources">{source_html}</footer><div class="page">{number:02d}</div></section>')
        note_html = rebase_links(embed_images(markdown(note), notes_path.parent), notes_path.parent, output.parent)
        note_blocks.append(f'<section class="note"><h2>{number:02d}. {html.escape(title)}</h2>{note_html}</section>')
    markup = f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Использование ИИ-агентов для быстрого программирования</title><style>{css}</style></head>
<body><main id="stage" aria-label="Презентация">{''.join(rendered)}</main><aside class="notes-panel" aria-label="Сценарий лектора">{''.join(note_blocks)}</aside><nav id="controls" aria-label="Управление презентацией"><button id="previous" aria-label="Предыдущий слайд">←</button><span id="counter"></span><button id="next" aria-label="Следующий слайд">→</button><button id="toggle-notes" aria-pressed="false">Заметки · N</button><button id="fullscreen" aria-label="Полноэкранный режим">⛶</button></nav><div id="help">← → слайды · N заметки · Home / End</div><div id="live-status" aria-live="polite"></div><script>{js}</script></body></html>'''
    ResourceCheck().feed(markup)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markup, encoding='utf-8')
    print(f'Собрано {len(slides)} слайдов, {previous_end//60}:{previous_end%60:02d} по плану: {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'slides.md')
    parser.add_argument('--notes', type=Path, default=ROOT/'script.md')
    parser.add_argument('--output', type=Path, default=ROOT/'lecture.html')
    args = parser.parse_args()
    try: build(args.source.resolve(), args.notes.resolve(), args.output.resolve())
    except (OSError, ValueError) as error:
        print(f'Ошибка сборки: {error}', file=sys.stderr); return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
