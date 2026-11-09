"""从当前安装的 table1 读取材料；不构造内核不认识的同位素名称。"""
from dataclasses import dataclass
from element_colors import periodic_color,tint_species_item
from pathlib import Path
import re
from PySide6.QtCore import Qt,QEvent
from PySide6.QtWidgets import (QComboBox, QDialog, QVBoxLayout, QHBoxLayout,
    QGridLayout, QWidget, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QDialogButtonBox)

TABLE_PATH = None
SYMBOLS = ('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn '
           'Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce '
           'Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At '
           'Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr').split()
SPECIAL = {'H':'氢 / 表内质量', 'H2':'质量与 D 相同的表内别名', 'D':'氘 / 氢-2',
           'T':'氚 / 氢-3', 'He3':'氦-3', 'He':'氦 / 表内质量',
           'B10':'硼-10', 'B11':'硼-11'}

class NoWheelComboBox(QComboBox):
    """关闭下拉框时滚轮交给父控件，不修改当前选项。"""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.installEventFilter(self)
    def eventFilter(self,obj,event):
        # Qt bypasses wheelEvent for disabled widgets; keep the same no-change rule there.
        if obj is self and event.type()==QEvent.Type.Wheel and not self.isEnabled():event.ignore();return True
        return super().eventFilter(obj,event)
    def wheelEvent(self, event):
        event.ignore()

@dataclass(frozen=True)
class Material:
    symbol: str
    z: int
    mass: float
    density: float
    atomic_density: float

    @property
    def description(self):
        if self.mass is None:return '标准元素符号（未配置材料表）'
        if self.symbol in SPECIAL:
            return SPECIAL[self.symbol]
        if self.symbol != SYMBOLS[self.z-1]:
            return '材料 / 表内变体'
        return '元素 / 表内质量'

def read_materials(path=None):
    """主表之后的 old/new 和 also 段是说明，不能当成可选材料。"""
    if path is None:
        path=TABLE_PATH
        if path is None or not Path(path).is_file():
            return [Material(symbol,z,None,None,None) for z,symbol in enumerate(SYMBOLS,1)]
    entries = []
    seen = set()
    for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        stripped = line.strip()
        if stripped.startswith(('old ', 'new ', '---', 'also:')):
            if entries:
                break
        parts = line.split()
        if len(parts) < 14 or not re.fullmatch(r'\d+', parts[1]):
            continue
        try:
            entry = Material(parts[0], int(parts[1]), *[float(v) for v in parts[2:5]])
        except ValueError:
            continue
        if 1 <= entry.z <= len(SYMBOLS) and entry.symbol not in seen:
            entries.append(entry)
            seen.add(entry.symbol)
    if not entries:
        raise ValueError('材料主表为空或格式无法识别：'+str(path))
    return entries

def periodic_positions():
    yield 1, 0, 0
    yield 2, 0, 17
    for start, row in ((3,1),(11,2)):
        for offset,col in enumerate((0,1,12,13,14,15,16,17)):
            yield start+offset,row,col
    for start,row in ((19,3),(37,4)):
        for col in range(18):
            yield start+col,row,col
    for start,row,fstart,frow in ((55,5,57,8),(87,6,89,9)):
        yield start,row,0
        yield start+1,row,1
        for offset in range(15):
            yield fstart+offset,frow,offset+2
        for offset in range(15):
            z=fstart+15+offset
            if z <= 103:
                yield z,row,offset+3

