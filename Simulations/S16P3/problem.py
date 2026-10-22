# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""§16 Problem 3: range of the angle between the two particles after a
disintegration, in the L system.

A particle moving with the velocity V along X breaks into two parts, pushed
apart by a short-range repulsion that releases the disintegration energy
epsilon (engine.cpp). The angle theta between the two final velocities is
measured from the engine trajectory alone, for emission angles theta0 over
[0, pi], and its extremes are searched by minimizing over theta0 with engine
runs. The solution's formulas are evaluated afterwards, only for the comparison.
"""
import numpy as np
from scipy.optimize import minimize_scalar
from verification import Verification, maximum, converges

RANGE = 1.0  # m, range R of the repulsion; the parts start R/2 apart
# Masses (kg) and energy (J) giving the C-system speeds a = v10 and b = v20
UNEQUAL = dict(mass1=2.0, mass2=1.0, energy=3.0)  # a = 1, b = 2 m/s
EQUAL = dict(mass1=1.0, mass2=1.0, energy=1.0)    # a = b = 1 m/s
# (masses, V in m/s, label): V = 0, slow, V = a, middle, V = b, fast; then a = b = V
CASES = [(UNEQUAL, 0.0, "rest"), (UNEQUAL, 0.5, "slow"), (UNEQUAL, 1.0, "V=a"), (UNEQUAL, 1.5, "middle"),
         (UNEQUAL, 2.0, "V=b"), (UNEQUAL, 3.0, "fast"), (EQUAL, 1.0, "a=b")]
GRID = np.arange(0, 181, 5)  # emission angles theta0 (degrees)
DURATION = 2.0  # s: the parts separate (r > R) well before
SAMPLE = 1/16   # s
STEPS = (1/256, 1/512, 1/1024, 1/2048, 1/4096)  # RK4 steps (s); the last one is used for the measurements


def speeds(masses):
    """C-system speeds from the momentum p0 of (16.2), for the comparison only."""
    m1, m2, epsilon = masses["mass1"], masses["mass2"], masses["energy"]
    p0 = np.sqrt(2 * epsilon * m1 * m2 / (m1 + m2))
    return p0 / m1, p0 / m2


def measure(data, masses):
    """Angle between the final velocities, the C-system velocities and the
    largest velocity change after the parts separated."""
    M = masses["mass1"] + masses["mass2"]
    v1 = np.array([data[k][-1] for k in ("VX1", "VY1", "VZ1")])
    v2 = np.array([data[k][-1] for k in ("VX2", "VY2", "VZ2")])
    theta = np.arctan2(np.linalg.norm(np.cross(v1, v2)), v1 @ v2)
    centre = np.array([data[f"momentum_{k}"][-1] for k in "XYZ"]) / M
    free = data["separation"] > RANGE
    flight = max(maximum(data[k][free] - data[k][-1]) for k in ("VX1", "VY1", "VX2", "VY2"))
    return theta, v1 - centre, v2 - centre, flight


# ---- Analytical results of the solution, for comparison only ----

def formula(V, a, b, theta0):
    # cot(theta) = [V^2 + (a - b) V cos(theta0) - a b] / [(a + b) V sin(theta0)], theta in [0, pi]
    return np.arctan2((a + b) * V * np.sin(theta0), V**2 + (a - b) * V * np.cos(theta0) - a * b)


def alpha(V, a, b):
    return np.arcsin((a + b) * V / (V**2 + a * b))


def verify(exe, work):
    test = Verification("S16P3", exe, work)
    rows, extrema, curves = [], [], {"emission": np.linspace(0, 180, 361)}
    for masses, V, label in CASES:
        a, b = speeds(masses)
        case = dict(**masses, range=RANGE, speed=V)
        cache = {}

        def run(theta0, h=STEPS[-1]):
            key = (theta0, h)
            if key not in cache:
                data = test.run(f"{label}-{theta0:.12g}-h{h:g}", dict(case, emission=theta0), DURATION, SAMPLE, h)
                cache[key] = data
            return cache[key]

        # Emission angles: the grid, without a part at rest in the L system
        # (V = a at theta0 = pi, V = b at theta0 = 0), plus angles near those ends
        angles = [d for d in GRID if not (V == a and d == 180) and not (V == b and d == 0)]
        if V == a:
            angles += [179.0, 179.9]
        if V == b:
            angles = [0.1, 1.0] + angles
        angles = np.deg2rad(sorted(angles))
        measured, scales = [], []
        for theta0 in angles:
            data = run(theta0)
            theta, c1, c2, flight = measure(data, masses)
            name = f"{label} theta0={np.rad2deg(theta0):.1f}"
            # Motion checks
            test.check(maximum(data["Z1"]) + maximum(data["Z2"]) + maximum(data["VZ1"]) + maximum(data["VZ2"]) == 0,
                       f"{name}: planar motion")
            test.check(data["separation"][-1] > 2 * RANGE and flight < 1e-15, f"{name}: free flight after separation")
            M = masses["mass1"] + masses["mass2"]
            momentum = max(maximum(data["momentum_X"] - M * V), maximum(data["momentum_Y"]))
            energy = maximum(data["energy"] - data["energy"][0]) / max(1, abs(data["energy"][0]))
            test.check(momentum < 1e-13 and energy < 1e-11, f"{name}: momentum and energy conserved")
            # The C-system velocities: opposite, along theta0, with the speeds of (16.2)
            direction = np.array([np.cos(theta0), np.sin(theta0), 0])
            test.check(np.linalg.norm(c1 - np.linalg.norm(c1) * direction) < 1e-13 and
                       np.linalg.norm(c2 + np.linalg.norm(c2) * direction) < 1e-13,
                       f"{name}: C-system velocities along +-(cos theta0, sin theta0)")
            test.check(abs(np.linalg.norm(c1) - a) < 1e-11 and abs(np.linalg.norm(c2) - b) < 1e-11,
                       f"{name}: C-system speeds v10, v20 from the energy epsilon")
            measured.append(theta)
            # The direction of a slow particle is sensitive to velocity errors:
            # scale the angle tolerance by b over the smaller L-system speed
            slowest = min(np.hypot(data["VX1"][-1], data["VY1"][-1]), np.hypot(data["VX2"][-1], data["VY2"][-1]))
            scales.append(max(1.0, b / slowest))
            reference = formula(V, a, b, theta0)
            rows.append((V, a, b, np.rad2deg(theta0), np.rad2deg(theta), np.rad2deg(reference),
                         max(abs(theta - reference) / scales[-1], 1e-16)))  # for a log axis
        measured = np.array(measured)

        # Extreme angle, searched with engine runs (slow: smallest, fast: largest)
        extreme = None
        if label in ("slow", "fast"):
            sign = 1 if label == "slow" else -1
            found = minimize_scalar(lambda t: sign * measure(run(t), masses)[0], bounds=(1e-3, np.pi - 1e-3),
                                    method="bounded", options=dict(xatol=1e-10))
            extreme = (found.x, measure(run(found.x), masses)[0])
            # Step convergence of the measured extreme angle
            values = [measure(run(found.x, h), masses)[0] for h in STEPS]
            differences = [abs(p - q) for p, q in zip(values, values[1:])]
            test.check(converges(differences, 1e-14), f"{label}: integration-step convergence of the extreme angle")
            print(f"{label}: extreme at theta0={np.rad2deg(found.x):.6f} deg, theta={np.rad2deg(extreme[1]):.12f} deg; "
                  f"step differences {', '.join(f'{d:.1e}' for d in differences)} rad")

        # Range of the measured angles, then the comparison with the solution
        low, high = measured.min(), measured.max()
        if extreme is not None:
            low, high = min(low, extreme[1]), max(high, extreme[1])
        span = (np.rad2deg(low), np.rad2deg(high))
        scales = np.array(scales)
        errors = np.abs(measured - formula(V, a, b, angles))
        test.check(np.all(errors < 1e-11 * scales),
                   f"{label}: measured theta(theta0) within 1e-11 b/min|v| rad of the cot formula")
        decreasing = np.all(np.diff(measured) < 0)
        tol = 1e-12
        if label == "rest":
            test.check(maximum(measured - np.pi) < tol, f"{label}: theta = pi")
        elif label == "slow":
            bound = np.pi - alpha(V, a, b)
            test.check(abs(high - np.pi) < tol and np.all(measured > bound - tol), f"{label}: pi - alpha <= theta <= pi")
            test.check(abs(extreme[1] - bound) < 1e-11, f"{label}: measured smallest angle equals pi - alpha")
        elif label == "middle":
            test.check(decreasing and abs(high - np.pi) < tol and abs(low) < tol, f"{label}: theta from pi to 0")
        elif label == "fast":
            bound = alpha(V, a, b)
            test.check(abs(low) < tol and np.all(measured < bound + tol), f"{label}: 0 <= theta <= alpha")
            test.check(abs(extreme[1] - bound) < 1e-11, f"{label}: measured largest angle equals alpha")
        elif label == "V=a":
            test.check(decreasing and abs(high - np.pi) < tol and low > np.pi / 2, f"{label}: pi/2 < theta <= pi")
        elif label == "V=b":
            test.check(decreasing and abs(low) < tol and high < np.pi / 2, f"{label}: 0 <= theta < pi/2")
        elif label == "a=b":
            test.check(np.all(np.abs(measured - np.pi / 2) < 1e-11 * scales), f"{label}: theta = pi/2")
        if extreme is not None:
            stationary = np.arccos((b - a) * V / (V**2 - a * b))
            test.check(abs(extreme[0] - stationary) < 1e-4,
                       f"{label}: extreme at cos(theta0) = (b - a) V / (V^2 - a b)")
            extrema.append((V, np.rad2deg(extreme[0]), np.rad2deg(extreme[1]), np.rad2deg(stationary),
                            np.rad2deg(alpha(V, a, b)), max(abs(extreme[1] - (bound)), 1e-16)))
        print(f"{label:6s} V={V:g} a={a:g} b={b:g}: measured {span[0]:.9f} to {span[1]:.9f} deg over "
              f"{len(angles)} emission angles; largest |theta - formula| = {errors.max():.1e} rad, "
              f"{(errors / scales).max():.1e} rad scaled by min|v|/b")
        if label != "a=b":
            curve = np.rad2deg(formula(V, a, b, np.deg2rad(curves["emission"])))
            # no direction for a part at rest in the L system (V = a at pi, V = b at 0)
            curve[(V == a) & (curves["emission"] == 180) | (V == b) & (curves["emission"] == 0)] = np.nan
            curves[f"V{round(100 * V):03d}"] = curve

    test.save("angles", dict(zip(("speed", "a", "b", "emission", "measured", "formula", "error"), np.array(rows).T)))
    test.save("extrema", dict(zip(("speed", "emission", "measured", "stationary", "alpha", "error"),
                                  np.array(extrema).T)))
    test.save("curves", curves)
    return test.finish()
