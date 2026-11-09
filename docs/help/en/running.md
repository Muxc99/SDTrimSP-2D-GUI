# Check, run and stop

## Installation and setup

The Windows installer and portable ZIP bundle Python, Qt/PySide6, NumPy, pandas and Matplotlib. Start SDTrimSP-2D_GUI.exe or its shortcut. The source download uses start-gui.cmd to install dependencies on first use (Internet required).

The computer icon opens Engine and data settings. Select the actual compiled engine and material tables directory separately; they may be on different drives. Scans suggest candidates for confirmation. No fixed drive, work/tables layout or run-case script is required. A Linux ELF executable requires WSL on Windows; a Windows PE executable requires native runtime libraries. Leave the WSL distribution blank to use the system default. Setup can be skipped for editing and viewing existing results.

## Before running

Check species order, fractions, geometry, mesh, auxiliaries and output switches. Run preflight shows the input location, engine format, material directory, required table files, runtime checks and output location. Missing items are listed individually. Engine version is not inferred. Configure the correct executable, distribution or table directory and check again after changes.

## Independent results

Default output is Documents / SDTrimSP-2D / Runs under the current user. Choose another writable directory in settings if needed. Each calculation creates a unique folder with private input and material copies. Only the run copy's tableinp is set to ./_tables. Original cases and the external installation are preserved. Run copies include licensed data; do not publish them with the GUI.

## Stop and completion

Request stop writes stop_run.inp=1. The engine checks at its existing interval. Wait for logged completion before loading full outputs. Existing progress and completion checks retain their behavior.

## About and diagnostics

About and diagnostics displays GUI, Python and Qt versions, engine format and SHA-256 fingerprint. Engine version is marked not reported. Exported JSON excludes user names, paths, input contents and logs.

## Scientific checks

Successful execution does not establish statistical convergence or physical applicability. Check fluence, mesh, statistics and models separately. A preview is not an engine result.
