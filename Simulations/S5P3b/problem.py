# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""§5 Problem 3(b): pendulum whose point of support oscillates horizontally, x = a cos(gamma t)."""

import sympy as sp

t = sp.Symbol("t")
m, l, a, gamma, g = sp.symbols("m l a gamma g", positive=True)
phi = sp.Function("phi")(t)
dphi = phi.diff(t)

COORDINATES = [phi]
ANGLES = [phi]

# The answer of the manual
LAGRANGIAN = (sp.Rational(1, 2) * m * l**2 * dphi**2 + m * l * a * gamma**2 * sp.cos(gamma * t) * sp.sin(phi)
              + m * g * l * sp.cos(phi))

# The particle in the engine frame (X = x, Y = -y)
POSITIONS = [sp.Matrix([a * sp.cos(gamma * t) + l * sp.sin(phi), -l * sp.cos(phi), 0])]
# L depends on t (the support does work): no conserved energy
ENERGY = None

# SI units; phi from the downward vertical, positive towards +x (the figure)
CASES = [
    dict(name="resonant", m=1.0, l=1.0, a=0.1, gamma=3.0, g=9.81, phi=0.0, dphi=0.0),
    dict(name="fast", m=0.5, l=0.6, a=0.05, gamma=15.0, g=9.81, phi=0.8, dphi=0.0),
]
DURATION = 5.0
