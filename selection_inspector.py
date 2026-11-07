"""绘图选择信息与固定原子分数色标；只读，不改动输入数据。"""
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QPainter,QColor,QLinearGradient,QPen,QFont
from PySide6.QtWidgets import QWidget,QLabel
from case_model import fmt

class AtomicFractionScale(QWidget):
    def mouseDoubleClickEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.editor.owner.initial_gradients.edit(self.editor.canvas)
    def __init__(self,editor):
        super().__init__(editor);self.editor=editor;self.symbol='';self.setFixedWidth(72);self.setMinimumHeight(220)
        self.setAccessibleName('Atomic fraction color scale')
    def sync(self,symbol):
        self.symbol=symbol;self.setToolTip(self.editor.text('原子分数范围为 0 到 1；双击色条可调整颜色渐变，与初始靶预览同步。白色空白区不表示零浓度材料。','Atomic fraction ranges from 0 to 1. Double-click the color scale to edit the gradient, shared with the initial target preview. Blank white space is not zero-fraction material.'));self.update()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setPen(QColor('#24364b'))
        font=QFont(self.font());font.setPointSize(9);p.setFont(font)
        p.drawText(QRectF(0,8,self.width(),22),Qt.AlignmentFlag.AlignCenter,self.symbol)
        p.drawText(QRectF(0,29,self.width(),22),Qt.AlignmentFlag.AlignCenter,self.editor.text('原子分数','Fraction'))
        top=62.;height=max(90.,self.height()-98.);bar=QRectF(8,top,15,height)
        gradient=QLinearGradient(0,top+height,0,top);cmap=self.editor.owner.initial_gradients.colormap(self.symbol)
        for i in range(257):gradient.setColorAt(i/256,QColor.fromRgbF(*cmap(i/256)))
        p.fillRect(bar,gradient);p.setPen(QPen(QColor('#637888'),.8));p.drawRect(bar)
        for i in range(6):
            q=i/5;y=top+(1-q)*height;p.drawLine(24,int(y),28,int(y));p.drawText(QRectF(31,y-10,39,20),Qt.AlignmentFlag.AlignVCenter,fmt(q))
        p.end()

class SelectionInspector:
    def init_inspector(self):
        self.selection_info=QLabel();self.selection_info.setObjectName('selectionInfo');self.selection_info.setWordWrap(True)
        self.selection_info.setTextFormat(Qt.TextFormat.PlainText);self.selection_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.selection_info.setMinimumWidth(315);self.selection_info.setMaximumWidth(465);self.selection_info.setMinimumHeight(96)
        self.selection_info.setStyleSheet('QLabel#selectionInfo {background:#f1f6fa;border:1px solid #bdcedc;border-radius:5px;padding:6px;font-size:9pt;}')
        self.fraction_scale=AtomicFractionScale(self)
    def update_inspector(self):
        if self.data is None:return
        symbol=self.owner.color_species.currentText();self.fraction_scale.sync(symbol)
        key=self.active_cell
        if key is None or not self.selected_cells:
            text=self.text('色块信息\n选择一个材料格，查看位置、尺寸和各元素原子分数。\n空白格也可选择；多选时显示当前活动格。','Cell information\nSelect a material cell to view its position, size and atomic fractions.\nEmpty cells can also be selected; multiple selection shows the active cell.')
        else:
            rows=self.rows();occupied=self.cell_occupancy();canonical=self.canonical_key(key);row=occupied.get(canonical)
            bounds=self.cell_bounds(key);material=row is not None
            if material:
                r=rows[row];bounds=r[:4]
                if canonical!=key:bounds=[-r[1],-r[0],r[2],r[3]]
                fractions=r[4:] if self.owner.with_qu.isChecked() else self.data['qu_tar']
                label=self.text(f'色块 #{row+1}',f'Block #{row+1}')
                composition=self.text('原子分数：','Fractions: ')+ '  '.join(f'{s}={fmt(q)}' for s,q in zip(self.data['symbol'],fractions))
            else:
                label=self.text('空白格','Empty cell');composition=self.text('无材料；原子分数不适用。','No material; atomic fractions do not apply.')
            f=self.owner.factor;a,b,c,d=[v/f for v in bounds];unit=self.owner.unit.currentText()
            total=len(self.selected_cells);count=len({occupied[k] for k in self.canonical_cells() if k in occupied})
            heading=label if total==1 else self.text(f'已选 {total} 格 / {count} 个材料块 · 当前：{label}',f'{total} cells / {count} material blocks · Active: {label}')
            coordinates=f'x: {fmt(a)} ～ {fmt(b)}   z: {fmt(c)} ～ {fmt(d)} {unit}'
            size=self.text('尺寸：','Size: ')+f'{fmt(b-a)} × {fmt(d-c)} {unit}'
            text='\n'.join((heading,coordinates,size+'  |  '+composition))
        self.selection_info.setText(text);self.selection_info.setToolTip(text)
