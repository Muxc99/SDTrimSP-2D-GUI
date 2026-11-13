"""GUI-owned layer documents; all serialized coordinates remain in Angstrom."""
import math
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QTabWidget,QWidget,
    QCheckBox,QTableWidget,QTableWidgetItem,QPushButton,QLabel,QDialogButtonBox,QHeaderView)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from case_model import parse_layers,number,fmt,surface_profile

LAYER_FILES={'initial_composition.inp':'iq0','initial_composition_surf.inp':'iq0_surf'}

def render_layers(rows,ncp):
    if not rows:raise ValueError('至少需要一层 / At least one layer is required.')
    lines=['Layer boundaries (Angstrom), atomic fractions',str(len(rows)),fmt(rows[0][0])]
    previous=rows[0][0]
    for upper,lower,q in rows:
        if not math.isclose(upper,previous,abs_tol=1e-8):
            raise ValueError('相邻层边界须连续 / Layer boundaries must be contiguous.')
        lines+=[' '.join(fmt(v) for v in q),fmt(lower)];previous=lower
    text='\n'.join(lines)+'\n';parse_layers(text,ncp)
    return text

def default_layer_rows(data,files,surface=False):
    if surface:return [(0.,-max(data['geo_dz'],100.),list(data['qu_tar']))]
    top=float(max(surface_profile(data,files)[1]))
    return [(top,data['geo_z'],list(data['qu_tar']))]

