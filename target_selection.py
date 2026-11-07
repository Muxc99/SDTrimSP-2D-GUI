from element_colors import tint_species_item
"""绘图区的单元选择、原子化编辑与内部剪贴板。物理坐标一律使用 Å。"""
import math
from PySide6.QtCore import Qt,QItemSelection,QItemSelectionModel
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QFormLayout,QLineEdit,QLabel,
    QDialogButtonBox,QTableWidget,QTableWidgetItem,QHeaderView,QPushButton,QMenu)
from matplotlib.patches import Rectangle
from matplotlib.collections import PolyCollection
from case_model import number,fmt
from drawing_model import cell_at,grid_key,split_rectangle,move_rows,MAX_DRAW_CELLS
from element_picker import NoWheelComboBox
from target_render import selection_rectangles

class BlockEditDialog(QDialog):
    def __init__(self,editor,mode):
        super().__init__(editor)
        self.editor=editor;self.mode=mode;self.rows=editor.owner.selected_rows();self.cells=set(editor.selected_cells)
        self.setWindowTitle(editor.text('编辑色块' if mode=='block' else '批量更改材料' if mode=='material' else '移动选区',
                                        'Edit block' if mode=='block' else 'Change selected material' if mode=='material' else 'Move selection'))
        self.setMinimumWidth(430);layout=QVBoxLayout(self);form=QFormLayout();layout.addLayout(form)
        values=editor.rows();chosen=[values[i] for i in self.rows]
        occupied={grid_key(r,*editor.geometry()[:3]) for r in chosen}
        chosen += [editor.canonical_bounds(k)+list(editor.data['qu_tar']) for k in editor.canonical_cells(self.cells) if k not in occupied]
        f=editor.owner.factor
        self.edits={};self.error=QLabel();self.error.setWordWrap(True);self.error.setStyleSheet('color:#c00000')
        if mode in ('block','move'):
            x=min(r[0] for r in chosen)/f;z=min(r[2] for r in chosen)/f
            fields=[('x',editor.text('左侧 x','Left x'),x),('z',editor.text('底部 z','Bottom z'),z)]
            if mode=='block':fields += [('width',editor.text('宽度','Width'),(chosen[0][1]-chosen[0][0])/f),('height',editor.text('高度','Height'),(chosen[0][3]-chosen[0][2])/f)]
            for key,label,value in fields:
                edit=QLineEdit(fmt(value));self.edits[key]=edit;form.addRow(label+' / '+editor.owner.unit.currentText(),edit)
        if mode!='move':
            layout.addWidget(QLabel(editor.text('成分（原子分数，合计为 1）','Composition (atomic fractions; sum = 1)')))
            self.composition=QTableWidget(1,len(editor.data['symbol']));self.composition.setHorizontalHeaderLabels(editor.data['symbol'])
            self.composition.verticalHeader().hide();self.composition.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.composition.setFixedHeight(78);layout.addWidget(self.composition)
            q=chosen[0][4:] if editor.owner.with_qu.isChecked() else editor.data['qu_tar']
            for i,value in enumerate(q):
                item=QTableWidgetItem(fmt(value));tint_species_item(item,editor.data['symbol'][i]);self.composition.setItem(0,i,item)
            preset=NoWheelComboBox();preset.addItem(editor.text('选择纯元素材料…','Choose a pure species…'),None)
            for i,symbol in enumerate(editor.data['symbol']):preset.addItem(symbol,i)
            def set_pure(index):
                species=preset.itemData(index)
                if species is not None:
                    for i in range(self.composition.columnCount()):self.composition.item(0,i).setText('1' if i==species else '0')
            preset.currentIndexChanged.connect(set_pure);layout.addWidget(preset)
            base=QPushButton(editor.text('采用基底成分','Use substrate'))
            base.clicked.connect(lambda:[self.composition.item(0,i).setText(fmt(q)) for i,q in enumerate(editor.data['qu_tar'])]);layout.addWidget(base)
        note=QLabel(editor.text('镜像开启时，左右两侧联动。尺寸跨网格时自动切分；与其他材料格冲突时整次拒绝。',
                               'Mirrored sides stay linked. Shapes crossing mesh lines are split; occupied-cell collisions reject the entire edit.'))
        note.setWordWrap(True);layout.addWidget(note);layout.addWidget(self.error)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(editor.text('确定','OK'))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(editor.text('取消','Cancel'))
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
        self.context=editor.edit_context();self.snapshot=editor.rows()

    def accept(self):
        e=self.editor
        try:
            if e.edit_context()!=self.context or e.rows()!=self.snapshot:
                raise ValueError(e.text('输入已变化，请关闭窗口后重新选择。','Inputs changed. Close this dialog and select again.'))
            f=e.owner.factor
            if self.mode=='move':
                e.move_selection(number(self.edits['x'].text())*f-min(e.canonical_bounds(k)[0] for k in e.canonical_cells(self.cells)),
                                 number(self.edits['z'].text())*f-min(e.canonical_bounds(k)[2] for k in e.canonical_cells(self.cells)),self.rows)
            else:
                q=[number(self.composition.item(0,i).text()) for i in range(self.composition.columnCount())]
                if self.mode=='block':
                    x,z,w,h=[number(self.edits[k].text())*f for k in ('x','z','width','height')]
                    e.edit_block(self.rows[0] if self.rows else None,[x,x+w,z,z+h],q)
                else:e.apply_material(q,self.rows,self.cells)
        except (ValueError,OverflowError) as error:self.error.setText(str(error));return
        super().accept()

