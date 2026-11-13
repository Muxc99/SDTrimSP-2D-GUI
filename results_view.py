"""桌面结果页：复用原 Plotter 的二维解析和精确网格规则。"""
from pathlib import Path
import numpy as np
import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QFileDialog,QMessageBox,QListWidget,QListWidgetItem,QAbstractItemView,QCheckBox,
    QSplitter,QFormLayout)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg,NavigationToolbar2QT
from matplotlib.figure import Figure
from element_picker import NoWheelComboBox
from layout_defaults import DefaultSplitter
from results_data import load_dataset,cell_grid,cell_snapshot_warning
from extended_results import ExtendedResults,EXTRA_KINDS,EXTRA_KEYS,EN,REQUIRES
from results_analysis import OPTIONAL_NAMES,extend_dataset
from element_colors import element_colormap
from results_maps import ResultMaps
from surface_paths import surface_path

KINDS=[('fraction','元素原子分数'),('density','元素数密度'),('total_density','总原子数密度'),
       ('surface','表面轮廓对比'),('local','局部反射与溅射贡献'),('totals','反射系数与溅射产额随注量')]

KINDS+=EXTRA_KINDS

class ResultsView(ResultMaps,ExtendedResults,QWidget):
    def __init__(self,owner):
        super().__init__(owner)
        self.owner=owner; self.dataset=None; self.current_frame=None; self.csv_name='results.csv'
        self.loading=False
        self.build_results_ui(KINDS)

    def open_directory(self):
        directory=QFileDialog.getExistingDirectory(self,'选择结果目录',str(self.owner.run_directory or self.owner.source))
        if directory:self.load_directory(Path(directory))

    def open_files(self):
        files,_=QFileDialog.getOpenFileNames(self,'选择同一算例的二维输出文件',str(self.owner.run_directory or self.owner.source),'SDTrimSP output (*.dat);;All files (*)')
        if files:self.load_paths([Path(p) for p in files])

    def load_current_run(self):
        if self.owner.process:
            QMessageBox.information(self,'计算仍在运行','请等待计算结束后载入完整输出。'); return
        if not self.owner.run_directory:
            QMessageBox.information(self,'尚无本次运行','请先运行案例，或使用“打开结果目录”。'); return
        self.load_directory(self.owner.run_directory)

    def load_directory(self,path):
        folder=Path(path)
        paths=[folder/name for name in ('T_10_2D.dat','surf.dat','sputter_yield.dat',*OPTIONAL_NAMES) if (folder/name).is_file()]
        paths+=sorted(folder.glob('partic_*.dat'))+sorted(folder.glob('trajec_*.dat'))
        return self.load_paths(paths)

    def load_paths(self,paths):
        try:
            paths=[Path(p) for p in paths]
            if not paths:raise ValueError(self.tr('所选目录中没有受支持的输出文件。','No supported output files in this folder.'))
            if len({p.resolve().parent for p in paths})!=1:raise ValueError(self.tr('请选择同一个目录内、同一算例的文件。','Select files from the same case directory.'))
            skipped=[p.name for p in paths if p.stat().st_size>64*1024*1024]
            contents={p.name:p.read_text(encoding='utf-8-sig',errors='replace') for p in paths if p.name not in skipped}
            core=any('#cel_coord' in t or '#surface coordinates: x z cell-Nr' in t or ('local R' in t and 'local Y' in t) for t in contents.values())
            # Broken block structure remains fatal; invalid geometry isolates whole snapshots.
            for name in ('T_10_2D.dat','surf.dat','sputter_yield.dat'):
                if name in contents and not any(marker in contents[name] for marker in ('#cel_coord','#surface coordinates: x z cell-Nr','local R')):
                    raise ValueError(name+': '+self.tr('缺少有效文件头。','Missing valid header.'))
            dataset=load_dataset(contents) if core else {'symbols':[],'files':{},'ignored':[]}
            dataset=extend_dataset(dataset,contents)
            warning=cell_snapshot_warning(dataset,getattr(self.owner,'ui_language','zh')=='en')
            if warning:dataset['warnings'].append(warning)
            if skipped:dataset['warnings'].append(self.tr('超过 64 MiB 的文件未读取：','Files over 64 MiB were not loaded: ')+', '.join(skipped))
            if not dataset['files']:raise ValueError(self.tr('未读取到可用的结果。','No usable results loaded.')+'\n'+'\n'.join(dataset['warnings']))
        except (ValueError,OSError) as error:
            QMessageBox.warning(self,self.tr('结果读取失败','Cannot load results'),str(error));return False
        self.timer.stop();self.dataset=dataset;self.loading=True
        folder=str(paths[0].resolve().parent);self.result_directory=folder;self.source_label.setText(folder+'  ·  '+str(len(dataset['files']))+self.tr(' 个有效输出',' valid outputs'));self.source_label.setToolTip(folder+'\n'+', '.join(dataset['files'].values()))
        self.species.clear();self.species.addItems(dataset['symbols'])
        self.files_list.clear()
        for key,name in dataset['files'].items():self.files_list.addItem('✓ '+name)
        for warning in dataset['warnings']:self.files_list.addItem('⚠ '+warning)
        for name in dataset['ignored']:self.files_list.addItem('— '+name)
        self.files_note.setText(self.tr('可用图像按文件自动启用。','Available plots follow the loaded files.')+('\n'+'\n'.join(dataset['warnings']) if dataset['warnings'] else ''))
        if dataset.get('cells'):
            df=dataset['cells'][0]['data'];f=self.unit.currentData()
            for widget,value in ((self.x_min,df.x1_A.min()*f),(self.x_max,df.x2_A.max()*f),(self.x_position,(df.x1_A.min()+df.x2_A.max())*.5*f),(self.z_position,(df.z1_A.min()+df.z2_A.max())*.5*f)):
                widget.setValue(value)
        chosen=None
        for i,(kind,_) in enumerate(KINDS):
            enabled=self.available(kind);item=self.kind.model().item(i);item.setEnabled(enabled)
            item.setToolTip(self.tr('数据已载入','Data loaded') if enabled else self.tr('需要：','Requires: ')+REQUIRES.get(self.key_for(kind),''))
            if enabled and chosen is None:chosen=i
        if chosen is None:
            self.loading=False;self.configure();return True
        self.category.setCurrentIndex(0);self.kind.setCurrentIndex(chosen);self.filter_plot_category();self.loading=False;self.configure();return True

    def snapshot_label(self,snap):
        if not np.isfinite(snap['fluence']):return str(snap['history'])+' · '+self.tr('注量未记录','Fluence not recorded')
        return f'{snap["history"]} · Φ={snap["fluence"]*self.fluence_unit.currentData():g} {self.fluence_unit.currentText()}'

    def configure(self,*args):
        self.configure_extended()

    def redraw(self,*args):
        if self.loading:return
        self.toolbar.capture_view()
        factor=self.unit.currentData()
        if factor!=self._space_factor:
            for spin in (self.x_position,self.z_position,self.x_min,self.x_max,self.reference_z):
                was=spin.blockSignals(True);spin.setValue(spin.value()*factor/self._space_factor);spin.blockSignals(was)
            self._space_factor=factor
        for i,(kind,zh) in enumerate(KINDS):
            if kind in EN:
                was=self.kind.blockSignals(True);self.kind.setItemText(i,self.tr(zh,EN[kind]));self.kind.blockSignals(was)
        key=self.key_for()
        for i,snap in enumerate((self.dataset or {}).get(key,[]) if key in ('cells','surface','yield','transport','transport_static','redeposit','hits','active') else []):
            if i<self.step.count():
                was=self.step.blockSignals(True);self.step.setItemText(i,self.snapshot_label(snap));self.step.blockSignals(was)
        if self.kind.currentData() in EXTRA_KEYS:return self.redraw_extended()
        if self.kind.currentData() in ('fraction','density','total_density') and (self.dataset or {}).get('cells'):
            try:return self.redraw_map()
            except (ValueError,KeyError,IndexError):
                # Keep the existing visible error handling for unsupported/invalid input.
                pass
        self.figure.clear();self.current_frame=None;self.csv_button.setEnabled(False);self.png_button.setEnabled(False)
        ax=self.create_results_axes()
        data=self.dataset or {};kind=self.kind.currentData()
        factor=self.unit.currentData();unit=self.unit.currentText()
        ff=self.fluence_unit.currentData();fu=self.fluence_unit.currentText()
        key='cells' if kind in ('fraction','density','total_density') else 'yield' if kind in ('local','totals') else 'surface'
        self.step.blockSignals(True)
        for i,snap in enumerate(data.get(key,[])):
            if i<self.step.count():self.step.setItemText(i,self.snapshot_label(snap))
        self.step.blockSignals(False)
        for i,snap in enumerate(data.get('surface',[])):
            if i<self.surface_steps.count():self.surface_steps.item(i).setText(self.snapshot_label(snap))
        is_english=getattr(self.owner,'ui_language','zh')=='en'
        def label(zh,en):return en if is_english else zh
        try:
            if not data:raise ValueError(label('载入二维输出后显示绘图。','Load 2D output files to display results.'))
            if kind in ('fraction','density','total_density'):
                snapshots=data.get('cells',[])
                if not snapshots:raise ValueError('T_10_2D.dat required')
                snap=snapshots[max(0,self.step.currentIndex())];df=snap['data'];symbol=self.species.currentText()
                if kind=='fraction':values=df['fraction_'+symbol].to_numpy();title=symbol+' '+label('原子分数','atomic fraction')
                elif kind=='density':values=(df['fraction_'+symbol]*df.density_at_A3*1e24).to_numpy();title=symbol+' (atoms/cm³)'
                else:values=(df.density_at_A3*1e24).to_numpy();title=label('总原子数密度','Total atomic density')+' (atoms/cm³)'
                self.current_frame=df.assign(fluence_ions_A2=snap['fluence'],history=snap['history'],display_value=values)
                self.csv_name=f'2d_{kind}_step_{snap["history"]}.csv'
                x,z,grid=cell_grid(snap,values)
                limits={'vmin':0,'vmax':1} if kind=='fraction' else {}
                if kind!='fraction' and self.fixed_scale.isChecked():
                    vmax=max(float((s['data']['fraction_'+symbol]*s['data'].density_at_A3*1e24).max()) if kind=='density' else float((s['data'].density_at_A3*1e24).max()) for s in snapshots)
                    limits={'vmin':0,'vmax':max(vmax,1e-30)}
                im=ax.pcolormesh(x*factor,z*factor,grid,shading='flat',cmap=element_colormap(symbol) if kind in ('fraction','density') else 'viridis',**limits)
                self.create_results_colorbar(im,title)
                if self.overlay.isChecked():
                    for surf in data.get('surface',[]):
                        if surf['history']==snap['history'] and np.isclose(surf['fluence'],snap['fluence'],atol=5e-6):
                            ax.plot(surf['data'].x_A*factor,surf['data'].z_A*factor,color='#df593f',lw=1);break
                sums=df[[f'fraction_{s}' for s in data['symbols']]].sum(axis=1)
                warning=label('部分材料单元原子分数之和偏离 1，显示原值。','Some material cells have fractions that do not sum to 1; original values retained.') if ((sums[df.density_at_A3>0]-1).abs()>1e-4).any() else ''
                self.note.setText(label('空白为无材料或无数据区域；不平滑，不自动归一化。','Blank areas have no material/data. No smoothing or renormalization.')+'\n'+warning)
                ax.set_title(title+'\n'+self.snapshot_label(snap))
            elif kind=='surface':
                frames=[];broken=[]
                for item in self.surface_steps.selectedItems():
                    snap=data['surface'][item.data(Qt.ItemDataRole.UserRole)];df=snap['data']
                    path,audit=surface_path(df)
                    ax.plot(path[:,0]*factor,path[:,1]*factor,label=self.snapshot_label(snap))
                    count=int((audit.break_reason!='').sum())
                    if count:broken.append(str(snap['history'])+': '+str(count))
                    frames.append(audit.assign(fluence_ions_A2=snap['fluence'],history=snap['history']))
                if not frames:raise ValueError(label('请载入 surf.dat 并选择历史步。','Load surf.dat and select snapshots.'))
                self.current_frame=pd.concat(frames,ignore_index=True);self.csv_name='2d_surface_comparison.csv'
                ax.legend(fontsize=8);ax.set_title(label('表面轮廓对比','Surface profile comparison'))
                notes=[label('保持原始边界遍历顺序和垂直面，不跨接边界跳转；原始点全部保留。','Original traversal and vertical faces are preserved. Boundary jumps are not connected; all raw points are retained.')]
                if broken:notes.append(label('已断开跨边界或非矩形边连接（历史步: 处数）：','Disconnected boundary/nonrectangular jumps (history: count): ')+', '.join(broken))
                selected={int(frame.history.iloc[0]) for frame in frames if len(frame)}
                bad=[str(s['history']) for s in data.get('invalid_cell_snapshots',[]) if s['history'] in selected]
                if bad:notes.append(label('注意：历史步 ','Warning: histories ')+', '.join(bad)+label(' 的二维单元输出含无效边界；轮廓仅显示原始记录，不能据此确认靶几何有效。',' have invalid cell boundaries. Displaying raw surface records does not establish valid target geometry.'))
                self.note.setText('\n'.join(notes))
            else:
                snapshots=data.get('yield',[])
                if not snapshots:raise ValueError('sputter_yield.dat required')
                if kind=='local':
                    snap=snapshots[max(0,self.step.currentIndex())];df=snap['data']
                    self.current_frame=df.assign(fluence_ions_A2=snap['fluence'],history=snap['history'])
                    self.csv_name=f'2d_local_RY_step_{snap["history"]}.csv'
                    x=df.x_A*factor;ax.set_title(self.snapshot_label(snap))
                else:
                    rows=[]
                    for snap in snapshots:
                        summary=snap.get('summary',snap['data'].iloc[:,1:].sum().to_dict())
                        rows.append(dict(fluence_ions_A2=snap['fluence'],history=snap['history'],**summary,
                            R_total=sum(v for k,v in summary.items() if k.startswith('R_')),
                            Y_total=sum(v for k,v in summary.items() if k.startswith('Y_'))))
                    df=pd.DataFrame(rows);self.current_frame=df;self.csv_name='2d_total_RY_vs_fluence.csv'
                    x=df.fluence_ions_A2*ff;ax.set_title(label('反射系数与溅射产额随注量','Reflection coefficient and sputtering yield vs fluence'))
                selected=self.curves.selectedItems()
                for item in selected:
                    col=item.data(Qt.ItemDataRole.UserRole) or item.text()
                    ax.plot(x,df[col],label=self.curve_label(col),marker='.' if kind=='totals' else None)
                if selected:ax.legend(fontsize=8)
                ax.set_ylabel(label('每个入射粒子的贡献 / 总量','Contribution / total per incident particle'))
                self.note.setText(label('局部反射与溅射贡献以全局入射数为分母；全靶反射系数与溅射产额对各列贡献求和，不求平均。','Local reflection and sputtering contributions use the global incident count. Whole-target coefficients and yields sum column contributions, without averaging.')+('' if data['symbols'] else '\n'+label('未载入组分表，曲线使用组分编号。','No component names loaded; numeric component labels are used.')))
            if kind=='totals':ax.set_xlabel(label('注量','Fluence')+' ('+fu+')')
            else:ax.set_xlabel('x ('+unit+')')
            if kind in ('fraction','density','total_density','surface'):ax.set_ylabel('z ('+unit+')')
            self.png_button.setEnabled(True)
        except (ValueError,KeyError,IndexError) as error:
            self.figure.clear();ax=self.create_results_axes();ax.text(.5,.5,str(error),ha='center',va='center',wrap=True,transform=ax.transAxes);ax.set_axis_off()
            self.note.setText(str(error))
        self.csv_button.setEnabled(self.current_frame is not None)
        self.canvas.draw_idle();self.finish_results_draw()

    def export_csv(self):
        if self.current_frame is None:return
        path,_=QFileDialog.getSaveFileName(self,'导出当前数据 CSV',self.csv_name,'CSV (*.csv)')
        if path:
            try:self.current_frame.to_csv(path,index=False,encoding='utf-8-sig')
            except OSError as error:QMessageBox.warning(self,'导出失败',str(error))

    def export_png(self):
        path,_=QFileDialog.getSaveFileName(self,'保存图片 PNG',Path(self.csv_name).stem+'.png','PNG (*.png)')
        if path:
            try:self.figure.savefig(path,dpi=240)
            except OSError as error:QMessageBox.warning(self,'导出失败',str(error))
