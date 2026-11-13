import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication,QTableWidgetItem
from new_case import initial_inputs
from case_model import inspect_input,Figure,validate,parse_layers
from target_inputs import *

def sample(geometry=26):
    files=initial_inputs('Synthetic target','He','W',100.,50.,10.,10.,1000.,0.,100.,geometry=geometry)
    _,d=inspect_input(files['tri.inp']);d['_files']={k:v for k,v in files.items() if k!='tri.inp'}
    return d,Figure.parse(files['fig.inp'],2) if geometry==26 else None

class FormatTests(unittest.TestCase):
    def test_mesh_retains_grid_and_block_boundaries(self):
        d,fig=sample();d.update(geo_x=200.,geo_z=-200.,geo_dx=25.,geo_dz=25.)
        fig.rows=[[-175.,-150.,0.,75.,0.,1.],[-100.,-75.,0.,47.,0.,1.]]
        xx,zz=composition_mesh(d,fig)
        for edge in range(-200,201,25):self.assertIn(edge,xx)
        for edge in range(-200,76,25):self.assertIn(edge,zz)
        self.assertIn(47.,zz)
        X,Z=np.meshgrid((xx[:-1]+xx[1:])/2,(zz[:-1]+zz[1:])/2)
        c=composition_field(d,fig,X,Z,1)
        for row in fig.rows:
            left,right,bottom,top=row[:4]
            filled=(X>=left)&(X<right)&(Z>=bottom)&(Z<top)
            self.assertFalse(np.ma.getmaskarray(c)[filled].any())
        self.assertTrue(np.ma.getmaskarray(c)[(X>=-150)&(X<-125)&(Z>0)].all())

    def test_local_indices_and_dimensions(self):
        d,_=sample();rows={(1,1):[0.,1.],(10,8):[.5,.5]}
        self.assertEqual(parse_local(render_local(rows,d),d),rows)
        text=render_local(rows,d)
        for bad in [text.replace('2 10 5','2 12 5'),text.replace('10 8','11 8'),text.replace('0.5 0.5','0.2 0.5'),text.replace('10 8','1 1')]:
            with self.assertRaises(ValueError):parse_local(bad,d)
        self.assertEqual(grid_shape(d),(10,5))

    def test_templates_and_distribution_limits(self):
        d,_=sample()
        for name in ('energy.inp','angle.inp'):self.assertGreaterEqual(len(parse_distribution(template(name,d),name=='angle.inp')),2)
        self.assertEqual(len(parse_matrix(template('mat_surfb.inp',d),d['symbol'])),2)
        for text,angle in [('header\n2\n1 1\n2 1',False),('header\n0 1\n91 1',True),('header\n1 0\n2 0',False),('header\n2 1\n1 1',False),('header\n'+'\n'.join(f'{i+1} 1' for i in range(101)),False)]:
            with self.assertRaises(ValueError):parse_distribution(text,angle)

    def test_precedence(self):
        from layer_editor import render_layers
        d,fig=sample();fig.rows=[[-10.,0.,0.,10.,0.,1.]]
        d.update(iq0=1,iq0_surf=1)
        d['_files']['initial_composition.inp']=render_layers([(20.,-50.,[1.,0.])],2)
        d['_files']['initial_composition_surf.inp']=render_layers([(0.,-3.,[.4,.6])],2)
        X,Z=np.meshgrid([-5.,5.],[-25.,2.,9.]);c=composition_field(d,fig,X,Z,0)
        self.assertEqual(c[0,0],1.) # Bulk.
        self.assertEqual(c[1,0],0.) # Block is not repainted by bulk.
        self.assertEqual(c[2,0],.4) # Surface overrides block.
        self.assertTrue(c.mask[1,1]) # Void.
        d.update(l_clust=True,l_clust_read=True)
        d['_files'][LOCAL_FILE]=render_local({(5,6):[.7,.3]},d)
        c=composition_field(d,fig,X,Z,0);self.assertEqual(c[2,0],.7) # Local last.

    def test_profile_conversion_and_seam(self):
        d,_=sample(24);text=profile_from_columns('-5 0\n0 1\n5 0',d,10)
        self.assertEqual(Profile.parse(text).rows,[[0.,0.],[50.,10.],[100.,0.]])
        d['_files']['rauh.inp']=text
        self.assertFalse(validate_auxiliary(d)[0])
        with self.assertRaises(ValueError):profile_from_columns('0 1\n-5 1\n5 0',d,10)
        with self.assertRaises(ValueError):profile_from_columns('-5 -5\n5 0',d,10)

    def test_cosine_periodicity_matches_engine_preflight_rule(self):
        from case_model import Profile
        for mode in (24,25,27):
            d,_=sample(mode);d['geo_x']=225.;d['geo_dx']=25.;d['pr_amp']=10.;d['pr_wl']=20.
            if mode==24:d['_files']['rauh.inp']=Profile([[0.,0.],[450.,0.]]).render()
            elif mode==25:d['_files']['rauh.inp']=Profile([[-225.,0.],[225.,0.]]).render()
            errors,_,_=validate(d,None)
            periodic=[e for e in errors if 'pr_wl' in e and '总宽' in e]
            self.assertEqual(len(periodic),1,(mode,errors))
            self.assertIn('450',periodic[0]);self.assertIn('22.5',periodic[0]);self.assertIn('pr_wl',periodic[0])
            from i18n import translated
            english=translated(periodic[0],'en')
            self.assertIn('must be an integer',english);self.assertNotIn('Suggested',english)
            d['pr_wl']=25.
            errors,_,_=validate(d,None)
            self.assertFalse(any('总宽' in e and 'pr_wl' in e for e in errors),(mode,errors))
        d,_=sample(25);d.update(geo_x=225.,geo_dx=25.,pr_amp=.001,pr_wl=20.)
        self.assertFalse(any('pr_amp>0' in e and 'pr_wl' in e for e in validate(d,None)[0]))

    def test_compound_expansion_and_special_geometry(self):
        d,_=sample(20);d['symbol']=['He','Ta','O'];d['ncp']=3;d['qu_tar']=[0.,.4,.6]
        d['dns_0']=[-1.]*3;d.update(l_two_comp=True,two_comp='Ta2O5')
        self.assertFalse(validate_auxiliary(d)[0])
        d['iq0']=1;self.assertTrue(any('Compound expansion' in e for e in validate_auxiliary(d)[0]))
        d['case_geo']=28;xx,zz,mask,r=cylinder_schematic(d)
        self.assertEqual(r,2510);self.assertLessEqual(mask.size,600*600)

class GuiFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def window(self,tmp):
        from app import Window
        settings=QSettings(str(Path(tmp)/'settings.ini'),QSettings.Format.IniFormat);settings.setValue('setup/v090_seen',True)
        return Window(settings=settings)

    def test_species_material_properties_and_qumax_are_editable(self):
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                self.assertFalse(w.species.isColumnHidden(5))
                self.assertEqual(w.species.horizontalHeaderItem(5).text(),'浓度上限')
                for row in range(w.species.rowCount()):
                    for col,value in zip((6,7,8),('183.84','19.3','0.063')):
                        w.set_cell(w.species,row,col,value)
                w.set_cell(w.species,0,6,'111.12345')
                w.set_cell(w.species,0,5,'0.7')
                data,fig=w.collect()
                self.assertEqual(data['qu_max'][0],0.7)
                self.assertEqual(data['_material_overrides'][0],
                    {'symbol':'Ar','mass':111.12345,'density':19.3,'atomic_density':0.063})
                tri,_=w.render_inputs(data,fig)
                self.assertNotIn('111.12345',tri)
                _,saved=inspect_input(tri)
                self.assertEqual(saved['qu_max'][0],0.7)
                w.ui_language='en';w.interface_language.apply(w)
                self.assertEqual(w.species.horizontalHeaderItem(6).text(),'Atomic mass u')
                self.assertEqual(w.species.horizontalHeaderItem(5).text(),'Concentration limit (engine)')
            finally:
                w.dirty=False
                w.close()

    def test_periodicity_error_appears_in_drawing_and_check_panels(self):
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                files=initial_inputs('Periodic check','He','W',100.,50.,10.,10.,1000.,0.,100.,geometry=25)
                from case_model import Profile
                files['rauh.inp']=Profile([[-225.,0.],[225.,0.]]).render()
                self.assertTrue(w.load_case(None,overrides=files))
                w.loading=True
                w.edits['geo_x'].setText('225');w.edits['geo_dx'].setText('25')
                w.edits['pr_amp'].setText('10');w.edits['pr_wl'].setText('20')
                w.loading=False;w.refresh()
                check=w.check_output.toPlainText();status=w.target_editor.validation_label.text()
                self.assertIn('22.5',check);self.assertIn('22.5',status)
                self.assertIn('pr_wl',check);self.assertIn('pr_wl',status)
                self.assertFalse(w.run_button.isEnabled())
                w.ui_language='en';w.refresh()
                self.assertIn('periodicity error',w.check_output.toPlainText())
                self.assertIn('periodicity error',w.target_editor.validation_label.text())
            finally:w.dirty=False;w.close();w.deleteLater()

    def test_profile_node_manual_coordinates_are_off_grid_and_undoable(self):
        from case_model import Profile
        from substrate_profile import ProfileEditError
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                for mode in (24,25):
                    files=initial_inputs('Profile','He','W',100.,50.,10.,10.,1000.,0.,100.,geometry=mode)
                    rows=[[0.,0.],[37.5,12.25],[200.,0.]] if mode==24 else [[-100.,0.],[-12.5,17.75],[100.,0.]]
                    files['rauh.inp']=Profile(rows).render()
                    self.assertTrue(w.load_case(None,overrides=files))
                    editor=w.target_editor.profile_editor
                    editor.set_node_position(1,-13.25,19.375)
                    saved=Profile.parse(w.current_files()['rauh.inp']).rows
                    expected_x=36.75 if mode==24 else -13.25
                    self.assertEqual(saved[1],[expected_x,19.375])
                    self.assertTrue(editor.undo_stack)
                    editor.undo();restored=Profile.parse(w.current_files()['rauh.inp']).rows
                    self.assertEqual(restored[1][1],12.25 if mode==24 else 17.75)
                    current=w.current_files()['rauh.inp']
                    with self.assertRaises(ProfileEditError):editor.set_node_position(1,1000.,19.)
                    self.assertEqual(w.current_files()['rauh.inp'],current)
            finally:w.dirty=False;w.close();w.deleteLater()

    def test_profile_drag_snaps_only_when_checkbox_enabled(self):
        from types import SimpleNamespace
        from case_model import Profile
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                files=initial_inputs('Profile','He','W',100.,50.,10.,10.,1000.,0.,100.,geometry=25)
                files['rauh.inp']=Profile([[-100.,0.],[-20.,10.],[100.,0.]]).render()
                self.assertTrue(w.load_case(None,overrides=files))
                editor=w.target_editor.profile_editor
                self.assertFalse(editor.snap_grid.isChecked())
                before=[r[:] for r in editor.rows]
                editor.drag={'index':1,'before':before,'rows':[r[:] for r in before]}
                event=SimpleNamespace(inaxes=w.target_editor.ax,xdata=-13.2,ydata=18.2)
                editor.on_motion(event)
                self.assertAlmostEqual(editor.drag['rows'][1][0],-13.2)
                self.assertAlmostEqual(editor.drag['rows'][1][1],18.2)
                editor.snap_grid.setChecked(True)
                editor.drag={'index':1,'before':before,'rows':[r[:] for r in before]}
                editor.on_motion(event)
                self.assertEqual(editor.drag['rows'][1],[-10.,20.])
                editor.cancel_drag()
            finally:w.dirty=False;w.close();w.deleteLater()

    def test_layers_are_embedded_and_apply_atomically(self):
        from target_features import TargetFeaturesDialog
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                dlg=TargetFeaturesDialog(w)
                self.assertEqual(dlg.layer_tabs.count(),2)
                page=dlg.layer_pages[0];page.enabled.setChecked(True);page.add_layer()
                self.assertNotIn('initial_composition.inp',w.current_files())
                dlg.apply();self.assertEqual(len(parse_layers(w.current_files()['initial_composition.inp'],len(dlg.data['symbol']))),2)
                self.assertEqual(w.collect()[0]['iq0'],1)
                before=w.current_files().copy();page.table.item(0,2).setText('invalid')
                dlg.apply();self.assertEqual(w.current_files(),before);dlg.close()
            finally:w.dirty=False;w.close();w.deleteLater()

    def stroke(self,w,start,end=None):
        from types import SimpleNamespace
        e=w.target_editor;e.set_tool('substrate_brush');f=w.factor
        def event(point):return SimpleNamespace(dblclick=False,button=1,inaxes=e.ax,xdata=point[0]/f,ydata=point[1]/f,x=100,y=100)
        e.on_press(event(start))
        if end is not None:e.on_motion(event(end))
        e.on_release(event(end or start))

    def test_local_and_models_apply_and_save(self):
        from target_features import TargetFeaturesDialog
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                d,_=w.collect();self.stroke(w,(-d['geo_x']+d['geo_dx']/2,d['geo_z']+d['geo_dz']/2))
                self.assertTrue(w.collect()[0]['l_clust_read'])
                folder=w.write_case(Path(tmp)/'output');self.assertTrue((folder/LOCAL_FILE).is_file())
                w.load_case(folder);data,_=w.collect();self.assertEqual(parse_local(w.current_files()[LOCAL_FILE],data),{(1,1):d['qu_tar']})
                dlg=TargetFeaturesDialog(w);self.assertFalse(hasattr(dlg,'local'))
                dlg.cluster.setChecked(True)
                for i,v in enumerate(d['qu_tar']):dlg.cluster_q.setItem(0,i,QTableWidgetItem(str(v)))
                dlg.count.setCurrentText('4');dlg.apply();data,_=w.collect()
                self.assertTrue(data['l_clust']);self.assertFalse(data['l_clust_read']);self.assertEqual(data['n_clust'],4)
                dlg.close()
            finally:w.dirty=False;w.close();w.deleteLater()

    def test_species_dependencies_do_not_silently_reinterpret(self):
        from layer_editor import render_layers
        from species_dependencies import plan_species_change,commit_species_plan
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                d,_=w.collect();name='initial_composition.inp'
                w.set_auxiliary_file(name,render_layers([(0.,-100.,d['qu_tar'])],len(d['symbol'])))
                w.add_species();self.assertEqual(len(parse_layers(w.current_files()[name],len(d['symbol'])+1)[0][2]),len(d['symbol'])+1)
                w.set_cell(w.species,w.species.rowCount()-1,0,'Fe');w.refresh()
                w.remove_species(w.species.rowCount()-1);self.assertEqual(len(parse_layers(w.current_files()[name],len(d['symbol']))[0][2]),len(d['symbol']))
                index=next(i for i,q in enumerate(d['qu_tar']) if q>0)
                with self.assertRaises(ValueError):plan_species_change(w,'remove',index)
                w.set_extra_values({'e_displ':', '.join('20' for _ in d['symbol'])})
                with self.assertRaises(ValueError):plan_species_change(w,'add')
            finally:w.dirty=False;w.close();w.deleteLater()

    def test_added_substrate_species_keeps_defaults_and_block_material(self):
        from species_dependencies import plan_species_change,commit_species_plan
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                for explicit_density in (False,True):
                    files=initial_inputs('Mixed substrate','Ar','W',100.,50.,10.,10.,1000.,0.,100.,geometry=26)
                    files['fig.inp']=Figure(0,1,[[-10.,0.,0.,10.,0.,1.]]).render()
                    if explicit_density:
                        from case_model import Namelist
                        files['tri.inp']=Namelist(files['tri.inp']).patch({'dns_0':'-1, 0.063','qu_clust':'0, 0'})
                    self.assertTrue(w.load_case(None,overrides=files))
                    w.add_species()
                    commit_species_plan(w,plan_species_change(w,'replace',2,'Si'))
                    w.loading=True
                    w.set_cell(w.species,2,0,'Si')
                    w.set_cell(w.species,1,4,'0.5');w.set_cell(w.species,2,4,'0.5')
                    w.loading=False;w.refresh()
                    d,fig=w.collect()
                    self.assertEqual(d['dns_0'],[-1.,0.063 if explicit_density else -1.,-1.])
                    self.assertEqual(d['qu_clust'],[0.,0.,0.])
                    self.assertEqual(fig.rows[0][4:],[0.,1.,0.])
                    self.assertFalse(validate(d,fig)[0],w.check_output.toPlainText())
                    tri,fig_text=w.render_inputs(d,fig)
                    self.assertTrue(w.load_case(None,overrides={'tri.inp':tri,'fig.inp':fig_text}))
                    restored,blocks=w.collect()
                    self.assertEqual(restored['qu_tar'],[0.,.5,.5])
                    self.assertFalse(validate(restored,blocks)[0])
                    w.loading=True
                    w.set_cell(w.species,1,4,'1');w.set_cell(w.species,2,4,'0')
                    w.loading=False;w.remove_species(2);w.refresh()
                    self.assertEqual(len(w.collect()[0]['dns_0']),2)
                    self.assertFalse(validate(*w.collect())[0])
                # Never conceal an explicitly supplied malformed density array.
                w.set_extra_values({'dns_0':'-1'})
                self.assertTrue(any('dns_0' in e for e in validate(*w.collect())[0]))
            finally:w.dirty=False;w.close();w.deleteLater()

    def test_composition_tables_open_their_own_right_click_editor(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                e=w.target_editor
                for table in (e.base_composition,e.brush_composition,e.substrate_composition):
                    with patch('brush_menu.edit_brush') as edit:
                        menu=e.composition_context_menu(table)
                        actions=[a for a in menu.actions() if a.text() in ('编辑材料成分…','Edit material composition…')]
                        self.assertEqual(len(actions),1)
                        actions[0].trigger();edit.assert_called_once_with(e,w,table)
                        if table is e.brush_composition:
                            self.assertTrue(any('使用基底成分' in a.text() or 'Use substrate composition' in a.text() for a in menu.actions()))
                        else:
                            self.assertFalse(any('使用基底成分' in a.text() or 'Use substrate composition' in a.text() for a in menu.actions()))
            finally:w.dirty=False;w.close();w.deleteLater()

    def test_brush_context_menu_contains_only_three_composition_actions(self):
        from unittest.mock import patch
        from brush_menu import brush_menu
        from PySide6.QtWidgets import QDialog,QDialogButtonBox,QMenu,QTableWidget
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                e=w.target_editor;d,fig=w.collect()
                for table in (e.brush_composition,e.substrate_composition):
                    menu=brush_menu(e,w,table,d,fig,(0.,0.))
                    self.assertEqual([a.text() for a in menu.actions()],['画笔成分…','使用基底成分','使用此处成分'])
                menu=brush_menu(e,w,e.brush_composition,d,fig,(0.,0.))
                def accept_dialog(dialog):
                    table=dialog.findChild(QTableWidget);table.item(0,0).setText('0.25');table.item(0,1).setText('0.75')
                    dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
                    return dialog.result()
                with patch.object(QDialog,'exec',accept_dialog):menu.actions()[0].trigger()
                self.assertEqual([e.brush_composition.item(0,i).text() for i in range(2)],['0.25','0.75'])
                e.brush_composition.item(0,0).setText('0')
                e.brush_composition.item(0,1).setText('1')
                menu.actions()[1].trigger()
                self.assertEqual([e.brush_composition.item(0,i).text() for i in range(2)],['0','1'])
                with patch('brush_menu.sample_composition',return_value=[1.,0.]):
                    menu.actions()[2].trigger()
                self.assertEqual([e.brush_composition.item(0,i).text() for i in range(2)],['1','0'])
            finally:w.dirty=False;w.close();w.deleteLater()

    def test_invalid_candidate_does_not_mutate_owner(self):
        from target_features import TargetFeaturesDialog
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                dlg=TargetFeaturesDialog(w);before=w.render_inputs(*w.collect());files=w.current_files().copy()
                enabled,edit,*_=dlg.documents['energy.inp'];enabled.setChecked(True);edit.setPlainText('header\ninvalid')
                dlg.apply();self.assertIn('energy.inp',dlg.error.text());self.assertEqual(w.render_inputs(*w.collect()),before);self.assertEqual(w.current_files(),files)
                dlg.close()
            finally:w.dirty=False;w.close();w.deleteLater()

    def test_brush_right_click_and_local_undo(self):
        from target_features import values
        from brush_menu import brush_menu
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                e=w.target_editor;d,_=w.collect();before=e.rows()
                e.substrate_composition.setItem(0,0,QTableWidgetItem('1'))
                e.substrate_composition.setItem(0,1,QTableWidgetItem('0'))
                self.stroke(w,(-d['geo_x']+d['geo_dx']/2,d['geo_z']+d['geo_dz']/2))
                self.assertEqual(parse_local(w.current_files()[LOCAL_FILE],d)[1,1],[1.,0.]);self.assertEqual(e.rows(),before)
                e.undo();self.assertNotIn(LOCAL_FILE,w.current_files());self.assertFalse(w.collect()[0]['l_clust'])
                e.redo();self.assertIn((1,1),parse_local(w.current_files()[LOCAL_FILE],d))
                saved=w.current_files()[LOCAL_FILE]
                self.stroke(w,(0.,d['geo_dz']/2));self.assertEqual(w.current_files()[LOCAL_FILE],saved)
                from unittest.mock import patch
                from PySide6.QtWidgets import QMenu
                event=SimpleNamespace(dblclick=False,button=3,inaxes=e.ax,xdata=0.,ydata=-10.)
                with patch.object(QMenu,'popup'):e.on_press(event)
                self.assertTrue(any('画笔成分' in a.text() for a in e.context_menu.actions()))
                self.assertFalse(any('选择画笔元素' in a.text() for a in e.context_menu.actions()))
                self.assertEqual(e.rows(),before)
            finally:w.dirty=False;w.close();w.deleteLater()

    def test_distribution_switches_profile_and_english(self):
        from target_features import TargetFeaturesDialog
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                w.ui_language='en';dlg=TargetFeaturesDialog(w);self.assertEqual(dlg.windowTitle(),'Target features')
                for name,(enabled,*_) in dlg.documents.items():enabled.setChecked(True)
                dlg.apply();d,_=w.collect()
                self.assertEqual((d['case_e0'],d['case_alpha'],d['isbv']),(1,4,6),dlg.error.text())
                for name,(enabled,*_) in dlg.documents.items():enabled.setChecked(False)
                dlg.apply();d,_=w.collect();self.assertEqual((d['case_e0'],d['case_alpha'],d['isbv']),(0,0,1));self.assertIn('energy.inp',w.current_files())
                dlg.close()
                files=initial_inputs('Profile','He','W',100.,50.,10.,10.,1000.,0.,100.,geometry=24)
                w.load_case(None,overrides=files)
                dlg=TargetFeaturesDialog(w);dlg.shape.setCurrentIndex(2);dlg.generate_profile();dlg.apply()
                self.assertGreater(len(Profile.parse(w.current_files()['rauh.inp']).rows),2,dlg.error.text());dlg.close()
            finally:w.dirty=False;w.close();w.deleteLater()

    def test_local_painting_on_all_supported_geometries(self):
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                for mode in (10,20,24,25,26,27):
                    files=initial_inputs('Synthetic','He','W',100.,50.,10.,10.,1000.,0.,100.,geometry=mode)
                    self.assertTrue(w.load_case(None,overrides=files))
                    self.stroke(w,(-45.,-45.));d,_=w.collect()
                    self.assertTrue(d['l_clust_read'],mode);self.assertIn((1,1),parse_local(w.current_files()[LOCAL_FILE],d))
                    if mode in (24,25):
                        self.assertIsNone(w.target_editor.profile_editor.drag)
            finally:w.dirty=False;w.close();w.deleteLater()

    def test_layer_default_is_surface_not_beam_height(self):
        from target_features import TargetFeaturesDialog
        from layer_editor import render_layers
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                files=initial_inputs('Profile','He','W',400.,200.,25.,25.,100.,0.,500.,geometry=25)
                files['rauh.inp']=Profile([[-200.,0.],[-25.,50.],[150.,50.],[200.,0.]]).render()
                w.load_case(None,overrides=files)
                dlg=TargetFeaturesDialog(w);self.assertEqual(dlg.layer_pages[0].rows()[0][0],50.)
                self.assertEqual(w.collect()[0]['z_start'],500.);dlg.close()
                w.set_auxiliary_file('initial_composition.inp',render_layers([(500.,-200.,[0.,1.])],2))
                dlg=TargetFeaturesDialog(w);self.assertEqual(dlg.layer_pages[0].rows()[0][0],500.);dlg.close()
            finally:w.dirty=False;w.close();w.deleteLater()

    def test_substrate_brush_preserves_blocks_and_erases_only_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            w=self.window(tmp)
            try:
                files=initial_inputs('Blocks','He','W',100.,50.,10.,10.,1000.,0.,100.,geometry=26)
                files['fig.inp']=Figure(0,1,[[-10.,0.,0.,10.,0.,1.]]).render()
                w.load_case(None,overrides=files);e=w.target_editor;before=e.rows()
                self.stroke(w,(-5.,5.));self.assertNotIn(LOCAL_FILE,w.current_files())
                self.stroke(w,(-5.,-5.));saved=w.current_files()[LOCAL_FILE]
                self.assertEqual(e.rows(),before)
                e.substrate_brush.erasing=True;self.stroke(w,(-5.,-5.))
                self.assertEqual(parse_local(w.current_files()[LOCAL_FILE],w.collect()[0]),{})
                e.undo();self.assertEqual(w.current_files()[LOCAL_FILE],saved);self.assertEqual(e.rows(),before)
                from target_features import TargetFeaturesDialog
                dlg=TargetFeaturesDialog(w);dlg.apply();self.assertTrue(w.collect()[0]['l_clust_read']);dlg.close()
                e.substrate_brush.erasing=False;w.unit.setCurrentText('nm');self.stroke(w,(5.,-5.))
                self.assertEqual(e.rows(),before);self.assertEqual(len(parse_local(w.current_files()[LOCAL_FILE],w.collect()[0])),2)
            finally:w.dirty=False;w.close();w.deleteLater()

if __name__=='__main__':unittest.main()
