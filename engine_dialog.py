"""Bilingual setup and explicit run preflight for separately licensed engines."""
from pathlib import Path
import hashlib
import json
import platform
import sys
from PySide6 import __version__ as qt_version
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,
    QLineEdit,QPushButton,QDialogButtonBox,QFileDialog,QPlainTextEdit,QComboBox,QMessageBox)
from engine_config import (EngineConfig,binary_kind,normalize_tables,discover,basic_errors,
                           probe_runtime,required_tables,runtime_directories)
from app_paths import documents_root

class EngineDialog(QDialog):
    def __init__(self,owner,first=False):
        super().__init__(owner);self.owner=owner;self.config=None
        self.trx=owner.raw_text;self.setWindowTitle(self.trx('内核与数据设置','Engine and data settings'))
        self.resize(850,560);layout=QVBoxLayout(self);form=QFormLayout();layout.addLayout(form)
        self.fields={}
        rows=(('executable','内核程序','Engine executable'),('tables','材料表目录','Material tables directory'),
              ('runtime','Windows 运行库目录（留空自动识别）','Windows runtime directory (blank = auto)'),
              ('results','结果目录','Results directory'),('distribution','WSL 发行版（留空为默认）','WSL distribution (blank = default)'))
        for key,zh,en in rows:
            edit=QLineEdit(getattr(owner.engine_config,key));self.fields[key]=edit
            if key=='runtime':
                edit.setPlaceholderText(self.trx('例如：内核安装目录下的 ucrt64/bin','For example: ucrt64/bin inside the engine installation'))
            row=QHBoxLayout();row.addWidget(edit,1)
            if key!='distribution':
                b=QPushButton(self.trx('浏览…','Browse…'));b.clicked.connect(lambda checked=False,k=key:self.browse(k));row.addWidget(b)
            form.addRow(self.trx(zh,en),row)
        row=QHBoxLayout();layout.addLayout(row)
        for zh,en,slot in [('搜索常用位置','Search common locations',self.scan_common),
                           ('扫描指定文件夹…','Scan a folder…',self.scan_folder),
                           ('重新检查','Check again',self.check)]:
            b=QPushButton(self.trx(zh,en));b.clicked.connect(slot);row.addWidget(b)
        self.binary_choices=QComboBox();self.table_choices=QComboBox()
        form.addRow(self.trx('发现的内核（请确认）','Detected engines (confirm selection)'),self.binary_choices)
        form.addRow(self.trx('发现的材料目录（请确认）','Detected tables (confirm selection)'),self.table_choices)
        self.binary_choices.activated.connect(lambda i:self.fields['executable'].setText(self.binary_choices.itemData(i)))
        self.table_choices.activated.connect(lambda i:self.fields['tables'].setText(self.table_choices.itemData(i)))
        self.report=QPlainTextEdit();self.report.setReadOnly(True);layout.addWidget(self.report,1)
        note=QLabel(self.trx('内核与材料可位于不同目录。可跳过内核设置，继续编辑和查看已有结果。',
                            'Engine and tables may be in different folders. You may skip setup and keep editing or viewing existing results.'))
        note.setWordWrap(True);layout.addWidget(note)
        box=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        box.button(QDialogButtonBox.StandardButton.Save).setText(self.trx('保存设置','Save settings'))
        box.button(QDialogButtonBox.StandardButton.Cancel).setText(self.trx('暂不配置' if first else '取消','Skip for now' if first else 'Cancel'))
        box.accepted.connect(self.accept);box.rejected.connect(self.reject);layout.addWidget(box)
        if first:self.scan_common()
        else:self.report.setPlainText('\n'.join(basic_errors(self.values())) or self.trx('路径已配置。点击“重新检查”核验运行环境。','Paths configured. Click Check again to verify the runtime.'))

    def values(self):
        values={k:v.text().strip() for k,v in self.fields.items()}
        if values['tables']:values['tables']=str(normalize_tables(values['tables']))
        return EngineConfig(**values)

    def browse(self,key):
        current=self.fields[key].text() or str(Path.home())
        if key=='executable':path,_=QFileDialog.getOpenFileName(self,self.trx('选择内核程序，不是源码','Select the engine executable, not source'),current,'All files (*)')
        else:path=QFileDialog.getExistingDirectory(self,self.trx('选择目录','Select directory'),current)
        if path:self.fields[key].setText(str(normalize_tables(path)) if key=='tables' else path)

    def scan_common(self):
        roots=[Path(sys.executable).parent,Path(__file__).resolve().parent.parent,
               documents_root().parent,Path.home()/'Desktop']
        legacy=self.owner.settings.value('engine/root','')
        if legacy:roots.insert(0,Path(str(legacy)))
        self.scan(roots)

    def scan_folder(self):
        path=QFileDialog.getExistingDirectory(self,self.trx('扫描内核安装目录','Scan engine installation folder'),str(Path.home()))
        if path:self.scan([Path(path)])

    def scan(self,roots):
        self.report.setPlainText(self.trx('正在查找…','Searching…'))
        binaries,tables=discover(roots)
        for key,combo,paths in (('executable',self.binary_choices,binaries),('tables',self.table_choices,tables)):
            current=self.fields[key].text().strip()
            combo.clear();combo.addItem(self.trx('请选择…','Select…'),'')
            for path in paths:combo.addItem(path,path)
            match=next((i for i in range(1,combo.count()) if combo.itemData(i)==current),None)
            if match is None and len(paths)==1:match=1
            if match is not None:
                combo.setCurrentIndex(match)
                self.fields[key].setText(str(normalize_tables(combo.itemData(match))) if key=='tables'
                                         else combo.itemData(match))
        self.report.setPlainText(self.trx('找到内核 {} 个、材料目录 {} 个。请在上方下拉框确认；也可分别浏览任意位置。',
                                         'Found {} engines and {} table directories. Confirm selections above or browse any location.').format(len(binaries),len(tables)))

    def check(self):
        config=self.values();errors=basic_errors(config);lines=list(errors)
        if binary_kind(config.executable)=='windows':
            try:lines.append(self.trx('Windows 运行库搜索目录：\n','Windows runtime search directories:\n')+'\n'.join(map(str,runtime_directories(config))))
            except ValueError:pass  # Already reported by basic_errors.
        if config.tables and (Path(config.tables)/'table1').is_file():
            try:
                from element_picker import read_materials
                lines.append(self.trx('材料条目：','Material entries: ')+str(len(read_materials(Path(config.tables)/'table1'))))
            except (OSError,ValueError) as e:lines.append(str(e));errors.append(str(e))
        if not errors:
            try:lines.append(probe_runtime(config));lines.append(self.trx('运行环境检查通过。','Runtime check passed.'))
            except (OSError,ValueError) as e:lines.append(str(e))
        self.report.setPlainText('\n'.join(lines))

    def accept(self):
        config=self.values()
        if config.tables:
            try:
                from element_picker import read_materials
                read_materials(Path(config.tables)/'table1')
            except (OSError,ValueError) as e:
                self.report.setPlainText(self.trx('材料表读取失败：','Material table error: ')+str(e));return
        if not config.results:config.results=str(documents_root()/'Runs')
        self.config=config;super().accept()

