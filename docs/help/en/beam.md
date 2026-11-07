# Beam, energy and angle

## Where to edit

Target drawing → Beam settings edits energy and angle. Select individual species with qu_beam>0. The preview arrow follows that species; its tip x follows x_start. Arrays retain the Elements species order.

| Parameter | Meaning |
| --- | --- |
| x_start / dx_start | Beam center / width |
| z_start | Starting height for applicable modes |
| case_start | Start sampling: 1 local surface, 3 fixed, 4 random beam |
| e0_beam / alpha0 | Interpretation depends on distribution mode |

In case_start=1, z_start is not the actual launch height. Small beam widths may trigger full-width handling; read validation messages.

## Energy modes

| Mode | Name | Meaning |
| --- | --- | --- |
| 0 | Fixed energy | Use e0_beam as the fixed energy for each incident species, in eV. |
| 1 | Energy file | Read and sample the energy distribution from energy.inp. Energy is in eV. |
| 2 | 3D Maxwellian | 3D Maxwellian thermal motion with sheath acceleration (charge × shth). e0_beam is the temperature energy scale kT (eV), not a fixed particle energy. This mode recalculates direction and is not independent of the angular mode. |
| 3 | Reduced Maxwellian | Reduced Maxwellian mode using energ; this local implementation restricts directions to the x–z plane. e0_beam is the temperature energy scale kT (eV), with sheath acceleration. This mode recalculates direction. |
| 5 | Gaussian energy | Gaussian energy: center e0_beam, standard deviation de0_beam, in eV. The local engine samples within ±4σ and rejects negative energies; de0_beam must be positive. |

## Angle modes

| Mode | Name | Meaning |
| --- | --- | --- |
| 0 | Fixed angle | Use alpha0 as the fixed angle for each incident species, in degrees from the reference surface normal; 0° is normal incidence. Energy modes 2/3 recalculate direction. |
| 1 | Uniform polar angle | Sample the polar angle uniformly from 0 to alpha0 with random azimuth. alpha0 is the upper bound in degrees, not the center. This is not uniform sampling over solid angle. |
| 2 | Cosine flux | Built-in cosine-flux distribution over polar angles 0–90°, with random azimuth. The polar-angle density peaks near 45°; alpha0 does not set its center. |
| 3 | Small-angle weighted | Built-in small-angle-weighted distribution over 0–90°, with random azimuth. Angles near the normal are more frequent; this differs from the cosine-flux distribution in mode 2. |
| 4 | Angle file | Read the angular distribution from angle.inp, in degrees. Caution: the local source samples alpha_pol but uses alpha_z in the coordinate conversion. This suspected variable error has not been numerically verified or fixed; verify before use. |
| 5 | Gaussian angle | Gaussian angle: center alpha0, standard deviation dalpha0, in degrees. The local engine samples within ±4σ and restricts angles to −180–180°; dalpha0 must be positive. |

## Interpretation

0° follows the reference surface normal. File/built-in angular modes do not use a single alpha0 to control actual angles, so the shortcut is disabled with an explanation. Energy modes 2/3 recalculate direction; energy and angular choices are not always independent. The arrow is a schematic, not a sampled distribution.

The local angle-mode-4 branch has a suspected inconsistent variable; dedicated numerical verification and a fix remain outstanding.

