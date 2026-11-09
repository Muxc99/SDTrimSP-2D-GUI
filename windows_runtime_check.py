"""Optional release integration check, using locally built synthetic DLL fixtures."""
from pathlib import Path
from PySide6.QtCore import QProcess,QProcessEnvironment,QEventLoop,QTimer
from engine_config import EngineConfig,probe_runtime,engine_environment,external_dll_search


def verify_native(window,fixture):
    config=EngineConfig(executable=fixture['executable'],runtime=fixture.get('runtime',''))
    assert 'checked' in probe_runtime(config)
    process=QProcess(window)
    env=QProcessEnvironment()
    for key,value in engine_environment(config).items():env.insert(key,value)
    process.setProcessEnvironment(env);process.setWorkingDirectory(str(Path(fixture['executable']).parent))
    with external_dll_search():
        process.start(config.executable,[])
        assert process.waitForStarted(3000),process.errorString()
    loop=QEventLoop();process.finished.connect(loop.quit)
    timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(loop.quit);timer.start(10000)
    if process.state()!=QProcess.ProcessState.NotRunning:loop.exec()
    timer.stop()
    if process.state()!=QProcess.ProcessState.NotRunning:
        process.kill();process.waitForFinished(2000);raise AssertionError('Native DLL fixture timed out.')
    assert process.exitCode()==0,(process.exitCode(),bytes(process.readAllStandardError()))
    missing=Path(fixture['dependency']);renamed=missing.with_suffix('.held')
    missing.rename(renamed)
    try:
        try:probe_runtime(config)
        except ValueError as e:assert missing.name in str(e),str(e)
        else:raise AssertionError('Missing dependent DLL was not detected.')
    finally:renamed.rename(missing)