def preflight(owner,config,data,warnings):
    errors=basic_errors(config);details=[];environment_errors=[]
    try:
        from element_picker import read_materials
        available={m.symbol for m in read_materials(Path(config.tables)/'table1')}
        missing=sorted(set(data['symbol'])-available)
        if missing:errors.append(owner.raw_text('材料表中没有这些条目：','Species missing from table1: ')+', '.join(missing))
    except (OSError,ValueError) as e:errors.append(str(e))
    for name in required_tables(data):
        if not (Path(config.tables)/name).is_file():errors.append(owner.raw_text('缺少材料文件：','Missing table file: ')+name)
    if not errors:
        try:details.append(probe_runtime(config))
        except (OSError,ValueError) as e:errors.append(str(e));environment_errors.append(str(e))
    # Probe the selected output location with an automatically removed temporary file.
    if not errors:
        import tempfile
        try:
            Path(config.results).mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryFile(dir=config.results):pass
        except OSError as e:errors.append(owner.raw_text('结果目录不可写：','Results directory is not writable: ')+str(e))
    dialog=QDialog(owner);dialog.setWindowTitle(owner.raw_text('运行前检查','Run preflight'));dialog.resize(800,550)
    layout=QVBoxLayout(dialog);report=QPlainTextEdit();report.setReadOnly(True);layout.addWidget(report)
    rows=[owner.raw_text('输入案例：','Input case: ')+str(owner.source or owner.raw_text('未保存的当前输入','Unsaved current inputs')),
          owner.raw_text('内核程序：','Engine: ')+config.executable,
          owner.raw_text('内核格式：','Engine format: ')+binary_kind(config.executable),
          owner.raw_text('内核版本：未由程序声明（不推测）。','Engine version: not reported (not inferred).'),
          owner.raw_text('材料目录：','Tables: ')+config.tables,
          owner.raw_text('结果目录：','Results: ')+config.results,
          owner.raw_text('WSL 发行版：','WSL distribution: ')+(config.distribution or owner.raw_text('系统默认','System default'))]
    if binary_kind(config.executable)=='windows':
        try:rows.append(owner.raw_text('Windows 运行库搜索目录：\n','Windows runtime search directories:\n')+'\n'.join(map(str,runtime_directories(config))))
        except ValueError:pass
    rows+=['']+details+['']+warnings+['']+errors
    if not errors:rows.append(owner.raw_text('检查通过。将使用当前输入的独立副本开始计算。','Checks passed. Start using a separate copy of the current inputs.'))
    report.setPlainText('\n'.join(rows))
    buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText(owner.raw_text('开始计算','Start calculation'))
    buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(not errors)
    buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
    accepted=dialog.exec()==QDialog.DialogCode.Accepted
    owner.runtime_errors=environment_errors
    owner.update_run_availability(True)
    return accepted

