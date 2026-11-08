// Локальный экспорт через официальный SDK. npm и сеть при обычном запуске не нужны.
import {readFile,writeFile,mkdtemp,rm,access} from 'node:fs/promises';
import {spawn} from 'node:child_process';
import {fileURLToPath,pathToFileURL} from 'node:url';
import path from 'node:path';
import os from 'node:os';
const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../..');
const markdown=await readFile(path.join(root,'slides.md'),'utf8');
const trial=markdown.split('## Проба визуализации. Агентский цикл\n')[1];
const match=trial?.match(/```diagram\n([\s\S]*?)\n```/);
if(!match) throw new Error('Не найден раздел пробы в slides.md');
const spec=JSON.parse(match[1]);
if(spec.artifact!=='ART-0018') throw new Error('Для новой версии заведите отдельный ID и путь результата');
const prompt=path.join(root,'prompts/ART-0018-agent-loop-excalidraw-v01.md');
await access(prompt);
const candidates=[process.env.CHROME_BIN,'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/usr/bin/google-chrome','/usr/bin/chromium',process.env.PROGRAMFILES&&path.join(process.env.PROGRAMFILES,'Google/Chrome/Application/chrome.exe')].filter(Boolean);
let chrome;
for(const candidate of candidates){try{await access(candidate);chrome=candidate;break;}catch{}}
if(!chrome) throw new Error('Укажите путь к Chrome в CHROME_BIN');
const temp=await mkdtemp(path.join(os.tmpdir(),'lecture-excalidraw-'));
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
  const loader=path.join(temp,'export.html');
  await writeFile(loader,`<!doctype html><meta charset="utf-8"><script src="${pathToFileURL(path.join(here,'vendor/export-bundle.js'))}"></script>`);
  await send('Page.navigate',{url:pathToFileURL(loader).href});
  let ready=false;
  for(let i=0;i<150;i++){const res=await send('Runtime.evaluate',{expression:'typeof window.renderLectureDiagram === "function"',returnByValue:true});if(res.result.value){ready=true;break;}await pause(100);}
  if(!ready)throw new Error('SDK не загрузился: '+errors.join('; '));
  const result=await send('Runtime.evaluate',{expression:`window.renderLectureDiagram(${JSON.stringify(spec)})`,awaitPromise:true,returnByValue:true});
  if(result.exceptionDetails)throw new Error(result.exceptionDetails.exception?.description||result.exceptionDetails.text);
  const output=result.result.value;
  if(requests.some(url=>/^https?:/.test(url)))throw new Error('SDK запрашивал сеть: '+requests.filter(url=>/^https?:/.test(url)).join(', '));
  if(errors.length)throw new Error(errors.join('; '));
  const basename=path.join(root,'assets/ART-0018-agent-loop-v01');
  await writeFile(basename+'.svg',output.svg);
  await writeFile(basename+'.excalidraw',JSON.stringify(output.scene,null,2)+'\n');
  const report={date:new Date().toISOString(),sdk:'@excalidraw/excalidraw 0.18.1',node:process.version,platform:process.platform,arch:process.arch,chrome:(await send('Browser.getVersion')).product,offline:true,errors,resources:requests.map(url=>url.startsWith('data:')?'embedded data resource':url.endsWith('export.html')?'local export.html':url.endsWith('export-bundle.js')?'local export-bundle.js':url),...output.summary};
  await writeFile(path.join(here,'render-report.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({svg:path.relative(root,basename+'.svg'),scene:path.relative(root,basename+'.excalidraw'),...report},null,2));
}finally{
  socket?.close();
  if(proc.exitCode===null){proc.kill('SIGTERM');await Promise.race([new Promise(r=>proc.once('exit',r)),pause(3000)]);}
  await rm(temp,{recursive:true,force:true,maxRetries:3,retryDelay:150});
}
