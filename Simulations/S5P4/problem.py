# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""§5 Problem 4: two masses m1 on rods, m2 sliding on the vertical axis, rotating at Omega."""

import sympy as sp

t = sp.Symbol("t")
m1, m2, a, Omega, g = sp.symbols("m1 m2 a Omega g", positive=True)
theta = sp.Function("theta")(t)
dtheta = theta.diff(t)

COORDINATES = [theta]
ANGLES = []

# The answer of the manual
LAGRANGIAN = (m1 * a**2 * (dtheta**2 + Omega**2 * sp.sin(theta)**2) + 2 * m2 * a**2 * dtheta**2 * sp.sin(theta)**2
              + 2 * (m1 + m2) * g * a * sp.cos(theta))

# Particles in the engine frame (Y up the axis, pivot at the origin): the two
# m1, then m2. The plane of the rods contains Y and u = (cos Omega t, 0, -sin Omega t).
u = sp.Matrix([sp.cos(Omega * t), 0, -sp.sin(Omega * t)])
down = sp.Matrix([0, -a * sp.cos(theta), 0])
POSITIONS = [down + a * sp.sin(theta) * u, down - a * sp.sin(theta) * u, 2 * down]
# L does not depend on t, but the rotation does work: the conserved energy
# function is the Jacobi integral E - Omega M_Y, not the energy E
ENERGY = "jacobi"

# SI units; theta from the downward axis. The rotation balances gravity at
# cos(theta) = (m1 + m2) g / (m1 a Omega^2).
CASES = [
    dict(name="oscillating", m1=1.0, m2=1.0, a=0.5, Omega=8.0, g=9.81, theta=0.5, dtheta=0.0),
    dict(name="fast", m1=0.5, m2=1.0, a=0.3, Omega=15.0, g=9.81, theta=0.7, dtheta=1.0),
]
DURATION = 5.0
