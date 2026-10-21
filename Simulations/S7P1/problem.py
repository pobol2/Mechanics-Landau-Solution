# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""Refraction/reflection at a tanh step, away from the exact threshold."""
import numpy as np
from verification import Verification, maximum, converges

STEPS = (0.008, 0.004, 0.002, 0.001)
WIDTHS = (0.2, 0.1, 0.05)
# m=1 kg, v=2 m/s, upward jump=1 J: critical incidence is 45 degrees.
# Include both sides with a 0.5 degree gap; equality is deliberately excluded.
CASES = [(1.0, a) for a in (0, 15, 30, 40, 44, 44.5, 45.5, 46, 50, 60)] + [(-0.6, a) for a in (0, 30, 60)]


def potential(x, width, jump):
    return jump * (1 + np.tanh(x / width)) / 2


def verify(exe, work):
    test = Verification("S7P1", exe, work)
    convergence, angles = [], []
    trajectories = {}
    for jump, degrees in CASES:
        angle = np.deg2rad(degrees)
        vx, vy = 2 * np.cos(angle), 2 * np.sin(angle)
        transmitted = vx*vx > 2*jump
        # Analytical sharp-step prediction; never used to generate the motion.
        prediction = np.arctan2(vy, np.sqrt(vx*vx - 2*jump)) if transmitted else np.pi - angle
        all_widths = []
        for width in WIDTHS:
            errors = []
            for h in STEPS:
                case = dict(mass=1.0, speed=2.0, jump=jump, angle=angle, width=width)
                data = test.run(f"jump{jump}-angle{degrees}-w{width}-h{h}", case, 16.0, 0.032, h)
                exits = np.flatnonzero((data["X1"] >= 1) | ((data["X1"] <= -1) & (data["VX1"] < 0)))
                if not len(exits):
                    test.check(False, f"{case}: no asymptotic exit in 16 s")
                    continue
                end = exits[0]
                data = {key: value[..., :end+1] for key, value in data.items()}
                actual_transmission = data["X1"][-1] >= 1 and data["VX1"][-1] > 0
                test.check(actual_transmission == transmitted, f"{case}: reflection threshold classification")
                measured = np.arctan2(data["VY1"][-1], data["VX1"][-1])
                # Finite endpoints have small tanh tails. Isolate integration
                # error using conservation at the measured endpoint, then
                # independently compare with the ideal half-space formula.
                final_vx2 = vx*vx - 2 * (potential(data["X1"][-1], width, jump) - potential(-1, width, jump))
                test.check(final_vx2 > 0, "positive asymptotic normal kinetic energy")
                smooth_prediction = np.arctan2(vy, (1 if transmitted else -1) * np.sqrt(max(0, final_vx2)))
                angle_error = abs(measured - prediction)
                integration_error = abs(measured - smooth_prediction)
                speed_error = abs(data["VX1"][-1] - (1 if transmitted else -1)*np.sqrt(max(0, final_vx2)))
                energy = maximum(data["energy_balance_error"])
                reconstructed = ((data["VX1"]**2 + data["VY1"]**2) / 2 + potential(data["X1"], width, jump))
                test.check(maximum(data["energy"] - reconstructed) < 1e-12, "consistent step potential")
                test.check(maximum(data["momentum_Y"] - vy) < 1e-12 and maximum(data["Z1"]) < 1e-14,
                           "tangential momentum and planar motion")
                convergence.append((jump, degrees, width, h, angle_error, integration_error, speed_error, energy, int(transmitted)))
                errors.append(speed_error)
                if h == STEPS[-1]:
                    all_widths.append(angle_error)
                    print(f"jump={jump:g}, incidence={degrees:g}, w={width:g}: "
                          f"{'transmitted' if transmitted else 'reflected'}, angle={np.rad2deg(measured):.9g} deg, "
                          f"sharp error={angle_error:.3e} rad, integration={integration_error:.3e}, energy={energy:.3e}")
                    test.check(speed_error < 1e-7 and energy < 1e-8, "tight integration and energy tolerances")
                    if width == WIDTHS[-1]:
                        test.check(angle_error < 1e-6, "sharp-step angle tolerance 1e-6 rad")
                        if transmitted:
                            angles.append((jump, degrees, np.rad2deg(prediction), np.rad2deg(measured)))
                        if jump == 1 and degrees in (30, 60):
                            trajectories[degrees] = data
            test.check(len(errors) == len(STEPS) and converges(errors, floor=1e-11),
                       f"jump={jump}, incidence={degrees}, width={width}: step convergence")
        # Reflected angles and normal incidence already agree at all widths;
        # their finite-width paths need not equal an abrupt-step trajectory.
        if transmitted and degrees != 0:
            test.check(len(all_widths) == len(WIDTHS) and converges(all_widths, floor=1e-8),
                       f"jump={jump}, incidence={degrees}: width convergence")
    test.save("angles", dict(zip(("jump", "incident", "predicted", "measured"), np.array(angles).T)))
    for degrees, data in trajectories.items():
        test.save(f"trajectory-{degrees}", dict(t=data["t"], x=data["X1"], y=data["Y1"]))
    test.save("convergence", dict(zip(("jump", "incident", "width", "step", "angle_error", "integration_error", "speed_error", "energy", "transmitted"), np.array(convergence).T)))
    return test.finish()
