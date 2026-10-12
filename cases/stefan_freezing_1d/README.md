# stefan_freezing_1d

Verification of freezing in `icoReactingMultiphaseInterFoam` against the one-phase Stefan problem. Water at its melting point fills a 10 mm column; at t = 0 the bottom wall is held at −10 °C and an ice layer grows from it.

## Analytical solution

s(t) = 2λ√(α_ice t), with λ e^{λ²} erf(λ) = St/√π and St = c_ice (T_m − T_w)/L. For the values in `caseParameters` (St = 0.0614, λ = 0.1734), s(t) = 0.361 mm × √(t/s), so 3.61 mm after 100 s.

## Model

| Item | Choice |
|---|---|
| Solver | `icoReactingMultiphaseInterFoam`, phases water (moving) and ice (static solid) |
| Phase change | `Lee` model, (liquid to solid), C < 0 activates below T_m = 273.15 K |
| Ice momentum | Voller-Prakash Darcy damping |
| Latent heat | Hf of the liquid, 3.34e5 J/kg |
| Densities | equal (1000 kg/m³) so freezing causes no flow, as the analytical solution assumes |
| Mesh | 200 cells over 10 mm (50 µm) |

## Run

```bash
./Allrun        # one case, a few minutes in serial
./runCStudy     # Lee coefficient C = -100, -1000, -10000 -> ../stefanC/stefan_C.png
```

The Lee model freezes at a rate proportional to the undercooling (T_m − T). A larger |C| keeps the front closer to T_m, which the analytical solution assumes, so the error should fall as |C| increases.
