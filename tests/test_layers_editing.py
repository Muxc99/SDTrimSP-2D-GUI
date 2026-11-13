import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from PySide6.QtCore import QSettings
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication,QMessageBox
from case_model import parse_layers,inspect_input
from layer_editor import render_layers,LayerDialog
from input_editing import required_input_files

class LayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_round_trip_and_invalid_composition(self):
        rows=[(1000.,0.,[0.,1.]),(0.,-100.,[.3,.7])]
        self.assertEqual(parse_layers(render_layers(rows,2),2),rows)
        for bad in [[(0.,-10.,[.1,.2])],[(0.,1.,[0.,1.])],[(0.,-10.,[0.,1.]),(-11.,-20.,[0.,1.])]]:
            with self.assertRaises(ValueError):render_layers(bad,2)

    def test_editor_and_file_lifecycle(self):
        from app import Window
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);settings=QSettings(str(root/'settings.ini'),QSettings.Format.IniFormat)
            settings.setValue('setup/v090_seen',True);w=Window(settings=settings)
            try:
                dialog=LayerDialog(w);page=dialog.pages[0]
                page.enabled.setChecked(True);page.add_layer();self.assertEqual(len(page.rows()),2)
                page.table.setCurrentCell(1,0);page.remove_layer();self.assertEqual(len(page.rows()),1)
                dialog.apply();self.assertFalse(dialog.error.text());self.assertEqual(w.collect()[0]['iq0'],1.)
                folder=w.write_case(root/'case');w.load_case(folder)
                name='initial_composition.inp';editor=w.aux_editors[name]
                editor.moveCursor(QTextCursor.MoveOperation.End);editor.insertPlainText('! comment\n')
                self.assertIn(name,w.raw_pending);self.assertTrue(w.apply_raw_edits())
                self.assertIs(w.aux_editors[name],editor);self.assertTrue(editor.document().isUndoAvailable())
                w.save_current();self.assertIs(w.aux_editors[name],editor)
                self.assertTrue(editor.document().isUndoAvailable())
                editor.undo();self.assertIn(name,w.raw_pending);self.assertTrue(w.apply_raw_edits())
                editor.moveCursor(QTextCursor.MoveOperation.End);editor.insertPlainText('bad layer trailer\n')
                w.discard_raw_edits();self.assertNotIn('bad layer trailer',editor.toPlainText())
                w.set_extra_values({'iq0':'0'});w.refresh();w.aux_tabs.setCurrentWidget(editor)
                with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes):w.remove_input_file()
                self.assertNotIn(name,w.current_files());self.assertIn(name,w.removed_files)
                # Applying a later tri.inp edit must not resurrect a removed disk file.
                w.tri_preview.moveCursor(QTextCursor.MoveOperation.End);w.tri_preview.insertPlainText('\n')
                self.assertTrue(w.apply_raw_edits());self.assertNotIn(name,w.current_files())
                from case_saving import save_input_files
                _,backup=save_input_files(w)
                self.assertFalse((folder/name).exists());self.assertTrue((backup/name).is_file())
                self.assertTrue((folder/'tri.inp').is_file());self.assertTrue((folder/'stop_run.inp').is_file())
                dialog.close()
            finally:w.dirty=False;w.close();w.deleteLater()

    def test_required_files_follow_features(self):
        data={'case_geo':25,'case_e0':1,'case_alpha':4,'iq0':1,'iq0_surf':0}
        required=required_input_files(data)
        self.assertTrue({'rauh.inp','energy.inp','angle.inp','initial_composition.inp','tri.inp','stop_run.inp'}<=required)
        self.assertNotIn('initial_composition_surf.inp',required)
        data['isbv']=6;self.assertIn('mat_surfb.inp',required_input_files(data))

if __name__=='__main__':unittest.main()
