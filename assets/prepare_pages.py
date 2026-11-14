"""Build the self-contained theory deck for GitHub Pages (standard library only)."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / '_site'


def main():
    OUTPUT.mkdir(exist_ok=True)
    target = OUTPUT / 'lecture-theory.html'
    subprocess.run(
        [sys.executable, str(ROOT / 'build.py'), '--block', '1', '--output', str(target)],
        cwd=ROOT, check=True,
    )
    # Both entry points contain the complete deck; no redirect or base-path assumptions.
    shutil.copyfile(target, OUTPUT / 'index.html')
    (OUTPUT / '.nojekyll').touch()
    print(f'GitHub Pages: {OUTPUT} (all display dependencies embedded in HTML)')


if __name__ == '__main__':
    main()
