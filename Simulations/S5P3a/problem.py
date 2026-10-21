# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""§5 Problem 3(a): pendulum whose point of support moves uniformly on a vertical circle."""

import sympy as sp

t = sp.Symbol("t")
m, l, a, gamma, g = sp.symbols("m l a gamma g", positive=True)
phi = sp.Function("phi")(t)
dphi = phi.diff(t)

COORDINATES = [phi]
ANGLES = [phi]

# The answer of the manual
LAGRANGIAN = (sp.Rational(1, 2) * m * l**2 * dphi**2 + m * a * l * gamma**2 * sp.sin(phi - gamma * t)
              + m * g * l * sp.cos(phi))

# The particle in the engine frame (X = x, Y = -y), the support at
# (a cos(gamma t), -a sin(gamma t)) in the figure
POSITIONS = [sp.Matrix([a * sp.cos(gamma * t) + l * sp.sin(phi), a * sp.sin(gamma * t) - l * sp.cos(phi), 0])]
# L depends on t (the support does work): no conserved energy
ENERGY = None

# SI units; phi from the downward vertical, positive towards +x (the figure)
CASES = [
    dict(name="tumbling", m=0.5, l=0.8, a=0.4, gamma=7.0, g=9.81, phi=-0.3, dphi=1.0),
    dict(name="swinging", m=1.0, l=1.0, a=0.3, gamma=2.0, g=9.81, phi=0.5, dphi=0.0),
]
DURATION = 5.0
