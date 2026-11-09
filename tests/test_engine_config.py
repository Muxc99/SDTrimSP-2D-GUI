import os
from pathlib import Path
import tempfile
import unittest
import subprocess
from unittest.mock import patch
from engine_config import (EngineConfig,binary_kind,discover,normalize_tables,basic_errors,
                           required_tables,stage_tables,launch_command,probe_runtime,command_output)

class ExternalEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
    def tearDown(self):self.tmp.cleanup()
    def test_independent_locations_and_nested_discovery(self):
        exe=self.root/'installation'/'bin'/'target.exe';exe.parent.mkdir(parents=True);exe.write_bytes(b'\x7fELFtest')
        tables=self.root/'unrelated'/'tables';tables.mkdir(parents=True);(tables/'table1').write_text('placeholder')
        binaries,found=discover([self.root])
        self.assertEqual(binaries,[str(exe)]);self.assertEqual(found,[str(tables)])
        self.assertEqual(normalize_tables(tables/'table1'),tables)
        self.assertEqual(normalize_tables(tables.parent),tables)
        self.assertEqual(binary_kind(exe),'linux')
    def test_snapshot_does_not_touch_original_tables(self):
        tables=self.root/'data';tables.mkdir();(tables/'table1').write_bytes(b'original\n')
        run=self.root/'output';run.mkdir()
        copied=stage_tables(EngineConfig(tables=str(tables)),run)
        (copied/'table1').write_text('changed')
        self.assertEqual((tables/'table1').read_bytes(),b'original\n')
    def test_no_runner_required_and_missing_file_reported(self):
        exe=self.root/'bin'/'target.exe';exe.parent.mkdir();exe.write_bytes(b'\x7fELFtest')
        tables=self.root/'tables';tables.mkdir();(tables/'table1').write_text('table')
        config=EngineConfig(str(exe),str(tables),str(self.root/'results'))
        with patch('engine_config.shutil.which',return_value='wsl.exe'):
            self.assertEqual(basic_errors(config),[])
        exe.unlink();self.assertIn('executable', '\n'.join(basic_errors(config)))
    def test_results_cannot_be_written_inside_material_installation(self):
        tables=self.root/'tables';tables.mkdir();(tables/'table1').touch()
        config=EngineConfig(tables=str(tables),results=str(tables/'runs'))
        self.assertIn('separate results','\n'.join(basic_errors(config)))
    def test_model_specific_companion_tables(self):
        self.assertEqual(required_tables({'symbol':['Ar','W']}),['table1','table6a','table6b','table7_a3a4a5','table7_ck'])
        tables=required_tables({'symbol':['He','W'],'isbv':8,'isot':[1,0]})
        self.assertTrue({'table1a','table2','table4','table6b'}<=set(tables))
        self.assertEqual(required_tables({'symbol':['Ar'],'inel0':[1]}),['table1'])
    def test_source_and_script_cannot_be_launched(self):
        p=self.root/'target.exe';p.write_text('#!/bin/sh\n')
        self.assertEqual(binary_kind(p),'unsupported')
        self.assertIn('PE/ELF','\n'.join(basic_errors(EngineConfig(str(p)))))
    def test_wsl_stderr_cannot_contaminate_converted_path(self):
        result=subprocess.CompletedProcess([],0,b'/mnt/e/engine path',('wsl: proxy warning').encode('utf-16-le'))
        with patch('engine_config.subprocess.run',return_value=result):
            self.assertEqual(command_output(['wsl.exe']),'/mnt/e/engine path')
    @unittest.skipUnless(os.name=='nt','Windows WSL command construction')
    def test_paths_are_arguments_not_interpolated_shell(self):
        exe=self.root/'engine space'/'target.exe';exe.parent.mkdir();exe.write_bytes(b'\x7fELFtest')
        config=EngineConfig(str(exe),distribution='Another distro')
        with patch('engine_config.linux_path',side_effect=['/mnt/f/case with space','/mnt/e/engine $(literal)']):
            program,args=launch_command(config,self.root/'case')
        self.assertEqual(program,'wsl.exe');self.assertEqual(args[:2],['-d','Another distro'])
        self.assertEqual(args[-2:],['/mnt/f/case with space','/mnt/e/engine $(literal)'])
        self.assertNotIn('$(literal)',args[-4])

if __name__=='__main__':unittest.main()
