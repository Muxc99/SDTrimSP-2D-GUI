"""Result workbench: conditional controls, additional plots and snapshot playback."""
from pathlib import Path
import math
import numpy as np
import pandas as pd
from PySide6.QtCore import Qt,QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,QScrollArea,QGroupBox,QCheckBox,QListWidget,QListWidgetItem,QAbstractItemView,QDoubleSpinBox,QSpinBox,QSlider,QTabWidget,QTableWidget,QTableWidgetItem,QHeaderView,QFileDialog,QMessageBox,QProgressDialog,QSizePolicy)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT
from element_picker import NoWheelComboBox
from element_colors import element_colormap
from layout_defaults import DefaultSplitter
from results_analysis import (OPTIONAL_NAMES,extend_dataset,horizontal_profile,cross_section,projected_inventory,morphology,surface_change,envelope)

EXTRA_KINDS=[('inventory', '投影面积库存量随注量'), ('morphology', '高度 / 宽度 / 截面积演化'), ('redeposit', '局部再沉积分布'), ('transport', '局部粒子收支分布'), ('transport_static', '静态局部粒子收支'), ('hits', '入射击中位置分布'), ('statistics', '全局粒子 / 能量统计'), ('energy', '能量收支（保留符号）'), ('particle_energy', '粒子能谱'), ('particle_angle', '粒子极角分布'), ('particle_range', '粒子停止位移 / 路径分布'), ('particle_positions', '粒子终点位置分布'), ('trajectory', '粒子轨迹 x–z'), ('active', '活跃单元组分收支'), ('timing', '计算阶段耗时')]
EXTRA_KEYS={k for k,_ in EXTRA_KINDS}
KEYS={'fraction': 'cells', 'density': 'cells', 'total_density': 'cells', 'surface': 'surface', 'local': 'yield', 'totals': 'yield', 'inventory': 'cells', 'morphology': 'cells', 'statistics': 'statistics', 'particle_energy': 'particles', 'particle_angle': 'particles', 'particle_range': 'particles', 'particle_positions': 'particles', 'trajectory': 'trajectories'}
TIME_KEYS={'cells','surface','yield','redeposit','transport','transport_static','hits','active'}
TIME_PLOTS={'hits', 'fraction', 'total_density', 'local', 'active', 'transport', 'density', 'transport_static', 'redeposit'}
REQUIRES={'cells':'T_10_2D.dat','surface':'surf.dat','yield':'sputter_yield.dat','profiles':'profil.dat','statistics':'E0_31_3D.dat','particles':'partic_*.dat','trajectories':'trajec_*.dat','energy':'energy_analyse.dat','timing':'time00.dat','active':'activ_cell.dat','hits':'surf_proj.dat','redeposit':'re_deposit.dat','transport':'loss_depos.dat','transport_static':'loss_depos_2.dat'}
EN={'inventory': 'Projected-area inventory vs fluence', 'morphology': 'Height / width / area evolution', 'redeposit': 'Local redeposition', 'transport': 'Local particle balance', 'transport_static': 'Static local particle balance', 'hits': 'Incident hit distribution', 'statistics': 'Global particle / energy statistics', 'energy': 'Signed energy budget', 'particle_energy': 'Particle energy spectrum', 'particle_angle': 'Particle polar-angle distribution', 'particle_range': 'Stopped displacement / path distribution', 'particle_positions': 'Particle endpoint positions', 'trajectory': 'Particle trajectories x–z', 'active': 'Active-cell component balance', 'timing': 'Computation time by stage'}

from results_render import ResultsRender
from results_navigation import ResultsNavigation

