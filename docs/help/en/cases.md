# Cases and saving

## New case

Startup is an unsaved blank case. Ctrl+N selects geometry, opens the periodic picker for incident/substrate species, and sets name, dimensions, mesh and beam conditions. Defaults are modeling starting points. Modes 24/25 create a flat rauh.inp; 26 starts without protrusions.

Edit the case title in the main top bar. Canceling a new-case or discard prompt preserves the current case.

## File destinations

| Operation | Destination | Active case path afterwards |
| --- | --- | --- |
| Save Ctrl+S | Current directory; first save asks for a new folder | Saved folder |
| Save as Ctrl+Shift+S | New directory | New directory |
| Run | Separate copy under a local work directory | Input case path retained |

Changed inputs are backed up before overwrite. Existing calculation outputs are preserved. Save as includes auxiliary inputs. Cases are supplied by the user.

## Open a case

Click Open case and select a directory containing tri.inp. Check geometry, species order, units and auxiliary files afterwards.
