"""Отрисовка смысловых блоков. Только стандартная библиотека; дизайн отделён от Markdown."""
import base64
import html
import json
import mimetypes
import re
from urllib.parse import unquote, urlsplit


def esc(value):
    return html.escape(str(value), quote=True)


def object_data(raw):
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f'Некорректный JSON блока: {error}') from error
    if not isinstance(data, dict):
        raise ValueError('Блок должен содержать JSON-объект')
    return data


def check_fields(data, allowed, required=()):
    unknown = set(data) - set(allowed) - {'author'}
    if unknown:
        raise ValueError(f'Неизвестные поля блока: {sorted(unknown)}')
    missing = set(required) - set(data)
    if missing:
        raise ValueError(f'Не заданы поля блока: {sorted(missing)}')
    if 'author' in data and not isinstance(data['author'], (str, dict)):
        raise ValueError('author: нужна строка или объект с пожеланиями автора')


def artifact_image(artifact_id, registry, alt, fit='contain'):
    """ID -> строка реестра -> локальная картинка и сохранённый промпт."""
    if not re.fullmatch(r'ART-\d{4}', artifact_id):
        raise ValueError(f'Некорректный ID изображения: {artifact_id}')
    if fit not in ('contain', 'cover'):
        raise ValueError('fit должен быть contain или cover')
    if not alt.strip():
        raise ValueError('Изображению нужно непустое описание alt')
    rows = [line for line in registry.read_text(encoding='utf-8').splitlines()
            if re.match(rf'^\|\s*{artifact_id}\s*\|', line)]
    if len(rows) != 1:
        raise ValueError(f'{artifact_id}: нужна одна запись в {registry.name}')
    cells = [cell.strip() for cell in rows[0].strip('|').split('|')]
    if len(cells) != 6:
        raise ValueError(f'{artifact_id}: неверный формат строки реестра')
    def paths(cell):
        result = []
        for url in re.findall(r'\]\(([^)]+)\)', cell):
            parts = urlsplit(url)
            if parts.scheme or parts.netloc:
                continue
            result.append((registry.parent / unquote(parts.path)).resolve())
        return result
    prompts = paths(cells[1])
    if not prompts or not all(p.is_file() for p in prompts):
        raise ValueError(f'{artifact_id}: нет локального сохранённого промпта')
    images = [p for p in paths(cells[2]) if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.svg')]
    if len(images) != 1 or not images[0].is_file():
        raise ValueError(f'{artifact_id}: нужна одна существующая картинка')
    mime = mimetypes.guess_type(images[0].name)[0]
    if images[0].suffix.lower() == '.svg':
        svg = images[0].read_text(encoding='utf-8')
        if re.search(r'<script|<foreignObject|\bon\w+\s*=|(?:href|src)\s*=\s*[\"\'](?!#|data:)|@import|url\(\s*(?!#)', svg, re.I):
            raise ValueError(f'{artifact_id}: SVG содержит внешние или активные ресурсы')
    uri = f'data:{mime};base64,' + base64.b64encode(images[0].read_bytes()).decode()
    return f'<img data-artifact="{artifact_id}" class="artifact-image fit-{fit}" src="{uri}" alt="{esc(alt)}">'


def flow(nodes):
    if not isinstance(nodes, list) or not nodes:
        raise ValueError('Нужен непустой список nodes')
    pieces = []
    for node in nodes:
        check_fields(node, {'text', 'accent'}, {'text'})
        tag = 'strong' if node.get('accent') else 'span'
        pieces.append(f'<{tag}>{esc(node["text"])}</{tag}>')
    return '<div class="flow">' + '<i aria-hidden="true">→</i>'.join(pieces) + '</div>'


def diagram(data):
    kind = data.get('kind')
    common = {'kind', 'render', 'artifact', 'alt', 'fit'}
    if kind == 'cycle':
        check_fields(data, common | {'nodes'}, {'nodes', 'alt'})
        nodes = data['nodes']
        if len(nodes) != 6:
            raise ValueError('Макет cycle рассчитан на шесть этапов')
        parts = []
        for i in (0, 1, 2, 5, 4, 3):
            node = nodes[i]; check_fields(node, {'title', 'detail', 'accent'}, {'title', 'detail'})
            accent = ' accent' if node.get('accent') else ''
            parts.append(f'<div class="cycle-node{accent}"><small>{i+1:02d}</small><b>{esc(node["title"])}</b><span>{esc(node["detail"])}</span></div>')
        arrows = ''.join(f'<span class="edge e{edge}" aria-hidden="true">{arrow}</span>' for edge, arrow in [('12','→'),('23','→'),('34','↓'),('45','←'),('56','←'),('61','↑')])
        return f'<div class="cycle" role="img" aria-label="{esc(data["alt"])}">'+''.join(parts)+arrows+'</div>'
    if kind == 'flows':
        check_fields(data, common | {'rows'}, {'rows'})
        rows = []
        for row in data['rows']:
            check_fields(row, {'title', 'nodes', 'return'}, {'title', 'nodes'})
            back = f'<div class="return-path">{esc(row["return"])}</div>' if row.get('return') else ''
            rows.append(f'<div class="model-row"><p class="label">{esc(row["title"])}</p>{flow(row["nodes"])}{back}</div>')
        return '<div class="model-rows">'+''.join(rows)+'</div>'
    if kind == 'context':
        check_fields(data, common | {'history', 'operation', 'context'}, {'history', 'operation', 'context'})
        def group(key, cls):
            group = data[key]; check_fields(group, {'title', 'items'}, {'title', 'items'})
            return f'<div class="{cls}"><p class="label">{esc(group["title"])}</p>'+''.join(f'<span>{esc(item)}</span>' for item in group['items'])+'</div>'
        return '<div class="context-map">'+group('history', 'context-history')+f'<div class="context-choice"><b>{esc(data["operation"])}</b><span aria-hidden="true">→</span></div>'+group('context', 'context-window')+'</div>'
    if kind == 'harness':
        check_fields(data, common | {'context', 'title', 'nodes', 'return', 'tools'}, {'context','title','nodes','return','tools'})
        return f'<div class="harness-map"><div class="harness-context"><b>Контекст</b><span>{esc(data["context"])}</span></div><div class="harness-core"><p class="label">{esc(data["title"])}</p>{flow(data["nodes"])}<div class="return-path">{esc(data["return"])}</div></div><div class="harness-tools"><b>Инструменты</b><span>{esc(data["tools"])}</span></div></div>'
    if kind == 'layers':
        check_fields(data, common | {'items'}, {'items'})
        parts = []
        for item in data['items']:
            check_fields(item, {'title','detail','example'}, {'title','detail','example'})
            parts.append(f'<div class="layer"><div><h3>{esc(item["title"])}</h3><p>{esc(item["detail"])}</p></div><strong>{esc(item["example"])}</strong></div>')
        return '<div class="layers">'+''.join(parts)+'</div>'
    raise ValueError(f'Неизвестный вид diagram: {kind}')


def render(kind, raw, registry):
    data = object_data(raw)
    mode = data.get('render', 'native')
    if mode not in ('native', 'image'):
        raise ValueError(f'Не поддерживается render={mode}; доступны native и image')
    if kind in ('diagram', 'table') and mode == 'image':
        return artifact_image(data.get('artifact',''), registry, data.get('alt',''), data.get('fit','contain'))
    if kind == 'image':
        check_fields(data, {'artifact','alt','fit'}, {'artifact','alt'})
        return artifact_image(data['artifact'], registry, data['alt'], data.get('fit','contain'))
    if kind == 'logos':
        check_fields(data, {'items'}, {'items'})
        if not isinstance(data['items'], list) or not 1 <= len(data['items']) <= 5:
            raise ValueError('logos: нужно от одного до пяти логотипов')
        items = []
        for item in data['items']:
            check_fields(item, {'artifact', 'name'}, {'artifact', 'name'})
            img = artifact_image(item['artifact'], registry, 'Логотип ' + item['name'])
            items.append(f'<figure>{img}<figcaption>{esc(item["name"])}</figcaption></figure>')
        return '<div class="logo-row">' + ''.join(items) + '</div>'
    if kind == 'diagram':
        return diagram(data)
    if kind == 'table':
        check_fields(data, {'columns','rows','render','artifact','alt','fit','emphasize'}, {'columns','rows'})
        width = len(data['columns'])
        if not width or not data['rows'] or any(len(row) != width for row in data['rows']):
            raise ValueError('В таблице должны совпадать размеры заголовка и строк')
        emphasis = data.get('emphasize', [])
        if any(type(i) is not int or not 0 <= i < width for i in emphasis):
            raise ValueError('emphasize: нужны индексы существующих столбцов, начиная с 0')
        header = ''.join(f'<th scope="col">{esc(value)}</th>' for value in data['columns'])
        rows = ''.join('<tr>'+''.join(f'<td><strong>{esc(value)}</strong></td>' if i in emphasis else f'<td>{esc(value)}</td>' for i,value in enumerate(row))+'</tr>' for row in data['rows'])
        return f'<table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>'
    if kind == 'callout':
        check_fields(data, {'text','tone'}, {'text'})
        tone = data.get('tone','key')
        if tone not in ('key','warning'):
            raise ValueError('tone: доступны key и warning')
        return f'<aside class="callout callout-{tone}">{esc(data["text"])}</aside>'
    if kind == 'cover':
        check_fields(data, {'date','subtitle','agenda'}, {'date','subtitle','agenda'})
        agenda = ''.join(f'<span><b>{esc(item[0])}</b>{esc(item[1])}</span>' for item in data['agenda'])
        return f'<div class="cover-meta">{esc(data["date"])}</div><div class="cover-subtitle">{esc(data["subtitle"])}</div><div class="cover-agenda">{agenda}</div>'
    if kind == 'result':
        check_fields(data, {'title','rows','summary'}, {'title','rows','summary'})
        rows=[]
        for row in data['rows']:
            check_fields(row, {'label','value','unexpected'}, {'label','value'})
            cls=' wrong' if row.get('unexpected') else ''
            rows.append(f'<div class="result-row{cls}"><b>{esc(row["label"])}</b><span>{esc(row["value"])}</span></div>')
        return f'<div class="code-result"><p class="label">{esc(data["title"])}</p>'+''.join(rows)+f'<p class="small">{esc(data["summary"])}</p></div>'
    if kind == 'caption':
        check_fields(data, {'text'}, {'text'})
        return f'<div class="asof">{esc(data["text"])}</div>'
    raise ValueError(f'Неизвестный блок: {kind}')
