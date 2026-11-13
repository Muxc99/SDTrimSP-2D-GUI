"""从明确、可编辑的起始参数创建内存案例，不读取或复制已有算例。"""
import re
from PySide6.QtGui import QShortcut,QKeySequence
from PySide6.QtWidgets import QDialog,QVBoxLayout,QFormLayout,QLineEdit,QLabel,QDialogButtonBox,QCheckBox,QMessageBox,QPushButton
from element_picker import ElementDialog
from case_model import ELEMENTS,GEOMETRIES,inspect_input,Figure,Profile,validate,number,fmt
from mode_hints import ModeComboBox


def initial_inputs(name,beam,target,width,depth,dx,dz,energy,angle,z_start,mirror=False,geometry=26):
    if not name.strip():raise ValueError('请填写案例名称。')
    if any(c in name for c in ('\n','\r')):raise ValueError('案例名称不能包含换行。')
    if beam not in ELEMENTS or target not in ELEMENTS:raise ValueError('请选择本机材料表支持的元素 / 同位素。')
    if geometry not in GEOMETRIES:raise ValueError('Unsupported geometry / 不支持的几何类型。')
    if geometry==10:dx=width
    symbols=[beam] if beam==target else [beam,target];n=len(symbols)
    beam_q=[1.]+[0.]*(n-1);base_q=[1.] if n==1 else [0.,1.]
    fields={
        'ncp':str(n),'symbol':', '.join('"'+v+'"' for v in symbols),
        'qu_beam':', '.join(fmt(v) for v in beam_q),'e0_beam':', '.join(fmt(energy if i==0 else 0.) for i in range(n)),
        'alpha0':', '.join(fmt(angle if i==0 else 0.) for i in range(n)),
        'qu_tar':', '.join(fmt(v) for v in base_q),'qu_max':', '.join('1' for _ in symbols),
        'case_geo':str(geometry),'geo_x':fmt(width/2),'geo_z':fmt(-depth),'geo_dx':fmt(dx),'geo_dz':fmt(dz),
        'case_start':'3' if geometry==10 else '4','case_e0':'0','case_alpha':'0','x_start':'0','dx_start':fmt(width),'z_start':fmt(z_start),
        'pr_amp':'0','pr_wl':'1','flc':'1','maxhist':'100','ihist_out':'10','nr_pproj':'64',
        'tar_dynamic':'.true.','ipot':'1','isbv':'1'}
    tri=name.strip()+'\n! Editable starting parameters; set values for the intended irradiation.\n&INPUT\n'
    tri+=''.join('    '+key+' = '+value+'\n' for key,value in fields.items())+'/\n'
    fig=Figure(int(bool(mirror)),1,[]).render()
    files={'fig.inp':fig,'stop_run.inp':'0\n'}
    if geometry in (24,25):
        x1,x2=(0.,width) if geometry==24 else (-width/2,width/2)
        files['rauh.inp']=Profile([[x1,0.],[x2,0.]]).render()
    nl,data=inspect_input(tri);data['_files']=files
    errors,_,_=validate(data,Figure.parse(fig,n) if geometry==26 else None)
    if errors:raise ValueError('\n'.join(errors))
    return {'tri.inp':tri,**files}


class NewCaseSpeciesButton(QPushButton):
    """复用主窗口的周期表与同位素/材料条目选择器。"""
    def __init__(self,value,dialog):
        super().__init__(dialog);self.dialog=dialog;self._symbol=value
        self.setStyleSheet('text-align:left;');self.setCurrentText(value)
        self.clicked.connect(self.choose)

    def currentText(self):return self._symbol

    def setCurrentText(self,value):
        self._symbol=value;self.setText(value+' …')
        self.setToolTip(self.dialog.owner.raw_text('点击打开元素 / 同位素 / 材料选择器','Click to choose an element / isotope / material'))

    def choose(self):
        try:picker=ElementDialog(self._symbol,self.dialog)
        except (OSError,ValueError) as error:
            QMessageBox.warning(self.dialog,self.dialog.owner.raw_text('材料表读取失败','Material table error'),str(error));return
        if picker.exec()==QDialog.DialogCode.Accepted and picker.selected_symbol:
            self.setCurrentText(picker.selected_symbol)


