"""SDTrimSP-2D 中文输入工作台，使用现有 Fortran 内核。"""
from __future__ import annotations
import sys
if '--probe-windows-runtime' in sys.argv:
    from windows_runtime_probe import main as probe_main
    sys.exit(probe_main(sys.argv[sys.argv.index('--probe-windows-runtime')+1:]))
import codecs
import argparse
from datetime import datetime
import math
import numpy as np
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import traceback
import ctypes
from PySide6.QtCore import Qt, QProcess, QProcessEnvironment, QTimer, QUrl, QLockFile, QSettings
from PySide6.QtGui import QDesktopServices, QFont, QFontDatabase, QTextCursor, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QSplitter, QPlainTextEdit,
    QFileDialog, QMessageBox, QScrollArea, QAbstractItemView, QStyle)
import matplotlib
matplotlib.use('qtagg')
from matplotlib import rcParams
rcParams['font.sans-serif']=['Microsoft YaHei','SimHei','DejaVu Sans']
rcParams['axes.unicode_minus']=False
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure as PlotFigure
from matplotlib.patches import Rectangle, Polygon
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
from target_render import add_target_blocks
from case_model import (Figure, Namelist, inspect_input, validate, number, fmt, read_text,
                        LENGTH_KEYS, SCALAR_KEYS, ARRAY_KEYS, REQUIRED, GEOMETRIES,
                        surface_profile, parse_layers)
from element_picker import ElementDialog, NoWheelComboBox
from results_view import ResultsView
from preview_navigation import PreviewNavigation
from i18n import InterfaceLanguage, translated
from compact_toolbar import install_tooltip_delay,icon_button
from mode_hints import ModeComboBox
from target_beam_controls import TargetBeamControls
from help_view import HelpView
from layout_defaults import DefaultSplitter
from target_editor import TargetEditor
from element_colors import element_colormap,tint_species_item,contrast_text
from input_file_io import atomic_write_text,normalized_input_text
from run_progress import RunProgress
from app_paths import documents_root,state_root
from engine_config import EngineConfig,discover,basic_errors,stage_tables,apply_material_overrides,launch_command,engine_environment,external_dll_search
from engine_dialog import EngineDialog,preflight,show_about
import case_model as case_model_module
import element_picker as element_picker_module

ROOT=Path(__file__).resolve().parent.parent
VERSION='1.0.0'
APP_TITLE='SDTrimSP-2D_GUI v'+VERSION
DEFAULT_CASE=documents_root()/'Cases'
UNITS={'Å':1., 'nm':10., 'μm':10000.}
LABELS={
 'geo_x':'横向半宽', 'geo_z':'基底底部（负值）',
 'geo_dx':'横向网格间距', 'geo_dz':'竖向网格间距',
 'x_start':'束斑中心', 'dx_start':'束斑宽度', 'z_start':'入射起始高度',
 'flc':'注量（ions/Å²）','maxhist':'注量步数',
 'ihist_out':'输出间隔（步）','nr_pproj':'每步入射抽样数',
 'ipot':'碰撞势编号','isbv':'表面结合能模型编号','pr_amp':'粗糙振幅 pr_amp','pr_wl':'粗糙周期 pr_wl'}
STYLE='''
QMainWindow {background:#eef2f6;}
QWidget {font-family:"Microsoft YaHei";font-size:10pt;color:#24364b;}
QGroupBox {background:white;border:1px solid #d8e1eb;border-radius:8px;margin-top:16px;padding:12px 9px 9px;}
QGroupBox::title {subcontrol-origin:margin;left:14px;padding:0 5px;color:#136d92;font-weight:bold;}
QLineEdit,QComboBox,QPlainTextEdit {background:white;border:1px solid #c9d5e2;border-radius:4px;padding:5px;}
QPushButton {background:white;border:1px solid #bdcddd;border-radius:5px;padding:7px 11px;}
QPushButton:hover {background:#e4f1f7;border-color:#198bb0;}
QPushButton:disabled {color:#9ba8b7;background:#edf1f5;}
QPushButton#primary {background:#087d9f;color:white;border:0;font-weight:bold;}
QToolButton {border:1px solid transparent;border-radius:4px;padding:4px;background:transparent;}
QToolButton:hover {background:#dcebf3;border-color:#a9c4d5;}
QToolButton:pressed {background:#c2dce9;}
QToolButton:checked {background:#d2eaf1;border:1px solid #69a7bd;}
QToolButton#primaryTool {background:#d1e9e8;border-color:#9cc5c2;}
QToolButton#primaryTool:hover {background:#b5dcd8;}
QTableView {background:white;gridline-color:#d7e0e8;selection-background-color:#b9cede;selection-color:#17364b;}
QTableView::item:selected {background:#b9cede;color:#17364b;}
QTableView::item:selected:!active {background:#b9cede;color:#17364b;}
QTableView::item:focus {border:2px solid #16885d;}
QTableView QLineEdit {background:#d0dfeb;color:#17364b;border:1px solid #16885d;border-radius:0;padding:1px;}
QHeaderView::section {background:#eaf2f7;color:#244c65;padding:7px;border:0;border-bottom:1px solid #cbdce7;}
QTabWidget::pane {border:1px solid #d5dee8;background:white;}
QTabBar::tab {padding:9px 17px;background:#e6edf4;border:0;}
QTabBar::tab:selected {background:white;color:#067a9f;font-weight:bold;}
QLabel#banner {background:#133a54;color:white;border-radius:8px;padding:13px;font-size:17pt;font-weight:bold;}
QLabel#note {color:#61758b;}
'''

def group(title):
    box=QGroupBox(title)
    return box,QVBoxLayout(box)

from input_editing import InputEditing
from new_case import NewCaseActions,initial_inputs
from case_saving import save_input_files
from PySide6.QtGui import QShortcut,QKeySequence

