"""Editable color stops; positions are fractions of the unchanged colorbar range."""
from copy import deepcopy
from PySide6.QtCore import Qt,Signal,QPointF
from PySide6.QtGui import QColor,QPainter,QPen,QLinearGradient,QPolygonF
from PySide6.QtWidgets import (QWidget,QDialog,QVBoxLayout,QHBoxLayout,QLabel,
    QPushButton,QDoubleSpinBox,QColorDialog,QDialogButtonBox)
from matplotlib.colors import LinearSegmentedColormap,to_hex


def gradient_colormap(stops):
    points=[(float(position),color) for position,color in stops]
    if points[0][0]>0:points.insert(0,(0.,points[0][1]))
    if points[-1][0]<1:points.append((1.,points[-1][1]))
    return LinearSegmentedColormap.from_list('custom_result_gradient',points,N=4096)


class GradientStrip(QWidget):
    selected=Signal()
    changed=Signal()
    edit_color=Signal()

    def __init__(self,stops,parent=None):
        super().__init__(parent);self.stops=deepcopy(stops);self.index=0;self.dragging=False
        self.setMinimumSize(360,100);self.setMouseTracking(True)
        self.setAccessibleName('Gradient color stops')

    def x_for(self,position):return 20+position*(self.width()-40)

    def hit(self,point):
        if not 40<=point.y()<=90:return None
        nearest=min(range(len(self.stops)),key=lambda i:abs(point.x()-self.x_for(self.stops[i][0])))
        return nearest if abs(point.x()-self.x_for(self.stops[nearest][0]))<=12 else None

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient=QLinearGradient(20,0,self.width()-20,0)
        for position,color in self.stops:gradient.setColorAt(position,QColor(color))
        painter.setBrush(gradient);painter.setPen(QPen(QColor('#8b9cad'),1))
        painter.drawRect(20,16,self.width()-40,30)
        for i,(position,color) in enumerate(self.stops):
            x=self.x_for(position);painter.setBrush(QColor(color))
            painter.setPen(QPen(QColor('#087d9f') if i==self.index else QColor('#475569'),3 if i==self.index else 1))
            painter.drawPolygon(QPolygonF([QPointF(x,48),QPointF(x-7,57),QPointF(x-7,70),QPointF(x+7,70),QPointF(x+7,57)]))
        painter.setPen(QColor('#61758b'));painter.drawText(16,95,'0%')
        painter.drawText(self.width()-48,95,'100%')

    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:return
        index=self.hit(event.position())
        if index is not None:
            self.index=index;self.dragging=True;self.selected.emit();self.update()

    def mouseMoveEvent(self,event):
        if self.dragging:
            self.set_position((event.position().x()-20)/(self.width()-40))
        else:self.setCursor(Qt.CursorShape.SizeHorCursor if self.hit(event.position()) is not None else Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self,event):self.dragging=False

    def mouseDoubleClickEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:return
        index=self.hit(event.position())
        if index is not None:
            self.index=index;self.dragging=False;self.selected.emit();self.edit_color.emit()

    def set_position(self,position):
        i=self.index
        low=self.stops[i-1][0]+.001 if i else 0.
        high=self.stops[i+1][0]-.001 if i+1<len(self.stops) else 1.
        self.stops[i][0]=round(max(low,min(high,position)),4)
        self.update();self.changed.emit()