class ExtendedResults(ResultsRender):
    def tr(self,zh,en):return en if getattr(self.owner,'ui_language','zh')=='en' else zh
    def key_for(self,kind=None):
        kind=kind or self.kind.currentData();return KEYS.get(kind,kind)
    def curve_label(self,col):
        if col.startswith(('R_','Y_')):
            local=self.kind.currentData()=='local'
            if col.startswith('R_'):name=self.tr('反射贡献','Reflection contribution') if local else self.tr('反射系数','Reflection coefficient')
            else:name=self.tr('溅射贡献','Sputtering contribution') if local else self.tr('溅射产额','Sputtering yield')
            suffix=self.tr('总计','Total') if col[2:]=='total' else col[2:]
            return name+' · '+suffix
        definitions={
            'max_height_A':('最高表面 z','Maximum surface z'), 'min_height_A':('最低表面 z','Minimum surface z'),
            'mean_height_A':('投影加权平均表面 z','Projected mean surface z'),
            'height_above_reference_A':('最高点相对参考高度','Height above reference'),
            'occupied_width_above_reference_A':('参考高度以上投影总宽','Projected width above reference'),
            'area_above_reference_A2':('参考高度以上截面积','Area above reference'),
            'material_area_A2':('材料总截面积','Total material area'),
            'material_area_change_A2':('材料截面积变化','Material area change'),
            'hits':('入射击中计数','Incident hits'), 'volume_statistic':('体积诊断量','Volume diagnostic')}
        if col in definitions:return self.tr(*definitions[col])
        prefixes={'composition_at_max_height':('最高点成分','Composition at maximum height'),'stopped_inventory':('程序保留面密度','Program retained areal density'),'backscattered':('背散射投射粒子','Backscattered projectiles'),'transmitted_recoil':('透射反冲原子','Transmitted recoils'),'transmitted':('透射投射粒子','Transmitted projectiles'),'sputter_energy':('溅射能量','Sputter energy'),'back_energy':('背散射能量','Backscatter energy'),'trans_energy':('透射能量','Transmission energy'),'trans_recoil_energy':('透射反冲能量','Transmitted recoil energy'),'input_energy':('输入能量','Input energy'),'chemical_erosion':('化学侵蚀','Chemical erosion'),'reemission':('再释放','Reemission'),'incident':('入射计数','Incident count'),'outgoing':('出射计数','Outgoing count'),'incoming':('进入计数','Incoming count'),'scattered':('散射计数','Scattered count'),'sputtered':('溅射计数','Sputtered count'),'reemitted':('再释放计数','Reemitted count'),'redeposit':('再沉积计数','Redeposited count'),'delta':('组分收支','Component balance')}
        for prefix in sorted(prefixes,key=len,reverse=True):
            if col.startswith(prefix+'_'):return self.tr(*prefixes[prefix])+' · '+col[len(prefix)+1:]
        return col

    def make_spin(self,value=0):
        w=QDoubleSpinBox();w.setDecimals(6);w.setRange(-1e9,1e9);w.setValue(value);w.setKeyboardTracking(False);return w
    def build_results_ui(self,kinds):
        self.loading=True;self._space_factor=.1;self._last_extra_key=None;self.table_dirty=True
        self.gradient_stops={}
        self.timer=QTimer(self);self.timer.setInterval(600);self.timer.timeout.connect(self.advance_frame)
        layout=QVBoxLayout(self);layout.setContentsMargins(8,7,8,5);layout.setSpacing(5)
        actions=QHBoxLayout();layout.addLayout(actions)
        for label,slot in [('打开结果目录…',self.open_directory),('选择输出文件…',self.open_files),('载入本次运行结果',self.load_current_run)]:
            button=QPushButton(label);button.clicked.connect(slot);actions.addWidget(button)
        actions.addStretch()
        self.csv_button=QPushButton('导出当前数据 CSV…');self.csv_button.clicked.connect(self.export_csv);actions.addWidget(self.csv_button)
        self.png_button=QPushButton('保存图片 PNG…');self.png_button.clicked.connect(self.export_png);actions.addWidget(self.png_button)
        self.source_label=QLabel('尚未载入结果。请选择同一算例的输出目录或文件。');self.source_label.setWordWrap(False);self.source_label.setMaximumHeight(23);self.source_label.setMinimumWidth(0);layout.addWidget(self.source_label)
        self.splitter=split=DefaultSplitter(Qt.Orientation.Horizontal,'results');layout.addWidget(split,1)
        self.control_tabs=QTabWidget();split.addWidget(self.control_tabs)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        options=QWidget();left=QVBoxLayout(options);left.setContentsMargins(7,5,7,5);scroll.setWidget(options);self.control_tabs.addTab(scroll,'绘图设置')
        box=QGroupBox('图像与单位');form=QFormLayout(box);left.addWidget(box)
        self.category=NoWheelComboBox()
        for zh,en,key in [('全部图像','All plots','all'),('二维分布','2D distributions','fields'),('表面与形貌','Surface and morphology','shape'),('收支与演化','Balances and evolution','balances'),('粒子与轨迹','Particles and trajectories','particles'),('能量与诊断','Energy and diagnostics','diagnostics')]:self.category.addItem(self.tr(zh,en),key)
        form.addRow('图像分类',self.category)
        self.kind=NoWheelComboBox();self.kind.setMaxVisibleItems(15)
        for key,label in kinds:self.kind.addItem(label,key)
        form.addRow('图像类型',self.kind)
        self.unit=NoWheelComboBox()
        for label,factor in [('Å',1.),('nm',.1),('μm',.0001)]:self.unit.addItem(label,factor)
        self.unit.setCurrentIndex(1);form.addRow('空间单位',self.unit)
        self.fluence_unit=NoWheelComboBox();self.fluence_unit.addItem('ions/Å²',1.);self.fluence_unit.addItem('ions/cm²',1e16);form.addRow('注量单位',self.fluence_unit)
        self.species=NoWheelComboBox();form.addRow('组分',self.species);self.species_label=form.labelForField(self.species)
        self.overlay=QCheckBox('叠加同一步表面轮廓');self.overlay.setChecked(True);left.addWidget(self.overlay)
        self.fixed_scale=QCheckBox('各历史步使用固定色标');self.fixed_scale.setChecked(True);left.addWidget(self.fixed_scale)
        self.geometry_box=QGroupBox('形貌统计范围');g=QFormLayout(self.geometry_box);left.addWidget(self.geometry_box)
        self.x_position=self.make_spin();self.z_position=self.make_spin();self.x_min=self.make_spin(-20);self.x_max=self.make_spin(20);self.reference_z=self.make_spin()
        self.geometry_rows={}
        for name,label,widget in [('x','取样 x',self.x_position),('z','取样 z',self.z_position),('xmin','形貌 x 最小值',self.x_min),('xmax','形貌 x 最大值',self.x_max),('reference','参考高度 z',self.reference_z)]:
            lab=QLabel(label);g.addRow(lab,widget);self.geometry_rows[name]=(lab,widget)
        self.profile_quantity=NoWheelComboBox();self.profile_quantity.addItem('原子分数','fraction');self.profile_quantity.addItem('原子数密度','density');g.addRow('剖面物理量',self.profile_quantity);self.profile_quantity_label=g.labelForField(self.profile_quantity)
        self.detail_box=QGroupBox('数据来源与统计');d=QFormLayout(self.detail_box);left.addWidget(self.detail_box)
        self.detail_source=NoWheelComboBox();d.addRow('文件 / 分组',self.detail_source)
        self.particle_species=NoWheelComboBox();d.addRow('粒子组分',self.particle_species);self.particle_species_label=d.labelForField(self.particle_species)
        self.hist_bins=QSpinBox();self.hist_bins.setRange(5,500);self.hist_bins.setValue(50);self.hist_bins.setKeyboardTracking(False);d.addRow('直方图分箱',self.hist_bins);self.bins_label=d.labelForField(self.hist_bins)
        self.trajectory_limit=QSpinBox();self.trajectory_limit.setRange(1,2000);self.trajectory_limit.setValue(100);self.trajectory_limit.setKeyboardTracking(False);d.addRow('显示轨迹上限',self.trajectory_limit);self.limit_label=d.labelForField(self.trajectory_limit)
        self.surface_box=QGroupBox('轮廓对比：选择历史步');sv=QVBoxLayout(self.surface_box);self.surface_steps=QListWidget();self.surface_steps.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection);self.surface_steps.setMinimumHeight(100);self.surface_steps.setMaximumHeight(260);sv.addWidget(self.surface_steps);left.addWidget(self.surface_box)
        self.curve_box=QGroupBox('选择曲线 / 统计项');cv=QVBoxLayout(self.curve_box);self.curve_group=NoWheelComboBox();cv.addWidget(self.curve_group);self.curves=QListWidget();self.curves.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection);self.curves.setMinimumHeight(120);self.curves.setMaximumHeight(300);cv.addWidget(self.curves)
        buttons=QHBoxLayout();cv.addLayout(buttons)
        for label,slot in [('全选',self.select_visible_curves),('清空选择',self.curves.clearSelection)]:b=QPushButton(label);b.clicked.connect(slot);buttons.addWidget(b)
        left.addWidget(self.curve_box);left.addStretch()
        files_page=QWidget();fv=QVBoxLayout(files_page);self.files_list=QListWidget();fv.addWidget(self.files_list)
        self.files_note=QLabel('可用图像会根据文件自动启用；缺失的输出不会伪造。');self.files_note.setWordWrap(True);fv.addWidget(self.files_note)
        help_button=QPushButton('查看文件与输出选项说明');help_button.clicked.connect(self.show_output_help);fv.addWidget(help_button);self.control_tabs.addTab(files_page,'数据文件')
        plot=QWidget();pl=QVBoxLayout(plot);pl.setContentsMargins(4,0,0,0);split.addWidget(plot)
        self.figure=Figure(figsize=(9,6),layout='none');self.canvas=FigureCanvasQTAgg(self.figure);self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding);self.toolbar=ResultsNavigation(self)
        self.data_button=QPushButton('数据表');self.data_button.setCheckable(True);self.data_button.toggled.connect(self.toggle_table)
        toolbar_row=QHBoxLayout();toolbar_row.addWidget(self.toolbar,1);toolbar_row.addWidget(self.data_button);pl.addLayout(toolbar_row);pl.addWidget(self.canvas,1)
        self.playback=QWidget();pb=QHBoxLayout(self.playback);pb.setContentsMargins(0,0,0,0)
        self.prev_button=QPushButton('◀');self.next_button=QPushButton('▶');self.play_button=QPushButton('播放');self.play_button.clicked.connect(self.toggle_play)
        self.prev_button.clicked.connect(lambda:self.step.setCurrentIndex(max(0,self.step.currentIndex()-1)));self.next_button.clicked.connect(lambda:self.step.setCurrentIndex(min(self.step.count()-1,self.step.currentIndex()+1)))
        for b in (self.prev_button,self.play_button,self.next_button):pb.addWidget(b)
        self.slider=QSlider(Qt.Orientation.Horizontal);pb.addWidget(self.slider,1);self.step=NoWheelComboBox();self.step.setMinimumWidth(180);pb.addWidget(self.step)
        self.speed=QSpinBox();self.speed.setRange(100,5000);self.speed.setSingleStep(100);self.speed.setValue(600);self.speed.setSuffix(' ms');self.speed.valueChanged.connect(self.timer.setInterval);pb.addWidget(self.speed);pl.addWidget(self.playback)
        self.note=QLabel();self.note.setWordWrap(True);self.note.setFixedHeight(48);self.note.setStyleSheet('QLabel {background:#f1f6fa;padding:6px;border-radius:4px;font-size:9pt;}');pl.addWidget(self.note)
        from results_table import ResultsDataDialog
        self.data_dialog=ResultsDataDialog(self);self.data_table=self.data_dialog.table
        self.data_dialog.finished.connect(lambda _:self.data_button.setChecked(False))
        # Let long translated labels wrap; prevent combo content hints from widening the sidebar.
        for combo in options.findChildren(NoWheelComboBox):
            combo.setMinimumWidth(0);combo.setMinimumContentsLength(9);combo.setSizeAdjustPolicy(NoWheelComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);combo.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
        for spin in options.findChildren(QDoubleSpinBox):spin.setMinimumWidth(85);spin.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
        for group in options.findChildren(QGroupBox):
            group.setMinimumWidth(0);form_layout=group.layout()
            if isinstance(form_layout,QFormLayout):
                form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows);form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
                for row in range(form_layout.rowCount()):
                    item=form_layout.itemAt(row,QFormLayout.ItemRole.LabelRole)
                    if item and isinstance(item.widget(),QLabel):item.widget().setWordWrap(True);item.widget().setMaximumWidth(135)
        self.category.currentIndexChanged.connect(self.filter_plot_category)
        self.curve_group.currentIndexChanged.connect(self.filter_curves)
        self.kind.currentIndexChanged.connect(self.configure)
        for combo in (self.unit,self.fluence_unit,self.species,self.step,self.profile_quantity,self.particle_species):combo.currentIndexChanged.connect(self.redraw)
        self.detail_source.currentIndexChanged.connect(self.source_changed)
        for spin in (self.x_position,self.z_position,self.x_min,self.x_max,self.reference_z,self.hist_bins,self.trajectory_limit):spin.valueChanged.connect(self.redraw)
        for check in (self.overlay,self.fixed_scale):check.toggled.connect(self.redraw)
        self.surface_steps.itemSelectionChanged.connect(self.redraw);self.curves.itemSelectionChanged.connect(self.redraw)
        self.slider.valueChanged.connect(self.step.setCurrentIndex);self.step.currentIndexChanged.connect(self.sync_slider)
        self.loading=False;self.configure()
    def filter_plot_category(self):
        groups={'fields':{'fraction','density','total_density'},'shape':{'surface','morphology'},'balances':{'local','totals','inventory','redeposit','transport','transport_static','statistics'},'particles':{'particle_energy','particle_angle','particle_range','particle_positions','trajectory'},'diagnostics':{'energy','active','hits','timing'}}
        category=self.category.currentData();keys=groups.get(category);first=None
        for i in range(self.kind.count()):
            keep=keys is None or self.kind.itemData(i) in keys;self.kind.view().setRowHidden(i,not keep)
            if keep and self.available(self.kind.itemData(i)) and first is None:first=i
        if keys is not None and self.kind.currentData() not in keys and first is not None:self.kind.setCurrentIndex(first)

    def available(self,kind):
        if kind in ('particle_angle','particle_range'):
            return any(len(v) and (('stop' in name.lower())==(kind=='particle_range')) for name,v in (self.dataset or {}).get('particles',{}).items())
        value=(self.dataset or {}).get(self.key_for(kind))
        if isinstance(value,pd.DataFrame):return not value.empty
        if isinstance(value,dict):return any(len(v) for v in value.values())
        return bool(value)
    def configure_extended(self):
        if self.loading:return
        self.timer.stop();self.play_button.setText(self.tr('播放','Play'));self.loading=True
        kind=self.kind.currentData();key=self.key_for();data=self.dataset or {}
        self.step.clear()
        if key in TIME_KEYS:
            for snap in data.get(key,[]):self.step.addItem(self.snapshot_label(snap))
        self.step.setCurrentIndex(self.step.count()-1)
        self.surface_steps.clear()
        for i,snap in enumerate(data.get('surface',[])):
            item=QListWidgetItem(self.snapshot_label(snap));item.setData(Qt.ItemDataRole.UserRole,i);self.surface_steps.addItem(item);item.setSelected(i in (0,len(data['surface'])-1))
        columns=[]
        if kind in ('local','totals') and data.get('yield'):
            columns=list(data['yield'][0]['data'].columns[1:])+(['R_total','Y_total'] if kind=='totals' else [])
        elif kind=='inventory':columns=data.get('symbols',[])
        elif kind=='morphology':columns=['max_height_A','min_height_A','mean_height_A','height_above_reference_A','occupied_width_above_reference_A','area_above_reference_A2','material_area_A2','material_area_change_A2']
        elif kind in ('transport','transport_static','redeposit','hits','active') and data.get(key):columns=[c for c in data[key][0]['data'].columns if c not in ('x_A','z_A','cell_id')]
        elif kind=='statistics' and isinstance(data.get(key),pd.DataFrame):columns=list(data[key].columns[1:])
        self.curves.clear()
        for col in columns:
            item=QListWidgetItem(self.curve_label(col));item.setData(Qt.ItemDataRole.UserRole,col);item.setToolTip(col);self.curves.addItem(item)
            default=(col in ('R_total','Y_total')) if kind=='totals' else (col=='height_above_reference_A') if kind=='morphology' else (col.startswith('stopped_inventory_')) if kind=='statistics' else (col.startswith('incident_') or col.startswith('sputtered_')) if kind.startswith('transport') else (col.startswith('delta_')) if kind=='active' else True
            item.setSelected(default)
        self.curve_group.clear()
        groups=([('长度','Length','length'),('截面积','Cross-sectional area','area')] if kind=='morphology' else [('保留面密度','Retained areal density','inventory'),('粒子计数','Particle counts','count'),('能量','Energy','energy'),('最高点成分','Top-cell composition','fraction'),('表面高度','Surface height','length')] if kind=='statistics' else [('组分收支','Component balance','count'),('体积诊断量','Volume diagnostic','volume')] if kind=='active' else [])
        for zh,en,keygroup in groups:self.curve_group.addItem(self.tr(zh,en),keygroup)
        self.curve_group.setVisible(bool(groups));self.filter_curves(redraw=False)
        self.curve_box.setVisible(bool(columns));self.surface_box.setVisible(kind=='surface')
        self.geometry_box.setVisible(kind=='morphology')
        for name,pair in self.geometry_rows.items():
            show=(name in ('xmin','xmax','reference') and kind=='morphology')
            for widget in pair:widget.setVisible(show)
        for widget in (self.profile_quantity,self.profile_quantity_label):widget.setVisible(False)
        self.species.setVisible(kind in ('fraction','density'));self.species_label.setVisible(kind in ('fraction','density'))
        self.species.setEnabled(kind in ('fraction','density'))
        self.overlay.setVisible(kind in ('fraction','density','total_density'));self.fixed_scale.setVisible(kind in ('fraction','density','total_density'))
        self.detail_box.setVisible(key in ('particles','trajectories','energy'))
        self.detail_source.clear()
        if key in ('particles','trajectories'):
            for name,records in data.get(key,{}).items():
                if len(records) and not (kind=='particle_angle' and 'stop' in name.lower()) and not (kind=='particle_range' and 'stop' not in name.lower()):self.detail_source.addItem(name,name)
        elif key=='profiles':
            for i,profile in enumerate(data.get(key,[])):self.detail_source.addItem(f"#{profile['cell_id']} x={profile['x1_A']:g}…{profile['x2_A']:g} Å",i)
        elif key=='energy' and isinstance(data.get(key),pd.DataFrame):
            for name in data[key].group.unique():self.detail_source.addItem(name,name)
        particle=key=='particles'
        for widget in (self.particle_species,self.particle_species_label):widget.setVisible(particle or key=='trajectories')
        for widget in (self.hist_bins,self.bins_label):widget.setVisible(kind in ('particle_energy','particle_angle','particle_range'))
        for widget in (self.trajectory_limit,self.limit_label):widget.setVisible(kind=='trajectory')
        self._last_extra_key=key;self.loading=False;self.update_particle_species();self.update_playback();self.redraw()
    def select_visible_curves(self):
        self.curves.blockSignals(True)
        for i in range(self.curves.count()):
            item=self.curves.item(i);item.setSelected(not item.isHidden())
        self.curves.blockSignals(False);self.redraw()

    def filter_curves(self,*args,redraw=True):
        kind=self.kind.currentData();wanted=self.curve_group.currentData()
        was=self.curves.blockSignals(True)
        for i in range(self.curves.count()):
            item=self.curves.item(i);c=item.data(Qt.ItemDataRole.UserRole) or item.text()
            typ='area' if c.endswith('_A2') else 'length' if c.endswith('_A') else 'inventory' if c.startswith('stopped_inventory_') else 'fraction' if c.startswith('composition_at_max_height_') else 'energy' if any(c.startswith(p+'_') for p in ('back_energy','trans_energy','sputter_energy','trans_recoil_energy','input_energy')) else 'volume' if c=='volume_statistic' else 'count'
            hidden=bool(wanted and typ!=wanted);item.setHidden(hidden)
            if hidden:item.setSelected(False)
        if wanted and not self.curves.selectedItems():
            for i in range(self.curves.count()):
                item=self.curves.item(i)
                if not item.isHidden():item.setSelected(True)
        self.curves.blockSignals(was)
        if redraw and not self.loading:self.redraw()

    def update_particle_species(self):
        data=self.dataset or {};key=self.key_for();self.particle_species.blockSignals(True);self.particle_species.clear();self.particle_species.addItem(self.tr('全部组分','All species'),-1)
        name=self.detail_source.currentData();records=data.get(key,{}).get(name,[]) if key in ('particles','trajectories') else []
        ids=sorted(set(records.species_id.astype(int))) if isinstance(records,pd.DataFrame) else sorted({r['species_id'] for r in records})
        for i in ids:
            symbols=data.get('symbols',[]);label=symbols[i-1] if 0<i<=len(symbols) else '#'+str(i);self.particle_species.addItem(label,i)
        self.particle_species.blockSignals(False)
    def source_changed(self):
        if self.loading:return
        self.update_particle_species();self.redraw()
    def sync_slider(self,index):
        self.slider.blockSignals(True);self.slider.setValue(max(0,index));self.slider.blockSignals(False)
    def update_playback(self):
        enabled=self.kind.currentData() in TIME_PLOTS and self.step.count()>0
        self.playback.setVisible(True);self.playback.setEnabled(enabled);self.slider.setRange(0,max(0,self.step.count()-1));self.sync_slider(self.step.currentIndex())
        self.play_button.setEnabled(self.step.count()>1)
    def toggle_play(self):
        if self.timer.isActive():self.timer.stop();self.play_button.setText(self.tr('播放','Play'))
        elif self.step.count()>1:
            if self.step.currentIndex()==self.step.count()-1:self.step.setCurrentIndex(0)
            self.timer.start();self.play_button.setText(self.tr('暂停','Pause'))
    def advance_frame(self):
        if not self.isVisible() or self.step.currentIndex()+1>=self.step.count():self.timer.stop();self.play_button.setText(self.tr('播放','Play'));return
        self.step.setCurrentIndex(self.step.currentIndex()+1)
    def toggle_table(self,checked):
        if checked:
            self.refresh_data_table();self.data_dialog.show();self.data_dialog.raise_();self.data_dialog.activateWindow()
        else:self.data_dialog.hide()
    def refresh_data_table(self):
        if not self.data_button.isChecked():return
        self.data_dialog.update_frame(self.current_frame)
    def refresh_results_metadata(self):
        if not self.dataset:return
        from results_data import cell_snapshot_warning
        for english in (False,True):
            previous=cell_snapshot_warning(self.dataset,english)
            if previous in self.dataset.get('warnings',[]):self.dataset['warnings'].remove(previous)
        warning=cell_snapshot_warning(self.dataset,getattr(self.owner,'ui_language','zh')=='en')
        if warning:self.dataset['warnings'].append(warning)
        folder=getattr(self,'result_directory','');self.source_label.setText(folder+'  ·  '+str(len(self.dataset['files']))+self.tr(' 个已读取输出',' loaded outputs'))
        self.files_note.setText(self.tr('可用图像按文件自动启用。','Available plots follow the loaded files.')+('\n'+'\n'.join(self.dataset.get('warnings',[])) if self.dataset.get('warnings') else ''))
        self.files_note.setToolTip(self.files_note.text())
        for spin in (self.x_position,self.z_position,self.x_min,self.x_max,self.reference_z):spin.setSuffix(' '+self.unit.currentText())

    # Share one plotting rectangle across all quantities, legends and optional colorbars.
    RESULTS_AXES_BOUNDS=(.075,.10,.845,.80)
    RESULTS_COLORBAR_BOUNDS=(.94,.10,.012,.80)
    def create_results_axes(self):
        self.results_axes=self.figure.add_axes(self.RESULTS_AXES_BOUNDS)
        return self.results_axes
    def create_results_colorbar(self,mappable,label):
        from gradient_editor import gradient_colormap
        key=self.gradient_key()
        if key in self.gradient_stops:mappable.set_cmap(gradient_colormap(self.gradient_stops[key]))
        color_axes=self.figure.add_axes(self.RESULTS_COLORBAR_BOUNDS)
        return self.figure.colorbar(mappable,cax=color_axes,label=label)
    def gradient_key(self):
        return (self.kind.currentData(),self.species.currentText() if self.kind.currentData() in ('fraction','density') else '')
    def gradient_mappable(self):
        ax=getattr(self,'results_axes',None)
        if ax is None or ax not in self.figure.axes:return None
        return next((artist for artist in ax.collections if artist.get_array() is not None),None) if self.kind.currentData() in ('fraction','density','total_density') else None
    def edit_gradient(self):
        from gradient_editor import GradientDialog
        mappable=self.gradient_mappable()
        if mappable is None:return
        playing=self.timer.isActive();self.timer.stop()
        try:GradientDialog(self,mappable,self.gradient_key()).exec()
        finally:
            if playing:self.timer.start()
    def fix_results_frame(self):
        ax=getattr(self,'results_axes',None)
        if ax is not None and ax in self.figure.axes:
            ax.set_position(self.RESULTS_AXES_BOUNDS)
            self.toolbar.ready()

    def finish_results_draw(self):
        if self.dataset and self.dataset.get('invalid_cell_snapshots') and self.kind.currentData() in ('fraction','density','total_density','inventory','morphology'):
            steps=', '.join(str(s['history']) for s in self.dataset['invalid_cell_snapshots'])
            warning=self.tr('⚠ 单元边界异常，未使用历史步：','⚠ Invalid cell boundaries; excluded histories: ')+steps
            self.note.setText(warning+'\n'+self.note.text())
        self.fix_results_frame()
        self.refresh_results_metadata()
        for i in range(self.curves.count()):
            item=self.curves.item(i);col=item.data(Qt.ItemDataRole.UserRole)
            if col:item.setText(self.curve_label(col))
        self.note.setToolTip(self.note.text());self.update_playback();self.refresh_data_table()
    def show_output_help(self):
        text=self.tr('常规二维图：T_10_2D.dat / surf.dat / sputter_yield.dat。\n收支与再沉积：loss_depos.dat / re_deposit.dat / surf_proj.dat。\n粒子明细需开启 lparticle_p / lparticle_r，并设置 ioutput_part 的输出数量。\n轨迹需开启 ltraj_p / ltraj_r，并设置 numb_hist 或 ioutput_hist。\n只显示实际记录；抽样粒子直方图不是自动归一化的产额。\nE0_31_3D.dat 按实际写出布局解析，cel_qu(maxdep) 不作为平均表面成分。','Core maps: T_10_2D.dat / surf.dat / sputter_yield.dat.\nTransport: loss_depos.dat / re_deposit.dat / surf_proj.dat.\nParticle records require lparticle_p / lparticle_r and ioutput_part limits.\nTrajectories require ltraj_p / ltraj_r and numb_hist or ioutput_hist.\nHistograms use recorded samples, not automatically normalized yields.\nE0_31_3D.dat is parsed by actual writer layout; cel_qu(maxdep) is not mean surface composition.')
        QMessageBox.information(self,self.tr('输出文件说明','Output files'),text)
