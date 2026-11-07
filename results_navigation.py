"""Friendly result navigation. Display ratios never change scientific data."""
import math
import numpy as np
from PySide6.QtCore import Qt,QSize
from PySide6.QtGui import QIcon,QPixmap,QPainter,QPen,QColor,QLinearGradient
from PySide6.QtWidgets import (QWidget,QHBoxLayout,QToolButton,QStyle,QMenu,QDialog,QVBoxLayout,QFormLayout,QGroupBox,QDoubleSpinBox,QLineEdit,QCheckBox,QDialogButtonBox,QLabel,QComboBox,QSizePolicy)
from matplotlib.patches import Rectangle
from matplotlib.ticker import MultipleLocator,AutoLocator
from element_picker import NoWheelComboBox

SPATIAL_PLOTS={'fraction','density','total_density','surface','particle_positions','trajectory'}

def navigation_icon(name):
    pix=QPixmap(22,22);pix.fill(Qt.GlobalColor.transparent);p=QPainter(pix);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setPen(QPen(QColor('#237a9a'),1.8))
    if name=='gradient':
        gradient=QLinearGradient(3,0,19,0);gradient.setColorAt(0,QColor('#2449ae'));gradient.setColorAt(.5,QColor('#f5d233'));gradient.setColorAt(1,QColor('#df3625'))
        p.fillRect(3,5,16,12,gradient);p.drawRect(3,5,16,12)
    elif name in ('plus','minus'):
        p.drawEllipse(3,2,12,12);p.drawLine(14,14,20,20);p.drawLine(6,8,12,8)
        if name=='plus':p.drawLine(9,5,9,11)
    elif name=='pan':
        p.drawLine(7,11,7,4);p.drawLine(10,10,10,2);p.drawLine(13,10,13,3);p.drawLine(16,11,16,5);p.drawLine(7,6,10,4);p.drawLine(10,3,13,4);p.drawLine(13,5,16,6);p.drawLine(16,5,18,7);p.drawLine(18,7,18,14);p.drawLine(18,14,15,20);p.drawLine(15,20,9,20);p.drawLine(9,20,3,13);p.drawLine(3,13,4,11);p.drawLine(4,11,7,14)
    elif name=='data':
        p.drawLine(3,18,3,3);p.drawLine(3,18,20,18);p.drawLine(5,14,10,8);p.drawLine(10,8,16,11);p.drawEllipse(8,6,4,4);p.drawLine(15,4,20,4);p.drawLine(17,2,17,6)
    elif name=='box':
        p.setPen(QPen(QColor('#237a9a'),1.5,Qt.PenStyle.DashLine));p.drawRect(3,3,15,15)
    elif name=='axes':
        p.drawLine(4,3,4,18);p.drawLine(4,18,20,18);p.drawLine(4,3,2,6);p.drawLine(4,3,6,6);p.drawLine(20,18,17,16);p.drawLine(20,18,17,20)
    elif name=='center':
        p.drawEllipse(6,6,9,9);p.drawLine(1,10,8,10);p.drawLine(13,10,21,10);p.drawLine(10,1,10,8);p.drawLine(10,13,10,21)
    elif name=='ratio':
        p.drawRect(4,4,14,14);p.drawLine(1,4,1,18);p.drawLine(4,21,18,21)
    else:p.drawRect(4,4,14,14)
    p.end();return QIcon(pix)