class Window(NewCaseActions,InputEditing,QMainWindow):
    VERSION=VERSION
    def __init__(self,case=None,settings=None):
        super().__init__()
        # 显式加载字体，保证无屏幕渲染检查和本机界面都能显示中文。
        for font in ('msyh.ttc','msyhbd.ttc','segoeui.ttf'):
            path=Path('C:/Windows/Fonts')/font
            if path.exists(): QFontDatabase.addApplicationFont(str(path))
        QApplication.instance().setFont(QFont('Microsoft YaHei',10))
        install_tooltip_delay()
        self.setWindowTitle(APP_TITLE)
        icon_path=Path(__file__).parent/'assets'/'SDTrimSP-2D_GUI.ico'
        if icon_path.exists(): self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1430,920)
        self.settings=settings if settings is not None else QSettings('LocalResearchTools','SDTrimSP2DWorkbench')
        self.engine_config=EngineConfig.load(self.settings,documents_root()/'Runs')
        self.engine_root=Path(str(self.settings.value('engine/root',''))) if self.settings.value('engine/root','') else None
        self.runtime_errors=[]
        self.configure_material_table(self.engine_config.tables)
        self.source=None; self.namelist=None; self.figure=None; self.data=None
        self.factor=1.; self.loading=False; self.dirty=False
        self.raw_pending=set();self.raw_error=None;self.raw_applying=False
        self.process=None; self.run_directory=None; self.log_file=None; self.stop_requested=False
        self.last_export=None
        self.files={}; self.aux_editors={}; self.error_history=[];self.removed_files=set()
        before=Path(__file__).parent/'compatibility-before.json'
        if before.exists():
            try:
                rows=json.loads(read_text(before)); self.error_history.append('0.1版本报错复现（升级前记录）：')
                for row in rows:
                    reason=row.get('import_error') or '；'.join(row.get('validation_errors',[])) or '可导入并通过输入检查'
                    self.error_history.append(row['case']+'：'+reason)
                self.error_history.append('\n0.2版本当前导入记录：')
            except (ValueError,OSError): pass
        self.timer=QTimer(self); self.timer.setSingleShot(True); self.timer.setInterval(450); self.timer.timeout.connect(self.refresh)
        central=QWidget(); outer=QVBoxLayout(central); outer.setContentsMargins(12,6,12,6);outer.setSpacing(5)
        self.header_bar=QWidget(central);self.header_bar.setObjectName('compactHeader')
        actions=QHBoxLayout(self.header_bar);actions.setContentsMargins(0,0,0,0);actions.setSpacing(5)
        outer.addWidget(self.header_bar)
        def button(label,slot,icon,primary=False):
            b=icon_button(self,label,icon,slot,primary)
            actions.addWidget(b);return b
        self.new_button=button('新建案例…（Ctrl+N）',self.new_case,QStyle.StandardPixmap.SP_FileIcon)
        self.new_shortcut=QShortcut(QKeySequence.StandardKey.New,self);self.new_shortcut.activated.connect(self.new_case)
        self.new_case_dialog=None
        self.open_button=button('打开案例…',self.choose_case,QStyle.StandardPixmap.SP_DirOpenIcon)
        self.save_button=button('保存（Ctrl+S）',self.save_current,QStyle.StandardPixmap.SP_DialogSaveButton)
        self.save_as_button=button('另存为…（Ctrl+Shift+S）',self.save_case,QStyle.StandardPixmap.SP_FileDialogNewFolder)
        self.save_shortcut=QShortcut(QKeySequence.StandardKey.Save,self);self.save_shortcut.activated.connect(self.save_current)
        self.save_as_shortcut=QShortcut(QKeySequence.StandardKey.SaveAs,self);self.save_as_shortcut.activated.connect(self.save_case)
        self.check_button=button('检查输入',self.check,QStyle.StandardPixmap.SP_DialogApplyButton)
        self.engine_button=button('内核设置',self.configure_engine,QStyle.StandardPixmap.SP_ComputerIcon)
        self.engine_button.setToolTip('选择外部计算内核目录\n未配置内核时仍可编辑，但不能运行。')
        self.run_button=button('运行当前输入',self.run_case,QStyle.StandardPixmap.SP_MediaPlay,True)
        self.stop_button=button('请求停止',self.stop_run,QStyle.StandardPixmap.SP_MediaStop);self.stop_button.setEnabled(False)
        self.stop_button.setToolTip('请求停止\n内核每10个注量步检查一次，请等待安全结束。')
        self.run_progress=RunProgress(self.header_bar);actions.addWidget(self.run_progress)
        self.results_button=button('打开结果目录',self.open_results,QStyle.StandardPixmap.SP_DirIcon);self.results_button.setEnabled(False)
        actions.addSpacing(8)
        self.info_button=button('案例信息',None,QStyle.StandardPixmap.SP_FileDialogInfoView)
        self.info_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.about_button=button('关于与诊断',lambda:show_about(self),QStyle.StandardPixmap.SP_MessageBoxInformation)
        actions.addSpacing(10)
        self.case_title_label=QLabel('案例标题');actions.addWidget(self.case_title_label)
        self.title_edit=QLineEdit(self.header_bar);self.title_edit.setMinimumWidth(150);self.title_edit.setMaximumWidth(280)
        self.title_edit.setToolTip('案例标题');self.title_edit.setAccessibleName('案例标题');self.case_title_label.setBuddy(self.title_edit)
        self.title_edit.textEdited.connect(self.changed);actions.addWidget(self.title_edit,1)
        actions.addStretch(1)
        self.unit=NoWheelComboBox(); self.unit.addItems(UNITS); self.unit.currentTextChanged.connect(self.change_unit)
        self.length_label=unit_mark=QLabel('长度');unit_mark.setToolTip('显示长度单位');actions.addWidget(unit_mark)
        self.unit.setToolTip('显示长度单位');self.unit.setAccessibleName('显示长度单位');actions.addWidget(self.unit)
        self.language=NoWheelComboBox(); self.language.addItem('中文','zh');self.language.addItem('English','en')
        self.language_label=language_mark=QLabel('语言 / Language');language_mark.setToolTip('语言 / Language');actions.addWidget(language_mark)
        self.language.setToolTip('语言 / Language');self.language.setAccessibleName('语言 / Language');actions.addWidget(self.language)
        # 路径与模式仍随导入更新，详细信息收进悬停提示，不额外占一行。
        self.path_label=QLabel(central);self.path_label.hide()
        self.mode_note=QLabel(central);self.mode_note.hide()
        self.tabs=QTabWidget(); outer.addWidget(self.tabs,1)
        setup=QWidget(); setup_layout=QVBoxLayout(setup)
        splitter=DefaultSplitter(Qt.Orientation.Horizontal,'input');self.setup_splitter=splitter;setup_layout.addWidget(splitter)
        left=QWidget(); left_layout=QVBoxLayout(left); left_layout.setContentsMargins(0,0,8,0)
        box,lay=group('元素');self.elements_box=box;left_layout.addWidget(box)
        self.species=QTableWidget(0,9)
        self.species.setHorizontalHeaderLabels(['元素','束流分数','能量 / eV','入射角 / °','基底分数','浓度上限','原子质量 u','质量密度 g/cm³','原子数密度 atoms/Å³'])
        # Keep engine arrays in their original logical columns; energy and angle are edited in beam settings.
        for column in (2,3):self.species.setColumnHidden(column,True)
        self.species.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.species.horizontalHeader().setStretchLastSection(True)
        self.species.setMinimumHeight(175); self.species.setMaximumHeight(250); self.species.itemChanged.connect(self.changed); lay.addWidget(self.species)
        self.species.setToolTip('点击元素名或“…”选择元素；点击 × 删除，点击 ＋ 新增空白元素。材料属性可直接编辑，仅用于当前运行，不修改原始材料表或案例输入。')
        row=QHBoxLayout(); lay.addLayout(row)
        self.add_species_button=QPushButton('＋');self.add_species_button.setFixedSize(28,26)
        self.add_species_button.setStyleSheet('QPushButton {padding:0;font-size:16pt;}')
        self.add_species_button.setToolTip('添加空白元素');self.add_species_button.setAccessibleName('添加空白元素')
        self.add_species_button.clicked.connect(self.add_species);row.addWidget(self.add_species_button)
        row.addStretch()
        lower=QHBoxLayout(); left_layout.addLayout(lower)
        box,lay=group('网格/基底/束流');self.target_settings_box=box
        self.edits={}; form=QFormLayout(); lay.addLayout(form)
        # 当前几何仍为模型状态；选择入口移到新建案例窗口。
        self.geometry=ModeComboBox('case_geo',self);self.geometry.hide()
        self.geometry_display=QLabel();self.geometry_display.setObjectName('note')
        self.geometry.currentIndexChanged.connect(self.geometry_changed)
        for key in LENGTH_KEYS:
            edit=QLineEdit(); edit.setMinimumWidth(85); edit.setToolTip('输入参数：'+key); edit.textEdited.connect(self.changed); self.edits[key]=edit
        self.target_beam_controls=TargetBeamControls(self,form,LABELS)
        hint=QLabel('总宽 = 2 × geo_x；geo_z 为负值。\n保存时长度统一转换为 Å。'); hint.setWordWrap(True); hint.setObjectName('note'); lay.addWidget(hint)
        box,lay=group('计算设置'); lower.addWidget(box,1)
        form=QFormLayout(); lay.addLayout(form)
        self.dynamic=QCheckBox('动态更新靶材'); self.dynamic.toggled.connect(self.changed); form.addRow(self.dynamic)
        self.mode_controls={}
        for key,label,options in [
            ('case_start','起点模式',[(1,'局部表面起射'),(3,'固定坐标'),(4,'均匀随机束斑'),(2,'相对表面（高级）'),(5,'特殊分布（高级）'),(6,'规则采样（高级）')]),
            ('case_e0','能量模式',[]),
            ('case_alpha','角度模式',[])]:
            combo=ModeComboBox(key) if key in ('case_e0','case_alpha') else NoWheelComboBox()
            if key=='case_start':
                for value,text in options: combo.addItem(str(value)+' · '+text,value)
            combo.currentIndexChanged.connect(self.changed); self.mode_controls[key]=combo; form.addRow(label,combo)
        for key in ('flc','maxhist','ihist_out','nr_pproj'):
            edit=QLineEdit(); edit.setMinimumWidth(85); edit.setToolTip('输入参数：'+key); edit.textEdited.connect(self.changed); self.edits[key]=edit; form.addRow(LABELS[key],edit)
        self.potential_combo=ModeComboBox('ipot');self.binding_combo=ModeComboBox('isbv')
        for key,label,combo in [('ipot','碰撞势',self.potential_combo),('isbv','表面结合能模型',self.binding_combo)]:
            self.mode_controls[key]=combo;combo.currentIndexChanged.connect(self.changed);form.addRow(label,combo)
        left_layout.addStretch()
        scroller=QScrollArea(); scroller.setWidgetResizable(True); scroller.setFrameShape(QScrollArea.Shape.NoFrame); scroller.setWidget(left); splitter.addWidget(scroller)
        right=QWidget(); rl=QVBoxLayout(right); rl.setContentsMargins(7,0,0,0)
        row=QHBoxLayout(); rl.addLayout(row); row.addWidget(QLabel('着色元素'))
        self.color_species=NoWheelComboBox(); self.color_species.currentIndexChanged.connect(self.refresh); row.addWidget(self.color_species); row.addStretch()
        self.show_start=QCheckBox('显示入射起始面'); self.show_start.toggled.connect(self.refresh); row.addWidget(self.show_start)
        self.plot=PlotFigure(figsize=(5,4),layout='none'); self.canvas=FigureCanvasQTAgg(self.plot); self.canvas.setMinimumSize(350,300)
        self.preview_navigation=PreviewNavigation(self); rl.addWidget(self.preview_navigation); rl.addWidget(self.canvas,1)
        self.summary=QLabel(); self.summary.setWordWrap(True); self.summary.setStyleSheet('background:#eaf4f7;padding:10px;border-radius:5px;'); rl.addWidget(self.summary)
        self.check_output=QPlainTextEdit(); self.check_output.setReadOnly(True); self.check_output.setMaximumHeight(150); rl.addWidget(self.check_output)
        splitter.addWidget(right); splitter.setSizes([480,520]); self.tabs.addTab(setup,'参数设置与预览')
        blocks=QWidget(); bl=QVBoxLayout(blocks)
        self.mirror=QCheckBox('关于 x=0 左右镜像'); self.mirror.toggled.connect(self.changed)
        self.with_qu=QCheckBox('每个块单独指定成分'); self.with_qu.toggled.connect(self.changed)
        self.blocks=QTableWidget(); self.blocks.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.blocks.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.blocks.itemChanged.connect(self.changed); bl.addWidget(self.blocks,1)
        row=QHBoxLayout(); bl.addLayout(row)
        for label,slot in [('添加块',self.add_block),('复制选中块',self.duplicate_blocks),('删除选中块',self.remove_blocks)]:
            b=QPushButton(label); b.clicked.connect(slot); row.addWidget(b)
        row.addStretch()
        self.target_editor=TargetEditor(self,self.target_settings_box)
        self.tabs.addTab(self.target_editor,'靶绘制')
        self.blocks_page=blocks
        self.tabs.addTab(self.blocks_page,'二维结构块')
        advanced=QWidget(); al=QVBoxLayout(advanced)
        self.extra_table=QTableWidget(0,2); self.extra_table.setHorizontalHeaderLabels(['参数名（只读）','值 / Fortran 表达式'])
        self.extra_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
        self.extra_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.extra_table.itemChanged.connect(self.changed); al.addWidget(self.extra_table,1)
        self.tabs.addTab(advanced,'高级参数')
        self.files_page=QWidget(); file_layout=QVBoxLayout(self.files_page)
        self.aux_tabs=QTabWidget();file_layout.addWidget(self.aux_tabs,1)
        self.tri_preview=QPlainTextEdit();self.tri_preview.setReadOnly(False);self.tri_preview.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.fig_preview=QPlainTextEdit();self.fig_preview.setReadOnly(False);self.fig_preview.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.init_raw_controls(file_layout)
        self.tabs.addTab(self.files_page,'输入文件')
        self.log=QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(6000); self.tabs.addTab(self.log,'运行日志')
        self.results_view=ResultsView(self);self.tabs.addTab(self.results_view,'结果绘图')
        self.help_view=HelpView(self);self.tabs.addTab(self.help_view,'使用说明')
        self.setCentralWidget(central);self.setStyleSheet(STYLE)
        if case is None:
            self.create_new_case(initial_inputs('New_case','Ar','W',400.,200.,25.,25.,100.,0.,500.));self.dirty=False
        else:self.load_case(Path(case))
        self.ui_language=str(self.settings.value('language','zh'))
        if self.ui_language not in ('zh','en'):self.ui_language='zh'
        self.interface_language=InterfaceLanguage(self)
        QApplication.instance().installEventFilter(self.interface_language)
        self.language.setCurrentIndex(self.language.findData(self.ui_language))
        self.language.currentIndexChanged.connect(self.change_language)
        self.change_language()
        if not self.settings.value('setup/v090_seen',False,type=bool):
            QTimer.singleShot(300,self.first_setup)

    def change_language(self,*args):
        self.ui_language=self.language.currentData()
        self.settings.setValue('language',self.ui_language)
        self.interface_language.apply(self)
        self.run_progress.set_language(self.ui_language)
        for combo in (self.geometry,self.mode_controls['case_e0'],self.mode_controls['case_alpha'],self.potential_combo,self.binding_combo):
            combo.set_language(self.ui_language)
        self.help_view.set_language(self.ui_language)
        self.engine_button.setToolTip(self.raw_text('内核与数据设置：分别选择程序、材料表和结果目录。','Engine and data settings: select executable, tables and results separately.'))
        self.about_button.setToolTip(self.raw_text('关于与诊断','About and diagnostics'))
        self.refresh();self.results_view.redraw()

    def configure_material_table(self,directory):
        table=Path(directory)/'table1' if directory else None
        element_picker_module.TABLE_PATH=table
        case_model_module.configure_material_table(table)
        try:self.material_lookup={m.symbol:m for m in element_picker_module.read_materials(table)}
        except (OSError,ValueError):self.material_lookup={}
        if hasattr(self,'species'):
            for row in range(self.species.rowCount()):
                if self.cell(self.species,row,0) and any(not self.cell(self.species,row,col) for col in (6,7,8)):
                    self.set_material_cells(row,self.cell(self.species,row,0))

    def set_material_cells(self,row,symbol,values=None):
        material=self.material_lookup.get(symbol) if values is None else None
        if values is None:
            values=(material.mass,material.density,material.atomic_density) if material else ('','','')
        for column,value in zip((6,7,8),values):
            self.set_cell(self.species,row,column,'' if value is None else fmt(value) if isinstance(value,(int,float)) else value)

    def first_setup(self):
        self.settings.setValue('setup/v090_seen',True)
        self.configure_engine(first=True)

    def configure_engine(self,checked=False,first=False):
        if self.process:
            QMessageBox.information(self,self.raw_text('计算运行中','Calculation running'),self.raw_text('请等待计算结束再更改内核或材料设置。','Wait until the calculation ends before changing engine or table settings.'));return
        dialog=EngineDialog(self,first)
        if dialog.exec()==EngineDialog.DialogCode.Accepted:
            self.engine_config=dialog.config;self.engine_config.save(self.settings)
            self.configure_material_table(self.engine_config.tables)
            self.runtime_errors=[];self.refresh()
            self.statusBar().showMessage(self.raw_text('设置已保存，运行时将重新检查。','Settings saved. Preflight will check them again before running.'),8000)

    def update_run_availability(self,inputs_valid):
        issues=basic_errors(self.engine_config)+self.runtime_errors
        self.run_button.setEnabled(inputs_valid and not issues and self.process is None)
        self.run_button.setToolTip(self.raw_text('运行当前输入','Run current inputs') if not issues else
            self.raw_text('仅编辑模式。点击“内核设置”：\n','Editing mode. Open Engine settings:\n')+'\n'.join(issues))

    def changed(self,*args):
        if not self.loading: self.dirty=True; self.timer.start()

    def geometry_changed(self,*args):
        if self.loading:return
        if hasattr(self,'target_editor'):self.target_editor.profile_editor.geometry_changed()
        else:self.changed()

    def set_auxiliary_file(self,name,text):
        """更新内存附件和文本页；实际落盘仍走原来的保存/备份路径。"""
        self.removed_files.discard(name)
        self.files[name]=text
        editor=self.aux_editors.get(name)
        if editor is None:
            editor=QPlainTextEdit();editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
            self.aux_editors[name]=editor;self.aux_tabs.addTab(editor,name);editor.textChanged.connect(lambda n=name:self.raw_edited(n))
        blocked=editor.blockSignals(True)
        editor.setPlainText(text);editor.document().setModified(False);editor.blockSignals(blocked)

    def set_cell(self,table,row,col,value):
        item=QTableWidgetItem(str(value))
        if table is self.species and col==0:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            item.setToolTip('点击选择元素 / 同位素 / 材料条目');tint_species_item(item,str(value))
        elif table is self.species and col==5:
            item.setToolTip(translated('qu_max：动态靶中该组分允许达到的最高原子分数，范围 0～1。1 表示不设有限上限；当前内核最多支持两个 0<qu_max<1 的组分。',getattr(self,'ui_language','zh')))
        table.setItem(row,col,item)
        if table is self.species and col==0:self.set_species_buttons(row,item)

    def set_species_buttons(self,row,item):
        old=self.species.cellWidget(row,0)
        if old is not None:old.hide()
        holder=QWidget();layout=QHBoxLayout(holder);layout.setContentsMargins(2,1,2,1);layout.setSpacing(3)
        holder.setObjectName('speciesCell')
        color=item.background().color().name()
        holder.setStyleSheet('QWidget#speciesCell {background:'+color+';}')
        remove=QPushButton('×');remove.setObjectName('speciesRemove');remove.setFixedSize(24,24)
        remove.setStyleSheet('QPushButton {padding:0;font-size:15pt;}')
        remove.setToolTip(translated('删除此元素',getattr(self,'ui_language','zh')));remove.setAccessibleName(remove.toolTip())
        remove.setEnabled(self.species.rowCount()>1)
        remove.clicked.connect(lambda checked=False:self.remove_species(self.species.row(item)))
        select=QPushButton(item.text() or '...');select.setObjectName('speciesSelect')
        select.setToolTip(translated('点击选择元素 / 同位素 / 材料条目',getattr(self,'ui_language','zh')));select.setAccessibleName(select.toolTip())
        select.setStyleSheet('QPushButton {background:'+color+';padding:1px 5px;}')
        select.clicked.connect(lambda checked=False:self.choose_species(self.species.row(item)))
        layout.addWidget(remove);layout.addWidget(select,1);self.species.setCellWidget(row,0,holder)

    def sync_species_buttons(self):
        for row in range(self.species.rowCount()):
            holder=self.species.cellWidget(row,0)
            if holder:
                holder.findChild(QPushButton,'speciesRemove').setEnabled(self.species.rowCount()>1)
        self.add_species_button.setEnabled(self.species.rowCount()<8)

    def cell(self,table,row,col):
        item=table.item(row,col)
        return item.text().strip() if item else ''

    def load_case(self,path,overrides=None):
        path=Path(path) if path is not None else None
        if path is not None and path.is_file():path=path.parent
        success=False
        same_case=self.raw_applying and not getattr(self,'reset_raw_history',False)
        try:
            overrides=overrides or {}
            text=overrides['tri.inp'] if 'tri.inp' in overrides else read_text(path/'tri.inp'); nl,d=inspect_input(text)
            files={p.name:read_text(p) for p in path.iterdir() if p.is_file() and p.suffix.lower()=='.inp' and p.name.lower()!='tri.inp'} if path is not None else {}
            files.update({name:content for name,content in overrides.items() if name!='tri.inp'})
            if same_case:
                files={name:text for name,text in files.items() if name not in self.removed_files}
            else:self.removed_files.clear()
            fig=Figure.parse(files.get('fig.inp',''),int(d['ncp'])) if d['case_geo']==26 else None
            self.raw_pending.clear();self.raw_error=None
            preserved={self.cell(self.species,i,0):tuple(self.cell(self.species,i,j) for j in (6,7,8))
                       for i in range(self.species.rowCount())} if same_case else {}
            self.loading=True; self.source=path.resolve() if path is not None else None; self.namelist=nl; self.data=d; self.figure=fig
            self.files=files
            self.title_edit.setText(text.splitlines()[0]); self.species.setRowCount(int(d['ncp']))
            for i in range(int(d['ncp'])):
                for j,k in enumerate(ARRAY_KEYS): self.set_cell(self.species,i,j,d[k][i] if k=='symbol' else fmt(d[k][i]))
                symbol=d['symbol'][i]
                self.set_material_cells(i,symbol,preserved.get(symbol))
            for k in LENGTH_KEYS: self.edits[k].setText(fmt(d[k]/self.factor))
            for k in ('flc','maxhist','ihist_out','nr_pproj'): self.edits[k].setText(fmt(d[k]))
            self.dynamic.setChecked(bool(d['tar_dynamic'])); self.geometry.setCurrentIndex(self.geometry.findData(int(d['case_geo'])))
            if self.geometry.currentIndex()<0:
                self.geometry.addItem(str(int(d['case_geo']))+' · 参数保留模式',int(d['case_geo'])); self.geometry.setCurrentIndex(self.geometry.count()-1)
            for key,combo in self.mode_controls.items():
                index=combo.findData(int(d[key]))
                if index<0: combo.addItem(str(int(d[key]))+' · 保留输入',int(d[key])); index=combo.count()-1
                combo.setCurrentIndex(index)
            self.mirror.setChecked(bool(fig.mirror) if fig else True); self.with_qu.setChecked(bool(fig.with_qu) if fig else True)
            self.blocks.setColumnCount(4+int(d['ncp'])); self.blocks.setRowCount(len(fig.rows) if fig else 0)
            if fig:
                for i,r in enumerate(fig.rows):
                    for j in range(4+int(d['ncp'])):
                        v=r[j] if j<len(r) else d['qu_tar'][j-4]
                        self.set_cell(self.blocks,i,j,fmt(v/self.factor if j<4 else v))
            self.update_headers(); self.color_species.clear(); self.color_species.addItems(d['symbol'])
            self.color_species.setCurrentIndex(d['symbol'].index('W') if 'W' in d['symbol'] else 0)
            self.path_label.setText('源案例：'+str(self.source) if self.source is not None else self.raw_text('新建案例（内存草稿）：','New case (in-memory draft): ')+self.title_edit.text()); self.dirty=False
            extras=[key for key in nl.fields if key not in REQUIRED and key!='tttt']
            self.extra_table.setRowCount(len(extras))
            for row,key in enumerate(extras):
                self.set_cell(self.extra_table,row,0,key)
                self.extra_table.item(row,0).setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable)
                self.set_cell(self.extra_table,row,1,nl.raw(key))
            old_editors=self.aux_editors.copy() if same_case else {}
            self.aux_tabs.clear()
            for name,editor in self.aux_editors.items():
                if name not in old_editors:editor.deleteLater()
            self.aux_editors={}
            self.aux_tabs.addTab(self.tri_preview,'tri.inp')
            if d['case_geo']==26 or 'fig.inp' in files:self.aux_tabs.addTab(self.fig_preview,'fig.inp')
            for name,content in sorted(files.items()):
                if name=='fig.inp':continue
                editor=old_editors.pop(name,None)
                if editor is None:
                    editor=QPlainTextEdit();editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
                    editor.textChanged.connect(lambda n=name:self.raw_edited(n))
                if editor.toPlainText()!=content:editor.setPlainText(content)
                editor.document().setModified(False)
                self.aux_tabs.addTab(editor,name); self.aux_editors[name]=editor
            for editor in old_editors.values():editor.deleteLater()
            self.error_history.append('成功载入：'+str(self.source)+'；几何 '+str(int(d['case_geo'])))
            self.statusBar().showMessage('案例已导入；原输入文件未修改。');success=True
        except Exception as e:
            self.error_history.append('导入失败：'+str(path)+'\n'+str(e))
            QMessageBox.warning(self,'无法导入',str(e))
        finally: self.loading=False
        if self.namelist: self.refresh()
        return success

    def update_headers(self):
        self.sync_species_buttons()
        symbols=[self.cell(self.species,i,0) for i in range(self.species.rowCount())]
        self.blocks.setHorizontalHeaderLabels(['x1','x2','z1','z2']+symbols)
        for j in range(4,self.blocks.columnCount()): self.blocks.setColumnHidden(j,not self.with_qu.isChecked())

    def collect(self):
        if not self.namelist: raise ValueError('尚未导入可编辑的案例。')
        extensions=self.extra_updates()
        effective,base=inspect_input(self.namelist.patch(extensions))
        d=dict(base); count=self.species.rowCount(); d['ncp']=count
        # Omitted arrays follow the edited species count, not the source ncp.
        # Explicit arrays are synchronized by species_dependencies and validated.
        for key,default in (('dns_0',-1.),('qu_clust',0.)):
            if key not in effective.fields:d[key]=[default]*count
        for j,k in enumerate(ARRAY_KEYS): d[k]=[self.cell(self.species,i,j) if k=='symbol' else number(self.cell(self.species,i,j)) for i in range(count)]
        def optional_material_number(text):return number(text) if text else None
        d['_material_overrides']=[{'symbol':self.cell(self.species,i,0),
            'mass':optional_material_number(self.cell(self.species,i,6)),
            'density':optional_material_number(self.cell(self.species,i,7)),
            'atomic_density':optional_material_number(self.cell(self.species,i,8))} for i in range(count)]
        if any(not symbol for symbol in d['symbol']):
            raise ValueError(translated('请点击空白元素行的“…”选择元素。',getattr(self,'ui_language','zh')))
        for k in LENGTH_KEYS: d[k]=number(self.edits[k].text())*self.factor
        for k in ('flc','maxhist','ihist_out','nr_pproj'): d[k]=number(self.edits[k].text())
        d['case_geo']=self.geometry.currentData(); d['tar_dynamic']=self.dynamic.isChecked(); rows=[]
        for key,combo in self.mode_controls.items(): d[key]=combo.currentData()
        d['_files']=self.current_files()
        if d['case_geo']==26:
            for i in range(self.blocks.rowCount()):
                r=[number(self.cell(self.blocks,i,j))*self.factor for j in range(4)]
                if self.with_qu.isChecked(): r += [number(self.cell(self.blocks,i,j)) for j in range(4,4+count)]
                rows.append(r)
            old=self.figure
            fig=Figure(int(self.mirror.isChecked()),int(self.with_qu.isChecked()),rows,old.original if old else '',old.baseline if old else (),old.tail if old else '')
        else: fig=None
        return d,fig

    def extra_updates(self):
        return {self.cell(self.extra_table,i,0):self.cell(self.extra_table,i,1) for i in range(self.extra_table.rowCount())}

    def current_files(self):
        return {name:(self.aux_editors[name].toPlainText() if name in self.aux_editors and self.aux_editors[name].document().isModified() else content)
                for name,content in self.files.items()}

    def render_inputs(self,d,fig):
        updates={'ncp':str(d['ncp'])}
        for k in LENGTH_KEYS+SCALAR_KEYS: updates[k]=('.true.' if d[k] else '.false.') if k=='tar_dynamic' else fmt(d[k])
        for k in ARRAY_KEYS: updates[k]=', '.join(('"'+v+'"') if k=='symbol' else fmt(v) for v in d[k])
        updates.update(self.extra_updates())
        return self.namelist.patch(updates,self.title_edit.text()),fig.render() if fig else None

    def refresh(self,*args):
        if self.loading or not self.namelist: return
        self.timer.stop()
        errors=[]
        try:
            d,fig=self.collect();self.target_beam_controls.sync(d);self.update_headers();selected=self.color_species.currentText()
            if [self.color_species.itemText(i) for i in range(self.color_species.count())]!=d['symbol']:
                self.color_species.blockSignals(True); self.color_species.clear(); self.color_species.addItems(d['symbol'])
                self.color_species.setCurrentIndex(max(0,self.color_species.findText(selected))); self.color_species.blockSignals(False)
            errors,warnings,stats=validate(d,fig)
            self.mode_note.setText(GEOMETRIES.get(int(d['case_geo']),'高级几何')+' · '+('动态' if d['tar_dynamic'] else '静态'))
            for key in ('pr_amp','pr_wl'): self.edits[key].setEnabled(int(d['case_geo']) in (24,25,27))
            self.edits['z_start'].setEnabled(int(d['case_start'])!=1)
            messages=['错误：'+x for x in errors]+['提示：'+x for x in warnings]
            self.check_output.setPlainText('\n'.join(messages) if messages else '输入检查通过；计算结果仍需验证收敛与物理适用性。')
            self.check_output.setStyleSheet('color:#ad3434;' if errors else 'color:#285d58;')
            tri,fig_text=self.render_inputs(d,fig);self.update_raw_previews(tri,fig_text)
            if stats:
                self.summary.setText(f"总宽 {fmt(2*d['geo_x']/self.factor)} {self.unit.currentText()}  ·  基底厚 {fmt(abs(d['geo_z'])/self.factor)} {self.unit.currentText()}\n"
                    f"基础网格 {stats['nx']} × {stats['nz']} = {stats['cells']:,}  ·  入射抽样 {stats['histories']:,}\n"
                    f"总注量 {fmt(d['flc'])} ions/Å²（{d['flc']*1e16:.3g} ions/cm²）")
                self.draw(d,fig,stats)
                self.target_editor.sync(d,fig,stats)
            self.save_button.setEnabled(not errors); self.update_run_availability(not errors)
        except Exception as e:
            errors=[str(e)]
            self.check_output.setPlainText('输入尚不完整：'+str(e)); self.save_button.setEnabled(False); self.run_button.setEnabled(False)
        self.save_as_button.setEnabled(self.save_button.isEnabled())
        if hasattr(self,'interface_language'):
            self.interface_language.apply(self)
            self.check_output.setPlainText(translated(self.check_output.toPlainText(),self.ui_language))
        language=getattr(self,'ui_language','zh')
        self.info_button.setToolTip(translated('案例信息',language)+'\n'+self.path_label.text()+'\n'+self.mode_note.text()+'\nSDTrimSP-2D 3.01')
        self.target_editor.report_validation_errors(errors)
        # Keep the persistent status compact; detailed errors belong to the timed overlay.
        note=translated(errors[0],language)[:140] if errors else '\n'.join(line[:140] for line in self.check_output.toPlainText().splitlines()[:2])
        self.target_editor.validation_label.setText(note)
        self.target_editor.validation_label.setToolTip(self.check_output.toPlainText())

    def draw(self,d,fig,stats,plot=None,canvas=None,editor=False):
        plot=self.plot if plot is None else plot;canvas=self.canvas if canvas is None else canvas
        english=getattr(self,'ui_language','zh')=='en'
        preview=not editor and plot is self.plot and canvas is self.canvas
        if preview:self.preview_navigation.toolbar.capture_view()
        plot.clear(); ax=plot.add_axes(self.preview_navigation.RESULTS_AXES_BOUNDS) if preview else plot.add_subplot(111)
        idx=max(0,self.color_species.currentIndex()); cmap=self.initial_gradients.colormap(d['symbol'][idx]); f=self.factor
        mode=int(d['case_geo'])
        if mode==28:
            from target_inputs import cylinder_schematic
            xx,zz,solid,radius=cylinder_schematic(d)
            field=np.ma.masked_where(~solid,np.full(solid.shape,d['qu_tar'][idx]))
            ax.pcolormesh(xx/f,zz/f,field,cmap=cmap,vmin=0,vmax=1,shading='flat',rasterized=True)
            ax.set_aspect('equal');ax.set_xlabel('x / '+self.unit.currentText());ax.set_ylabel('z / '+self.unit.currentText())
            ax.set_title(('Specialized geometry 28: grid-selection schematic, R=' if english else '专用几何 28：网格筛选示意，R=')+fmt(radius/f)+' '+self.unit.currentText(),fontsize=10)
            if preview:self.preview_navigation.unavailable(ax)
            canvas.draw_idle();return ax
        if mode not in GEOMETRIES:
            ax.text(.5,.5,'该几何仅保留输入参数\n暂不提供结构预览',ha='center',va='center',transform=ax.transAxes)
            ax.set_axis_off()
            if preview:self.preview_navigation.unavailable(ax)
            canvas.draw_idle(); return ax
        try:sx,sz=surface_profile(d,d['_files'])
        except ValueError as error:
            if mode not in (24,25):raise
            ax.text(.5,.5,('Profile unavailable: ' if english else '轮廓不可用：')+str(error),ha='center',va='center',wrap=True,transform=ax.transAxes)
            ax.set_xlim(-d['geo_x']/f,d['geo_x']/f);ax.set_ylim(d['geo_z']/f,max(1.,abs(d['geo_z'])/f*.25))
            ax.set_xlabel(f'x / {self.unit.currentText()}');ax.set_ylabel(f'z / {self.unit.currentText()}')
            if preview:self.preview_navigation.unavailable(ax)
            canvas.draw_idle();return ax
        layered=d.get('iq0',0)>0 or d.get('iq0_surf',0)==1 or (d.get('l_clust') and d.get('l_clust_read'))
        if layered:
            from target_inputs import composition_field,composition_mesh
            xx,zz=composition_mesh(d,fig)
            xc=(xx[:-1]+xx[1:])/2;zc=(zz[:-1]+zz[1:])/2
            X,Z=np.meshgrid(xc,zc)
            composition=composition_field(d,fig,X,Z,idx)
            ax.pcolormesh(xx/f,zz/f,composition,cmap=cmap,vmin=0,vmax=1,shading='flat',rasterized=True)
        else:
            vertices=[(-d['geo_x']/f,d['geo_z']/f),(d['geo_x']/f,d['geo_z']/f)]
            vertices+=list(zip(sx[::-1]/f,sz[::-1]/f))
            patch=Polygon(vertices,closed=True,facecolor=cmap(float(d['qu_tar'][idx])),edgecolor='#536779',linewidth=.7)
            patch._target_fraction=float(d['qu_tar'][idx]);ax.add_patch(patch)
            ax.text(0,d['geo_z']/f*.55,('Matrix' if d.get('l_clust') else 'Substrate') if english else ('基体' if d.get('l_clust') else '基底'),ha='center',va='center',color=contrast_text(cmap(float(d['qu_tar'][idx]))),fontsize=10)
        ax.plot(sx/f,sz/f,color='#526a7d',lw=.7)
        if fig and not layered:
            add_target_blocks(ax,fig,d,idx,f,cmap)
        width=2*d['geo_x']/f; top=stats['top']/f; gap=max(width*.18,top*.12,1e-6); upper=top+gap
        if self.show_start.isChecked() and int(d['case_start'])!=1:
            upper=max(upper,d['z_start']/f+gap*.1); a=(d['x_start']-stats['beam_width']/2)/f; b=(d['x_start']+stats['beam_width']/2)/f
            ax.plot([a,b],[d['z_start']/f]*2,color='#df6942',ls='--',lw=1.3,label='入射起始面'); ax.legend(loc='upper right',fontsize=8)
        beam=self.target_beam_controls.species.currentData()
        if beam is None or not 0<=beam<len(d['qu_beam']) or d['qu_beam'][beam]<=0:
            beam=next((i for i,q in enumerate(d['qu_beam']) if q>0),0)
        angle=d['alpha0'][beam]*math.pi/180
        length=min(gap*.8,width*.18); beam_center=d['x_start']/f; x0=beam_center+length*math.sin(angle); z0=top+gap*.8
        ax.annotate('',xy=(beam_center,z0-length*math.cos(angle)),xytext=(x0,z0),arrowprops={'arrowstyle':'-|>','color':'#d75e36','lw':2})
        ax.text(x0,z0+gap*.08,f"{d['symbol'][beam]}  {fmt(d['e0_beam'][beam])} eV / {fmt(d['alpha0'][beam])}°",fontsize=8,ha='center',color='#a74427')
        ax.axhline(0,color='#657b8e',lw=.6,ls=':'); ax.axvline(0,color='#9aabba',lw=.5,ls=':')
        ax.set_xlim(-d['geo_x']/f-width*.04,d['geo_x']/f+width*.04); ax.set_ylim(d['geo_z']/f-width*.04,upper)
        ax.set_aspect('auto' if editor else 'equal',adjustable='box'); ax.set_xlabel(f'x / {self.unit.currentText()}'); ax.set_ylabel(f'z / {self.unit.currentText()}')
        title='初始轮廓 / 分层示意（内核按网格建靶）' if layered or mode in (24,25,27) else '一维靶（横向为单网格）' if mode==10 else '初始靶材截面'
        if d.get('l_clust') and not d.get('l_clust_read'): title='成分示意（内置团簇固定布局由内核生成，未显示）'
        if english:
            title='Initial profile / layer schematic (kernel builds the target on its mesh)' if layered or mode in (24,25,27) else '1D target (single lateral cell)' if mode==10 else 'Initial target cross section'
            if d.get('l_clust') and not d.get('l_clust_read'):title='Composition schematic (kernel-defined clusters not shown)'
        ax.set_title(title,fontsize=10)
        if not editor:
            cb=plot.colorbar(ScalarMappable(norm=Normalize(0,1),cmap=cmap),cax=plot.add_axes(self.preview_navigation.COLORBAR_BOUNDS)) if preview else plot.colorbar(ScalarMappable(norm=Normalize(0,1),cmap=cmap),ax=ax,shrink=.72,pad=.04)
            cb.set_label(d['symbol'][idx]+(' atomic fraction' if english else ' 原子分数'),fontsize=9)
            plot._initial_colorbar=cb
        else:
            ax.set_title('')
            ax.tick_params(top=True,right=True,labeltop=True,labelright=True,direction='out')
        ax.tick_params(labelsize=8)
        ax.spines[['top','right']].set_visible(editor)
        if preview:self.preview_navigation.update_preview(ax,d,fig,sx,sz,idx)
        canvas.draw_idle();return ax

    def change_unit(self,label):
        if self.loading: return
        new=UNITS[label]; ratio=self.factor/new
        try:
            converted={k:fmt(number(self.edits[k].text())*ratio) for k in LENGTH_KEYS}
            cells={(i,j):fmt(number(self.cell(self.blocks,i,j))*ratio) for i in range(self.blocks.rowCount()) for j in range(4)}
        except ValueError:
            self.unit.blockSignals(True); self.unit.setCurrentText(next(k for k,v in UNITS.items() if v==self.factor)); self.unit.blockSignals(False)
            QMessageBox.warning(self,'无法切换单位','请先补全长度数值，再切换单位。'); return
        self.loading=True
        for k,v in converted.items(): self.edits[k].setText(v)
        for (i,j),v in cells.items(): self.set_cell(self.blocks,i,j,v)
        self.factor=new; self.loading=False; self.refresh()

    def choose_species(self,row=None):
        if self.raw_pending and not self.apply_raw_edits():return
        if row is None: row=max(0,self.species.currentRow())
        if not 0<=row<self.species.rowCount(): return
        self.species.setCurrentCell(row,0)
        try: dialog=ElementDialog(self.cell(self.species,row,0),self)
        except (OSError,ValueError) as error:
            QMessageBox.warning(self,'材料表读取失败',str(error)); return
        if dialog.exec()==ElementDialog.DialogCode.Accepted and dialog.selected_symbol:
            if dialog.selected_symbol!=self.cell(self.species,row,0):
                try:
                    from species_dependencies import plan_species_change,commit_species_plan
                    plan=plan_species_change(self,'replace',row,dialog.selected_symbol)
                except ValueError as e:
                    QMessageBox.warning(self,self.raw_text('元素依赖','Species dependencies'),str(e));return
                commit_species_plan(self,plan)
                self.set_cell(self.species,row,0,dialog.selected_symbol)
                self.set_material_cells(row,dialog.selected_symbol)
                self.refresh()

    def add_species(self):
        if self.raw_pending and not self.apply_raw_edits():return
        if self.species.rowCount()>=8: QMessageBox.information(self,'元素数量','试用版最多支持8种元素。'); return
        try:
            if any(not self.cell(self.species,i,0) for i in range(self.species.rowCount())):raise ValueError(self.raw_text('请先选择空白行的元素。','Choose the species for the blank row first.'))
            from species_dependencies import plan_species_change,commit_species_plan
            plan=plan_species_change(self,'add')
        except ValueError as e:
            QMessageBox.warning(self,self.raw_text('元素依赖','Species dependencies'),str(e));return
        commit_species_plan(self,plan)
        self.loading=True; i=self.species.rowCount(); self.species.insertRow(i)
        for j,v in enumerate(['',0,0,0,0,1]): self.set_cell(self.species,i,j,v)
        self.set_material_cells(i,'')
        col=self.blocks.columnCount(); self.blocks.setColumnCount(col+1)
        for row in range(self.blocks.rowCount()): self.set_cell(self.blocks,row,col,0)
        self.loading=False;self.update_headers(); self.changed(); self.species.setCurrentCell(i,0)

    def remove_species(self,row=None):
        if self.raw_pending and not self.apply_raw_edits():return
        i=self.species.currentRow() if row is None else row
        if not 0<=i<self.species.rowCount() or self.species.rowCount()<=1: return
        try:
            from species_dependencies import plan_species_change,commit_species_plan
            plan=plan_species_change(self,'remove',i)
        except ValueError as e:
            QMessageBox.warning(self,self.raw_text('元素依赖','Species dependencies'),str(e));return
        commit_species_plan(self,plan)
        widget=self.species.cellWidget(i,0)
        if widget is not None:widget.hide()
        self.loading=True; self.species.removeRow(i); self.blocks.removeColumn(4+i); self.loading=False;self.update_headers(); self.changed()

    def add_block(self):
        self.loading=True; i=self.blocks.rowCount(); self.blocks.insertRow(i)
        for j in range(self.blocks.columnCount()): self.set_cell(self.blocks,i,j,'' if j<4 else self.cell(self.species,j-4,4))
        self.loading=False; self.changed(); self.blocks.setCurrentCell(i,0); self.blocks.editItem(self.blocks.item(i,0))

    def selected_rows(self): return sorted({i.row() for i in self.blocks.selectedIndexes()})

    def duplicate_blocks(self):
        rows=self.selected_rows(); self.loading=True
        for row in rows:
            i=self.blocks.rowCount(); self.blocks.insertRow(i)
            for j in range(self.blocks.columnCount()): self.set_cell(self.blocks,i,j,self.cell(self.blocks,row,j))
        self.loading=False; self.changed()

    def remove_blocks(self):
        self.loading=True
        for i in reversed(self.selected_rows()): self.blocks.removeRow(i)
        self.loading=False; self.changed()

    def choose_case(self):
        if self.dirty and QMessageBox.question(self,'切换案例','当前编辑尚未另存，是否放弃这些编辑并打开其他案例？')!=QMessageBox.StandardButton.Yes: return
        p=QFileDialog.getExistingDirectory(self,'选择含 tri.inp 的案例目录',str(self.source or DEFAULT_CASE))
        if p: self.load_case(Path(p))

    def checked_inputs(self):
        if not self.apply_raw_edits():raise ValueError(self.raw_error or '文本修改未能应用。')
        d,fig=self.collect(); errors,warnings,stats=validate(d,fig)
        if errors: raise ValueError('\n'.join(errors))
        tri,figtext=self.render_inputs(d,fig)
        return tri,figtext,warnings

    def check(self):
        self.refresh()
        try:
            tri,fig,warnings=self.checked_inputs(); QMessageBox.information(self,'输入检查','未发现当前检查范围内的输入错误。'+('\n\n提示：\n'+'\n'.join(warnings) if warnings else ''))
        except Exception as e: QMessageBox.warning(self,'需要修正',str(e))

    def write_case(self,destination):
        tri,figtext,warnings=self.checked_inputs(); destination=Path(destination).resolve()
        if destination.exists(): raise ValueError('为保护已有案例，请使用一个尚不存在的新文件夹名称。')
        destination.parent.mkdir(parents=True,exist_ok=True); staging=Path(tempfile.mkdtemp(prefix='.sd2d-staging-',dir=destination.parent))
        try:
            for name,content in self.current_files().items():
                atomic_write_text(staging/name,content)
            atomic_write_text(staging/'tri.inp',tri)
            if figtext is not None: atomic_write_text(staging/'fig.inp',figtext)
            if not (staging/'stop_run.inp').exists(): atomic_write_text(staging/'stop_run.inp','0\n',encoding='ascii')
            staging.rename(destination)
        except Exception:
            shutil.rmtree(staging,ignore_errors=True); raise
        return destination

    def adopt_saved_case(self,out):
        out=Path(out).resolve()
        previous=self.raw_applying;self.raw_applying=True
        try:self.load_case(out)
        finally:self.raw_applying=previous
        self.removed_files.clear();self.last_export=out;self.dirty=False
        self.target_editor.select_cells(self.target_editor.selected_cells,self.target_editor.active_cell)

    def save_current(self):
        if self.source is None:return self.save_case()
        try:
            out,backup=save_input_files(self);self.adopt_saved_case(out)
            message=self.raw_text('已保存当前案例：','Saved current case: ')+str(out)
            if backup:message+=self.raw_text('；修改前输入已备份。','; previous inputs were backed up.')
            self.statusBar().showMessage(message,9000)
        except Exception as error:QMessageBox.warning(self,self.raw_text('保存失败','Save failed'),str(error))

    def save_case(self):
        parent=self.source.parent if self.source is not None else documents_root()/'Cases'
        default=parent/(self.case_basename()+'_gui_'+datetime.now().strftime('%m%d_%H%M%S'))
        path,_=QFileDialog.getSaveFileName(self,'输入新的案例文件夹名称（不覆盖已有目录）',str(default),'案例目录 (*)')
        if not path:return
        try:
            out=self.write_case(path);self.adopt_saved_case(out)
            self.statusBar().showMessage(self.raw_text('已另存并切换到新案例：','Saved as and switched to new case: ')+str(out),9000)
            QMessageBox.information(self,self.raw_text('保存成功','Saved'),self.raw_text('已生成输入文件并切换到新案例：\n','Input files saved; new case is now active:\n')+str(out))
        except Exception as error:QMessageBox.warning(self,self.raw_text('保存失败','Save failed'),str(error))

    def run_case(self):
        if self.process: return
        try:
            tri,figtext,warnings=self.checked_inputs();data,_=self.collect()
            run_namelist=Namelist(tri)
            for key in ('inel0','isot'):
                if key in run_namelist.fields:data[key]=run_namelist.get(key)
            incomplete=[row['symbol'] for row in data['_material_overrides']
                        if any(row[key] is None or row[key]<=0 for key in ('mass','density','atomic_density'))]
            if incomplete:
                QMessageBox.warning(self,self.raw_text('材料参数不完整','Incomplete material properties'),
                    self.raw_text('请为以下组分填写大于0的原子质量、质量密度和原子数密度：','Enter positive atomic mass, mass density, and atomic number density for: ')+', '.join(incomplete))
                return
            if not preflight(self,self.engine_config,data,warnings):return
            self.run_progress.reset_run()
            destination=Path(self.engine_config.results)/(datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'_GUI_'+self.case_basename())
            self.write_case(destination); self.run_directory=destination; self.stop_requested=False
            staged_tables=stage_tables(self.engine_config,destination)
            apply_material_overrides(staged_tables,data['_material_overrides'],data['isbv'])
            # Only the private run copy receives a portable path to its table snapshot.
            run_tri=read_text(destination/'tri.inp')
            run_changes={'tableinp':"'./_tables'",'dns_0':', '.join('-1' for _ in data['symbol'])}
            atomic_write_text(destination/'tri.inp',Namelist(run_tri).patch(run_changes))
            atomic_write_text(destination/'stop_run.inp','0\n',encoding='ascii')
            program,arguments=launch_command(self.engine_config,destination)
            self.log.clear(); self.log.appendPlainText(self.raw_text('运行目录：','Run directory: ')+str(destination)+'\n'+self.raw_text('正在启动所选内核 / 单进程计算…','Starting selected engine / single-process calculation…')+'\n')
            self.log_file=(destination/'run.log').open('wb'); self.decoder=codecs.getincrementaldecoder('utf-8')(errors='replace')
            self.process=QProcess(self); self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
            environment=QProcessEnvironment()
            for key,value in engine_environment(self.engine_config).items():environment.insert(key,value)
            self.process.setProcessEnvironment(environment)
            self.process.readyReadStandardOutput.connect(self.read_log); self.process.finished.connect(self.finished); self.process.errorOccurred.connect(self.process_error)
            self.run_button.setEnabled(False); self.stop_button.setEnabled(True); self.results_button.setEnabled(True)
            self.process.setWorkingDirectory(str(destination))
            with external_dll_search():
                self.process.start(program,arguments)
                # Ensure CreateProcess has completed before restoring the GUI DLL directory.
                self.process.waitForStarted(3000)
            self.tabs.setCurrentWidget(self.log); self.statusBar().showMessage('计算运行中；输入副本保存在独立结果目录。')
        except Exception as e:
            self.run_progress.set_state('failed')
            self.close_log(); self.process=None; self.refresh(); QMessageBox.warning(self,'无法运行',str(e))

    def read_log(self):
        if not self.process: return
        chunk=bytes(self.process.readAllStandardOutput())
        if self.log_file: self.log_file.write(chunk); self.log_file.flush()
        if chunk:
            decoded=self.decoder.decode(chunk)
            self.run_progress.feed(decoded)
            self.log.moveCursor(QTextCursor.MoveOperation.End); self.log.insertPlainText(decoded); self.log.ensureCursorVisible()

    def close_log(self):
        if self.log_file: self.log_file.close(); self.log_file=None

    def process_error(self,error):
        if error==QProcess.ProcessError.FailedToStart:
            self.run_progress.set_state('failed')
            self.log.appendPlainText('启动失败：'+self.process.errorString()); self.close_log(); old=self.process; self.process=None; old.deleteLater()
            self.stop_button.setEnabled(False); self.refresh(); self.statusBar().showMessage('未能启动计算，请查看日志。')

    def finished(self,code,status):
        self.read_log(); self.close_log()
        self.run_progress.feed(self.decoder.decode(b'',final=True),final=True)
        text=(self.run_directory/'run.log').read_bytes().decode('utf-8',errors='replace') if (self.run_directory/'run.log').exists() else ''
        bad=bool(re.search(r'\bERROR\b|Fortran runtime error|SIGSEGV|SIGFPE|(?<![A-Za-z])NaN(?![A-Za-z])',text,re.I))
        normal=(status==QProcess.ExitStatus.NormalExit and code==0 and not bad)
        success=(normal and 'hist_loop beendet' in text and (self.run_directory/'time_run.dat').exists())
        stopped=self.stop_requested and normal
        self.run_progress.set_state('stopped' if stopped else 'completed' if success else 'failed')
        message=('运行已按请求提前结束；结果可能不完整。' if stopped else '计算正常完成。' if success else '运行未通过完成检查，请查看日志及输出。')
        fatal=re.search(r'^Fortran runtime error:.*$',text,re.M)
        if fatal:
            message='Fortran 内核异常：'+fatal[0].partition(':')[2].strip()
            self.error_history.append('运行目录：'+str(self.run_directory)+'\n'+message)
        self.log.appendPlainText('\n'+message+'\n结果目录：'+str(self.run_directory)); old=self.process; self.process=None
        if old: old.deleteLater()
        self.stop_button.setEnabled(False); self.statusBar().showMessage(message); self.refresh()

    def stop_run(self):
        if self.process and self.run_directory:
            try:
                atomic_write_text(self.run_directory/'stop_run.inp','1\n',encoding='ascii'); self.stop_requested=True; self.stop_button.setEnabled(False)
                self.run_progress.set_state('stopping')
                self.log.appendPlainText('\n已请求停止：内核每10个注量步检查一次，请等待安全结束。')
            except OSError as e: QMessageBox.warning(self,'停止请求失败',str(e))

    def open_results(self):
        if self.run_directory: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.run_directory)))

    def closeEvent(self,event):
        if self.process:
            QMessageBox.information(self,'计算仍在运行','请先请求停止并等待计算结束，再关闭窗口。'); event.ignore(); return
        if self.dirty and QMessageBox.question(self,'尚未另存','当前有未另存的编辑。是否放弃并关闭？')!=QMessageBox.StandardButton.Yes: event.ignore(); return
        event.accept()

