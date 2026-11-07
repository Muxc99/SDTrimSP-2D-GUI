"""共用基底尺寸手柄；24/25 同步轮廓，26 始终保留凸起块优先。"""
import math
import numpy as np
from case_model import number, fmt, validate
from PySide6.QtCore import Qt
from substrate_profile import ProfileEditError, PROFILE_MODES, check_profile, profile_text, centered_rows

RECTANGLE_MODES=(10,20,24,25,26,27)
FIELDS=('geo_x','geo_z','geo_dx','geo_dz')

class SubstrateRectangleEditor:
    def __init__(self,editor):
        self.editor=editor;self.owner=editor.owner;self.drag=None;self.artists=[];self.selected_shape=False
    @property
    def active(self):return self.owner.geometry.currentData() in RECTANGLE_MODES
    @property
    def selected_shape(self):return self.editor.substrate_selected
    @selected_shape.setter
    def selected_shape(self,value):self.editor.substrate_selected=bool(value)
    def values(self):
        return {key:number(self.owner.edits[key].text())*self.owner.factor for key in FIELDS}
    def action(self,slot):
        try:return slot()
        except ValueError as error:
            if isinstance(error,ProfileEditError):self.editor.show_error(error.zh,error.en)
            else:self.editor.show_error(str(error))
            self.draw_overlay();return False

    def handles(self,values,rows=None):
        x,z=values['geo_x'],values['geo_z']
        if self.owner.geometry.currentData() in PROFILE_MODES:
            rows=self.editor.profile_editor.rows if rows is None else rows
            if not rows:return {}
            xs,zs=np.array(rows).T;left=float(np.interp(-x,xs,zs));right=float(np.interp(x,xs,zs))
            return {'tl':(-x,left),'tr':(x,right),'bl':(-x,z),'br':(x,z),
                    'left':(-x,(left+z)/2),'right':(x,(right+z)/2),'bottom':(0.,z)}
        return {'tl':(-x,0.),'tr':(x,0.),'bl':(-x,z),'br':(x,z),
                'left':(-x,z/2),'right':(x,z/2),'bottom':(0.,z),'top':(0.,0.)}

    def hit(self,event):
        if not self.selected_shape or event.xdata is None:return None
        handles=self.handles(self.values());keys=list(handles)
        if not handles:return None
        if self.owner.geometry.currentData()==26:
            handles.pop('top');keys=list(handles)
        pixels=self.editor.ax.transData.transform(np.array(list(handles.values()))/self.owner.factor)
        distance=np.hypot(pixels[:,0]-event.x,pixels[:,1]-event.y);index=int(np.argmin(distance))
        if distance[index]<=10:return keys[index]
        # 在无凸起干扰的模式，可直接拖动边；26保留既有块/空格选择。
        if self.owner.geometry.currentData()!=26:
            x,z=event.xdata*self.owner.factor,event.ydata*self.owner.factor;v=self.values()
            ax=self.editor.ax;scale_x=abs(ax.get_xlim()[1]-ax.get_xlim()[0])*self.owner.factor/ax.bbox.width*7
            scale_z=abs(ax.get_ylim()[1]-ax.get_ylim()[0])*self.owner.factor/ax.bbox.height*7
            left_top=handles['tl'][1];right_top=handles['tr'][1]
            if v['geo_z']<=z<=left_top:
                if abs(x+v['geo_x'])<=scale_x:return 'left'
            if v['geo_z']<=z<=right_top:
                if abs(x-v['geo_x'])<=scale_x:return 'right'
            if -v['geo_x']<=x<=v['geo_x']:
                if abs(z-v['geo_z'])<=scale_z:return 'bottom'
                if self.owner.geometry.currentData() not in PROFILE_MODES and abs(z)<=scale_z:return 'top'
        return None

    def on_press(self,event):
        if not self.active or self.editor.tool!='select' or event.button!=1:return False
        if self.owner.geometry.currentData()==26:
            # z>=0 整个凸起编辑区（包括空白格）仍走原有 Excel 式选择。
            # 基底必须从 z<0 的实体内部选中，不能抢占框选、Alt 移动或右键。
            if str(getattr(event,'key','') or '') or event.ydata*self.owner.factor>=-1e-8:
                self.selected_shape=False;self.draw_overlay();return False
            if self.editor.hit(event.xdata*self.owner.factor,event.ydata*self.owner.factor)[0] is not None:
                self.selected_shape=False;self.draw_overlay();return False
        kind=self.hit(event)
        if kind is None:
            if self.owner.geometry.currentData() in PROFILE_MODES:return False
            values=self.values();x=event.xdata*self.owner.factor;z=event.ydata*self.owner.factor
            if -values['geo_x']<=x<=values['geo_x'] and values['geo_z']<=z<=0:
                self.selected_shape=True;self.clear_block_selection();self.draw_overlay();return True
            self.selected_shape=False;self.draw_overlay();return False
        if kind=='top':
            self.editor.message('参考上边固定为 z=0；拖动侧边调整宽度，拖动底边调整深度。','The reference top stays at z=0. Drag a side to change width or the bottom to change depth.');return True
        self.drag={'handle':kind,'before':self.values(),'after':self.values()}
        if self.owner.geometry.currentData() in PROFILE_MODES:
            self.drag['before_rows']=[r[:] for r in self.editor.profile_editor.rows]
        self.selected_shape=True
        self.clear_block_selection()
        self.editor.message('拖动基底手柄：宽度绕 x=0 对称调整，底边保持水平；松开后检查几何规则。','Drag substrate handles: width changes symmetrically about x=0; the bottom stays level. Geometry is checked on release.')
        self.draw_overlay();return True

    def clear_block_selection(self):
        self.editor.selected_cells.clear();self.editor.active_cell=None;self.editor.active_block=None
        self.editor.selection_anchor=None;self.owner.blocks.clearSelection();self.editor.highlight_selection()

    def candidate(self,event):
        values=dict(self.drag['before']);kind=self.drag['handle'];mode=self.owner.geometry.currentData()
        x,z=event.xdata*self.owner.factor,event.ydata*self.owner.factor
        if kind in ('tl','tr','bl','br','left','right'):
            half=-x if kind in ('tl','bl','left') else x
            if mode!=10:half=round(half/values['geo_dx'])*values['geo_dx']
            if half<=0:raise ProfileEditError('横向半宽必须大于零，左右边不能交叉。','Half-width must be positive; the left and right edges cannot cross.')
            values['geo_x']=half
            if mode==10:values['geo_dx']=2*half
        if kind in ('bl','br','bottom'):
            bottom=round(z/values['geo_dz'])*values['geo_dz']
            if bottom>=0:raise ProfileEditError('底边须位于 z=0 以下，至少保留一层网格。','The bottom must stay below z=0, with at least one mesh layer.')
            values['geo_z']=bottom
        if mode in PROFILE_MODES:
            ratio=values['geo_x']/self.drag['before']['geo_x']
            rows=[[number(fmt(a*ratio)),b] for a,b in self.drag['before_rows']]
            if kind in ('tl','tr'):
                rows[0 if kind=='tl' else -1][1]=round(z/values['geo_dz'])*values['geo_dz']
            check_profile(rows,dict(self.editor.data,**values))
            self.drag['profile_rows']=rows
        return values

    def on_motion(self,event):
        if self.drag is None or event.inaxes is not self.editor.ax or event.xdata is None:return
        self.drag['after']=self.candidate(event);self.draw_overlay(self.drag['after'],self.drag.get('profile_rows'))

    def checked(self,values,text=None):
        data,fig=self.owner.collect();candidate=dict(data,**values)
        if text is not None:
            candidate['_files']=dict(data['_files'],**{'rauh.inp':text})
            check_profile(centered_rows(text,candidate['case_geo'],candidate['geo_x']),candidate)
        before_errors=validate(data,fig)[0];errors=validate(candidate,fig)[0]
        added=[e for e in errors if e not in before_errors]
        if added:raise ProfileEditError('此尺寸不符合当前几何规则，已保留原基底：\n'+'\n'.join(added), 'This size violates the current geometry rules; the original substrate is retained.\n'+'\n'.join(added))
        if candidate['case_geo']==27 and candidate.get('pr_amp',0)>0:
            wl=candidate['pr_wl']
            if wl<=0 or not math.isclose(2*candidate['geo_x']/wl,round(2*candidate['geo_x']/wl),abs_tol=1e-7):
                raise ProfileEditError('余弦模式要求靶总宽包含整数个波长；请选择兼容 pr_wl 的网格列。','For cosine geometry, the full width must contain an integer number of wavelengths. Choose a grid column compatible with pr_wl.')
        return candidate,fig

    def commit(self,values,record=True,profile_rows=None):
        before=self.values()
        values={key:number(fmt(value)) for key,value in values.items()}
        profile=self.editor.profile_editor;text=None;oldtext=None
        if profile.active:
            oldtext=profile.current_text()
            if profile_rows is None:
                profile_rows=[[x*values['geo_x']/before['geo_x'],z] for x,z in profile.rows]
            text=profile_text(profile_rows,self.owner.geometry.currentData(),values['geo_x'],oldtext)
        if values==before and (text is None or text==oldtext):return
        candidate,fig=self.checked(values,text)
        self.write_values(values,candidate,fig,text)
        if record:
            if profile.active:
                profile.undo_stack.append({'kind':'substrate','before':{'values':before,'text':oldtext},'after':{'values':values,'text':text}})
                profile.undo_stack=profile.undo_stack[-40:];profile.redo_stack.clear()
            else:
                self.editor.undo_stack.append({'kind':'substrate','before':before,'after':values})
                self.editor.undo_stack=self.editor.undo_stack[-40:];self.editor.redo_stack.clear()
        self.editor.update_history_buttons()

    def restore(self,snapshot):
        candidate,fig=self.checked(snapshot['values'],snapshot['text'])
        self.write_values(snapshot['values'],candidate,fig,snapshot['text'])

    def write_values(self,values,data,fig,text=None):
        loading=self.owner.loading;self.owner.loading=True
        try:
            for key,value in values.items():self.owner.edits[key].setText(fmt(value/self.owner.factor))
            if text is not None:
                self.owner.set_auxiliary_file('rauh.inp',text)
                self.editor.profile_editor.expected=self.editor.profile_editor.state(data,text)
        finally:self.owner.loading=loading
        signature=(str(self.owner.source),self.owner.factor,data['geo_x'],data['geo_z'],data['geo_dx'],data['geo_dz'],data['case_geo'])
        rows=self.editor.rows() if fig is not None else []
        self.editor.expected=(signature,rows,bool(self.owner.mirror.isChecked()),bool(self.owner.with_qu.isChecked()))
        self.owner.changed();self.owner.refresh()

    def on_release(self,event):
        if self.drag is None:return
        drag=self.drag
        try:
            if event.inaxes is self.editor.ax and event.xdata is not None:
                values=self.candidate(event);rows=self.drag.get('profile_rows');self.drag=None;self.commit(values,profile_rows=rows)
        finally:self.drag=None;self.draw_overlay()

    def cancel_drag(self):self.drag=None

    def draw_overlay(self,values=None,rows=None):
        for artist in self.artists:
            try:artist.remove()
            except (ValueError,NotImplementedError):pass
        self.artists=[];ax=self.editor.ax
        if not self.active or ax is None:return
        if not self.selected_shape:
            self.editor.redraw_overlays();return
        values=self.values() if values is None else values;x,z=values['geo_x'],values['geo_z'];f=self.owner.factor
        profile=self.owner.geometry.currentData() in PROFILE_MODES
        if profile:
            self.editor.profile_editor.draw_overlay(rows,dict(self.editor.data,**values))
        else:
            line,=ax.plot(np.array([-x,x,x,-x,-x])/f,np.array([0,0,z,z,0])/f,'--',lw=1.,color='#4e92a8',alpha=.8,zorder=6);self.artists.append(line)
        handles=self.handles(values,rows)
        for keys,marker,size,fill in [(('bl','br') if profile else ('tl','tr','bl','br'),'s',6,'white'),(('left','right','bottom'),'D',5,'#c4dce6')]:
            points=np.array([handles[k] for k in keys if k in handles])/f
            if len(points):
                artist,=ax.plot(points[:,0],points[:,1],marker,ms=size,mfc=fill,mec='#3b819c',linestyle='None',zorder=9);self.artists.append(artist)
        if profile:self.editor.canvas.draw_idle();return
        if self.selected_shape:
            unit=self.owner.unit.currentText();text=self.editor.text('基底矩形调整','Resize substrate rectangle')+f'\n2 × geo_x = {fmt(2*x/f)} {unit}\ngeo_z = {fmt(z/f)} {unit}'
            text+='\n'+self.editor.text('参考上边 z=0；不可增加节点。','Reference top z=0; nodes cannot be added.')
            if self.owner.geometry.currentData()==10:text+='\n'+self.editor.text('一维模式：geo_dx 同步为总宽。','1D mode: geo_dx follows the full width.')
            self.editor.selection_info.setText(text)
        self.editor.canvas.draw_idle()
