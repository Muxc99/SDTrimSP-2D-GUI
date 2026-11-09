"""External engine discovery and execution; no engine or material data are bundled."""
from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import subprocess

@dataclass
class EngineConfig:
    executable: str = ''
    tables: str = ''
    results: str = ''
    distribution: str = ''  # empty means the user's default WSL distribution

    @classmethod
    def load(cls,settings,default_results):
        return cls(*(str(settings.value('engine/'+key,default)) for key,default in (
            ('executable',''),('tables',''),('results',str(default_results)),('distribution',''))))

    def save(self,settings):
        for key in ('executable','tables','results','distribution'):
            settings.setValue('engine/'+key,getattr(self,key))

def binary_kind(path):
    try:
        with Path(path).open('rb') as stream:header=stream.read(4)
    except OSError:return 'missing'
    if header==b'\x7fELF':return 'linux'
    if header[:2]==b'MZ':return 'windows'
    return 'unsupported'

def normalize_tables(path):
    p=Path(path).expanduser()
    if p.is_file() and p.name.lower()=='table1':return p.parent
    for relative in ('','tables','work/tables'):
        candidate=p/relative
        if (candidate/'table1').is_file():return candidate
    return p

def discover(roots,max_depth=4):
    """Bounded folder search. Never execute candidates or choose one silently."""
    binaries=[];tables=[];visited=set();budget=2500
    excluded={'.git','.venv','venv','node_modules','__pycache__','runs','cases','backups'}
    for root in roots:
        root=Path(root)
        if not root.is_dir():continue
        root=root.resolve()
        for folder,dirs,files in os.walk(root,followlinks=False):
            key=str(Path(folder).resolve()).lower()
            if key in visited:dirs[:]=[];continue
            visited.add(key);budget-=1
            if budget<0:return sorted(set(binaries)),sorted(set(tables))
            depth=len(Path(folder).relative_to(root).parts)
            dirs[:]=sorted(d for d in dirs if d.lower() not in excluded and depth<max_depth)
            names={f.lower():f for f in files}
            if 'table1' in names:tables.append(str(Path(folder)))
            for name in ('target.exe','target','sdtrimsp','sdtrimsp.exe','sdtrimsp-2d','sdtrimsp-2d.exe'):
                if name in names:
                    p=Path(folder)/names[name]
                    if binary_kind(p) in ('linux','windows'):binaries.append(str(p))
    return sorted(set(binaries)),sorted(set(tables))

def wsl_prefix(config):
    return ['wsl.exe']+(['-d',config.distribution] if config.distribution else [])+['--exec']

def command_output(args,timeout=12):
    kwargs={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    env=os.environ.copy();env['WSL_UTF8']='1'
    try:
        result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,env=env,**kwargs)
    except subprocess.TimeoutExpired:
        raise ValueError('运行环境检查超时，请确认 WSL 能正常启动。 / Runtime check timed out; check WSL.')
    def decode(value):
        if value.startswith((b'\xff\xfe',b'\xfe\xff')):return value.decode('utf-16',errors='replace').strip()
        if b'\x00' in value:return value.decode('utf-16-le',errors='replace').strip()
        return value.decode('utf-8',errors='replace').strip()
    text=decode(result.stdout)
    if result.returncode:raise ValueError('\n'.join(s for s in (text,decode(result.stderr)) if s) or 'Runtime command failed / 运行环境命令失败')
    return text

def linux_path(config,path):
    return command_output(wsl_prefix(config)+['wslpath','-a','-u',str(Path(path).resolve())])

def basic_errors(config):
    errors=[]
    protected=[]
    if config.executable:protected.append(Path(config.executable).resolve().parent)
    if config.tables:protected.append(Path(config.tables).resolve())
    kind=binary_kind(config.executable)
    if kind=='missing':errors.append('请选择实际的内核程序文件。 / Select the engine executable file.')
    elif kind=='unsupported':errors.append('所选文件不是 Windows 或 Linux 可执行程序，不能选择源码或启动脚本。 / Select a PE/ELF executable, not source or a script.')
    if kind=='linux' and os.name=='nt' and not shutil.which('wsl.exe'):
        errors.append('Linux 内核需要 WSL；本机未找到 WSL。 / A Linux engine requires WSL, which was not found.')
    if kind=='windows' and os.name!='nt':errors.append('Windows 内核需要 Windows。 / A Windows engine requires Windows.')
    if not config.tables or not (Path(config.tables)/'table1').is_file():
        errors.append('材料目录中缺少 table1；可单独选择材料目录或 table1。 / Missing table1; select its directory separately.')
    if not config.results:errors.append('请选择结果保存目录。 / Select a results directory.')
    elif any(Path(config.results).resolve().is_relative_to(p) for p in protected):
        errors.append('结果目录应独立于内核和材料目录。 / Use a separate results directory.')
    return errors