def diagnostic_info(owner):
    config=owner.engine_config;kind=binary_kind(config.executable)
    digest=''
    if kind in ('linux','windows'):
        with Path(config.executable).open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    return {'gui_version':owner.VERSION if hasattr(owner,'VERSION') else '0.9.2',
            'python_version':platform.python_version(),'pyside6_version':qt_version,
            'platform':sys.platform,'architecture':platform.machine(),'frozen':bool(getattr(sys,'frozen',False)),
            'engine_format':kind,'engine_version':'not reported','engine_sha256':digest,
            'wsl_distribution_configured':bool(config.distribution),
            'windows_runtime_directory_configured':bool(config.runtime),
            'table_files_present':{name:(Path(config.tables)/name).is_file() for name in required_tables({})},
            'configuration_issues':len(basic_errors(config))}

def show_about(owner):
    info=diagnostic_info(owner);dialog=QDialog(owner);dialog.setWindowTitle(owner.raw_text('关于与诊断','About and diagnostics'))
    dialog.resize(650,430);layout=QVBoxLayout(dialog);text=QPlainTextEdit();text.setReadOnly(True)
    text.setPlainText('SDTrimSP-2D_GUI v'+info['gui_version']+'\n\n'+json.dumps(info,indent=2,ensure_ascii=False));layout.addWidget(text)
    export=QPushButton(owner.raw_text('导出诊断信息…','Export diagnostics…'));layout.addWidget(export)
    def save():
        path,_=QFileDialog.getSaveFileName(dialog,owner.raw_text('保存诊断信息','Save diagnostics'),str(documents_root()/'diagnostics.json'),'JSON (*.json)')
        if path:
            from input_file_io import atomic_write_text
            atomic_write_text(path,json.dumps(info,indent=2,ensure_ascii=False)+'\n')
    export.clicked.connect(save)
    note=QLabel(owner.raw_text('导出内容不含用户名、目录路径、输入文件或运行日志。','Export excludes usernames, directory paths, input files and run logs.'));note.setWordWrap(True);layout.addWidget(note)
    box=QDialogButtonBox(QDialogButtonBox.StandardButton.Close);box.rejected.connect(dialog.reject);layout.addWidget(box);dialog.exec()