class SelectionActions:
    def init_selection(self):
        self.active_block=None;self.paste_point=None;self.clipboard=None;self.clipboard_context=None
        self.selection_context=None;self.context_menu=None;self.edit_dialog=None
        self.selected_cells=set();self.active_cell=None;self.selection_anchor=None

    def edit_context(self):
        d=self.data
        return (str(self.owner.source),tuple(d['symbol']),d['case_geo'],d['geo_x'],d['geo_dx'],d['geo_dz'],bool(self.owner.mirror.isChecked()))

    def sync_selection(self):
        context=self.edit_context()
        if self.selection_context is not None and context!=self.selection_context:
            self.clipboard=None;self.active_block=None;self.paste_point=None;self.selected_cells.clear();self.active_cell=None;self.selection_anchor=None;self.owner.blocks.clearSelection()
        if self.clipboard and self.clipboard['cut'] and self.clipboard['snapshot']!=self.rows():self.clipboard=None
        self.selection_context=context
        if self.active_block and self.active_block[0]>=self.owner.blocks.rowCount():self.active_block=None

    def selection_grid(self):
        d=self.data
        return d['geo_x'],d['geo_dx'],d['geo_dz'],self.owner.mirror.isChecked()

    def cell_key(self,x,z):
        gx,dx,dz,mirror=self.selection_grid()
        if not all(math.isfinite(v) for v in (x,z)) or not -gx<=x<gx or not 0<=z<4998*dz:return None
        return (math.floor((x+gx)/dx),math.floor(z/dz))

    def valid_cell(self,key):
        gx,dx,dz,_=self.selection_grid()
        return 0<=key[0]<round(2*gx/dx) and 0<=key[1]<4998

    def canonical_key(self,key):
        gx,dx,dz,mirror=self.selection_grid();nx=round(2*gx/dx)
        return (nx-1-key[0],key[1]) if mirror and key[0]<nx//2 else key

    def canonical_cells(self,cells=None):
        return {self.canonical_key(k) for k in (self.selected_cells if cells is None else cells)}

    def cell_bounds(self,key):
        gx,dx,dz,_=self.selection_grid();a=-gx+key[0]*dx;c=key[1]*dz
        return [a,min(a+dx,gx),c,c+dz]

    def canonical_bounds(self,key):return self.cell_bounds(self.canonical_key(key))

    def cell_occupancy(self):
        gx,dx,dz,_=self.selection_grid()
        rows=self.cached_rows();key=(gx,dx,dz)
        if self._occupancy_cache is None or self._occupancy_cache[0]!=key:
            self._occupancy_cache=(key,{grid_key(r,gx,dx,dz):i for i,r in enumerate(rows)})
        return self._occupancy_cache[1]

    def select_cells(self,cells,active=None):
        cells=set(cells)
        if len(cells)>MAX_DRAW_CELLS:raise ValueError(self.text('选区超过 20000 格，请缩小范围。','Selection exceeds 20000 cells. Select a smaller region.'))
        self.selected_cells={k for k in cells if self.valid_cell(k)}
        self.active_cell=active if active in self.selected_cells else (min(self.selected_cells,key=lambda k:(k[1],k[0])) if self.selected_cells else None)
        occupied=self.cell_occupancy();indices=sorted({occupied[k] for k in self.canonical_cells() if k in occupied})
        active_row=occupied.get(self.canonical_key(self.active_cell)) if self.active_cell else None
        side=bool(self.active_cell and self.cell_bounds(self.active_cell)[1]<=0 and self.owner.mirror.isChecked())
        self.active_block=(active_row,side) if active_row is not None else None
        table=self.owner.blocks;selection=QItemSelection()
        # Compress consecutive rows into ranges instead of thousands of Qt selections.
        start=last=None
        for i in indices+[None]:
            if last is not None and i!=last+1:
                selection.select(table.model().index(start,0),table.model().index(last,table.columnCount()-1));start=None
            if start is None:start=i
            last=i
        blocked=table.blockSignals(True)
        table.selectionModel().select(selection,QItemSelectionModel.SelectionFlag.ClearAndSelect|QItemSelectionModel.SelectionFlag.Rows)
        if self.active_block:table.selectionModel().setCurrentIndex(table.model().index(self.active_block[0],0),QItemSelectionModel.SelectionFlag.NoUpdate)
        table.blockSignals(blocked)
        self.paste_point=None
        if self.active_cell is not None and active_row is None:
            a,b,c,d=self.cell_bounds(self.active_cell);self.paste_point=((a+b)/2,(c+d)/2)
        if self.selection_anchor not in self.selected_cells:self.selection_anchor=self.active_cell
        self.highlight_selection()

    def select_rows(self,indices,active=None):
        indices=sorted(set(i for i in indices if 0<=i<self.owner.blocks.rowCount()));rows=self.rows()
        gx,dx,dz,mirror=self.selection_grid();nx=round(2*gx/dx)
        side=bool(active and active[1] and mirror)
        keys={grid_key(rows[i],gx,dx,dz) for i in indices}
        if side:keys={(nx-1-i,j) for i,j in keys}
        key=grid_key(rows[active[0]],gx,dx,dz) if active and active[0] in indices else None
        if key and side:key=(nx-1-key[0],key[1])
        self.select_cells(keys,key)

    def select_at(self,point,modifiers=()):
        key=self.cell_key(*point);prior=set(self.selected_cells)
        if key is None:self.select_cells([]);return
        if {'ctrl','control'} & set(modifiers):
            if key in prior:prior.remove(key)
            else:prior.add(key)
            self.select_cells(prior,key)
        elif 'shift' in modifiers and self.selection_anchor is not None:
            start=self.cell_bounds(self.selection_anchor);end=self.cell_bounds(key)
            self.select_region(((start[0]+start[1])/2,(start[2]+start[3])/2),((end[0]+end[1])/2,(end[2]+end[3])/2),add_cells=prior)
        else:
            self.select_cells([key],key);self.selection_anchor=key

    def table_selection_changed(self):
        if self.owner.loading or self.syncing:return
        self.select_rows(self.owner.selected_rows(),self.active_block)

    def visual_rows(self):
        for i,r in enumerate(self.rows()):
            yield i,False,r[:4]
            if self.owner.mirror.isChecked():yield i,True,[-r[1],-r[0],r[2],r[3]]

    def select_region(self,start,end,add=(),add_cells=()):
        gx,dx,dz,mirror=self.selection_grid();a,b=sorted((start[0],end[0]));c,d=sorted((start[1],end[1]))
        ia=max(0,math.floor((a+gx)/dx));ib=min(round(2*gx/dx),math.ceil((b+gx)/dx-1e-10))
        ja=max(0,math.floor(c/dz));jb=min(4998,math.ceil(d/dz-1e-10))
        if max(0,ib-ia)*max(0,jb-ja)>MAX_DRAW_CELLS:raise ValueError(self.text('选区超过 20000 格，请缩小范围。','Selection exceeds 20000 cells. Select a smaller region.'))
        cells=set(add_cells)|{(i,j) for i in range(ia,ib) for j in range(ja,jb)}
        rows=self.rows()
        for i in add:
            if 0<=i<len(rows):cells.add(grid_key(rows[i],gx,dx,dz))
        end_key=self.cell_key(*end);self.select_cells(cells,end_key)
        return self.owner.selected_rows()

    def select_grid_span(self,start,end,add_cells=()):
        gx,dx,dz,_=self.selection_grid();nx=round(2*gx/dx)
        def key(point):return (max(0,min(nx-1,math.floor((point[0]+gx)/dx))),max(0,min(4997,math.floor(point[1]/dz))))
        first=key(start);last=key(end);ia,ib=sorted((first[0],last[0]));ja,jb=sorted((first[1],last[1]))
        if (ib-ia+1)*(jb-ja+1)>MAX_DRAW_CELLS:raise ValueError(self.text('选区超过 20000 格，请缩小范围。','Selection exceeds 20000 cells. Select a smaller region.'))
        cells=set(add_cells)|{(i,j) for i in range(ia,ib+1) for j in range(ja,jb+1)}
        if cells!=self.selected_cells or last!=self.active_cell:self.select_cells(cells,last)
        self.selection_anchor=first
        return self.owner.selected_rows()

    def select_all_cells(self):
        f=self.owner.factor;a,b=self.ax.get_xlim();c,d=self.ax.get_ylim()
        return self.select_region((a*f,c*f),(b*f,d*f),add=range(self.owner.blocks.rowCount()))

    def selection_decorations(self):
        f=self.owner.factor
        if self.selected_cells:
            bounds=[self.cell_bounds(key) for key in self.selected_cells]
            self.selection_artists.extend(selection_rectangles(self.ax,bounds,self.selection_grid()[:3],f,'#168fa5','#168fa5',.16,.8,7))
        if self.active_cell is not None:
            a,b,c,d=self.cell_bounds(self.active_cell)
            p=Rectangle((a/f,c/f),(b-a)/f,(d-c)/f,fill=False,edgecolor='#147d92',lw=2.3,zorder=9)
            self.ax.add_patch(p);self.selection_artists.append(p)
        if self.clipboard and self.clipboard['cut']:
            polygons=[]
            for key in self.clipboard.get('cells',()):
                a,b,c,d=self.cell_bounds(key);polygons.append([(a/f,c/f),(b/f,c/f),(b/f,d/f),(a/f,d/f)])
            p=PolyCollection(polygons,facecolors='none',edgecolors='#a44e1d',linewidths=1.5,linestyles='--',zorder=10)
            self.ax.add_collection(p,autolim=False);self.selection_artists.append(p)

    def check_fractions(self,q):
        if len(q)!=len(self.data['symbol']) or any(not math.isfinite(v) or not 0<=v<=1 for v in q) or not math.isclose(sum(q),1.,abs_tol=1e-6):
            raise ValueError(self.text('成分须与元素数量一致，各项为 0～1，合计为 1。','Fractions must match the species count, lie in [0,1] and sum to 1.'))

    def effective_rows(self):
        rows=self.rows()
        if not self.owner.with_qu.isChecked():
            for r in rows:r[4:]=self.data['qu_tar']
        return rows

    def apply_material(self,q,indices=None,cells=None):
        self.check_fractions(q);indices=self.owner.selected_rows() if indices is None else indices
        cells=set(self.selected_cells if cells is None else cells)
        if not indices and not cells:return
        before=self.rows();after=self.effective_rows();occupied=self.cell_occupancy()
        for i in indices:after[i][4:]=q
        for key in sorted(self.canonical_cells(cells)):
            if key not in occupied:after.append(self.cell_bounds(key)+list(q))
        if len(after)>MAX_DRAW_CELLS:raise ValueError(self.text('填充后超过 20000 个块，请缩小选区。','Fill would exceed 20000 blocks. Select fewer cells.'))
        active=self.active_cell;self.commit(before,after,with_qu=True);self.select_cells(cells,active)
        self.message(f'已填充或更改 {len(self.canonical_cells(cells))} 个网格的材料。',f'Filled or changed material in {len(self.canonical_cells(cells))} cells.')

    def edit_block(self,index,bounds,q):
        self.check_fractions(q);a,b,c,d=bounds;gx,dx,dz,mirror=self.selection_grid()
        if not all(math.isfinite(v) for v in bounds) or not a<b or not 0<=c<d:
            raise ValueError(self.text('宽高须大于零，底部 z 不能小于零。','Width and height must be positive; bottom z must be nonnegative.'))
        if a<(-1e-9 if mirror else -gx-1e-9) or b>gx+1e-9:
            raise ValueError(self.text('编辑后超出横向范围；镜像时只编辑右半区。','Edited block exceeds lateral bounds; edit the right half when mirroring.'))
        before=self.rows();source=self.effective_rows();stationary=[r for i,r in enumerate(source) if i!=index]
        new=split_rectangle(a,b,c,d,gx,dx,dz,mirror,q)
        occupied={grid_key(r,gx,dx,dz) for r in stationary}
        if any(grid_key(r,gx,dx,dz) in occupied for r in new):raise ValueError(self.text('编辑后占用其他色块的网格，请调整尺寸或位置。','Edited block collides with occupied cells. Adjust size or position.'))
        self.commit(before,stationary+new,with_qu=True);self.select_rows(range(len(stationary),len(stationary)+len(new)))
        self.message(f'已更新尺寸和成分，按网格保存为 {len(new)} 个块。',f'Size and composition updated; stored as {len(new)} mesh blocks.')

    def move_selection(self,sx,sz,indices=None):
        if not math.isfinite(sx) or not math.isfinite(sz):raise ValueError(self.text('移动坐标必须为有限数值。','Move coordinates must be finite.'))
        indices=set(self.owner.selected_rows() if indices is None else indices);cells=set(self.selected_cells)
        if not indices and not cells:return
        gx,dx,dz,mirror=self.selection_grid();occupied=self.cell_occupancy();empty=self.canonical_cells(cells)-occupied.keys()
        if empty and (not math.isclose(sx/dx,round(sx/dx),abs_tol=1e-8) or not math.isclose(sz/dz,round(sz/dz),abs_tol=1e-8)):
            raise ValueError(self.text('含空白格的选区请按整格移动。','Move selections containing empty cells by whole grid increments.'))
        nx=round(2*gx/dx);shifted=set()
        for key in cells:
            side=mirror and key[0]<nx//2;target=(key[0]+round((-sx if side else sx)/dx),key[1]+round(sz/dz))
            if not self.valid_cell(target):raise ValueError(self.text('移动后选区超出靶区。','Moved selection exceeds target bounds.'))
            shifted.add(target)
        before=self.rows();after=move_rows(before,indices,sx,sz,gx,dx,dz,mirror)
        stationary={grid_key(r,gx,dx,dz) for i,r in enumerate(before) if i not in indices}
        if self.canonical_cells(shifted)&stationary:raise ValueError(self.text('移动后选区包含已占用的网格。','Moved selection contains occupied cells.'))
        count=len(before)-len(indices);self.commit(before,after)
        if empty or not indices:self.select_cells(shifted)
        else:self.select_rows(range(count,len(after)))
        self.message(f'已移动 {len(cells)} 个网格的选区。',f'Moved a selection of {len(cells)} cells.')

    def copy_selection(self,cut=False):
        indices=self.owner.selected_rows()
        cells=self.canonical_cells()
        if not indices and not cells:return
        source=self.rows();effective=self.effective_rows();gx,dx,dz,mirror=self.selection_grid()
        payload=[effective[i][:] for i in indices]
        self.clipboard={'rows':payload,'indices':indices[:],'cut':cut,'snapshot':source,
                        'cells':cells,'anchor':(min(k[0] for k in cells),min(k[1] for k in cells))}
        self.clipboard_context=self.edit_context();self.paste_point=None;self.highlight_selection()
        self.message('已准备剪切；点击空白格后 Ctrl+V。成功粘贴时才移除原位置。' if cut else '已复制；点击空白格后 Ctrl+V，可重复粘贴。',
                     'Cut ready. Click an empty cell, then Ctrl+V. Source is removed only after a valid paste.' if cut else 'Copied. Click an empty cell, then Ctrl+V. Repeat paste is supported.')

    def paste_selection(self,point=None):
        if not self.clipboard:return
        try:
            if self.edit_context()!=self.clipboard_context:raise ValueError(self.text('案例或网格已变化，请重新复制。','Case or mesh changed. Copy again.'))
            target=self.paste_point if point is None else point
            if target is None:raise ValueError(self.text('请先点击一个空白格，指定粘贴位置。','Click an empty cell to choose the paste destination first.'))
            gx,dx,dz,mirror=self.selection_grid();x,z=target
            cell=cell_at(abs(x) if mirror else x,z,gx,dx,dz,mirror)
            if cell is None:raise ValueError(self.text('请选择靶区内 z≥0 的空白格。','Choose an empty target cell at z>=0.'))
            clip=self.clipboard;before=self.rows();ix,iz=grid_key(cell,gx,dx,dz);sx=(ix-clip['anchor'][0])*dx;sz=(iz-clip['anchor'][1])*dz
            if clip['cut']:
                if before!=clip['snapshot']:raise ValueError(self.text('剪切来源已变化，请重新选择。','Cut source changed. Select again.'))
                selected=set(clip['indices']);base=before
            else:base=before+[r[:] for r in clip['rows']];selected=set(range(len(before),len(base)))
            destinations={(i+ix-clip['anchor'][0],j+iz-clip['anchor'][1]) for i,j in clip['cells']}
            if any(not self.valid_cell(k) for k in destinations):raise ValueError(self.text('粘贴的选区超出靶区。','Pasted selection exceeds target bounds.'))
            occupied={grid_key(r,gx,dx,dz) for i,r in enumerate(base) if i not in selected}
            if occupied & destinations:raise ValueError(self.text('目标选区包含已占用网格，请选择空白区域。','Destination contains occupied cells. Choose an empty region.'))
            # 关闭逐块成分时，粘贴前把既有块的实际基底成分显式保留下来。
            enable=self.owner.with_qu.isChecked() or any(r[4:]!=self.data['qu_tar'] for r in clip['rows'])
            if enable and not self.owner.with_qu.isChecked():
                base=[r[:4]+list(self.data['qu_tar']) if i<len(before) else r[:] for i,r in enumerate(base)]
            after=move_rows(base,selected,sx,sz,gx,dx,dz,mirror);count=len(base)-len(selected)
            if len(after)>MAX_DRAW_CELLS:raise ValueError(self.text('粘贴后超过 20000 个块，请缩小选区。','Paste would exceed 20000 blocks. Use a smaller selection.'))
            self.commit(before,after,with_qu=enable)
            if clip['cut']:self.clipboard=None
            nx=round(2*gx/dx);visual={(nx-1-i,j) for i,j in destinations} if mirror and x<0 else destinations
            self.paste_point=None;self.select_cells(visual)
            self.message(f'已粘贴 {len(after)-count} 个块。',f'Pasted {len(after)-count} blocks.')
        except (ValueError,OverflowError) as error:self.show_error(str(error))

    def open_edit_dialog(self,mode):
        selected=self.owner.selected_rows()
        if not self.selected_cells or self.owner.geometry.currentData()!=26:return
        if mode=='block' and len(self.canonical_cells())!=1:mode='material'
        self.edit_dialog=BlockEditDialog(self,mode);self.edit_dialog.open()

    def build_context_menu(self,point):
        menu=QMenu(self);selected=self.selected_cells;enabled=self.owner.geometry.currentData()==26
        def action(zh,en,slot,active=True):
            a=menu.addAction(self.text(zh,en));a.setEnabled(enabled and active);a.triggered.connect(lambda checked=False:slot());return a
        action('编辑大小和成分…','Edit size and composition…',lambda:self.open_edit_dialog('block'),len(self.canonical_cells())==1)
        action('整体更改材料…','Change selected material…',lambda:self.open_edit_dialog('material'),bool(selected))
        menu.addSeparator()
        action('复制\tCtrl+C','Copy\tCtrl+C',self.copy_selection,bool(selected))
        action('剪切\tCtrl+X','Cut\tCtrl+X',lambda:self.copy_selection(True),bool(selected))
        action('粘贴\tCtrl+V','Paste\tCtrl+V',lambda:self.paste_selection(point),self.clipboard is not None)
        action('移动到…','Move selection to…',lambda:self.open_edit_dialog('move'),bool(selected))
        menu.addSeparator();action('删除\tDelete','Delete\tDelete',self.delete_selected,bool(selected))
        action('全选\tCtrl+A','Select all\tCtrl+A',self.select_all_cells)
        return menu

    def navigate(self,direction,extend=False):
        if self.active_cell is None:
            selected=self.owner.selected_rows()
            if not selected:return
            self.select_rows(selected,self.active_block)
        if self.active_cell is None:return
        i,j=self.active_cell;di,dj={'left':(-1,0),'right':(1,0),'up':(0,1),'down':(0,-1)}[direction];target=(i+di,j+dj)
        if not self.valid_cell(target):return
        if extend:
            anchor=self.selection_anchor or self.active_cell;a=self.cell_bounds(anchor);b=self.cell_bounds(target)
            self.select_region(((a[0]+a[1])/2,(a[2]+a[3])/2),((b[0]+b[1])/2,(b[2]+b[3])/2));self.select_cells(self.selected_cells,target)
        else:self.select_cells([target],target);self.selection_anchor=target
        self.ensure_visible(self.cell_bounds(target))

    def ensure_visible(self,r):
        f=self.owner.factor;a,b=self.ax.get_xlim();c,d=self.ax.get_ylim();sx=sz=0.
        if r[0]/f<a:sx=r[0]/f-a-(b-a)*.04
        elif r[1]/f>b:sx=r[1]/f-b+(b-a)*.04
        if r[2]/f<c:sz=r[2]/f-c-(d-c)*.04
        elif r[3]/f>d:sz=r[3]/f-d+(d-c)*.04
        if sx or sz:self.ax.set_xlim(a+sx,b+sx);self.ax.set_ylim(c+sz,d+sz);self.update_grid()
