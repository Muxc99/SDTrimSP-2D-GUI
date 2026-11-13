# Shortcuts and troubleshooting

## Shortcuts

| Key | Use |
| --- | --- |
| Ctrl+N / S / Shift+S | New / Save / Save as |
| Ctrl+C / X / V | Copy / prepare cut / paste protrusion selection |
| Ctrl+Z / Y | Drawing undo / redo |
| Arrows / Shift+arrows | Navigate / extend cells |
| Alt+drag | Move protrusions on mesh |
| Delete / F2 / Enter | Delete material/interior node / edit block |
| Escape | Cancel gesture, pending cut or substrate selection |

Drawing shortcuts apply to the canvas; text fields retain normal editing.

## A plot did not update

Check errors and unapplied text, and confirm the selected incident species. Display units do not change file values. Selecting an example name alone does not load it. Existing windows do not hot-reload code; save and restart for updates.

## Cannot drag the substrate

Select it first to show handles. Mode 26 gives the protrusion area priority; select substrate inside z<0. Modes 24/25 give substrate priority. Other geometries retain their native rectangular rules.

## Disabled result choices

A plot is disabled when its required output file is missing or the corresponding output option was not enabled. Particle plots require the particle-output switches and `ioutput_part`; trajectory plots require trajectory output and the relevant history setting. A single data file larger than 64 MiB is not loaded automatically. Check the Data files help page and the run directory. A parse error preserves the previous plot and reports the failure.


## Engine errors

Read the end of the GUI run log and `run.log` in the current run directory. Identify whether failure occurred while reading inputs, initializing the target, or during calculation. Check preflight for executable format, runtime libraries, material tables and case attachments. A generic `&INPUT` hint alone does not prove a spelling error; inspect the actual `tri.inp`, line endings and any Fortran runtime line number.

Preflight validates only implemented formats and constraints; it cannot prove every engine parameter combination is valid or replace a calculation. Keep the failed run directory and log for diagnosis, and avoid overwriting the original case or external material table. Behaviors marked as requiring dedicated numerical verification remain unresolved.

