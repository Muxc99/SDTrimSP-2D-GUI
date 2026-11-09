# Build from a clean venv containing only GUI dependencies and PyInstaller.
from pathlib import Path
from importlib.metadata import distribution
import sys
import os
root=Path(SPECPATH)
license_data=[]
for name in ('PySide6-Essentials','shiboken6','numpy','pandas','matplotlib','pillow',
             'contourpy','cycler','fonttools','kiwisolver','packaging','pefile',
             'pyparsing','python-dateutil','tzdata'):
    package=distribution(name)
    for file in package.files or ():
        if any(part.lower() in ('licenses','license','license.txt','copying','copying.txt') for part in file.parts):
            source=Path(package.locate_file(file))
            if source.is_file():license_data.append((str(source),'third_party_licenses/'+name+'/'+str(file.parent)))
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if python_license.is_file():license_data.append((str(python_license),'third_party_licenses/Python'))
a=Analysis([str(root/'app.py')],pathex=[str(root)],
    binaries=[],datas=[(str(root/'assets'),'assets'),(str(root/'docs/help'),'docs/help')]+license_data,
    hiddenimports=['matplotlib.backends.backend_qtagg','pefile'],
    excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtQml',
              'PySide6.QtQuick','tkinter','scipy','IPython','pytest'],noarchive=False)
# Never collect an unrelated tool's same-named DLL from the builder's PATH.
allowed=[Path(sys.prefix).resolve(),Path(sys.base_prefix).resolve(),
         Path(os.environ['SystemRoot']).resolve()]
unexpected=[source for _,source,_ in a.binaries
            if not any(Path(source).resolve().is_relative_to(folder) for folder in allowed)]
if unexpected:
    raise RuntimeError('Foreign build DLLs detected. Use build_windows.py with a clean venv: '+repr(unexpected))
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='SDTrimSP-2D_GUI',
    debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False,
    icon=str(root/'assets/SDTrimSP-2D_GUI.ico'))
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='SDTrimSP-2D_GUI')