class ResultAxisDialog(QDialog):
    def __init__(self,navigation):
        super().__init__(navigation.view);self.nav=navigation;v=navigation.view;ax=v.results_axes;self.setWindowTitle(v.tr('坐标轴设置','Axis settings'));self.setMinimumWidth(430)
        layout=QVBoxLayout(self);box=QGroupBox(v.tr('显示范围','Visible range'));form=QFormLayout(box);layout.addWidget(box);self.bounds=[]
        if navigation.spatial:box.setTitle(box.title()+' ('+v.unit.currentText()+')')
        for label,value in zip((v.tr('X 最小值','X minimum'),v.tr('X 最大值','X maximum'),v.tr('Z 最小值','Z minimum') if navigation.spatial else v.tr('Y 最小值','Y minimum'),v.tr('Z 最大值','Z maximum') if navigation.spatial else v.tr('Y 最大值','Y maximum')),(*sorted(ax.get_xlim()),*sorted(ax.get_ylim()))):
            spin=QDoubleSpinBox();spin.setDecimals(10);spin.setRange(-1e100,1e100);spin.setValue(value);spin.setKeyboardTracking(False);spin.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed);spin.setMinimumWidth(150);form.addRow(label,spin);self.bounds.append(spin)
        self.equal=QCheckBox(v.tr('锁定横纵单位长度显示比例','Lock physical unit display ratio'));self.equal.setChecked(navigation.spatial and navigation.ratio_locked);self.equal.setEnabled(navigation.spatial);form.addRow(self.equal)
        self.ratio=QDoubleSpinBox();self.ratio.setDecimals(3);self.ratio.setRange(.01,100.);self.ratio.setValue(navigation.unit_ratio if navigation.spatial else 1.);self.ratio.setEnabled(self.equal.isChecked());self.equal.toggled.connect(self.ratio.setEnabled);form.addRow(v.tr('横向 / 纵向单位显示长度','X / Y unit display length'),self.ratio)
        hint=QLabel(v.tr('1 表示同样的物理长度显示得一样长（正方形保持正方形）。2 表示横向每单位显示长度是纵向的两倍。关闭锁定后可分别设置横纵范围。锁定时会扩展范围以兼顾比例。','1 keeps equal physical lengths equal on screen (squares stay square). 2 doubles the displayed horizontal unit length. Unlock to set ranges independently. Locked ranges expand to preserve the chosen ratio.'));hint.setWordWrap(True);hint.setStyleSheet('color:#61758b;font-size:9pt;');layout.addWidget(hint)
        appearance=QGroupBox(v.tr('外观','Appearance'));style=QFormLayout(appearance);layout.addWidget(appearance);self.title=QLineEdit(ax.get_title());self.xlabel=QLineEdit(ax.get_xlabel());self.ylabel=QLineEdit(ax.get_ylabel());style.addRow(v.tr('图像标题','Plot title'),self.title);style.addRow(v.tr('横轴名称','X-axis label'),self.xlabel);style.addRow(v.tr('纵轴名称','Y-axis label'),self.ylabel)
        self.grid=QCheckBox(v.tr('显示浅色网格','Show light grid'));self.grid.setChecked(any(line.get_visible() for line in ax.get_xgridlines()));style.addRow(self.grid)
        self.tick_x=QDoubleSpinBox();self.tick_y=QDoubleSpinBox()
        for spin in (self.tick_x,self.tick_y):spin.setDecimals(8);spin.setRange(0,1e80);spin.setSpecialValueText(v.tr('自动','Auto'));spin.setKeyboardTracking(False)
        self.tick_x.setValue(navigation._styles.get(navigation.style_key(),{}).get('tick_x',0));self.tick_y.setValue(navigation._styles.get(navigation.style_key(),{}).get('tick_y',0));style.addRow(v.tr('横轴刻度间隔','X tick interval'),self.tick_x);style.addRow(v.tr('纵轴刻度间隔','Y tick interval'),self.tick_y)
        categorical=v.kind.currentData() in ('energy','timing');self.tick_y.setEnabled(not categorical)
        for spin in self.findChildren(QDoubleSpinBox):spin.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed);spin.setMinimumWidth(125)
        self.error=QLabel();self.error.setStyleSheet('color:#b43e3e');self.error.setWordWrap(True);layout.addWidget(self.error)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Apply|QDialogButtonBox.StandardButton.Close);buttons.button(QDialogButtonBox.StandardButton.Apply).setText(v.tr('应用','Apply'));buttons.button(QDialogButtonBox.StandardButton.Close).setText(v.tr('关闭','Close'));buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply);buttons.rejected.connect(self.close);layout.addWidget(buttons)
    def apply(self):
        nav=self.nav;v=nav.view;ax=v.results_axes;x0,x1,y0,y1=[s.value() for s in self.bounds]
        if not x0<x1 or not y0<y1:self.error.setText(v.tr('最小值必须小于最大值。','Minimum must be less than maximum.'));return False
        for lo,hi,step in ((x0,x1,self.tick_x.value()),(y0,y1,self.tick_y.value())):
            if step>0 and (hi-lo)/step>150:self.error.setText(v.tr('刻度间隔太小，请将单轴刻度数控制在150以内。','Tick interval is too small. Keep fewer than 150 ticks per axis.'));return False
        nav.ratio_locked=self.equal.isChecked() if nav.spatial else nav.ratio_locked
        if nav.spatial:nav.unit_ratio=self.ratio.value()
        ax.set_aspect('auto');ax.set_xlim(x0,x1);ax.set_ylim(y0,y1)
        if nav.spatial and nav.ratio_locked:nav.enforce_ratio(expand=True)
        old=nav._default_labels;style={'grid':self.grid.isChecked(),'tick_x':self.tick_x.value(),'tick_y':self.tick_y.value() if self.tick_y.isEnabled() else 0}
        for key,text,default in zip(('title','xlabel','ylabel'),(self.title.text(),self.xlabel.text(),self.ylabel.text()),old):
            if text!=default:style[key]=text
        nav._styles[nav.style_key()]=style;nav.apply_style();nav.capture_view();nav.push_history();nav.refresh_labels();v.canvas.draw_idle();self.error.clear()
        for spin,value in zip(self.bounds,(*sorted(ax.get_xlim()),*sorted(ax.get_ylim()))):spin.setValue(value)
        return True