class NewCaseDialog(QDialog):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.factor=owner.factor;self.payload=None
        self.interface_language=owner.interface_language
        self.setWindowTitle(owner.raw_text('新建案例','New case'));self.setMinimumWidth(490)
        layout=QVBoxLayout(self);note=QLabel(owner.raw_text('选择几何类型，从空白基底开始；下列初始值仅用于建模起步，请按实际工况修改。',
          'Choose a geometry and start with a blank substrate. Initial values are editable starting points; set them for your intended conditions.'))
        note.setWordWrap(True);layout.addWidget(note);form=QFormLayout();layout.addLayout(form)
        self.name_edit=QLineEdit('New_case');form.addRow(owner.raw_text('案例名称','Case name'),self.name_edit)
        self.geometry=ModeComboBox('case_geo',self);self.geometry.set_language(owner.ui_language)
        self.geometry.setCurrentIndex(max(0,self.geometry.findData(owner.geometry.currentData())))
        form.addRow(owner.raw_text('几何类型','Geometry type'),self.geometry)
        self.beam=NewCaseSpeciesButton('Ar',self);self.target=NewCaseSpeciesButton('W',self)
        form.addRow(owner.raw_text('入射元素 / 同位素','Incident species / isotope'),self.beam)
        form.addRow(owner.raw_text('基底元素 / 同位素','Substrate species / isotope'),self.target)
        self.edits={};unit=owner.unit.currentText()
        for key,zh,en,value in [('width','靶区总宽','Target width',400.),('depth','基底厚度','Substrate thickness',200.),
             ('dx','横向网格间距','Mesh spacing x',25.),('dz','竖向网格间距','Mesh spacing z',25.),('z_start','入射起始高度','Starting height',500.)]:
            edit=QLineEdit(fmt(value/self.factor));self.edits[key]=edit;form.addRow(owner.raw_text(zh,en)+' / '+unit,edit)
        for key,zh,en,value in [('energy','入射能量 / eV','Incident energy / eV',100.),('angle','入射角 / °','Incident angle / °',0.)]:
            edit=QLineEdit(fmt(value));self.edits[key]=edit;form.addRow(owner.raw_text(zh,en),edit)
        self.mirror=QCheckBox(owner.raw_text('关于 x=0 左右镜像','Mirror about x=0'));form.addRow(self.mirror)
        self.hint=hint=QLabel()
        hint.setWordWrap(True);layout.addWidget(hint);self.error=QLabel();self.error.setWordWrap(True);self.error.setStyleSheet('color:#c00000');layout.addWidget(self.error)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(owner.raw_text('创建','Create'))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(owner.raw_text('取消','Cancel'))
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
        self._previous_dx=self.edits['dx'].text();self._was_1d=False
        self.geometry.currentIndexChanged.connect(self.update_geometry)
        self.edits['width'].textChanged.connect(lambda text:self.edits['dx'].setText(text) if self.geometry.currentData()==10 else None)
        self.update_geometry()

    def update_geometry(self,*args):
        mode=self.geometry.currentData();one=mode==10
        if one:
            if not self._was_1d:self._previous_dx=self.edits['dx'].text()
            self.edits['dx'].setText(self.edits['width'].text())
        elif self._was_1d:self.edits['dx'].setText(self._previous_dx)
        self.edits['dx'].setEnabled(not one);self._was_1d=one;self.mirror.setEnabled(mode==26)
        notes={
            10:('一维平面：横向只有一个网格，geo_dx 自动等于靶总宽，采用固定坐标起射。','1D flat: one lateral cell. geo_dx automatically equals the full width; the starting position is fixed.'),
            20:('二维平面基底，初始为矩形。创建后可拖动角点和边调整尺寸，不可增加节点。','2D flat substrate, initially a rectangle. Drag corners and edges to resize; nodes cannot be added.'),
            24:('基底初始为闭合矩形，可在上边界加点、拖动。自动生成 rauh.inp，文件 x 从左边界起算。','Starts as a closed rectangle. Add and drag upper-edge nodes. rauh.inp is generated with x measured from the left edge.'),
            25:('基底初始为闭合矩形，可在上边界加点、拖动。自动生成 rauh.inp，文件 x 以靶中心为零。','Starts as a closed rectangle. Add and drag upper-edge nodes. rauh.inp is generated with x centered on the target.'),
            26:('平面基底＋矩形块，初始不含凸起。可调整基底尺寸，已有材料块不会自动缩放。','Flat substrate plus rectangular blocks, initially without protrusions. Resize the substrate; existing blocks are not scaled.'),
            27:('余弦表面：初始 pr_amp=0；创建后设置 pr_amp、pr_wl。调整宽度时需兼容波长，不可增加节点。','Cosine surface: initially pr_amp=0; set pr_amp and pr_wl after creation. Width changes must match the wavelength; nodes cannot be added.')}
        text=self.owner.raw_text(*notes[mode])
        if not one:text+='\n'+self.owner.raw_text('总宽须为横向网格间距的偶数倍。','Width must be an even multiple of mesh spacing x.')
        self.hint.setText(text)

    def accept(self):
        try:
            args={key:number(edit.text())*(self.factor if key in ('width','depth','dx','dz','z_start') else 1.) for key,edit in self.edits.items()}
            if args['width']<=0 or args['depth']<=0:raise ValueError(self.owner.raw_text('总宽和基底厚度必须大于零。','Width and substrate thickness must be positive.'))
            self.payload=initial_inputs(self.name_edit.text(),self.beam.currentText(),self.target.currentText(),mirror=self.mirror.isChecked(),geometry=self.geometry.currentData(),**args)
            if not self.owner.create_new_case(self.payload):return
        except (ValueError,OverflowError) as error:self.error.setText(str(error));return
        super().accept()


