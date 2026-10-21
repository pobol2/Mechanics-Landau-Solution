# SPDX-License-Identifier: MIT
# Copyright (c) 2026 P.O. Bolduc. See LICENSE-CODE.
"""§5 Problem 1: coplanar double pendulum."""

import sympy as sp

t = sp.Symbol("t")
m1, m2, l1, l2, g = sp.symbols("m1 m2 l1 l2 g", positive=True)
phi1, phi2 = sp.Function("phi1")(t), sp.Function("phi2")(t)
dphi1, dphi2 = phi1.diff(t), phi2.diff(t)

COORDINATES = [phi1, phi2]
ANGLES = [phi1, phi2]

# The answer of the manual
LAGRANGIAN = (sp.Rational(1, 2) * (m1 + m2) * l1**2 * dphi1**2
              + sp.Rational(1, 2) * m2 * l2**2 * dphi2**2
              + m2 * l1 * l2 * dphi1 * dphi2 * sp.cos(phi1 - phi2)
              + (m1 + m2) * g * l1 * sp.cos(phi1) + m2 * g * l2 * sp.cos(phi2))

# Particles in the engine frame (X = x, Y = -y): m1, then m2
r1 = sp.Matrix([l1 * sp.sin(phi1), -l1 * sp.cos(phi1), 0])
r2 = r1 + sp.Matrix([l2 * sp.sin(phi2), -l2 * sp.cos(phi2), 0])
POSITIONS = [r1, r2]

# SI units; angles from the downward vertical, positive towards +x (the figure)
CASES = [
    dict(name="tumbling", m1=1.0, m2=1.0, l1=1.0, l2=1.0, g=9.81,
         phi1=2.0, phi2=2.5, dphi1=0.0, dphi2=4.0),
    dict(name="unequal", m1=2.0, m2=0.5, l1=1.2, l2=0.7, g=9.81,
         phi1=0.9, phi2=-0.6, dphi1=0.0, dphi2=1.0),
]
DURATION = 5.0
