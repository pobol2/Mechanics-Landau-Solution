# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""§11 Problem 1: period of a simple pendulum as a function of the amplitude.

The period is measured from the engine trajectory alone, between successive
crossings of the equilibrium X=0 in the same direction (X decreasing). The
analytical formulas are evaluated afterwards, only for the comparison.
"""
import numpy as np
from scipy.interpolate import CubicHermiteSpline
from scipy.optimize import brentq
from scipy.special import ellipk
from verification import Verification, maximum, converges

MASS, LENGTH, G = 1.0, 1.0, 9.81  # SI units
T0 = 2 * np.pi * np.sqrt(LENGTH / G)  # small-angle period
STRING = (10, 20, 30, 40, 50, 60, 70, 80, 89)  # degrees; a string stays taut
ROD = (100, 120, 140, 160, 170)  # rigid-rod extension: a string would go slack
# Binary fractions of a second, so that samples fall exactly on RK4 steps.
STEPS = (1/32, 1/64, 1/128, 1/256, 1/512, 1/1024)  # RK4 steps (s), sampled every SAMPLES[0]
SAMPLES = (1/32, 1/64, 1/128, 1/256)  # sample intervals (s), at the finest step
DURATION = 32.0  # s: at least five periods up to 170 degrees


def crossings(t, x, v):
    """Times at which x decreases through 0: root of the cubic Hermite
    interpolant of the sampled positions and velocities on each bracketing
    interval (error of order dt^4)."""
    out = []
    for i in np.flatnonzero((x[:-1] > 0) & (x[1:] <= 0)):
        spline = CubicHermiteSpline(t[i:i+2], x[i:i+2], v[i:i+2])
        out.append(brentq(spline, t[i], t[i+1], xtol=1e-15, rtol=1e-15))
    return np.array(out)


def measure(data, every=1):
    """Mean period over all complete cycles, and the largest deviation of a
    single cycle from it, from every `every`-th sample."""
    times = crossings(data["t"][::every], data["X1"][::every], data["VX1"][::every])
    cycles = np.diff(times)
    mean = (times[-1] - times[0]) / len(cycles)
    return mean, len(cycles), maximum(cycles - mean)


# ---- Analytical results of the solution (T/T0), for comparison only ----

def exact(phi0):
    # T = 4 sqrt(l/g) K(k) with the modulus k = sin(phi0/2). SciPy's ellipk
    # takes the parameter m = k^2, not k.
    k = np.sin(phi0 / 2)
    return 2 * ellipk(k * k) / np.pi


def exact_agm(phi0):
    # Independent evaluation, K(k) = pi / (2 AGM(1, sqrt(1-k^2))), in the modulus
    a, b = 1.0, np.cos(phi0 / 2)
    for _ in range(64):  # quadratic convergence; a and b may end one rounding apart
        a, b = (a + b) / 2, np.sqrt(a * b)
        if abs(a - b) <= 4e-16 * a:
            break
    return 1 / a


def exact_series(phi0):
    # The solution's sum over n of [(2n-1)!!/(2n)!! sin^n(phi0/2)]^2
    k2, term, total, n = np.sin(phi0 / 2)**2, 1.0, 1.0, 0
    while term > 1e-17 * total:
        n += 1
        term *= ((2*n - 1) / (2*n))**2 * k2
        total += term
    return total


def expansion(phi0, order):
    # Truncations of 1 + phi0^2/16 + 11 phi0^4/3072 + ...
    return 1 + (order >= 2) * phi0**2 / 16 + (order >= 4) * 11 * phi0**4 / 3072


def verify(exe, work):
    test = Verification("S11P1", exe, work)
    every = round(SAMPLES[0] / SAMPLES[-1])
    rows, convergence = [], []
    print(f"T0 = {T0:.12f} s; steps {STEPS} s; sample intervals {SAMPLES} s")
    for degrees in STRING + ROD:
        phi0 = np.deg2rad(degrees)
        case = dict(mass=MASS, length=LENGTH, g=G, amplitude=phi0)
        by_step, by_sample = [], []
        for h in STEPS:
            finest = h == STEPS[-1]
            data = test.run(f"amplitude{degrees}-h{h:g}", case, DURATION, SAMPLES[-1] if finest else SAMPLES[0], h)
            by_step.append(measure(data, every if finest else 1))
        by_sample = [measure(data, round(s / SAMPLES[-1])) for s in SAMPLES]

        # Motion checks on the finest run
        x, y, z, vx, vy, vz = (data[k] for k in ("X1", "Y1", "Z1", "VX1", "VY1", "VZ1"))
        test.check(abs(x[0] - LENGTH * np.sin(phi0)) < 1e-15 and abs(y[0] + LENGTH * np.cos(phi0)) < 1e-15
                   and vx[0] == vy[0] == 0, f"{degrees} deg: release at rest from the amplitude")
        test.check(maximum(z) + maximum(vz) < 1e-14, f"{degrees} deg: planar motion")
        speed2 = vx**2 + vy**2 + vz**2
        reconstructed = MASS * speed2 / 2 + MASS * G * y
        test.check(maximum(reconstructed - data["energy"]) < 1e-12, f"{degrees} deg: engine energy is T + m g Y")
        energy = max(maximum(data["energy_balance_error"]),
                     maximum(data["energy"] - data["energy"][0]) / max(1, abs(data["energy"][0])))
        r = np.sqrt(x**2 + y**2 + z**2)
        length_error = maximum(r - LENGTH)
        radial_speed = maximum((x * vx + y * vy + z * vz) / r)
        engine_constraint = max(data["constraint_error"].max(), data["constraint_velocity_error"].max())
        test.check(energy < 1e-9, f"{degrees} deg: scaled energy drift below 1e-9")
        test.check(max(length_error, radial_speed, engine_constraint) < 1e-12,
                   f"{degrees} deg: rod length and radial velocity residuals below 1e-12")
        # Rod tension over m g, from the sampled state: N = m v^2/l + m g cos(phi)
        tension = np.min(speed2 / (G * LENGTH) - y / LENGTH)
        string = degrees < 90
        test.check((tension > 0) == string, f"{degrees} deg: rod in tension exactly when below 90 deg")
        test.check(maximum(np.unwrap(data["phi"])) <= phi0 + 1e-9, f"{degrees} deg: oscillation within the amplitude")

        periods = [p for p, _, _ in by_step]
        samples = [p for p, _, _ in by_sample]
        measured, cycles, spread = by_sample[-1]
        test.check(cycles >= 5, f"{degrees} deg: at least five complete periods")
        test.check(len({c for _, c, _ in by_step + by_sample}) == 1, f"{degrees} deg: same cycles at every setting")
        step_differences = [abs(a - b) / T0 for a, b in zip(periods, periods[1:])]
        sample_differences = [abs(a - b) / T0 for a, b in zip(samples, samples[1:])]
        test.check(converges(step_differences), f"{degrees} deg: integration-step convergence")
        test.check(converges(sample_differences), f"{degrees} deg: crossing-resolution convergence")

        # Comparison with the solution, after the measurement
        ratio = measured / T0
        reference = exact(phi0)
        test.check(abs(exact_agm(phi0) / reference - 1) < 1e-14 and abs(exact_series(phi0) / reference - 1) < 1e-13,
                   f"{degrees} deg: K(k) from SciPy (parameter k^2), the AGM and the solution's series agree")
        error = abs(ratio / reference - 1)
        test.check(error < 1e-9, f"{degrees} deg: measured period within 1e-9 of the exact formula")
        truncations = [expansion(phi0, order) for order in (0, 2, 4)]
        measured_truncation = [abs(s / ratio - 1) for s in truncations]
        analytic_truncation = [abs(s / reference - 1) for s in truncations]
        rows.append((degrees, ratio, reference, *truncations, max(error, 1e-16), int(string), tension, cycles,
                     spread / T0, energy, max(length_error, radial_speed, engine_constraint),
                     *measured_truncation))
        for kind, settings, values in ((0, STEPS, periods), (1, SAMPLES, samples)):
            for s, p in zip(settings, values):
                convergence.append((degrees, kind, s if kind == 0 else STEPS[-1], s if kind == 1 else SAMPLES[0],
                                    p / T0, abs(p / T0 / reference - 1)))
        print(f"{degrees:3d} deg {'string' if string else 'rod   '}: T/T0={ratio:.12f} exact={reference:.12f} "
              f"error={error:.2e} ({cycles} periods, cycle spread {spread / T0:.1e}); "
              f"dh={', '.join(f'{d:.1e}' for d in step_differences)}; "
              f"ddt={', '.join(f'{d:.1e}' for d in sample_differences)}; "
              f"energy={energy:.1e}, |r|-l={length_error:.1e}, r.v={radial_speed:.1e}, "
              f"engine={engine_constraint:.1e}, min N/mg={tension:+.3f}; "
              f"truncation small/phi^2/phi^4 measured {', '.join(f'{e:.2e}' for e in measured_truncation)}"
              f" analytic {', '.join(f'{e:.2e}' for e in analytic_truncation)}")

    # Where the truncated expansions lose accuracy (analytical, for the text)
    for order in (0, 2, 4):
        for level in (1e-4, 1e-3, 1e-2):
            angle = brentq(lambda a: abs(expansion(a, order) / exact(a) - 1) - level, 1e-3, np.pi - 1e-3)
            print(f"truncation through phi0^{order}: relative error {level:.0e} at {np.rad2deg(angle):.1f} deg")

    columns = ("amplitude", "measured", "exact", "small", "quadratic", "quartic", "error", "string", "tension",
               "periods", "spread", "energy", "constraint", "measured_small", "measured_quadratic", "measured_quartic")
    test.save("periods", dict(zip(columns, np.array(rows).T)))
    grid = np.deg2rad(np.arange(1, 175.5, 0.5))
    reference = exact(grid)
    curves = dict(amplitude=np.rad2deg(grid), exact=reference)
    for order, label in ((0, "small"), (2, "quadratic"), (4, "quartic")):
        curves[label] = expansion(grid, order)
        curves[f"error_{label}"] = np.maximum(np.abs(curves[label] / reference - 1), 1e-16)  # for a log axis
    test.save("curves", curves)
    test.save("convergence", dict(zip(("amplitude", "refined", "step", "sample", "period", "error"),
                                      np.array(convergence).T)))
    return test.finish()
