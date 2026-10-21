# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""Checks a solution's Lagrangian against the engine: python Simulations/study.py S5P1

<problem>/problem.py defines
    COORDINATES  generalized coordinates, functions of t (e.g. phi1(t))
    ANGLES       the coordinates unwrapped (not jumping by 2 pi) in the plot data
    LAGRANGIAN   the final Lagrangian of the manual; it may depend on t
    POSITIONS    each particle's position (X, Y, Z) in the engine frame, in
                 terms of the coordinates (and t for a moving support), in the
                 engine's particle order
    ENERGY       optional, the engine column equal to the Lagrangian's energy
                 function sum(dq dL/ddq) - L, which the motion conserves:
                 "energy" (the default), another column such as a Jacobi
                 integral, or None when L depends on t
    CONSERVED    optional, {engine column: expression}: other quantities that
                 the motion conserves, e.g. {"momentum_X": ...}
    CASES        dicts: a name, the Lagrangian's parameters (named like its
                 symbols) and initial values (phi1, dphi1, ...)
    DURATION     simulated time (s)
    DT           optional, sample interval (s), DT below by default
The engine executable (build/simulations/bin/<problem>) gets every case value
as --name value and writes t, the coordinates, their rates, each particle's
position and velocity, momentum, energy, energy-balance error (energy change
minus work of moving supports, zero for the exact motion) and constraint
residuals (study.hpp).
The models are compared by the particles' Cartesian positions and velocities.
Each case runs at standard and tight tolerances; the check passes if the tight
position difference is below LIMIT and smaller than the standard one.

Writes the plot data to Figures/Data/<problem>-verification.csv (plotted by
Figures/<problem>-coordinates.tex and -difference.tex) and prints a summary. Exits with 1 if the
check fails.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = [("standard", 1e-9, 1e-11), ("tight", 1e-11, 1e-13)]  # engine, Lagrangian tolerances
LIMIT = 1e-6  # largest accepted position difference (m) on tight settings
DT = 0.01     # sample interval (s); the plot keeps every PLOT_EVERY-th sample
PLOT_EVERY = 5


def name(q):
    return str(q.func)


class LagrangianModel:
    """Euler-Lagrange equations of the problem's Lagrangian, with its energy,
    conserved quantities and particle positions as functions of (t, q, dq, p)."""

    def __init__(self, problem):
        L, qs = problem.LAGRANGIAN, problem.COORDINATES
        t = qs[0].args[0]
        dqs = [q.diff(t) for q in qs]
        a = sp.symbols(f"a0:{len(qs)}")
        equations = [(sp.diff(L.diff(dq), t) - L.diff(q)).subs({q.diff(t, 2): ai for q, ai in zip(qs, a)})
                     for q, dq in zip(qs, dqs)]
        M, b = sp.linear_eq_to_matrix(equations, a)
        quantities = dict(getattr(problem, "CONSERVED", {}))
        energy = getattr(problem, "ENERGY", "energy")
        if energy:
            quantities = {energy: sum(dq * L.diff(dq) for dq in dqs) - L, **quantities}
        positions = sp.Matrix([[*r] for r in problem.POSITIONS])
        velocities = positions.diff(t)

        Q, DQ = sp.symbols(f"q0:{len(qs)}"), sp.symbols(f"dq0:{len(qs)}")
        plain = {**dict(zip(dqs, DQ)), **dict(zip(qs, Q))}  # derivatives first
        self.params = [str(s) for s in sorted(L.free_symbols - {t}, key=str)]
        f = lambda X: sp.lambdify((t, Q, DQ, sp.symbols(self.params)), X.subs(plain))
        self._M, self._b = f(M), f(b)
        self._quantities = {k: f(X) for k, X in quantities.items()}
        # as nested lists: constant entries (e.g. Z = 0) stay scalars
        cartesian = lambda X: sp.lambdify((t, Q, DQ, sp.symbols(self.params)), X.subs(plain).tolist())
        self._positions, self._velocities = cartesian(positions), cartesian(velocities)
        self.names = [name(q) for q in qs]
        self.conserved = list(quantities)

    def accelerations(self, time, q, dq, p):
        return np.linalg.solve(np.array(self._M(time, q, dq, p), float),
                               np.array(self._b(time, q, dq, p), float).ravel())

    def run(self, case, times, tolerance):
        p, n = [case[k] for k in self.params], len(self.names)
        y0 = [case[k] for k in self.names] + [case["d" + k] for k in self.names]
        sol = solve_ivp(lambda time, y: np.concatenate([y[n:], self.accelerations(time, y[:n], y[n:], p)]),
                        (times[0], times[-1]), y0, method="DOP853", t_eval=times, rtol=tolerance, atol=tolerance)
        if not sol.success:
            raise RuntimeError(sol.message)
        q, dq = sol.y[:n], sol.y[n:]
        out = dict(zip(self.names, q))
        for k, f in self._quantities.items():
            out[k] = f(times, q, dq, p) * np.ones_like(times)
        # particle, axis, sample
        out["positions"] = self._cartesian(self._positions, q, dq, p, times)
        out["velocities"] = self._cartesian(self._velocities, q, dq, p, times)
        return out

    @staticmethod
    def _cartesian(f, q, dq, p, times):
        rows = f(times, q, dq, p)
        return np.array([[np.broadcast_to(np.asarray(c, float), times.shape) for c in row] for row in rows])


