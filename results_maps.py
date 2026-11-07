"""Exact output rectangles, bounded geometry cache and reusable map artists."""
from collections import OrderedDict
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.colors import Normalize
from element_colors import element_colormap


def checked_rectangles(snap,max_bins=1500000):
    """Same exact-edge size/overlap checks as cell_grid, without filling each cell."""
    df=snap['data']
    if df.empty:raise ValueError('该历史步没有单元。')
    x=np.unique(df[['x1_A','x2_A']].to_numpy());z=np.unique(df[['z1_A','z2_A']].to_numpy())
    if (len(x)-1)*(len(z)-1)>max_bins:
        raise ValueError('精确边界组合过大，当前界面不进行重采样。请先导出 CSV，或使用更小的几何算例。')
    material=df.density_at_A3.to_numpy()>0
    bounds=df.loc[material,['x1_A','x2_A','z1_A','z2_A']].to_numpy()
    a,b=np.searchsorted(x,bounds[:,:2]).T;c,d=np.searchsorted(z,bounds[:,2:]).T
    # Rectangle difference array: positive area covered twice means true overlap.
    coverage=np.zeros((len(z),len(x)),dtype=np.int32)
    for rows,cols,value in ((c,a,1),(c,b,-1),(d,a,-1),(d,b,1)):np.add.at(coverage,(rows,cols),value)
    np.cumsum(coverage,axis=0,dtype=np.int32,out=coverage)
    np.cumsum(coverage,axis=1,dtype=np.int32,out=coverage)
    if np.any(coverage>1):raise ValueError('检测到相互重叠的二维单元，请检查输出。')
    return material,bounds[:,[0,2,1,2,1,3,0,3]].reshape(-1,4,2)


class ResultMaps:
    def map_geometry(self,snap):
        cache=getattr(self,'_map_geometry_cache',None)
        if cache is None or getattr(self,'_map_dataset',None) is not self.dataset:
            self._map_dataset=self.dataset;self._map_geometry_cache=cache=OrderedDict();self._map_maxima={}
        key=id(snap)
        if key in cache:
            cache.move_to_end(key);return cache[key]
        material,vertices=checked_rectangles(snap)
        cache[key]=(material,vertices)
        while len(cache)>1 and sum(v.nbytes+m.nbytes for m,v in cache.values())>32*1024*1024:cache.popitem(last=False)
        return material,vertices

    def redraw_map(self):
        data=self.dataset;kind=self.kind.currentData();snap=data['cells'][max(0,self.step.currentIndex())]
        df=snap['data'];symbol=self.species.currentText();f=self.unit.currentData()
        english=getattr(self.owner,'ui_language','zh')=='en'
        label=lambda zh,en:en if english else zh
        material,vertices=self.map_geometry(snap)
        if kind=='fraction':values=df['fraction_'+symbol].to_numpy();title=symbol+' '+label('原子分数','atomic fraction')
        elif kind=='density':values=(df['fraction_'+symbol]*df.density_at_A3*1e24).to_numpy();title=symbol+' (atoms/cm³)'
        else:values=df.density_at_A3.to_numpy()*1e24;title=label('总原子数密度','Total atomic density')+' (atoms/cm³)'
        if kind=='fraction':low,high=0.,1.
        elif self.fixed_scale.isChecked():
            key=(kind,symbol if kind=='density' else '')
            if key not in self._map_maxima:
                self._map_maxima[key]=max(float((s['data']['fraction_'+symbol]*s['data'].density_at_A3*1e24).max()) if kind=='density' else float(s['data'].density_at_A3.max()*1e24) for s in data['cells'])
            low,high=0.,max(self._map_maxima[key],1e-30)
        else:
            actual=values[material];low=float(actual.min()) if len(actual) else 0.;high=float(actual.max()) if len(actual) else 1.
        from gradient_editor import gradient_colormap
        stops=self.gradient_stops.get(self.gradient_key())
        cmap=gradient_colormap(stops) if stops else element_colormap(symbol) if kind in ('fraction','density') else 'viridis'
        state=getattr(self,'_map_artists',None)
        reuse=state is not None and state['ax'] in self.figure.axes and state['dataset'] is data
        if reuse:
            ax=state['ax'];im=state['im'];cb=state['cb']
            if self.toolbar._tip is not None:
                self.toolbar._tip.remove();self.toolbar._tip=None
            if state['geometry']!=(id(snap),f):im.set_verts(vertices*f)
            im.set_array(values[material]);im.set_cmap(cmap)
            if im.norm.vmin!=low or im.norm.vmax!=high:im.set_norm(Normalize(low,high))
        else:
            self.figure.clear();ax=self.create_results_axes()
            im=PolyCollection(vertices*f,array=values[material],cmap=cmap,norm=Normalize(low,high),edgecolors='none',antialiaseds=False)
            ax.add_collection(im);cb=self.create_results_colorbar(im,title)
            line,=ax.plot([],[],color='#df593f',lw=1)
            state={'ax':ax,'im':im,'cb':cb,'line':line,'dataset':data};self._map_artists=state
        state['geometry']=(id(snap),f)
        ax.dataLim.set_points(np.array([[df.x1_A.min(),df.z1_A.min()],[df.x2_A.max(),df.z2_A.max()]])*f)
        cb.set_label(title);line=state['line'];line.set_data([],[])
        if self.overlay.isChecked():
            for surf in data.get('surface',[]):
                if surf['history']==snap['history'] and np.isclose(surf['fluence'],snap['fluence'],atol=5e-6):
                    line.set_data(surf['data'].x_A.to_numpy()*f,surf['data'].z_A.to_numpy()*f);break
            if len(line.get_xdata()):ax.update_datalim(np.column_stack(line.get_data()))
        self.results_axes=ax
        self.current_frame=df.assign(fluence_ions_A2=snap['fluence'],history=snap['history'],display_value=values)
        self.csv_name=f'2d_{kind}_step_{snap["history"]}.csv'
        sums=df[[f'fraction_{s}' for s in data['symbols']]].sum(axis=1)
        warning=label('部分材料单元原子分数之和偏离 1，显示原值。','Some material cells have fractions that do not sum to 1; original values retained.') if ((sums[df.density_at_A3>0]-1).abs()>1e-4).any() else ''
        self.note.setText(label('空白为无材料或无数据区域；不平滑，不自动归一化。','Blank areas have no material/data. No smoothing or renormalization.')+'\n'+warning)
        ax.set_title(title+'\n'+self.snapshot_label(snap));ax.set_xlabel('x ('+self.unit.currentText()+')');ax.set_ylabel('z ('+self.unit.currentText()+')')
        self.csv_button.setEnabled(True);self.png_button.setEnabled(True)
        self.finish_results_draw();self.canvas.draw_idle()
