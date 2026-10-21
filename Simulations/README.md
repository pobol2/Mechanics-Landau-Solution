# Numerical study details

See the [main README](../README.md#numerical-studies) for the overview,
requirements and build/run commands. Run every study through
`python Simulations/study.py <ID>` using the environment described there.
Engine output goes to `build/simulations/runs/`; saved plot and convergence
CSVs go to `Figures/Data/`.

## Models and verification

Each `<ID>/engine.cpp` constructs an independent Cartesian particle model;
`<ID>/problem.py` defines its comparison. `study.hpp` supplies options and
CSV output. Section 5 uses adaptive integration; sections 7 and 10 supply
`--fixed_step` for the engine's existing RK4 integrator. Engine sources are
unchanged.

**Section 5:** SymPy derives Euler-Lagrange equations from the manual's
Lagrangian and SciPy integrates them independently. Standard/tight engine
tolerances are 1e-9/1e-11; reference tolerances are 1e-11/1e-13. The tight
maximum Cartesian position difference must be below 1e-6 m and smaller than
the standard difference. Reports also include velocity agreement, energy
balance, constraint residuals and applicable conserved quantities. Energy
conservation is omitted when the Lagrangian depends explicitly on time.

**S7P1:** `customForce` implements `U=jump*(1+tanh(x/width))/2` and its
negative gradient. With m=1 kg and incident speed 2 m/s, a particle starts
at x=-1 m; outgoing velocity is measured at the first crossing of x=1 m or
return through x=-1 m. Samples are 0.032 s apart, with a 16 s time limit.

| Parameter | Values |
| --- | --- |
| Upward jump, incidence | 1 J; 0, 15, 30, 40, 44, 44.5, 45.5, 46, 50, 60 degrees |
| Downward jump, incidence | -0.6 J; 0, 30, 60 degrees |
| Transition width | 0.2, 0.1, 0.05 m |
| RK4 step at each width | 0.008, 0.004, 0.002, 0.001 s |

Classification and transmission angles are compared with the half-space
energy/momentum formulas. The exact 45-degree upward-step threshold is
excluded. A separate comparison using actual endpoint potentials isolates
integration error from finite tanh tails. Normal velocity error must converge
with step size; nonzero transmitted angle errors must converge with width.
Reflected paths are not required to equal abrupt-step paths.

**S10P1 / S10P2:** both use `U=scale*(k*x^2/2+alpha*x^4/4)` and
`F=-scale*(k*x+alpha*x^3)`, released at x=A from rest. Base cases
`(m,k,alpha,A)=(1,1,1,1)` and `(1.5,0.7,1.3,0.8)` use SI units and scale=1.
S10P1 compares `x_4m(2t)=x_m(t)`; S10P2 compares `x_4U(t/2)=x_U(t)` at fixed
mass, scaling both force and potential. Base/4U runs last 16 s; heavy-mass
runs last 32 s. Corresponding samples align without interpolation. Independent
runs use the same physical RK4 steps, 0.04, 0.02, 0.01 s.

Each oscillator trajectory also converges against the independent analytic
solution `x=A*cn(omega*t | p)`, with
`omega^2=scale*(k+alpha*A^2)/m` and `p=alpha*A^2/(2*(k+alpha*A^2))`, evaluated
after the engine run. Position self-convergence and rescaled velocity agreement
are checked too. See [similarity.py](similarity.py) and
[the step verifier](S7P1/problem.py) for the calculations.

## Acceptance bounds and results

| Finest-setting check | S7P1 | S10P1 / S10P2 |
| --- | --- | --- |
| Angle / similarity position error | 1e-6 rad | 1e-6 m |
| Normal / rescaled velocity error | 1e-7 m/s | 3e-6 m/s |
| Independent analytic position / velocity error | Not applicable | 2e-6 m / 5e-6 m/s |
| Scaled energy drift/balance | 1e-8 | 1e-7 |
| Engine energy versus stated potential | 1e-12 J | 1e-12 J |

S7P1 also requires correct classification and tangential momentum agreement
within 1e-12 kg m/s. Oscillator rest releases and transverse motion are checked.
Bounds allow near-threshold angle sensitivity and accumulated RK4 phase error
while requiring sub-micrometre similarity agreement. Successive refinements
must reduce errors by at least two (RK4 typically gives about 16), with floors
of 1e-12 for oscillator errors, 1e-11 m/s for step velocity error and 1e-8 rad
for width refinement. Non-finite or incomplete output also fails verification.

| Study | Observed maximum at finest settings | Scaled energy error |
| --- | --- | --- |
| S7P1, width 0.05 m | 9.13e-10 rad | 7.58e-10 |
| S10P1 | 1.03e-8 m similarity; 1.10e-8 m analytic | 4.08e-10 |
| S10P2 | 1.71e-7 m similarity; 3.97e-7 m analytic | 2.15e-8 |

Full results are saved in `Figures/Data/<ID>-convergence.csv`.

## Regression checks

Run `study.py` for S5P1, S5P2, S5P3a, S5P3b, S5P3c, S5P4, S7P1, S10P1
and S10P2, then `latexmk`. Relevant existing engine tests run separately:

```sh
cmake -S physics-engine -B build/engine-checks -DCMAKE_BUILD_TYPE=Release
cmake --build build/engine-checks --config Release --target physics_library_tests physics_tests
ctest --test-dir build/engine-checks -C Release --output-on-failure -R "^(force_library|forces_energy|oscillator_accuracy|oscillator_convergence|conservation|simulation_time|mass_gravity|adaptive_integration|diagnostics)$"
```

For MinGW, add `-G Ninja -DCMAKE_EXE_LINKER_FLAGS=-static` when configuring
these tests. Pass `-DEigen3_DIR=<package-directory>` to reuse an Eigen install.

## Adding a study

1. Copy an existing model and define `<ID>/problem.py`: use
   [S5P1](S5P1/problem.py) for a Lagrangian comparison, or a `verify(exe, work)`
   callback as in [S10P1](S10P1/problem.py) for analytical comparisons.
2. Build the engine model in `<ID>/engine.cpp`, call `study::run`, and document
   its coordinate convention. Add `add_study(<ID>)` to `CMakeLists.txt`.
3. Build and run the study. Add standalone PGFPlots sources in `Figures/`
   using the saved CSVs and existing figure styles.
4. Include the plots in the solution's verification argument (`[...]` after
   the answer), briefly giving the cases, agreement and limits of the check.
