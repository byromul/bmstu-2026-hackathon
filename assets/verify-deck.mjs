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
for(let i=1;i<=10;i++){
 await send('Runtime.evaluate',{expression:`location.hash='slide-${String(i).padStart(2,'0')}'`});
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
await send('Input.dispatchKeyEvent',{type:'keyDown',key:'n',code:'KeyN'});await send('Input.dispatchKeyEvent',{type:'keyUp',key:'n',code:'KeyN'});
let notes=(await send('Runtime.evaluate',{expression:"document.body.classList.contains('notes-on') && document.querySelector('.note.active h2').textContent.startsWith('02.')",returnByValue:true})).result.value;
await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape'});await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape'});

  const network=requests.filter(url=>/^https?:/.test(url));
  const report={date:new Date().toISOString(),chrome:(await send('Browser.getVersion')).product,
    offline:true,reports,errors,resources:requests.map(url=>url.startsWith('data:')?'embedded image':url.startsWith('file:')?'local lecture.html':url),
    keys:{first,second,notes}};
  await writeFile(path.join(dir,'report.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({slides:reports.length,overflow:reports.filter(r=>r.overflow.length),errors,network,keys:report.keys},null,2));
  if(network.length||errors.length||reports.some(r=>r.overflow.length||r.images.some(i=>!i.loaded))||first!=='slide-01'||second!=='slide-02'||!notes)throw new Error('Проверка презентации не пройдена; см. assets/preview/report.json');
}finally{
  socket?.close();
  if(proc.exitCode===null){proc.kill('SIGTERM');await Promise.race([new Promise(r=>proc.once('exit',r)),pause(3000)]);}
  await rm(temp,{recursive:true,force:true,maxRetries:3,retryDelay:150});
}
