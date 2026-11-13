"""External engine discovery and execution; no engine or material data are bundled."""
from dataclasses import dataclass
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager

@dataclass
class EngineConfig:
    executable: str = ''
    tables: str = ''
    results: str = ''
    distribution: str = ''  # empty means the user's default WSL distribution
    runtime: str = ''  # Windows engine DLL directory; empty enables local discovery

    @classmethod
    def load(cls,settings,default_results):
        return cls(*(str(settings.value('engine/'+key,default)) for key,default in (
            ('executable',''),('tables',''),('results',str(default_results)),('distribution',''),('runtime',''))))

    def save(self,settings):
        for key in ('executable','tables','results','distribution','runtime'):
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


def runtime_candidates(executable):
    """Only inspect nearby installation folders; do not mix global toolchains."""
    if binary_kind(executable)!='windows':return []
    folder=Path(executable).resolve().parent
    found=[];seen={str(folder).casefold()}
    for base in (folder,folder.parent):
        for relative in ('ucrt64/bin','mingw64/bin','ucrt/ucrt64/bin','ucrt/mingw64/bin',
                         'mingw/ucrt64/bin','mingw/mingw64/bin','bin','runtime/bin','runtime','lib'):
            candidate=base/relative
            key=str(candidate).casefold()
            if key in seen:continue
            seen.add(key)
            if candidate.is_dir() and any(candidate.glob('*.dll')):found.append(candidate)
    # A Fortran runtime is a more specific match than an arbitrary bin folder.
    fortran=[p for p in found if any(p.glob('libgfortran*.dll'))]
    return fortran or found


def runtime_directories(config):
    if binary_kind(config.executable)!='windows':return []
    folder=Path(config.executable).resolve().parent
    if config.runtime:
        chosen=Path(config.runtime).expanduser().resolve()
        if not chosen.is_dir():
            raise ValueError('Windows 运行库目录不存在。 / Windows runtime directory does not exist: '+str(chosen))
        return list(dict.fromkeys((folder,chosen)))
    # DLLs alongside the executable need no extra runtime directory.
    if any(folder.glob('libgfortran*.dll')):return [folder]
    candidates=runtime_candidates(config.executable)
    if len(candidates)>1:
        raise ValueError('找到多个运行库目录，请在设置中明确选择。 / Multiple runtime directories found; select one explicitly:\n'+
                         '\n'.join(map(str,candidates)))
    return [folder]+candidates


def engine_environment(config,environ=None):
    """Use the same external DLL path for preflight and the actual child process."""
    env=dict(os.environ if environ is None else environ)
    if binary_kind(config.executable)=='windows':
        original=env.get('PATH','')
        if getattr(sys,'frozen',False):
            internal=Path(sys._MEIPASS).resolve()
            original=os.pathsep.join(entry for entry in original.split(os.pathsep)
                if entry and not Path(entry).resolve().is_relative_to(internal))
        env['PATH']=os.pathsep.join([*map(str,runtime_directories(config)),original])
    env['WSL_UTF8']='1'
    return env


@contextmanager
def external_dll_search():
    """PyInstaller's DLL directory must not be inherited by an external engine."""
    if os.name!='nt' or not getattr(sys,'frozen',False):
        yield;return
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetDllDirectoryW.argtypes=[wintypes.DWORD,wintypes.LPWSTR]
    kernel.GetDllDirectoryW.restype=wintypes.DWORD
    kernel.SetDllDirectoryW.argtypes=[wintypes.LPCWSTR]
    kernel.SetDllDirectoryW.restype=wintypes.BOOL
    size=kernel.GetDllDirectoryW(0,None)
    previous=ctypes.create_unicode_buffer(size+1)
    kernel.GetDllDirectoryW(len(previous),previous)
    if not kernel.SetDllDirectoryW(None):raise ctypes.WinError(ctypes.get_last_error())
    try:yield
    finally:kernel.SetDllDirectoryW(previous.value or None)

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
    if kind=='windows':
        try:runtime_directories(config)
        except ValueError as e:errors.append(str(e))
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
        import json
        helper=([sys.executable,'--probe-windows-runtime'] if getattr(sys,'frozen',False) else
                [sys.executable,str(Path(__file__).with_name('windows_runtime_probe.py'))])
        args=helper+[str(Path(config.executable).resolve()),*map(str,runtime_directories(config))]
        with external_dll_search():
            try:
                result=subprocess.run(args,env=engine_environment(config),stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            except subprocess.TimeoutExpired as e:
                raise ValueError('Windows 运行库检查超时。 / Windows runtime check timed out.') from e
        try:report=json.loads(result.stdout.decode('utf-8'))
        except (UnicodeError,ValueError) as e:
            raise ValueError('运行库检查进程异常退出。 / Runtime checker exited unexpectedly: '+str(result.returncode)) from e
        if result.returncode or not report['ok']:raise ValueError(report['message'])
        return report['message']
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

def apply_material_overrides(table_directory,overrides,isbv=0):
    """Apply per-run mass and density edits to private table snapshots only."""
    root=Path(table_directory)
    symbols={str(row['symbol']):row for row in overrides}
    if not symbols:return
    targets=[root/'table1']
    if (root/'table1a').is_file():targets.append(root/'table1a')
    active=root/('table1a' if int(isbv)==8 else 'table1')
    if active not in targets:raise ValueError('当前结合能模型需要材料表 '+active.name+'，但运行副本中不存在。')
    seen={symbol:set() for symbol in symbols}
    for path in targets:
        text=path.read_text(encoding='utf-8')
        lines=text.splitlines(keepends=True)
        for index,line in enumerate(lines):
            if index<11 or not line.strip() or line.lstrip().startswith('!'):continue
            matches=list(re.finditer(r'\S+',line))
            if len(matches)<5:continue
            symbol=matches[0].group()
            if symbol not in symbols:continue
            values=(symbols[symbol]['mass'],symbols[symbol]['density'],symbols[symbol]['atomic_density'])
            replacements=(format(values[0],'.10g'),format(values[1],'.10g'),format(values[2],'.10g'))
            for column,value in reversed(list(zip((2,3,4),replacements))):
                span=matches[column].span()
                line=line[:span[0]]+value+line[span[1]:]
            lines[index]=line
            seen[symbol].add(path.name)
        path.write_text(''.join(lines),encoding='utf-8',newline='')
    missing=[symbol for symbol in symbols if active.name not in seen[symbol]]
    if missing:raise ValueError('所选材料未在运行副本材料表中找到：'+', '.join(missing))

def launch_command(config,run_directory):
    exe=str(Path(config.executable).resolve())
    if binary_kind(exe)=='linux' and os.name=='nt':
        run=linux_path(config,run_directory);engine=linux_path(config,exe)
        args=wsl_prefix(config)+['sh','-c','cd -- "$1" && exec "$2"','sd2d-run',run,engine]
        return args[0],args[1:]
    return exe,[]
