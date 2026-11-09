"""本机 Markdown 帮助中心：目录、检索与页内目录。"""
from pathlib import Path
from PySide6.QtCore import Qt,QUrl
from PySide6.QtGui import QDesktopServices,QTextCursor,QTextBlockFormat,QTextTable,QTextFrameFormat,QColor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QSplitter,QLineEdit,
    QTreeWidget,QTreeWidgetItem,QTextBrowser,QLabel,QPushButton,QListWidget,QMessageBox)

DOCS=Path(__file__).resolve().parent/'docs'/'help'
TOPICS=(
 ('start','开始使用','Getting started',(
  ('overview','界面与快速开始','Overview and quick start'),
  ('cases','新建、打开与保存','Cases and saving'),
  ('elements','元素、同位素与成分','Elements and composition'),
 )),
 ('target','靶与束流','Target and beam',(
  ('mesh','网格、基底与单位','Mesh, substrate and units'),
  ('geometry','几何类型与轮廓文件','Geometry and profiles'),
  ('blocks','26：绘制与编辑凸起块','26: protrusion editing'),
  ('profile','24/25：基底轮廓编辑','24/25: outline editing'),
  ('beam','束流、能量与角度','Beam, energy and angle'),
  ('models','碰撞势与结合能模型','Potential and binding models'),
 )),
 ('run','计算与结果','Run and results',(
  ('files','输入文本与高级参数','Input text and advanced parameters'),
  ('running','检查、运行与停止','Check, run and stop'),
  ('results','结果图种与物理含义','Plots and physical quantities'),
  ('navigation','绘图交互与数据导出','Plot navigation and export'),
 )),
 ('reference','参考与排错','Reference and troubleshooting',(
  ('shortcuts','快捷键与常见问题','Shortcuts and troubleshooting'),
 )),
)

