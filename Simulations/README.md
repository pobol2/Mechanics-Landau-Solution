# Numerical studies

A study checks a solution's final Lagrangian numerically. The same system is
simulated twice, from the same parameters and initial conditions:

- with the [`physics-engine`](../physics-engine) library: particles, forces and
  constraints in Cartesian coordinates, moving by Newton's laws (no Lagrangian);
- from the manual's Lagrangian: SymPy derives the Euler-Lagrange equations and
  SciPy integrates them.

`study.py` compares the particles' Cartesian positions and velocities, and
prints both models' drift of the energy (and of any other conserved quantity
the problem lists, such as a momentum), the engine's energy-balance error
(energy change minus the work of moving supports) and its constraint
residuals. A Lagrangian may depend on time, as for a driven support; its
energy function is then not conserved and is not checked.
Each case runs at standard and tight tolerances; the check passes when the
tight position difference is below 1e-6 m and smaller than the standard one.
It writes the plot data to `Figures/Data/<problem>-verification.csv`, which
the PGFPlots figures `Figures/<problem>-coordinates.tex` (the motion) and
`Figures/<problem>-difference.tex` (the position difference) plot. All are
kept in Git, so `latexmk` builds the manual without running any simulation,
and recompiles a figure only when its `.tex` or the `.csv` changes.

```
CMakeLists.txt        add_study(<problem>) for each problem
study.hpp             engine side: options and CSV output
study.py              Lagrangian side, comparison, plot data
<problem>/engine.cpp  the system built with the engine
<problem>/problem.py  the manual's Lagrangian, coordinates, cases, duration
```

## Running

Prerequisites: CMake 3.20+, a C++17 compiler, Python 3.11+, and the
submodule (`git submodule update --init physics-engine`). From the repository
root:

```sh
# Build every engine model (Eigen is downloaded on the first configure)
cmake -S Simulations -B build/simulations -DCMAKE_BUILD_TYPE=Release
cmake --build build/simulations --config Release

# Python environment (once; on Linux and macOS use bin/ instead of Scripts/)
python -m venv build/simulations-venv
build/simulations-venv/Scripts/python -m pip install -r Simulations/requirements.txt

# Run a study, then rebuild the manual
build/simulations-venv/Scripts/python Simulations/study.py S5P1
latexmk
```

With MinGW (e.g. Strawberry Perl's g++), add `-G Ninja` to the configure
command. The engine's CSV files go to `build/simulations/runs/`.

## Adding a problem

1. `<problem>/problem.py`: copy `S5P1/problem.py` and set `COORDINATES`,
   `ANGLES`, `LAGRANGIAN` (the manual's answer), `POSITIONS` (each particle in
   the engine frame), `CASES` and `DURATION`, and optionally `CONSERVED`
   (as in `S5P2/problem.py`), `ENERGY` (`None` for a Lagrangian that depends
   on time, as in `S5P3a/problem.py`, or another conserved column, as the
   Jacobi integral in `S5P4/problem.py`) and `DT` (a finer sample interval for
   a fast drive, as in `S5P3c/problem.py`).
2. `<problem>/engine.cpp`: build the `Model` and `State` from the options and
   call `study::run` with the same coordinates and rates, as in
   `S5P1/engine.cpp` (the sampler also gets the time, for a moving support,
   as in `S5P3a/engine.cpp`). Note the conversion between the engine frame and the
   manual's figure in a comment.
3. Add `add_study(<problem>)` to `CMakeLists.txt`, build, and run `study.py`.
4. Copy `Figures/S5P1-coordinates.tex` and `Figures/S5P1-difference.tex` to
   `Figures/<problem>-coordinates.tex` and `Figures/<problem>-difference.tex`,
   adapt the column names, and include them in the problem's verification
   (`[...]` after the answer) with a short text that reads without the
   repository: what was simulated, the cases (values), what each figure shows,
   the agreement, and that it is evidence, not a proof.
