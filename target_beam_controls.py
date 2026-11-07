"""靶绘制页的几何信息与入射角快捷编辑，组分表仍是唯一数据源。"""
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import QLabel,QLineEdit
from element_picker import NoWheelComboBox
from case_model import number,fmt

class TargetBeamControls:
    def __init__(self,owner,form,labels):
        self.owner=owner;self.busy=False;self.token=None;self.data=None
        self.geometry=owner.geometry_display;self.geometry.setWordWrap(True)
        self.section_labels=[]
        def section(zh,en):
            label=QLabel();label.setStyleSheet('color:#136d92;font-weight:bold;margin-top:3px;')
            self.section_labels.append((label,zh,en));form.addRow(label)
        def length(key):form.addRow(labels[key],owner.edits[key])
        section('网格宽度与间距','Grid width and spacing')
        for key in ('geo_dx','geo_dz'):length(key)
        section('基底设置','Substrate settings')
        self.geometry_label=QLabel();form.addRow(self.geometry_label,self.geometry)
        for key in ('geo_x','geo_z','pr_amp','pr_wl'):length(key)
        section('束流设置','Beam settings')
        self.species_label=QLabel();self.species=NoWheelComboBox();form.addRow(self.species_label,self.species)
        self.energy_label=QLabel();self.energy=QLineEdit();self.energy.setMinimumWidth(85)
        validator=QDoubleValidator(0.,1e100,8,self.energy);validator.setNotation(QDoubleValidator.Notation.ScientificNotation);self.energy.setValidator(validator)
        self.energy.setProperty('tooltipDelayMs',500);form.addRow(self.energy_label,self.energy)
        self.angle_label=QLabel();self.angle=QLineEdit();self.angle.setMinimumWidth(85)
        validator=QDoubleValidator(-180.,180.,8,self.angle);validator.setNotation(QDoubleValidator.Notation.StandardNotation);self.angle.setValidator(validator)
        self.angle.setProperty('tooltipDelayMs',500);form.addRow(self.angle_label,self.angle)
        self.species.currentIndexChanged.connect(self.select_species);self.angle.textEdited.connect(self.edit_angle)
        self.angle.editingFinished.connect(self.finish_edit)
        self.energy.textEdited.connect(self.edit_energy);self.energy.editingFinished.connect(self.finish_energy)
        for key in ('x_start','dx_start','z_start'):length(key)

    def tr(self,zh,en):return en if getattr(self.owner,'ui_language','zh')=='en' else zh

    def sync(self,data):
        self.busy=True
        try:
            self.data=data;old=self.species.currentData();token=id(self.owner.namelist)
            if token!=self.token:old=None;self.angle.setModified(False);self.energy.setModified(False)
            self.token=token
            for label,zh,en in self.section_labels:label.setText(self.tr(zh,en))
            self.geometry_label.setText(self.tr('当前几何类型','Current geometry'))
            self.geometry.setText(self.owner.geometry.currentText());self.geometry.setToolTip(self.owner.geometry.toolTip())
            self.species_label.setText(self.tr('入射组分','Incident species'))
            blocked=self.species.blockSignals(True);self.species.clear()
            rows=[i for i,q in enumerate(data['qu_beam']) if q>0]
            for i in rows:self.species.addItem(f"{data['symbol'][i]} (#{i+1})",i)
            if old in rows:self.species.setCurrentIndex(self.species.findData(old))
            self.species.blockSignals(blocked)
            multiple=len(rows)>1;self.species_label.setVisible(multiple);self.species.setVisible(multiple)
            self.show_angle()
        finally:self.busy=False

    def select_species(self,*args):
        if not self.busy:
            self.angle.setModified(False);self.energy.setModified(False);self.show_angle();self.owner.refresh()

    def show_angle(self):
        data=self.data
        if data is None:return
        row=self.species.currentData();mode=int(data['case_alpha'])
        energy_mode=int(data['case_e0'])
        energy_label=('束流能量 / eV','Beam energy / eV')
        if energy_mode in (2,3):energy_label=('温度能量 kT / eV','Thermal energy kT / eV')
        elif energy_mode==5:energy_label=('能量中心 / eV','Energy center / eV')
        self.energy_label.setText(self.tr(*energy_label))
        if not (self.energy.hasFocus() and self.energy.isModified()):
            self.energy.setText(fmt(data['e0_beam'][row]) if row is not None else '')
        self.energy.setEnabled(row is not None and energy_mode in (0,2,3,5))
        self.energy.setToolTip(self.tr('同步所选入射组分的 e0_beam。固定模式为粒子能量，高斯模式为中心，麦克斯韦模式为温度能量 kT；文件分布模式从 energy.inp 读取。','Edits e0_beam for the selected incident species: fixed particle energy, Gaussian center, or Maxwellian thermal energy kT. File-distribution mode reads energy.inp.'))
        label=('入射角 / °','Incidence angle / °')
        if mode==1:label=('入射角上限 / °','Angle upper limit / °')
        elif mode==5:label=('入射角中心 / °','Angle center / °')
        self.angle_label.setText(self.tr(*label))
        blocked=self.angle.blockSignals(True)
        if not (self.angle.hasFocus() and self.angle.isModified()):
            self.angle.setText(fmt(data['alpha0'][row]) if row is not None else '')
        self.angle.blockSignals(blocked)
        used=mode in (0,1,5) and int(data['case_e0']) not in (2,3) and row is not None
        self.angle.setEnabled(used)
        if int(data['case_e0']) in (2,3):
            tip=self.tr('当前麦克斯韦能量模式会重新计算方向，alpha0 不控制实际入射角。','The current Maxwellian energy mode recalculates direction; alpha0 does not control the actual angle.')
        elif mode not in (0,1,5):
            tip=self.tr('当前角度由内置分布或 angle.inp 决定；请在参数页选择固定角度、极角均匀或高斯角度模式后调节。','This angle mode uses a built-in distribution or angle.inp. Choose Fixed, Uniform polar or Gaussian angle on the input page to edit alpha0 here.')
        else:
            tip=self.tr('同步所选入射组分的 alpha0。0° 沿参考表面法线入射；极角均匀模式为上限，高斯模式为中心。','Edits alpha0 for the selected incident species. 0° is along the reference surface normal; Uniform polar uses an upper limit and Gaussian uses a center.')
        self.angle.setToolTip(tip)

    def edit_angle(self,text):
        if self.busy or self.owner.loading or not self.angle.isEnabled() or not self.angle.hasAcceptableInput():return
        try:value=number(text)
        except ValueError:return
        row=self.species.currentData()
        if row is None:return
        item=self.owner.species.item(row,3)
        if item is not None and number(item.text())!=value:
            item.setText(fmt(value));self.data['alpha0'][row]=value

    def finish_edit(self):
        if self.busy or self.owner.loading:return
        self.edit_angle(self.angle.text());self.angle.setModified(False)
        self.owner.refresh()

    def edit_energy(self,text):
        if self.busy or self.owner.loading or not self.energy.isEnabled() or not self.energy.hasAcceptableInput():return
        try:value=number(text)
        except ValueError:return
        row=self.species.currentData()
        if row is None:return
        item=self.owner.species.item(row,2)
        if item is not None and number(item.text())!=value:
            item.setText(fmt(value));self.data['e0_beam'][row]=value

    def finish_energy(self):
        if self.busy or self.owner.loading:return
        self.edit_energy(self.energy.text());self.energy.setModified(False);self.owner.refresh()
