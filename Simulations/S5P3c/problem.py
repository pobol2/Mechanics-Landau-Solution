# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""§5 Problem 3(c): pendulum whose point of support oscillates vertically, y = a cos(gamma t)."""

import sympy as sp

t = sp.Symbol("t")
m, l, a, gamma, g = sp.symbols("m l a gamma g", positive=True)
phi = sp.Function("phi")(t)
dphi = phi.diff(t)

COORDINATES = [phi]
ANGLES = [phi]

# The answer of the manual
LAGRANGIAN = (sp.Rational(1, 2) * m * l**2 * dphi**2 + m * l * a * gamma**2 * sp.cos(gamma * t) * sp.cos(phi)
              + m * g * l * sp.cos(phi))

# The particle in the engine frame (X = x, Y = -y), y pointing down
POSITIONS = [sp.Matrix([l * sp.sin(phi), -a * sp.cos(gamma * t) - l * sp.cos(phi), 0])]
# L depends on t (the support does work): no conserved energy
ENERGY = None

# SI units; phi from the downward vertical, positive towards +x (the figure).
# Kapitza: a fast drive (a^2 gamma^2 > 2 g l) holds the pendulum upside down;
# parametric: gamma = 2 sqrt(g / l) makes small swings grow.
CASES = [
    dict(name="Kapitza", m=1.0, l=0.3, a=0.05, gamma=60.0, g=9.81, phi=2.8, dphi=0.0),
    dict(name="parametric", m=1.0, l=1.0, a=0.1, gamma=6.26, g=9.81, phi=0.2, dphi=0.0),
]
DURATION = 5.0
DT = 0.002  # samples resolving the fast drive (period 0.1 s)
