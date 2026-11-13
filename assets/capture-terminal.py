import os,pty,fcntl,termios,struct,select,time,subprocess,tempfile,json,socket
from pathlib import Path
import pyte
import html
root=Path(tempfile.mkdtemp(prefix='lecture-terminal-'));project=root/'demo';project.mkdir()
env=os.environ.copy()
for var,folder in [('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_STATE_HOME','state'),('XDG_CACHE_HOME','cache')]:
 p=root/folder;p.mkdir();env[var]=str(p)
for key in list(env):
 if any(word in key for word in ('API_KEY','AUTH_TOKEN','SECRET','PASSWORD')):del env[key]
env['TERM']='xterm-256color';env['COLORTERM']='truecolor';env['OPENCODE_DISABLE_AUTOUPDATE']='true'
sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
setup=subprocess.run(['/opt/homebrew/bin/opencode','service','set','port',str(port)],env=env,cwd=project,capture_output=True,text=True);print('setup',setup.returncode,setup.stdout,setup.stderr)
master,slave=pty.openpty();cols,rows=120,32
fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',rows,cols,0,0))
p=subprocess.Popen(['/opt/homebrew/bin/opencode'],cwd=project,env=env,stdin=slave,stdout=slave,stderr=slave,start_new_session=True);os.close(slave)
raw=b'';end=time.time()+18
while time.time()<end and p.poll() is None:
 ready,_,_=select.select([master],[],[],.2)
 if ready:
  try:raw+=os.read(master,65536)
  except OSError:break
p.terminate()
try:p.wait(timeout=3)
except subprocess.TimeoutExpired:p.kill();p.wait()
os.close(master)
subprocess.run(['/opt/homebrew/bin/opencode','service','stop'],env=env,cwd=project,capture_output=True,timeout=15)
Path('/private/tmp/lecture-terminal-raw.bin').write_bytes(raw)
screen=pyte.Screen(cols,rows);stream=pyte.Stream(screen);stream.feed(raw.decode(errors='replace'))
Path('/private/tmp/lecture-terminal-screen.txt').write_text('\n'.join(screen.display))
w,h=14,31
colors={'default':'#e4e4e4','black':'#111111','red':'#ed7777','green':'#83c492','brown':'#d4bc77','blue':'#7d9dd9','magenta':'#bb99dc','cyan':'#7fc5ce','white':'#eeeeee','brightblack':'#888888','brightwhite':'#ffffff'}
parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{cols*w+48}" height="{rows*h+48}" viewBox="0 0 {cols*w+48} {rows*h+48}"><rect width="100%" height="100%" fill="#101013"/>']
for y in range(rows):
 for x in range(cols):
  cell=screen.buffer[y][x];fg=colors.get(cell.fg,'#'+cell.fg if len(cell.fg)==6 else '#eeeeee');bg=colors.get(cell.bg,'#'+cell.bg if len(cell.bg)==6 else '#101013') if cell.bg!='default' else '#101013'
  if cell.reverse:fg,bg=bg,fg
  parts.append(f'<rect x="{24+x*w}" y="{24+y*h}" width="{w}" height="{h}" fill="{bg}"/>')
  if cell.data.strip():parts.append(f'<text x="{24+x*w}" y="{48+y*h}" font-family="Menlo,monospace" font-size="22" fill="{fg}">{html.escape(cell.data)}</text>')
parts.append('</svg>');Path('/private/tmp/lecture-opencode-first.svg').write_text(''.join(parts))
print('\n'.join(screen.display));print('capture:',root)