class GradientDialog(QDialog):
    def __init__(self,view,mappable,key):
        super().__init__(view);self.view=view;self.key=key;self.mappable=mappable
        self.original_cmap=mappable.get_cmap();self.original=deepcopy(view.gradient_stops.get(key))
        self.setWindowTitle(view.tr('颜色渐变','Color gradient'));self.resize(570,240)
        layout=QVBoxLayout(self)
        hint=QLabel(view.tr('拖动下方色标调整渐变位置；双击色标或点击颜色按钮修改颜色。',
            'Drag a stop to adjust its position. Double-click a stop or click Color to change its color.'))
        hint.setWordWrap(True);layout.addWidget(hint)
        stops=self.original or [[p,to_hex(self.original_cmap(p))] for p in (0.,.33,.67,1.)]
        self.strip=GradientStrip(stops);layout.addWidget(self.strip)
        row=QHBoxLayout();layout.addLayout(row)
        self.color=QPushButton(view.tr('色标颜色…','Stop color…'));row.addWidget(self.color)
        row.addWidget(QLabel(view.tr('位置','Position')))
        self.position=QDoubleSpinBox();self.position.setRange(0,100);self.position.setDecimals(1)
        self.position.setSuffix(' %');self.position.setKeyboardTracking(False);row.addWidget(self.position)
        row.addStretch()
        self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(view.tr('确定','OK'))
        self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(view.tr('取消','Cancel'))
        layout.addWidget(self.buttons)
        self.strip.selected.connect(self.sync_controls);self.strip.changed.connect(self.preview)
        self.strip.edit_color.connect(self.choose_color);self.color.clicked.connect(self.choose_color)
        self.position.valueChanged.connect(lambda value:self.strip.set_position(value/100))
        self.buttons.accepted.connect(self.accept);self.buttons.rejected.connect(self.reject)
        self.sync_controls()

    def sync_controls(self):
        position,color=self.strip.stops[self.strip.index]
        self.position.blockSignals(True);self.position.setValue(position*100);self.position.blockSignals(False)
        self.color.setStyleSheet('QPushButton {border:3px solid '+color+';}')

    def choose_color(self):
        color=QColorDialog.getColor(QColor(self.strip.stops[self.strip.index][1]),self,
            self.view.tr('选择色标颜色','Choose stop color'))
        if color.isValid():
            self.strip.stops[self.strip.index][1]=color.name();self.strip.update();self.preview()

    def preview(self):
        self.sync_controls()
        self.view.gradient_stops[self.key]=deepcopy(self.strip.stops)
        self.mappable.set_cmap(gradient_colormap(self.strip.stops))
        self.view.canvas.draw_idle()

    def reject(self):
        if self.original is None:self.view.gradient_stops.pop(self.key,None)
        else:self.view.gradient_stops[self.key]=self.original
        self.mappable.set_cmap(self.original_cmap);self.view.canvas.draw_idle()
        super().reject()

    def accept(self):
        self.preview();super().accept()


class InitialGradientController(QWidget):
    """One display palette per element, shared by the two initial-target views."""
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.gradient_stops={};self.canvas=owner.canvas

    def tr(self,zh,en):return en if getattr(self.owner,'ui_language','zh')=='en' else zh

    def colormap(self,symbol):
        from element_colors import element_colormap
        stops=self.gradient_stops.get(('initial',symbol))
        return gradient_colormap(stops) if stops else element_colormap(symbol)

    def apply_colormap(self,cmap):
        from element_colors import contrast_text
        for canvas in (self.owner.canvas,self.owner.target_editor.canvas):
            for ax in canvas.figure.axes:
                if hasattr(ax,'_colorbar'):
                    ax._colorbar.mappable.set_cmap(cmap);continue
                for patch in ax.patches:
                    if hasattr(patch,'_target_fraction'):patch.set_facecolor(cmap(patch._target_fraction))
                for collection in ax.collections:
                    if collection.get_array() is not None:collection.set_cmap(cmap)
                for image in ax.images:
                    if getattr(image,'_target_composition',False):image.set_cmap(cmap)
                for text in ax.texts:
                    if text.get_text() in ('基底','基体','Substrate','Matrix'):
                        idx=self.owner.color_species.currentIndex()
                        text.set_color(contrast_text(cmap(self.owner.collect()[0]['qu_tar'][idx])))
            canvas.draw_idle()
        self.owner.target_editor.fraction_scale.update()

    def edit(self,canvas):
        from matplotlib.cm import ScalarMappable
        from matplotlib.colors import Normalize
        symbol=self.owner.color_species.currentText()
        if not symbol:return
        self.canvas=canvas
        mappable=ScalarMappable(norm=Normalize(0,1),cmap=self.colormap(symbol))
        mappable.callbacks.connect('changed',lambda changed:self.apply_colormap(changed.get_cmap()))
        GradientDialog(self,mappable,('initial',symbol)).exec()
