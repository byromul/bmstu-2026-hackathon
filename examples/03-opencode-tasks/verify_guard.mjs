import assert from 'node:assert/strict';
import {mkdtemp,readFile,rm} from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {createGuard} from './.opencode/plugins/guard.js';
const temp=await mkdtemp(path.join(os.tmpdir(),'lecture-guard-'));
try {
 const before=createGuard(temp);
 await before({tool:'shell',input:{command:'git status --short'}});
 for(const command of ['git push','git push origin main','git -C /tmp/example push','echo ok && git push']) {
   await assert.rejects(()=>before({tool:'shell',input:{command}}),/DEMO_GUARD/);
 }
 const log=await readFile(path.join(temp,'.lab/guard.log'),'utf8');
 assert.equal(log.split('\n').filter(s=>s.startsWith('DENY ')).length,4);
 console.log('Callback плагина: git status разрешён; 4 запроса git push отклонены до запуска.');
 console.log('Это проверка callback; интеграция OpenCode проверяется отдельно.');
} finally {await rm(temp,{recursive:true,force:true});}
