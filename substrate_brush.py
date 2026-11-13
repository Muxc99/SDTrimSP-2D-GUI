"""Substrate-only composition strokes on the main target canvas."""
import math
import numpy as np
from PySide6.QtGui import QCursor
from case_model import surface_profile,validate
from target_inputs import LOCAL_FILE,grid_shape,parse_local,render_local,fractions

class SubstrateBrush:
    def __init__(self,editor):
        self.editor=editor;self.owner=editor.owner;self.stroke=None;self.erasing=False

    def state(self):
        d,_=self.owner.collect()
        return (self.owner.current_files().get(LOCAL_FILE),bool(d.get('l_clust')),bool(d.get('l_clust_read')))

    def prepare(self):
        if self.owner.raw_pending and not self.owner.apply_raw_edits():
            raise ValueError(self.owner.raw_text('请先修正输入文本。','Correct pending input text first.'))
        d,fig=self.owner.collect()
        if d['case_geo'] not in (10,20,24,25,26,27):raise ValueError('Unsupported substrate geometry')
        self.d=d;self.fig=fig;self.nx,self.nz=grid_shape(d)
        text=self.owner.current_files().get(LOCAL_FILE)
        self.rows=parse_local(text,d) if text is not None else {}
        self.before=self.state();self.sx,self.sz=surface_profile(d,d['_files'])

    def cell(self,point):
        x,z=point;d=self.d
        return math.floor((x+self.nx*d['geo_dx']/2)/d['geo_dx'])+1,math.floor(z/d['geo_dz']+self.nz)+1

    def bounds(self,key):
        ix,iz=key;d=self.d;x=(ix-1)*d['geo_dx']-self.nx*d['geo_dx']/2;z=(iz-1-self.nz)*d['geo_dz']
        return [x,x+d['geo_dx'],z,z+d['geo_dz']]

    def in_substrate(self,point):
        x,z=point;d=self.d
        return -d['geo_x']<=x<d['geo_x'] and d['geo_z']<=z<float(np.interp(x,self.sx,self.sz))

    def begin(self,event):
        try:
            self.prepare();point=(event.xdata*self.owner.factor,event.ydata*self.owner.factor)
            if not self.in_substrate(point):return
            d=self.d
            if not self.erasing:
                if d.get('l_clust') and not d.get('l_clust_read'):
                    raise ValueError(self.owner.raw_text('先在靶材功能中关闭内置团簇，再使用基底成分画笔。','Disable built-in clusters in Target features before painting substrate composition.'))
                if any(d.get(k) for k in ('l_two_comp','l_two_comp2','l_two_comp3')):
                    raise ValueError(self.owner.raw_text('请先关闭化合物模型。','Disable the compound model first.'))
            self.q=[float(self.editor.substrate_composition.item(0,i).text()) for i in range(len(d['symbol']))]
            if not self.erasing:fractions(self.q,len(d['symbol']))
            self.stroke={'last':point,'cells':set(),'erase':self.erasing};self.paint_to(point)
        except (ValueError,AttributeError) as error:self.editor.show_error(str(error));self.cancel()

    def paint_to(self,point):
        stroke=self.stroke
        if stroke is None:return
        d=self.d;a=stroke['last'];dx=d['geo_dx'];dz=d['geo_dz']
        count=max(1,math.ceil(max(abs(point[0]-a[0])/dx,abs(point[1]-a[1])/dz)*3))
        if count>20000:raise ValueError('笔划过长 / Stroke too long')
        for i in range(count+1):
            p=(a[0]+(point[0]-a[0])*i/count,a[1]+(point[1]-a[1])*i/count)
            if not self.in_substrate(p):continue
            key=self.cell(p)
            if not -5000<=key[1]<=self.nz+4999:continue
            stroke['cells'].add(key)
            if stroke['erase']:self.rows.pop(key,None)
            else:self.rows[key]=self.q[:]
        if len(stroke['cells'])>20000:raise ValueError('单次笔划超过 20000 格 / Stroke exceeds 20000 cells')
        stroke['last']=point
        from matplotlib.collections import PolyCollection
        f=self.owner.factor;polys=[]
        for key in stroke['cells']:
            x1,x2,z1,z2=self.bounds(key);z1=max(z1,d['geo_z'])
            xs=np.unique(np.r_[x1,x2,self.sx[(self.sx>x1)&(self.sx<x2)]])
            top=np.maximum(np.minimum(z2,np.interp(xs,self.sx,self.sz)),z1)
            polys.append(np.array([(x1,z1),(x2,z1),*zip(xs[::-1],top[::-1])])/f)
        e=self.editor
        if e.preview is None:
            e.preview=PolyCollection(polys,facecolors='#e76f51' if stroke['erase'] else '#17a673',edgecolors='#138658',alpha=.5,zorder=8);e.ax.add_collection(e.preview,autolim=False)
        else:e.preview.set_verts(polys)
        e.redraw_overlays()

    def end(self,event):
        if self.stroke is None:return
        try:
            if event.inaxes is self.editor.ax and event.xdata is not None:self.paint_to((event.xdata*self.owner.factor,event.ydata*self.owner.factor))
            if not self.stroke['cells']:return
            text=render_local(self.rows,self.d)
            after=(text,self.before[1] if self.stroke['erase'] else True,self.before[2] if self.stroke['erase'] else True)
            if self.before==after:return
            self.apply(after)
            self.editor.undo_stack.append({'kind':'local','before':self.before,'after':after})
            self.editor.undo_stack=self.editor.undo_stack[-40:];self.editor.redo_stack.clear();self.editor.update_history_buttons()
        except ValueError as error:self.editor.show_error(str(error))
        finally:self.cancel();self.editor.cancel_gesture()

    def apply(self,state):
        text,enabled,read=state;d,fig=self.owner.collect();files=dict(self.owner.current_files())
        if text is None:files.pop(LOCAL_FILE,None)
        else:files[LOCAL_FILE]=text
        candidate=dict(d,_files=files,l_clust=enabled,l_clust_read=read)
        errors,_,_=validate(candidate,fig)
        if errors:raise ValueError('\n'.join(errors))
        if text is None:
            self.owner.files.pop(LOCAL_FILE,None);self.owner.removed_files.add(LOCAL_FILE);self.owner.raw_pending.discard(LOCAL_FILE)
            edit=self.owner.aux_editors.pop(LOCAL_FILE,None)
            if edit:self.owner.aux_tabs.removeTab(self.owner.aux_tabs.indexOf(edit));edit.deleteLater()
        else:self.owner.set_auxiliary_file(LOCAL_FILE,text)
        self.owner.set_extra_values({'l_clust':'.true.' if enabled else '.false.','l_clust_read':'.true.' if read else '.false.'})
        self.owner.dirty=True;self.owner.refresh()

    def menu(self,event):
        from brush_menu import brush_menu
        d,fig=self.owner.collect();point=(event.xdata*self.owner.factor,event.ydata*self.owner.factor)
        menu=brush_menu(self.editor,self.owner,self.editor.substrate_composition,d,fig,point)
        self.editor.context_menu=menu;menu.popup(QCursor.pos())

    def cancel(self):self.stroke=None