def probe_runtime(config):
    """Probe libraries without running the simulation executable."""
    kind=binary_kind(config.executable)
    if kind=='linux' and os.name=='nt':
        p=linux_path(config,config.executable)
        command_output(wsl_prefix(config)+['test','-x',p])
        script='out=$(ldd "$1" 2>&1); rc=$?; printf "%s\\n" "$out"; case "$out" in *"not found"*) exit 2;; *"not a dynamic executable"*|*"statically linked"*) exit 0;; esac; exit "$rc"'
        return command_output(wsl_prefix(config)+['sh','-c',script,'sd2d-check',p])
    if kind=='windows':
        import ctypes
        from ctypes import wintypes
        import pefile
        path=Path(config.executable).resolve()
        try:
            with pefile.PE(str(path),fast_load=True) as pe:
                pe.parse_data_directories(directories=[1,13])
                if pe.FILE_HEADER.Machine!=0x8664:
                    raise ValueError('此 GUI 支持 Windows x64 内核；请选 64 位内核。 / Select a Windows x64 engine.')
                imports={item.dll.decode('ascii') for name in ('DIRECTORY_ENTRY_IMPORT','DIRECTORY_ENTRY_DELAY_IMPORT') for item in getattr(pe,name,[])}
        except pefile.PEFormatError as e:raise ValueError('Invalid Windows executable / 无效的 Windows 程序') from e
        loader=ctypes.WinDLL('kernel32',use_last_error=True)
        loader.LoadLibraryExW.argtypes=[wintypes.LPCWSTR,wintypes.HANDLE,wintypes.DWORD]
        loader.LoadLibraryExW.restype=wintypes.HMODULE
        loader.FreeLibrary.argtypes=[wintypes.HMODULE]
        with os.add_dll_directory(str(path.parent)):
            for dll in sorted(imports):
                handle=loader.LoadLibraryExW(dll,None,0x1000)
                if not handle:
                    raise ValueError('缺少或无法加载运行库 / Missing or unloadable runtime library: '+dll)
                loader.FreeLibrary(handle)
        return 'Windows x64: import libraries checked (simulation not executed)'
    if kind=='linux':
        if not os.access(config.executable,os.X_OK):raise ValueError('Engine is not executable / 内核没有执行权限')
        return 'Linux executable'
    raise ValueError('Unsupported engine / 不支持的内核')

def required_tables(data):
    names={'table1'}
    symbols=data.get('symbol',['Ar','W'])
    modes=list(data.get('inel0',[-1]*len(symbols)))
    modes+=[-1]*max(0,len(symbols)-len(modes))
    modes={int(mode) if mode>=0 else 4 if symbol in ('H','D','T') else 5 if symbol in ('He','He3') else 7
           for symbol,mode in zip(symbols,modes)}
    if 4 in modes:names.add('table3')
    if 5 in modes:names.add('table4')
    if modes & {6,7}:names.update(('table6a','table6b'))
    if 7 in modes:names.update(('table7_ck','table7_a3a4a5'))
    if 8 in modes:names.add('tbsp.db')
    if any(v>0 for v in data.get('isot',[])):names.add('table2')
    if data.get('isbv')==8:names.add('table1a')
    if data.get('l_two_comp'):names.add('table.compound')
    return sorted(names)

def stage_tables(config,run_directory):
    """Private per-run snapshot; never write to the external engine installation."""
    destination=Path(run_directory)/'_tables'
    destination.mkdir()
    for source in Path(config.tables).iterdir():
        if source.is_file() and (source.name.lower().startswith('table') or source.name.lower()=='tbsp.db'):
            shutil.copy2(source,destination/source.name)
    return destination

def launch_command(config,run_directory):
    exe=str(Path(config.executable).resolve())
    if binary_kind(exe)=='linux' and os.name=='nt':
        run=linux_path(config,run_directory);engine=linux_path(config,exe)
        args=wsl_prefix(config)+['sh','-c','cd -- "$1" && exec "$2"','sd2d-run',run,engine]
        return args[0],args[1:]
    return exe,[]
