# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""§11 Problem 2(a): period of oscillation in U = A|x|^n as a function of E.

The period is measured from the engine trajectory alone, between successive
crossings of the equilibrium X=0 in the same direction (X decreasing). The
RK4 steps, sample intervals and duration are fixed times in seconds, the same
for every case, so that nothing in the runs is scaled with the expected period.
The analytical formula is evaluated afterwards, only for the comparison.
"""
import numpy as np
from scipy.integrate import quad
from scipy.special import beta, gamma
from verification import Verification, maximum, converges
from S11P1.problem import crossings  # same equilibrium-crossing measurement

EXPONENTS = (2, 4, 6)
PARAMETERS = ((1.0, 1.0), (0.5, 3.0))  # (m in kg, A in J/m^n)
ENERGIES = (0.1, 0.3, 1.0, 3.0, 10.0)  # J
# Binary fractions of a second, so that samples fall exactly on RK4 steps.
STEPS = (1/64, 1/128, 1/256, 1/512, 1/1024, 1/2048, 1/4096)  # RK4 steps (s), sampled every SAMPLES[0]
SAMPLES = (1/32, 1/64, 1/128, 1/256)  # sample intervals (s), at the finest step
DURATION = 64.0  # s: at least eight periods in every case


def measure(data, every=1):
    """Mean period over all complete cycles, and the largest deviation of a
    single cycle from it, from every `every`-th sample."""
    times = crossings(data["t"][::every], data["X1"][::every], data["VX1"][::every])
    cycles = np.diff(times)
    mean = (times[-1] - times[0]) / len(cycles)
    return mean, len(cycles), maximum(cycles - mean)


# ---- Analytical results of the solution, for comparison only ----

def formula(n, mass, A, E):
    # The solution's answer, T = (2/n) sqrt(2 pi m/E) (E/A)^(1/n) Gamma(1/n) / Gamma(1/2 + 1/n)
    return 2 / n * np.sqrt(2 * np.pi * mass / E) * (E / A)**(1 / n) * gamma(1 / n) / gamma(0.5 + 1 / n)


def quadrature(n, mass, A, E):
    # Independent evaluation of the step before the substitution u = y^n,
    # 2 sqrt(2m/E) (E/A)^(1/n) int_0^1 dy / sqrt(1 - y^n), with the endpoint
    # singularity (1 - y)^(-1/2) handled by the quadrature weight and
    # 1 - y^n = (1 - y) sum_{k<n} y^k for integer n.
    integral = quad(lambda y: 1 / np.sqrt(sum(y**k for k in range(n))), 0, 1,
                    weight="alg", wvar=(0, -0.5), epsabs=0, epsrel=1e-13)[0]
    return 2 * np.sqrt(2 * mass / E) * (E / A)**(1 / n) * integral


def verify(exe, work):
    test = Verification("S11P2a", exe, work)
    every = round(SAMPLES[0] / SAMPLES[-1])
    rows, convergence, slopes = [], [], []
    print(f"steps {STEPS} s; sample intervals {SAMPLES} s; duration {DURATION} s")
    for n in EXPONENTS:
        for group, (mass, A) in enumerate(PARAMETERS):
            measured_set = []
            for E in ENERGIES:
                case = dict(mass=mass, A=A, n=n, energy=E)
                label = f"n{n}-m{mass:g}-A{A:g}-E{E:g}"
                by_step = []
                for h in STEPS:
                    finest = h == STEPS[-1]
                    data = test.run(f"{label}-h{h:g}", case, DURATION, SAMPLES[-1] if finest else SAMPLES[0], h)
                    by_step.append(measure(data, every if finest else 1))
                by_sample = [measure(data, round(s / SAMPLES[-1])) for s in SAMPLES]

                # Motion checks on the finest run
                x, v = data["X1"], data["VX1"]
                amplitude = (E / A)**(1 / n)
                test.check(abs(x[0] / amplitude - 1) < 1e-15 and v[0] == 0, f"{label}: release at rest from (E/A)^(1/n)")
                test.check(maximum(data["Y1"]) + maximum(data["Z1"]) + maximum(data["VY1"]) + maximum(data["VZ1"]) == 0,
                           f"{label}: one-dimensional motion")
                reconstructed = mass * v**2 / 2 + A * np.abs(x)**n
                test.check(maximum(reconstructed - data["energy"]) < 1e-13 * max(1, E),
                           f"{label}: engine energy is m v^2/2 + A|x|^n")
                test.check(abs(data["energy"][0] / E - 1) < 1e-14, f"{label}: initial energy E")
                energy = max(maximum(data["energy"] / E - 1), maximum(data["energy_balance_error"]))
                test.check(energy < 1e-9, f"{label}: relative energy drift below 1e-9")
                test.check(maximum(x) <= amplitude * (1 + 1e-9), f"{label}: oscillation within the turning points")

                periods = [p for p, _, _ in by_step]
                samples = [p for p, _, _ in by_sample]
                measured, cycles, spread = by_sample[-1]
                test.check(cycles >= 8, f"{label}: at least eight complete periods")
                test.check(len({c for _, c, _ in by_step + by_sample}) == 1, f"{label}: same cycles at every setting")
                step_differences = [abs(a - b) / measured for a, b in zip(periods, periods[1:])]
                sample_differences = [abs(a - b) / measured for a, b in zip(samples, samples[1:])]
                test.check(converges(step_differences), f"{label}: integration-step convergence")
                test.check(converges(sample_differences), f"{label}: crossing-resolution convergence")
                measured_set.append(measured)

                # Comparison with the solution, after the measurement
                reference = formula(n, mass, A, E)
                test.check(abs(quadrature(n, mass, A, E) / reference - 1) < 1e-13 and
                           abs(2 / n * np.sqrt(2 * mass / E) * (E / A)**(1 / n) * beta(1 / n, 0.5) / reference - 1) < 1e-14,
                           f"{label}: the Gamma formula agrees with the beta function and a quadrature")
                error = abs(measured / reference - 1)
                test.check(error < 1e-9, f"{label}: measured period within 1e-9 of the formula")
                rows.append((n, group, mass, A, E, measured, reference, max(error, 1e-16), cycles,
                             spread / measured, energy, step_differences[-1], sample_differences[-1]))
                for kind, settings, values in ((0, STEPS, periods), (1, SAMPLES, samples)):
                    for s, p in zip(settings, values):
                        convergence.append((n, group, E, kind, s if kind == 0 else STEPS[-1],
                                            s if kind == 1 else SAMPLES[0], p, abs(p / reference - 1)))
                print(f"n={n} m={mass:g} A={A:g} E={E:5g}: T={measured:.12f} s formula={reference:.12f} s "
                      f"error={error:.2e} ({cycles} periods, cycle spread {spread / measured:.1e}); "
                      f"dh={', '.join(f'{d:.1e}' for d in step_differences)}; "
                      f"ddt={', '.join(f'{d:.1e}' for d in sample_differences)}; energy={energy:.1e}")

            # Energy scaling, from the measured periods alone: least-squares
            # slope of log T against log E, and the largest deviation from it
            fit = np.polyfit(np.log(ENERGIES), np.log(measured_set), 1)
            residual = maximum(np.log(measured_set) - np.polyval(fit, np.log(ENERGIES)))
            expected = 1 / n - 1 / 2
            test.check(abs(fit[0] - expected) < 1e-10 and residual < 1e-10,
                       f"n={n} m={mass:g} A={A:g}: T proportional to E^(1/n - 1/2)")
            slopes.append((n, group, fit[0], expected, residual))
            print(f"n={n} m={mass:g} A={A:g}: slope {fit[0]:+.12f} (1/n-1/2 = {expected:+.12f}, "
                  f"difference {abs(fit[0] - expected):.1e}), log residual {residual:.1e}")

    # Dependence on m and A, from the measured periods alone: at equal E,
    # T2/T1 = sqrt(m2/m1) (A1/A2)^(1/n)
    table = np.array(rows)
    (m1, A1), (m2, A2) = PARAMETERS
    for n in EXPONENTS:
        first = table[(table[:, 0] == n) & (table[:, 1] == 0), 5]
        second = table[(table[:, 0] == n) & (table[:, 1] == 1), 5]
        expected = np.sqrt(m2 / m1) * (A1 / A2)**(1 / n)
        deviation = maximum(second / first / expected - 1)
        test.check(deviation < 1e-9, f"n={n}: ratio of the two parameter sets")
        print(f"n={n}: T(m={m2:g}, A={A2:g}) / T(m={m1:g}, A={A1:g}) = sqrt(m2/m1) (A1/A2)^(1/n) "
              f"= {expected:.12f} within {deviation:.1e}")
    print(f"largest relative error {table[:, 7].max():.2e}; largest energy drift {table[:, 10].max():.1e}; "
          f"largest last step change {table[:, 11].max():.1e}; largest last sample change {table[:, 12].max():.1e}; "
          f"periods {int(table[:, 8].min())} to {int(table[:, 8].max())}; "
          f"T from {table[:, 5].min():.3f} to {table[:, 5].max():.3f} s")

    columns = ("n", "group", "mass", "A", "energy", "measured", "formula", "error", "periods", "spread",
               "drift", "step_change", "sample_change")
    test.save("periods", dict(zip(columns, table.T)))
    grid = np.geomspace(0.07, 14, 61)
    curves = dict(energy=grid)
    for n in EXPONENTS:
        for group, (mass, A) in enumerate(PARAMETERS):
            curves[f"n{n}-g{group}"] = formula(n, mass, A, grid)
    test.save("curves", curves)
    test.save("convergence", dict(zip(("n", "group", "energy", "refined", "step", "sample", "period", "error"),
                                      np.array(convergence).T)))
    return test.finish()
