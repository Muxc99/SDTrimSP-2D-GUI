"""Shared brush context actions for composition editing and sampling."""
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu,QDialog,QVBoxLayout,QDialogButtonBox,QLabel,QMessageBox
from case_model import fmt
from target_inputs import fractions,composition_field

def set_brush_table(widget,q):
    from PySide6.QtWidgets import QTableWidgetItem
    for i,v in enumerate(q):widget.setItem(0,i,QTableWidgetItem(fmt(v)))

def enable_protrusion_brush(owner,widget):
    if widget is getattr(getattr(owner,'target_editor',None),'brush_composition',None):owner.with_qu.setChecked(True)

def edit_brush(parent,owner,widget):
    from target_features import table,values
    tr=owner.raw_text;dialog=QDialog(parent);dialog.setWindowTitle(tr('画笔成分（原子分数）','Brush composition (atomic fractions)'));dialog.resize(650,170)
    layout=QVBoxLayout(dialog);q=table([owner.cell(owner.species,i,0) for i in range(owner.species.rowCount())],[values(widget)]);layout.addWidget(q)
    error=QLabel();layout.addWidget(error);box=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);layout.addWidget(box)
    box.button(QDialogButtonBox.StandardButton.Ok).setText(tr('确定','OK'));box.button(QDialogButtonBox.StandardButton.Cancel).setText(tr('取消','Cancel'))
    def accept():
        try:
            value=values(q);fractions(value,len(value));enable_protrusion_brush(owner,widget);set_brush_table(widget,value);dialog.accept()
        except ValueError as e:error.setText(str(e))
    box.accepted.connect(accept);box.rejected.connect(dialog.reject);dialog.exec()

def sample_composition(d,fig,point):
    if d.get('l_clust') and not d.get('l_clust_read'):
        raise ValueError('内置团簇位置未显示，不能吸取真实单元成分。 / Built-in cluster positions are not shown; actual cell composition cannot be sampled.')
    x,z=point;X=np.array([[x]]);Z=np.array([[z]])
    q=[]
    for i in range(len(d['symbol'])):
        value=composition_field(d,fig,X,Z,i)
        if np.ma.is_masked(value[0,0]):raise ValueError('此处没有材料 / No material here')
        q.append(float(value[0,0]))
    return q

def brush_menu(parent,owner,widget,d,fig,point):
    tr=owner.raw_text;menu=QMenu(parent);menu.setProperty('tooltipDelayMs',500);menu.setToolTipsVisible(True)
    def action(zh,en,slot):
        a=menu.addAction(tr(zh,en));a.triggered.connect(slot);return a
    action('画笔成分…','Brush composition…',lambda:edit_brush(parent,owner,widget))
    action('使用基底成分','Use substrate composition',lambda:set_brush_table(widget,d['qu_tar']))
    def sample():
        try:
            q=sample_composition(d,fig,point);enable_protrusion_brush(owner,widget);set_brush_table(widget,q)
        except ValueError as e:QMessageBox.information(parent,tr('吸取成分','Sample composition'),str(e))
    action('使用此处成分','Use composition here',sample)
    return menu
