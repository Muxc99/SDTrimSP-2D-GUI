"""24/25 基底闭合外轮廓：上边节点可编辑，底边由 geo_z 定义。"""
from bisect import bisect_left
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (QGroupBox,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QMenu,QCheckBox,
    QDialog,QDialogButtonBox,QFormLayout,QDoubleSpinBox)
from case_model import Profile, number, fmt, surface_profile

PROFILE_MODES = (24, 25)

class ProfileEditError(ValueError):
    def __init__(self, zh, en):
        super().__init__(zh)
        self.zh, self.en = zh, en

def centered_rows(text, mode, half):
    return [[x-half if mode == 24 else x, z] for x, z in Profile.parse(text).rows]

def profile_text(rows, mode, half, original=''):
    """仅重写声明的第一组点；未编辑时保留原文，编辑时仍保留尾部数据。"""
    file_rows = [[number(fmt(x+half if mode == 24 else x)), number(fmt(z))] for x, z in rows]
    old = Profile.parse(original) if original else Profile([])
    return Profile(file_rows, old.original, old.baseline, old.tail).render()

def check_profile(rows, data):
    if not 2 <= len(rows) <= 100000:
        raise ProfileEditError('轮廓至少需要两个端点，最多 100000 点。', 'Keep 2–100000 profile points.')
    rows = [[number(str(x)), number(str(z))] for x, z in rows]
    if any(b[0] <= a[0] for a, b in zip(rows, rows[1:])):
        raise ProfileEditError('上边节点不可左右交叉或重合；请保持 x 严格递增。', 'Upper nodes cannot cross or share x; keep x strictly increasing.')
    half = data['geo_x']
    if rows[0][0] > -half+1e-8 or rows[-1][0] < half-1e-8:
        raise ProfileEditError('上边界必须覆盖完整靶宽。', 'The upper boundary must cover the full target width.')
    _, height = surface_profile(dict(data, case_geo=25), {'rauh.inp':profile_text(rows, 25, half)})
    if min(z for x,z in rows) <= data['geo_z'] or float(np.min(height)) <= data['geo_z']:
        raise ProfileEditError('节点须高于基底底边，不能使闭合轮廓翻折。', 'Nodes must stay above the bottom so the outline cannot fold over.')
    return rows

def closed_outline(rows, half, bottom):
    """按靶宽裁取显示外框；文件中的外延点保持原样。"""
    if not rows:
        return []
    xs, zs = np.array(rows).T
    top = [[-half,float(np.interp(-half,xs,zs))]]
    top.extend([list(r) for r in rows if -half < r[0] < half])
    top.append([half,float(np.interp(half,xs,zs))])
    return [[-half,bottom], *top, [half,bottom], [-half,bottom]]

def visible_profile_indices(rows, half):
    """Return source-row indices that lie inside the displayed target width."""
    return [i for i, row in enumerate(rows) if -half-1e-8 <= row[0] <= half+1e-8]