class HelpView(QWidget):
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.language='zh';self.current_topic='overview'
        self.pages={};self.items={};self.positions=[];self.history=[];self.history_index=-1
        root=QVBoxLayout(self);root.setContentsMargins(0,0,0,0)
        split=QSplitter(Qt.Orientation.Horizontal);root.addWidget(split,1);self.splitter=split
        left=QWidget();ll=QVBoxLayout(left);ll.setContentsMargins(12,14,12,12)
        self.brand=QLabel('SDTrimSP-2D_GUI v0.9.2');self.brand.setStyleSheet('font-weight:bold;font-size:13pt;color:#136d92;');ll.addWidget(self.brand)
        self.search=QLineEdit();self.search.setClearButtonEnabled(True);ll.addWidget(self.search)
        self.tree=QTreeWidget();self.tree.setHeaderHidden(True);self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(12);ll.addWidget(self.tree,1)
        self.empty=QLabel();self.empty.setWordWrap(True);ll.addWidget(self.empty);self.empty.hide()
        split.addWidget(left)
        right=QWidget();rl=QVBoxLayout(right);rl.setContentsMargins(18,12,16,8)
        bar=QHBoxLayout();self.back=QPushButton('‹');self.forward=QPushButton('›')
        for button in (self.back,self.forward):button.setFixedWidth(34);bar.addWidget(button)
        self.breadcrumb=QLabel();bar.addWidget(self.breadcrumb,1);self.copy=QPushButton();bar.addWidget(self.copy);rl.addLayout(bar)
        body=QHBoxLayout();self.browser=QTextBrowser();self.browser.setOpenLinks(False);self.browser.setOpenExternalLinks(False)
        self.browser.setStyleSheet('QTextBrowser {background:white;font-size:11pt;}')
        self.browser.setFrameShape(QTextBrowser.Shape.NoFrame);body.addWidget(self.browser,1)
        side=QVBoxLayout();self.toc_label=QLabel();side.addWidget(self.toc_label)
        self.toc=QListWidget();self.toc.setFixedWidth(180);self.toc.setWordWrap(True)
        self.toc.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.toc.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        side.addWidget(self.toc,1);body.addLayout(side);rl.addLayout(body,1)
        self.location=QLabel();self.location.setStyleSheet('color:#6c8191;font-size:9pt;');rl.addWidget(self.location)
        split.addWidget(right);split.setSizes([270,1100]);split.setCollapsible(0,False);split.setCollapsible(1,False)
        left.setMinimumWidth(220);right.setMinimumWidth(450)
        self.tree.setStyleSheet('QTreeWidget {border:0;background:#f5f8fb;} QTreeWidget::item {padding:7px 3px;} QTreeWidget::item:selected {background:#dcebf7;color:#126780;}')
        self.toc.setStyleSheet('QListWidget {border:0;border-left:1px solid #d8e1eb;background:white;} QListWidget::item {padding:6px;color:#61758b;}')
        self.browser.document().setDefaultStyleSheet('body {color:#24364b;font-family:"Microsoft YaHei";font-size:11pt;} h1 {color:#123e56;font-size:22pt;} h2 {color:#136d92;font-size:15pt;margin-top:20px;} h3 {color:#24576b;} p,li {line-height:150%;} table {border-collapse:collapse;margin:14px 0;} th {background:#eaf2f7;} th,td {border:1px solid #cbdce7;padding:9px;} pre {background:#f1f5f9;padding:12px;} code {font-family:Consolas;color:#9b4b23;} a {color:#087d9f;} blockquote {color:#61758b;}')
        self.search.textChanged.connect(self.filter)
        self.tree.currentItemChanged.connect(self.choose)
        self.toc.currentRowChanged.connect(self.scroll_section)
        self.browser.anchorClicked.connect(self.open_link)
        self.copy.clicked.connect(self.copy_markdown)
        self.back.clicked.connect(lambda:self.go_history(-1));self.forward.clicked.connect(lambda:self.go_history(1))
        self.set_language('zh')

    def tr(self,zh,en):return en if self.language=='en' else zh

    def set_language(self,language):
        self.language=language;self.pages={};self.items={}
        blocked=self.tree.blockSignals(True);self.tree.clear()
        for _,zh,en,topics in TOPICS:
            group=QTreeWidgetItem(self.tree,[self.tr(zh,en)]);group.setFlags(group.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            font=group.font(0);font.setBold(True);group.setFont(0,font)
            for key,title_zh,title_en in topics:
                path=DOCS/language/(key+'.md')
                text=path.read_text(encoding='utf-8') if path.exists() else self.tr('# 文档暂缺','# Document unavailable')
                self.pages[key]=text
                item=QTreeWidgetItem(group,[self.tr(title_zh,title_en)]);item.setData(0,Qt.ItemDataRole.UserRole,key);self.items[key]=item
            group.setExpanded(True)
        self.tree.blockSignals(blocked)
        self.search.setPlaceholderText(self.tr('搜索章节或参数，例如 geo_x','Search topics or parameters, e.g. geo_x'))
        self.copy.setText(self.tr('复制 Markdown','Copy Markdown'));self.toc_label.setText(self.tr('本页目录','On this page'))
        self.back.setToolTip(self.tr('上一访问页','Previous visited page'));self.forward.setToolTip(self.tr('下一访问页','Next visited page'))
        self.empty.setText(self.tr('没有匹配的章节，请尝试参数名或其他关键词。','No matching topics. Try a parameter name or another keyword.'))
        self.show_topic(self.current_topic,record=False);self.filter(self.search.text())

    def choose(self,item,previous):
        if item:
            key=item.data(0,Qt.ItemDataRole.UserRole)
            if key:self.show_topic(key)

    def show_topic(self,key,record=True):
        if key not in self.pages:return
        if record and (not self.history or self.history[self.history_index]!=key):
            self.history=self.history[:self.history_index+1]+[key];self.history_index=len(self.history)-1
        elif not self.history:self.history=[key];self.history_index=0
        self.current_topic=key
        item=self.items[key];blocked=self.tree.blockSignals(True);self.tree.setCurrentItem(item);self.tree.blockSignals(blocked)
        self.breadcrumb.setText(item.parent().text(0)+'  /  '+item.text(0))
        self.browser.setMarkdown(self.pages[key]);self.format_document()
        self.browser.moveCursor(QTextCursor.MoveOperation.Start)
        self.positions=[];blocked=self.toc.blockSignals(True);self.toc.clear()
        block=self.browser.document().begin()
        while block.isValid():
            if block.blockFormat().headingLevel() in (2,3):
                self.toc.addItem(block.text());self.positions.append(block.position())
            block=block.next()
        self.toc.blockSignals(blocked)
        self.location.setText(self.tr('本机帮助 · ','Local help · ')+f'docs/help/{self.language}/{key}.md')
        self.back.setEnabled(self.history_index>0);self.forward.setEnabled(self.history_index<len(self.history)-1)

    def format_document(self):
        # Qt 的 Markdown 阅读器不应用全部 CSS；显式设置段落与表格间距。
        document=self.browser.document()
        block=document.begin()
        while block.isValid():
            cursor=QTextCursor(block);fmt=block.blockFormat()
            if fmt.headingLevel():
                fmt.setTopMargin(16 if fmt.headingLevel()>1 else 4);fmt.setBottomMargin(8)
            elif not cursor.currentTable() and not fmt.nonBreakableLines():
                fmt.setTopMargin(3);fmt.setBottomMargin(6)
                fmt.setLineHeight(135,QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            cursor.setBlockFormat(fmt);block=block.next()
        for frame in document.rootFrame().childFrames():
            if isinstance(frame,QTextTable):
                fmt=frame.format();fmt.setCellPadding(6);fmt.setCellSpacing(0)
                fmt.setBorderBrush(QColor('#cbdce7'));frame.setFormat(fmt)
                for row in range(frame.rows()):
                    for col in range(frame.columns()):
                        cell=frame.cellAt(row,col);cell_format=cell.format().toTableCellFormat()
                        cell_format.setBorder(.5)
                        cell_format.setBorderStyle(QTextFrameFormat.BorderStyle.BorderStyle_Solid)
                        cell_format.setBorderBrush(QColor('#cbdce7'))
                        if row==0:cell_format.setBackground(QColor('#eaf2f7'))
                        cell.setFormat(cell_format)

    def filter(self,text):
        query=text.strip().casefold();count=0
        for key,item in self.items.items():
            visible=not query or query in (item.text(0)+' '+self.pages[key]).casefold()
            item.setHidden(not visible);count+=visible
        for i in range(self.tree.topLevelItemCount()):
            group=self.tree.topLevelItem(i);group.setHidden(all(group.child(j).isHidden() for j in range(group.childCount())))
        self.empty.setVisible(count==0)

    def scroll_section(self,index):
        if 0<=index<len(self.positions):
            cursor=QTextCursor(self.browser.document());cursor.setPosition(self.positions[index])
            self.browser.setTextCursor(cursor);self.browser.ensureCursorVisible()

    def go_history(self,delta):
        index=self.history_index+delta
        if 0<=index<len(self.history):
            self.history_index=index;self.show_topic(self.history[index],record=False)

    def copy_markdown(self):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.pages[self.current_topic])

    def open_link(self,url):
        if url.scheme()=='help':self.show_topic(url.path())
        elif url.scheme() in ('http','https'):QDesktopServices.openUrl(url)

    def toPlainText(self):
        return '\n\n'.join(self.pages.values())