class NewCaseActions:
    def new_case(self):
        if self.process is not None:
            QMessageBox.information(self,self.raw_text('计算仍在运行','Calculation running'),self.raw_text('请先停止并等待当前计算结束，再新建案例。','Stop and wait for the current calculation to finish before creating a case.'));return
        if self.dirty:
            reply=QMessageBox.question(self,self.raw_text('尚未保存的修改','Unsaved changes'),
                self.raw_text('当前有未保存的修改。放弃这些修改并新建案例吗？','Discard current unsaved changes and create a new case?'),
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
            if reply!=QMessageBox.StandardButton.Yes:return
        self.new_case_dialog=NewCaseDialog(self);self.new_case_dialog.open()

    def create_new_case(self,payload):
        if self.process is not None:raise ValueError(self.raw_text('请等待当前计算结束。','Wait for the current calculation to finish.'))
        _,d=inspect_input(payload['tri.inp']);fig=Figure.parse(payload['fig.inp'],int(d['ncp'])) if d['case_geo']==26 else None;d['_files']={k:v for k,v in payload.items() if k!='tri.inp'}
        errors,_,_=validate(d,fig)
        if errors:raise ValueError('\n'.join(errors))
        self.timer.stop();self.removed_files.clear();self.raw_applying=True;self.reset_raw_history=True
        try:
            if not self.load_case(None,overrides=payload):return False
            e=self.target_editor;e.cancel_gesture();e.undo_stack.clear();e.redo_stack.clear();e.clipboard=None;e.selection_anchor=None;e.select_cells([]);e.fit_view();e.update_history_buttons()
            self.last_export=None;self.run_directory=None;self.results_button.setEnabled(False);self.log.clear();self.dirty=True
            self.tabs.setCurrentWidget(e)
            self.statusBar().showMessage(self.raw_text('新建案例已就绪；绘制和编辑后请另存为新目录。','New case ready. Draw/edit, then save to a new folder.'),9000)
            return True
        finally:self.raw_applying=False;self.reset_raw_history=False

    def case_basename(self):
        if self.source is not None:return self.source.name
        value=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',self.title_edit.text()).strip(' .')[:80]
        return value or 'New_case'
