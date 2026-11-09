"""Keep writable user data separate from bundled application resources."""
from pathlib import Path
from PySide6.QtCore import QStandardPaths

def documents_root():
    base=QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    return Path(base or Path.home()/'Documents')/'SDTrimSP-2D'

def state_root():
    base=QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    path=Path(base or Path.home()/'.sdtrimsp2d')
    path.mkdir(parents=True,exist_ok=True)
    return path
