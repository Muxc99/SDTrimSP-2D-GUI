# Check, run and stop

## Before running

Check species order, fractions, geometry bounds, mesh, auxiliaries and output switches. Errors block saving/running. Warnings may indicate engine-specific parameter handling and need review.

## Separate run copy

Run creates a separate directory in the local work area and calls the configured compatible engine with current valid inputs. Raw diagnostics remain visible; errors are not bypassed as success. Without an engine, the GUI cannot run calculations.

## Stop and completion

Request stop writes stop_run.inp=1. The engine checks at its existing interval (every 10 fluence steps), rather than being killed immediately. Wait for logged termination/completion before loading full outputs. Load current run results after it ends.

## Scientific checks

Completion markers, errors and time_run.dat support execution checks. Also check statistics, fluence-step and mesh convergence, and model applicability. Initial sketches are not engine verification; short runs do not establish convergence.