def run_engine(exe, case, duration, dt, tolerance, csv, particles):
    options = {**{k: v for k, v in case.items() if k != "name"},
               "duration": duration, "dt": dt, "tolerance": tolerance}
    command = [str(exe)] + [s for k, v in options.items() for s in (f"--{k}", repr(float(v)))]
    done = subprocess.run(command + ["--csv", str(csv)], capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"{exe.name}: {done.stderr.strip()}")
    data = np.genfromtxt(csv, delimiter=",", names=True)
    out = {k: data[k] for k in data.dtype.names}
    for kind, prefix in (("positions", ""), ("velocities", "V")):
        out[kind] = np.array([[data[f"{prefix}{axis}{i}"] for axis in "XYZ"] for i in range(1, particles + 1)])
    return out


def drift(values, scale):
    return np.ptp(values) / max(1.0, abs(scale))  # relative, as in the engine's diagnostics


def main(problem_name):
    folder = ROOT / "Simulations" / problem_name
    spec = importlib.util.spec_from_file_location("problem", folder / "problem.py")
    problem = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(problem)
    exe = next((p for p in (ROOT / "build/simulations/bin").glob(problem_name + "*") if p.is_file()), None)
    if exe is None:
        sys.exit(f"No build/simulations/bin/{problem_name}: build it first (see Simulations/README.md)")
    work = ROOT / "build/simulations/runs"
    work.mkdir(parents=True, exist_ok=True)

    model = LagrangianModel(problem)
    conserved = model.conserved
    angles = {name(q) for q in problem.ANGLES}
    columns, passed = {}, True
    header = f"{'case':>10} {'settings':>9} {'position':>8} {'velocity':>8}"
    for k in conserved:
        header += f" {k + ' 0':>12} {'engine':>8} {'Lagr.':>8}"
    print(header + f" {'balance':>8} {'constr.':>8} {'constr.v':>8}")
    for i, case in enumerate(problem.CASES):
        worst = {}
        for setting, engine_tol, lagrangian_tol in SETTINGS:
            eng = run_engine(exe, case, problem.DURATION, getattr(problem, "DT", DT), engine_tol,
                             work / f"{problem_name}-{case['name']}-{setting}.csv", len(problem.POSITIONS))
            ref = model.run(case, eng["t"], lagrangian_tol)
            # largest distance between the two models' particles, at each time
            position = np.linalg.norm(eng["positions"] - ref["positions"], axis=1).max(axis=0)
            velocity = np.linalg.norm(eng["velocities"] - ref["velocities"], axis=1).max()
            line = f"{case['name']:>10} {setting:>9} {position.max():8.1e} {velocity:8.1e}"
            for k in conserved:  # initial mismatch, then drift of each model
                scale = ref[k][0]
                line += (f" {abs(eng[k][0] - scale) / max(1.0, abs(scale)):12.1e}"
                         f" {drift(eng[k], scale):8.1e} {drift(ref[k], scale):8.1e}")
            line += f" {np.abs(eng['energy_balance_error']).max():8.1e}"
            print(line + f" {eng['constraint_error'].max():8.1e} {eng['constraint_velocity_error'].max():8.1e}")
            worst[setting] = position.max()
            columns["t"] = eng["t"]
            columns[f"diff-{case['name']}-{setting}"] = np.maximum(position, 1e-16)  # for a log axis
            if i == 0 and setting == SETTINGS[-1][0]:  # motion of the first case
                for k in model.names:
                    columns[k] = ref[k]
                    columns[k + "-engine"] = np.unwrap(eng[k]) if k in angles else eng[k]
        passed &= worst["tight"] <= LIMIT and worst["tight"] < worst["standard"]

    out = ROOT / "Figures/Data" / f"{problem_name}-verification.csv"
    table = np.column_stack(list(columns.values()))[::PLOT_EVERY]
    np.savetxt(out, table, fmt="%.6g", delimiter=",", header=",".join(columns), comments="")
    print(f"Check (tight position difference below {LIMIT:.0e} m and smaller than standard): "
          f"{'PASS' if passed else 'FAIL'}\nWrote {out.relative_to(ROOT)}")
    return 0 if passed else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__.splitlines()[0])
    sys.exit(main(sys.argv[1]))