def main():
    parser=argparse.ArgumentParser(description='SDTrimSP-2D 中文输入工作台')
    parser.add_argument('case',nargs='?',default=None)
    parser.add_argument('--capture',help=argparse.SUPPRESS)
    parser.add_argument('--results-dir',help=argparse.SUPPRESS)
    parser.add_argument('--target-editor',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--input-files',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--self-test',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if sys.platform == 'win32':
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('SDTrimSP-2D.GUI')
        except (AttributeError, OSError):
            pass
    app=QApplication(sys.argv); app.setFont(QFont('Microsoft YaHei',10))
    app.setApplicationName('SDTrimSP-2D_GUI');app.setOrganizationName('LocalResearchTools');app.setApplicationVersion(VERSION)
    icon_path=Path(__file__).parent/'assets'/'SDTrimSP-2D_GUI.ico'
    if icon_path.exists(): app.setWindowIcon(QIcon(str(icon_path)))
    # Installed app directories may be read-only. Never close an existing GUI.
    lock=QLockFile(str(state_root()/'session.lock'))
    if not args.self_test and not lock.tryLock(0):
        QMessageBox.information(None,'工作台已打开','输入工作台已经在运行，请切换到现有窗口。首次启动可能需要稍候。')
        return 0
    test_directory=tempfile.TemporaryDirectory(prefix='sd2d-self-test-') if args.self_test else None
    test_settings=QSettings(str(Path(test_directory.name)/'settings.ini'),QSettings.Format.IniFormat) if test_directory else None
    if test_settings:test_settings.setValue('setup/v090_seen',True)
    window=Window(Path(args.case) if args.case else None,settings=test_settings)
    if args.target_editor:window.tabs.setCurrentWidget(window.target_editor)
    if args.input_files:window.tabs.setCurrentWidget(window.files_page)
    if args.results_dir:
        window.results_view.load_directory(Path(args.results_dir));window.tabs.setCurrentWidget(window.results_view)
    screen=app.primaryScreen()
    if screen:
        area=screen.availableGeometry()
        window.resize(min(1430,int(area.width()*.94)),min(920,int(area.height()*.9)))
        window.move(area.center()-window.rect().center())
    window.showMaximized()
    if args.self_test:
        def self_test():
            from smoke_check import verify_window
            try:
                report=verify_window(window,Path(test_directory.name),Path(args.self_test))
                atomic_write_text(Path(args.self_test),json.dumps(report,ensure_ascii=False,indent=2)+'\n')
                window.dirty=False;window.close();app.exit(0)
            except Exception:
                atomic_write_text(Path(args.self_test),json.dumps({'ok':False,'traceback':traceback.format_exc()},ensure_ascii=False,indent=2)+'\n')
                app.exit(1)
        QTimer.singleShot(500,self_test)
    if args.capture:
        def capture():
            window.canvas.draw(); window.grab().save(str(Path(args.capture)))
        QTimer.singleShot(2500,capture)
    return app.exec()

if __name__=='__main__':
    try: sys.exit(main())
    except Exception:
        (state_root()/'startup-error.log').write_text(traceback.format_exc(),encoding='utf-8'); raise