class ResultsNavigation(QWidget):
    def __init__(self,view):
        super().__init__(view);self.view=view;self.ax=None;self._active_key=None;self._views={};self._styles={};self._history=[];self._history_index=-1;self.ratio_locked=True;self.unit_ratio=1.;self.center_mode='zero';self._drag=None;self._box=None;self._changing=False;self._last_canvas_size=None;self._default_labels=('','','');self._tip=None;self._fit_extents=None
        row=QHBoxLayout(self);row.setContentsMargins(5,3,5,3);row.setSpacing(3);self.buttons={};self.hint=QLabel(self);self.hint.hide();row.addStretch(1)
        specs=[('fit','显示全部','Fit all',QStyle.StandardPixmap.SP_TitleBarMaxButton,lambda:self.fit('all')),('back','后退','Back',QStyle.StandardPixmap.SP_ArrowBack,self.back),('forward','前进','Forward',QStyle.StandardPixmap.SP_ArrowForward,self.forward),('pan','平移','Pan',None,None),('plus','放大','Zoom in',None,lambda:self.zoom(.8)),('minus','缩小','Zoom out',None,lambda:self.zoom(1.25)),('box','框选放大','Box zoom',None,None),('data','数据查看','Data tips',None,None),('center','居中','Center',None,None),('axes','坐标设置','Axes',None,self.axis_settings),('save','保存图片','Save PNG',QStyle.StandardPixmap.SP_DialogSaveButton,view.export_png)]
        self._button_text={}
        specs.insert(-1,('gradient','颜色渐变','Color gradient',None,view.edit_gradient))
        for name,zh,en,icon,callback in specs:
            b=QToolButton(self);b.setProperty('tooltipDelayMs',500);b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly);b.setIcon(self.style().standardIcon(icon) if icon is not None else navigation_icon(name));b.setIconSize(QSize(18,18));b.setAutoRaise(True);b.setFixedSize(32,32);self.buttons[name]=b;self._button_text[name]=(zh,en);row.addWidget(b)
            if callback:b.clicked.connect(callback)
        for name in ('pan','box','data'):
            self.buttons[name].setCheckable(True);self.buttons[name].toggled.connect(lambda checked,n=name:self.mode_toggled(n,checked))
        self.buttons['pan'].setChecked(True);
        menu=QMenu(self.buttons['center']);self._center_actions=[]
        for zh,en,mode in [('z=0 居中','Center z=0','zero'),('靶表面居中','Center surface','surface')]:
            action=menu.addAction(view.tr(zh,en));action.triggered.connect(lambda checked=False,m=mode:self.fit(m));self._center_actions.append((action,zh,en))
        self.buttons['center'].setMenu(menu);self.buttons['center'].setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup);
        self.setStyleSheet('ResultsNavigation {background:transparent;border:0;} QToolButton {padding:4px;border:1px solid transparent;border-radius:4px;color:#28546b;} QToolButton:hover {background:#e0f0f6;border-color:#a8cedd;} QToolButton:checked {background:#d7edf1;border-color:#64a8bb;color:#126780;} QToolButton:disabled {color:#a5b1b9;}')
        self._connections=[view.canvas.mpl_connect(event,handler) for event,handler in [('button_press_event',self.press),('motion_notify_event',self.motion),('button_release_event',self.release),('scroll_event',self.scroll),('resize_event',self.resize),('key_press_event',self.key),('button_press_event',self.double_click)]]
        view.canvas.setFocusPolicy(Qt.FocusPolicy.StrongFocus);self.refresh_labels()
    @property
    def spatial(self):return self.view.kind.currentData() in SPATIAL_PLOTS
    def view_key(self):
        v=self.view;return (id(v.dataset),v.kind.currentData(),None if self.spatial else (v.unit.currentData(),v.fluence_unit.currentData()))
    def style_key(self):return (id(self.view.dataset),self.view.kind.currentData(),self.view.unit.currentData(),self.view.fluence_unit.currentData())
    def refresh_labels(self):
        v=self.view
        tips={'pan':('平移：按住左键直接拖动图像；鼠标中键也可平移。','Pan: drag with the left mouse button. The middle button also pans.'),'data':('数据查看：点击图中单元或曲线数据点显示数值；空白处显示光标坐标。','Data tips: click a material cell or a curve point for values; blank areas show cursor coordinates.'),'fit':('显示全部数据；双击图像也可恢复此视图。','Fit all data. Double-click the plot to restore this view.'),'box':('开启后拖出矩形以放大；关闭后直接拖动平移。','Drag a rectangle to zoom. Turn off to drag-pan.'),'center':('将纵轴 z=0 或靶表面放在图中央。','Center z=0 or the target surface.'),'ratio':('横纵单位长度显示比例；正方形默认显示为正方形。可在坐标设置中修改。','Physical unit display ratio. Squares remain square by default. Change it in Axes.'),'axes':('设置坐标范围、单位显示比例、标题、网格和刻度间隔。','Set ranges, physical unit ratio, labels, grid and tick intervals.')}
        for name,b in self.buttons.items():
            b.setText(v.tr(*self._button_text[name]));b.setToolTip(v.tr(*tips[name]) if name in tips else b.text());b.setAccessibleName(b.text())
            if name not in ('back','forward'):b.setEnabled(v.current_frame is not None)
        self.buttons['center'].setEnabled(v.current_frame is not None and self.spatial)
        self.buttons['gradient'].setEnabled(v.gradient_mappable() is not None)
        for a,zh,en in self._center_actions:a.setText(v.tr(zh,en))
        self.buttons['back'].setEnabled(self._history_index>0);self.buttons['forward'].setEnabled(self._history_index+1<len(self._history));self.update_cursor()
    def update_cursor(self):self.view.canvas.setCursor(Qt.CursorShape.CrossCursor if self.buttons['box'].isChecked() or self.buttons['data'].isChecked() else Qt.CursorShape.OpenHandCursor if self.buttons['pan'].isChecked() else Qt.CursorShape.ArrowCursor)
    def mode_toggled(self,name,checked):
        self._drag=None
        if checked:
            for other in ('pan','box','data'):
                if other!=name:
                    was=self.buttons[other].blockSignals(True);self.buttons[other].setChecked(False);self.buttons[other].blockSignals(was)
        self.update_cursor()

    def capture_view(self):
        if self.ax is None or self._active_key is None or self.view.current_frame is None:return
        x,y=self.ax.get_xlim(),self.ax.get_ylim();factor=getattr(self,'_active_factor',1.)
        self._views[self._active_key]=(tuple(v/factor for v in x),tuple(v/factor for v in y))
    def ready(self):
        v=self.view;self._drag=None;self._box=None;self.ax=v.results_axes;self._tip=None;self._fit_extents=np.array(self.ax.dataLim.extents,dtype=float);key=self.view_key();changed=key!=self._active_key;self._active_key=key;self._active_factor=v.unit.currentData() if self.spatial else 1.;self._default_labels=(self.ax.get_title(),self.ax.get_xlabel(),self.ax.get_ylabel());self._last_canvas_size=v.canvas.get_width_height()
        if len(self._views)>100:self._views={k:value for k,value in self._views.items() if k[0]==id(v.dataset)}
        self.ax.set_aspect('auto');self.ax.set_position(v.RESULTS_AXES_BOUNDS)
        if v.current_frame is not None:
            if key in self._views:
                x,y=self._views[key];self.ax.set_xlim(np.array(x)*self._active_factor);self.ax.set_ylim(np.array(y)*self._active_factor)
                if self.spatial and self.ratio_locked:self.enforce_ratio()
            elif self.spatial:self.fit(self.center_mode,record=False)
            self.apply_style()
        if changed:self._history=[];self._history_index=-1
        self.capture_view();self.push_history();self.refresh_labels()
        v.canvas.setToolTip(v.tr('直接按住左键拖动平移；滚轮以鼠标位置为中心缩放；双击显示全部。横纵单位默认等长，比例可在“坐标设置”中修改。','Drag with the left mouse button to pan. Wheel zooms at the cursor. Double-click fits all data. Physical units have equal display length by default; change this in Axes.'))
    def pixel_ratio(self):
        bbox=self.ax.get_window_extent();return max(bbox.width,1.)/max(bbox.height,1.)
    def enforce_ratio(self,expand=False):
        if not self.spatial or not self.ratio_locked:return
        ax=self.ax;ax.set_aspect('auto');x0,x1=ax.get_xlim();y0,y1=ax.get_ylim();dx=abs(x1-x0);dy=abs(y1-y0);desired=self.pixel_ratio()/self.unit_ratio
        if expand:dx=max(dx,dy*desired)
        dy=dx/desired;cx=(x0+x1)/2;cy=(y0+y1)/2
        ax.set_xlim(cx-dx/2,cx+dx/2);ax.set_ylim(cy-dy/2,cy+dy/2)
        ax.set_aspect(1./self.unit_ratio,adjustable='datalim');ax.set_position(self.view.RESULTS_AXES_BOUNDS)
    def surface_height(self):
        v=self.view
        if hasattr(v,'preview_surface_height'):return v.preview_surface_height()
        data=v.dataset or {};snaps=data.get('cells',[])
        if snaps:
            from results_analysis import envelope
            i=min(max(0,v.step.currentIndex()),len(snaps)-1);df=envelope(snaps[i]).dropna();dx=df.x2_A-df.x1_A
            if len(df) and dx.sum()>0:return float((df.height_A*dx).sum()/dx.sum())*v.unit.currentData()
        surfaces=data.get('surface',[])
        if surfaces:return float(surfaces[-1]['data'].z_A.median())*v.unit.currentData()
        return 0.
    def fit(self,mode='all',record=True):
        if self.ax is None or self.view.current_frame is None:return
        ax=self.ax;raw=np.array(self._fit_extents if self._fit_extents is not None else ax.dataLim.extents,dtype=float)
        if not np.isfinite(raw).all():return
        x0,y0,x1,y1=raw;dx=max(x1-x0,1e-9)*1.08;dy=max(y1-y0,1e-9)*1.12;cx=(x0+x1)/2;cy=(y0+y1)/2
        if self.spatial:
            if mode in ('zero','surface'):
                cy=0. if mode=='zero' else self.surface_height();self.center_mode=mode
                if self.ratio_locked:dy=max(dx/(self.pixel_ratio()/self.unit_ratio),2*abs(y1-cy)*1.12,1e-9)
                else:dy=2*max(abs(y0-cy),abs(y1-cy))*1.12
            if self.ratio_locked:dx=max(dx,dy*self.pixel_ratio()/self.unit_ratio);dy=dx/(self.pixel_ratio()/self.unit_ratio)
        ax.set_aspect('auto');ax.set_xlim(cx-dx/2,cx+dx/2);ax.set_ylim(cy-dy/2,cy+dy/2)
        self.apply_style()
        if self.spatial and self.ratio_locked:self.enforce_ratio()
        self.view.canvas.draw_idle()
        if record:self.capture_view();self.push_history();self.refresh_labels()
    def push_history(self):
        if self.ax is None:return
        state=(*self.ax.get_xlim(),*self.ax.get_ylim())
        if self._history and self._history_index>=0 and np.allclose(state,self._history[self._history_index],rtol=1e-12,atol=1e-15):return
        self._history=self._history[:self._history_index+1]+[state];self._history=self._history[-100:];self._history_index=len(self._history)-1;self.refresh_labels()
    def history_move(self,delta):
        i=self._history_index+delta
        if not 0<=i<len(self._history):return
        self._history_index=i;x0,x1,y0,y1=self._history[i];self.ax.set_aspect('auto');self.ax.set_xlim(x0,x1);self.ax.set_ylim(y0,y1)
        if self.spatial and self.ratio_locked:self.enforce_ratio()
        self.capture_view();self.refresh_labels();self.view.canvas.draw_idle()
    def back(self):self.history_move(-1)
    def forward(self):self.history_move(1)
    def toggle_ratio(self):
        if not self.spatial:return
        self.ratio_locked=not self.ratio_locked
        if self.ratio_locked:self.unit_ratio=1.;self.enforce_ratio(expand=True)
        else:self.ax.set_aspect('auto')
        self.capture_view();self.push_history();self.refresh_labels();self.view.canvas.draw_idle()
    def zoom(self,factor,center=None):
        if self.ax is None or self.view.current_frame is None:return
        x0,x1=self.ax.get_xlim();y0,y1=self.ax.get_ylim();cx,cy=center if center is not None else ((x0+x1)/2,(y0+y1)/2);new=(cx+(x0-cx)*factor,cx+(x1-cx)*factor,cy+(y0-cy)*factor,cy+(y1-cy)*factor)
        if not np.isfinite(new).all() or new[1]-new[0]<1e-13 or new[3]-new[2]<1e-13:return
        self.ax.set_xlim(new[:2]);self.ax.set_ylim(new[2:]);self.apply_style();self.capture_view();self.push_history();self.view.canvas.draw_idle()
    def scroll(self,event):
        if event.inaxes is not self.ax or event.xdata is None or event.ydata is None:return
        self.zoom(.8**max(-5,min(5,event.step)),(event.xdata,event.ydata))
    def press(self,event):
        if event.inaxes is not self.ax or event.button not in (1,2) or event.dblclick or self.view.current_frame is None:return
        self.view.canvas.setFocus()
        if event.button==1 and self.buttons['data'].isChecked():self.show_data_tip(event);return
        if event.button==1 and not self.buttons['pan'].isChecked() and not self.buttons['box'].isChecked():return
        self._drag=(event.x,event.y,self.ax.get_xlim(),self.ax.get_ylim(),event.xdata,event.ydata)
        if self.buttons['box'].isChecked() and event.button==1:
            self._box=Rectangle((event.xdata,event.ydata),0,0,fill=True,facecolor='#2c91ab',alpha=.18,edgecolor='#147894',linewidth=1.5);self.ax.add_patch(self._box)
        else:self.view.canvas.setCursor(Qt.CursorShape.ClosedHandCursor)
    def motion(self,event):
        if self._drag is None:return
        px,py,xlim,ylim,xdata,ydata=self._drag
        if self._box is not None:
            x,y=self.ax.transData.inverted().transform((event.x,event.y));self._box.set_bounds(min(x,xdata),min(y,ydata),abs(x-xdata),abs(y-ydata))
        else:
            bbox=self.ax.get_window_extent();dx=(event.x-px)*(xlim[1]-xlim[0])/bbox.width;dy=(event.y-py)*(ylim[1]-ylim[0])/bbox.height;self.ax.set_xlim(np.array(xlim)-dx);self.ax.set_ylim(np.array(ylim)-dy)
        self.view.canvas.draw_idle()
    def release(self,event):
        if self._drag is None:return
        start=self._drag;self._drag=None
        if self._box is not None:
            patch=self._box;self._box=None;patch.remove()
            if abs(event.x-start[0])>5 and abs(event.y-start[1])>5:
                x,y=self.ax.transData.inverted().transform((event.x,event.y));self.ax.set_xlim(sorted((start[4],x)));self.ax.set_ylim(sorted((start[5],y)))
                if self.spatial and self.ratio_locked:self.enforce_ratio(expand=True)
            self.buttons['box'].setChecked(False);self.buttons['pan'].setChecked(True)
        self.capture_view();self.push_history();self.update_cursor();self.view.canvas.draw_idle()
    def double_click(self,event):
        if event.dblclick and event.button==1 and event.inaxes is not None and hasattr(event.inaxes,'_colorbar'):
            self._drag=None;self.view.edit_gradient();return
        if event.dblclick and event.inaxes is self.ax:self.fit('all')
    def resize(self,event):
        if self.ax is None or self.view.current_frame is None:return
        size=self.view.canvas.get_width_height()
        if size==self._last_canvas_size:return
        self._last_canvas_size=size
        if self.spatial and self.ratio_locked:self.enforce_ratio();self.capture_view()
    def key(self,event):
        if event.key in ('+','='):self.zoom(.8)
        elif event.key=='-':self.zoom(1.25)
        elif event.key in ('home','h'):self.fit('all')
        elif event.key=='escape':
            self.buttons['pan'].setChecked(True)
            if self._tip is not None:self._tip.set_visible(False);self.view.canvas.draw_idle()
    def show_data_tip(self,event):
        v=self.view;ax=self.ax;x,y=event.xdata,event.ydata;label=v.tr('光标坐标','Cursor coordinates');value=None;point=(x,y)
        frame=v.current_frame
        if frame is not None and all(c in frame.columns for c in ('x1_A','x2_A','z1_A','z2_A')):
            f=v.unit.currentData();xa,za=x/f,y/f;cut=frame[(frame.x1_A<=xa)&(frame.x2_A>=xa)&(frame.z1_A<=za)&(frame.z2_A>=za)&(frame.density_at_A3>0)]
            if not cut.empty:
                cell=cut.iloc[0];label=v.tr('单元','Cell')+' '+str(int(cell.cell_id));value=float(cell.display_value) if 'display_value' in cell else None
                if value is not None:label+='\n'+v.species.currentText()+' = '+f'{value:.6g}'+('' if v.kind.currentData()=='fraction' else ' atoms/cm³')
        elif not hasattr(v,'preview_data_tip'):
            best=14.**2
            for line in ax.lines:
                xy=np.asarray(line.get_xydata());valid=np.isfinite(xy).all(axis=1);xy=xy[valid]
                if not len(xy):continue
                pixels=ax.transData.transform(xy);dist=((pixels-[event.x,event.y])**2).sum(axis=1);i=int(np.argmin(dist))
                if dist[i]<best:best=dist[i];point=tuple(xy[i]);label=line.get_label() if not line.get_label().startswith('_') else v.tr('数据点','Data point')
            if label==v.tr('光标坐标','Cursor coordinates'):
                for collection in ax.collections:
                    if not hasattr(collection,'get_offsets'):continue
                    xy=np.asarray(collection.get_offsets())
                    if xy.ndim!=2 or xy.shape[1]!=2 or not len(xy):continue
                    pixels=ax.transData.transform(xy);dist=((pixels-[event.x,event.y])**2).sum(axis=1);i=int(np.argmin(dist))
                    if dist[i]<best:best=dist[i];point=tuple(xy[i]);label=v.tr('数据点','Data point')
        if hasattr(v,'preview_data_tip'):label=v.preview_data_tip(x,y)
        text=label+f'\nx = {point[0]:.6g}'+('\nz' if self.spatial else '\ny')+f' = {point[1]:.6g}'
        if self._tip is not None:
            try:self._tip.remove()
            except ValueError:pass
        bbox=ax.get_window_extent();right=event.x>bbox.x0+bbox.width*.65;top=event.y>bbox.y0+bbox.height*.65
        self._tip=ax.annotate(text,xy=point,xytext=(-14 if right else 14,-14 if top else 14),textcoords='offset points',ha='right' if right else 'left',va='top' if top else 'bottom',fontsize=9,color='#244557',bbox=dict(boxstyle='round,pad=.5',fc='#f8fcff',ec='#79acbd',alpha=.97),arrowprops=dict(arrowstyle='-',color='#6a9aac'),zorder=20);v.canvas.draw_idle()

    def apply_style(self):
        ax=self.ax;style=self._styles.get(self.style_key(),{})
        for key,setter in (('title',ax.set_title),('xlabel',ax.set_xlabel),('ylabel',ax.set_ylabel)):
            if key in style:setter(style[key])
        if 'grid' in style:
            if style['grid']:ax.grid(True,alpha=.15)
            else:ax.grid(False)
        for key,axis in (('tick_x',ax.xaxis),('tick_y',ax.yaxis)):
            if key in style and not (key=='tick_y' and self.view.kind.currentData() in ('energy','timing')):
                step=style[key];span=np.ptp(ax.get_xlim() if key=='tick_x' else ax.get_ylim());axis.set_major_locator(MultipleLocator(step) if step>0 and span/step<150 else AutoLocator())
    def axis_settings(self):
        if self.view.current_frame is None:return
        if hasattr(self.view,'timer'):self.view.timer.stop();self.view.play_button.setText(self.view.tr('播放','Play'))
        dialog=ResultAxisDialog(self);dialog.exec()
