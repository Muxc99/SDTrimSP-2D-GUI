"""Isolated Windows DLL check. Never import Qt or run the engine executable."""
import ctypes
from ctypes import wintypes
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sys
import pefile


def check(executable,directories):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.SetDllDirectoryW.argtypes=[wintypes.LPCWSTR]
    kernel.SetDllDirectoryW.restype=wintypes.BOOL
    kernel.SetErrorMode(0x0001|0x8000)  # No missing-DLL Windows popup in the helper.
    if not kernel.SetDllDirectoryW(None):raise ctypes.WinError(ctypes.get_last_error())
    directories=[Path(p).resolve() for p in directories]
    # Include inherited PATH for users who already configured their toolchain.
    for entry in os.environ.get('PATH','').split(os.pathsep):
        p=Path(entry)
        if entry and p.is_dir() and p not in directories:directories.append(p)
    kernel.LoadLibraryExW.argtypes=[wintypes.LPCWSTR,wintypes.HANDLE,wintypes.DWORD]
    kernel.LoadLibraryExW.restype=wintypes.HMODULE
    kernel.FreeLibrary.argtypes=[wintypes.HMODULE]
    handles=[];seen=set()
    def visit(path,chain):
        key=str(path).casefold()
        if key in seen:return
        seen.add(key)
        try:
            with pefile.PE(str(path),fast_load=True) as pe:
                if pe.FILE_HEADER.Machine!=0x8664:
                    raise ValueError('需要 Windows x64 程序和运行库。 / Windows x64 executable and DLLs required: '+str(path))
                pe.parse_data_directories(directories=[1])
                imports=[item.dll.decode('ascii') for item in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[])]
        except pefile.PEFormatError as e:raise ValueError('无效的 Windows 文件 / Invalid PE: '+str(path)) from e
        for name in imports:
            if '/' in name or '\\' in name:raise ValueError('Invalid DLL name: '+name)
            candidate=next((d/name for d in directories if (d/name).is_file()),None)
            if candidate and not candidate.is_relative_to(Path(os.environ['SystemRoot'])):
                visit(candidate,chain+[name])
            handle=kernel.LoadLibraryExW(str(candidate) if candidate else name,None,0x1100 if candidate else 0x1000)
            if not handle:
                code=ctypes.get_last_error()
                raise ValueError('缺少或无法加载运行库 / Missing or unloadable runtime library: '+
                    ' -> '.join(chain+[name])+f'\nWindows error {code}: '+ctypes.FormatError(code).strip()+
                    '\n请在内核设置中选择配套的 Windows 运行库目录。 / Select the matching Windows runtime directory in Engine settings.')
            handles.append(handle)
    with ExitStack() as stack:
        for folder in directories:stack.enter_context(os.add_dll_directory(str(folder)))
        try:visit(Path(executable).resolve(),[Path(executable).name])
        finally:
            for handle in reversed(handles):kernel.FreeLibrary(handle)
    return 'Windows x64：运行库检查通过（未执行模拟）。 / Runtime libraries checked (simulation not executed).'


def main(args=None):
    args=sys.argv[1:] if args is None else args
    try:report={'ok':True,'message':check(args[0],args[1:])}
    except Exception as e:report={'ok':False,'message':str(e)}
    payload=json.dumps(report,ensure_ascii=False).encode('utf-8')+b'\n'
    if sys.stdout is not None:
        sys.stdout.buffer.write(payload);sys.stdout.buffer.flush()
    else:
        # A windowed frozen EXE has no sys.stdout, even with a redirected handle.
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetStdHandle.argtypes=[wintypes.DWORD];kernel.GetStdHandle.restype=wintypes.HANDLE
        kernel.WriteFile.argtypes=[wintypes.HANDLE,wintypes.LPCVOID,wintypes.DWORD,
                                  ctypes.POINTER(wintypes.DWORD),wintypes.LPVOID]
        count=wintypes.DWORD()
        kernel.WriteFile(kernel.GetStdHandle(-11 & 0xffffffff),payload,len(payload),ctypes.byref(count),None)
    return 0 if report['ok'] else 1


if __name__=='__main__':sys.exit(main())
