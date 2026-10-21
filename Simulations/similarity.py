# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""Independent engine runs for mechanical similarity in an anharmonic well."""
import numpy as np
from scipy.special import ellipj
from verification import Verification, maximum, converges

STEPS = (0.04, 0.02, 0.01)
CASES = [dict(mass=1.0, k=1.0, alpha=1.0, amplitude=1.0, scale=1.0),
         dict(mass=1.5, k=0.7, alpha=1.3, amplitude=0.8, scale=1.0)]


def exact(case, times):
    # x=A cn(omega t | p), cn''=(2p-1)cn-2p cn^3. This independent
    # closed-form reference is evaluated only AFTER running the engine.
    A, k, alpha, mass, scale = (case[key] for key in ("amplitude", "k", "alpha", "mass", "scale"))
    omega = np.sqrt(scale * (k + alpha * A*A) / mass)
    p = alpha * A*A / (2 * (k + alpha * A*A))
    sn, cn, dn, _ = ellipj(omega * times, p)
    return A * cn, -A * omega * sn * dn


def verify_similarity(name, exe, work):
    test = Verification(name, exe, work)
    mass_change = name == "S10P1"
    beta = 2.0 if mass_change else 0.5
    rows = []
    for i, case in enumerate(CASES):
        changed = {**case, "mass": 4 * case["mass"]} if mass_change else {**case, "scale": 4.0}
        histories = []
        runs = []
        for h in STEPS:
            base = test.run(f"case{i}-base-h{h}", case, 16.0, 0.08, h)
            other = test.run(f"case{i}-scaled-h{h}", changed, 32.0 if mass_change else 16.0,
                             0.08 * beta, h)
            n = len(base["t"])
            test.check(np.allclose(other["t"][:n], beta * base["t"], atol=1e-12, rtol=0),
                       "corresponding times must align without interpolation")
            dx = base["X1"] - other["X1"][:n]
            dv = base["VX1"] - beta * other["VX1"][:n]
            analytic_x = analytic_v = energy = 0.0
            for parameters, data in ((case, base), (changed, other)):
                x, v = exact(parameters, data["t"])
                analytic_x = max(analytic_x, maximum(data["X1"] - x))
                analytic_v = max(analytic_v, maximum(data["VX1"] - v))
                reconstructed = (parameters["mass"] * data["VX1"]**2 / 2 + parameters["scale"] *
                                 (parameters["k"] * data["X1"]**2 / 2 + parameters["alpha"] * data["X1"]**4 / 4))
                test.check(maximum(reconstructed - data["energy"]) < 1e-12,
                           "engine potential must match the stated scaled U")
                energy = max(energy, maximum(data["energy_balance_error"]),
                             maximum(data["energy"] - data["energy"][0]) / max(1, abs(data["energy"][0])))
                test.check(data["X1"][0] == parameters["amplitude"] and data["VX1"][0] == 0,
                           "release from the same position at rest")
                test.check(maximum(data["Y1"]) + maximum(data["Z1"]) +
                           maximum(data["VY1"]) + maximum(data["VZ1"]) < 1e-14,
                           "one-dimensional motion")
            metrics = (maximum(dx), maximum(dv), analytic_x, analytic_v, energy)
            rows.append((i, h, *metrics))
            histories.append(metrics)
            runs.append((base, other))
            print(f"case {i}, h={h:g}: scaling x={metrics[0]:.3e} m, v={metrics[1]:.3e} m/s; "
                  f"analytic x={analytic_x:.3e}, v={analytic_v:.3e}; energy={energy:.3e}")
        for j, label in enumerate(("scaling position", "scaling velocity", "analytic position", "analytic velocity", "energy")):
            test.check(converges([v[j] for v in histories]), f"case {i}: {label} convergence")
        # Absolute errors over several oscillations. Bounds allow RK4 phase error
        # over 16 s (32 s for the heavy mass), including the faster 4U orbit.
        limits = (1e-6, 3e-6, 2e-6, 5e-6, 1e-7)
        test.check(all(a <= b for a, b in zip(histories[-1], limits)), f"case {i}: tight tolerances {limits}")
        # Self-convergence also catches common errors hidden by similarity.
        for component in (0, 1):
            differences = [maximum(runs[j][component]["X1"] - runs[j+1][component]["X1"]) for j in (0, 1)]
            test.check(converges(differences), f"case {i}: trajectory self-convergence")
        if i == 0:
            base, other = runs[-1]
            test.save("verification", dict(t=base["t"], base=base["X1"],
                      scaled=other["X1"][:len(base["t"])],
                      difference=np.abs(base["X1"] - other["X1"][:len(base["t"])])))
            # Physical-time curves also use actual samples, on their common grid.
            physical_t = base["t"][::2] if mass_change else base["t"]
            physical_base = base["X1"][::2] if mass_change else base["X1"]
            physical_other = other["X1"][:len(physical_t)] if mass_change else other["X1"][::2]
            test.save("physical", dict(t=physical_t, base=physical_base, scaled=physical_other))
    test.save("convergence", dict(zip(("case", "step", "position", "velocity", "analytic_position", "analytic_velocity", "energy"), np.array(rows).T)))
    return test.finish()
