"""Render the November 14 diagrams from slides.md using only the standard library."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = {d['artifact']: d for raw in re.findall(r'```diagram\n(.*?)\n```', (ROOT / 'slides.md').read_text(), re.S) if (d := json.loads(raw)).get('artifact')}
INK, BLUE, RUST = '#17252b', '#17615f', '#a13f2d'

def text(x, y, value, size=30, color=INK, anchor='start', bold=False):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{700 if bold else 400}">{html.escape(value)}</text>'

def box(x, y, w, h, fill='#e9f2ef', stroke=BLUE):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'

def arrow(path, color=BLUE):
    return f'<path d="{path}" fill="none" stroke="{color}" stroke-width="4" marker-end="url(#{"red" if color == RUST else "green"})"/>'

def save(name, height, parts):
    markers = ''.join(f'<marker id="{key}" viewBox="0 0 12 12" refX="10" refY="6" markerWidth="9" markerHeight="9" orient="auto-start-reverse"><path d="M 1 1 L 11 6 L 1 11 z" fill="{color}"/></marker>' for key, color in [('green', BLUE), ('red', RUST)])
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="{height}" viewBox="0 0 1500 {height}" role="img"><defs>{markers}</defs><g font-family="Arial, sans-serif">' + ''.join(parts) + '</g></svg>\n'
    (ROOT / 'assets' / name).write_text(svg)

p=[]
for i, (title, detail) in enumerate(DATA['ART-0070']['rows']):
    y=8+i*85
    p += [box(6,y,1488,74),text(30,y+47,title,30,bold=True),text(570,y+47,detail,30)]
save('ART-0070-ownership.svg',350,p)

p=[]
for i,(stage,width) in enumerate(zip(DATA['ART-0076']['stages'],[1030,240,190,220])):
    y=10+i*70
    p += [text(6,y+33,f'{i+1:02}',26,BLUE),text(70,y+33,stage,32,bold=i==0),box(420,y,1030,46,'#f0f3f1','#d8dfdf'),box(420,y,width,46,BLUE if i==0 else '#e9f2ef')]
save('ART-0076-effort-bars.svg',280,p)

d=DATA['ART-0072']['nodes']
p=[box(450,8,530,90),text(715,65,d['session'],32,BLUE,'middle',True),box(970,173,510,90,'#fff2ed',RUST),text(1225,230,d['summary'],32,RUST,'middle',True),box(450,355,530,90),text(715,412,d['next'],32,BLUE,'middle',True),arrow('M 560 100 V 352'),text(535,240,'хорошо',28,BLUE,'end'),arrow('M 980 53 H 1225 V 170',RUST),text(1100,37,'плохо',28,RUST,'middle'),arrow('M 1225 265 V 310 H 860 V 352')]
save('ART-0072-context.svg',460,p)

d=DATA['ART-0073']['nodes'];p=[]
for key,x,y,w in [('model',6,70,350),('gate',535,70,430),('tool',1140,70,354),('deny',535,300,430)]:
    red=key=='deny';color=RUST if red else BLUE
    p += [box(x,y,w,110,'#fff2ed' if red else '#e9f2ef',color),text(x+w/2,y+42,d[key][0],30,color,'middle',True),text(x+w/2,y+83,d[key][1],27,INK,'middle')]
p += [arrow('M 358 125 H 532'),text(445,105,'запрос',26,BLUE,'middle'),arrow('M 967 125 H 1137'),text(1050,105,'разрешено',26,BLUE,'middle'),arrow('M 750 183 V 297',RUST),text(775,248,'запрещено',26,RUST)]
save('ART-0073-controls.svg',430,p)
print('Rendered 4 SVG diagrams')
