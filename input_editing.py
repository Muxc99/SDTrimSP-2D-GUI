"""输入文件文本草稿：检查后同步 GUI，不因预览刷新而丢失未完成编辑。"""
from PySide6.QtWidgets import QHBoxLayout,QPushButton,QLabel
from case_model import inspect_input,Figure,validate

class InputEditing:
    def raw_text(self,zh,en):return en if getattr(self,'ui_language','zh')=='en' else zh

    def init_raw_controls(self,layout):
        row=QHBoxLayout();layout.insertLayout(1,row)
        self.apply_raw_button=QPushButton('应用文本修改');self.discard_raw_button=QPushButton('撤销未应用文本')
        row.addWidget(self.apply_raw_button);row.addWidget(self.discard_raw_button);row.addStretch()
        self.raw_status=QLabel();self.raw_status.setWordWrap(True);self.raw_status.setMaximumHeight(58);layout.insertWidget(2,self.raw_status)
        self.apply_raw_button.clicked.connect(lambda:self.apply_raw_edits())
        self.discard_raw_button.clicked.connect(self.discard_raw_edits)
        self.tri_preview.textChanged.connect(lambda:self.raw_edited('tri.inp'))
        self.fig_preview.textChanged.connect(lambda:self.raw_edited('fig.inp'))
        self.tabs.currentChanged.connect(self.raw_tab_changed);self.update_raw_status()

    def update_raw_status(self):
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
                blocked=editor.blockSignals(True);editor.setPlainText(texts[name]);editor.document().setModified(False);editor.blockSignals(blocked)
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
        self.raw_pending.clear();self.raw_error=None;self.refresh();self.update_raw_status()

    def raw_tab_changed(self,index):
        if self.loading or self.raw_applying or not self.raw_pending or self.tabs.widget(index) is self.files_page:return
        if not self.apply_raw_edits():self.tabs.setCurrentWidget(self.files_page)
