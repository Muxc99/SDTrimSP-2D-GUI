"""保存当前案例输入；先检查、备份并暂存，出错时恢复已替换文件。"""
from datetime import datetime
from pathlib import Path
import os,uuid
from case_model import read_text
from input_file_io import normalized_input_text


def save_input_files(owner):
    if owner.source is None:raise ValueError(owner.raw_text('新案例请先选择保存目录。','Choose a save folder for this new case first.'))
    tri,fig,_=owner.checked_inputs();folder=Path(owner.source)
    contents=owner.current_files();contents['tri.inp']=tri
    if fig is not None:contents['fig.inp']=fig
    contents.setdefault('stop_run.inp','0\n')
    changed={}
    for name,text in contents.items():
        if Path(name).name!=name or not name.lower().endswith('.inp'):raise ValueError('非法输入文件名：'+name)
        target=folder/name
        text=normalized_input_text(text)
        if target.exists() and read_text(target)==text:continue
        changed[name]=text
    removed={name for name in getattr(owner,'removed_files',set()) if name not in contents}
    from input_editing import required_input_files
    from case_model import inspect_input
    _,data=inspect_input(tri)
    for name in removed:
        if Path(name).name!=name or not name.endswith('.inp') or name in required_input_files(data):
            raise ValueError('不能移除必要输入文件 / Cannot remove required input: '+name)
    removed={name for name in removed if (folder/name).is_file()}
    if not changed and not removed:return folder,None
    backup=folder/'.gui-backups'/(datetime.now().strftime('%Y%m%d_%H%M%S_%f'));backup.mkdir(parents=True)
    old={};staged={};written=[]
    try:
        for name,text in changed.items():
            target=folder/name;old[name]=target.read_bytes() if target.exists() else None
            if old[name] is not None:(backup/name).write_bytes(old[name])
            temp=folder/('.'+name+'.gui-save-'+uuid.uuid4().hex+'.tmp');staged[name]=temp
            temp.write_bytes(text.encode('utf-8'))
        for name,temp in staged.items():
            os.replace(temp,folder/name);written.append(name)
        for name in removed:
            target=folder/name;old[name]=target.read_bytes();(backup/name).write_bytes(old[name])
            target.unlink();written.append(name)
    except Exception:
        for name in reversed(written):
            target=folder/name
            if old[name] is None:target.unlink(missing_ok=True)
            else:
                recovery=folder/('.'+name+'.gui-restore-'+uuid.uuid4().hex+'.tmp')
                recovery.write_bytes(old[name]);os.replace(recovery,target)
        raise
    finally:
        for temp in staged.values():temp.unlink(missing_ok=True)
    return folder,backup