class LayerPage(QWidget):
    def __init__(self,dialog,name):
        super().__init__();self.dialog=dialog;self.name=name;self.drag=None;self.busy=False
        self.surface=name.endswith('_surf.inp');owner=dialog.owner;tr=owner.raw_text
        layout=QVBoxLayout(self)
        self.enabled=QCheckBox(tr('启用此分层','Enable these layers'));self.enabled.setChecked(dialog.data.get(LAYER_FILES[name],0)>0);layout.addWidget(self.enabled)
        note=QLabel(tr('距局部表面的竖直偏移：表面为 0，向下为负。表面层覆盖体分层。',
            'Vertical offsets below the local surface: 0 at surface, negative below. Surface layers override bulk layers.') if self.surface else
            tr('绝对 z 坐标：从上到下递减；未覆盖区域使用基底成分。',
               'Absolute z coordinates decrease downwards. Uncovered regions use substrate composition.'))
        note.setText(note.text()+'\n'+tr('连续示意；内核按网格单元分层。当前竖向网格：','Continuous schematic; kernel layers follow cells. Current vertical grid: ')+fmt(dialog.data['geo_dz']/owner.factor)+' '+owner.unit.currentText())
        note.setWordWrap(True);layout.addWidget(note)
        self.table=QTableWidget(0,2+len(dialog.data['symbol']))
        self.table.setHorizontalHeaderLabels([tr('上边界','Upper')+' / '+owner.unit.currentText(),tr('下边界','Lower')+' / '+owner.unit.currentText()]+dialog.data['symbol'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table,2)
        row=QHBoxLayout();layout.addLayout(row)
        for zh,en,slot in [('增加层','Add layer',self.add_layer),('删除层','Remove layer',self.remove_layer)]:
            b=QPushButton(tr(zh,en));b.clicked.connect(slot);row.addWidget(b)
        self.figure=Figure(figsize=(7,2.6));self.canvas=FigureCanvasQTAgg(self.figure);layout.addWidget(self.canvas,2)
        self.error=QLabel();self.error.setStyleSheet('color:#b42318');self.error.setWordWrap(True);layout.addWidget(self.error)
        self.canvas.mpl_connect('button_press_event',self.press)
        self.canvas.mpl_connect('motion_notify_event',self.motion)
        self.canvas.mpl_connect('button_release_event',self.release)
        text=owner.current_files().get(name)
        rows=parse_layers(text,len(dialog.data['symbol'])) if text else default_layer_rows(dialog.data,owner.current_files(),self.surface)
        self.fill(rows);self.table.itemChanged.connect(self.edited)

    def fill(self,rows):
        self.busy=True;self.table.setRowCount(len(rows))
        for i,(up,low,q) in enumerate(rows):
            for j,v in enumerate([up/self.dialog.owner.factor,low/self.dialog.owner.factor]+list(q)):
                self.table.setItem(i,j,QTableWidgetItem(fmt(v)))
        self.busy=False;self.edited()

    def rows(self):
        f=self.dialog.owner.factor
        rows=[]
        for i in range(self.table.rowCount()):
            values=[number(self.table.item(i,j).text()) for j in range(self.table.columnCount())]
            rows.append((values[0]*f,values[1]*f,values[2:]))
        render_layers(rows,len(self.dialog.data['symbol']))
        if self.surface and rows[0][0]>0:raise ValueError('表面层坐标须 ≤ 0 / Surface offsets must be <= 0.')
        return rows

    def edited(self,item=None):
        if self.busy:return
        if item is not None and item.column() in (0,1):
            r=item.row();neighbor=(r-1,1) if item.column()==0 else (r+1,0)
            if 0<=neighbor[0]<self.table.rowCount():
                self.busy=True
                self.table.item(*neighbor).setText(item.text());self.busy=False
        try:rows=self.rows()
        except (ValueError,AttributeError) as e:self.error.setText(str(e));return
        self.error.clear();self.figure.clear();self.ax=self.figure.add_subplot(111)
        from matplotlib.patches import Rectangle
        from element_colors import species_color
        f=self.dialog.owner.factor
        for i,(up,low,q) in enumerate(rows):
            x=0.
            for symbol,frac in zip(self.dialog.data['symbol'],q):
                if frac>0:
                    self.ax.add_patch(Rectangle((x,low/f),frac,(up-low)/f,facecolor=species_color(symbol),edgecolor='white'))
                    if frac>.12 and (up-low)>.09*(rows[0][0]-rows[-1][1]):self.ax.text(x+frac/2,(up+low)/2/f,symbol,ha='center',va='center')
                x+=frac
            self.ax.axhline(low/f,color='#555',picker=6)
        self.ax.set_xlim(0,1);self.ax.set_ylim(rows[-1][1]/f,rows[0][0]/f);self.ax.set_xlabel(self.dialog.owner.raw_text('原子分数（可拖动内部分界线）','Atomic fraction (drag internal boundaries)'))
        self.figure.subplots_adjust(left=.14,bottom=.23,top=.94,right=.97);self.canvas.draw_idle()

    def add_layer(self):
        try:
            rows=self.rows();up,low,q=rows[-1];mid=(up+low)/2
            rows[-1]=(up,mid,q);rows.append((mid,low,list(q)));self.fill(rows);self.enabled.setChecked(True)
        except ValueError as e:self.error.setText(str(e))

    def remove_layer(self):
        try:
            rows=self.rows();i=self.table.currentRow()
            if len(rows)<=1:return
            i=max(0,i)
            if i==0:rows[1]=(rows[0][0],rows[1][1],rows[1][2])
            else:rows[i-1]=(rows[i-1][0],rows[i][1],rows[i-1][2])
            rows.pop(i);self.fill(rows)
        except ValueError as e:self.error.setText(str(e))

    def press(self,event):
        if event.button!=1 or event.inaxes is not getattr(self,'ax',None):return
        try:rows=self.rows()
        except ValueError:return
        f=self.dialog.owner.factor
        hits=[(abs(self.ax.transData.transform((0,rows[i][1]/f))[1]-event.y),i) for i in range(len(rows)-1)]
        if hits and min(hits)[0]<9:self.drag=min(hits)[1]

    def motion(self,event):
        if self.drag is None or event.inaxes is not self.ax or event.ydata is None:return
        rows=self.rows();i=self.drag;step=self.dialog.data['geo_dz'];value=round(event.ydata*self.dialog.owner.factor/step)*step
        if rows[i+1][1]<value<rows[i][0]:
            rows[i]=(rows[i][0],value,rows[i][2]);rows[i+1]=(value,rows[i+1][1],rows[i+1][2]);self.fill(rows)

    def release(self,event):self.drag=None

class LayerDialog(QDialog):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.data,_=owner.collect();self.setWindowTitle(owner.raw_text('分层成分编辑','Layer composition editor'));self.resize(900,700)
        layout=QVBoxLayout(self);tabs=QTabWidget();layout.addWidget(tabs);self.pages=[]
        for name,zh,en in [('initial_composition.inp','体分层（绝对 z）','Bulk layers (absolute z)'),('initial_composition_surf.inp','表面分层（相对深度）','Surface layers (relative depth)')]:
            page=LayerPage(self,name);self.pages.append(page);tabs.addTab(page,owner.raw_text(zh,en))
        self.error=QLabel();self.error.setStyleSheet('color:#b42318');layout.addWidget(self.error)
        box=QDialogButtonBox(QDialogButtonBox.StandardButton.Apply|QDialogButtonBox.StandardButton.Close);layout.addWidget(box)
        box.button(QDialogButtonBox.StandardButton.Apply).setText(owner.raw_text('应用到靶结构','Apply to target'))
        box.button(QDialogButtonBox.StandardButton.Close).setText(owner.raw_text('关闭','Close'))
        box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply);box.rejected.connect(self.reject)

    def apply(self):
        try:
            changes={};flags={}
            for page in self.pages:
                flags[LAYER_FILES[page.name]]=str(int(page.enabled.isChecked()))
                if page.enabled.isChecked() or page.name in self.owner.current_files():changes[page.name]=render_layers(page.rows(),len(self.data['symbol']))
            for name,text in changes.items():self.owner.set_auxiliary_file(name,text)
            self.owner.set_extra_values(flags);self.owner.dirty=True;self.owner.refresh();self.error.clear()
        except ValueError as e:self.error.setText(str(e))
