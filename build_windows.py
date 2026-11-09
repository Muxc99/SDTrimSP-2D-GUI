"""Build with an isolated DLL search path; invoke using a clean build venv."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    if os.name != 'nt':
        raise SystemExit('Build the Windows package on Windows x64.')
    root = Path(__file__).resolve().parent
    system = Path(os.environ['SystemRoot'])
    env = os.environ.copy()
    env['PATH'] = os.pathsep.join(map(str, (
        Path(sys.executable).parent, Path(sys.base_prefix), system/'System32',
        system, system/'System32'/'Wbem')))
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    return subprocess.call([
        sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm',
        *sys.argv[1:], str(root/'SDTrimSP-2D_GUI.spec')], cwd=root, env=env)


if __name__ == '__main__':
    sys.exit(main())
