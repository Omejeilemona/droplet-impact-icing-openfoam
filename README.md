# Droplet impact and icing in OpenFOAM

Simulations of water droplets impacting surfaces of controlled wettability, built step by step towards droplet freezing on cold surfaces, the process behind aircraft and wind-turbine icing. The work uses OpenFOAM (v2606, openfoam.com) with volume-of-fluid interface capturing, and is aimed at the question of how the wall, through its wettability, its contact-line dynamics and later its temperature, controls spreading and freezing.

![Droplet impact: spreading, recoil and axial jet (N25, We = 28, θ = 90°)](figures/impact.gif)

*Interface (α = 0.5) of a 2 mm water droplet hitting a wall at 1 m/s, mirrored about the axis. Generated with `postProcess/animate.py`.*

## Status

| Phase | Content | Status |
|---|---|---|
| 1 | Isothermal axisymmetric impact (`interFoam`), comparison with spreading correlations, mesh study | Done; β_max not mesh-converged (see 1b) |
| 1b | Wall-region resolution: wall-graded mesh and imposed slip length | Next |
| 1c | Weber-number sweep (We ≈ 7–170) | Next |
| 2 | Wettability sweep (θ = 30°–160°), deposition and rebound | Planned |
| 3 | Dynamic contact-angle boundary condition from molecular-kinetic theory (C++ library) | Planned |
| 4a | Freezing verification: 1D Stefan problem with `icoReactingMultiphaseInterFoam` | Done |
| 4b | Sessile droplet freezing on a cold plate (water, ice, air; ice expansion) | In progress |
| 4c | Droplet impact on a cold plate | Planned |
| 5 | 3D impact with adaptive mesh refinement, parallel scaling | Planned |

## Phase 1 results

A 2 mm water droplet hits a flat wall at 1 m/s in air, with a static contact angle of 90° (We = ρU₀²D₀/σ = 27.8, Re = U₀D₀/ν = 2000). The spreading factor β = D/D₀ is measured from the α = 0.5 interface, and time is t* = tU₀/D₀ from contact.

| Mesh | Cells per radius | Δx (µm) | β_max | t* at β_max | vs Pasandideh-Fard (1996) |
|---|---|---|---|---|---|
| N25 | 25 | 40 | 2.661 | 1.70 | −1.2 % |
| N35 | 35 | 29 | 2.640 | 1.63 | −2.0 % |
| N50 | 50 | 20 | 2.608 | 1.57 | −3.2 % |

For comparison, the correlations of Clanet et al. (2004) and Roisman (2009) give 2.07 and 2.39. Clanet's scaling was derived mainly for non-wetting surfaces, which explains most of that gap. Pasandideh-Fard's energy balance includes the contact angle and is the closest reference here.

![Spreading factor on three meshes](figures/beta_t_mesh.png)

**Findings**

- Early spreading (t* < 1) is the same on all three meshes, and recoil converges (N35 and N50 differ by 0.015 at t* = 3).
- β_max does **not** converge. It falls by about 1 % per refinement, with growing differences (0.021, then 0.032). Two mechanisms fit, both making coarse meshes overpredict spreading:
  1. numerical contact-line slip, since on a no-slip wall the contact line moves by about one cell;
  2. an under-resolved wall boundary layer, δ ≈ D₀/√Re ≈ 45 µm, covered by only one or two cells.

  Phase 1b is designed to separate them.
- Liquid volume is conserved to better than 0.001 % through maximum spread.
- During recoil at θ = 90°, the collapsing cavity drives a thin axial jet rising at about 4 m/s (4 U₀). Its radius is close to the cell size, so its speed is not resolved, and volume loss starts when it forms (−0.085 % by 10 ms). Validation runs therefore stop at t* = 3.
- β_max is independent of domain height (identical in 4 mm and 8 mm domains).
- The animation shows a small air bubble trapped on the axis at the wall from the moment of impact, consistent with the air cushion being enclosed under the droplet (Thoroddsen et al. 2005). At N25 it spans only a few cells, so its size is not resolved.
- The axial jet breaks into satellite droplets (three by t ≈ 9 ms). The jet and these droplets are a few cells across, which is where the late volume loss occurs.

The full impact, including recoil, from an earlier exploratory run to t* = 5 (N25, 4 mm tall domain, otherwise identical):

![Full impact, spreading and recoil to t* = 5 (N25)](figures/beta_t_N25_full.png)

Data: [`results/mesh_study.csv`](results/mesh_study.csv)

## Freezing verification (Phase 4a)

Water at 0 °C in a 10 mm column is frozen from a wall held at −10 °C (`cases/stefan_freezing_1d`). The solver is `icoReactingMultiphaseInterFoam` with water and ice as phases, the Lee phase-change model (liquid to solid, active below 0 °C) and Voller-Prakash damping in the ice. Ice and water densities are set equal so that freezing causes no flow, as the analytical solution assumes. The exact front position is s(t) = 2λ√(α_ice t), with λ e^{λ²} erf(λ) = St/√π; here St = 0.061 and s = 0.361 mm √(t/s).

