"""Unified, staged target tools. Closing a tool never writes the source case."""
import math
import numpy as np
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QDialog,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,
    QTabWidget,QLabel,QPushButton,QCheckBox,QComboBox,QLineEdit,QPlainTextEdit,
    QTableWidget,QTableWidgetItem,QHeaderView,QDialogButtonBox,QFileDialog,QSpinBox)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from case_model import number,fmt,Profile,surface_profile,parse_layers
from target_inputs import (LOCAL_FILE,CLUSTER_COUNTS,grid_shape,parse_local,render_local,
    fractions,composition_field,composition_mesh,profile_from_columns,template,parse_distribution,parse_matrix,validate_auxiliary)

def table(headers,rows):
    w=QTableWidget(len(rows),len(headers));w.setHorizontalHeaderLabels(headers)
    w.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    for i,row in enumerate(rows):
        for j,v in enumerate(row):w.setItem(i,j,QTableWidgetItem(str(v)))
    return w

def values(w,row=0):
    return [number(w.item(row,j).text() if w.item(row,j) else '') for j in range(w.columnCount())]

class TargetFeaturesDialog(QDialog):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.tr=owner.raw_text;self.data,self.fig=owner.collect();self.resize(1000,780)
        self.setWindowTitle(self.tr('靶材功能','Target features'));layout=QVBoxLayout(self);self.tabs=QTabWidget();layout.addWidget(self.tabs,1)
        self.overview()
        self.models();self.profile();self.attachments()
        self.error=QLabel();self.error.setWordWrap(True);self.error.setStyleSheet('color:#b42318');layout.addWidget(self.error)
        box=QDialogButtonBox(QDialogButtonBox.StandardButton.Apply|QDialogButtonBox.StandardButton.Close)
        box.button(QDialogButtonBox.StandardButton.Apply).setText(self.tr('应用','Apply'));box.button(QDialogButtonBox.StandardButton.Close).setText(self.tr('关闭','Close'))
        box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply);box.rejected.connect(self.reject);layout.addWidget(box)
        if self.data['case_geo']==28:
            self.profile_page.setEnabled(False)
        for widget in self.findChildren(QWidget):
            widget.setProperty('tooltipDelayMs',500)
            if isinstance(widget,(QPushButton,QCheckBox)) and not widget.toolTip():widget.setToolTip(widget.text())

    def page(self,zh,en):
        w=QWidget();layout=QVBoxLayout(w);self.tabs.addTab(w,self.tr(zh,en));return w,layout

    def overview(self):
        _,layout=self.page('分层 / 靶材设置','Layers / target settings')
        note=QLabel(self.tr('基底 / 体分层 → 凸起自身成分 → 表面分层 → 局部成分或内置团簇\n\n体分层不自动重涂模式 26 的凸起。表面层为连续竖直深度示意；内核按表面网格层号分配，台阶或薄层处可能不同。内置团簇由内核专用算法放置并包含随机抽样；GUI 预览不预测具体随机布局。',
            'Substrate / bulk layers → protrusion composition → surface layers → local composition or built-in clusters\n\nBulk layers do not repaint geometry-26 protrusions. Surface layers show continuous vertical depth; the kernel assigns layers by surface-cell index, which can differ near steps or thin layers. Built-in clusters use a dedicated placement algorithm with random sampling; the GUI preview does not predict the exact layout.'))
        note.setWordWrap(True);layout.addWidget(note)
        from layer_editor import LayerPage
        self.layer_tabs=QTabWidget();self.layer_pages=[]
        for name,zh,en in [('initial_composition.inp','体分层（绝对 z）','Bulk layers (absolute z)'),('initial_composition_surf.inp','表面分层（相对深度）','Surface layers (relative depth)')]:
            page=LayerPage(self,name);self.layer_pages.append(page);self.layer_tabs.addTab(page,self.tr(zh,en))
        self.bulk=self.layer_pages[0].enabled;self.surface=self.layer_pages[1].enabled
        layout.addWidget(self.layer_tabs,1)
        label=QLabel(self.tr('关闭以上开关并关闭局部成分、团簇，即使用均匀基底。附件可保留，再启用时复用。','Disable the above switches, local composition and clusters for a homogeneous substrate. Files can remain for later reuse.'));label.setWordWrap(True);layout.addWidget(label)
        self.imax=QComboBox();self.imax.addItem(self.tr('1 · 单次几何处理','1 · One geometry pass'),1);self.imax.addItem(self.tr('2 · 两次几何处理（单元缩减）','2 · Two geometry passes (cell reduction)'),2);self.imax.setCurrentIndex(max(0,self.imax.findData(self.data.get('geo_imax',1))))
        form=QFormLayout();form.addRow('geo_imax',self.imax);layout.addLayout(form)
        self.rough=QCheckBox(self.tr('局部粗糙入射修正（l_alpha_rough_kor）','Local rough-surface incidence correction (l_alpha_rough_kor)'));self.rough.setChecked(self.data.get('l_alpha_rough_kor',False));layout.addWidget(self.rough)
        if self.data['case_geo']==28:
            r=2510 if self.data['geo_x']<3000 else 25010
            label=QLabel(self.tr(f'几何 28：本机内核专用圆柱截面，硬编码半径 {r} Å；保留原输入，禁用通用基底和局部绘制。需用对应内核算例单独验证。',f'Geometry 28: specialized kernel cylinder section, hardcoded radius {r} A. Existing input is retained; general substrate/local drawing is disabled. Requires a matching kernel case for validation.'));label.setWordWrap(True);layout.addWidget(label)
        layout.addStretch()

    def models(self):
        _,layout=self.page('团簇 / 材料模型','Clusters / material models');form=QFormLayout();layout.addLayout(form)
        self.cluster=QCheckBox(self.tr('启用内置团簇（与局部文件互斥）','Enable built-in clusters (exclusive with local file)'));self.cluster.setChecked(self.data.get('l_clust',False) and not self.data.get('l_clust_read',False));form.addRow(self.cluster)
        self.count=QComboBox();self.count.addItems(list(map(str,CLUSTER_COUNTS)));self.count.setCurrentText(str(int(self.data.get('n_clust',1))));form.addRow('n_clust',self.count)
        self.cluster_q=table(self.data['symbol'],[(self.data['qu_clust'] if math.isclose(sum(self.data.get('qu_clust',[])),1.,abs_tol=1e-6) else self.data['qu_tar'])]);self.cluster_q.setMaximumHeight(85);form.addRow(self.tr('团簇原子分数','Cluster atomic fractions'),self.cluster_q)
        self.compounds=QComboBox();self.compounds.addItems([self.tr('关闭','Off'),self.tr('1 种二元化合物','1 binary compound'),self.tr('2 种二元化合物','2 binary compounds'),self.tr('3 种二元化合物','3 binary compounds')])
        self.compounds.setCurrentIndex(next((i+1 for i,s in enumerate(('','2','3')) if self.data.get('l_two_comp'+s,False)),0));form.addRow(self.tr('化合物模型','Compound model'),self.compounds)
        rows=[[self.data.get('two_comp'+s,''),fmt(self.data.get('rhom'+s,-1))] for s in ('','2','3')]
        self.compound_table=table([self.tr('公式（材料表名称）','Formula (material table name)'),self.tr('密度 g/cm³；-1 使用表值','Density g/cm³; -1 uses table')],rows);self.compound_table.setMaximumHeight(160);form.addRow(self.compound_table)
        self.density=table(self.data['symbol'],[self.data.get('dns_0',[-1]*len(self.data['symbol']))]);self.density.setMaximumHeight(85);form.addRow(self.tr('原子数密度 atoms/Å³；-1 使用表值','Atomic density atoms/A³; -1 uses table'),self.density)
        label=QLabel(self.tr('化合物名须存在于外部内核的材料表中，公式中的两种元素须已添加。这里设置输入模型，不自动推断键合能或物性。','Compound names must exist in the external kernel material table and both elements must be listed. These controls set the input model; they do not infer binding energies or material properties.'));label.setWordWrap(True);layout.addWidget(label);layout.addStretch()


    def profile(self):
        self.profile_page,layout=self.page('表面轮廓','Surface profile');enabled=self.data['case_geo'] in (24,25)
        note=QLabel(self.tr('模式 24 / 25：以下始终使用以靶中心为零的 x，单位为当前显示单位。写出时自动转换为对应格式的 Å。','Geometry 24 / 25: edit centered x in the current display unit. Saving converts to the proper file coordinates in Angstrom.'));note.setWordWrap(True);layout.addWidget(note)
        self.profile_text=QPlainTextEdit();layout.addWidget(self.profile_text,1)
        if enabled:
            p=Profile.parse(self.data['_files']['rauh.inp'])
            self.profile_text.setPlainText('\n'.join(fmt((x-(self.data['geo_x'] if self.data['case_geo']==24 else 0))/self.owner.factor)+' '+fmt(z/self.owner.factor) for x,z in p.rows))
        row=QHBoxLayout();layout.addLayout(row);b=QPushButton(self.tr('导入两列数据…','Import two columns…'));b.clicked.connect(self.import_profile);row.addWidget(b)
        self.shape=QComboBox();self.shape.addItems([self.tr('平面','Flat'),self.tr('正弦','Sine'),self.tr('三角波','Triangle'),self.tr('台阶','Steps')]);row.addWidget(self.shape)
        self.amplitude=QLineEdit(fmt(self.data['geo_dz']/self.owner.factor));self.periods=QSpinBox();self.periods.setRange(1,100);self.periods.setValue(2)
        form=QFormLayout();form.addRow(self.tr('高度 / 当前单位','Height / display unit'),self.amplitude);form.addRow(self.tr('周期数','Periods'),self.periods);layout.addLayout(form)
        b=QPushButton(self.tr('生成（替换上方草稿）','Generate (replace draft above)'));b.clicked.connect(self.generate_profile);layout.addWidget(b)
        self.profile_page.setEnabled(enabled);self.original_profile=self.profile_text.toPlainText()

    def import_profile(self):
        p,_=QFileDialog.getOpenFileName(self,self.tr('导入 x z 两列数据','Import x z columns'),'','Data (*.txt *.csv *.dat);;All (*)')
        if p:
            from case_model import read_text
            self.profile_text.setPlainText(read_text(p))

    def generate_profile(self):
        try:
            a=number(self.amplitude.text());n=self.periods.value();half=self.data['geo_x']/self.owner.factor
            if a<0:raise ValueError('高度须非负 / Height must be nonnegative')
            x=np.linspace(-half,half,max(101,40*n+1));phase=(x+half)/(2*half)*n
            mode=self.shape.currentIndex()
            z=np.zeros_like(x) if mode==0 else a*(1-np.cos(phase*2*np.pi))/2 if mode==1 else a*(1-abs(2*(phase%1)-1)) if mode==2 else np.where((phase%1)<.5,0.,a)
            if mode==3:z[-1]=z[0] # finite-slope discretized steps, no repeated x.
            self.profile_text.setPlainText('\n'.join(fmt(xx)+' '+fmt(zz) for xx,zz in zip(x,z)))
        except ValueError as e:self.error.setText(str(e))

    def attachments(self):
        _,layout=self.page('分布 / 结合能矩阵','Distributions / binding matrix')
        label=QLabel(self.tr('编辑有效模板并勾选启用；取消启用时恢复固定模式 / 默认结合能模型。矩阵模板的 1 eV 是占位初值，必须根据材料修改。','Edit a valid template and check Enable. Disabling restores fixed distributions / the default binding model. The matrix template starts at a placeholder 1 eV; set values for your materials.'));label.setWordWrap(True);layout.addWidget(label)
        self.documents={};tabs=QTabWidget();layout.addWidget(tabs,1)
        for name,key,active in [('energy.inp','case_e0',1),('angle.inp','case_alpha',4),('mat_surfb.inp','isbv',6)]:
            w=QWidget();box=QVBoxLayout(w);enabled=QCheckBox(self.tr('启用此文件','Enable this file'));enabled.setChecked(self.data[key]==active);box.addWidget(enabled)
            edit=QPlainTextEdit();edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
            try:text=self.data['_files'].get(name) or template(name,self.data)
            except ValueError:text=''
            edit.setPlainText(text);box.addWidget(edit);tabs.addTab(w,name);self.documents[name]=(enabled,edit,key,active,text)
            if name=='angle.inp':
                label=QLabel(self.tr('角度文件格式可检查；本机内核的模式 4 方向变量仍需专项数值验证。','File syntax is checked; the local kernel mode-4 direction variables still require numerical verification.'));label.setWordWrap(True);box.addWidget(label)

    def apply(self):
        try:
            flags={'iq0':str(int(self.bulk.isChecked())),'iq0_surf':str(int(self.surface.isChecked())),
                'geo_imax':str(self.imax.currentData()),'l_alpha_rough_kor':'.true.' if self.rough.isChecked() else '.false.'}
            files=dict(self.owner.current_files());changes={}
            from layer_editor import render_layers
            for page in self.layer_pages:
                if page.enabled.isChecked() or page.name in files:
                    changes[page.name]=render_layers(page.rows(),len(self.data['symbol']))
            local=bool(self.data.get('l_clust') and self.data.get('l_clust_read'));cluster=self.cluster.isChecked()
            if cluster:local=False
            if local and cluster:raise ValueError('局部文件与内置团簇不可同时启用 / Choose local file or built-in clusters')
            flags.update(l_clust='.true.' if local or cluster else '.false.',l_clust_read='.true.' if local else '.false.',n_clust=self.count.currentText())
            if cluster:
                q=values(self.cluster_q);fractions(q,len(self.data['symbol']));flags['qu_clust']=', '.join(map(fmt,q))
            count=self.compounds.currentIndex()
            for i,s in enumerate(('','2','3')):
                flags['l_two_comp'+s]='.true.' if count==i+1 else '.false.'
                if i<count:
                    formula=self.compound_table.item(i,0).text().strip()
                    if not formula or not all(c.isalnum() for c in formula):raise ValueError('无效化合物名 / Invalid compound name')
                    flags['two_comp'+s]='"'+formula+'"';flags['rhom'+s]=fmt(number(self.compound_table.item(i,1).text()))
            flags['dns_0']=', '.join(map(fmt,values(self.density)))
            if self.profile_page.isEnabled() and self.profile_text.toPlainText()!=self.original_profile:
                changes['rauh.inp']=profile_from_columns(self.profile_text.toPlainText(),self.data,self.owner.factor)
                flags['pr_amp']='0' # New explicit points replace, rather than add to, any analytic ripple.
            for name,(enabled,edit,key,active,original) in self.documents.items():
                on=enabled.isChecked();text=edit.toPlainText()
                flags[key]=str(active if on else (1 if key=='isbv' and self.data[key]==active else 0 if self.data[key]==active else self.data[key]))
                if on or text!=original:changes[name]=text
            # Validate the complete candidate before mutating any live widgets/files.
            from case_model import inspect_input
            tri,_=self.owner.render_inputs(*self.owner.collect());from case_model import Namelist
            _,candidate=inspect_input(Namelist(tri).patch(flags));candidate['_files']={**files,**changes}
            from case_model import validate
            errors,_,_=validate(candidate,self.fig)
            if errors:raise ValueError('\n'.join(errors))
            self.owner.set_extra_values({k:v for k,v in flags.items() if k not in ('case_e0','case_alpha','isbv','pr_amp')})
            for k in ('case_e0','case_alpha','isbv'):self.owner.mode_controls[k].setCurrentIndex(self.owner.mode_controls[k].findData(int(flags[k])))
            if 'pr_amp' in flags:self.owner.edits['pr_amp'].setText('0')
            for name,text in changes.items():self.owner.set_auxiliary_file(name,text)
            self.owner.dirty=True;self.owner.refresh();self.error.setText(self.tr('已应用到草稿；保存案例后写入文件。','Applied to draft. Save the case to write files.'))
            self.data,self.fig=self.owner.collect();self.original_profile=self.profile_text.toPlainText()
        except (ValueError,AttributeError) as e:self.error.setText(str(e))
