# Input text and advanced parameters

## Layer composition editor

Open **Layer composition editor** from Target drawing or Input files. Bulk layers use absolute z coordinates. Surface layers use vertical offsets below the local surface (zero at the surface, negative below); they override bulk composition in their depth range. Enable either independently. The diagram is a schematic, not the engine mesh result.

Edit contiguous upper/lower boundaries and species fractions (sum = 1), add/remove layers, or drag internal boundaries with vertical-mesh snapping. Display units follow the GUI; files always use Angstrom. Apply updates the in-memory target; Save writes the case.

## Optional inputs and text editing

Geometry and layering are independent features. Add/import optional inputs; adding a layer template enables its switch. Disable layers before removing their files. Required inputs for the active geometry, distribution or model cannot be removed. Removals are staged until Save, which backs up originals under .gui-backups. Non-input files are untouched.

The toolbar provides case Save, current-document Undo/Redo, Add/Import/Remove and Find. Ctrl+S saves the case; Ctrl+Z/Ctrl+Y undo/redo in the editor; Ctrl+F finds text. An asterisk marks unapplied text. Apply validates and updates memory. Discard unapplied text drops the pending draft.

Compact toolbar icons show tooltips after 0.5 seconds. Find is collapsed by default; use the magnifier or Ctrl+F to open it.

## Editing entry points

Forms edit common inputs; 2D structure blocks provides numeric rectangles; Input files edits tri.inp, fig.inp and loaded auxiliaries. These synchronize. File lengths always use Å.

## Apply drafts

Use Apply text edits after changes. Switching pages, saving or running also attempts valid application. Invalid drafts remain editable and are not replaced by old previews. Correct and reapply, or discard unapplied edits to restore the form.

## Advanced inputs

Use original Fortran syntax; untouched extensions retain their text. Species arrays must follow element order.

| File | Role |
| --- | --- |
| rauh.inp | Modes 24/25 surface |
| energy.inp / angle.inp | File distributions |
| initial_composition.inp | Bulk layers |
| initial_composition_surf.inp | Surface layers |
| mat_surfb.inp | Custom binding matrix |

Files and enabling parameters must agree. Do not remove required auxiliaries. Advanced physical models require intentional settings; GUI does not fit them automatically.

