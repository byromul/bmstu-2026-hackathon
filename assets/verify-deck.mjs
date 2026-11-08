// Проверка и превью автономной HTML-презентации в отдельном временном Chrome.
import {readFile,writeFile,mkdtemp,rm,access,mkdir} from 'node:fs/promises';
import {spawn} from 'node:child_process';
import {fileURLToPath,pathToFileURL} from 'node:url';
import path from 'node:path';
import os from 'node:os';
const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'..');
const candidates=[process.env.CHROME_BIN,'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/usr/bin/google-chrome','/usr/bin/chromium',process.env.PROGRAMFILES&&path.join(process.env.PROGRAMFILES,'Google/Chrome/Application/chrome.exe')].filter(Boolean);
let chrome;
for(const candidate of candidates){try{await access(candidate);chrome=candidate;break;}catch{}}
if(!chrome) throw new Error('Укажите путь к Chrome в CHROME_BIN');
const temp=await mkdtemp(path.join(os.tmpdir(),'lecture-deck-review-'));
const proc=spawn(chrome,['--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--disable-background-networking','--remote-debugging-port=0',`--user-data-dir=${temp}`,'about:blank'],{stdio:'ignore'});
let socket;const errors=[],requests=[];let exitError;
proc.on('error',error=>{exitError=error;});
const pause=ms=>new Promise(r=>setTimeout(r,ms));
try{
  let port;
  for(let i=0;i<150;i++){if(exitError)throw exitError;try{port=(await readFile(path.join(temp,'DevToolsActivePort'),'utf8')).split('\n')[0];break;}catch{await pause(100);}}
  if(!port)throw new Error('Chrome не запустил локальный отладочный порт');
  const tabs=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  socket=new WebSocket(tabs.find(tab=>tab.type==='page').webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
  let id=0;const pending=new Map();
  socket.onmessage=event=>{const msg=JSON.parse(event.data);if(msg.id){const p=pending.get(msg.id);if(!p)return;clearTimeout(p.timer);pending.delete(msg.id);msg.error?p.reject(new Error(JSON.stringify(msg.error))):p.resolve(msg.result);}else if(msg.method==='Runtime.exceptionThrown')errors.push(msg.params.exceptionDetails.text);else if(msg.method==='Network.requestWillBeSent')requests.push(msg.params.request.url);};
  const send=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;const timer=setTimeout(()=>{pending.delete(n);reject(new Error('Timeout: '+method));},30000);pending.set(n,{resolve,reject,timer});socket.send(JSON.stringify({id:n,method,params}));});
  await send('Page.enable');await send('Runtime.enable');await send('Network.enable');
  await send('Network.emulateNetworkConditions',{offline:true,latency:0,downloadThroughput:0,uploadThroughput:0});