class ElementDialog(QDialog):
    def __init__(self, current='', parent=None, materials=None):
        super().__init__(parent)
        self.setWindowTitle('选择元素 / 同位素 / 材料条目')
        self.resize(1160,650)
        self.materials = list(materials if materials is not None else read_materials())
        self.by_symbol = {m.symbol:m for m in self.materials}
        self.by_z = {}
        for m in self.materials:
            self.by_z.setdefault(m.z,[]).append(m)
        self.selected_symbol = None
        self.current_symbol = current
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText('搜索材料名、元素符号或原子序数，如 D、He3、C_g、W、74')
        layout.addWidget(self.search)
        body = QHBoxLayout(); layout.addLayout(body,1)
        grid_widget=QWidget(); grid=QGridLayout(grid_widget)
        grid.setSpacing(3); grid.setContentsMargins(0,8,8,8)
        body.addWidget(grid_widget,3)
        self.buttons={}
        for z,row,col in periodic_positions():
            button=QPushButton(f'{z}\n{SYMBOLS[z-1]}')
            button.setMinimumSize(36,43)
            button.setStyleSheet('QPushButton {padding:2px; background:'+(
                periodic_color(z))+';}')
            button.setEnabled(z in self.by_z)
            button.setToolTip(' / '.join(m.symbol for m in self.by_z.get(z,[])))
            button.clicked.connect(lambda checked=False,z=z:self.select_element(z))
            grid.addWidget(button,row,col); self.buttons[z]=button
        grid.addWidget(QLabel('镧系'),8,0,1,2)
        grid.addWidget(QLabel('锕系'),9,0,1,2)
        side=QVBoxLayout(); body.addLayout(side,2)
        self.heading=QLabel(); side.addWidget(self.heading)
        self.entries=QTableWidget(0,3)
        self.entries.setObjectName('material_entries')
        self.entries.setHorizontalHeaderLabels(['表内名称','质量 / u','类型'])
        self.entries.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.entries.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.entries.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.entries.verticalHeader().hide()
        self.entries.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.entries.horizontalHeader().setStretchLastSection(True)
        side.addWidget(self.entries,1)
        self.details=QLabel(); self.details.setWordWrap(True); side.addWidget(self.details)
        note=QLabel(('未配置材料表：可选择标准元素符号进行编辑；运行前需用外部 table1 核验。' if any(m.mass is None for m in self.materials) else
                    '列表只提供本机 table1 的有效名称；材料变体不是同位素。\n'
                    'H2 在此表中的质量与 D 相同（2.014083 u）。\n'
                    '这里只选择单个表内条目，不自动展开天然同位素混合物。'))
        note.setWordWrap(True); layout.addWidget(note)
        self.button_box=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText('使用所选条目')
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText('取消')
        layout.addWidget(self.button_box)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.entries.currentCellChanged.connect(self.show_details)
        self.entries.cellDoubleClicked.connect(lambda *_:self.accept())
        self.search.textChanged.connect(self.filter_entries)
        self.search.returnPressed.connect(self.accept)
        self.select_element(self.by_symbol[current].z if current in self.by_symbol else 1,current)

    def populate(self,entries,preferred=''):
        self.entries.setRowCount(0)
        for row,m in enumerate(entries):
            self.entries.insertRow(row)
            for col,value in enumerate((m.symbol,f'{m.mass:g}' if m.mass is not None else '—',m.description)):
                item=QTableWidgetItem(value)
                if col==0:
                    item.setData(Qt.ItemDataRole.UserRole,m.symbol);tint_species_item(item,m.symbol)
                self.entries.setItem(row,col,item)
        selected=next((i for i,m in enumerate(entries) if m.symbol==preferred),0)
        if entries: self.entries.setCurrentCell(selected,0)
        self.show_details()

    def select_element(self,z,preferred=''):
        self.search.blockSignals(True); self.search.clear(); self.search.blockSignals(False)
        self.heading.setText(f'{SYMBOLS[z-1]} · Z = {z} · 同位素 / 材料条目')
        for number,button in self.buttons.items():
            button.setCheckable(True)
            button.setChecked(number==z)
        self.populate(self.by_z.get(z,[]),preferred)

    def filter_entries(self,text):
        query=text.strip().lower()
        if not query:
            self.heading.setText('全部可用条目')
            self.populate(self.materials,self.current_symbol)
            return
        exact=self.by_symbol.get(text.strip())
        if exact:
            entries=self.by_z[exact.z]
        else:
            entries=[m for m in self.materials if query in m.symbol.lower()
                     or query==str(m.z) or query==SYMBOLS[m.z-1].lower()]
        self.heading.setText(f'搜索结果 · {len(entries)} 个条目')
        self.populate(entries,exact.symbol if exact else '')

    def show_details(self,*args):
        item=self.entries.item(self.entries.currentRow(),0)
        symbol=item.data(Qt.ItemDataRole.UserRole) if item else None
        m=self.by_symbol.get(symbol)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(m is not None)
        self.details.setText((f'{m.symbol} · Z={m.z}\n'+('未配置材料表；此处不提供质量或密度数据。' if m.mass is None else
            f'质量：{m.mass:.6f} u\n'
            f'质量密度：{m.density:g} g/cm³\n原子数密度：{m.atomic_density:g} atoms/Å³\n'
            '数据来源：已配置的外部计算内核材料表')) if m else '没有匹配的条目。')
        owner=self.parent()
        if owner is not None and hasattr(owner,'interface_language'):
            owner.interface_language.apply(self)

    def accept(self):
        item=self.entries.item(self.entries.currentRow(),0)
        if item:
            self.selected_symbol=item.data(Qt.ItemDataRole.UserRole)
            super().accept()
