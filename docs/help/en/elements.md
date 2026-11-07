# Elements, isotopes and composition

## Periodic picker

In the species table, click an element name or ... to open the periodic-table picker. Use × to remove a row and + to add a blank row, then click ... to choose its species. Elements and material entries come from the configured external engine material table. Cancel preserves the old choice. A blank row must be assigned before saving.

H2 is a table alias with the same mass as D. C_g and related names are material variants, not isotopes. Selecting a single entry does not expand a natural isotopic mixture.

## Fractions and order

| Field | Meaning | Rule |
| --- | --- | --- |
| qu_beam | Incident atomic fractions | Sum to 1; zero means not incident |
| qu_tar | Initial substrate atomic fractions | Sum to 1 |
| qu_max | Species concentration limit | Use the engine/model definition |

Energy and angle are edited under Target drawing → Beam settings. Select each incident species separately. Substrate and protrusion composition tables follow the same species order.

## Extended arrays

Changing species count or order also requires updating all species-dependent advanced arrays. The application rejects incompatible extensions; check the input text first.