| Lee coefficient C (1/s) | s at 100 s (mm) | Exact (mm) | Error |
|---|---|---|---|
| −100 | 3.502 | 3.610 | −2.97 % |
| −1000 | 3.575 | 3.610 | −0.97 % |
| −10000 | 3.594 | 3.610 | −0.43 % |

![Stefan problem: front position and error](figures/stefan_C.png)

The Lee model freezes water at a rate proportional to its undercooling, so the front runs slightly behind the exact solution. The lag is fixed early (the curves are parallel in √t), so the relative error decays over time. It falls with |C|, but by less than a factor of 10 per decade, which suggests a second error source (the 50 µm cells, 1.4 % of the final thickness) dominates at C = −10000. C = −1000 is used for the droplet cases as a compromise between accuracy and time step.

Data: [`results/stefan_C.csv`](results/stefan_C.csv)

## Model

| Item | Choice |
|---|---|
| Solver | `interFoam`: incompressible two-phase Navier-Stokes, algebraic VOF with MULES and interface compression |
| Surface tension | Continuum surface force (Brackbill et al. 1992) |
| Wall | No-slip, `constantAlphaContactAngle` |
| Geometry | 2D axisymmetric 5° wedge, r = 0–6 mm, y = 0–8 mm, square cells |
| Time step | Adaptive, Courant ≤ 0.2, Δt ≤ 0.6 × capillary limit √(ρΔx³/2πσ) |
| Fluids | Water and air at 20 °C, σ = 0.072 N/m |

## Running

Requirements: OpenFOAM v2606 (openfoam.com), Python 3 with NumPy and Matplotlib. Tested under Ubuntu 24.04 (WSL2).

```bash
cd cases/droplet_impact_axisym
./Allrun            # mesh, setFields, interFoam on 4 cores, spreading analysis
NP=1 ./Allrun       # serial
./Allclean          # reset the case
./runMeshStudy      # N = 25, 35, 50 -> cases/meshStudy/beta_t_mesh.png
./runSweep          # Weber-number sweep -> cases/sweep/betamax_We.png
```

All physical, mesh and run-length inputs are in `caseParameters`. `Allrun` sets the end time and the time-step limit from them. Study and sweep runs are written to `cases/meshStudy/` and `cases/sweep/`, which git does not track; selected figures and tables are copied to `figures/` and `results/`.

## Repository layout

```
cases/droplet_impact_axisym/   OpenFOAM case (0.orig, constant, system), run scripts
cases/stefan_freezing_1d/      freezing verification against the Stefan problem
cases/.../postProcess/         spreading.py: beta(t), correlations, sweep and mesh plots
                               animate.py: GIF of the interface
figures/                       figures used in this README
results/                       tabulated results
```

## References

- Pasandideh-Fard, M., Qiao, Y. M., Chandra, S. & Mostaghimi, J. Capillary effects during droplet impact on a solid surface. *Physics of Fluids* 8, 650 (1996).
- Clanet, C., Béguin, C., Richard, D. & Quéré, D. Maximal deformation of an impacting drop. *Journal of Fluid Mechanics* 517, 199–208 (2004).
- Roisman, I. V. Inertia dominated drop collisions. II. An analytical solution of the Navier–Stokes equations for a spreading viscous film. *Physics of Fluids* 21, 052104 (2009).
- Brackbill, J. U., Kothe, D. B. & Zemach, C. A continuum method for modeling surface tension. *Journal of Computational Physics* 100, 335–354 (1992).
- Afkhami, S., Zaleski, S. & Bussmann, M. A mesh-dependent model for applying dynamic contact angles to VOF simulations. *Journal of Computational Physics* 228, 5370–5389 (2009).
- Voller, V. R. & Prakash, C. A fixed grid numerical modelling methodology for convection-diffusion mushy region phase-change problems. *International Journal of Heat and Mass Transfer* 30, 1709–1719 (1987).
- Lee, W. H. A pressure iteration scheme for two-phase flow modeling. Los Alamos Scientific Laboratory report LA-UR-79-975 (1979).
- Bartolo, D., Josserand, C. & Bonn, D. Singular jets and bubbles in drop impact. *Physical Review Letters* 96, 124501 (2006).
- Thoroddsen, S. T., Etoh, T. G., Takehara, K., Ootsuka, N. & Hatsuki, Y. The air bubble entrapped under a drop impacting on a solid surface. *Journal of Fluid Mechanics* 545, 203–212 (2005).

## Author

Ilemona Sunday Omeje · [Google Scholar](https://scholar.google.com/citations?user=_6zzk-UAAAAJ&hl=en)

## License

MIT
