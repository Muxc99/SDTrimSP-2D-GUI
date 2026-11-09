"""Source download launcher. Frozen Windows downloads do not need this setup."""
import os
from pathlib import Path
import subprocess
import sys
import venv

def main():
    if sys.version_info<(3,11):raise RuntimeError('Python 3.11 or newer is required. Use the Windows installer instead.')
    root=Path(__file__).resolve().parent
    state=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local')))/'SDTrimSP-2D_GUI'/'source-runtime-v090'
    python=state/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.exists():
        print('Preparing GUI runtime / 正在准备运行环境…',flush=True)
        venv.EnvBuilder(with_pip=True).create(state)
    ready=subprocess.run([str(python),'-c','import PySide6.QtWidgets,matplotlib,numpy,pefile,pandas'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if not ready:
        print('Installing required GUI packages automatically / 正在自动安装所需依赖…',flush=True)
        subprocess.run([str(python),'-m','pip','install','-r',str(root/'requirements.txt')],check=True)
    return subprocess.call([str(python),str(root/'app.py'),*sys.argv[1:]],cwd=root)

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:
        print('Startup failed / 启动失败:',e,flush=True);sys.exit(1)