await send('Emulation.setDeviceMetricsOverride',{width:1600,height:900,deviceScaleFactor:1,mobile:false});
await send('Network.emulateNetworkConditions',{offline:true,latency:0,downloadThroughput:0,uploadThroughput:0});
await send('Page.navigate',{url:pathToFileURL(path.join(root,'lecture.html')).href});
await new Promise(r=>setTimeout(r,500));
const dir=path.join(root,'assets/preview');await mkdir(dir,{recursive:true});
const reports=[];
const slideIds=(await send('Runtime.evaluate',{expression:"[...document.querySelectorAll('.slide')].map(s=>s.id)",returnByValue:true})).result.value;
if(!slideIds?.length) throw new Error('Нет слайдов для проверки');
for(const [offset,slideId] of slideIds.entries()){
 const i=offset+1;
 await send('Runtime.evaluate',{expression:`location.hash=${JSON.stringify(slideId)}`});
 await new Promise(r=>setTimeout(r,100));
 const report=await send('Runtime.evaluate',{expression:`(()=>{const s=document.querySelector('.slide.active'); const body=s.querySelector('.body');const footer=s.querySelector('.sources').getBoundingClientRect();const bounds=body.getBoundingClientRect();let out=[];for(const e of body.querySelectorAll('*')){if(!e.textContent.trim()&&e.tagName!=='IMG')continue;const r=e.getBoundingClientRect();if(r.bottom>footer.top-10||r.right>1536||r.left<56)out.push({tag:e.tagName,text:e.textContent.slice(0,65),x:r.x,y:r.y,right:r.right,bottom:r.bottom});}return {title:s.querySelector('h1').textContent,images:[...s.querySelectorAll('img')].map(i=>({artifact:i.dataset.artifact,loaded:i.complete&&i.naturalWidth>0})),bodyHeight:bounds.height,scrollHeight:body.scrollHeight,footerTop:footer.top,overflow:out};})()`,returnByValue:true});
 reports.push({slide:i,...report.result.value});
 const png=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
 await writeFile(`${dir}/slide-${String(i).padStart(2,'0')}.png`,Buffer.from(png.data,'base64'));
}
await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Home',code:'Home'});await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Home',code:'Home'});
let first=(await send('Runtime.evaluate',{expression:"document.querySelector('.slide.active').id",returnByValue:true})).result.value;
await send('Input.dispatchKeyEvent',{type:'keyDown',key:'ArrowRight',code:'ArrowRight'});await send('Input.dispatchKeyEvent',{type:'keyUp',key:'ArrowRight',code:'ArrowRight'});
let second=(await send('Runtime.evaluate',{expression:"document.querySelector('.slide.active').id",returnByValue:true})).result.value;
await send('Input.dispatchKeyEvent',{type:'keyDown',key:'End',code:'End'});await send('Input.dispatchKeyEvent',{type:'keyUp',key:'End',code:'End'});
let last=(await send('Runtime.evaluate',{expression:"document.querySelector('.slide.active').id",returnByValue:true})).result.value;
await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Home',code:'Home'});await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Home',code:'Home'});
await send('Input.dispatchKeyEvent',{type:'keyDown',key:'ArrowRight',code:'ArrowRight'});await send('Input.dispatchKeyEvent',{type:'keyUp',key:'ArrowRight',code:'ArrowRight'});
await send('Input.dispatchKeyEvent',{type:'keyDown',key:'n',code:'KeyN'});await send('Input.dispatchKeyEvent',{type:'keyUp',key:'n',code:'KeyN'});
let notes=(await send('Runtime.evaluate',{expression:"document.body.classList.contains('notes-on') && document.querySelector('.note.active h2').textContent.startsWith('02.')",returnByValue:true})).result.value;
await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape'});await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape'});

  const network=requests.filter(url=>/^https?:/.test(url));
  const report={date:new Date().toISOString(),chrome:(await send('Browser.getVersion')).product,
    offline:true,reports,errors,resources:requests.map(url=>url.startsWith('data:')?'embedded image':url.startsWith('file:')?'local lecture.html':url),
    keys:{first,second,last,notes}};
  await writeFile(path.join(dir,'report.json'),JSON.stringify(report,null,2)+'\n');
  const cards=reports.map(r=>`<a href="slide-${String(r.slide).padStart(2,'0')}.png"><img loading="lazy" src="slide-${String(r.slide).padStart(2,'0')}.png" alt="Слайд ${r.slide}"><span>${String(r.slide).padStart(2,'0')}. ${r.title.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')}</span></a>`).join('');
  await writeFile(path.join(dir,'index.html'),`<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Теоретическая часть — превью</title><style>body{margin:32px;background:#fafaf7;color:#18272d;font:18px Arial,sans-serif}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px}a{color:#17615f}img{width:100%;border:1px solid #ccd7d9}span{display:block;margin-top:8px}h1{font-size:32px}</style><h1>Теоретическая часть: ${reports.length} слайдов</h1><p>Превью автономного HTML. <a href="../../lecture.html">Открыть презентацию</a></p><main>${cards}</main></html>`);
  console.log(JSON.stringify({slides:reports.length,overflow:reports.filter(r=>r.overflow.length),errors,network,keys:report.keys},null,2));
  if(network.length||errors.length||reports.some(r=>r.overflow.length||r.images.some(i=>!i.loaded))||first!==slideIds[0]||second!==slideIds[1]||last!==slideIds.at(-1)||!notes)throw new Error('Проверка презентации не пройдена; см. assets/preview/report.json');
}finally{
  socket?.close();
  if(proc.exitCode===null){proc.kill('SIGTERM');await Promise.race([new Promise(r=>proc.once('exit',r)),pause(3000)]);}
  await rm(temp,{recursive:true,force:true,maxRetries:3,retryDelay:150});
}
