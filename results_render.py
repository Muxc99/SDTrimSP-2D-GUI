"""Render verified output fields without changing source data."""
import io
import numpy as np
import pandas as pd
from PySide6.QtWidgets import QFileDialog,QMessageBox,QProgressDialog,QApplication
from PySide6.QtCore import Qt
from results_analysis import projected_inventory,morphology

class ResultsRender:
    def cached_analysis(self,kind,compute,*parameters):
        if getattr(self,'_analysis_dataset',None) is not self.dataset:
            self._analysis_dataset=self.dataset;self._analysis_cache={}
        key=(kind,*parameters)
        if key not in self._analysis_cache:
            if len(self._analysis_cache)>=8:self._analysis_cache.clear()
            self._analysis_cache[key]=compute()
        return self._analysis_cache[key]

    def redraw_extended(self):
        self.figure.clear();ax=self.create_results_axes();self.current_frame=None
        self.csv_button.setEnabled(False);self.png_button.setEnabled(False)
        data=self.dataset or {};kind=self.kind.currentData();key=self.key_for();f=self.unit.currentData();u=self.unit.currentText();ff=self.fluence_unit.currentData();fu=self.fluence_unit.currentText();symbol=self.species.currentText()
        title=self.kind.currentText();note='';frames=[]
        def selected(df):return [i.data(Qt.ItemDataRole.UserRole) or i.text() for i in self.curves.selectedItems() if (i.data(Qt.ItemDataRole.UserRole) or i.text()) in df.columns]
        def segments(df,a,b,y,vertical=False):
            # Independent intervals preserve gaps; do not invent interpolation.
            xx=np.column_stack([df[a].to_numpy(),df[b].to_numpy(),np.full(len(df),np.nan)]).ravel()*f
            yy=np.column_stack([np.asarray(y),np.asarray(y),np.full(len(df),np.nan)]).ravel()
            if vertical:ax.plot(yy,xx)
            else:ax.plot(xx,yy)
        def group(col):
            if col.endswith('_A2'):return 'area'
            if col.endswith('_A'):return 'length'
            if col.startswith('stopped_inventory_'):return 'inventory'
            if col.startswith('composition_at_max_height_'):return 'fraction'
            if any(col.startswith(p+'_') for p in ('back_energy','trans_energy','sputter_energy','trans_recoil_energy','input_energy')):return 'energy'
            if col=='volume_statistic':return 'volume'
            return 'count'
        def compatible(cols):
            if not cols:raise ValueError(self.tr('请至少选择一条曲线。','Select at least one curve.'))
            groups={group(c) for c in cols}
            if len(groups)>1:raise ValueError(self.tr('所选统计项的单位不同，请分别选择同一单位的曲线绘制。','Selected quantities have different units. Select curves with matching units.'))
            return next(iter(groups))
        try:
            if not self.available(kind):raise ValueError(self.tr('此图需要输出文件：','Required output: ')+__import__('extended_results').REQUIRES.get(key,key))
            if key in ('cells','transport','transport_static','redeposit','hits','active'):
                snaps=data[key];snap=snaps[max(0,self.step.currentIndex())]
            if kind in ('inventory','morphology','statistics'):
                if kind=='inventory':df=self.cached_analysis(kind,lambda:projected_inventory(data['cells'],data['symbols']))
                elif kind=='morphology':
                    parameters=(self.reference_z.value()/f,self.x_min.value()/f,self.x_max.value()/f)
                    df=self.cached_analysis(kind,lambda:morphology(data['cells'],*parameters),*parameters)
                else:df=data[key].copy()
                cols=selected(df)
                typ='inventory' if kind=='inventory' else compatible(cols)
                if not cols:raise ValueError(self.tr('请选择曲线。','Select curves.'))
                scale={'inventory':1e16,'length':f,'area':f*f}.get(typ,1.)
                units={'inventory':'atoms/cm²','length':u,'area':u+'²','fraction':self.tr('原子分数','Atomic fraction'),'energy':'eV','count':self.tr('累计抽样计数','Cumulative sampled count')}
                for col in cols:ax.plot(df.fluence_ions_A2*ff,df[col]*scale,label=self.curve_label(col),marker='.')
                ax.set_xlabel(self.tr('注量','Fluence')+' ('+fu+')');ax.set_ylabel(units.get(typ,typ));ax.legend(fontsize=8)
                if kind=='inventory':note=self.tr('由二维单元积分，除以完整靶投影宽度；包含初始基底原子，不等于仅保留的入射原子。','Integrated over cells and divided by full target projected width. Includes initial substrate atoms, not just retained incident particles.')
                elif kind=='morphology':note=self.tr('宽度为参考高度以上各段投影宽度之和，不是单个凸起直径；参考高度附近的微小形变也会计入。截面积为二维量。','Width sums projected intervals above the reference, not a single protrusion diameter. Small shifts near the reference count. Areas are 2D cross-sections.')
                else:note=self.tr('保留程序原始统计。最高点成分不是平均表面成分；stopped_inventory 使用程序自身归一化，不与单元积分库存量混为一谈。','Original program statistics. Composition at maximum height is not mean surface composition. stopped_inventory uses the program normalization and is distinct from cell-integrated inventory.')
            elif kind in ('redeposit','transport','transport_static','hits','active'):
                df=snap['data'].copy();cols=selected(df);typ=compatible(cols)
                xcol='cell_id' if kind in ('active','transport_static') else 'x_A';scale=1 if xcol=='cell_id' else f
                for col in cols:ax.plot(df[xcol]*scale,df[col],label=self.curve_label(col),marker='.' if xcol=='cell_id' else None)
                ax.legend(fontsize=8);ax.set_xlabel(self.tr('单元编号','Cell ID') if xcol=='cell_id' else 'x ('+u+')');ax.set_ylabel(self.tr('程序原始统计值','Original output statistic'));title+='\n'+self.snapshot_label(snap)
                df=df.assign(history=snap['history'],fluence_ions_A2=snap['fluence'])
                note=self.tr('保留程序原始计数/收支，未除以局部入射数；不能直接解读为局部概率。活跃单元按编号显示，不与其他历史步的几何强行匹配。','Raw program counts/balances; not divided by local incident counts and not local probabilities. Active cells use IDs, without matching geometry from another history.')
            elif kind=='energy':
                df=data['energy'];df=df[df.group==self.detail_source.currentData()].copy();ax.barh(df.term,df.energy_keV,color=['#c46953' if v<0 else '#4289a5' for v in df.energy_keV]);ax.axvline(0,color='#65788a',lw=.7);ax.set_xlabel('keV');note=self.tr('保留正负号；各项中含总量与分项，不应再次相加。投射粒子和反冲原子分组显示。','Signs are preserved. Totals and components must not be summed again. Projectile and recoil budgets are separate groups.')
            elif key=='particles':
                name=self.detail_source.currentData();raw=data['particles'][name];sid=self.particle_species.currentData();raw=raw[raw.species_id==sid] if sid is not None and sid>=0 else raw
                if raw.empty:raise ValueError(self.tr('当前文件 / 组分没有粒子记录。','No particle records for this file / species.'))
                stopped='stop' in name.lower()
                if kind=='particle_positions':
                    df=raw.copy();ax.scatter(df.x_end_A*f,df.z_end_A*f,s=6,alpha=.5);ax.set_xlabel('x ('+u+')');ax.set_ylabel('z ('+u+')')
                else:
                    if kind=='particle_energy':vals=raw.energy_eV.to_numpy();xlabel='Energy (eV)';quantity='energy_eV';scale=1
                    elif kind=='particle_angle':
                        if stopped:raise ValueError(self.tr('停止粒子的角度字段可能是占位值，请选择出射粒子文件。','Stopped-particle angles may be placeholders. Select an escaping-particle file.'))
                        if ((raw.cos_polar.abs()>1+1e-6)).any():raise ValueError('Invalid cos_polar values')
                        vals=np.degrees(np.arccos(np.clip(raw.cos_polar,-1,1)));xlabel=self.tr('出射极角 / °（程序全局参考）','Exit polar angle / degrees (program global reference)');quantity='polar_angle_deg';scale=1
                    else:
                        if not stopped:raise ValueError(self.tr('停止位移与路径请使用 partic_*_stop.dat；最大深度字段不作为二维射程。','Use partic_*_stop.dat for stopping displacement/path. Maximum-depth fields are not used as 2D range.'))
                        # Two separate histograms; signed displacement is distinct from path length.
                        frames=[]
                        for q,values in [('z_displacement_A',(raw.z_end_A-raw.z_start_A).to_numpy()),('path_A',raw.path_A.to_numpy())]:
                            counts,edges=np.histogram(values,bins=self.hist_bins.value());ax.stairs(counts,edges*f,label=q);frames.append(pd.DataFrame({'quantity':q,'bin_left_A':edges[:-1],'bin_right_A':edges[1:],'count':counts}))
                        df=pd.concat(frames,ignore_index=True);ax.legend(fontsize=8);ax.set_xlabel(self.tr('停止位移 / 路径','Stopping displacement / path')+' ('+u+')');ax.set_ylabel(self.tr('记录粒子数','Recorded particles'))
                    if kind!='particle_range':
                        counts,edges=np.histogram(vals,bins=self.hist_bins.value());ax.stairs(counts,edges*scale,fill=True,alpha=.65);df=pd.DataFrame({'quantity':quantity,'bin_left':edges[:-1],'bin_right':edges[1:],'count':counts});ax.set_xlabel(xlabel);ax.set_ylabel(self.tr('记录粒子数','Recorded particles'))
                note=self.tr('仅统计文件中实际记录的抽样粒子；直方图不是产额。角度使用程序全局出射参考，不是局部表面法线。位移保留正负号。','Uses recorded sampled particles only; histograms are not yields. Angles use the program global exit reference, not local surface normals. Displacements retain their signs.')+' · '+name
            elif kind=='trajectory':
                records=data['trajectories'][self.detail_source.currentData()];sid=self.particle_species.currentData();records=[r for r in records if sid is None or sid<0 or r['species_id']==sid];shown=records[:self.trajectory_limit.value()];frames=[]
                for r in shown:
                    p=r['data'];ax.plot(p.x_A*f,p.z_A*f,lw=.8,alpha=.7);frames.append(p.assign(trajectory=r['trajectory'],history=r['history'],species_id=r['species_id']))
                if not frames:raise ValueError('No trajectory records')
                df=pd.concat(frames,ignore_index=True);ax.set_xlabel('x ('+u+')');ax.set_ylabel('z ('+u+')');note=self.tr('每条轨迹独立绘制；显示','Each trajectory is independent. Showing ')+f'{len(shown)} / {len(records)}'+self.tr(' 条。CSV 导出当前显示的轨迹。',' trajectories. CSV exports the displayed trajectories.')
            elif kind=='timing':
                df=data['timing'].copy();ax.barh(df.stage,df.seconds,color='#4289a5');ax.set_xlabel(self.tr('秒','Seconds'));note=self.tr('阶段可能包含嵌套总耗时，不能简单累加为总运行时间。','Stages can include nested totals and must not simply be summed for total runtime.')
            else:raise ValueError('Unsupported plot')
            if df.empty:raise ValueError(self.tr('没有可绘制的数据。','No plottable data.'))
            
            for axis in (ax.xaxis,ax.yaxis):
                formatter=axis.get_major_formatter()
                if hasattr(formatter,'set_useOffset'):formatter.set_useOffset(False)
            self.current_frame=df;self.csv_name='2d_'+kind+'.csv';ax.set_title(title,fontsize=11);ax.grid(True,alpha=.15);self.note.setText(note);self.png_button.setEnabled(True);self.csv_button.setEnabled(True)
        except (ValueError,KeyError,IndexError,TypeError) as error:
            self.current_frame=None;self.figure.clear();ax=self.create_results_axes();ax.text(.5,.5,str(error),ha='center',va='center',wrap=True,transform=ax.transAxes);ax.set_axis_off();self.note.setText(str(error))
        self.canvas.draw_idle();self.finish_results_draw()

    def export_gif(self):
        if self.step.count()<2:return
        path,_=QFileDialog.getSaveFileName(self,self.tr('导出动画 GIF','Export animation GIF'),'2d_'+self.kind.currentData()+'.gif','GIF (*.gif)')
        if path:self.save_animation(path)

    def save_animation(self,path):
        from PIL import Image
        import tempfile
        import os
        self.timer.stop();initial=self.step.currentIndex();n=self.step.count();images=[];tempname=None
        # Explicit guard prevents accidental multi-gigabyte allocations.
        width,height=self.canvas.get_width_height()
        if n*min(width,1100)*min(height,800)>100_000_000:
            QMessageBox.warning(self,self.tr('动画过大','Animation too large'),self.tr('历史步或画布过大，请缩小窗口或改用逐步播放。未自动跳帧。','Too many frames or canvas too large. Resize the window or use playback. No frames were silently skipped.'));return False
        progress=QProgressDialog(self.tr('正在生成动画…','Rendering animation…'),self.tr('取消','Cancel'),0,n,self);progress.setWindowModality(Qt.WindowModality.WindowModal);progress.setMinimumDuration(0)
        # Freeze controls while events are processed; cancellation stays available.
        widgets=[self.control_tabs,self.playback,self.csv_button,self.png_button]
        if hasattr(self,'gif_button'):widgets.append(self.gif_button)
        states=[w.isEnabled() for w in widgets]
        for w in widgets:w.setEnabled(False)
        try:
            for i in range(n):
                progress.setValue(i);QApplication.processEvents()
                if progress.wasCanceled():return False
                if self.step.currentIndex()==i:self.redraw()
                else:self.step.setCurrentIndex(i)
                self.canvas.draw()
                if self.current_frame is None:raise ValueError(self.note.text())
                buf=io.BytesIO();self.figure.savefig(buf,format='png',dpi=90);buf.seek(0);im=Image.open(buf).convert('RGB');im.thumbnail((1100,800));images.append(im)
            with tempfile.NamedTemporaryFile(suffix='.gif',dir=str(__import__('pathlib').Path(path).resolve().parent),delete=False) as temp:tempname=temp.name
            images[0].save(tempname,save_all=True,append_images=images[1:],duration=self.speed.value(),loop=0);os.replace(tempname,path);tempname=None;return True
        except (OSError,ValueError) as error:QMessageBox.warning(self,self.tr('导出失败','Export failed'),str(error));return False
        finally:
            if tempname and os.path.exists(tempname):os.unlink(tempname)
            for im in images:im.close()
            progress.close()
            for w,state in zip(widgets,states):w.setEnabled(state)
            self.step.setCurrentIndex(initial);self.redraw();self.play_button.setText(self.tr('播放','Play'))
