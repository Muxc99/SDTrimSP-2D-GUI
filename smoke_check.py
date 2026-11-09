"""Noninteractive release startup check with isolated settings and synthetic inputs."""
from pathlib import Path
import hashlib
import json
from PySide6.QtCore import QEventLoop,QTimer
from PySide6.QtWidgets import QApplication,QDialogButtonBox
from engine_dialog import EngineDialog,diagnostic_info
from engine_config import EngineConfig
from element_picker import ElementDialog

def verify_window(window,scratch,report_path):
    assert window.windowTitle()=='SDTrimSP-2D_GUI v0.9.2'
    assert not window.run_button.isEnabled()
    assert window.save_button.isEnabled()
    assert window.open_button.icon().cacheKey()!=window.engine_button.icon().cacheKey()
    picker=ElementDialog('W',window)
    assert 'W' in picker.by_symbol and picker.by_symbol['W'].mass is None
    picker.select_element(74);assert picker.entries.item(0,0).text()=='W'
    picker.close()
    case=window.write_case(scratch/'synthetic')
    assert (case/'tri.inp').is_file()
    info=diagnostic_info(window)
    assert info['gui_version']=='0.9.2' and info['engine_format']=='missing'
    assert all('path' not in key for key in info)
    dialog=EngineDialog(window)
    assert set(dialog.fields)=={'executable','tables','results','distribution','runtime'}
    dialog.close()
    window.language.setCurrentIndex(window.language.findData('en'));QApplication.processEvents()
    dialog=EngineDialog(window)
    assert dialog.windowTitle()=='Engine and data settings'
    dialog.close()
    window.showNormal();window.resize(1430,920);QApplication.processEvents()
    window.grab().save(str(report_path.with_suffix('.png')))
    checks=[
        'startup without engine','periodic-table editing without material data','save synthetic case',
        'independent engine/tables/results fields','distinct open/settings icons','English settings',
        'private diagnostic payload','bundled help and preview rendering']
    assert (Path(__file__).parent/'docs/help/en/running.md').is_file()
    # Optional local integration fixture. Never ship the fixture or its licensed data.
    fixture=report_path.with_suffix('.engine.json')
    if fixture.is_file():
        verify_external(window,json.loads(fixture.read_text(encoding='utf-8')),report_path)
        checks+=['external engine preflight','external engine one-history run',
                 'separate tables and results','completion and result loading',
                 'original input and material table unchanged']
    native=report_path.with_suffix('.native.json')
    if native.is_file():
        from windows_runtime_check import verify_native
        verify_native(window,json.loads(native.read_text(encoding='utf-8')))
        checks+=['Windows external DLL preflight','Windows child process DLL path',
                 'frozen DLL isolation','missing transitive DLL diagnostic']
    return {'ok':True,'gui':'0.9.2','frozen':info['frozen'],'checks':checks}


def verify_external(window,fixture,report_path):
    config=EngineConfig(**fixture['engine'])
    source=Path(fixture['case'])
    fingerprint=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    originals=[source/'tri.inp',Path(config.tables)/'table1']
    before=[fingerprint(p) for p in originals]
    window.engine_config=config;window.configure_material_table(config.tables)
    window.load_case(source)
    data,_=window.collect()
    assert data['maxhist']==1, 'Integration fixture must use exactly one history.'
    errors=[]
    def confirm():
        modal=QApplication.activeModalWidget()
        box=modal.findChild(QDialogButtonBox) if modal else None
        if not box or not box.button(QDialogButtonBox.StandardButton.Ok).isEnabled():
            errors.append('External engine preflight failed.')
            if modal:modal.reject()
        else:modal.accept()
    QTimer.singleShot(10,confirm);window.run_case()
    assert not errors, errors
    loop=QEventLoop();poll=QTimer();poll.setInterval(20)
    poll.timeout.connect(lambda:loop.quit() if window.process is None else None)
    deadline=QTimer();deadline.setSingleShot(True);deadline.timeout.connect(loop.quit)
    poll.start();deadline.start(30000)
    if window.process is not None:loop.exec()
    poll.stop();deadline.stop()
    if window.process is not None:
        window.process.kill();window.process.waitForFinished(3000)
        raise AssertionError('External engine integration test timed out.')
    assert window.run_progress.state=='completed',window.log.toPlainText()[-3000:]
    assert [fingerprint(p) for p in originals]==before
    assert (window.run_directory/'_tables/table1').is_file()
    window.results_view.load_directory(window.run_directory)
    window.tabs.setCurrentWidget(window.results_view);QApplication.processEvents()
    window.grab().save(str(report_path.with_name(report_path.stem+'-results.png')))
