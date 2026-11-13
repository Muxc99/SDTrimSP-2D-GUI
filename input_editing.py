"""输入文件文本草稿：检查后同步 GUI，不因预览刷新而丢失未完成编辑。"""
from pathlib import Path
from PySide6.QtCore import Qt,QSize
from PySide6.QtGui import QTextCursor,QTextDocument,QShortcut,QKeySequence,QPixmap,QPainter,QPen,QColor,QIcon
from PySide6.QtWidgets import QHBoxLayout,QLabel,QFileDialog,QInputDialog,QMessageBox,QLineEdit,QWidget,QStyle
from compact_toolbar import icon_button
from case_model import inspect_input,Figure,validate

def required_input_files(data):
    names={'tri.inp','stop_run.inp'}
    if data['case_geo']==26:names.add('fig.inp')
    if data['case_geo'] in (24,25):names.add('rauh.inp')
    if data['case_e0']==1:names.add('energy.inp')
    if data['case_alpha']==4:names.add('angle.inp')
    if data.get('isbv')==6:names.add('mat_surfb.inp')
    for key,name in [('iq0','initial_composition.inp'),('iq0_surf','initial_composition_surf.inp')]:
        if data.get(key,0):names.add(name)
    if data.get('l_clust') and data.get('l_clust_read'):names.add('doped_zellen_2D.inp')
    return names

