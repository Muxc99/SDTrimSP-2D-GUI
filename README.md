# SDTrimSP-2D GUI v0.9.0

A bilingual desktop editor for SDTrimSP-2D inputs, 2D target drawing and interactive result plots.

**GUI only.** The separately licensed SDTrimSP-2D engine, material tables, original examples, simulation outputs and official manual are not included. Obtain a compatible engine and its data from an authorized source. Editing and viewing existing results are available without an engine; calculations require one.

## Download and start / 下载与启动

Download from [Releases](https://github.com/Muxc99/SDTrimSP-2D-GUI/releases):

| Download | How to start |
| --- | --- |
| **Windows-Setup.exe** (recommended) | Install for the current user, then use the desktop or Start menu shortcut. Includes Python, PySide6, NumPy, pandas and Matplotlib, plus an uninstaller. |
| **Windows-Portable.zip** | Extract the **entire ZIP**, then double-click **SDTrimSP-2D_GUI.exe**. Keep the _internal folder next to it. No separate Python installation or administrator access is required. |
| **Source.zip** / GitHub source code | For developers. Install Python 3.11+, then double-click **start-gui.cmd**. It creates a user-local environment and installs dependencies automatically on first use (Internet required). |

普通用户请选择 **Windows-Setup.exe**，或完整解压 **Windows-Portable.zip** 后双击 **SDTrimSP-2D_GUI.exe**；无需另装 Python 或依赖。不要只把 EXE 拖出压缩包。源码版双击 **start-gui.cmd**，首次会自动安装依赖。

Windows packages target Windows 10/11 x64. They are not digitally signed. This is an independent GUI, not an official SDTrimSP distribution.

## First launch: engine and data settings

Setup can be skipped. The **computer icon** in the toolbar opens **Engine and data settings**.

1. Select the actual compiled **engine executable**, such as target.exe or target. Do not select source, a Makefile or a launcher script. The GUI checks PE/ELF headers; an .exe suffix alone does not prove it is a Windows program.
2. Select the **material tables directory** separately. Choose the folder containing table1 and its companion tables. The dialog also recognizes tables, work/tables, or a table1 path entered directly. Engine and tables may be on different drives.
3. Select an independent **results directory**. Default: the current user's Documents / SDTrimSP-2D / Runs.
4. A Linux ELF engine requires WSL on Windows and the Linux libraries required by that engine. Leave the distribution blank to use the user's default, or enter an installed distribution name. Native Windows x64 engines require their Windows runtime libraries.
5. Use **Check again** to verify materials and runtime. Before a run, the GUI shows input location, engine format, data location, required files, runtime checks and output location. Engine version is marked not reported when unavailable; no version is guessed.

首次启动可跳过配置，继续编辑和查看结果。点击顶部**电脑图标**分别选择**内核程序、材料表目录、结果目录**，三者不必在同一位置。扫描结果需要手动确认。Linux 内核需 WSL；Windows 内核需对应运行库。运行前逐项显示缺项，不再要求固定盘符、目录结构或额外的 run-case.sh。

Each run receives independent input and table copies. Only the run copy's tableinp is changed to ./_tables. Original cases and external installations are preserved. Run folders can contain licensed data; do not upload them with GUI code.

## Features

- Input creation, validation, text editing and saving.
- Grid target drawing, composition controls and geometry-specific substrate editing.
- Interactive previews, pan/zoom, gradients, result plots and data export.
- Chinese and English interface and offline help.
- Independent engine, table and results settings, with bounded discovery.
- About and diagnostics: GUI/Python/Qt versions, engine format/fingerprint and JSON export excluding personal paths, inputs and logs.

## Screenshots

Earlier GUI versions are illustrated below; the 0.9 toolbar and engine settings have changed.

![Target editor](docs/images/target-editor.png)

![Result plots](docs/images/result-plots.png)

![Input and preview](docs/images/initial-preview.png)

## Run from source manually

~~~powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
~~~

## Build Windows packages

Use a clean Windows x64 Python environment, not a private engine installation:

~~~powershell
python -m venv .build-venv
.build-venv\Scripts\python.exe -m pip install -r requirements-build.txt
.build-venv\Scripts\python.exe build_windows.py
~~~

The portable app is in dist/SDTrimSP-2D_GUI. Copy README.md and PLOTTER-LICENSE.txt into it. Compile installer.iss using Inno Setup 6 or newer. PortableDir and OutputDirPath defines can override the input/output paths. The installer creates shortcuts and an uninstall entry; user cases and results are preserved on uninstall.

The release uses Python 3.14 x64 and the pinned build dependencies. The build wrapper isolates DLL search paths; the spec rejects DLLs collected from unrelated software. Always test the frozen EXE, not only the source application.

## Third-party notices

See PLOTTER-LICENSE.txt for the included plotting component. This notice does not license or redistribute the external SDTrimSP engine. Bundled Windows dependencies retain their included licenses.
