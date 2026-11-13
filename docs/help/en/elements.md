# Elements, isotopes and composition

## Periodic picker

In the species table, click an element name or ... to open the periodic-table picker. Use × to remove a row and + to add a blank row, then click ... to choose its species. Elements and material entries come from the configured external engine material table. Cancel preserves the old choice. A blank row must be assigned before saving.

H2 is a table alias with the same mass as D. C_g and related names are material variants, not isotopes. Selecting a single entry does not expand a natural isotopic mixture.

## Fractions and order

| Field | Meaning | Rule |
| --- | --- | --- |
| qu_beam | Incident atomic fractions | Sum to 1; zero means not incident |
| qu_tar | Initial substrate atomic fractions | Sum to 1 |
| qu_max | Maximum allowed local fraction in a dynamic target | 0–1; 1 means no finite limit |
| Atomic mass | Relative atomic mass from table1 | Must be positive; current run only |
| Mass density | Mass density from table1 (g/cm^3) | Must be positive; current run only |
| Atomic number density | Atomic density from table1 (atoms/A^3) | Must be positive; current run only |

`qu_max` is an engine input, not another name for `qu_tar`: `qu_tar` is the initial target composition, while `qu_max` limits the local atomic fraction a species may reach during dynamic target updates. A value of `1` means no finite limit; `0 < qu_max < 1` sets a finite limit. The current 3.01 engine supports at most two species with finite limits, and at least one species must remain at `1`. The GUI validates the range and count and writes values to `tri.inp` in species order. Static targets do not use this limit for dynamic updates.

Atomic mass, mass density and atomic number density default to the configured `table1`. Edits go only to a private table copy in the current run directory; the run input selects that copy. The source table and case input remain unchanged, and saving a case does not persist these material-property overrides. See official report §§3 and 10.4.1 (printed pp. 9–10 and 44); the `qu_max` parameter is listed in Appendix I.2 (printed p. 90).

Energy and angle are edited under Target drawing → Beam settings. Select each incident species separately. Substrate and protrusion composition tables follow the same species order.

## Extended arrays

Changing species count or order also requires updating all species-dependent advanced arrays. The application rejects incompatible extensions; check the input text first.