class InputEditing:
    def raw_text(self,zh,en):return en if getattr(self,'ui_language','zh')=='en' else zh

    def init_raw_controls(self,layout):
        row=QHBoxLayout();row.setSpacing(2);layout.insertLayout(0,row)
        self.raw_buttons=[]
        def tool(parent,zh,en,icon,slot):
            b=icon_button(self,zh,icon,slot);b.setFixedSize(28,26);b.setIconSize(QSize(16,16))
            parent.addWidget(b);self.raw_buttons.append((b,zh,en));return b
        sp=QStyle.StandardPixmap
        tool(row,'添加文件…','Add file…',sp.SP_FileIcon,self.add_input_file)
        tool(row,'导入文件…','Import file…',sp.SP_DialogOpenButton,self.import_input_file)
        tool(row,'保存（Ctrl+S）','Save (Ctrl+S)',sp.SP_DialogSaveButton,self.save_current)
        tool(row,'移除文件','Remove file',sp.SP_TrashIcon,self.remove_input_file)
        row.addSpacing(7)
        from target_editor import tool_icon
        undo=tool(row,'撤销（Ctrl+Z）','Undo (Ctrl+Z)',sp.SP_ArrowBack,lambda:self.raw_editor_action('undo'));undo.setIcon(tool_icon('undo'))
        redo=tool(row,'重做（Ctrl+Y）','Redo (Ctrl+Y)',sp.SP_ArrowForward,lambda:self.raw_editor_action('redo'));redo.setIcon(tool_icon('redo'))
        row.addSpacing(7)
        self.apply_raw_button=tool(row,'应用文本修改','Apply text edits',sp.SP_DialogApplyButton,lambda:self.apply_raw_edits())
        self.discard_raw_button=tool(row,'撤销未应用文本','Discard unapplied text',sp.SP_DialogResetButton,self.discard_raw_edits)
        self.layers_raw_button=tool(row,'靶材功能…','Target features…',sp.SP_FileDialogDetailedView,self.edit_target_features)
        find=tool(row,'查找（Ctrl+F）','Find (Ctrl+F)',sp.SP_FileDialogContentsView,self.show_raw_find)
        pixmap=QPixmap(20,20);pixmap.fill(Qt.GlobalColor.transparent);p=QPainter(pixmap);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor('#41596b'),1.8));p.drawEllipse(3,2,10,10);p.drawLine(12,11,18,17);p.end();find.setIcon(QIcon(pixmap))
        row.addStretch()
        self.raw_search_bar=QWidget();search=QHBoxLayout(self.raw_search_bar);search.setContentsMargins(0,0,0,0);search.setSpacing(2)
        layout.insertWidget(1,self.raw_search_bar);self.raw_search_bar.hide()
        self.raw_search=QLineEdit();search.addWidget(self.raw_search,1)
        self.raw_search.returnPressed.connect(self.find_raw_text)
        tool(search,'上一处','Previous',sp.SP_ArrowUp,lambda:self.find_raw_text(True))
        tool(search,'下一处','Next',sp.SP_ArrowDown,lambda:self.find_raw_text(False))
        tool(search,'关闭查找','Close find',sp.SP_DialogCloseButton,self.raw_search_bar.hide)
        shortcut=QShortcut(QKeySequence.StandardKey.Find,self.files_page);shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(self.show_raw_find);self.raw_find_shortcut=shortcut
        self.raw_status=QLabel();self.raw_status.setWordWrap(True);self.raw_status.setMaximumHeight(58);layout.addWidget(self.raw_status)
        self.tri_preview.textChanged.connect(lambda:self.raw_edited('tri.inp'))
        self.fig_preview.textChanged.connect(lambda:self.raw_edited('fig.inp'))
        self.tabs.currentChanged.connect(self.raw_tab_changed);self.update_raw_status()

    def show_raw_find(self):
        self.raw_search_bar.show();self.raw_search.setFocus();self.raw_search.selectAll()

    def raw_editor_action(self,action):
        editor=self.aux_tabs.currentWidget()
        if editor:getattr(editor,action)()

    def find_raw_text(self,backward=False):
        editor=self.aux_tabs.currentWidget();text=self.raw_search.text()
        if not editor or not text:return
        flags=QTextDocument.FindFlag.FindBackward if backward else QTextDocument.FindFlag(0)
        if not editor.find(text,flags):
            editor.moveCursor(QTextCursor.MoveOperation.End if backward else QTextCursor.MoveOperation.Start)
            editor.find(text,flags)

    def set_extra_values(self,updates):
        previous=self.loading;self.loading=True
        try:
            for key,value in updates.items():
                row=next((r for r in range(self.extra_table.rowCount()) if self.cell(self.extra_table,r,0)==key),None)
                if row is None:
                    row=self.extra_table.rowCount();self.extra_table.insertRow(row)
                    self.set_cell(self.extra_table,row,0,key)
                    self.extra_table.item(row,0).setFlags(self.extra_table.item(row,0).flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.set_cell(self.extra_table,row,1,value)
        finally:self.loading=previous

    def edit_target_features(self):
        if not self.apply_raw_edits():return
        try:
            from target_features import TargetFeaturesDialog
            TargetFeaturesDialog(self).exec()
        except ValueError as e:QMessageBox.warning(self,self.raw_text('靶材输入错误','Target input error'),str(e))

    def edit_layers(self):
        if not self.apply_raw_edits():return
        try:
            from layer_editor import LayerDialog
            dialog=LayerDialog(self);dialog.exec()
        except ValueError as e:QMessageBox.warning(self,self.raw_text('分层输入错误','Layer input error'),str(e))

    def add_input_file(self):
        if not self.apply_raw_edits():return
        name,ok=QInputDialog.getItem(self,self.raw_text('添加输入文件','Add input file'),self.raw_text('选择可选功能文件','Choose an optional feature file'),
            ['initial_composition.inp','initial_composition_surf.inp','energy.inp','angle.inp','mat_surfb.inp','doped_zellen_2D.inp'],0,True)
        if ok:self.install_input_file(name.strip(),None)

    def import_input_file(self):
        if not self.apply_raw_edits():return
        path,_=QFileDialog.getOpenFileName(self,self.raw_text('导入输入文件','Import input file'),'','Input (*.inp)')
        if path:
            from case_model import read_text
            self.install_input_file(Path(path).name,read_text(path))

    def install_input_file(self,name,text):
        try:
            if Path(name).name!=name or not name.lower().endswith('.inp') or name in ('tri.inp','fig.inp','stop_run.inp'):
                raise ValueError(self.raw_text('请选择有效的辅助 .inp 文件名。','Choose a valid auxiliary .inp filename.'))
            if name in self.files:raise ValueError(self.raw_text('文件已经存在，请直接编辑。','File already exists; edit its tab.'))
            from layer_editor import LAYER_FILES,render_layers,default_layer_rows
            if name in LAYER_FILES:
                d,_=self.collect()
                if text is None:text=render_layers(default_layer_rows(d,self.current_files(),name.endswith('_surf.inp')),len(d['symbol']))
                from case_model import parse_layers
                parse_layers(text,len(d['symbol']))
                self.set_extra_values({LAYER_FILES[name]:'1'})
            if text is None:
                from target_inputs import template
                text=template(name,self.collect()[0])
            from target_inputs import parse_local,parse_distribution,parse_matrix
            d,_=self.collect()
            if name=='doped_zellen_2D.inp':parse_local(text,d)
            if name in ('energy.inp','angle.inp'):parse_distribution(text,name=='angle.inp')
            if name=='mat_surfb.inp':parse_matrix(text,d['symbol'])
            self.set_auxiliary_file(name,text)
            self.dirty=True;self.refresh();self.aux_tabs.setCurrentWidget(self.aux_editors[name])
        except (ValueError,OSError) as e:QMessageBox.warning(self,self.raw_text('无法添加文件','Cannot add file'),str(e))

    def remove_input_file(self):
        if not self.apply_raw_edits():return
        name=self.aux_tabs.tabText(self.aux_tabs.currentIndex()).rstrip(' *')
        try:
            d,_=self.collect()
            if name in required_input_files(d):
                raise ValueError(self.raw_text('当前配置需要此文件，不能移除。分层文件请先在分层编辑器中关闭启用开关。','This file is required by the current configuration. Disable the corresponding layers before removing a layer file.'))
            if name not in self.files:return
            if QMessageBox.question(self,self.raw_text('移除文件','Remove file'),self.raw_text('从当前案例移除此文件？保存时会备份原文件后再移除。','Remove this file from the case? Saving will back up the original before removal.'))!=QMessageBox.StandardButton.Yes:return
            self.files.pop(name);self.removed_files.add(name);self.raw_pending.discard(name)
            editor=self.aux_editors.pop(name,None)
            if editor:self.aux_tabs.removeTab(self.aux_tabs.indexOf(editor));editor.deleteLater()
            elif name=='fig.inp':self.aux_tabs.removeTab(self.aux_tabs.indexOf(self.fig_preview))
            self.dirty=True;self.refresh()
        except ValueError as e:QMessageBox.warning(self,self.raw_text('不能移除','Cannot remove'),str(e))

    def update_raw_status(self):
        if hasattr(self,'raw_buttons'):
            for b,zh,en in self.raw_buttons:
                label=self.raw_text(zh,en);b.setText(label);b.setToolTip(label);b.setAccessibleName(label);b.setStatusTip(label)
            self.layers_raw_button.setText(self.raw_text('靶材功能…','Target features…'))
            self.raw_search.setPlaceholderText(self.raw_text('查找当前文件（Ctrl+F）','Find in current file (Ctrl+F)'))
        if hasattr(self,'aux_tabs'):
            for i in range(self.aux_tabs.count()):
                name=self.aux_tabs.tabText(i).rstrip(' *');self.aux_tabs.setTabText(i,name+(' *' if name in self.raw_pending else ''))
        self.apply_raw_button.setEnabled(bool(self.raw_pending));self.discard_raw_button.setEnabled(bool(self.raw_pending))
        if self.raw_error:
            self.raw_status.setText(self.raw_text('文本未应用：','Text not applied: ')+self.raw_error)
            self.raw_status.setStyleSheet('color:#c00000');self.raw_status.setToolTip(self.raw_error)
        elif self.raw_pending:
            self.raw_status.setText(self.raw_text('待应用：','Pending: ')+', '.join(sorted(self.raw_pending))+self.raw_text('。点击应用，或切换页面、保存/运行时自动检查并应用。','. Apply now, or switch pages/save/run to validate and apply.'))
            self.raw_status.setStyleSheet('color:#8b5c2c');self.raw_status.setToolTip('')
        else:
            self.raw_status.setText(self.raw_text('文本与当前参数同步。文件中的长度单位为 Å。','Text is synchronized with current parameters. File lengths use Å.'))
            self.raw_status.setStyleSheet('color:#285d58');self.raw_status.setToolTip('')

    def raw_edited(self,name):
        if self.loading or self.raw_applying:return
        self.raw_pending.add(name);self.raw_error=None;self.dirty=True;self.update_raw_status()
        self.save_button.setEnabled(True);self.save_as_button.setEnabled(True);self.run_button.setEnabled(self.process is None)

    def update_raw_previews(self,tri,figtext):
        texts={'tri.inp':tri,'fig.inp':figtext if figtext is not None else self.files.get('fig.inp','')}
        for name,editor in [('tri.inp',self.tri_preview),('fig.inp',self.fig_preview)]:
            if name in self.raw_pending:continue
            if editor.toPlainText()!=texts[name]:
                blocked=editor.blockSignals(True)
                if self.raw_applying:
                    cursor=editor.textCursor();cursor.beginEditBlock();cursor.select(QTextCursor.SelectionType.Document);cursor.insertText(texts[name]);cursor.endEditBlock()
                else:editor.setPlainText(texts[name])
                editor.document().setModified(False);editor.blockSignals(blocked)
        self.update_raw_status()

    def apply_raw_edits(self):
        if not self.raw_pending:return True
        if self.raw_applying:return True
        try:
            texts=self.current_files();texts['tri.inp']=self.tri_preview.toPlainText()
            if 'fig.inp' in self.raw_pending or 'fig.inp' in texts:texts['fig.inp']=self.fig_preview.toPlainText()
            nl,data=inspect_input(texts['tri.inp'])
            fig=Figure.parse(texts.get('fig.inp',''),int(data['ncp'])) if data['case_geo']==26 else None
            data['_files']={name:text for name,text in texts.items() if name!='tri.inp'}
            errors,_,_=validate(data,fig)
            if errors:raise ValueError('\n'.join(errors))
        except Exception as error:
            self.raw_error=str(error);self.update_raw_status();return False
        self.raw_applying=True
        try:
            if not self.load_case(self.source,overrides=texts):return False
            self.dirty=True;self.raw_error=None;self.raw_pending.clear();self.update_raw_status()
            self.target_editor.select_cells(self.target_editor.selected_cells,self.target_editor.active_cell)
            self.statusBar().showMessage(self.raw_text('文本已应用到参数表和绘图；原案例文件未修改。','Text applied to parameters and drawing; original case files are unchanged.'),7000)
            return True
        finally:self.raw_applying=False

    def discard_raw_edits(self):
        self.loading=True
        try:
            for name,editor in self.aux_editors.items():
                if name in self.raw_pending:editor.setPlainText(self.files.get(name,''));editor.document().setModified(False)
        finally:self.loading=False
        self.raw_pending.clear();self.raw_error=None;self.refresh();self.update_raw_status()

    def raw_tab_changed(self,index):
        if self.loading or self.raw_applying or not self.raw_pending or self.tabs.widget(index) is self.files_page:return
        if not self.apply_raw_edits():self.tabs.setCurrentWidget(self.files_page)
