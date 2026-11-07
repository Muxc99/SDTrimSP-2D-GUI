"""Shared controls for initial geometry schematics, without input mutation."""
from pathlib import Path
import numpy as np
import pandas as pd
from PySide6.QtWidgets import QWidget,QVBoxLayout,QFileDialog,QMessageBox
from results_navigation import ResultsNavigation
from case_model import parse_layers

class PreviewChoice:
    def __init__(self,data,text=lambda:''):self.data=data;self.text=text
    def currentData(self):return self.data()
    def currentText(self):return self.text()

class PreviewNavigation(QWidget):
    RESULTS_AXES_BOUNDS=(.09,.12,.77,.77)
    COLORBAR_BOUNDS=(.90,.12,.018,.77)
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.canvas=owner.canvas;self.results_axes=None
        self.dataset={};self.current_frame=None;self._geometry_key=None;self._case_key=None
        self.kind=PreviewChoice(lambda:'fraction');self.unit=PreviewChoice(lambda:1./owner.factor,lambda:owner.unit.currentText())
        self.fluence_unit=PreviewChoice(lambda:1.);self.species=owner.color_species
        from gradient_editor import InitialGradientController
        owner.initial_gradients=InitialGradientController(owner)
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        self.toolbar=ResultsNavigation(self);layout.addWidget(self.toolbar);self.toolbar.hint.setMinimumWidth(0)
    def tr(self,zh,en):return en if getattr(self.owner,'ui_language','zh')=='en' else zh
    def gradient_mappable(self):
        cb=getattr(self.owner.plot,'_initial_colorbar',None)
        return cb.mappable if cb is not None and cb.ax in self.owner.plot.axes else None
    def edit_gradient(self):
        if self.gradient_mappable() is not None:self.owner.initial_gradients.edit(self.canvas)
    def unavailable(self,ax):
        self.results_axes=ax;self.current_frame=None;self.toolbar.ready()
    def update_preview(self,ax,d,fig,sx,sz,idx):
        self.results_axes=ax;self.data=d;self.fig=fig;self.sx=sx;self.sz=sz;self.idx=idx
        case=str(getattr(self.owner,'source',''))
        key=(float(d['geo_x']),float(d['geo_z']),tuple(sx),tuple(sz),tuple(tuple(row[:4]) for row in fig.rows) if fig else (),bool(fig.mirror) if fig else False)
        if key!=self._geometry_key or case!=self._case_key:
            self.toolbar._views.clear();self.toolbar._history=[];self.toolbar._history_index=-1;self._geometry_key=key;self._case_key=case
        self.current_frame=pd.DataFrame();self.toolbar.ready()
    def preview_surface_height(self):
        if len(self.sx)<2:return 0.
        regions=[]
        if self.fig:
            for row in self.fig.rows:
                x1,x2,z1,z2=row[:4];regions.append((x1,x2,z2))
                if self.fig.mirror:regions.append((-x2,-x1,z2))
        lo,hi=-self.data['geo_x'],self.data['geo_x']
        edges=np.unique(np.r_[self.sx,[max(lo,min(hi,x)) for a,b,z in regions for x in (a,b)]])
        mid=(edges[:-1]+edges[1:])*.5;heights=np.interp(mid,self.sx,self.sz)
        for a,b,z in regions:heights=np.where((mid>=a)&(mid<=b),np.maximum(heights,z),heights)
        dx=np.diff(edges);return float(np.sum(heights*dx)/np.sum(dx))*self.unit.currentData() if np.sum(dx)>0 else 0.
    def preview_data_tip(self,x,z):
        f=self.unit.currentData();x=x/f;z=z/f;d=self.data;idx=self.idx;q=None
        if self.fig:
            for i,row in reversed(list(enumerate(self.fig.rows))):
                a,b,c,e=row[:4]
                if c<=z<=e and (a<=x<=b or self.fig.mirror and -b<=x<=-a):
                    q=row[4+idx] if self.fig.with_qu else d['qu_tar'][idx];label=self.tr('初始凸起块','Initial block')+f' {i+1}';break
        if q is None and -d['geo_x']<=x<=d['geo_x'] and d['geo_z']<=z<=np.interp(x,self.sx,self.sz):
            q=d['qu_tar'][idx];label=self.tr('初始基底示意','Initial substrate schematic')
            for flag,name,value in [('iq0','initial_composition.inp',z),('iq0_surf','initial_composition_surf.inp',z-np.interp(x,self.sx,self.sz))]:
                if d.get(flag,0)>0:
                    for upper,lower,values in parse_layers(d['_files'][name],len(d['symbol'])):
                        if lower<=value<upper:q=values[idx]
        if q is None:return self.tr('空白区域','Empty region')
        return label+'\n'+d['symbol'][idx]+self.tr(' 原子分数 = ',' atomic fraction = ')+f'{q:.6g}'
    def export_png(self):
        path,_=QFileDialog.getSaveFileName(self,self.tr('保存初始靶预览','Save initial target preview'),'initial_target.png','PNG (*.png)')
        if path:
            try:self.owner.plot.savefig(Path(path),dpi=200)
            except OSError as error:QMessageBox.warning(self,self.tr('保存失败','Save failed'),str(error))
