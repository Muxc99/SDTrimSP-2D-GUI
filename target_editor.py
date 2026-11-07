"""靶绘制初版：左侧画布、右侧原输入控件；表格仍是保存的唯一几何数据。"""
import math
import numpy as np
from PySide6.QtCore import Qt,QSize,QEvent,QTimer
from types import SimpleNamespace
from PySide6.QtGui import QIcon,QPixmap,QPainter,QPen,QColor,QPolygonF
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QSplitter,QScrollArea,
    QToolButton,QButtonGroup,QCheckBox,QLabel,QGroupBox,QTableWidget,QTableWidgetItem,
    QHeaderView,QPushButton,QAbstractItemView)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.collections import LineCollection,PolyCollection
from matplotlib.patches import Rectangle
from case_model import number,fmt,validate
from element_picker import NoWheelComboBox
from layout_defaults import DefaultSplitter
from drawing_model import cell_at,grid_key,split_rectangle,merge_rows,move_rows,MAX_DRAW_CELLS
from target_render import selection_rectangles

def tool_icon(name):
    pixmap=QPixmap(26,26);pixmap.fill(Qt.GlobalColor.transparent)
    p=QPainter(pixmap);p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor('#28465d'),1.8));p.setBrush(Qt.BrushStyle.NoBrush)
    if name=='select':
        from PySide6.QtCore import QPointF
        p.setBrush(QColor('#d5e7f0'));p.drawPolygon(QPolygonF([QPointF(5,3),QPointF(20,14),QPointF(13,15),QPointF(10,22)]))
    elif name=='brush':
        p.drawLine(8,18,21,4);p.drawLine(5,16,11,22);p.setBrush(QColor('#d5e7f0'));p.drawEllipse(3,17,7,6)
    elif name=='erase':
        p.drawLine(4,17,13,5);p.drawLine(13,5,22,12);p.drawLine(22,12,13,23);p.drawLine(13,23,4,17);p.drawLine(8,12,17,19)
    elif name=='rectangle':p.drawRect(4,6,18,14)
    elif name=='pan':
        for a,b,c,d in [(13,3,13,23),(3,13,23,13),(13,3,9,7),(13,3,17,7),(23,13,19,9),(23,13,19,17),(3,13,7,9),(3,13,7,17),(13,23,9,19),(13,23,17,19)]:p.drawLine(a,b,c,d)
    elif name in ('plus','minus'):
        p.drawEllipse(4,4,18,18);p.drawLine(8,13,18,13)
        if name=='plus':p.drawLine(13,8,13,18)
    elif name=='fit':
        for a,b,c,d in [(4,10,4,4),(4,4,10,4),(16,4,22,4),(22,4,22,10),(22,16,22,22),(22,22,16,22),(10,22,4,22),(4,22,4,16)]:p.drawLine(a,b,c,d)
    elif name in ('undo','redo'):
        # Draw one canonical curved arrow; undo is mirrored after rasterizing
        # so antialiasing remains exactly symmetric at the pixel level.
        p.drawArc(5,7,16,15,20*16,260*16)
        p.drawLine(21,11,21,4);p.drawLine(21,11,14,10)
    elif name=='delete':
        p.drawRect(7,8,12,14);p.drawLine(4,6,22,6);p.drawLine(10,3,16,3);p.drawLine(11,11,11,19);p.drawLine(15,11,15,19)
    p.end()
    if name=='undo':
        pixmap=QPixmap.fromImage(pixmap.toImage().mirrored(True,False))
    return QIcon(pixmap)

from target_selection import SelectionActions
from selection_inspector import SelectionInspector
from element_colors import tint_species_item
from substrate_profile import SubstrateProfileEditor
from substrate_rectangle import SubstrateRectangleEditor

