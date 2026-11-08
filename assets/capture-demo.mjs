// Захват реальных учебных интерфейсов. Не запускает модели и не генерирует изображения.
import {access,mkdtemp,readFile,writeFile,rm} from 'node:fs/promises';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import os from 'node:os';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const id=process.argv[2];
const options={'ART-0040':{port:8080,name:'task-app',prompt:'task-app-preview'},'ART-0041':{port:8025,name:'mailpit',prompt:'mailpit-preview'},'ART-0047':{port:8080,name:'task-app',prompt:'task-app-preview',version:'v02',focus:'app'},'ART-0048':{port:8025,name:'mailpit',prompt:'mailpit-preview',version:'v02',focus:'mail'}};
const option=options[id];if(!option)throw Error('Нужен ART-0040, ART-0041, ART-0047 или ART-0048');
await access(path.join(root,`prompts/${id}-${option.prompt}-${option.version||"v01"}.md`));
const chrome=process.env.CHROME_BIN||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const temp=await mkdtemp(path.join(os.tmpdir(),'lecture-demo-preview-'));
const proc=spawn(chrome,['--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--remote-debugging-port=0',`--user-data-dir=${temp}`,'about:blank'],{stdio:'ignore'});
const pause=ms=>new Promise(r=>setTimeout(r,ms));let socket;
try{
 let port;for(let i=0;i<150;i++){try{port=(await readFile(path.join(temp,'DevToolsActivePort'),'utf8')).split('\n')[0];break;}catch{await pause(100);}}
 if(!port)throw Error('Chrome не открыл порт');
 const tabs=await(await fetch(`http://127.0.0.1:${port}/json/list`)).json();socket=new WebSocket(tabs.find(t=>t.type==='page').webSocketDebuggerUrl);
 await new Promise((r,j)=>{socket.onopen=r;socket.onerror=j});let seq=0;const pending=new Map();
 socket.onmessage=event=>{const m=JSON.parse(event.data);if(!m.id)return;const p=pending.get(m.id);if(p){pending.delete(m.id);clearTimeout(p.timer);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result)}};
 const send=(method,params={})=>new Promise((resolve,reject)=>{const n=++seq;const timer=setTimeout(()=>reject(Error('Timeout '+method)),15000);pending.set(n,{resolve,reject,timer});socket.send(JSON.stringify({id:n,method,params}))});
 await send('Page.enable');await send('Runtime.enable');await send('Emulation.setDeviceMetricsOverride',{width:1600,height:900,deviceScaleFactor:1,mobile:false});
 await send('Emulation.setEmulatedMedia',{features:[{name:'prefers-color-scheme',value:'light'}]});
 await send('Page.navigate',{url:`http://127.0.0.1:${option.port}/`});
 await pause(1000);
 if(option.name==='mailpit'){
  const found=await send('Runtime.evaluate',{expression:`(()=>{const a=[...document.querySelectorAll('a')].find(a=>a.textContent.includes('Учебная задача: отметка выполнена'));if(a){a.click();return true}return false})()`,returnByValue:true});
  if(!found.result.value)throw Error('Учебное письмо не найдено в интерфейсе');await pause(600);
 }
 const visible=await send('Runtime.evaluate',{expression:'document.body.innerText',returnByValue:true});
 if(option.name==='task-app'&&(!visible.result.value.includes('Готово')||!visible.result.value.includes('Не выполнена')))throw Error('Нет ожидаемого состояния задач');
 if(option.name==='mailpit'&&!visible.result.value.includes('boss@example.test'))throw Error('Не открыт адресат учебного письма');
 let clip;
 if(option.focus==='app'){
  const measured=await send('Runtime.evaluate',{expression:'(()=>{const r=document.body.getBoundingClientRect();return {x:Math.max(0,r.x-24),y:Math.max(0,r.y-20),width:r.width+48,height:r.height+40,scale:1}})()',returnByValue:true});clip=measured.result.value;
 }
 if(option.focus==='mail'){
  await send('Runtime.evaluate',{expression:"document.documentElement.setAttribute('data-bs-theme','light');document.documentElement.style.fontSize='20px';document.querySelectorAll('pre').forEach(p=>{p.style.fontSize='20px';p.style.lineHeight='1.5';p.style.whiteSpace='pre-wrap'})"});
  await pause(200);clip={x:400,y:60,width:1180,height:500,scale:1};
 }
 const png=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,...(clip?{clip}:{})});
 const output=path.join(root,`assets/${id}-${option.name}-${option.version||"v01"}.png`);await writeFile(output,Buffer.from(png.data,'base64'));
 console.log(JSON.stringify({artifact:id,file:path.relative(root,output),date:new Date().toISOString(),source:'реальный локальный интерфейс',model:false}));
}finally{socket?.close();proc.kill();await Promise.race([new Promise(r=>proc.once('exit',r)),pause(2000)]);await rm(temp,{recursive:true,force:true,maxRetries:3,retryDelay:150});}
