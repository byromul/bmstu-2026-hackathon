// OpenCode V2: переиспользуем plugin API готового harness.
import {appendFile, mkdir} from 'node:fs/promises';
import path from 'node:path';
export function checkCommand(command) {
  if (typeof command !== 'string') throw new Error('Команда должна быть строкой');
  // Учебный барьер; не анализатор всего shell и не системная граница сети.
  if (/\bgit\b[^\n;&|]*\bpush\b/i.test(command)) throw new Error('DEMO_GUARD: git push запрещён до выполнения');
}
export function createGuard(directory) {
  return async event => {
    if (event.tool !== 'shell') return;
    const command = event.input.command;
    await mkdir(path.join(directory, '.lab'), {recursive:true});
    try {checkCommand(command);} catch(error) {
      await appendFile(path.join(directory, '.lab/guard.log'), `DENY ${command}\n`);
      throw error;
    }
    await appendFile(path.join(directory, '.lab/guard.log'), `ALLOW ${command}\n`);
  };
}
export default {
  id: 'lecture-guard',
  async setup(ctx) {
    const directory=ctx.location.directory;
    await mkdir(path.join(directory, '.lab'), {recursive:true});
    await appendFile(path.join(directory, '.lab/guard.log'), `LOADED OpenCode ${ctx.app.version}\n`);
    const registration=await ctx.tool.hook('execute.before',createGuard(directory));
    return ()=>registration.dispose();
  },
};