class TargetEditor(SelectionInspector,SelectionActions,QWidget):
    def __init__(self,owner,settings):
        super().__init__(owner)
        self.owner=owner;self.ax=None;self.data=None;self.fig=None;self.stats=None
        self.signature=None;self.expected=None;self.undo_stack=[];self.redo_stack=[]
        self.tool='select';self.gesture=None;self.preview=None;self.grid_artist=None;self.selection_artists=[]
        self.substrate_selected=False
        self.syncing=False
        self._rows_cache=None;self._occupancy_cache=None;self._hit_cache=None
        self._overlay_background=None;self._overlay_background_key=None
        model=owner.blocks.model()
        for signal in (model.dataChanged,model.rowsInserted,model.rowsRemoved,model.columnsInserted,model.columnsRemoved,model.modelReset,model.layoutChanged):
            signal.connect(self.invalidate_rows)
        self.init_selection()
        self.last_message=None;self.last_language=None;self.drawing_height_error=None
        layout=QHBoxLayout(self);layout.setContentsMargins(3,4,3,3)
        split=DefaultSplitter(Qt.Orientation.Horizontal,'drawing');layout.addWidget(split)
        drawing=QWidget();dl=QVBoxLayout(drawing);dl.setContentsMargins(0,0,5,0)
        self.options=options=QHBoxLayout();dl.addLayout(options)
        self.show_grid=QCheckBox('显示网格');self.show_grid.setChecked(True);options.addWidget(self.show_grid)
        options.addWidget(owner.mirror);options.addWidget(owner.with_qu)
        options.addStretch();options.addWidget(QLabel('着色元素'))
        self.color=NoWheelComboBox();options.addWidget(self.color)
        center=QHBoxLayout();dl.addLayout(center,1)
        tools=QVBoxLayout();tools.setSpacing(5);center.addLayout(tools)
        self.tool_buttons={};self.tool_group=QButtonGroup(self);self.tool_group.setExclusive(True)
        labels=[('select','选择 / 框选（右键编辑，Alt+拖动移动）'),('brush','画笔：按网格涂绘'),
                ('erase','橡皮擦：删除整个凸起块，不擦除基底'),('rectangle','矩形：自动按网格切分'),
                ('pan','平移画面')]
        for key,label in labels:
            button=self.make_button(key,label);button.setCheckable(True);button.setChecked(key=='select')
            self.tool_group.addButton(button);button.clicked.connect(lambda checked=False,key=key:self.set_tool(key))
            self.tool_buttons[key]=button;tools.addWidget(button)
        tools.addSpacing(12)
        for key,label,slot in [('plus','放大',lambda:self.zoom(.8)),('minus','缩小',lambda:self.zoom(1.25)),('fit','适应全部靶区',self.fit_view),
                              ('undo','撤销绘图操作（Ctrl+Z）',self.undo),('redo','重做绘图操作（Ctrl+Y）',self.redo),('delete','删除选中的凸起块',self.delete_selected)]:
            button=self.make_button(key,label);button.clicked.connect(slot);self.tool_buttons[key]=button;tools.addWidget(button)
        tools.addStretch()
        self.figure=Figure(figsize=(8,7));self.canvas=FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumSize(340,320);self.canvas.setFocusPolicy(Qt.FocusPolicy.StrongFocus);self.canvas.installEventFilter(self);center.addWidget(self.canvas,1)
        self.init_inspector();center.addWidget(self.fraction_scale)
        bottom=QHBoxLayout();dl.addLayout(bottom);status=QVBoxLayout();bottom.addLayout(status,1);bottom.addWidget(self.selection_info)
        self.coordinate=QLabel('x / z');status.addWidget(self.coordinate)
        self.message_label=QLabel('选择：单击选块、拖框多选；右键编辑，Ctrl+C/X/V 复制剪切粘贴；方向键换选，Alt+拖动移动。')
        self.message_label.setWordWrap(True);status.addWidget(self.message_label)
        self.drawing_error_label=QLabel(self.canvas);self.drawing_error_label.setWordWrap(True)
        self.drawing_error_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.drawing_error_label.setTextFormat(Qt.TextFormat.PlainText)
        self.drawing_error_label.setStyleSheet('color:#b42318;background:#fff0ee;border:1px solid #f2b5ae;border-radius:4px;padding:6px;font-weight:bold;')
        self.drawing_error_label.hide()
        self.error_timer=QTimer(self);self.error_timer.setSingleShot(True);self.error_timer.setInterval(5000)
        self.error_timer.timeout.connect(self.clear_drawing_height_error)
        self.error_message=None
        self.last_validation_errors=()
        self.validation_label=QLabel();self.validation_label.setWordWrap(True);self.validation_label.setFixedHeight(38)
        self.validation_label.setStyleSheet('color:#8b5c2c;font-size:9pt;');status.addWidget(self.validation_label)
        split.addWidget(drawing)
        side=DefaultSplitter(Qt.Orientation.Vertical,'materials')
        top=QWidget();tl=QVBoxLayout(top);tl.setContentsMargins(0,0,0,0)
        scroller=QScrollArea();scroller.setWidgetResizable(True);scroller.setFrameShape(QScrollArea.Shape.NoFrame)
        settings.setTitle('网格/基底/束流');scroller.setWidget(settings);tl.addWidget(scroller,1)
        base=QGroupBox('基底成分（原子分数）');bl=QVBoxLayout(base)
        self.base_composition=QTableWidget(1,0);self.base_composition.setFixedHeight(72)
        self.base_composition.verticalHeader().hide();self.base_composition.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        bl.addWidget(self.base_composition);tl.addWidget(base);side.addWidget(top)
        lower=QGroupBox('凸起成分（原子分数）');self.block_settings=lower;ll=QVBoxLayout(lower);ll.setContentsMargins(7,12,7,6)
        self.brush_composition=QTableWidget(1,0);self.brush_composition.setFixedHeight(72)
        self.brush_composition.verticalHeader().hide();self.brush_composition.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        ll.addWidget(self.brush_composition)
        row=QHBoxLayout();ll.addLayout(row)
        for label,slot in [('采用基底成分',self.use_base),('采用选中块成分',self.use_selected)]:
            button=QPushButton(label);button.clicked.connect(slot);row.addWidget(button)
        # 几何开关集中在画布上方；右侧只保留成分，明细表仍在独立页。
        ll.addStretch(1)
        side.addWidget(lower);side.setSizes([550,250]);split.addWidget(side);split.setSizes([960,430])
        self.splitter=split;self.sidebar=side
        self.profile_editor=SubstrateProfileEditor(self)
        self.rectangle_editor=SubstrateRectangleEditor(self)
        self.show_grid.toggled.connect(self.update_grid)
        self.color.currentTextChanged.connect(self.change_color)
        self.base_composition.itemChanged.connect(self.update_base)
        owner.blocks.itemSelectionChanged.connect(self.table_selection_changed)
        for event,handler in [('button_press_event',self.on_press),('motion_notify_event',self.on_motion),
                              ('button_release_event',self.on_release),('scroll_event',self.on_scroll),('key_press_event',self.on_key),('resize_event',self.on_resize),('figure_leave_event',self.on_canvas_leave),('draw_event',self.on_canvas_draw)]:
            self.canvas.mpl_connect(event,handler)

    def overlay_key(self):
        return (id(self.ax),tuple(self.ax.bbox.extents),self.ax.get_xlim(),self.ax.get_ylim())

    def overlay_artists(self):
        return self.selection_artists+([self.preview] if self.preview is not None else [])

    def on_canvas_draw(self,event):
        if self.ax is None or self.canvas.is_saving():return
        self._overlay_background=self.canvas.copy_from_bbox(self.figure.bbox)
        self._overlay_background_key=self.overlay_key() if not self.substrate_selected else None
        self.paint_overlays(blit=False)

    def paint_overlays(self,blit=True):
        for artist in sorted(self.overlay_artists(),key=lambda a:a.get_zorder()):
            if artist.get_animated() and artist.axes is self.ax:self.ax.draw_artist(artist)
        if blit:self.canvas.blit(self.figure.bbox)

    def redraw_overlays(self):
        if self.ax is None:return
        fast=self.canvas.supports_blit and self.owner.geometry.currentData()==26 and not self.substrate_selected
        for artist in self.overlay_artists():artist.set_animated(fast)
        if fast and self._overlay_background is not None and self._overlay_background_key==self.overlay_key():
            self.canvas.restore_region(self._overlay_background);self.paint_overlays()
        else:self.canvas.draw_idle()

    def make_button(self,key,label):
        button=QToolButton();button.setIcon(tool_icon(key));button.setIconSize(QSize(23,23));button.setFixedSize(34,34)
        button.setToolTip(label);button.setAccessibleName(label);button.setCheckable(False)
        return button

    def text(self,zh,en):return en if getattr(self.owner,'ui_language','zh')=='en' else zh

    def message(self,zh,en=None):
        if '\n' in zh:
            self.show_error(zh,en);return
        self.last_message=(zh,en)
        text=self.text(zh,en or zh);self.message_label.setText(text);self.owner.statusBar().showMessage(text,7000)

    def show_error(self,zh,en=None):
        # Independent Qt overlay: never add error text to the canvas layout or plot artists.
        self.error_message=(zh,en or zh)
        self.render_error()
        self.drawing_error_label.show();self.drawing_error_label.raise_()
        self.error_timer.start()

    def report_validation_errors(self,errors):
        current=tuple(errors)
        if current and current!=self.last_validation_errors:
            from i18n import translated
            detail='\n'.join(errors)
            self.show_error('输入错误：\n'+detail,
                            'Input error:\n'+translated(detail,'en'))
        self.last_validation_errors=current

    def render_error(self):
        if not self.error_message:return
        lines=[line.strip() for line in self.text(*self.error_message).splitlines() if line.strip()]
        summary='\n'.join(line[:160] for line in lines[:2])
        if len(lines)>2:
            summary+=self.text(f'\n另有 {len(lines)-2} 项错误，请检查基底尺寸及参数。',f'\n{len(lines)-2} more errors. Check substrate dimensions and parameters.')
        self.drawing_error_label.setText(summary[:420])
        self.position_error()

    def position_error(self):
        if not hasattr(self,'drawing_error_label'):return
        width=max(100,min(720,self.canvas.width()-32))
        self.drawing_error_label.setFixedWidth(width);self.drawing_error_label.adjustSize()
        self.drawing_error_label.setFixedHeight(min(150,self.drawing_error_label.heightForWidth(width)+14))
        self.drawing_error_label.move(max(0,(self.canvas.width()-width)//2),16)

    def height_error_context(self,data):
        return (str(self.owner.source),data['case_geo'],data['case_start'],data['z_start'])

    def update_drawing_height_error(self,data,top=None):
        new_error=top is not None
        if top is not None:
            self.drawing_height_error=(self.height_error_context(data),top)
        if self.drawing_height_error is None:return
        context,top=self.drawing_height_error
        if context!=self.height_error_context(data):
            self.clear_drawing_height_error();return
        f=self.owner.factor;unit=self.owner.unit.currentText()
        height=fmt(top/f);start=fmt(data['z_start']/f)
        pair=(
            f'绘制失败：色块顶部 {height} {unit} 达到或超过入射起始高度 {start} {unit}，本次操作未保存。请在“束流设置”中将入射起始高度调高至色块顶部以上，再重新绘制。',
            f'Drawing failed: block top {height} {unit} reaches or exceeds the beam starting height {start} {unit}. This edit was not saved. Increase Starting height in Beam settings above the block top, then draw again.')
        if new_error:self.show_error(*pair)
        else:self.error_message=pair;self.render_error()

    def clear_drawing_height_error(self):
        self.drawing_height_error=None;self.error_message=None
        self.error_timer.stop();self.drawing_error_label.clear();self.drawing_error_label.hide()

    def set_tool(self,key):
        self.cancel_gesture();self.tool=key
        if self.owner.geometry.currentData()==26 and key!='select':
            self.substrate_selected=False;self.rectangle_editor.draw_overlay()
        if key in self.tool_buttons and self.tool_buttons[key].isCheckable():self.tool_buttons[key].setChecked(True)
        if self.profile_editor.active:
            self.profile_editor.tool_changed(key)
            self.canvas.setCursor(Qt.CursorShape.OpenHandCursor if key=='pan' else Qt.CursorShape.CrossCursor if key!='select' else Qt.CursorShape.ArrowCursor)
            return
        if self.rectangle_editor.active and self.owner.geometry.currentData()!=26 and key=='select':
            self.message('拖动矩形角点或侧边/底边手柄调整尺寸；上边固定 z=0，不能增加节点。','Drag rectangle corners or side/bottom handles to resize. The reference top stays at z=0; nodes cannot be added.')
            self.canvas.setCursor(Qt.CursorShape.ArrowCursor);return
        descriptions={'select':('单击选块，拖框多选；右键编辑，Ctrl+C/X/V 复制剪切粘贴；方向键换选，Alt+拖动移动。','Click a block or drag a selection. Right-click to edit; Ctrl+C/X/V for copy/cut/paste, arrows to navigate, Alt+drag to move.'),
          'brush':('按住左键涂绘整格；成分取右侧“凸起成分（原子分数）”。','Hold the left button to paint grid cells using Protrusion composition (atomic fractions) on the right.'),
          'erase':('拖动删除经过的整个凸起块；基底保持不变。','Drag to remove whole protrusion blocks; the substrate is preserved.'),
          'rectangle':('拖出矩形；自动切分到背景网格，边缘可保留不满格。','Drag a rectangle; grid splitting preserves partial edge cells.'),
          'pan':('拖动画面；滚轮缩放，四角图标恢复全部靶区。','Drag to pan; wheel to zoom. Fit restores the full target view.')}
        self.message(*descriptions[key])
        self.canvas.setCursor(Qt.CursorShape.OpenHandCursor if key=='pan' else Qt.CursorShape.CrossCursor if key not in ('select',) else Qt.CursorShape.ArrowCursor)

    def invalidate_rows(self,*args):
        self._rows_cache=None;self._occupancy_cache=None;self._hit_cache=None

    def cached_rows(self):
        key=(self.owner.factor,self.owner.blocks.rowCount(),self.owner.blocks.columnCount())
        if self._rows_cache is None or self._rows_cache[0]!=key:
            rows=[[number(fmt(number(self.owner.cell(self.owner.blocks,r,c))*(self.owner.factor if c<4 else 1.)))
                   for c in range(key[2])] for r in range(key[1])]
            self._rows_cache=(key,rows);self._occupancy_cache=None;self._hit_cache=None
        return self._rows_cache[1]

    def rows(self):
        # Callers may edit their snapshot; cached geometry is never handed out for mutation.
        return [r[:] for r in self.cached_rows()]

    def sync(self,data,fig,stats,force_fit=False):
        if self.syncing:return
        self.syncing=True
        try:
            previous_mode=self.data.get('case_geo') if self.data is not None else None
            if previous_mode!=data['case_geo']:self.substrate_selected=False
            self.data=data;self.fig=fig;self.stats=stats
            signature=(str(self.owner.source),self.owner.factor,data['geo_x'],data['geo_z'],data['geo_dx'],data['geo_dz'],data['case_geo'])
            if self.gesture is not None and signature!=self.signature:self.cancel_gesture()
            view=(self.ax.get_xlim(),self.ax.get_ylim()) if not force_fit and self.ax is not None and signature==self.signature else None
            current=self.rows() if fig is not None else []
            # 手工改表、切换案例、改变网格后，旧绘图撤销记录不能覆盖新输入。
            expected=(signature,current,bool(self.owner.mirror.isChecked()),bool(self.owner.with_qu.isChecked()))
            if self.expected is not None and expected!=self.expected:
                self.undo_stack.clear();self.redo_stack.clear()
            self.expected=expected;self.signature=signature
            self.profile_editor.sync(data)
            self.sync_selection()
            symbols=data['symbol']
            if [self.color.itemText(i) for i in range(self.color.count())]!=symbols:
                self.color.blockSignals(True);self.color.clear();self.color.addItems(symbols);self.color.blockSignals(False)
            self.color.blockSignals(True);self.color.setCurrentText(self.owner.color_species.currentText());self.color.blockSignals(False)
            old_symbols=[self.brush_composition.horizontalHeaderItem(i).text() for i in range(self.brush_composition.columnCount())]
            for table in (self.base_composition,self.brush_composition):
                table.blockSignals(True);table.setColumnCount(len(symbols));table.setHorizontalHeaderLabels(symbols)
            for i,q in enumerate(data['qu_tar']):
                self.base_composition.setItem(0,i,QTableWidgetItem(fmt(q)))
                if old_symbols!=symbols or self.brush_composition.item(0,i) is None:
                    self.brush_composition.setItem(0,i,QTableWidgetItem(fmt(q)))
            for table in (self.base_composition,self.brush_composition):
                for i,symbol in enumerate(symbols):tint_species_item(table.item(0,i),symbol)
                table.blockSignals(False)
            enabled=data['case_geo']==26
            profile=self.profile_editor.active
            for key in ('brush','erase','rectangle','delete'):self.tool_buttons[key].setEnabled(enabled or (profile and key!='rectangle'))
            labels={
                'select':('选择 / 拖动轮廓节点','Select / drag outline nodes') if profile else ('选择 / 框选（右键编辑，Alt+拖动移动）','Select / marquee (right-click edits; Alt+drag moves)'),
                'brush':('增加边上节点','Add node on edge') if profile else ('画笔：按网格涂绘','Brush: paint grid cells'),
                'erase':('删除上边界内部节点','Delete interior upper nodes') if profile else ('橡皮擦：删除整个凸起块，不擦除基底','Eraser: remove whole protrusion blocks; preserve substrate'),
                'delete':('删除选中节点','Delete selected node') if profile else ('删除选中的凸起块','Delete selected protrusion blocks')}
            for key,pair in labels.items():
                label=self.text(*pair);self.tool_buttons[key].setToolTip(label);self.tool_buttons[key].setAccessibleName(label)
            if self.tool in self.tool_buttons and not self.tool_buttons[self.tool].isEnabled():self.set_tool('select')
            self.brush_composition.setEnabled(enabled and self.owner.with_qu.isChecked())
            self.ax=self.owner.draw(data,fig,stats,plot=self.figure,canvas=self.canvas,editor=True)
            self.profile_editor.artists=[]
            self.rectangle_editor.artists=[]
            self.grid_artist=None;self.selection_artists=[]
            if self.ax is not None:
                if view:self.ax.set_xlim(*view[0]);self.ax.set_ylim(*view[1])
                self.layout_view(fit=view is None);self.update_grid();self.highlight_selection()
            language=getattr(self.owner,'ui_language','zh')
            if enabled and previous_mode!=26:self.set_tool('select')
            elif profile and (previous_mode!=data['case_geo'] or language!=self.last_language):
                self.profile_editor.tool_changed(self.tool)
            elif not enabled and (previous_mode!=data['case_geo'] or language!=self.last_language):
                if self.rectangle_editor.active:
                    self.message('选择工具可拖动矩形角点与边；上边固定 z=0，宽度关于中心对称，不能增加节点。','Use Select to drag rectangle corners or edges. The top stays at z=0, width changes symmetrically, and nodes cannot be added.')
                else:self.message('当前几何仅提供预览，请核对内核支持情况。','This geometry is previewed only; check engine support.')
            if language!=self.last_language and self.last_message:self.message(*self.last_message)
            self.last_language=language
            self.update_drawing_height_error(data)
            self.render_error()
            self.update_history_buttons()
        finally:self.syncing=False

    def layout_view(self,fit=False):
        """固定绘图区边框，只改变可见坐标范围，保持 x/z 等比例。"""
        if self.ax is None:return
        width,height=self.figure.get_size_inches()*self.figure.dpi
        # 像素边距预留四边刻度和轴标题；不参与自动布局或缩放。
        left=min(72.,width*.18);right=min(62.,width*.16)
        bottom=min(55.,height*.18);top=min(36.,height*.12)
        self.ax.set_position([left/width,bottom/height,(width-left-right)/width,(height-bottom-top)/height])
        self.ax.set_aspect('auto')
        a,b=self.ax.get_xlim();c,d=self.ax.get_ylim()
        ratio=self.ax.bbox.width/self.ax.bbox.height
        xspan=b-a;zspan=d-c
        if fit:zspan=max(zspan,xspan/ratio)
        xspan=zspan*ratio
        x=(a+b)/2;z=(c+d)/2
        self.ax.set_xlim(x-xspan/2,x+xspan/2);self.ax.set_ylim(z-zspan/2,z+zspan/2)

    def on_resize(self,event):
        self.position_error()
        if self.ax is not None:
            self.layout_view();self.update_grid()

    def change_color(self,symbol):
        if not self.syncing:self.owner.color_species.setCurrentText(symbol)

    def update_base(self,item):
        if not self.syncing:
            target=self.owner.species.item(item.column(),4)
            if target and target.text()!=item.text():target.setText(item.text())

    def use_base(self):
        for i in range(self.owner.species.rowCount()):self.brush_composition.setItem(0,i,QTableWidgetItem(self.owner.cell(self.owner.species,i,4)))

    def use_selected(self):
        rows=self.owner.selected_rows()
        if not rows:return
        for i in range(self.owner.species.rowCount()):self.brush_composition.setItem(0,i,QTableWidgetItem(self.owner.cell(self.owner.blocks,rows[0],4+i)))

    def fractions(self):
        if not self.owner.with_qu.isChecked():return list(self.data['qu_tar'])
        result=[number(self.brush_composition.item(0,i).text()) for i in range(self.brush_composition.columnCount())]
        if any(q<0 or q>1 for q in result) or not math.isclose(sum(result),1.,abs_tol=1e-6):
            raise ValueError(self.text('新绘制块的成分必须在 0～1 之间，合计为 1。','New-block fractions must lie in [0,1] and sum to 1.'))
        return result

    def geometry(self):
        return (*[number(self.owner.edits[k].text())*self.owner.factor for k in ('geo_x','geo_dx','geo_dz')],self.owner.mirror.isChecked())

    def update_grid(self,*args):
        if self.ax is None or self.data is None:return
        if self.show_grid.isChecked():
            f=self.owner.factor;dx=self.data['geo_dx']/f;dz=self.data['geo_dz']/f;origin=-self.data['geo_x']/f
            if dx<=0 or dz<=0:return
            a,b=self.ax.get_xlim();c,d=self.ax.get_ylim();segments=[]
            for low,high,step,offset,vertical in ((a,b,dx,origin,True),(c,d,dz,0.,False)):
                first=math.ceil((low-offset)/step);last=math.floor((high-offset)/step)
                stride=max(1,math.ceil((last-first+1)/180))
                for i in range(first,last+1,stride):
                    value=offset+i*step
                    segments.append([(value,c),(value,d)] if vertical else [(a,value),(b,value)])
            if self.grid_artist is None:
                self.grid_artist=LineCollection(segments,colors='#91a2ae',linewidths=.45,alpha=.28,zorder=4)
                self.ax.add_collection(self.grid_artist,autolim=False)
            else:self.grid_artist.set_segments(segments)
            self.grid_artist.set_visible(True)
        elif self.grid_artist is not None:self.grid_artist.set_visible(False)
        self.canvas.draw_idle()

    def highlight_selection(self):
        if self.ax is None:return
        for artist in self.selection_artists:
            try:artist.remove()
            except (ValueError,NotImplementedError):pass
        self.selection_artists=[]
        if self.profile_editor.active:
            self.fraction_scale.sync(self.owner.color_species.currentText());self.profile_editor.draw_overlay();self.rectangle_editor.draw_overlay();return
        f=self.owner.factor
        bounds=[];rows=self.cached_rows()
        for i in self.owner.selected_rows():
            r=rows[i]
            for a,b in [(r[0],r[1])]+([(-r[1],-r[0])] if self.owner.mirror.isChecked() else []):
                bounds.append((a,b,r[2],r[3]))
        view=(self.ax.get_xlim(),self.ax.get_ylim())
        self.selection_artists.extend(selection_rectangles(self.ax,bounds,self.selection_grid()[:3],f,'none','#ed7a22',1.,2,7))
        self.selection_decorations()
        self.ax.set_xlim(*view[0]);self.ax.set_ylim(*view[1])
        self.update_inspector()
        self.rectangle_editor.draw_overlay()
        if not self.rectangle_editor.active:self.redraw_overlays()

    def hit(self,x,z):
        if not math.isfinite(x) or not math.isfinite(z):return None,False
        rows=self.cached_rows();occupied=self.cell_occupancy();gx,dx,dz,mirror=self.selection_grid()
        key=(id(rows),gx,dx,dz)
        if self._hit_cache is None or self._hit_cache[0]!=key:
            bounds=np.asarray([r[:4] for r in rows],dtype=float).reshape(-1,4)
            fallback=len(occupied)!=len(rows) or np.any((bounds[:,1]-bounds[:,0]>dx+1e-8)|(bounds[:,3]-bounds[:,2]>dz+1e-8))
            self._hit_cache=(key,bounds if fallback else None)
        bounds=self._hit_cache[1]
        if bounds is not None:
            direct=(bounds[:,0]<=x)&(x<=bounds[:,1])&(bounds[:,2]<=z)&(z<=bounds[:,3])
            reflected=mirror&(-bounds[:,1]<=x)&(x<=-bounds[:,0])&(bounds[:,2]<=z)&(z<=bounds[:,3])
            hits=np.flatnonzero(direct|reflected)
            if len(hits):
                i=int(hits[-1]);return i,not bool(direct[i])
            return None,False
        # Include adjacent cells to preserve inclusive rectangle-edge hit semantics.
        ix=math.floor((x+gx)/dx);iz=math.floor(z/dz);candidates=set()
        for cx in (ix-1,ix,ix+1):
            for cz in (iz-1,iz,iz+1):
                key=self.canonical_key((cx,cz));i=occupied.get(key)
                if i is not None:candidates.add(i)
        for i in sorted(candidates,reverse=True):
            r=rows[i]
            if r[0]<=x<=r[1] and r[2]<=z<=r[3]:return i,False
            if self.owner.mirror.isChecked() and -r[1]<=x<=-r[0] and r[2]<=z<=r[3]:return i,True
        return None,False

    def eventFilter(self,watched,event):
        if watched is self.canvas and event.type()==QEvent.Type.KeyPress:
            keys={Qt.Key.Key_Left:'left',Qt.Key.Key_Right:'right',Qt.Key.Key_Up:'up',Qt.Key.Key_Down:'down',
                  Qt.Key.Key_Delete:'delete',Qt.Key.Key_Backspace:'backspace',Qt.Key.Key_Escape:'escape',
                  Qt.Key.Key_Return:'enter',Qt.Key.Key_Enter:'enter',Qt.Key.Key_F2:'f2',
                  Qt.Key.Key_C:'c',Qt.Key.Key_X:'x',Qt.Key.Key_V:'v',Qt.Key.Key_A:'a',Qt.Key.Key_Z:'z',Qt.Key.Key_Y:'y'}
            key=keys.get(event.key())
            if key:
                modifiers=event.modifiers();prefix=''
                if modifiers & Qt.KeyboardModifier.ControlModifier:prefix+='ctrl+'
                if modifiers & Qt.KeyboardModifier.ShiftModifier:prefix+='shift+'
                if modifiers & Qt.KeyboardModifier.AltModifier:prefix+='alt+'
                if prefix or len(key)>1:
                    self.on_key(SimpleNamespace(key=prefix+key));event.accept();return True
        return super().eventFilter(watched,event)

    def on_press(self,event):
        if event.dblclick and event.button==1 and event.inaxes is self.ax:
            self.cancel_gesture();self.owner.initial_gradients.edit(self.canvas);return
        if event.inaxes is not self.ax or event.xdata is None or event.button not in (1,2,3):
            if event.button==1 and self.tool=='select':self.deselect_substrate()
            return
        self.canvas.setFocus();self.cancel_gesture()
        mode=self.owner.geometry.currentData()
        # 24/25 的轮廓优先；26 先保留凸起工具、材料格和空白格的完整操作。
        if mode!=26 and self.rectangle_editor.active and self.rectangle_editor.action(lambda:self.rectangle_editor.on_press(event)):return
        if self.profile_editor.active and event.button!=2 and self.tool!='pan':
            self.profile_editor.action(lambda:self.profile_editor.on_press(event));return
        point=(event.xdata*self.owner.factor,event.ydata*self.owner.factor)
        if mode==26:
            modifiers=set(getattr(event,'modifiers',()) or ())|set(str(getattr(event,'key','') or '').lower().split('+'))
            block_action=(event.button!=1 or self.tool!='select' or any(modifiers) or
                          self.cell_key(*point) is not None or self.hit(*point)[0] is not None or point[1]>=0)
            if block_action:self.deselect_substrate()
            elif self.rectangle_editor.action(lambda:self.rectangle_editor.on_press(event)):return
        if event.button==3:
            if self.tool!='select' or self.owner.geometry.currentData()!=26:return
            key=self.cell_key(*point)
            if key not in self.selected_cells:self.select_at(point)
            elif key is not None:self.active_cell=key
            self.highlight_selection();self.context_menu=self.build_context_menu(point)
            from PySide6.QtGui import QCursor
            self.context_menu.popup(QCursor.pos());return
        if event.button==2 or self.tool=='pan':
            self.gesture={'tool':'pan','pixel':(event.x,event.y),'view':(self.ax.get_xlim(),self.ax.get_ylim())};return
        if self.owner.geometry.currentData()!=26:return
        try:
            self.rows();self.geometry()
            self.gesture={'tool':self.tool,'start':point,'last':point,'pixel':(event.x,event.y),'new':{},'erased':set(),'before':self.rows()}
            if self.tool=='select':
                key=self.cell_key(*point)
                modifiers=set(getattr(event,'modifiers',()) or ())|set(str(getattr(event,'key','') or '').lower().split('+'))
                additive=bool({'shift','ctrl','control'} & modifiers);prior=set(self.selected_cells)
                side=bool(key is not None and self.owner.mirror.isChecked() and self.cell_bounds(key)[1]<=0)
                self.gesture.update(mirrored=side,add=[],add_cells=prior if additive else set(),drag=False)
                if 'alt' not in modifiers or key not in prior:self.select_at(point,modifiers)
                self.gesture['selected']=self.owner.selected_rows()
                self.gesture['move']='alt' in modifiers and key is not None
                if 'alt' in modifiers and key in prior:self.highlight_selection()
                return
            if self.tool in ('brush','rectangle') and (point[1]<0 or (self.owner.mirror.isChecked() and point[0]<0)):
                self.message('请在 z≥0 区域绘制；镜像开启时在右半区绘制。','Draw at z≥0. With mirroring enabled, draw on the right half.');self.cancel_gesture();return
            if self.tool in ('brush','rectangle'):self.gesture['fractions']=self.fractions()
            if self.tool in ('brush','erase'):self.stroke(point)
        except (ValueError,AttributeError) as error:self.show_error(str(error));self.cancel_gesture()

    def stroke(self,point):
        gesture=self.gesture;gx,dx,dz,mirror=self.geometry();start=gesture['last']
        count=max(1,math.ceil(max(abs(point[0]-start[0])/dx,abs(point[1]-start[1])/dz)*3))
        if count>MAX_DRAW_CELLS:raise ValueError('笔划过长，请分段绘制。')
        for k in range(count+1):
            x=start[0]+(point[0]-start[0])*k/count;z=start[1]+(point[1]-start[1])*k/count
            if gesture['tool']=='brush':
                cell=cell_at(x,z,gx,dx,dz,mirror)
                if cell:gesture['new'][grid_key(cell,gx,dx,dz)]=cell+gesture['fractions']
            else:
                row,_=self.hit(x,z)
                if row is not None:gesture['erased'].add(row)
        if len(gesture['new'])>MAX_DRAW_CELLS:raise ValueError('单次笔划超过 20000 格。')
        gesture['last']=point
        self.show_preview(list(gesture['new'].values()) if gesture['tool']=='brush' else [gesture['before'][i] for i in gesture['erased']],gesture['tool']=='erase')

    def show_preview(self,rows,erasing=False):
        if self.preview is not None and not isinstance(self.preview,PolyCollection):
            try:self.preview.remove()
            except ValueError:pass
            self.preview=None
        f=self.owner.factor
        polygons=[[(r[0]/f,r[2]/f),(r[1]/f,r[2]/f),(r[1]/f,r[3]/f),(r[0]/f,r[3]/f)] for r in rows]
        if self.preview is None:
            self.preview=PolyCollection(polygons,facecolors='#e76f51' if erasing else '#23a6aa',edgecolors='#147f90',alpha=.45,zorder=8)
            self.ax.add_collection(self.preview,autolim=False)
        else:self.preview.set_verts(polygons)
        self.redraw_overlays()

    def on_motion(self,event):
        self.update_substrate_cursor(event)
        if event.inaxes is self.ax and event.xdata is not None:
            self.coordinate.setText(f'x = {event.xdata:.5g}    z = {event.ydata:.5g}    {self.owner.unit.currentText()}')
        if self.profile_editor.active and self.profile_editor.drag is not None:
            self.profile_editor.action(lambda:self.profile_editor.on_motion(event));return
        if self.rectangle_editor.drag is not None:
            self.rectangle_editor.action(lambda:self.rectangle_editor.on_motion(event));return
        if not self.gesture:return
        gesture=self.gesture
        if gesture['tool']=='pan':
            bounds=self.ax.bbox;vx,vz=gesture['view']
            sx=(event.x-gesture['pixel'][0])*(vx[1]-vx[0])/bounds.width;sz=(event.y-gesture['pixel'][1])*(vz[1]-vz[0])/bounds.height
            self.ax.set_xlim(vx[0]-sx,vx[1]-sx);self.ax.set_ylim(vz[0]-sz,vz[1]-sz);self.update_grid();return
        if event.inaxes is not self.ax or event.xdata is None:return
        point=(event.xdata*self.owner.factor,event.ydata*self.owner.factor)
        try:
            if gesture['tool'] in ('brush','erase'):self.stroke(point)
            elif gesture['tool']=='select':
                if math.hypot(event.x-gesture['pixel'][0],event.y-gesture['pixel'][1])<4:return
                gesture['drag']=True;x,z=gesture['start'];a,b=point;f=self.owner.factor
                if gesture['move']:
                    gx,dx,dz,mirror=self.geometry();sx=round((a-x)/dx)*dx;sz=round((b-z)/dz)*dz
                    if gesture['mirrored']:sx=-sx
                    self.show_preview([[r[0]+sx,r[1]+sx,r[2]+sz,r[3]+sz,*r[4:]] for i,r in enumerate(gesture['before']) if i in gesture['selected']])
                else:
                    # 选择只显示整格高亮，不绘制独立的自由矩形预览。
                    self.select_grid_span(gesture['start'],point,gesture['add_cells'])
            elif gesture['tool']=='rectangle':
                x,z=gesture['start'];a,b=point;f=self.owner.factor
                bounds=(min(x,a)/f,min(z,b)/f,abs(a-x)/f,abs(b-z)/f)
                if not isinstance(self.preview,Rectangle):
                    if self.preview is not None:self.preview.remove()
                    self.preview=Rectangle(bounds[:2],bounds[2],bounds[3],fill=False,edgecolor='#168fa5',lw=1.5,zorder=8)
                    self.ax.add_patch(self.preview)
                else:self.preview.set_bounds(*bounds)
                self.redraw_overlays()
        except (ValueError,AttributeError) as error:self.show_error(str(error));self.cancel_gesture()

    def deselect_substrate(self):
        if not self.substrate_selected:return
        self.substrate_selected=False;self.profile_editor.selected=None
        self.profile_editor.draw_overlay();self.rectangle_editor.draw_overlay()
        if self.profile_editor.active:self.profile_editor.retranslate()
        else:self.update_inspector()
        self.canvas.draw_idle()

    def on_canvas_leave(self,event):
        if self.gesture is None and self.rectangle_editor.drag is None and self.profile_editor.drag is None:
            self.canvas.unsetCursor()

    def update_substrate_cursor(self,event):
        cursor=Qt.CursorShape.OpenHandCursor if self.tool=='pan' else Qt.CursorShape.CrossCursor if self.tool!='select' else Qt.CursorShape.ArrowCursor
        cursors={'left':Qt.CursorShape.SizeHorCursor,'right':Qt.CursorShape.SizeHorCursor,
                 'bottom':Qt.CursorShape.SizeVerCursor,'top':Qt.CursorShape.ForbiddenCursor,
                 'tl':Qt.CursorShape.SizeFDiagCursor,'br':Qt.CursorShape.SizeFDiagCursor,
                 'tr':Qt.CursorShape.SizeBDiagCursor,'bl':Qt.CursorShape.SizeBDiagCursor}
        if self.rectangle_editor.drag is not None:
            self.canvas.setCursor(cursors[self.rectangle_editor.drag['handle']]);return
        if self.profile_editor.drag is not None:
            self.canvas.setCursor(Qt.CursorShape.SizeAllCursor);return
        if self.substrate_selected and self.tool=='select' and event.inaxes is self.ax and event.xdata is not None:
            point=(event.xdata*self.owner.factor,event.ydata*self.owner.factor)
            block_area=self.owner.geometry.currentData()==26 and (point[1]>=0 or self.cell_key(*point) is not None or self.hit(*point)[0] is not None)
            if not block_area:
                kind=self.rectangle_editor.hit(event) if self.rectangle_editor.active else None
                cursor=cursors.get(kind,cursor)
                if kind is None and self.profile_editor.active and self.profile_editor.nearest(event) is not None:
                    cursor=Qt.CursorShape.SizeAllCursor
        self.canvas.setCursor(cursor)

    def on_release(self,event):
        if self.rectangle_editor.drag is not None:
            self.rectangle_editor.action(lambda:self.rectangle_editor.on_release(event));return
        if self.profile_editor.active and self.profile_editor.drag is not None:
            self.profile_editor.action(lambda:self.profile_editor.on_release(event));return
        if not self.gesture:return
        gesture=self.gesture
        try:
            if gesture['tool']=='pan':return
            before=gesture['before'];gx,dx,dz,mirror=self.geometry();kind=gesture['tool']
            if kind in ('rectangle','select') and (event.inaxes is not self.ax or event.xdata is None):return
            if kind=='rectangle':
                x,z=gesture['start'];a=event.xdata*self.owner.factor;b=event.ydata*self.owner.factor
                new=split_rectangle(x,a,z,b,gx,dx,dz,mirror,gesture['fractions'])
                after,skipped=merge_rows(before,new,gx,dx,dz,True)
            elif kind=='brush':after,skipped=merge_rows(before,list(gesture['new'].values()),gx,dx,dz,True)
            elif kind=='erase':after=[r for i,r in enumerate(before) if i not in gesture['erased']];skipped=0
            elif kind=='select':
                if not gesture.get('drag'):return
                if not gesture.get('move'):
                    self.select_grid_span(gesture['start'],(event.xdata*self.owner.factor,event.ydata*self.owner.factor),gesture['add_cells'])
                    count=len(self.selected_cells);filled=len(self.owner.selected_rows());self.message(f'已选中 {count} 格（含 {filled} 个材料块）；右键填充或编辑，Ctrl+C/X 复制剪切。',f'{count} cells selected ({filled} material blocks). Right-click to fill or edit; Ctrl+C/X to copy or cut.');return
                sx=event.xdata*self.owner.factor-gesture['start'][0];sz=event.ydata*self.owner.factor-gesture['start'][1]
                if gesture.get('mirrored'):sx=-sx
                sx=round(sx/dx)*dx;sz=round(sz/dz)*dz
                if self.selected_cells and (sx or sz):self.move_selection(sx,sz,gesture['selected'])
                return
            else:return
            self.commit(before,after)
            self.message(f'现有 {len(after)} 个矩形块；跳过 {skipped} 个已占用格。',f'{len(after)} rectangle blocks; skipped {skipped} occupied cells.')
        except (ValueError,AttributeError) as error:
            if self.drawing_height_error is None:self.show_error(str(error))
        finally:self.cancel_gesture()

    def commit(self,before,after,record=True,with_qu=None):
        f=self.owner.factor
        after=[[number(fmt(number(fmt(value/f))*f)) if j<4 else number(fmt(value)) for j,value in enumerate(row)] for row in after]
        before_mode=self.owner.with_qu.isChecked();after_mode=before_mode if with_qu is None else bool(with_qu)
        if before==after and before_mode==after_mode:return
        # 写入前用现有模型检查，非法几何整次拒绝，不留下半次操作。
        from case_model import Figure
        data,_=self.owner.collect();figure=Figure(int(self.owner.mirror.isChecked()),int(after_mode),after)
        errors,_,_=validate(data,figure)
        if errors:
            top=max((r[3] for r in after),default=0.)
            if int(data['case_start']) in (3,4,5,6) and data['z_start']<=top:
                self.update_drawing_height_error(data,top)
            raise ValueError('\n'.join(errors))
        self.clear_drawing_height_error()
        if record:self.undo_stack.append((before,after,before_mode,after_mode));self.undo_stack=self.undo_stack[-40:];self.redo_stack.clear()
        self.expected=(self.signature,after,bool(self.owner.mirror.isChecked()),after_mode)
        self.owner.loading=True
        self.owner.blocks.setUpdatesEnabled(False)
        try:
            old=self.owner.with_qu.blockSignals(True);self.owner.with_qu.setChecked(after_mode);self.owner.with_qu.blockSignals(old)
            self.owner.blocks.clearSelection();self.active_block=None
            self.owner.blocks.setRowCount(len(after))
            for i,row in enumerate(after):
                if i<len(before) and row==before[i]:continue
                for j,value in enumerate(row):self.owner.set_cell(self.owner.blocks,i,j,fmt(value/self.owner.factor if j<4 else value))
        finally:
            self.owner.blocks.setUpdatesEnabled(True);self.owner.loading=False
        self.owner.changed();self.owner.refresh();self.update_history_buttons()

    def delete_selected(self):
        if self.profile_editor.active:self.profile_editor.action(self.profile_editor.delete_selected);return
        if self.owner.geometry.currentData()!=26:return
        try:
            before=self.rows();selected=set(self.owner.selected_rows());cells=set(self.selected_cells);active=self.active_cell
            self.commit(before,[r for i,r in enumerate(before) if i not in selected]);self.select_cells(cells,active)
        except ValueError as error:self.show_error(str(error))

    def undo(self):
        if self.profile_editor.active:self.profile_editor.action(self.profile_editor.undo);return
        if not self.undo_stack:return
        if isinstance(self.undo_stack[-1],dict) and self.undo_stack[-1].get('kind')=='substrate':
            item=self.undo_stack.pop()
            try:self.rectangle_editor.commit(item['before'],False);self.redo_stack.append(item)
            except ValueError as error:self.undo_stack.append(item);self.rectangle_editor.action(lambda:(_ for _ in ()).throw(error))
            self.update_history_buttons();return
        item=self.undo_stack.pop();before,after,before_mode,after_mode=item
        try:self.commit(after,before,False,with_qu=before_mode);self.redo_stack.append(item)
        except ValueError as error:self.undo_stack.append(item);self.show_error(str(error))
        self.update_history_buttons()

    def redo(self):
        if self.profile_editor.active:self.profile_editor.action(lambda:self.profile_editor.undo(True));return
        if not self.redo_stack:return
        if isinstance(self.redo_stack[-1],dict) and self.redo_stack[-1].get('kind')=='substrate':
            item=self.redo_stack.pop()
            try:self.rectangle_editor.commit(item['after'],False);self.undo_stack.append(item)
            except ValueError as error:self.redo_stack.append(item);self.rectangle_editor.action(lambda:(_ for _ in ()).throw(error))
            self.update_history_buttons();return
        item=self.redo_stack.pop();before,after,before_mode,after_mode=item
        try:self.commit(before,after,False,with_qu=after_mode);self.undo_stack.append(item)
        except ValueError as error:self.redo_stack.append(item);self.show_error(str(error))
        self.update_history_buttons()

    def update_history_buttons(self):
        profile=self.profile_editor
        self.tool_buttons['undo'].setEnabled(bool(profile.undo_stack if profile.active else self.undo_stack))
        self.tool_buttons['redo'].setEnabled(bool(profile.redo_stack if profile.active else self.redo_stack))

    def cancel_gesture(self):
        self.gesture=None
        if hasattr(self,'profile_editor'):
            was_dragging=self.profile_editor.drag is not None;self.profile_editor.cancel_drag()
            if was_dragging:self.profile_editor.draw_overlay()
        if hasattr(self,'rectangle_editor'):
            was_dragging=self.rectangle_editor.drag is not None;self.rectangle_editor.cancel_drag()
            if was_dragging:self.rectangle_editor.draw_overlay()
        if self.preview is not None:
            try:self.preview.remove()
            except (ValueError,NotImplementedError):pass
            self.preview=None;self.redraw_overlays()

    def zoom(self,scale,x=None,z=None):
        if self.ax is None:return
        a,b=self.ax.get_xlim();c,d=self.ax.get_ylim();x=(a+b)/2 if x is None else x;z=(c+d)/2 if z is None else z
        if (b-a)*scale<1e-10 or (d-c)*scale<1e-10:return
        self.ax.set_xlim(x+(a-x)*scale,x+(b-x)*scale);self.ax.set_ylim(z+(c-z)*scale,z+(d-z)*scale);self.update_grid()

    def on_scroll(self,event):
        if event.inaxes is self.ax and not self.gesture:self.zoom(.8 if event.button=='up' else 1.25,event.xdata,event.ydata)

    def fit_view(self):
        if self.data is None:return
        self.sync(self.data,self.fig,self.stats,force_fit=True)

    def on_key(self,event):
        try:self.handle_key(event)
        except (ValueError,OverflowError) as error:self.show_error(str(error))

    def handle_key(self,event):
        key=event.key
        if key in ('ctrl+z','cmd+z'):self.undo()
        elif key in ('ctrl+y','cmd+y','ctrl+shift+z'):self.redo()
        elif key=='escape':
            self.cancel_gesture();self.clipboard=None;self.paste_point=None;self.deselect_substrate();self.highlight_selection()
        elif self.profile_editor.active and key in ('delete','backspace'):self.delete_selected()
        elif self.tool=='select' and self.owner.geometry.currentData()==26:
            if key in ('delete','backspace'):self.delete_selected()
            elif key in ('ctrl+c','cmd+c'):self.copy_selection()
            elif key in ('ctrl+x','cmd+x'):self.copy_selection(True)
            elif key in ('ctrl+v','cmd+v'):self.paste_selection()
            elif key in ('ctrl+a','cmd+a'):self.select_all_cells()
            elif key in ('left','right','up','down'):self.navigate(key)
            elif key in ('shift+left','shift+right','shift+up','shift+down'):self.navigate(key.split('+')[1],extend=True)
            elif key in ('enter','f2'):self.open_edit_dialog('block')