class SubstrateProfileEditor:
    def __init__(self, editor):
        self.editor=editor;self.owner=editor.owner
        self.mode=None;self.file_mode=None;self.case_token=None;self.expected=None
        self.rows=[];self.selected=None;self.selected_shape=False;self.drag=None;self.artists=[]
        self.undo_stack=[];self.redo_stack=[]
        self.panel=QGroupBox(editor);layout=QVBoxLayout(self.panel)
        layout.setContentsMargins(7,12,7,6);layout.setSpacing(6)
        self.note=QLabel();self.note.setWordWrap(True);layout.addWidget(self.note)
        self.add_button=QPushButton();self.add_button.setCheckable(True)
        self.add_button.clicked.connect(lambda checked:self.editor.set_tool('brush' if checked else 'select'))
        controls=QHBoxLayout();controls.addWidget(self.add_button,1)
        self.snap_grid=QCheckBox();self.snap_grid.setChecked(False);controls.addWidget(self.snap_grid)
        layout.addLayout(controls)
        row=QHBoxLayout();layout.addLayout(row)
        self.delete_button=QPushButton();self.reset_button=QPushButton()
        row.addWidget(self.delete_button);row.addWidget(self.reset_button)
        self.delete_button.clicked.connect(lambda:self.action(self.delete_selected))
        self.reset_button.clicked.connect(lambda:self.action(self.reset_rectangle))
        self.count_label=QLabel();self.count_label.setWordWrap(True);layout.addWidget(self.count_label)
        self.encoding_label=QLabel();self.encoding_label.setWordWrap(True);layout.addWidget(self.encoding_label)
        layout.addStretch(1)
        for b in (self.add_button,self.snap_grid,self.delete_button,self.reset_button):b.setProperty('tooltipDelayMs',500)
        self.panel.hide()

    @property
    def active(self):return self.owner.geometry.currentData() in PROFILE_MODES
    @property
    def selected_shape(self):return self.editor.substrate_selected
    @selected_shape.setter
    def selected_shape(self,value):self.editor.substrate_selected=bool(value)
    def tr(self,zh,en):return self.editor.text(zh,en)
    def data(self):return self.owner.collect()[0]
    def current_text(self):return self.owner.current_files().get('rauh.inp','')

    def action(self,slot):
        try:return slot()
        except (ValueError,OSError) as error:
            self.editor.show_error(error.zh,error.en) if isinstance(error,ProfileEditError) else self.editor.show_error(str(error))
            self.draw_overlay();return False

    def state(self,data,text):
        return (id(self.owner.namelist),data['case_geo'],data['geo_x'],data['geo_z'],data['geo_dx'],data['geo_dz'],data['pr_amp'],data['pr_wl'],text)

    def geometry_changed(self):
        if self.owner.loading:return
        new=self.owner.geometry.currentData();old=self.mode
        try:
            if new in PROFILE_MODES:
                half=number(self.owner.edits['geo_x'].text())*self.owner.factor
                if half<=0:raise ProfileEditError('请先设置有效的横向半宽。','Set a positive target half-width first.')
                text=self.current_text();encoding=old if old in PROFILE_MODES else self.file_mode
                if not text:
                    self.owner.set_auxiliary_file('rauh.inp',profile_text([[-half,0.],[half,0.]],new,half))
                elif encoding in PROFILE_MODES and encoding!=new:
                    self.owner.set_auxiliary_file('rauh.inp',profile_text(centered_rows(text,encoding,half),new,half,text))
                self.file_mode=new
        except ValueError as error:
            if old is not None:
                was=self.owner.geometry.blockSignals(True);self.owner.geometry.setCurrentIndex(self.owner.geometry.findData(old));self.owner.geometry.blockSignals(was)
            self.action(lambda:(_ for _ in ()).throw(error));return
        self.owner.changed();self.owner.refresh()

    def sync(self,data):
        token=id(self.owner.namelist)
        if token!=self.case_token:
            self.case_token=token;self.file_mode=data['case_geo'] if data['case_geo'] in PROFILE_MODES else None
            self.expected=None;self.selected=None;self.selected_shape=False;self.undo_stack.clear();self.redo_stack.clear()
        self.mode=data['case_geo']
        target=self.panel if self.active else self.editor.block_settings
        if self.editor.sidebar.widget(1) is not target:
            sizes=self.editor.sidebar.sizes();old=self.editor.sidebar.replaceWidget(1,target)
            old.hide();old.setParent(self.editor);target.show();self.editor.sidebar.setSizes(sizes)
        for widget in (self.owner.mirror,self.owner.with_qu):widget.setEnabled(not self.active)
        if not self.active:self.cancel_drag();return
        self.file_mode=self.mode;text=self.current_text();expected=self.state(data,text)
        if self.expected!=expected:self.undo_stack.clear();self.redo_stack.clear();self.cancel_drag()
        self.expected=expected
        try:self.rows=centered_rows(text,self.mode,data['geo_x'])
        except ValueError:self.rows=[]
        if self.selected is not None and not 0<=self.selected<len(self.rows):self.selected=None
        self.retranslate()

    def retranslate(self):
        self.panel.setTitle(self.tr('基底闭合轮廓','Closed substrate outline'))
        self.note.setText(self.tr('先点击基底显示手柄，再拖动节点、侧边或底边；点击空白处取消选择。','Click the substrate to show handles, then drag nodes, sides or bottom. Click outside to deselect.'))
        self.add_button.setText(self.tr('增加边上节点','Add node on edge'))
        self.add_button.setToolTip(self.tr('点击按钮后，再点击上边界增加节点；右键节点可精确编辑坐标。','Activate and click the upper edge to add a node. Right-click a node to edit exact coordinates.'))
        self.snap_grid.setText(self.tr('吸附网格','Snap to grid'))
        self.snap_grid.setToolTip(self.tr('开启后拖动节点会吸附到最近网格交点；默认关闭。','When enabled, dragged nodes snap to the nearest grid intersection. Off by default.'))
        self.add_button.setChecked(self.editor.tool=='brush')
        self.delete_button.setText(self.tr('删除选中节点','Delete node'));self.reset_button.setText(self.tr('恢复矩形','Reset rectangle'))
        self.reset_button.setToolTip(self.tr('将基础轮廓恢复为两个 z=0 的端点，可撤销。若 pr_amp 非零，附加余弦仍保留。','Reset the base profile to two endpoints at z=0. Undo is available. Nonzero pr_amp still adds cosine modulation.'))
        self.count_label.setText(self.tr(f'上边界 {len(self.rows)} 个节点 · 闭合外框 {len(self.rows)+2} 个节点',f'{len(self.rows)} upper nodes · {len(self.rows)+2} outline nodes'))
        encoding=self.tr('左边界起算','left-edge origin') if self.mode==24 else self.tr('中心坐标','centered x')
        self.encoding_label.setText(f'{self.mode} · rauh.inp: '+encoding+self.tr('；文件长度为 Å。','; file lengths in Å.'))
        self.delete_button.setEnabled(self.selected is not None and self.selected not in (0,len(self.rows)-1))

    def tool_changed(self,key):
        self.add_button.setChecked(key=='brush')
        descriptions={
            'select':('先点击选中基底；拖动节点、侧边或底边调整形状。Delete 删除内部节点。','Click to select the substrate; drag nodes, sides or bottom. Delete removes interior nodes.'),
            'brush':('点击上边界增加节点，再拖动节点改变轮廓；底边保持闭合。','Click the upper edge to add a node, then drag nodes to reshape the closed outline.'),
            'erase':('点击删除上边界内部节点；两端点保留以维持闭合。','Click to delete an interior upper node. Endpoints are retained to keep the outline closed.'),
            'pan':('拖动画面；滚轮缩放，适应全部恢复视图。','Drag to pan; wheel to zoom; Fit restores the view.')}
        self.editor.message(*descriptions.get(key,descriptions['select']))

    def prepare(self):
        if self.owner.raw_pending and not self.owner.apply_raw_edits():
            raise ProfileEditError('请先修正未应用的输入文本。','Correct the pending input text first.')
        # 文本可能刚被编辑，禁止旧画布覆盖新文本。
        current=centered_rows(self.current_text(),self.mode,self.data()['geo_x'])
        if current!=self.rows:self.owner.refresh();self.rows=current

    def commit(self,rows):
        data=self.data();rows=check_profile(rows,data);before=self.current_text()
        try:text=profile_text(rows,self.mode,data['geo_x'],before)
        except ValueError:text=profile_text(rows,self.mode,data['geo_x'])
        if text==before:return
        self.write_text(text)
        self.undo_stack.append((before,text));self.undo_stack=self.undo_stack[-40:];self.redo_stack.clear()
        self.editor.update_history_buttons()

    def write_text(self,text):
        data=self.data();self.owner.set_auxiliary_file('rauh.inp',text);self.expected=self.state(data,text)
        self.owner.changed();self.owner.refresh()

    def undo(self,redo=False):
        source,target=(self.redo_stack,self.undo_stack) if redo else (self.undo_stack,self.redo_stack)
        if not source:return
        item=source.pop()
        try:
            if isinstance(item,dict):self.editor.rectangle_editor.restore(item['after'] if redo else item['before'])
            else:self.write_text(item[1] if redo else item[0])
        except ValueError:source.append(item);raise
        target.append(item);self.editor.update_history_buttons()

    def reset_rectangle(self):
        half=self.data()['geo_x'];self.selected=None;self.commit([[-half,0.],[half,0.]])
        self.editor.message('基础轮廓已恢复矩形；附加余弦参数仍保留，可撤销。','Base outline reset to a rectangle. Additional cosine parameters are retained. Undo is available.')

    def delete_selected(self):
        self.prepare();i=self.selected
        if i is None:return
        if i in (0,len(self.rows)-1):raise ProfileEditError('两端点不可删除；可上下拖动调整高度。','Endpoints cannot be deleted; drag them vertically to change height.')
        self.selected=None;self.commit([r[:] for j,r in enumerate(self.rows) if j!=i])

    def set_node_position(self,index,x,z):
        """Set a profile node in physical Angstroms; coordinates need not lie on the mesh."""
        self.prepare()
        if not 0<=index<len(self.rows):return
        rows=[r[:] for r in self.rows];rows[index]=[float(x),float(z)]
        rows=check_profile(rows,self.data())
        self.selected=index;self.selected_shape=True;self.commit(rows)
        self.retranslate();self.draw_overlay()

    def edit_node_position(self,index):
        if not 0<=index<len(self.rows):return
        factor=self.owner.factor;unit=self.owner.unit.currentText()
        dialog=QDialog(self.editor);dialog.setWindowTitle(self.tr('编辑节点坐标','Edit node coordinates'))
        form=QFormLayout(dialog);x_input=QDoubleSpinBox();z_input=QDoubleSpinBox()
        for widget in (x_input,z_input):
            widget.setDecimals(6);widget.setRange(-1e9,1e9);widget.setKeyboardTracking(False)
        x_input.setValue(self.rows[index][0]/factor);z_input.setValue(self.rows[index][1]/factor)
        form.addRow(self.tr(f'x / {unit}',f'x / {unit}'),x_input)
        form.addRow(self.tr(f'z / {unit}',f'z / {unit}'),z_input)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(self.tr('确定','OK'))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(self.tr('取消','Cancel'))
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec()==QDialog.DialogCode.Accepted:self.set_node_position(index,x_input.value()*factor,z_input.value()*factor)

    def nearest(self,event):
        if not self.rows:return None
        data=self.data();indices=visible_profile_indices(self.rows,data['geo_x'])
        if not indices:return None
        pixels=self.editor.ax.transData.transform(np.array([self.rows[i] for i in indices])/self.owner.factor)
        d=np.hypot(pixels[:,0]-event.x,pixels[:,1]-event.y);i=int(np.argmin(d))
        return indices[i] if d[i]<=11 else None

    def inside(self,event):
        if not self.rows or event.xdata is None:return False
        x=event.xdata*self.owner.factor;z=event.ydata*self.owner.factor;data=self.data()
        if not -data['geo_x']<=x<=data['geo_x']:return False
        xs,zs=surface_profile(data,data['_files']);return data['geo_z']<=z<=float(np.interp(x,xs,zs))

    def edge_point(self,event):
        if len(self.rows)<2:return None
        points=self.editor.ax.transData.transform(np.array(self.rows)/self.owner.factor)
        p=np.array([event.x,event.y]);best=None
        for i,(a,b) in enumerate(zip(points,points[1:])):
            v=b-a;t=float(np.clip(np.dot(p-a,v)/np.dot(v,v),0,1));q=a+t*v;distance=float(np.linalg.norm(p-q))
            if distance<=12 and (best is None or distance<best[0]):best=(distance,i,t)
        if best is None:return None
        _,i,t=best;a=np.array(self.rows[i]);b=np.array(self.rows[i+1]);return list(a+t*(b-a))

    def add_on_edge(self,event):
        self.prepare();point=self.edge_point(event)
        if point is None:raise ProfileEditError('请点击上边界线段添加节点。','Click an upper-edge segment to add a node.')
        data=self.data();x=-data['geo_x']+round((point[0]+data['geo_x'])/data['geo_dx'])*data['geo_dx']
        xs=[r[0] for r in self.rows];i=bisect_left(xs,x)
        if i==0 or i==len(xs) or abs(xs[i]-x)<=1e-8:
            raise ProfileEditError('此网格列已有节点，请选择其他位置。','This grid column already has a node; choose another position.')
        # 插点仍在线段上，不改变原形；拖动时 x、z 均吸附网格。
        z=float(np.interp(x,xs,[r[1] for r in self.rows]));rows=[r[:] for r in self.rows];rows.insert(i,[x,z])
        self.selected=i;self.commit(rows)

    def on_press(self,event):
        self.prepare()
        if self.editor.tool=='select' and not self.selected_shape:
            self.selected=None;self.selected_shape=self.inside(event) or self.edge_point(event) is not None
            self.retranslate();self.draw_overlay();self.editor.rectangle_editor.draw_overlay();return
        self.selected=self.nearest(event)
        if event.button==3:
            menu=QMenu(self.editor);add=menu.addAction(self.tr('在此增加边上节点','Add node on edge here'))
            add.setEnabled(self.edge_point(event) is not None);add.triggered.connect(lambda:self.action(lambda:self.add_on_edge(event)))
            edit=menu.addAction(self.tr('编辑节点坐标…','Edit node coordinates…'))
            edit.setEnabled(self.selected is not None)
            if self.selected is not None:edit.triggered.connect(lambda:self.action(lambda:self.edit_node_position(self.selected)))
            delete=menu.addAction(self.tr('删除选中节点','Delete selected node'));delete.setEnabled(self.selected is not None and self.selected not in (0,len(self.rows)-1))
            delete.triggered.connect(lambda:self.action(self.delete_selected));self.menu=menu;menu.popup(QCursor.pos())
        elif self.editor.tool=='erase':self.delete_selected()
        elif self.editor.tool=='brush' and self.selected is None:
            self.selected_shape=True;self.add_on_edge(event)
        elif self.selected is not None:
            self.selected_shape=True;self.drag={'index':self.selected,'before':[r[:] for r in self.rows],'rows':[r[:] for r in self.rows]}
        elif self.inside(event):
            self.selected_shape=True
        else:self.selected_shape=False
        self.retranslate();self.draw_overlay()
        self.editor.rectangle_editor.draw_overlay()

    def on_motion(self,event):
        if self.drag is None or event.inaxes is not self.editor.ax or event.xdata is None:return
        data=self.data();i=self.drag['index'];rows=[r[:] for r in self.drag['before']]
        x=event.xdata*self.owner.factor;z=event.ydata*self.owner.factor
        if self.snap_grid.isChecked():
            x=-data['geo_x']+round((x+data['geo_x'])/data['geo_dx'])*data['geo_dx']
            z=round(z/data['geo_dz'])*data['geo_dz']
            if i in (0,len(rows)-1):x=rows[i][0]
        if (i>0 and x<=rows[i-1][0]) or (i<len(rows)-1 and x>=rows[i+1][0]):
            self.editor.message('上边节点不能左右交叉或与相邻节点重合。','Upper nodes cannot cross or overlap adjacent nodes.');return
        if z<=data['geo_z']:
            self.editor.message('上边节点须高于基底底边。','Upper nodes must stay above the substrate bottom.');return
        rows[i]=[x,z];self.drag['rows']=rows;self.draw_overlay(rows)

    def on_release(self,event):
        if self.drag is None:return
        self.on_motion(event);rows=self.drag['rows'];self.drag=None
        if event.inaxes is self.editor.ax and event.xdata is not None:self.commit(rows)
        self.draw_overlay()

    def cancel_drag(self):self.drag=None

    def draw_overlay(self,rows=None,data_override=None):
        for artist in self.artists:
            try:artist.remove()
            except (ValueError,NotImplementedError):pass
        self.artists=[];ax=self.editor.ax
        if not self.active or ax is None:return
        if not self.selected_shape:
            self.editor.selection_info.setText(self.tr('未选中基底；点击基底显示节点与尺寸手柄。','Substrate not selected. Click the substrate to show nodes and resize handles.'))
            self.editor.canvas.draw_idle()
            return
        rows=self.rows if rows is None else rows;data=self.editor.data if data_override is None else data_override
        if rows and data is not None:
            f=self.owner.factor;closed=np.array(closed_outline(rows,data['geo_x'],data['geo_z']))/f
            line,=ax.plot(closed[:,0],closed[:,1],'-',lw=1.5,color='#e07a26',zorder=8);self.artists.append(line)
            visible=visible_profile_indices(rows,data['geo_x'])
            pts=np.array([rows[i] for i in visible])/f
            nodes,=ax.plot(pts[:,0],pts[:,1],'o',ms=6,mfc='white',mec='#e07a26',zorder=9);self.artists.append(nodes)
            if self.selected is not None and self.selected<len(rows) and self.selected in visible:
                # ``selected`` indexes the source rows, while ``pts`` only
                # contains the visible subset.  Read the selected source row
                # directly so hidden out-of-width rows cannot shift the marker.
                x,z=np.array(rows[self.selected])/f
                dot,=ax.plot([x],[z],'o',ms=9,color='#138eb1',zorder=10);self.artists.append(dot)
        text=self.tr('基底已选中\n拖动上边节点改轮廓；拖动侧边、底边和角点改尺寸。\n宽度绕中心调整，底边保持水平。','Substrate selected\nDrag upper nodes to reshape; drag sides, bottom or corners to resize.\nWidth stays centered and the bottom stays level.')
        if self.selected is not None and self.selected<len(rows):
            x,z=rows[self.selected];text+=f'\n#{self.selected+1}   x={fmt(x/self.owner.factor)}   z={fmt(z/self.owner.factor)} {self.owner.unit.currentText()}'
        if data and data.get('pr_amp',0)>0:text+='\n'+self.tr('橙线为基础轮廓；灰线上表面含附加余弦。','Orange: base outline; gray upper surface includes cosine modulation.')
        self.editor.selection_info.setText(text);self.editor.selection_info.setToolTip(text);self.editor.canvas.draw_idle()
