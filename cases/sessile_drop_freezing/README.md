# sessile_drop_freezing

**Status: in progress.** The case does not yet conserve ice mass and its contact line spreads as soon as ice forms; see the Phase 4b diagnosis in the top-level README. Treat results from it as diagnostic only.

A water droplet (R = 1 mm, initially a 90° hemisphere at 0 °C) freezes on a plate held at −30 °C, in air at 0 °C. Axisymmetric wedge, `icoReactingMultiphaseInterFoam` with three phases: air and water (moving) and ice (static).

| Item | Setting |
|---|---|
| Phase change | Lee model (liquid to solid), C = −1000 1/s, active below 0 °C (verified in `stefan_freezing_1d`) |
| Ice | ρ = 917 kg/m³, so freezing expands the droplet by about 9 %; Voller-Prakash damping keeps ice static |
| Surface tension | water-air, σ = 0.0756 N/m |
| Contact angle | 90° (zero-gradient volume fractions at the plate) |
| Mesh | 42 × 42 cells over 3 × 3 mm (Δx = 71 µm, 14 cells per radius) |
| Time step | ≤ 11.5 µs, set by the capillary limit √(ρΔx³/2πσ) |

The mesh is coarse because explicit surface tension limits the time step while freezing takes seconds: about 350,000 steps even at this resolution. Finer meshes are a job for an HPC cluster.

## Run

```bash
./Allrun                                  # serial; NP=2 ./Allrun for two cores
python3 postProcess/freezing.py . --gif   # plots and animation
```

## Outputs

- `log.freezing`: frozen mass fraction, freezing time (99 % frozen), apex height, volume ratio, mass change
- `freezing.png`: frozen fraction and apex height against time, initial and final outline with ice fronts
- `freezing.gif`: outline (blue) and ice front (grey)

## What to look for

Water expands on freezing. The last liquid freezes at the top of the droplet, and its expansion is expected to form a pointed tip on the frozen drop (Marín et al., Phys. Rev. Lett. 113, 054301, 2014). The final volume should approach ρ_water/ρ_ice = 1.09 times the initial volume while mass is conserved.
