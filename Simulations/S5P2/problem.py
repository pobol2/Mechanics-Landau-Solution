# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""§5 Problem 2: pendulum whose point of support m1 moves on a horizontal line."""

import sympy as sp

t = sp.Symbol("t")
m1, m2, l, g = sp.symbols("m1 m2 l g", positive=True)
x, phi = sp.Function("x")(t), sp.Function("phi")(t)
dx, dphi = x.diff(t), phi.diff(t)

COORDINATES = [x, phi]
ANGLES = [phi]

# The answer of the manual
LAGRANGIAN = (sp.Rational(1, 2) * (m1 + m2) * dx**2
              + sp.Rational(1, 2) * m2 * (l**2 * dphi**2 + 2 * l * dx * dphi * sp.cos(phi))
              + m2 * g * l * sp.cos(phi))

# Particles in the engine frame (X = x, Y = -y): m1, then m2
POSITIONS = [sp.Matrix([x, 0, 0]), sp.Matrix([x + l * sp.sin(phi), -l * sp.cos(phi), 0])]
# x is cyclic: its generalized momentum is the total horizontal momentum
CONSERVED = {"momentum_X": LAGRANGIAN.diff(dx)}

# SI units; phi from the downward vertical, positive towards +x (the figure)
CASES = [
    dict(name="looping", m1=1.0, m2=1.0, l=1.0, g=9.81,
         x=0.0, phi=0.5, dx=-3.5, dphi=8.0),
    dict(name="swinging", m1=3.0, m2=0.8, l=1.5, g=9.81,
         x=0.2, phi=1.2, dx=-0.3, dphi=0.0),
]
DURATION = 5.0
