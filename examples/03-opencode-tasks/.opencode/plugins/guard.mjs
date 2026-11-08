// OpenCode 1.14.48: V1 plugin API. Проверка до запуска bash.
import {appendFile, mkdir} from 'node:fs/promises';
import path from 'node:path';
export function checkCommand(command) {
  if (typeof command !== 'string') throw new Error('Команда должна быть строкой');
  // Учебный барьер; не анализатор всего shell и не системная граница сети.
  if (/\bgit\b[^\n;&|]*\bpush\b/i.test(command)) throw new Error('DEMO_GUARD: git push запрещён до выполнения');
}
export default async ({directory}) => ({
  'tool.execute.before': async (input, output) => {
    if (input.tool !== 'bash') return;
    const command = output.args.command;
    await mkdir(path.join(directory, '.lab'), {recursive:true});
    try {checkCommand(command);} catch(error) {
      await appendFile(path.join(directory, '.lab/guard.log'), `DENY ${command}\n`);
      throw error;
    }
    await appendFile(path.join(directory, '.lab/guard.log'), `ALLOW ${command}\n`);
  },
});
