# SDTrimSP-2D_GUI v1.0.0

Edit inputs, draw targets and inspect outputs using the existing Fortran engine. Choose a topic on the left, search titles/content/parameter names, or jump using On this page. Copy Markdown for local notes. Help works offline.

## First session

1. Create a case: choose geometry, incident species, substrate, dimensions and beam conditions.
2. Set atomic fractions in Elements and mesh/substrate/beam values in Target drawing.
3. Draw protrusions in mode 26 or edit upper profiles in modes 24/25.
4. Check and save inputs, run, then load outputs from that same case directory.

## Pages

| Page | Purpose |
| --- | --- |
| Input and preview | Elements, fractions, calculation modes and initial sketch |
| Target drawing | Mesh/substrate/beam and shape editing |
| 2D structure blocks | Numeric fig.inp rectangle data |
| Advanced parameters / Input files | Extensions and source text |
| Run log / Result plots | Progress and recorded outputs |

## Sources and interpretation

Help separates current GUI behavior, rules confirmed by the SDTrimSP-2D 3.01 source/manual, and limits that have not received dedicated numerical verification. “Local engine” refers to the 3.01 source checked during development; it does not guarantee behavior in every user-configured engine build. Manual page numbers below are printed page numbers. The manual is referenced for context and is not bundled with this GUI.

Key references: §2 geometry (printed pp. 5–8); §§3 and 10.4.1 species-fraction limits (pp. 9–10, 44); §8 mesh resolution (p. 25); §§10.1–10.3 dimensions, geometry and beam start (pp. 28–41); §10.4 initialization, layering and clusters (pp. 44–48); Appendices A units (p. 70), D Gaussian distributions (p. 74), E input/output (pp. 75–77), F distribution files (pp. 78–79), and I parameters (pp. 83–90). These references explain inputs and do not replace the manual for the engine actually installed by a user.


